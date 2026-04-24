"""End-to-end-ish test that duplicate payment webhooks don't extend premium twice.

We exercise the DB path directly: insert a Payment twice with the same tx_id
via the same upsert statement used by the handler, and verify only the first
insert reports rowcount==1 (the signal the handler uses to gate activation).
"""
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot.db import Base
from bot.models import Payment, User
from bot.services.subscription import activate_premium


@pytest.mark.asyncio
async def test_duplicate_payment_insert_is_no_op(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    # Patch bot.db to point at our test engine for activate_premium's session_scope
    import bot.db as db_mod
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", Session)

    async with Session() as s:
        s.add(User(tg_id=42, lang="vi", plan="free"))
        await s.commit()

    values = {
        "user_id": 42,
        "provider": "telegram_stars",
        "amount": 500,
        "currency": "XTR",
        "tx_id": "tx_abc_123",
        "status": "success",
        "raw_payload": "{}",
    }
    stmt = sqlite_insert(Payment).values(**values).on_conflict_do_nothing(index_elements=["tx_id"])

    async with Session() as s:
        r1 = await s.execute(stmt)
        await s.commit()
        assert r1.rowcount == 1, "first insert should succeed"

    async with Session() as s:
        r2 = await s.execute(stmt)
        await s.commit()
        assert r2.rowcount == 0, "duplicate tx_id should be a no-op"

    # Simulate the handler logic: activate ONLY on first insert.
    until = await activate_premium(42, 30)
    expected_window_start = datetime.now(UTC) + timedelta(days=29, hours=23)
    expected_window_end = datetime.now(UTC) + timedelta(days=30, minutes=1)
    assert expected_window_start < until < expected_window_end, (
        "first activation should extend ~30 days"
    )

    # If the handler had ignored the rowcount==0 signal and called activate_premium
    # again, premium_until would now be ~60 days out. We explicitly do NOT call it.
    async with Session() as s:
        user = await s.get(User, 42)
        assert user.plan == "premium"
        # SQLite drops tz info on read; normalize to naive UTC for comparison.
        stored = user.premium_until.replace(tzinfo=None) if user.premium_until.tzinfo else user.premium_until
        diff_days = (stored - datetime.now(UTC).replace(tzinfo=None)).total_seconds() / 86400
        assert 29.9 < diff_days < 30.1, f"expected ~30 day window, got {diff_days}"

    await engine.dispose()
