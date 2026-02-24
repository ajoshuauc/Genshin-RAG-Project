"""
Async SQLAlchemy engine and session factory for Supabase Postgres.
Includes SSL support and connection pooling.
"""
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.core.config import config


def _get_async_url(url: str) -> str:
    """
    Convert plain postgresql:// URL to postgresql+asyncpg:// for async SQLAlchemy.
    Supabase requires asyncpg for async connections.
    """
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url  # Already has a dialect suffix


# Async engine with SSL and connection pooling
engine = create_async_engine(
    _get_async_url(config.DATABASE_URL),
    pool_pre_ping=True,         # Check connections before use
    pool_size=2,                # Small pool for Supabase session limits
    max_overflow=3,             # Allow small burst connections
    echo=False,                 # Set True for SQL debugging
    connect_args={"ssl": "require"},  # Enable SSL for Supabase
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async database session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()