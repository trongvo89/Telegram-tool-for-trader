from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.db import session_scope
from bot.i18n import t
from bot.models import Trade
from bot.services import symbols
from bot.services.journal_stats import compute_stats, pnl_of
from bot.services.users import get_lang, is_premium
from bot.utils.parse import fmt, parse_number

FREE_TRADE_LIMIT_PER_MONTH = 20

L_ASSET, L_SYMBOL, L_SIDE, L_ENTRY, L_SIZE, L_SL, L_TP, L_NOTE = range(8)


def _asset_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("asset_crypto", lang), callback_data="log_asset:crypto")],
        [
            InlineKeyboardButton(t("asset_metal_gold", lang), callback_data="log_asset:XAUUSD"),
            InlineKeyboardButton(t("asset_metal_silver", lang), callback_data="log_asset:XAGUSD"),
        ],
        [
            InlineKeyboardButton(t("asset_energy_wti", lang), callback_data="log_asset:WTI"),
            InlineKeyboardButton(t("asset_energy_brent", lang), callback_data="log_asset:BRENT"),
        ],
    ])


def _side_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("log_side_long", lang), callback_data="log_side:long"),
        InlineKeyboardButton(t("log_side_short", lang), callback_data="log_side:short"),
    ]])


async def _check_free_quota(tg_id: int) -> bool:
    """Return True if user is within free tier quota (or premium)."""
    if await is_premium(tg_id):
        return True
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    async with session_scope() as s:
        res = await s.execute(
            select(func.count())
            .select_from(Trade)
            .where(Trade.user_id == tg_id, Trade.opened_at >= month_start)
        )
        count = res.scalar_one()
    return count < FREE_TRADE_LIMIT_PER_MONTH


