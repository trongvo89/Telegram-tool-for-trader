# Telegram Tool for Trader

Telegram bot giải quyết 3 pain-point quen thuộc của trader, đa thị trường và đa ngôn ngữ:

- 🔔 **Price Alerts** — crypto (Binance), vàng (XAU), bạc (XAG), dầu WTI & Brent
- 📊 **Trading Journal** — ghi lệnh, tính win-rate, PnL, R:R
- 🧮 **Position Calculator** — tính khối lượng vào lệnh theo rủi ro
- 💎 **Premium tự động** qua Telegram Stars (không cần backend payment riêng)
- 🌐 **Đa ngôn ngữ** — Tiếng Việt 🇻🇳 / English 🇬🇧, đổi ngay trong bot

## Quick start

### 1. Lấy credential
- **Bot token**: chat với [@BotFather](https://t.me/BotFather) → `/newbot`
- **TwelveData API key**: đăng ký free tại https://twelvedata.com (800 req/ngày — đủ xài cho commodity)

### 2. Chạy local bằng Docker

```bash
cp .env.example .env
# sửa .env: điền BOT_TOKEN, TWELVEDATA_API_KEY
docker compose up --build
```

Bot sẽ tự tạo schema SQLite/Postgres ở lần chạy đầu. Healthcheck tại `http://localhost:8080/healthz`.

### 3. Chạy bare-metal (không Docker)

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env      # rồi sửa các giá trị
python -m bot.main
```

## Các lệnh Telegram

| Lệnh | Mô tả |
|------|-------|
| `/start` | Đăng ký + chọn ngôn ngữ lần đầu |
| `/lang` | Đổi ngôn ngữ VI ↔ EN bất kỳ lúc nào |
| `/help` | Danh sách lệnh |
| `/alert` | Wizard tạo cảnh báo (chọn asset → symbol → điều kiện → target) |
| `/alerts` | Liệt kê cảnh báo đang bật |
| `/delalert <id>` | Xoá cảnh báo |
| `/log` | Wizard ghi nhật ký lệnh mới |
| `/close <id> <giá>` | Đóng lệnh và tính PnL |
| `/journal` | 10 lệnh gần nhất |
| `/stats` | Thống kê win-rate, PnL, R:R |
| `/calc` | Wizard tính position size |
| `/upgrade` | Nâng cấp Premium (Telegram Stars) |
| `/cancel` | Huỷ wizard đang chạy |

## Thị trường hỗ trợ

| Symbol | Loại | Nguồn giá |
|--------|------|-----------|
| Bất kỳ USDT pair (`BTCUSDT`, `ETHUSDT`…) | Crypto | Binance WebSocket (realtime) |
| `XAUUSD` | Vàng | TwelveData (fallback yfinance) |
| `XAGUSD` | Bạc | TwelveData (fallback yfinance) |
| `WTI` | Dầu WTI | TwelveData (fallback yfinance) |
| `BRENT` | Dầu Brent | TwelveData (fallback yfinance) |

Commodity poll mỗi 120s. Alert scan mỗi 5s cho Premium, 60s cho Free.

## Kiến trúc

```
bot/
├── main.py              # entrypoint: bootstrap DB + PTB + cron + health server
├── config.py            # pydantic-settings đọc .env
├── db.py                # SQLAlchemy 2.0 async engine + session_scope
├── models.py            # User, Alert, Trade, Payment
├── i18n.py              # t(key, lang, **kwargs) + parity check
├── health.py            # aiohttp /healthz
├── locales/             # vi.py, en.py — dict chuỗi dịch
├── handlers/            # start, lang, alerts, journal, calculator, payment
├── services/            # price_feed, symbols, alert_engine, journal_stats, subscription, users
└── jobs/cron.py         # alert scans, commodity poller, subscription expiry
```

## Pricing & monetize

Mặc định:

| Gói | Giá | Lợi ích |
|-----|-----|---------|
| Free | 0 | 3 alerts, 20 trades/tháng, scan 60s crypto / 5p commodity |
| Premium Monthly | 500 ⭐ | Không giới hạn alerts, 5s scan, unlimited trades, CSV export, AI weekly review |
| Premium Yearly | 4000 ⭐ | Như trên, tiết kiệm 33% |

Chỉnh số Stars trong `.env` (`PREMIUM_MONTHLY_STARS`, `PREMIUM_YEARLY_STARS`).

Luồng payment hoàn toàn tự động:
1. User click `/upgrade` → chọn gói → Telegram mở invoice.
2. User pay 1 tap. Telegram gửi `pre_checkout_query` → bot auto-approve.
3. Telegram gửi `successful_payment` → bot upsert `payments` (idempotent theo `tx_id`), set `users.plan='premium'`, `premium_until = NOW() + N days`.
4. Cron 6h/lần: ai hết hạn → xuống Free + gửi DM; còn 3 ngày → gửi DM nhắc gia hạn (1 lần).

## Phát triển

```bash
pip install -e '.[dev]'
pytest
ruff check bot/
```

## Những gì chưa làm (roadmap v1.1+)

- CryptoBot payment provider (phí 3% thay vì 30%)
- CSV export trade journal
- AI weekly review qua Claude API
- Forex & stocks
- Ngôn ngữ khác (TH, ZH, KO)
