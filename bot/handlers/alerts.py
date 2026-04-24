from decimal import Decimal

from sqlalchemy import select
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
from bot.models import Alert
from bot.services import price_feed, symbols
from bot.services.users import get_lang, is_premium
from bot.utils.parse import fmt, parse_number

FREE_ALERT_LIMIT = 3

A_ASSET, A_SYMBOL, A_COND, A_TARGET = range(4)


def _op_str(cond: str) -> str:
    return {"above": ">", "below": "<", "pct_change": "±%"}.get(cond, cond)


def _asset_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("asset_crypto", lang), callback_data="alert_asset:crypto")],
        [
            InlineKeyboardButton(t("asset_metal_gold", lang), callback_data="alert_asset:XAUUSD"),
            InlineKeyboardButton(t("asset_metal_silver", lang), callback_data="alert_asset:XAGUSD"),
        ],
        [
            InlineKeyboardButton(t("asset_energy_wti", lang), callback_data="alert_asset:WTI"),
            InlineKeyboardButton(t("asset_energy_brent", lang), callback_data="alert_asset:BRENT"),
        ],
    ])


def _cond_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("alert_cond_above", lang), callback_data="alert_cond:above"),
            InlineKeyboardButton(t("alert_cond_below", lang), callback_data="alert_cond:below"),
        ],
        [InlineKeyboardButton(t("alert_cond_pct_change", lang), callback_data="alert_cond:pct_change")],
    ])


