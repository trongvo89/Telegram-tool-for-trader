"""Auto-close open journal trades when price hits TP or SL.

Runs on the same tick rates as alert_engine:
 - free:    every 60s
 - premium: every 5s
Only trades that have tp or sl set are checked.
"""
import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode

from bot.db import session_scope
from bot.i18n import t
from bot.models import Trade, User
from bot.services import price_feed, symbols
from bot.services.journal_stats import pnl_of
from bot.utils.parse import fmt

logger = logging.getLogger(__name__)


def _hits_tp(side: str, price: Decimal, tp: Decimal) -> bool:
    return price >= tp if side == "long" else price <= tp


def _hits_sl(side: str, price: Decimal, sl: Decimal) -> bool:
    return price <= sl if side == "long" else price >= sl


async def scan_and_close(bot: Bot, tier: str) -> None:
    """Scan open trades for the given tier and auto-close any that hit TP or SL."""
    async with session_scope() as s:
        res = await s.execute(
            select(Trade, User)
            .join(User, User.tg_id == Trade.user_id)
            .where(Trade.status == "open", User.plan == tier)
        )
        rows = list(res.all())

    now = datetime.now(UTC)
    to_close: list[tuple[Trade, User, Decimal, str]] = []

    for trade, user in rows:
        if trade.tp is None and trade.sl is None:
            continue
        price = await price_feed.get_price(trade.symbol)
        if price is None:
            continue
        reason: str | None = None
        if trade.tp and _hits_tp(trade.side, price, trade.tp):
            reason = "tp"
        elif trade.sl and _hits_sl(trade.side, price, trade.sl):
            reason = "sl"
        if reason:
            to_close.append((trade, user, price, reason))

    if not to_close:
        return

    async with session_scope() as s:
        for trade, user, price, reason in to_close:
            fresh = await s.get(Trade, trade.id)
            if not fresh or fresh.status != "open":
                continue
            fresh.exit = price
            fresh.pnl = pnl_of(fresh.side, fresh.entry, price, fresh.size)
            fresh.status = "closed"
            fresh.closed_at = now

            info = symbols.get_info(fresh.symbol)
            notional = fresh.entry * fresh.size
            pnl_pct = (
                (fresh.pnl / notional * Decimal(100)).quantize(Decimal("0.01"))
                if notional else Decimal(0)
            )
            try:
                await bot.send_message(
                    chat_id=user.tg_id,
                    text=t(
                        "trade_auto_closed",
                        user.lang,
                        id=fresh.id,
                        reason=t(f"close_reason_{reason}", user.lang),
                        symbol=fresh.symbol,
                        exit=fmt(price, info.decimals),
                        pnl=fmt(fresh.pnl, 2),
                        pnl_pct=fmt(pnl_pct, 2),
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as exc:
                logger.warning("Auto-close DM failed for user %s: %s", user.tg_id, exc)


async def scan_free(context) -> None:
    await scan_and_close(context.bot, tier="free")


async def scan_premium(context) -> None:
    await scan_and_close(context.bot, tier="premium")
