STRINGS: dict[str, str] = {
    # Generic
    "lang_name": "English",
    "back": "« Back",
    "cancel": "Cancel",
    "cancelled": "Cancelled.",
    "yes": "Yes",
    "no": "No",
    "invalid_number": "Invalid number. Try again?",
    "error_generic": "Something went wrong, please try again.",
    "price_unavailable": "⚠️ Couldn't fetch price right now. Please try again in a moment.",
    "premium_required": "This feature requires Premium. Use /upgrade to unlock.",

    # Asset classes
    "asset_crypto": "🪙 Crypto",
    "asset_metal_gold": "🥇 Gold (XAU)",
    "asset_metal_silver": "🥈 Silver (XAG)",
    "asset_energy_wti": "🛢 WTI Oil",
    "asset_energy_brent": "🛢 Brent Oil",

    # /start
    "pick_language": "🌐 Chọn ngôn ngữ / Choose language:",
    "language_set": "✅ Language set to English.",
    "welcome": (
        "👋 *Welcome to Trader Bot*\n\n"
        "This bot helps you:\n"
        "🔔 Price alerts for crypto / gold / silver / oil\n"
        "📊 Trading journal with win-rate stats\n"
        "🧮 Position size calculator based on risk\n\n"
        "Use the menu below to get started."
    ),
    "menu_alerts": "🔔 Alerts",
    "menu_journal": "📊 Journal",
    "menu_calc": "🧮 Calculator",
    "menu_upgrade": "💎 Upgrade",
    "menu_lang": "🌐 Language",

    # /help
    "help": (
        "*Available commands:*\n\n"
        "🔔 *Price alerts*\n"
        "/alert — Create a new alert\n"
        "/alerts — List active alerts\n"
        "/delalert <id> — Delete an alert\n\n"
        "📊 *Trading journal*\n"
        "/log — Log a new trade\n"
        "/close <id> <exit_price> — Close trade\n"
        "/journal — Recent trades\n"
        "/stats — Stats (win-rate, PnL, R:R)\n\n"
        "🧮 *Position calculator*\n"
        "/calc — Position size by risk\n\n"
        "💎 *Other*\n"
        "/upgrade — Upgrade to Premium\n"
        "/lang — Change language\n"
        "/help — Show this help"
    ),

    # Calculator
    "calc_intro": "🧮 *Position calculator*\n\nEnter account balance (USD):",
    "calc_risk": "Enter risk per trade (%, e.g. 1.5):",
    "calc_entry": "Enter entry price:",
    "calc_sl": "Enter stop-loss price:",
    "calc_result": (
        "*Result:*\n"
        "• Max risk: `{risk_amt}` USD\n"
        "• SL distance: `{sl_dist}` ({sl_pct}%)\n"
        "• Position size: `{size}` units\n"
        "• Notional: `{notional}` USD"
    ),
    "calc_sl_equal_entry": "❌ Stop-loss must differ from entry price.",

    # Alerts
    "alert_pick_asset": "🔔 *Create alert*\n\nPick asset class:",
    "alert_pick_symbol_crypto": "Enter symbol (e.g. `BTCUSDT`, `ETHUSDT`):",
    "alert_pick_condition": "Pick condition for *{symbol}* (current: `{price}`):",
    "alert_cond_above": "⬆️ Crosses above",
    "alert_cond_below": "⬇️ Crosses below",
    "alert_target_prompt": "Enter target price:",
    "alert_created": (
        "✅ Alert *#{id}* created\n"
        "{symbol} {op} `{target}`\n"
        "Current: `{price}`"
    ),
    "alert_symbol_invalid": "❌ No price found for this symbol. Please check.",
    "alert_list_empty": "No active alerts. Use /alert to create one.",
    "alert_list_header": "*Active alerts:*",
    "alert_list_item": "`#{id}` {symbol} {op} `{target}` (now: `{price}`)",
    "alert_deleted": "🗑 Deleted alert #{id}.",
    "alert_not_found": "Alert not found.",
    "alert_limit_free": "⚠️ Free plan limited to *{limit}* alerts. /upgrade for unlimited.",
    "alert_triggered": (
        "🚨 *Alert #{id} triggered!*\n"
        "{symbol} {op} `{target}`\n"
        "Current: `{price}`"
    ),
    "alert_market_closed": "🕑 Market is closed (weekend/holiday). Commodity alerts paused.",

    # Journal
    "log_pick_asset": "📊 *Log new trade*\n\nPick asset class:",
    "log_symbol": "Enter symbol (e.g. `BTCUSDT`, `XAUUSD`):",
    "log_side": "Pick side:",
    "log_side_long": "🟢 Long",
    "log_side_short": "🔴 Short",
    "log_entry": "Enter entry price:",
    "log_size": "Enter size (units):",
    "log_sl": "Enter stop-loss (or type `skip`):",
    "log_tp": "Enter take-profit (or type `skip`):",
    "log_note": "Short note (or type `skip`):",
    "log_saved": "✅ Trade *#{id}* saved: {side} {symbol} @ `{entry}`",
    "log_limit_free": "⚠️ Free plan limited to *{limit}* trades/month. /upgrade for unlimited.",

    "close_usage": "Usage: `/close <id> <exit_price>`",
    "close_not_found": "Trade not found or already closed.",
    "close_done": (
        "✅ Closed trade *#{id}*\n"
        "Exit: `{exit}`\n"
        "PnL: `{pnl}` USD ({pnl_pct}%)"
    ),

    "journal_empty": "No trades yet. Use /log to add one.",
    "journal_header": "*Recent trades:*",
    "journal_item_open": "`#{id}` {side} {symbol} @ `{entry}` — *open*",
    "journal_item_closed": "`#{id}` {side} {symbol} @ `{entry}` → `{exit}` — `{pnl}` USD",

    "stats_empty": "Not enough data. Close at least 1 trade to see stats.",
    "stats_body": (
        "📊 *Trading stats*\n\n"
        "Total closed: *{total}*\n"
        "Wins: *{wins}* • Losses: *{losses}*\n"
        "Win-rate: *{winrate}%*\n"
        "Total PnL: *{total_pnl}* USD\n"
        "Avg win: `{avg_win}` USD\n"
        "Avg loss: `{avg_loss}` USD\n"
        "Avg R:R: `{avg_rr}`"
    ),

    # Language
    "lang_current": "Current language: *{name}*\n\nPick a new one:",

    # Payment
    "upgrade_intro": (
        "💎 *Upgrade to Premium*\n\n"
        "Benefits:\n"
        "• Unlimited alerts (vs 3 on Free)\n"
        "• 5s price checks (vs 60s)\n"
        "• Unlimited trade journal\n"
        "• CSV export + weekly AI review\n\n"
        "Pick a plan:"
    ),
    "upgrade_monthly": "⭐ Monthly — {stars} Stars",
    "upgrade_yearly": "⭐ Yearly — {stars} Stars (save 33%)",
    "invoice_title_monthly": "Trader Bot Premium — 1 month",
    "invoice_title_yearly": "Trader Bot Premium — 1 year",
    "invoice_desc": "Unlock all premium features.",
    "payment_success": (
        "🎉 *Premium activated!*\n"
        "Expires: *{until}*\n\n"
        "Thanks for your support! Use /help to see new features."
    ),
    "payment_renew_reminder": (
        "⏰ Your Premium expires in *{days}* days "
        "({until}).\n\nUse /upgrade to renew."
    ),
    "payment_expired": (
        "ℹ️ Your Premium has expired. You are back on the Free plan.\n"
        "Use /upgrade to continue."
    ),
}
