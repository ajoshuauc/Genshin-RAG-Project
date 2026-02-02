from langchain_classic.memory import ConversationSummaryBufferMemory
from langchain_community.chat_message_histories import SQLChatMessageHistory
from sqlalchemy import create_engine

from backend.core.deps import get_memory_llm
from backend.core.config import config
from backend.db.session_store import get_summary, update_summary, init_sessions_table


def _get_sync_sqlalchemy_url(url: str) -> str:
    """Convert plain postgresql:// URL to postgresql+psycopg:// for sync SQLAlchemy."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url  # Already has a dialect suffix


# Single shared sync engine (small pool) so we don't exhaust Supabase Session mode.
_sync_engine = None


def _get_sync_engine():
    """Return the shared sync SQLAlchemy engine, creating it once on first use."""
    global _sync_engine
    if _sync_engine is None:
        if not config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set. Please set it in your .env file.")
        _sync_engine = create_engine(
            _get_sync_sqlalchemy_url(config.DATABASE_URL),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=2,
        )
    return _sync_engine


# Lazy initialization - only call when actually needed
_db_initialized = False


def _ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        if not config.DATABASE_URL:
            raise ValueError("DATABASE_URL is not set. Please set it in your .env file.")
        try:
            init_sessions_table()
            _db_initialized = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to database: {e}. Make sure the database is running.")


def get_memory(session_id: str) -> ConversationSummaryBufferMemory:
    """
    Creates a ConversationSummaryBufferMemory where:
    - raw messages are stored in Postgres by SQLChatMessageHistory
    - the rolling summary is loaded from / saved to our sessions table
    """
    # Ensure database is initialized before creating memory
    _ensure_db_initialized()

    # Use shared sync engine (single pool) instead of creating one per request
    engine = _get_sync_engine()
    history = SQLChatMessageHistory(session_id=session_id, connection=engine)

    memory = ConversationSummaryBufferMemory(
        llm=get_memory_llm(),  # Use memory-specific LLM with higher max_tokens
        chat_memory=history,
        max_token_limit=config.MAX_TOKEN_LIMIT,
        return_messages=True,
        memory_key="chat_history",
    )

    memory.moving_summary_buffer = get_summary(session_id) or ""
    return memory

def persist_memory(session_id: str, memory: ConversationSummaryBufferMemory) -> None:
    """
    Saves the current summary to the database.
    """
    update_summary(session_id, memory.moving_summary_buffer or "")