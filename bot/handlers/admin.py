"""Admin commands — only accessible to the bot owner (OWNER_TG_ID).

All strings are intentionally hardcoded in English here; these commands are
never shown to regular users so i18n is not needed.
"""
import asyncio
import logging

from sqlalchemy import func, select
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import CommandHandler, ContextTypes

from bot.config import settings
from bot.db import session_scope
from bot.models import Alert, Payment, Trade, User
from bot.services.subscription import activate_premium

logger = logging.getLogger(__name__)


def _is_owner(tg_id: int) -> bool:
    return settings.owner_tg_id is not None and tg_id == settings.owner_tg_id


async def _guard(update: Update) -> bool:
    if not _is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ Unauthorized.")
        return False
    return True


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/admin — overview stats."""
    if not await _guard(update):
        return
    async with session_scope() as s:
        total_users = (await s.execute(select(func.count()).select_from(User))).scalar_one()
        premium_count = (await s.execute(
            select(func.count()).select_from(User).where(User.plan == "premium")
        )).scalar_one()
        active_alerts = (await s.execute(
            select(func.count()).select_from(Alert).where(Alert.active.is_(True))
        )).scalar_one()
        open_trades = (await s.execute(
            select(func.count()).select_from(Trade).where(Trade.status == "open")
        )).scalar_one()
        total_payments = (await s.execute(
            select(func.count()).select_from(Payment)
        )).scalar_one()
        total_stars = (await s.execute(
            select(func.sum(Payment.amount)).select_from(Payment)
        )).scalar_one() or 0

    await update.message.reply_text(
        "📊 *Bot Stats*\n\n"
        f"👤 Users: *{total_users}* ({premium_count} premium, {total_users - premium_count} free)\n"
        f"🔔 Active alerts: *{active_alerts}*\n"
        f"📋 Open trades: *{open_trades}*\n"
        f"💳 Payments: *{total_payments}* ({total_stars:.0f} Stars total)\n\n"
        "Commands: /userinfo /grant /revoke /broadcast",
        parse_mode=ParseMode.MARKDOWN,
    )


async def admin_userinfo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/userinfo <tg_id> — show details for a specific user."""
    if not await _guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/userinfo <tg_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        tg_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid tg_id — must be a number.")
        return

    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if not user:
            await update.message.reply_text(f"User `{tg_id}` not found.", parse_mode=ParseMode.MARKDOWN)
            return
        alert_count = (await s.execute(
            select(func.count()).select_from(Alert).where(Alert.user_id == tg_id)
        )).scalar_one()
        trade_count = (await s.execute(
            select(func.count()).select_from(Trade).where(Trade.user_id == tg_id)
        )).scalar_one()
        payment_count = (await s.execute(
            select(func.count()).select_from(Payment).where(Payment.user_id == tg_id)
        )).scalar_one()

    until = user.premium_until.strftime("%d/%m/%Y") if user.premium_until else "—"
    joined = user.created_at.strftime("%d/%m/%Y") if user.created_at else "—"
    await update.message.reply_text(
        f"👤 *User {tg_id}*\n"
        f"@{user.username or 'unknown'} · lang=`{user.lang}`\n\n"
        f"Plan: *{user.plan}*\n"
        f"Premium until: `{until}`\n"
        f"Joined: `{joined}`\n\n"
        f"🔔 Alerts: {alert_count} · 📋 Trades: {trade_count} · 💳 Payments: {payment_count}",
        parse_mode=ParseMode.MARKDOWN,
    )


async def admin_grant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/grant <tg_id> <days> — manually grant premium to a user."""
    if not await _guard(update):
        return
    if len(context.args or []) < 2:
        await update.message.reply_text(
            "Usage: `/grant <tg_id> <days>`", parse_mode=ParseMode.MARKDOWN
        )
        return
    try:
        tg_id, days = int(context.args[0]), int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid arguments — both must be integers.")
        return
    if days <= 0:
        await update.message.reply_text("Days must be positive.")
        return

    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if not user:
            await update.message.reply_text(f"User `{tg_id}` not found.", parse_mode=ParseMode.MARKDOWN)
            return

    expiry = await activate_premium(tg_id, days)
    await update.message.reply_text(
        f"✅ Granted *{days} days* premium to `{tg_id}`.\nExpires: `{expiry.strftime('%d/%m/%Y')}`",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("Admin granted %d days premium to user %d (expires %s)", days, tg_id, expiry.date())


async def admin_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/revoke <tg_id> — revoke premium immediately."""
    if not await _guard(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/revoke <tg_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    try:
        tg_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid tg_id.")
        return

    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if not user:
            await update.message.reply_text(f"User `{tg_id}` not found.", parse_mode=ParseMode.MARKDOWN)
            return
        user.plan = "free"
        user.premium_until = None
        user.renewal_reminded = False

    await update.message.reply_text(
        f"✅ Revoked premium from `{tg_id}`. User is now on Free plan.",
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("Admin revoked premium from user %d", tg_id)


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/broadcast <message> — send a DM to every registered user."""
    if not await _guard(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/broadcast <message>`\n\nSupports Markdown.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    text = " ".join(context.args)
    async with session_scope() as s:
        result = await s.execute(select(User.tg_id))
        tg_ids = list(result.scalars().all())

    status_msg = await update.message.reply_text(f"📡 Sending to {len(tg_ids)} users...")
    sent = failed = 0
    for tg_id in tg_ids:
        try:
            await context.bot.send_message(chat_id=tg_id, text=text, parse_mode=ParseMode.MARKDOWN)
            sent += 1
        except Exception as exc:
            logger.debug("Broadcast failed for %d: %s", tg_id, exc)
            failed += 1
        await asyncio.sleep(0.05)  # stay under Telegram 30 msg/s global limit

    await status_msg.edit_text(f"✅ Done: {sent} sent, {failed} failed.")


def register(app) -> None:
    app.add_handler(CommandHandler("admin", admin_stats))
    app.add_handler(CommandHandler("userinfo", admin_userinfo))
    app.add_handler(CommandHandler("grant", admin_grant))
    app.add_handler(CommandHandler("revoke", admin_revoke))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
