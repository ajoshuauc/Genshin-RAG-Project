"""
Async SQLAlchemy engine and session factory for Supabase Postgres.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.core.config import config


def _get_async_url(url: str) -> str:
    """Convert plain postgresql:// URL to postgresql+psycopg:// for async SQLAlchemy."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url  # Already has a dialect suffix


# Create async engine with connection pooling.
# Keep pool small so async + sync (memory.py) stay under Supabase Session mode limit.
engine = create_async_engine(
    _get_async_url(config.DATABASE_URL),
    pool_pre_ping=True,  # Verify connections before use
    pool_size=2,
    max_overflow=3,
    echo=False,  # Set True for SQL debugging
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI dependency that yields an async database session.
    Usage: db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
