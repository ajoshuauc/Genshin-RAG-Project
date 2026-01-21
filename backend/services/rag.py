from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers import MultiQueryRetriever
import json

from backend.core.deps import get_llm, get_vectorstore, get_reranker
from backend.core.config import config
from backend.services.utils import format_docs
from backend.services.memory import get_memory, persist_memory


def classify_query_complexity(question: str) -> dict:
    """
    Classify if a question is 'simple' or 'deep/complex'.
    Returns dict with 'complexity' and 'reasoning'.
    """
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """Classify this Genshin Impact lore question as either 'simple' or 'deep'.

        A 'simple' question:
        - Asks for a straightforward fact (e.g., "Who is Zhongli?", "What is Mondstadt?")
        - Has a direct answer in the lore
        - Requires basic retrieval only

        A 'deep' question:
        - Requires analysis, comparison, or synthesis (e.g., "How does Raiden's philosophy differ from Venti's?")
        - Asks about relationships, motivations, or complex themes
        - Needs precise document ranking to find the most relevant information
        - May require connecting information across multiple sources

        Question: {question}

        Respond with JSON:
        {{
            "complexity": "simple" or "deep",
            "reasoning": "brief explanation"
        }}"""
    )
    
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"question": question})
    
    try:
        # Try to parse JSON response
        result = json.loads(response)
    except:
        # Fallback: check if response contains keywords
        if "deep" in response.lower():
            result = {"complexity": "deep", "reasoning": response}
        else:
            result = {"complexity": "simple", "reasoning": response}
    
    return result

def build_simple_retriever():
    """Fast retrieval for simple questions - uses multi-query for better coverage"""
    vs = get_vectorstore()
    llm = get_llm()
    
    base_retriever = vs.as_retriever(
        search_kwargs={"k": config.TOP_K}
    )
    
    # Use multi-query for better query understanding (fast, low latency)
    retriever = MultiQueryRetriever.from_llm(
        retriever=base_retriever,
        llm=llm,
        include_original=True
    )
    
    return retriever

def build_deep_retriever():
    """Precise retrieval for deep questions - uses reranking for accuracy"""
    vs = get_vectorstore()
    llm = get_llm()
    
    # Retrieve more documents initially
    base_retriever = vs.as_retriever(
        search_kwargs={"k": config.INITIAL_RETRIEVAL_K}  # e.g., 20
    )
    
    # Add reranking for precision (using Cohere - fast and accurate)
    reranker = get_reranker()
    retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever
    )
    
    return retriever

def build_retriever(complexity: str = "simple"):
    """
    Route to appropriate retriever based on query complexity.
    
    Args:
        complexity: "simple" or "deep"
    """
    if complexity == "deep":
        return build_deep_retriever()
    else:
        return build_simple_retriever()

def build_answer_chain():
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are a knowledgeable Genshin Impact lore expert helping users understand the game's story and characters.

    Your task is to answer questions using ONLY the provided LORE CONTEXT below. The context is split into numbered chunks like [1], [2], etc.

    Guidelines:
    - Ground every factual claim in the LORE CONTEXT.
    - After every sentence that states a fact, add citations like [1] or [2][5] referring to the chunk numbers.
    - Do NOT mix facts across different entities. If a chunk is about a different character/faction/event than the question, only use it if it explicitly links back to the asked entity, and cite it.
    - If two chunks conflict, present both versions with citations and do not merge them.
    - You may use CONVERSATION SUMMARY / RECENT CHAT only to resolve references (e.g., pronouns) or user intent, but do not introduce new lore facts unless supported by LORE CONTEXT.
    - If the LORE CONTEXT does not support an answer, say what is missing and ask a brief clarifying question (do not guess).

    CONVERSATION SUMMARY:
    {summary}

    RECENT CHAT:
    {chat_history}

    LORE CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:"""
            )
    return prompt | llm | StrOutputParser()

def answer_with_rag(session_id: str, user_message: str) -> tuple[str, list]:
    memory = get_memory(session_id)

    # Load memory variables
    mem_vars = memory.load_memory_variables({})
    history_msgs = mem_vars.get("history", [])

    chat_history_str = ""
    for m in history_msgs:
        if m.type == "human":
            chat_history_str += f"User: {m.content}\n"
        elif m.type == "ai":
            chat_history_str += f"Assistant: {m.content}\n"

    summary = memory.moving_summary_buffer or ""

    # 0) Classify query complexity
    classification = classify_query_complexity(user_message)
    complexity = classification.get("complexity", "simple")
    
    print(f"DEBUG: Query classified as '{complexity}': {classification.get('reasoning', '')}")

    # 1) Route to appropriate retriever (use the original user message as the query)
    retriever = build_retriever(complexity=complexity)
    docs = retriever.invoke(user_message)
    context = format_docs(docs)
    
    print(f"DEBUG: Retrieved {len(docs)} documents using {complexity} retrieval")
    print(f"DEBUG: Context length: {len(context)} characters")
    if context:
        print(f"DEBUG: Context preview (first 200 chars): {context[:200]}")
    else:
        print(f"DEBUG: Context is empty - using fallback")

    # 3) Generate answer
    answer_chain = build_answer_chain()
    answer = answer_chain.invoke({
        "summary": summary or "(none yet)",
        "chat_history": chat_history_str or "(no recent chat)",
        "context": context or "(no docs retrieved)",
        "question": user_message,
    })

    # 4) Save interaction
    memory.save_context({"input": user_message}, {"output": answer})
    persist_memory(session_id, memory)

    sources = [{"metadata": d.metadata, "preview": d.page_content[:200]} for d in docs]
    return answer, sources