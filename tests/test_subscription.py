from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.db as db_mod
from bot.db import Base
from bot.models import User
from bot.services.subscription import activate_premium


async def _fresh_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", Session)
    return engine, Session


@pytest.mark.asyncio
async def test_activate_from_free_starts_at_now(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=1, lang="vi", plan="free"))
        await s.commit()

    before = datetime.now(UTC)
    until = await activate_premium(1, 30)
    assert until > before + timedelta(days=29, hours=23)
    assert until < before + timedelta(days=30, minutes=1)

    await engine.dispose()


@pytest.mark.asyncio
async def test_renewal_extends_from_existing_expiry(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    existing_expiry = datetime.now(UTC) + timedelta(days=10)
    async with Session() as s:
        s.add(User(tg_id=2, lang="vi", plan="premium", premium_until=existing_expiry))
        await s.commit()

    until = await activate_premium(2, 30)
    # Should be existing + 30 days, not now + 30
    diff = (until - existing_expiry).total_seconds()
    assert abs(diff - 30 * 86400) < 60, f"renewal should add 30 days, got diff={diff}s"

    await engine.dispose()


@pytest.mark.asyncio
async def test_activate_creates_user_if_missing(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    # No user inserted yet
    until = await activate_premium(999, 30)
    assert until is not None

    async with Session() as s:
        user = await s.get(User, 999)
        assert user is not None
        assert user.plan == "premium"

    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_premium_renews_from_now_not_past(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    past_expiry = datetime.now(UTC) - timedelta(days=5)  # already expired
    async with Session() as s:
        s.add(User(tg_id=3, lang="vi", plan="premium", premium_until=past_expiry))
        await s.commit()

    before = datetime.now(UTC)
    until = await activate_premium(3, 30)
    # Past expiry should be ignored; new expiry ~now+30d, not past+30d
    assert until > before + timedelta(days=29, hours=23)

    await engine.dispose()
