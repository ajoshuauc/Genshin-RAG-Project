from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
from langchain_classic.retrievers import ContextualCompressionRetriever
import json

from backend.core.deps import get_llm_simple, get_llm_deep, get_vectorstore, get_reranker
from backend.core.config import config
from backend.services.utils import format_docs
from backend.services.memory import get_memory, persist_memory


def classify_query(question: str) -> dict:
    """Classify a standalone question as 'simple' or 'deep'. Used for first messages only."""
    llm = get_llm_simple()
    prompt = ChatPromptTemplate.from_template(
        """Classify this Genshin Impact lore question as either 'simple' or 'deep'.

        simple: straightforward fact lookup (e.g., "Who is Zhongli?", "What is Mondstadt?")
        deep: requires analysis, comparison, synthesis, or connecting multiple sources
              (e.g., "How does Ei's ideal of eternity compare to Zhongli's idea of contracts?")

        Question: {question}

        Respond with JSON only:
        {{"complexity": "simple" or "deep", "reasoning": "one sentence"}}"""
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"question": question})

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        if "deep" in response.lower():
            return {"complexity": "deep", "reasoning": response}
        return {"complexity": "simple", "reasoning": response}


def rewrite_and_classify(user_message: str, chat_history: str, summary: str) -> dict:
    """Rewrite a follow-up into a standalone search query AND classify complexity in one call."""
    llm = get_llm_simple()
    prompt = ChatPromptTemplate.from_template(
        """You are a Genshin Impact lore search assistant.

Given conversation context and a user message, do TWO things:

1. REWRITE the user's message into a standalone search query optimized for
   retrieving Genshin Impact lore. Resolve all pronouns and references
   ("he", "she", "it", "that", "more detail", etc.) using the conversation
   context. Use canonical Genshin terms — character titles (e.g. "Raiden
   Shogun" not "the electro archon lady"), region names (Mondstadt, Liyue,
   Inazuma, Sumeru, Fontaine, Natlan, Snezhnaya), faction names (Fatui,
   Knights of Favonius, Abyss Order), and item/concept names as they appear
   in-game.

2. CLASSIFY the query complexity:
   - "simple": straightforward fact lookup (e.g., "Who is Zhongli?")
   - "deep": requires analysis, comparison, synthesis, or connecting
     multiple sources (e.g., "How does Ei's ideal of eternity compare to
     Zhongli's idea of contracts?")

CONVERSATION SUMMARY:Did 
{summary}

RECENT CHAT:
{chat_history}

USER MESSAGE: {question}

Respond with JSON only:
{{"rewritten_query": "...", "complexity": "simple" or "deep", "reasoning": "one sentence"}}"""
    )
    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({
        "summary": summary or "(none)",
        "chat_history": chat_history or "(none)",
        "question": user_message,
    }).strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "rewritten_query": user_message,
            "complexity": "deep" if "deep" in response.lower() else "simple",
            "reasoning": response,
        }

def build_simple_retriever():
    """Fast retrieval for simple questions — k=10, rerank top 3."""
    vs = get_vectorstore()
    base_retriever = vs.as_retriever(
        search_kwargs={"k": config.SIMPLE_RETRIEVAL_K}
    )
    reranker = get_reranker(top_n=config.SIMPLE_RERANK_TOP_N)
    return ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever
    )

def build_deep_retriever():
    """Wider retrieval for deep questions — k=15, rerank top 5."""
    vs = get_vectorstore()
    base_retriever = vs.as_retriever(
        search_kwargs={"k": config.DEEP_RETRIEVAL_K}
    )
    reranker = get_reranker(top_n=config.DEEP_RERANK_TOP_N)
    return ContextualCompressionRetriever(
        base_compressor=reranker, base_retriever=base_retriever
    )

def build_retriever(complexity: str = "simple"):
    """Route to appropriate retriever based on query complexity."""
    if complexity == "deep":
        return build_deep_retriever()
    return build_simple_retriever()


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
    - If asked about something random or not related to the game, say that you are a Genshin Impact lore expert and you can only answer questions about the game.

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

    is_first_message = len(all_messages) == 0

    if is_first_message:
        search_query = user_message
        classification = classify_query(user_message)
        complexity = classification.get("complexity", "simple")
        print(f"DEBUG: First message — skipped rewrite")
    else:
        result = rewrite_and_classify(user_message, chat_history_str, summary)
        search_query = result["rewritten_query"]
        complexity = result.get("complexity", "simple")
        print(f"DEBUG: Rewritten query: {search_query}")

    print(f"DEBUG: Query classified as '{complexity}'")

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