import sys
from typing import AsyncGenerator
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# Base Declarative Class for all ORM models
Base = declarative_base()

engine = None
AsyncSessionLocal = None

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    
    from sqlalchemy.pool import NullPool

    # Under pytest each TestClient call runs on its own event loop; pooled asyncpg
    # connections stay bound to the first loop ("attached to a different loop").
    # NullPool avoids caching them. Production keeps the regular pool.
    engine_kwargs = {"poolclass": NullPool} if "pytest" in sys.modules else {"pool_pre_ping": True}

    # Initialize async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.DEBUG,
        future=True,
        **engine_kwargs,
    )

    # Async Session Factory
    AsyncSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
except Exception as exc:
    # Graceful fallback when optional async driver (asyncpg) is not installed in the current environment
    print(f"[Database] Notice: Async driver not loaded ({exc}). Install dependencies via: pip install -r requirements.txt")


async def get_db() -> AsyncGenerator:
    """Dependency for providing transactional database sessions."""
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database driver (asyncpg) is not installed. Run: pip install -r requirements.txt"
        )
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
