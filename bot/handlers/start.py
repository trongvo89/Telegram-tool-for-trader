from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.i18n import t
from bot.services.users import get_lang, get_or_create_user, set_lang


def _language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang:vi"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang:en"),
        ]
    ])


def _main_menu(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(t("menu_alerts", lang), callback_data="menu:alerts"),
            InlineKeyboardButton(t("menu_journal", lang), callback_data="menu:journal"),
        ],
        [
            InlineKeyboardButton(t("menu_calc", lang), callback_data="menu:calc"),
            InlineKeyboardButton(t("menu_upgrade", lang), callback_data="menu:upgrade"),
        ],
        [InlineKeyboardButton(t("menu_lang", lang), callback_data="menu:lang")],
    ])


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tg_user = update.effective_user
    user, created = await get_or_create_user(tg_user.id, tg_user.username)
    if created:
        await update.effective_message.reply_text(
            t("pick_language"), reply_markup=_language_keyboard()
        )
        return
    await update.effective_message.reply_text(
        t("welcome", user.lang), parse_mode=ParseMode.MARKDOWN, reply_markup=_main_menu(user.lang)
    )


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    await update.effective_message.reply_text(
        t("lang_current", lang, name=t("lang_name", lang)),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_language_keyboard(),
    )


async def on_language_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    _, new_lang = q.data.split(":", 1)
    if new_lang not in ("vi", "en"):
        return
    await set_lang(update.effective_user.id, new_lang)
    await q.edit_message_text(t("language_set", new_lang))
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=t("welcome", new_lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_main_menu(new_lang),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = await get_lang(update.effective_user.id)
    await update.effective_message.reply_text(t("help", lang), parse_mode=ParseMode.MARKDOWN)


async def on_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route non-wizard menu clicks. Wizard entries (calc, alert, log) are
    handled by their own ConversationHandler entry_points."""
    from bot.handlers import alerts as alerts_h
    from bot.handlers import journal as journal_h
    from bot.handlers import payment as pay_h

    q = update.callback_query
    await q.answer()
    _, choice = q.data.split(":", 1)
    if choice == "alerts":
        await alerts_h.list_alerts_cmd(update, context)
    elif choice == "journal":
        await journal_h.journal_cmd(update, context)
    elif choice == "upgrade":
        await pay_h.upgrade_cmd(update, context)
    elif choice == "lang":
        await lang_cmd(update, context)


def register(app) -> None:
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CallbackQueryHandler(on_language_choice, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(on_menu, pattern=r"^menu:(alerts|journal|upgrade|lang)$"))
