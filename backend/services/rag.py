from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from backend.core.deps import get_llm, get_vectorstore
from backend.core.config import config
from backend.services.utils import format_docs
from backend.services.memory import get_memory, persist_memory


def build_query_rewrite_chain():
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """Rewrite this Genshin lore question into a short search query. Include key characters,regions, factions, and lore terms.

        User question: {question}
        Search query:"""
        )
    return prompt | llm | StrOutputParser()

def build_retriever():
    vs = get_vectorstore()
    llm = get_llm()

    base = vs.as_retriever(search_kwargs={"k": config.TOP_K})
    return base

def build_answer_chain():
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are a knowledgeable Genshin Impact lore expert helping users understand the game's story and characters.

    Your task is to answer questions using the provided LORE CONTEXT. The context may contain information from multiple sources - piece together relevant details to form a complete answer.

    Guidelines:
    - Synthesize information from ALL relevant context chunks, even if they don't directly state the answer
    - Make reasonable inferences based on the context (e.g., if context describes actions/behaviors, you can infer motivations)
    - Connect related information across different context sections
    - Use the CONVERSATION SUMMARY and RECENT CHAT to understand what was previously discussed
    - If the context contains ANY relevant information (even indirect), use it to answer - don't say "not enough info" unless the context is truly empty or completely unrelated
    - When context is limited, provide what you CAN infer and note any uncertainties
    - Explain clearly and comprehensively, as if teaching someone the lore

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

    # load memory variables (history messages)
    mem_vars = memory.load_memory_variables({})
    history_msgs = mem_vars.get("history", [])

    chat_history_str = ""
    for m in history_msgs:
        if m.type == "human":
            chat_history_str += f"User: {m.content}\n"
        elif m.type == "ai":
            chat_history_str += f"Assistant: {m.content}\n"

    # Rolling summary buffer (persisted separately)
    summary = memory.moving_summary_buffer or ""

    rewrite_chain = build_query_rewrite_chain()
    retriever = build_retriever()
    answer_chain = build_answer_chain()

    # 1) Rewrite query
    rewritten_query = rewrite_chain.invoke({"question": user_message})

    # 2) Retrieve relevant context - use invoke() instead of get_relevant_documents()
    docs = retriever.invoke(rewritten_query)
    context = format_docs(docs)
    
    # Debug logging
    print(f"DEBUG: Retrieved {len(docs)} documents")
    print(f"DEBUG: Context length: {len(context)} characters")
    if context:
        print(f"DEBUG: Context preview (first 200 chars): {context[:200]}")
    else:
        print(f"DEBUG: Context is empty - using fallback")

    # 3) Answer
    answer = answer_chain.invoke({
        "summary": summary or "(none yet)",
        "chat_history": chat_history_str or "(no recent chat)",
        "context": context or "(no docs retrieved)",
        "question": user_message,
    })

    # 4) Save interaction into SQLChatMessageHistory
    # This updates memory and may update moving_summary_buffer internally
    memory.save_context({"input": user_message}, {"output": answer})

    # 5) Persist the rolling summary buffer to sessions table
    persist_memory(session_id, memory)

    sources = [{"metadata": d.metadata, "preview": d.page_content[:200]} for d in docs]
    return answer, sources