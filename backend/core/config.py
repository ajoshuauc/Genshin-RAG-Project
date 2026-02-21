import os
from pydantic import SecretStr

class Config:
    OPENAI_API_KEY: SecretStr = SecretStr(os.getenv("OPENAI_API_KEY", "YOUR_KEY"))
    LLM_MODEL_SIMPLE: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_MODEL_DEEP: str = os.getenv("LLM_MODEL_DEEP", "gpt-5-mini")
    EMB_MODEL: str = os.getenv("EMB_MODEL", "text-embedding-3-small")

    # Pinecone
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "genshin-lore")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "YOUR_KEY")

    # Cohere
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "YOUR_KEY")

    # Postgres (async: postgresql+asyncpg://...)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # CORS
    CORS_ALLOW_ORIGINS: list[str] = os.getenv(
        "CORS_ALLOW_ORIGINS", "http://localhost:3000"
    ).split(",")

    # Retrieval
    INITIAL_RETRIEVAL_K: int = int(os.getenv("INITIAL_RETRIEVAL_K", "10"))  # For deep questions before reranking
    RERANK_TOP_N: int = int(os.getenv("RERANK_TOP_N", "3"))  # Final docs after reranking

    # LLM Performance
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "3000"))  # Limit response length for faster generation
    MAX_CONTEXT_LENGTH: int = int(os.getenv("MAX_CONTEXT_LENGTH", "16000"))  # Limit context characters

    # Memory
    MAX_TOKEN_LIMIT: int = int(os.getenv("MAX_TOKEN_LIMIT", "1000"))
    MEMORY_LLM_MAX_TOKENS: int = int(os.getenv("MEMORY_LLM_MAX_TOKENS", "2000"))  # Higher limit for summary generation
    RECENT_CHAT_MESSAGES_COUNT: int = int(os.getenv("RECENT_CHAT_MESSAGES_COUNT", "12"))  # Last N messages (e.g. 12 = 6 exchanges) in RAG context

config = Config()