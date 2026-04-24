"""PTB JobQueue-based cron jobs.

We piggy-back on python-telegram-bot's JobQueue (which wraps APScheduler) so
we don't need a separate scheduler process. Jobs get the bot via context.bot.
"""
import logging

from telegram.ext import Application, ContextTypes

from bot.services import alert_engine, journal_auto_close, price_feed
from bot.services.subscription import expire_and_remind

logger = logging.getLogger(__name__)


async def _commodity_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    await price_feed.refresh_commodity_cache()


async def _expire_sweep(context: ContextTypes.DEFAULT_TYPE) -> None:
    await expire_and_remind(context.bot)


def schedule(app: Application) -> None:
    jq = app.job_queue
    # commodity price poll every 120s (stays well under TwelveData free 800/day)
    jq.run_repeating(_commodity_poll, interval=120, first=5, name="commodity_poll")
    # alert scans
    jq.run_repeating(alert_engine.scan_premium, interval=5, first=10, name="alert_scan_premium")
    jq.run_repeating(alert_engine.scan_free, interval=60, first=30, name="alert_scan_free")
    # auto TP/SL close — same tick rates as alert scans
    jq.run_repeating(journal_auto_close.scan_premium, interval=5, first=12, name="auto_close_premium")
    jq.run_repeating(journal_auto_close.scan_free, interval=60, first=35, name="auto_close_free")
    # subscription expiry sweep: every 6h, plus once 30s after startup
    jq.run_repeating(_expire_sweep, interval=6 * 3600, first=30, name="subscription_expiry")
    logger.info("Scheduled %d jobs", len(jq.jobs()))
