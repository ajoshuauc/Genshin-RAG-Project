from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.retrievers import MultiQueryRetriever

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
    return MultiQueryRetriever.from_llm(retrievers=base, llm=llm)

def build_answer_chain():
    llm = get_llm()
    prompt = ChatPromptTemplate.from_template(
        """You are a Genshin Impact lore explainer.

    Rules:
    - Use ONLY the LORE CONTEXT to answer.
    - If the context lacks info, say you don't have enough info.
    - Explain clearly, step-by-step, like teaching someone catching up.

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

def answer_with_rag(session_id: str, question: str) -> tuple[str, list]:
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

    
