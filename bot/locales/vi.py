STRINGS: dict[str, str] = {
    # Generic
    "lang_name": "Tiếng Việt",
    "back": "« Quay lại",
    "cancel": "Huỷ",
    "cancelled": "Đã huỷ.",
    "yes": "Có",
    "no": "Không",
    "invalid_number": "Số không hợp lệ. Thử lại?",
    "error_generic": "Có lỗi xảy ra, thử lại sau.",
    "price_unavailable": "⚠️ Không lấy được giá lúc này. Thử lại sau vài giây.",
    "premium_required": "Tính năng này cần gói Premium. Dùng /upgrade để nâng cấp.",

    # Asset classes
    "asset_crypto": "🪙 Tiền số (Crypto)",
    "asset_metal_gold": "🥇 Vàng (XAU)",
    "asset_metal_silver": "🥈 Bạc (XAG)",
    "asset_energy_wti": "🛢 Dầu WTI",
    "asset_energy_brent": "🛢 Dầu Brent",

    # /start
    "pick_language": "🌐 Chọn ngôn ngữ / Choose language:",
    "language_set": "✅ Đã chọn Tiếng Việt.",
    "welcome": (
        "👋 *Chào mừng đến với Trader Bot*\n\n"
        "Bot giúp bạn:\n"
        "🔔 Cảnh báo giá crypto / vàng / bạc / dầu\n"
        "📊 Ghi nhật ký lệnh + thống kê win-rate\n"
        "🧮 Tính khối lượng vào lệnh theo rủi ro\n\n"
        "Dùng menu bên dưới để bắt đầu."
    ),
    "menu_alerts": "🔔 Cảnh báo giá",
    "menu_journal": "📊 Nhật ký",
    "menu_calc": "🧮 Máy tính lệnh",
    "menu_upgrade": "💎 Nâng cấp",
    "menu_lang": "🌐 Ngôn ngữ",

    # /help
    "help": (
        "*Các lệnh khả dụng:*\n\n"
        "🔔 *Cảnh báo giá*\n"
        "/alert — Tạo cảnh báo mới\n"
        "/alerts — Xem cảnh báo đang bật\n"
        "/delalert <id> — Xoá cảnh báo\n\n"
        "📊 *Nhật ký giao dịch*\n"
        "/log — Ghi lệnh mới\n"
        "/close <id> <giá_đóng> — Đóng lệnh\n"
        "/journal — Xem lệnh gần đây\n"
        "/stats — Thống kê (win-rate, PnL, R:R)\n\n"
        "🧮 *Máy tính khối lượng*\n"
        "/calc — Tính position size theo rủi ro\n\n"
        "💎 *Khác*\n"
        "/upgrade — Nâng cấp Premium\n"
        "/lang — Đổi ngôn ngữ\n"
        "/help — Xem trợ giúp"
    ),

    # Calculator
    "calc_intro": "🧮 *Máy tính khối lượng*\n\nNhập số dư tài khoản (USD):",
    "calc_risk": "Nhập % rủi ro mỗi lệnh (vd 1.5):",
    "calc_entry": "Nhập giá vào lệnh:",
    "calc_sl": "Nhập giá stop-loss:",
    "calc_result": (
        "*Kết quả:*\n"
        "• Rủi ro tối đa: `{risk_amt}` USD\n"
        "• Khoảng cách SL: `{sl_dist}` ({sl_pct}%)\n"
        "• Khối lượng: `{size}` đơn vị\n"
        "• Giá trị vị thế: `{notional}` USD"
    ),
    "calc_sl_equal_entry": "❌ Giá SL không được bằng giá vào lệnh.",

    # Alerts
    "alert_pick_asset": "🔔 *Tạo cảnh báo*\n\nChọn loại tài sản:",
    "alert_pick_symbol_crypto": "Nhập mã coin (vd `BTCUSDT`, `ETHUSDT`):",
    "alert_pick_condition": "Chọn điều kiện cho *{symbol}* (giá hiện tại: `{price}`):",
    "alert_cond_above": "⬆️ Vượt qua",
    "alert_cond_below": "⬇️ Xuống dưới",
    "alert_cond_pct_change": "📊 % Thay đổi",
    "alert_target_prompt": "Nhập giá mục tiêu:",
    "alert_target_prompt_pct": "Nhập % thay đổi (vd `3` = cảnh báo khi giá dịch chuyển ±3% từ mức hiện tại):",
    "alert_created": (
        "✅ Đã tạo cảnh báo *#{id}*\n"
        "{symbol} {op} `{target}`\n"
        "Giá hiện tại: `{price}`"
    ),
    "alert_created_pct": (
        "✅ Đã tạo cảnh báo *#{id}*\n"
        "{symbol} thay đổi ±`{target}`% từ `{reference}`"
    ),
    "alert_symbol_invalid": "❌ Không tìm thấy giá cho mã này. Kiểm tra lại.",
    "alert_list_empty": "Chưa có cảnh báo nào đang bật. Dùng /alert để tạo.",
    "alert_list_header": "*Cảnh báo đang bật:*",
    "alert_list_item": "`#{id}` {symbol} {op} `{target}` (hiện: `{price}`)",
    "alert_list_item_pct": "`#{id}` {symbol} ±`{target}`% từ `{reference}` (hiện: `{price}`)",
    "alert_deleted": "🗑 Đã xoá cảnh báo #{id}.",
    "alert_not_found": "Không tìm thấy cảnh báo.",
    "alert_limit_free": "⚠️ Gói Free giới hạn *{limit}* cảnh báo. /upgrade để không giới hạn.",
    "alert_triggered": (
        "🚨 *Cảnh báo #{id} kích hoạt!*\n"
        "{symbol} {op} `{target}`\n"
        "Giá hiện tại: `{price}`"
    ),
    "alert_triggered_pct": (
        "🚨 *Cảnh báo #{id} kích hoạt!*\n"
        "{symbol} đã dịch `{pct}%` từ `{reference}` → `{price}`\n"
        "Ngưỡng: ±{target}%"
    ),
    "alert_market_closed": "🕑 Thị trường đang đóng cửa (cuối tuần/lễ). Cảnh báo commodity sẽ tạm ngưng.",

    # Journal
    "log_pick_asset": "📊 *Ghi lệnh mới*\n\nChọn loại tài sản:",
    "log_symbol": "Nhập mã (vd `BTCUSDT`, `XAUUSD`):",
    "log_side": "Chọn hướng:",
    "log_side_long": "🟢 Long",
    "log_side_short": "🔴 Short",
    "log_entry": "Nhập giá vào lệnh:",
    "log_size": "Nhập khối lượng (đơn vị):",
    "log_sl": "Nhập stop-loss (hoặc gõ `skip`):",
    "log_tp": "Nhập take-profit (hoặc gõ `skip`):",
    "log_note": "Ghi chú ngắn (hoặc gõ `skip`):",
    "log_saved": "✅ Đã lưu lệnh *#{id}* {side} {symbol} @ `{entry}`",
    "log_auto_close_note": "🤖 TP/SL đã thiết lập — lệnh sẽ tự động đóng khi chạm mục tiêu.",
    "log_limit_free": "⚠️ Gói Free giới hạn *{limit}* lệnh/tháng. /upgrade để không giới hạn.",
    "trade_auto_closed": (
        "🤖 *Lệnh #{id} tự động đóng — {reason}*\n"
        "{symbol} @ `{exit}`\n"
        "PnL: `{pnl}` USD ({pnl_pct}%)"
    ),
    "close_reason_tp": "Chốt lời TP",
    "close_reason_sl": "Cắt lỗ SL",

    "close_usage": "Cú pháp: `/close <id> <giá_đóng>`",
    "close_not_found": "Không tìm thấy lệnh hoặc lệnh đã đóng.",
    "close_done": (
        "✅ Đã đóng lệnh *#{id}*\n"
        "Giá đóng: `{exit}`\n"
        "PnL: `{pnl}` USD ({pnl_pct}%)"
    ),

    "journal_empty": "Chưa có lệnh nào. Dùng /log để ghi.",
    "journal_header": "*Lệnh gần đây:*",
    "journal_item_open": "`#{id}` {side} {symbol} @ `{entry}` — *mở*",
    "journal_item_closed": "`#{id}` {side} {symbol} @ `{entry}` → `{exit}` — `{pnl}` USD",

    "stats_empty": "Chưa đủ dữ liệu để thống kê. Đóng ít nhất 1 lệnh để xem.",
    "stats_body": (
        "📊 *Thống kê giao dịch*\n\n"
        "Tổng lệnh đã đóng: *{total}*\n"
        "Thắng: *{wins}* • Thua: *{losses}*\n"
        "Win-rate: *{winrate}%*\n"
        "Tổng PnL: *{total_pnl}* USD\n"
        "Trung bình thắng: `{avg_win}` USD\n"
        "Trung bình thua: `{avg_loss}` USD\n"
        "R:R trung bình: `{avg_rr}`"
    ),

    # Language
    "lang_current": "Ngôn ngữ hiện tại: *{name}*\n\nChọn ngôn ngữ mới:",

    # Payment
    "upgrade_intro": (
        "💎 *Nâng cấp Premium*\n\n"
        "Lợi ích:\n"
        "• Không giới hạn cảnh báo (thay vì 3)\n"
        "• Check giá 5s (thay vì 60s)\n"
        "• Không giới hạn số lệnh ghi nhật ký\n"
        "• Export CSV + AI review hàng tuần\n\n"
        "Chọn gói:"
    ),
    "upgrade_monthly": "⭐ Monthly — {stars} Stars",
    "upgrade_yearly": "⭐ Yearly — {stars} Stars (tiết kiệm 33%)",
    "invoice_title_monthly": "Trader Bot Premium — 1 tháng",
    "invoice_title_yearly": "Trader Bot Premium — 1 năm",
    "invoice_desc": "Mở khoá toàn bộ tính năng Premium.",
    "payment_success": (
        "🎉 *Kích hoạt Premium thành công!*\n"
        "Hết hạn: *{until}*\n\n"
        "Cảm ơn đã ủng hộ! Dùng /help để xem các tính năng mới."
    ),
    "payment_renew_reminder": (
        "⏰ Gói Premium của bạn sẽ hết hạn trong *{days}* ngày "
        "({until}).\n\nDùng /upgrade để gia hạn."
    ),
    "payment_expired": (
        "ℹ️ Gói Premium đã hết hạn. Bạn đã được chuyển về gói Free.\n"
        "Dùng /upgrade để tiếp tục."
    ),
}
