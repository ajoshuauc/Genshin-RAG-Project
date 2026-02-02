from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import anyio

from backend.models.schemas import ChatRequest, ChatResponse
from backend.services.rag import answer_with_rag
from backend.db.database import get_db
from backend.core.deps import get_user_id
from backend.db import chat_repo

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: UUID = Depends(get_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Two-phase chat persistence:
    - Txn 1: upsert user, ensure/verify session, insert user message
    - LLM/RAG call (outside transaction)
    - Txn 2: insert assistant message, touch session updated_at
    """
    session_id = request.session_id
    user_message = request.message

    # Generate message IDs upfront
    user_msg_id = uuid4()
    assistant_msg_id = uuid4()

    # -------------------------------------------------------------------------
    # Txn 1: Pre-LLM writes
    # -------------------------------------------------------------------------
    try:
        async with db.begin():
            # Upsert user (update last_seen_at)
            await chat_repo.upsert_user(db, user_id)

            # Ensure session exists or verify ownership
            try:
                await chat_repo.get_or_create_session(db, session_id, user_id)
            except PermissionError:
                raise HTTPException(status_code=404, detail="Session not found")

            # Insert user message
            await chat_repo.insert_message(
                db,
                message_id=user_msg_id,
                session_id=session_id,
                role="user",
                content=user_message,
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error (Txn1): {e}")

    # -------------------------------------------------------------------------
    # LLM/RAG call (outside transaction to avoid holding locks)
    # -------------------------------------------------------------------------
    try:
        # answer_with_rag is synchronous; run in threadpool
        assistant_content, sources = await anyio.to_thread.run_sync(
            lambda: answer_with_rag(str(session_id), user_message)
        )
    except Exception as e:
        # LLM failed; user message is already saved, but no assistant response
        raise HTTPException(status_code=500, detail=f"RAG error: {e}")

    # -------------------------------------------------------------------------
    # Txn 2: Post-LLM writes
    # -------------------------------------------------------------------------
    try:
        async with db.begin():
            # Insert assistant message
            await chat_repo.insert_message(
                db,
                message_id=assistant_msg_id,
                session_id=session_id,
                role="assistant",
                content=assistant_content,
                meta={"sources_count": len(sources) if sources else 0},
            )

            # Touch session updated_at
            await chat_repo.touch_session(db, session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error (Txn2): {e}")

    return ChatResponse(response=assistant_content, sources=sources)