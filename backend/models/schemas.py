from pydantic import BaseModel
from typing import Optional, Any, Dict, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ChatRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


# ---------------------------------------------------------------------------
# Chat endpoints
# ---------------------------------------------------------------------------
class ChatRequest(BaseModel):
    session_id: UUID
    message: str


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[Dict[str, Any]]] = None


# ---------------------------------------------------------------------------
# Sessions endpoints
# ---------------------------------------------------------------------------
class SessionSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class SessionListResponse(BaseModel):
    sessions: List[SessionSummary]


class MessageOut(BaseModel):
    id: UUID
    role: ChatRole
    content: str
    created_at: datetime


class SessionTranscriptResponse(BaseModel):
    session_id: UUID
    title: str
    messages: List[MessageOut]
