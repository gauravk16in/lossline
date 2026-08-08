import os
import sys
import pytest
from typing import AsyncGenerator, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models import Base  # noqa: E402
from app.db.session import get_db_session  # noqa: E402
from app.main import app  # noqa: E402

import logging  # noqa: E402

# Suppress verbose debug logs during testing
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

import pytest_asyncio  # noqa: E402

# SQLite in-memory test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """
    Create a test database engine and run table migrations.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
    )

    # Create all tables in-memory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a transactional database session for unit testing, rolling back changes.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    SessionLocal = async_sessionmaker(
        bind=connection, expire_on_commit=False, class_=AsyncSession
    )

    async with SessionLocal() as session:
        yield session

    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture
async def client_override(db_session):
    """
    Overrides the FastAPI dependency get_db_session to use the test session.
    """

    async def _get_db_session_override():
        yield db_session

    app.dependency_overrides[get_db_session] = _get_db_session_override
    yield
    app.dependency_overrides.pop(get_db_session, None)


class MockRedisClient:
    """
    Mock Redis client emulating Streams for isolated testing.
    """

    def __init__(self) -> None:
        self.streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self.groups: dict[str, set[str]] = {}

    async def xadd(
        self, name: str, fields: dict[str, Any], *args: Any, **kwargs: Any
    ) -> str:
        if name not in self.streams:
            self.streams[name] = []
        msg_id = f"{len(self.streams[name]) + 1}-0"
        self.streams[name].append((msg_id, fields))
        return msg_id

    async def xgroup_create(
        self,
        name: str,
        groupname: str,
        id: str = "0",
        mkstream: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if name not in self.groups:
            self.groups[name] = set()
        self.groups[name].add(groupname)

    async def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int | None = None,
        block: int | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]]:
        results: list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]] = []
        for stream_name, last_id in streams.items():
            if stream_name in self.streams and self.streams[stream_name]:
                msgs = []
                for msg_id, fields in self.streams[stream_name]:
                    # Encode keys and values to bytes to mirror redis-py interface
                    encoded_fields = {
                        k.encode("utf-8") if isinstance(k, str) else k: (
                            v.encode("utf-8") if isinstance(v, str) else v
                        )
                        for k, v in fields.items()
                    }
                    msgs.append((msg_id.encode("utf-8"), encoded_fields))
                results.append((stream_name.encode("utf-8"), msgs))
                # Clear stream as read group messages for simplistic mock behavior
                self.streams[stream_name] = []
        return results

    async def xack(
        self, name: str, groupname: str, *ids: bytes | str, **kwargs: Any
    ) -> int:
        return len(ids)

    async def close(self) -> None:
        pass


@pytest.fixture
def mock_redis() -> MockRedisClient:
    return MockRedisClient()
