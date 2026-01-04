import os

class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "YOUR_KEY")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    EMB_MODEL: str = os.getenv("EMB_MODEL", "text-embedding-3-small")

    # Pinecone
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "genshin-lore")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "YOUR_KEY")

    # Postgres
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Retrieval
    TOP_K: int = int(os.getenv("TOP_K", "12"))

    # Memory
    MAX_TOKEN_LIMIT: int = int(os.getenv("MAX_TOKEN_LIMIT", "1000"))

config = Config()