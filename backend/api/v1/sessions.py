from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.schemas import (
    SessionListResponse,
    SessionSummary,
    SessionTranscriptResponse,
    MessageOut,
    ChatRole,
)
from backend.db.database import get_db
from backend.core.deps import get_user_id
from backend.db import chat_repo

router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    List all sessions for the current user, ordered by updated_at desc.
    Excludes soft-deleted sessions.
    """
    sessions = await chat_repo.list_sessions(db, user_id)
    return SessionListResponse(
        sessions=[
            SessionSummary(
                id=s["id"],
                title=s["title"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
            for s in sessions
        ]
    )


@router.get("/sessions/{session_id}", response_model=SessionTranscriptResponse)
async def get_session_transcript(
    session_id: UUID,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a session's transcript (messages ordered by created_at asc).
    Verifies session ownership.
    """
    session_info, messages = await chat_repo.get_transcript(db, session_id, user_id)

    if session_info is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionTranscriptResponse(
        session_id=session_info["id"],
        title=session_info["title"],
        messages=[
            MessageOut(
                id=m["id"],
                role=ChatRole(m["role"]),
                content=m["content"],
                created_at=m["created_at"],
            )
            for m in messages
        ],
    )
