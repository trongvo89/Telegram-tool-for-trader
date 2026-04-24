"""Alert matching engine. Runs on APScheduler.

Two tick rates:
 - free: scan every 60s
 - premium: scan every 5s
Uses in-memory price cache from price_feed.
"""
import logging
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode

from bot.db import session_scope
from bot.i18n import t
from bot.models import Alert, User
from bot.services import price_feed, symbols

logger = logging.getLogger(__name__)

_OP = {"above": ">", "below": "<"}


def _is_triggered(cond: str, price: Decimal, target: Decimal) -> bool:
    if cond == "above":
        return price >= target
    if cond == "below":
        return price <= target
    return False


async def scan_and_fire(bot: Bot, tier: str) -> None:
    """Scan active alerts for a given plan tier and fire any that match."""
    async with session_scope() as s:
        res = await s.execute(
            select(Alert, User)
            .join(User, User.tg_id == Alert.user_id)
            .where(Alert.active.is_(True), User.plan == tier)
        )
        rows = list(res.all())

    market_closed = price_feed.is_market_closed_commodities()
    now = datetime.now(UTC)
    to_fire: list[tuple[Alert, User, Decimal]] = []

    for alert, user in rows:
        if alert.asset_class in ("metal", "energy") and market_closed:
            continue
        price = await price_feed.get_price(alert.symbol)
        if price is None:
            continue
        if _is_triggered(alert.condition, price, alert.target):
            to_fire.append((alert, user, price))

    if not to_fire:
        return

    async with session_scope() as s:
        for alert, user, price in to_fire:
            fresh = await s.get(Alert, alert.id)
            if not fresh or not fresh.active:
                continue
            fresh.active = False
            fresh.triggered_at = now

            info = symbols.get_info(fresh.symbol)
            try:
                await bot.send_message(
                    chat_id=user.tg_id,
                    text=t(
                        "alert_triggered",
                        user.lang,
                        id=fresh.id,
                        symbol=fresh.symbol,
                        op=_OP.get(fresh.condition, fresh.condition),
                        target=f"{fresh.target:.{info.decimals}f}",
                        price=f"{price:.{info.decimals}f}",
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception as exc:
                logger.warning("Failed to send alert to %s: %s", user.tg_id, exc)


async def scan_free(context) -> None:
    await scan_and_fire(context.bot, tier="free")


async def scan_premium(context) -> None:
    await scan_and_fire(context.bot, tier="premium")
