from functools import lru_cache
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

from core.config import config

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
    metadata_keys should match what you used when upserting.
    """
    pc = get_pinecone_client()
    index = pc.Index(config.PINECONE_INDEX_NAME)

    return PineconeVectorStore(
        index=index,
        embedding=get_embeddings(),
        text_key="text",
        metadata_keys=["type", "title", "section", "url", "lang", "content_type", "characters"]
    )

# def get_retriever() -> PineconeVectorStore:
#     vectorstore = get_vectorstore()
#     return vectorstore.as_retriever(search_kwargs={"k": config.TOP_K})
