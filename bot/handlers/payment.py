"""Telegram Stars payment handler.

Flow:
 1. /upgrade or menu:upgrade → show plan buttons
 2. User picks plan → bot sendInvoice with currency="XTR"
 3. Telegram fires pre_checkout_query → bot auto-answers ok
 4. Telegram fires successful_payment → bot activates premium + records payment
"""
import json
import logging

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from bot.config import settings
from bot.db import session_scope
from bot.i18n import t
from bot.models import Payment
from bot.services.subscription import activate_premium
from bot.services.users import get_lang

logger = logging.getLogger(__name__)

PAYLOAD_MONTHLY = "premium_monthly"
PAYLOAD_YEARLY = "premium_yearly"


def _plan_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            t("upgrade_monthly", lang, stars=settings.premium_monthly_stars),
            callback_data=f"pay:{PAYLOAD_MONTHLY}",
        )],
        [InlineKeyboardButton(
            t("upgrade_yearly", lang, stars=settings.premium_yearly_stars),
            callback_data=f"pay:{PAYLOAD_YEARLY}",
        )],
    ])


async def upgrade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    msg = update.effective_message or update.callback_query.message
    await msg.reply_text(
        t("upgrade_intro", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_plan_keyboard(lang),
    )


async def on_plan_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    lang = await get_lang(update.effective_user.id)
    _, payload = q.data.split(":", 1)

    if payload == PAYLOAD_MONTHLY:
        title = t("invoice_title_monthly", lang)
        amount = settings.premium_monthly_stars
    elif payload == PAYLOAD_YEARLY:
        title = t("invoice_title_yearly", lang)
        amount = settings.premium_yearly_stars
    else:
        return

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=title,
        description=t("invoice_desc", lang),
        payload=payload,
        provider_token=settings.stars_provider_token,  # empty string for XTR
        currency="XTR",
        prices=[LabeledPrice(label=title, amount=amount)],
    )


async def on_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Auto-approve every pre-checkout. Telegram verifies funds before firing successful_payment."""
    await update.pre_checkout_query.answer(ok=True)


async def on_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sp = update.message.successful_payment
    tg_id = update.effective_user.id
    payload = sp.invoice_payload
    days = 30 if payload == PAYLOAD_MONTHLY else 365 if payload == PAYLOAD_YEARLY else 30
    tx_id = sp.telegram_payment_charge_id or sp.provider_payment_charge_id

    async with session_scope() as s:
        stmt_values = {
            "user_id": tg_id,
            "provider": "telegram_stars",
            "amount": sp.total_amount,
            "currency": sp.currency,
            "tx_id": tx_id,
            "status": "success",
            "raw_payload": json.dumps(sp.to_dict()),
        }
        # Upsert on tx_id; rowcount==1 means new payment, ==0 means Telegram retry.
        # Only call activate_premium on new inserts to stay idempotent.
        if settings.database_url.startswith("postgresql"):
            stmt = pg_insert(Payment).values(**stmt_values).on_conflict_do_nothing(index_elements=["tx_id"])
        else:
            stmt = sqlite_insert(Payment).values(**stmt_values).on_conflict_do_nothing(index_elements=["tx_id"])
        result = await s.execute(stmt)
        inserted = result.rowcount == 1

    if not inserted:
        logger.info("Duplicate payment webhook for tx_id=%s, skipping activation", tx_id)
        return

    until = await activate_premium(tg_id, days)
    lang = await get_lang(tg_id)
    await update.message.reply_text(
        t("payment_success", lang, until=until.strftime("%Y-%m-%d")),
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info("Premium activated for %s via %s until %s", tg_id, payload, until)


def register(app) -> None:
    app.add_handler(CommandHandler("upgrade", upgrade_cmd))
    app.add_handler(CallbackQueryHandler(on_plan_click, pattern=r"^pay:"))
    app.add_handler(PreCheckoutQueryHandler(on_precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, on_successful_payment))
