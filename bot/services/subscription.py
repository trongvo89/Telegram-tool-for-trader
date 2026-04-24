"""Subscription lifecycle: activate, expire, renewal reminders."""
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode

from bot.db import session_scope
from bot.i18n import t
from bot.models import User

logger = logging.getLogger(__name__)

REMINDER_DAYS_BEFORE = 3


def _aware(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is tz-aware (SQLite strips tzinfo on read)."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


async def activate_premium(tg_id: int, days: int) -> datetime:
    """Extend or start premium. Returns new expiry."""
    now = datetime.now(UTC)
    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if not user:
            user = User(tg_id=tg_id, lang="vi")
            s.add(user)
        current = _aware(user.premium_until)
        base = current if current and current > now else now
        user.premium_until = base + timedelta(days=days)
        user.plan = "premium"
        user.renewal_reminded = False
        return user.premium_until


async def expire_and_remind(bot: Bot) -> None:
    """Daily sweep: downgrade expired users, DM reminders to near-expiry users."""
    now = datetime.now(UTC)
    remind_before = now + timedelta(days=REMINDER_DAYS_BEFORE)

    async with session_scope() as s:
        res = await s.execute(select(User).where(User.plan == "premium"))
        users = list(res.scalars().all())

        for user in users:
            expiry = _aware(user.premium_until)
            if expiry and expiry < now:
                user.plan = "free"
                user.renewal_reminded = False
                try:
                    await bot.send_message(
                        chat_id=user.tg_id,
                        text=t("payment_expired", user.lang),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception as exc:
                    logger.warning("Expire DM failed %s: %s", user.tg_id, exc)
                continue
            if expiry and not user.renewal_reminded and expiry <= remind_before:
                days_left = (expiry - now).days + 1
                user.renewal_reminded = True
                try:
                    await bot.send_message(
                        chat_id=user.tg_id,
                        text=t(
                            "payment_renew_reminder",
                            user.lang,
                            days=days_left,
                            until=expiry.strftime("%Y-%m-%d"),
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception as exc:
                    logger.warning("Reminder DM failed %s: %s", user.tg_id, exc)
