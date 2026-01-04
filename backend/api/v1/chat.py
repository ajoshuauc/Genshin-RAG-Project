from fastapi import APIRouter
from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.rag import answer_with_rag

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    response, sources = answer_with_rag(request.session_id, request.message)
    return ChatResponse(response=response, sources=sources)