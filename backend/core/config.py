import os
from pydantic import SecretStr

class Config:
    OPENAI_API_KEY: SecretStr = SecretStr(os.getenv("OPENAI_API_KEY", "YOUR_KEY"))
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-5-mini")
    EMB_MODEL: str = os.getenv("EMB_MODEL", "text-embedding-3-small")

    # Pinecone
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "genshin-lore")
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "YOUR_KEY")

    # Cohere
    COHERE_API_KEY: str = os.getenv("COHERE_API_KEY", "YOUR_KEY")

    # Postgres
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Retrieval
    TOP_K: int = int(os.getenv("TOP_K", "20"))
    INITIAL_RETRIEVAL_K: int = int(os.getenv("INITIAL_RETRIEVAL_K", "20"))  # For deep questions before reranking
    RERANK_TOP_N: int = int(os.getenv("RERANK_TOP_N", "12"))  # Final docs after reranking

    # Memory
    MAX_TOKEN_LIMIT: int = int(os.getenv("MAX_TOKEN_LIMIT", "1000"))

config = Config()