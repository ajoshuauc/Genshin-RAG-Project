from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from backend.api.v1.chat import router as chat_router

app = FastAPI(title="Genshin RAG API", description="API for the Genshin RAG project")

app.include_router(chat_router, prefix="/api/v1", tags=["chat"])