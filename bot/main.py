"""Entry point: bootstraps DB, Telegram Application, background tasks, health server."""
import asyncio
import logging

from telegram.ext import Application, ApplicationBuilder

from bot import models  # noqa: F401 - ensure models imported before create_all
from bot.config import settings
from bot.db import Base, engine
from bot.handlers import admin, alerts, calculator, journal, payment, start
from bot.health import start_health_server
from bot.i18n import validate_parity
from bot.jobs import cron
from bot.services import price_feed


def _setup_logging() -> None:
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _post_init(app: Application) -> None:
    await _init_db()
    app.bot_data["ws_stop"] = asyncio.Event()
    app.bot_data["ws_task"] = asyncio.create_task(
        price_feed.binance_ws_loop(stop_event=app.bot_data["ws_stop"])
    )
    app.bot_data["health_runner"] = await start_health_server()
    await price_feed.refresh_commodity_cache()


async def _post_shutdown(app: Application) -> None:
    stop: asyncio.Event | None = app.bot_data.get("ws_stop")
    if stop:
        stop.set()
    task: asyncio.Task | None = app.bot_data.get("ws_task")
    if task:
        task.cancel()
    runner = app.bot_data.get("health_runner")
    if runner:
        await runner.cleanup()


def main() -> None:
    _setup_logging()
    log = logging.getLogger(__name__)

    missing = validate_parity()
    if missing:
        log.warning("i18n parity issues: %s", missing)

    app = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .post_init(_post_init)
        .post_shutdown(_post_shutdown)
        .build()
    )

    start.register(app)
    calculator.register(app)
    alerts.register(app)
    journal.register(app)
    payment.register(app)
    admin.register(app)

    cron.schedule(app)

    log.info("Bot starting in polling mode")
    app.run_polling(allowed_updates=["message", "callback_query", "pre_checkout_query"])


if __name__ == "__main__":
    main()
