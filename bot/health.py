"""Tiny aiohttp server exposing /healthz for UptimeRobot & orchestrators."""
import logging

from aiohttp import web

from bot.config import settings

logger = logging.getLogger(__name__)


async def _healthz(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def start_health_server() -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/healthz", _healthz)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, settings.health_host, settings.health_port)
    await site.start()
    logger.info("Health server listening on %s:%s", settings.health_host, settings.health_port)
    return runner
