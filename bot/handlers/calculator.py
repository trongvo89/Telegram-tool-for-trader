from decimal import Decimal

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.i18n import t
from bot.services.users import get_lang
from bot.utils.parse import fmt, parse_number

CALC_BALANCE, CALC_RISK, CALC_ENTRY, CALC_SL = range(4)


async def calc_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    lang = await get_lang(update.effective_user.id)
    context.user_data["calc_lang"] = lang
    await update.effective_message.reply_text(t("calc_intro", lang), parse_mode=ParseMode.MARKDOWN)
    return CALC_BALANCE


async def calc_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("calc_lang", "vi")
    num = parse_number(update.message.text)
    if not num or num <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return CALC_BALANCE
    context.user_data["calc_balance"] = num
    await update.message.reply_text(t("calc_risk", lang))
    return CALC_RISK


async def calc_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("calc_lang", "vi")
    num = parse_number(update.message.text)
    if not num or num <= 0 or num > 100:
        await update.message.reply_text(t("invalid_number", lang))
        return CALC_RISK
    context.user_data["calc_risk"] = num
    await update.message.reply_text(t("calc_entry", lang))
    return CALC_ENTRY


async def calc_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("calc_lang", "vi")
    num = parse_number(update.message.text)
    if not num or num <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return CALC_ENTRY
    context.user_data["calc_entry"] = num
    await update.message.reply_text(t("calc_sl", lang))
    return CALC_SL


async def calc_sl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("calc_lang", "vi")
    sl = parse_number(update.message.text)
    if not sl or sl <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return CALC_SL

    balance: Decimal = context.user_data["calc_balance"]
    risk_pct: Decimal = context.user_data["calc_risk"]
    entry: Decimal = context.user_data["calc_entry"]

    if sl == entry:
        await update.message.reply_text(t("calc_sl_equal_entry", lang))
        return ConversationHandler.END

    risk_amt = (balance * risk_pct / Decimal(100)).quantize(Decimal("0.01"))
    sl_dist = abs(entry - sl)
    sl_pct = (sl_dist / entry * Decimal(100)).quantize(Decimal("0.01"))
    size = (risk_amt / sl_dist).quantize(Decimal("0.00000001"))
    notional = (size * entry).quantize(Decimal("0.01"))

    await update.message.reply_text(
        t(
            "calc_result",
            lang,
            risk_amt=fmt(risk_amt),
            sl_dist=fmt(sl_dist, 4),
            sl_pct=fmt(sl_pct),
            size=fmt(size, 8),
            notional=fmt(notional),
        ),
        parse_mode=ParseMode.MARKDOWN,
    )
    context.user_data.clear()
    return ConversationHandler.END


async def calc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(update.effective_user.id)
    await update.message.reply_text(t("cancelled", lang))
    context.user_data.clear()
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("calc", calc_start),
            CallbackQueryHandler(calc_start, pattern=r"^menu:calc$"),
        ],
        states={
            CALC_BALANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_balance)],
            CALC_RISK: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_risk)],
            CALC_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_entry)],
            CALC_SL: [MessageHandler(filters.TEXT & ~filters.COMMAND, calc_sl)],
        },
        fallbacks=[CommandHandler("cancel", calc_cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
