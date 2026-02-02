from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.v1.chat import router as chat_router
from backend.api.v1.sessions import router as sessions_router
from backend.core.config import config

app = FastAPI(title="Genshin RAG API", description="API for the Genshin RAG project")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
app.include_router(sessions_router, prefix="/api/v1", tags=["sessions"])