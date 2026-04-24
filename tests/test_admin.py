"""Tests for admin command handlers."""
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.db as db_mod
from bot.db import Base
from bot.models import Alert, Payment, Trade, User

os.environ.setdefault("OWNER_TG_ID", "999")


async def _fresh_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", Session)
    return engine, Session


def _make_update(tg_id: int, text: str = "", args: list[str] | None = None):
    """Build a minimal mock Update for command handlers."""
    user = MagicMock()
    user.id = tg_id

    message = MagicMock()
    message.reply_text = AsyncMock()
    message.edit_text = AsyncMock()

    update = MagicMock()
    update.effective_user = user
    update.message = message
    return update


def _make_context(args: list[str] | None = None, bot=None):
    ctx = MagicMock()
    ctx.args = args or []
    ctx.bot = bot or MagicMock()
    ctx.bot.send_message = AsyncMock()
    return ctx


# ── Guard ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_non_owner_blocked(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    from bot.handlers.admin import admin_stats
    update = _make_update(tg_id=123)
    await admin_stats(update, _make_context())
    update.message.reply_text.assert_called_once_with("⛔ Unauthorized.")


@pytest.mark.asyncio
async def test_no_owner_configured_blocks_all(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", None)
    from bot.handlers.admin import admin_stats
    update = _make_update(tg_id=999)
    await admin_stats(update, _make_context())
    update.message.reply_text.assert_called_once_with("⛔ Unauthorized.")


# ── /admin stats ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats_returns_overview(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=1, lang="vi", plan="free"))
        s.add(User(tg_id=2, lang="vi", plan="premium"))
        await s.commit()

    from bot.handlers.admin import admin_stats
    update = _make_update(tg_id=999)
    await admin_stats(update, _make_context())

    call_text = update.message.reply_text.call_args[0][0]
    assert "2" in call_text      # total users
    assert "1 premium" in call_text
    await engine.dispose()


# ── /userinfo ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_userinfo_found(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=42, lang="en", plan="premium", username="alice"))
        await s.commit()

    from bot.handlers.admin import admin_userinfo
    update = _make_update(tg_id=999)
    await admin_userinfo(update, _make_context(args=["42"]))

    text = update.message.reply_text.call_args[0][0]
    assert "42" in text
    assert "premium" in text
    await engine.dispose()


@pytest.mark.asyncio
async def test_userinfo_not_found(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    engine, Session = await _fresh_db(monkeypatch)

    from bot.handlers.admin import admin_userinfo
    update = _make_update(tg_id=999)
    await admin_userinfo(update, _make_context(args=["9999"]))

    text = update.message.reply_text.call_args[0][0]
    assert "not found" in text
    await engine.dispose()


@pytest.mark.asyncio
async def test_userinfo_invalid_id(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    from bot.handlers.admin import admin_userinfo
    update = _make_update(tg_id=999)
    await admin_userinfo(update, _make_context(args=["abc"]))
    text = update.message.reply_text.call_args[0][0]
    assert "Invalid" in text


# ── /grant ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_grant_upgrades_user(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=5, lang="vi", plan="free"))
        await s.commit()

    from bot.handlers.admin import admin_grant
    update = _make_update(tg_id=999)
    await admin_grant(update, _make_context(args=["5", "30"]))

    async with Session() as s:
        user = await s.get(User, 5)
        assert user.plan == "premium"
        assert user.premium_until is not None

    text = update.message.reply_text.call_args[0][0]
    assert "30" in text
    await engine.dispose()


@pytest.mark.asyncio
async def test_grant_missing_args(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    from bot.handlers.admin import admin_grant
    update = _make_update(tg_id=999)
    await admin_grant(update, _make_context(args=["5"]))  # missing days
    text = update.message.reply_text.call_args[0][0]
    assert "Usage" in text


# ── /revoke ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_downgrades_user(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    engine, Session = await _fresh_db(monkeypatch)
    expiry = datetime.now(UTC) + timedelta(days=30)
    async with Session() as s:
        s.add(User(tg_id=7, lang="vi", plan="premium", premium_until=expiry))
        await s.commit()

    from bot.handlers.admin import admin_revoke
    update = _make_update(tg_id=999)
    await admin_revoke(update, _make_context(args=["7"]))

    async with Session() as s:
        user = await s.get(User, 7)
        assert user.plan == "free"
        assert user.premium_until is None

    text = update.message.reply_text.call_args[0][0]
    assert "Revoked" in text
    await engine.dispose()


# ── /broadcast ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_broadcast_sends_to_all_users(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=10, lang="vi", plan="free"))
        s.add(User(tg_id=11, lang="en", plan="free"))
        await s.commit()

    from bot.handlers.admin import admin_broadcast

    # status_msg returned by reply_text so we can edit it later
    status_msg = MagicMock()
    status_msg.edit_text = AsyncMock()

    update = _make_update(tg_id=999)
    update.message.reply_text = AsyncMock(return_value=status_msg)

    ctx = _make_context(args=["Hello", "traders!"])
    await admin_broadcast(update, ctx)

    assert ctx.bot.send_message.call_count == 2
    call_ids = {c.kwargs.get("chat_id") or c.args[0] for c in ctx.bot.send_message.call_args_list}
    assert {10, 11} == call_ids
    status_msg.edit_text.assert_called_once()
    assert "2 sent" in status_msg.edit_text.call_args[0][0]
    await engine.dispose()


@pytest.mark.asyncio
async def test_broadcast_no_message(monkeypatch):
    monkeypatch.setattr("bot.handlers.admin.settings.owner_tg_id", 999)
    from bot.handlers.admin import admin_broadcast
    update = _make_update(tg_id=999)
    await admin_broadcast(update, _make_context(args=[]))
    text = update.message.reply_text.call_args[0][0]
    assert "Usage" in text
