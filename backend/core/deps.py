from functools import lru_cache
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from langchain_cohere import CohereRerank

from backend.core.config import config

@lru_cache
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=config.OPENAI_API_KEY,
        model=config.LLM_MODEL, 
        temperature=0
    )

@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        api_key=config.OPENAI_API_KEY,
        model=config.EMB_MODEL
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
        cohere_api_key=config.COHERE_API_KEY,
        model="rerank-english-v3.0",
        top_n=config.RERANK_TOP_N
    )

# def get_retriever() -> PineconeVectorStore:
#     vectorstore = get_vectorstore()
#     return vectorstore.as_retriever(search_kwargs={"k": config.TOP_K})