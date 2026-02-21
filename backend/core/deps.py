from functools import lru_cache
from uuid import UUID
from fastapi import Header, HTTPException
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_cohere import CohereRerank
from pydantic import SecretStr
from backend.core.config import config


# ---------------------------------------------------------------------------
# X-User-Id dependency (anonymous user scoping)
# ---------------------------------------------------------------------------
def get_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> UUID:
    """
    FastAPI dependency that extracts and validates the X-User-Id header.
    Returns a UUID. Raises 400 if missing or invalid.
    """
    try:
        return UUID(x_user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid or missing X-User-Id header (must be UUID)")

@lru_cache
def get_llm_simple() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=config.LLM_MODEL_SIMPLE,
        temperature=0,
        max_completion_tokens=config.LLM_MAX_TOKENS,
        timeout=60.0
    )

@lru_cache
def get_llm_deep() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=config.LLM_MODEL_DEEP,
        max_completion_tokens=config.LLM_MAX_TOKENS,
        timeout=60.0
    )

@lru_cache
def get_memory_llm() -> ChatOpenAI:
    """Separate LLM instance for memory summarization with higher max_tokens."""
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=config.LLM_MODEL_SIMPLE,
        temperature=0,
        max_completion_tokens=config.MEMORY_LLM_MAX_TOKENS,
        timeout=60.0
    )

@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        api_key=config.OPENAI_API_KEY,
        model=config.EMB_MODEL,
        dimensions=1536  # Match the dimension used in embedding script
    )

@lru_cache
def get_pinecone_client() -> Pinecone:
    # Pinecone v3 client style client
    return Pinecone(api_key=config.PINECONE_API_KEY)

@lru_cache
def get_vectorstore() -> PineconeVectorStore:
    """
    IMPORTANT: text_key must match what you used when upserting.
    We'll use "text" in the ingestion script below.
    """
    pc = get_pinecone_client()
    index = pc.Index(config.PINECONE_INDEX_NAME)

    return PineconeVectorStore(
        index=index,
        embedding=get_embeddings(),
        text_key="text"
    )

@lru_cache
def get_reranker() -> CohereRerank:
    if not config.COHERE_API_KEY:
        raise ValueError("COHERE_API_KEY is not set")

    return CohereRerank(
        cohere_api_key=SecretStr(config.COHERE_API_KEY),
        model="rerank-english-v3.0",
        top_n=config.RERANK_TOP_N
    )

# def get_retriever() -> PineconeVectorStore:
#     vectorstore = get_vectorstore()
#     return vectorstore.as_retriever(search_kwargs={"k": config.TOP_K})