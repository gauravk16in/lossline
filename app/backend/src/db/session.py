from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.config import settings

# engine setup optimized for Neon connection pooler (PgBouncer transaction mode)
# by setting prepared_statement_cache_size=0 inside connect_args
engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args={
        "prepared_statement_cache_size": 0,
        "ssl": True
    },
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# AsyncSession factory
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency yielding db session with async context management.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
