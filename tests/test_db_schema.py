"""Smoke test: make sure SQLAlchemy can build all models and create schema
against an in-memory SQLite database."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from bot import models  # noqa: F401 — ensure all models registered
from bot.db import Base


@pytest.mark.asyncio
async def test_schema_creates_cleanly():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    table_names = set(Base.metadata.tables.keys())
    assert {"users", "alerts", "trades", "payments"} <= table_names

    await engine.dispose()