async def log_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(update.effective_user.id)
    context.user_data["log_lang"] = lang
    if not await _check_free_quota(update.effective_user.id):
        await update.effective_message.reply_text(
            t("log_limit_free", lang, limit=FREE_TRADE_LIMIT_PER_MONTH),
            parse_mode=ParseMode.MARKDOWN,
        )
        return ConversationHandler.END
    msg = update.effective_message or update.callback_query.message
    await msg.reply_text(t("log_pick_asset", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=_asset_keyboard(lang))
    return L_ASSET


async def on_log_asset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get("log_lang", "vi")
    _, value = q.data.split(":", 1)
    if value == "crypto":
        context.user_data["log_asset_class"] = "crypto"
        await q.edit_message_text(t("log_symbol", lang), parse_mode=ParseMode.MARKDOWN)
        return L_SYMBOL
    info = symbols.get_info(value)
    context.user_data.update({
        "log_asset_class": info.asset_class,
        "log_symbol": value,
    })
    await q.edit_message_text(t("log_side", lang), reply_markup=_side_keyboard(lang))
    return L_SIDE


async def on_log_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("log_lang", "vi")
    symbol = symbols.normalize_crypto_symbol(update.message.text)
    context.user_data["log_symbol"] = symbol
    await update.message.reply_text(t("log_side", lang), reply_markup=_side_keyboard(lang))
    return L_SIDE


async def on_log_side(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get("log_lang", "vi")
    _, side = q.data.split(":", 1)
    context.user_data["log_side"] = side
    await q.edit_message_text(t("log_entry", lang))
    return L_ENTRY


async def on_log_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("log_lang", "vi")
    num = parse_number(update.message.text)
    if not num or num <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return L_ENTRY
    context.user_data["log_entry"] = num
    await update.message.reply_text(t("log_size", lang))
    return L_SIZE


async def on_log_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("log_lang", "vi")
    num = parse_number(update.message.text)
    if not num or num <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return L_SIZE
    context.user_data["log_size"] = num
    await update.message.reply_text(t("log_sl", lang))
    return L_SL


async def on_log_sl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("log_lang", "vi")
    raw = update.message.text.strip().lower()
    if raw in ("skip", "-"):
        context.user_data["log_sl"] = None
    else:
        num = parse_number(raw)
        if not num or num <= 0:
            await update.message.reply_text(t("invalid_number", lang))
            return L_SL
        context.user_data["log_sl"] = num
    await update.message.reply_text(t("log_tp", lang))
    return L_TP


async def on_log_tp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("log_lang", "vi")
    raw = update.message.text.strip().lower()
    if raw in ("skip", "-"):
        context.user_data["log_tp"] = None
    else:
        num = parse_number(raw)
        if not num or num <= 0:
            await update.message.reply_text(t("invalid_number", lang))
            return L_TP
        context.user_data["log_tp"] = num
    await update.message.reply_text(t("log_note", lang))
    return L_NOTE


async def on_log_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("log_lang", "vi")
    raw = update.message.text.strip()
    note = None if raw.lower() in ("skip", "-") else raw[:500]

    tg_id = update.effective_user.id
    symbol = context.user_data["log_symbol"]
    decimals = symbols.get_info(symbol).decimals

    async with session_scope() as s:
        trade = Trade(
            user_id=tg_id,
            asset_class=context.user_data["log_asset_class"],
            symbol=symbol,
            side=context.user_data["log_side"],
            entry=context.user_data["log_entry"],
            size=context.user_data["log_size"],
            sl=context.user_data.get("log_sl"),
            tp=context.user_data.get("log_tp"),
            note=note,
            status="open",
        )
        s.add(trade)
        await s.flush()
        trade_id = trade.id

    side_label = t("log_side_long", lang) if context.user_data["log_side"] == "long" else t("log_side_short", lang)
    reply = t(
        "log_saved",
        lang,
        id=trade_id,
        side=side_label,
        symbol=symbol,
        entry=fmt(context.user_data["log_entry"], decimals),
    )
    if context.user_data.get("log_tp") or context.user_data.get("log_sl"):
        reply += "\n" + t("log_auto_close_note", lang)
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    context.user_data.clear()
    return ConversationHandler.END


async def close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    if len(context.args) < 2:
        await update.message.reply_text(t("close_usage", lang), parse_mode=ParseMode.MARKDOWN)
        return
    try:
        trade_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text(t("close_usage", lang), parse_mode=ParseMode.MARKDOWN)
        return
    exit_price = parse_number(context.args[1])
    if not exit_price or exit_price <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return

    async with session_scope() as s:
        trade = await s.get(Trade, trade_id)
        if not trade or trade.user_id != tg_id or trade.status != "open":
            await update.message.reply_text(t("close_not_found", lang))
            return
        trade.exit = exit_price
        trade.pnl = pnl_of(trade.side, trade.entry, exit_price, trade.size)
        trade.status = "closed"
        trade.closed_at = datetime.now(UTC)
        symbol = trade.symbol
        pnl = trade.pnl
        notional = trade.entry * trade.size

    pnl_pct = (pnl / notional * Decimal(100)).quantize(Decimal("0.01")) if notional else Decimal(0)
    await update.message.reply_text(
        t(
            "close_done",
            lang,
            id=trade_id,
            exit=fmt(exit_price, symbols.get_info(symbol).decimals),
            pnl=fmt(pnl, 2),
            pnl_pct=fmt(pnl_pct, 2),
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


async def journal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    async with session_scope() as s:
        res = await s.execute(
            select(Trade).where(Trade.user_id == tg_id).order_by(Trade.id.desc()).limit(10)
        )
        rows = list(res.scalars().all())
    msg = update.effective_message or update.callback_query.message
    if not rows:
        await msg.reply_text(t("journal_empty", lang))
        return
    lines = [t("journal_header", lang)]
    for r in rows:
        decimals = symbols.get_info(r.symbol).decimals
        side_label = t("log_side_long", lang) if r.side == "long" else t("log_side_short", lang)
        if r.status == "closed":
            lines.append(
                t(
                    "journal_item_closed",
                    lang,
                    id=r.id,
                    side=side_label,
                    symbol=r.symbol,
                    entry=fmt(r.entry, decimals),
                    exit=fmt(r.exit, decimals) if r.exit else "-",
                    pnl=fmt(r.pnl or Decimal(0), 2),
                )
            )
        else:
            lines.append(
                t(
                    "journal_item_open",
                    lang,
                    id=r.id,
                    side=side_label,
                    symbol=r.symbol,
                    entry=fmt(r.entry, decimals),
                )
            )
    await msg.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    stats = await compute_stats(tg_id)
    if not stats:
        await update.message.reply_text(t("stats_empty", lang))
        return
    await update.message.reply_text(
        t(
            "stats_body",
            lang,
            total=stats.total,
            wins=stats.wins,
            losses=stats.losses,
            winrate=stats.winrate,
            total_pnl=stats.total_pnl,
            avg_win=stats.avg_win,
            avg_loss=stats.avg_loss,
            avg_rr=stats.avg_rr,
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


async def log_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(update.effective_user.id)
    await update.message.reply_text(t("cancelled", lang))
    context.user_data.clear()
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CommandHandler("log", log_start)],
        states={
            L_ASSET: [CallbackQueryHandler(on_log_asset, pattern=r"^log_asset:")],
            L_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_log_symbol)],
            L_SIDE: [CallbackQueryHandler(on_log_side, pattern=r"^log_side:")],
            L_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_log_entry)],
            L_SIZE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_log_size)],
            L_SL: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_log_sl)],
            L_TP: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_log_tp)],
            L_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_log_note)],
        },
        fallbacks=[CommandHandler("cancel", log_cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("close", close_cmd))
    app.add_handler(CommandHandler("journal", journal_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
