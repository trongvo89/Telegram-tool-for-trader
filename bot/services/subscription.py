"""Subscription lifecycle: activate, expire, renewal reminders."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from telegram import Bot
from telegram.constants import ParseMode

from bot.db import session_scope
from bot.i18n import t
from bot.models import User

logger = logging.getLogger(__name__)

REMINDER_DAYS_BEFORE = 3


async def activate_premium(tg_id: int, days: int) -> datetime:
    """Extend or start premium. Returns new expiry."""
    now = datetime.now(timezone.utc)
    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if not user:
            user = User(tg_id=tg_id, lang="vi")
            s.add(user)
        base = user.premium_until if user.premium_until and user.premium_until > now else now
        user.premium_until = base + timedelta(days=days)
        user.plan = "premium"
        user.renewal_reminded = False
        return user.premium_until


async def expire_and_remind(bot: Bot) -> None:
    """Daily sweep: downgrade expired users, DM reminders to near-expiry users."""
    now = datetime.now(timezone.utc)
    remind_before = now + timedelta(days=REMINDER_DAYS_BEFORE)

    async with session_scope() as s:
        res = await s.execute(select(User).where(User.plan == "premium"))
        users = list(res.scalars().all())

        for user in users:
            if user.premium_until and user.premium_until < now:
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
            if (
                user.premium_until
                and not user.renewal_reminded
                and user.premium_until <= remind_before
            ):
                days_left = (user.premium_until - now).days + 1
                user.renewal_reminded = True
                try:
                    await bot.send_message(
                        chat_id=user.tg_id,
                        text=t(
                            "payment_renew_reminder",
                            user.lang,
                            days=days_left,
                            until=user.premium_until.strftime("%Y-%m-%d"),
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception as exc:
                    logger.warning("Reminder DM failed %s: %s", user.tg_id, exc)
