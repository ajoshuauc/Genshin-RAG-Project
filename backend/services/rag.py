from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
from langchain_classic.retrievers import ContextualCompressionRetriever
import json

from backend.core.deps import get_llm_simple, get_llm_deep, get_vectorstore, get_reranker
from backend.core.config import config
from backend.services.utils import format_docs
from backend.services.memory import get_memory, persist_memory


def classify_query_complexity(question: str) -> dict:
    """
    Classify if a question is 'simple' or 'deep/complex'.
    Returns dict with 'complexity' and 'reasoning'.
    """
    llm = get_llm_simple()
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
    """Fast retrieval for simple questions - uses reranking for precision"""
    vs = get_vectorstore()
    
    base_retriever = vs.as_retriever(
        search_kwargs={"k": config.INITIAL_RETRIEVAL_K}
    )
    
    reranker = get_reranker()
    retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever
    )
    
    return retriever

def build_deep_retriever():
    """Precise retrieval for deep questions - uses reranking for accuracy"""
    vs = get_vectorstore()
    
    base_retriever = vs.as_retriever(
        search_kwargs={"k": config.INITIAL_RETRIEVAL_K}
    )
    
    # Add reranking for precision (using Cohere - fast and accurate)
    reranker = get_reranker()
    retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever
    )
    
    return retriever

def build_retriever(complexity: str = "simple"):
    """Route to appropriate retriever based on query complexity."""
    if complexity == "deep":
        return build_deep_retriever()
    else:
        return build_simple_retriever()

def rewrite_query(user_message: str, chat_history: str, summary: str) -> str:
    """Rewrite a follow-up message into a standalone search query using conversation context."""
    llm = get_llm_simple()
    prompt = ChatPromptTemplate.from_template(
        """Rewrite the user's latest message into a single standalone search query
            that captures the full intent, using the conversation context to resolve
            references like "he", "she", "it", "that", "more detail", etc.

            CONVERSATION SUMMARY:
            {summary}

            RECENT CHAT:
            {chat_history}

            USER MESSAGE: {question}

            Return ONLY the rewritten query, nothing else."""
    )
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "summary": summary or "(none)",
        "chat_history": chat_history or "(none)",
        "question": user_message,
    }).strip()


def build_answer_chain(llm):
    prompt = ChatPromptTemplate.from_template(
        """You are a knowledgeable Genshin Impact lore expert helping users understand the game's story and characters.

    Your task is to answer questions using ONLY the retrieved lore below. Present information naturally as your own expert knowledge.

    Guidelines:
    - Ground every factual claim in the retrieved lore.
    - Do NOT mix facts across different entities. If a chunk is about a different character/faction/event than the question, only use it if it explicitly links back to the asked entity.
    - If two chunks conflict, present both versions and do not merge them.
    - Do NOT include any chunk references or citations (e.g., [1], [2]) in your answer.
    - Never tell the user that lore or context was "provided" or "retrieved". Present information naturally as if you know it.
    - You may use CONVERSATION SUMMARY / RECENT CHAT only to resolve references (e.g., pronouns) or user intent, but do not introduce new lore facts unless supported by the retrieved lore.
    - If the retrieved lore does not support an answer, say what is missing and ask a brief clarifying question (do not guess).

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

    # Keep more recent messages: take last N from full chat history (not just buffer)
    all_messages = memory.chat_memory.messages
    n = config.RECENT_CHAT_MESSAGES_COUNT
    recent_msgs = all_messages[-n:] if len(all_messages) > n else all_messages

    chat_history_str = ""
    for m in recent_msgs:
        if m.type == "human":
            chat_history_str += f"User: {m.content}\n"
        elif m.type == "ai":
            chat_history_str += f"Assistant: {m.content}\n"

    summary = memory.moving_summary_buffer or ""

    # 1) Rewrite query to be standalone using conversation context
    search_query = rewrite_query(user_message, chat_history_str, summary)
    print(f"DEBUG: Rewritten query: {search_query}")

    # 2) Classify query complexity
    classification = classify_query_complexity(search_query)
    complexity = classification.get("complexity", "simple")
    
    print(f"DEBUG: Query classified as '{complexity}': {classification.get('reasoning', '')}")

    # 3) Select LLM based on complexity
    llm = get_llm_deep() if complexity == "deep" else get_llm_simple()

    # 4) Route to appropriate retriever
    retriever = build_retriever(complexity=complexity)
    docs = retriever.invoke(search_query)
    context = format_docs(docs)
    
    print(f"DEBUG: Retrieved {len(docs)} documents using {complexity} retrieval")
    print(f"DEBUG: Context length: {len(context)} characters")
    if context:
        print(f"DEBUG: Context preview (first 200 chars): {context[:200]}")
    else:
        print(f"DEBUG: Context is empty - using fallback")

    # 5) Generate answer
    answer_chain = build_answer_chain(llm)
    answer = answer_chain.invoke({
        "summary": summary or "(none yet)",
        "chat_history": chat_history_str or "(no recent chat)",
        "context": context or "(no docs retrieved)",
        "question": user_message,
    })

    # 6) Save interaction
    memory.save_context({"input": user_message}, {"output": answer})
    persist_memory(session_id, memory)

    sources = [{"metadata": d.metadata, "preview": d.page_content[:200]} for d in docs]
    return answer, sources