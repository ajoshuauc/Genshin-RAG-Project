"""
Async data-access layer for chat persistence (users, sessions, messages).
"""
from uuid import UUID
from datetime import datetime
from typing import Optional
from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
async def upsert_user(db: AsyncSession, user_id: UUID) -> None:
    """
    Insert user if not exists; always update last_seen_at.
    """
    await db.execute(
        text("""
            INSERT INTO users (id, created_at, last_seen_at)
            VALUES (:user_id, now(), now())
            ON CONFLICT (id) DO UPDATE SET last_seen_at = now()
        """),
        {"user_id": user_id},
    )


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
async def get_session_owner(db: AsyncSession, session_id: UUID) -> Optional[UUID]:
    """
    Return the user_id that owns this session, or None if session doesn't exist.
    """
    result = await db.execute(
        text("SELECT user_id FROM chat_sessions WHERE id = :session_id"),
        {"session_id": session_id},
    )
    row = result.fetchone()
    return row[0] if row else None


async def create_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
    title: str = "New Conversation",
) -> None:
    """
    Create a new chat session.
    """
    await db.execute(
        text("""
            INSERT INTO chat_sessions (id, user_id, title, created_at, updated_at)
            VALUES (:session_id, :user_id, :title, now(), now())
        """),
        {"session_id": session_id, "user_id": user_id, "title": title},
    )


async def get_or_create_session(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
) -> bool:
    """
    Ensure session exists and belongs to user.
    Returns True if OK, raises exception if ownership mismatch.
    """
    owner = await get_session_owner(db, session_id)
    if owner is None:
        await create_session(db, session_id, user_id)
        return True
    if owner != user_id:
        raise PermissionError("Session does not belong to this user")
    return True


async def touch_session(db: AsyncSession, session_id: UUID) -> None:
    """
    Update session's updated_at to now().
    """
    await db.execute(
        text("UPDATE chat_sessions SET updated_at = now() WHERE id = :session_id"),
        {"session_id": session_id},
    )


async def list_sessions(db: AsyncSession, user_id: UUID) -> list[dict]:
    """
    List all non-deleted sessions for a user, ordered by updated_at desc.
    """
    result = await db.execute(
        text("""
            SELECT id, title, created_at, updated_at
            FROM chat_sessions
            WHERE user_id = :user_id AND deleted_at IS NULL
            ORDER BY updated_at DESC
        """),
        {"user_id": user_id},
    )
    rows = result.fetchall()
    return [
        {
            "id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
async def insert_message(
    db: AsyncSession,
    message_id: UUID,
    session_id: UUID,
    role: str,
    content: str,
    meta: dict | None = None,
) -> None:
    """
    Insert a chat message.
    """
    stmt = text("""
            INSERT INTO chat_messages (id, session_id, role, content, created_at, meta)
            VALUES (:id, :session_id, CAST(:role AS public.chat_role), :content, now(), :meta)
        """).bindparams(
        bindparam("meta", type_=JSONB),
    )
    await db.execute(
        stmt,
        {
            "id": message_id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "meta": meta or {},
        },
    )


async def get_transcript(
    db: AsyncSession,
    session_id: UUID,
    user_id: UUID,
) -> tuple[dict | None, list[dict]]:
    """
    Verify session ownership and return (session_info, messages).
    Returns (None, []) if session not found or not owned.
    """
    # Verify ownership
    result = await db.execute(
        text("""
            SELECT id, title, user_id
            FROM chat_sessions
            WHERE id = :session_id AND deleted_at IS NULL
        """),
        {"session_id": session_id},
    )
    session_row = result.fetchone()
    if session_row is None:
        return None, []
    if session_row[2] != user_id:
        return None, []

    session_info = {"id": session_row[0], "title": session_row[1]}

    # Fetch messages
    result = await db.execute(
        text("""
            SELECT id, role, content, created_at
            FROM chat_messages
            WHERE session_id = :session_id
            ORDER BY created_at ASC
        """),
        {"session_id": session_id},
    )
    rows = result.fetchall()
    messages = [
        {
            "id": row[0],
            "role": row[1],
            "content": row[2],
            "created_at": row[3],
        }
        for row in rows
    ]
    return session_info, messages
