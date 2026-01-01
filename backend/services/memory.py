from langchain_classic.memory import ConversationSummaryBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory

from backend.core.deps import get_llm
from backend.core.config import config
from backend.db.session_store import get_summary, update_summary, init_sessions_table

#Ensure the sessions table exists
init_sessions_table()

def get_memory(session_id: str) -> ConversationSummaryBufferMemory:
    """
    Creates a ConversationSummaryBufferMemory where:
    - raw messages are stored in Postgres by SQLChatMessageHistory
    - the rolling summary is loaded from / saved to our sessions table
    """

    history = SQLChatMessageHistory(session_id=session_id, connection_string=config.DATABASE_URL)

    memory = ConversationSummaryBufferMemory(
        llm=get_llm(),
        chat_memory=history,
        max_token_limit=config.MAX_TOKEN_LIMIT,
        return_messages=True,
    )

    memory.moving_summary_buffer = get_summary(session_id) or ""
    return memory

def persist_memory(session_id: str, memory: ConversationSummaryBufferMemory) -> None:
    """
    Saves the current summary to the database.
    """
    update_summary(session_id, memory.moving_summary_buffer or "")