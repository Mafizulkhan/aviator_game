"""
Anti-Gravity Backend — Database Setup
Async SQLAlchemy engine + session factory using SQLite (dev) or PostgreSQL (prod).
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from backend.config import settings


# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,           # set True to log all SQL
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base class for all ORM models ──────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Dependency for FastAPI routes ──────────────────────────────────────────────
async def get_db() -> AsyncSession:
    """Yield a database session; always close after request."""
    async with AsyncSessionLocal() as session:
        yield session


# ── Create all tables ──────────────────────────────────────────────────────────
async def init_db():
    """Create all tables if they don't exist. Called on startup."""
    async with engine.begin() as conn:
        # Import all models so Base knows about them
        import backend.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
