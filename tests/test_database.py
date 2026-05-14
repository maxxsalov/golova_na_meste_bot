import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_engine, get_session_factory


def test_get_engine_returns_async_engine():
    engine = get_engine("sqlite+aiosqlite:///test.db")
    assert "async" in str(type(engine)).lower()


def test_get_session_factory_returns_async_sessionmaker():
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine("sqlite+aiosqlite:///test.db")
    factory = get_session_factory(engine)
    assert factory.class_ == AsyncSession