async def alert_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(update.effective_user.id)
    context.user_data["alert_lang"] = lang
    msg = update.effective_message or update.callback_query.message
    await msg.reply_text(
        t("alert_pick_asset", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=_asset_keyboard(lang)
    )
    return A_ASSET


async def on_asset_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get("alert_lang", await get_lang(update.effective_user.id))
    _, value = q.data.split(":", 1)
    if value == "crypto":
        context.user_data["alert_asset_class"] = "crypto"
        await q.edit_message_text(t("alert_pick_symbol_crypto", lang), parse_mode=ParseMode.MARKDOWN)
        return A_SYMBOL
    # commodity short-cut: value is the canonical symbol
    info = symbols.get_info(value)
    price = await price_feed.get_price(value)
    if price is None:
        # Cache cold — try one immediate refresh before giving up
        await price_feed.refresh_commodity_cache()
        price = await price_feed.get_price(value)
    if price is None:
        await q.edit_message_text(t("price_unavailable", lang))
        return ConversationHandler.END
    context.user_data.update({
        "alert_asset_class": info.asset_class,
        "alert_symbol": value,
        "alert_decimals": info.decimals,
        "alert_current_price": price,
    })
    await q.edit_message_text(
        t("alert_pick_condition", lang, symbol=value, price=fmt(price, info.decimals)),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_cond_keyboard(lang),
    )
    return A_COND


async def on_symbol_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("alert_lang", "vi")
    raw = update.message.text
    symbol = symbols.normalize_crypto_symbol(raw)
    price = await price_feed.get_price(symbol)
    if price is None:
        # WS may not be warm yet — try Binance REST as one-shot fallback
        price = await price_feed.fetch_binance_spot_once(symbol)
        if price is not None:
            await price_feed.update_cache(symbol, price)
    if price is None:
        await update.message.reply_text(t("alert_symbol_invalid", lang))
        return A_SYMBOL
    info = symbols.get_info(symbol)
    context.user_data.update({
        "alert_symbol": symbol,
        "alert_decimals": info.decimals,
        "alert_current_price": price,
    })
    await update.message.reply_text(
        t("alert_pick_condition", lang, symbol=symbol, price=fmt(price, info.decimals)),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_cond_keyboard(lang),
    )
    return A_COND


async def on_cond_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()
    lang = context.user_data.get("alert_lang", "vi")
    _, cond = q.data.split(":", 1)
    context.user_data["alert_cond"] = cond
    key = "alert_target_prompt_pct" if cond == "pct_change" else "alert_target_prompt"
    await q.edit_message_text(t(key, lang))
    return A_TARGET


async def on_target(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("alert_lang", "vi")
    tg_id = update.effective_user.id
    target = parse_number(update.message.text)
    if not target or target <= 0:
        await update.message.reply_text(t("invalid_number", lang))
        return A_TARGET

    # quota check
    premium = await is_premium(tg_id)
    if not premium:
        async with session_scope() as s:
            res = await s.execute(
                select(Alert).where(Alert.user_id == tg_id, Alert.active.is_(True))
            )
            count = len(list(res.scalars().all()))
        if count >= FREE_ALERT_LIMIT:
            await update.message.reply_text(
                t("alert_limit_free", lang, limit=FREE_ALERT_LIMIT),
                parse_mode=ParseMode.MARKDOWN,
            )
            context.user_data.clear()
            return ConversationHandler.END

    symbol = context.user_data["alert_symbol"]
    asset_class = context.user_data["alert_asset_class"]
    cond = context.user_data["alert_cond"]
    decimals = context.user_data.get("alert_decimals", 2)
    reference = context.user_data.get("alert_current_price") if cond == "pct_change" else None

    async with session_scope() as s:
        a = Alert(
            user_id=tg_id,
            asset_class=asset_class,
            symbol=symbol,
            condition=cond,
            target=target,
            reference=reference,
            active=True,
        )
        s.add(a)
        await s.flush()
        alert_id = a.id

    price = await price_feed.get_price(symbol) or Decimal(0)
    if cond == "pct_change" and reference:
        reply_text = t(
            "alert_created_pct",
            lang,
            id=alert_id,
            symbol=symbol,
            target=f"{target:.2f}",
            reference=fmt(reference, decimals),
        )
    else:
        reply_text = t(
            "alert_created",
            lang,
            id=alert_id,
            symbol=symbol,
            op=_op_str(cond),
            target=fmt(target, decimals),
            price=fmt(price, decimals),
        )
    await update.message.reply_text(reply_text, parse_mode=ParseMode.MARKDOWN)
    context.user_data.clear()
    return ConversationHandler.END


async def list_alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    async with session_scope() as s:
        res = await s.execute(
            select(Alert).where(Alert.user_id == tg_id, Alert.active.is_(True)).order_by(Alert.id)
        )
        rows = list(res.scalars().all())
    msg = update.effective_message or update.callback_query.message
    if not rows:
        await msg.reply_text(t("alert_list_empty", lang))
        return
    lines = [t("alert_list_header", lang)]
    for a in rows:
        decimals = symbols.get_info(a.symbol).decimals
        price = await price_feed.get_price(a.symbol) or Decimal(0)
        if a.condition == "pct_change" and a.reference:
            lines.append(t(
                "alert_list_item_pct",
                lang,
                id=a.id,
                symbol=a.symbol,
                target=f"{a.target:.2f}",
                reference=fmt(a.reference, decimals),
                price=fmt(price, decimals),
            ))
        else:
            lines.append(t(
                "alert_list_item",
                lang,
                id=a.id,
                symbol=a.symbol,
                op=_op_str(a.condition),
                target=fmt(a.target, decimals),
                price=fmt(price, decimals),
            ))
    await msg.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)


async def del_alert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_id = update.effective_user.id
    lang = await get_lang(tg_id)
    if not context.args:
        await update.message.reply_text(t("alert_not_found", lang))
        return
    try:
        alert_id = int(context.args[0].lstrip("#"))
    except ValueError:
        await update.message.reply_text(t("alert_not_found", lang))
        return
    async with session_scope() as s:
        a = await s.get(Alert, alert_id)
        if not a or a.user_id != tg_id:
            await update.message.reply_text(t("alert_not_found", lang))
            return
        await s.delete(a)
    await update.message.reply_text(t("alert_deleted", lang, id=alert_id), parse_mode=ParseMode.MARKDOWN)


async def alert_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = await get_lang(update.effective_user.id)
    await update.message.reply_text(t("cancelled", lang))
    context.user_data.clear()
    return ConversationHandler.END


def register(app) -> None:
    conv = ConversationHandler(
        entry_points=[CommandHandler("alert", alert_start)],
        states={
            A_ASSET: [CallbackQueryHandler(on_asset_pick, pattern=r"^alert_asset:")],
            A_SYMBOL: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_symbol_text)],
            A_COND: [CallbackQueryHandler(on_cond_pick, pattern=r"^alert_cond:")],
            A_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_target)],
        },
        fallbacks=[CommandHandler("cancel", alert_cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("alerts", list_alerts_cmd))
    app.add_handler(CommandHandler("delalert", del_alert_cmd))
