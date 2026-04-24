"""Tests for journal auto TP/SL close logic."""
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import bot.db as db_mod
from bot.db import Base
from bot.models import Trade, User
from bot.services.journal_auto_close import _hits_sl, _hits_tp, scan_and_close


async def _fresh_db(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(db_mod, "engine", engine)
    monkeypatch.setattr(db_mod, "SessionLocal", Session)
    return engine, Session


# ── Pure logic tests ────────────────────────────────────────────────────────

def test_hits_tp_long():
    assert _hits_tp("long", Decimal("101"), Decimal("100")) is True
    assert _hits_tp("long", Decimal("100"), Decimal("100")) is True
    assert _hits_tp("long", Decimal("99"), Decimal("100")) is False


def test_hits_tp_short():
    assert _hits_tp("short", Decimal("99"), Decimal("100")) is True
    assert _hits_tp("short", Decimal("100"), Decimal("100")) is True
    assert _hits_tp("short", Decimal("101"), Decimal("100")) is False


def test_hits_sl_long():
    assert _hits_sl("long", Decimal("99"), Decimal("100")) is True
    assert _hits_sl("long", Decimal("100"), Decimal("100")) is True
    assert _hits_sl("long", Decimal("101"), Decimal("100")) is False


def test_hits_sl_short():
    assert _hits_sl("short", Decimal("101"), Decimal("100")) is True
    assert _hits_sl("short", Decimal("100"), Decimal("100")) is True
    assert _hits_sl("short", Decimal("99"), Decimal("100")) is False


# ── Integration tests ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auto_close_tp_long(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=1, lang="en", plan="free"))
        s.add(Trade(
            user_id=1, asset_class="crypto", symbol="BTCUSDT",
            side="long", entry=Decimal("60000"), size=Decimal("1"),
            tp=Decimal("65000"), sl=Decimal("58000"), status="open",
        ))
        await s.commit()

    bot_mock = MagicMock()
    bot_mock.send_message = AsyncMock()

    with patch("bot.services.journal_auto_close.price_feed.get_price", return_value=Decimal("65000")):
        await scan_and_close(bot_mock, tier="free")

    bot_mock.send_message.assert_called_once()
    call_kwargs = bot_mock.send_message.call_args
    assert "Take Profit" in call_kwargs[1]["text"] or "Take Profit" in str(call_kwargs)

    async with Session() as s:
        from sqlalchemy import select
        res = await s.execute(select(Trade).where(Trade.user_id == 1))
        trade = res.scalar_one()
        assert trade.status == "closed"
        assert trade.exit == Decimal("65000")
        assert trade.pnl == Decimal("5000")

    await engine.dispose()


@pytest.mark.asyncio
async def test_auto_close_sl_short(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=2, lang="vi", plan="premium"))
        s.add(Trade(
            user_id=2, asset_class="crypto", symbol="ETHUSDT",
            side="short", entry=Decimal("3000"), size=Decimal("2"),
            tp=Decimal("2500"), sl=Decimal("3200"), status="open",
        ))
        await s.commit()

    bot_mock = MagicMock()
    bot_mock.send_message = AsyncMock()

    with patch("bot.services.journal_auto_close.price_feed.get_price", return_value=Decimal("3200")):
        await scan_and_close(bot_mock, tier="premium")

    bot_mock.send_message.assert_called_once()
    msg_text = bot_mock.send_message.call_args[1]["text"]
    assert "SL" in msg_text or "Cắt" in msg_text

    async with Session() as s:
        from sqlalchemy import select
        res = await s.execute(select(Trade).where(Trade.user_id == 2))
        trade = res.scalar_one()
        assert trade.status == "closed"
        assert trade.pnl == Decimal("-400")  # short: (3000-3200)*2 = -400

    await engine.dispose()


@pytest.mark.asyncio
async def test_no_close_when_price_not_hit(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=3, lang="en", plan="free"))
        s.add(Trade(
            user_id=3, asset_class="crypto", symbol="BTCUSDT",
            side="long", entry=Decimal("60000"), size=Decimal("1"),
            tp=Decimal("65000"), sl=Decimal("58000"), status="open",
        ))
        await s.commit()

    bot_mock = MagicMock()
    bot_mock.send_message = AsyncMock()

    with patch("bot.services.journal_auto_close.price_feed.get_price", return_value=Decimal("62000")):
        await scan_and_close(bot_mock, tier="free")

    bot_mock.send_message.assert_not_called()

    async with Session() as s:
        from sqlalchemy import select
        res = await s.execute(select(Trade).where(Trade.user_id == 3))
        trade = res.scalar_one()
        assert trade.status == "open"

    await engine.dispose()


@pytest.mark.asyncio
async def test_skip_trade_without_tp_sl(monkeypatch):
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=4, lang="en", plan="free"))
        s.add(Trade(
            user_id=4, asset_class="crypto", symbol="BTCUSDT",
            side="long", entry=Decimal("60000"), size=Decimal("1"),
            tp=None, sl=None, status="open",
        ))
        await s.commit()

    bot_mock = MagicMock()
    bot_mock.send_message = AsyncMock()

    with patch("bot.services.journal_auto_close.price_feed.get_price", return_value=Decimal("99999")):
        await scan_and_close(bot_mock, tier="free")

    bot_mock.send_message.assert_not_called()
    await engine.dispose()


@pytest.mark.asyncio
async def test_no_double_close(monkeypatch):
    """Race condition: trade already closed between snapshot and fire."""
    engine, Session = await _fresh_db(monkeypatch)
    async with Session() as s:
        s.add(User(tg_id=5, lang="en", plan="free"))
        # Trade already closed
        s.add(Trade(
            user_id=5, asset_class="crypto", symbol="BTCUSDT",
            side="long", entry=Decimal("60000"), size=Decimal("1"),
            tp=Decimal("65000"), sl=Decimal("58000"), status="closed",
        ))
        await s.commit()

    bot_mock = MagicMock()
    bot_mock.send_message = AsyncMock()

    with patch("bot.services.journal_auto_close.price_feed.get_price", return_value=Decimal("65000")):
        await scan_and_close(bot_mock, tier="free")

    bot_mock.send_message.assert_not_called()
    await engine.dispose()
