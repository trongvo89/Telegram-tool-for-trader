"""Unified price feed.

Crypto: Binance WebSocket !miniTicker@arr (realtime for all USDT pairs).
Commodities: TwelveData REST polled every N seconds by commodity_poller job,
             with yfinance as a free fallback.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import websockets

from bot.config import settings
from bot.services import symbols as sym

logger = logging.getLogger(__name__)

# In-memory price cache: symbol -> (price, timestamp)
_cache: dict[str, tuple[Decimal, datetime]] = {}
_cache_lock = asyncio.Lock()

BINANCE_WS = "wss://stream.binance.com:9443/ws/!miniTicker@arr"
TWELVEDATA_BASE = "https://api.twelvedata.com"


async def _set_price(symbol: str, price: Decimal) -> None:
    async with _cache_lock:
        _cache[symbol] = (price, datetime.now(timezone.utc))


async def get_price(symbol: str) -> Decimal | None:
    """Return latest cached price or None."""
    async with _cache_lock:
        entry = _cache.get(symbol)
    return entry[0] if entry else None


async def get_price_with_age(symbol: str) -> tuple[Decimal, datetime] | None:
    async with _cache_lock:
        return _cache.get(symbol)


# ---------- Binance crypto WS ----------

async def binance_ws_loop(stop_event: asyncio.Event) -> None:
    """Subscribe to all-market miniTicker stream and update cache indefinitely."""
    backoff = 1
    while not stop_event.is_set():
        try:
            async with websockets.connect(BINANCE_WS, ping_interval=30) as ws:
                logger.info("Binance WS connected")
                backoff = 1
                while not stop_event.is_set():
                    raw = await asyncio.wait_for(ws.recv(), timeout=60)
                    data = json.loads(raw)
                    if not isinstance(data, list):
                        continue
                    for tick in data:
                        sym_name = tick.get("s")
                        close = tick.get("c")
                        if sym_name and close:
                            try:
                                await _set_price(sym_name, Decimal(close))
                            except Exception:
                                pass
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Binance WS error: %s — reconnect in %ss", exc, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)


# ---------- Commodity fetchers ----------

async def fetch_commodities_twelvedata() -> dict[str, Decimal]:
    """Fetch all commodity symbols in one batch call. Returns {canonical: price}."""
    if not settings.twelvedata_api_key:
        return {}
    pairs = [c.twelvedata_symbol for c in sym.all_commodities() if c.twelvedata_symbol]
    if not pairs:
        return {}
    url = f"{TWELVEDATA_BASE}/price"
    params = {"symbol": ",".join(pairs), "apikey": settings.twelvedata_api_key}
    out: dict[str, Decimal] = {}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as exc:
        logger.warning("TwelveData fetch failed: %s", exc)
        return {}
    # Response shape when multi-symbol: {"XAU/USD": {"price": "2345.1"}, ...}
    # When single symbol: {"price": "..."}
    if "price" in data and len(pairs) == 1:
        single = sym.all_commodities()[0]
        try:
            out[single.symbol] = Decimal(str(data["price"]))
        except Exception:
            pass
        return out
    for info in sym.all_commodities():
        entry = data.get(info.twelvedata_symbol) if isinstance(data, dict) else None
        if entry and "price" in entry:
            try:
                out[info.symbol] = Decimal(str(entry["price"]))
            except Exception:
                pass
    return out


async def fetch_commodities_yfinance() -> dict[str, Decimal]:
    """Fallback using yfinance (sync lib, run in thread)."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    def _fetch_sync() -> dict[str, Decimal]:
        out: dict[str, Decimal] = {}
        for info in sym.all_commodities():
            if not info.yfinance_symbol:
                continue
            try:
                ticker = yf.Ticker(info.yfinance_symbol)
                hist = ticker.history(period="1d", interval="5m")
                if not hist.empty:
                    out[info.symbol] = Decimal(str(float(hist["Close"].iloc[-1])))
            except Exception as exc:
                logger.warning("yfinance %s failed: %s", info.yfinance_symbol, exc)
        return out

    return await asyncio.to_thread(_fetch_sync)


async def refresh_commodity_cache() -> None:
    """Called by the commodity poller cron. Try TwelveData, fallback to yfinance."""
    prices = await fetch_commodities_twelvedata()
    if not prices:
        logger.info("TwelveData empty — trying yfinance fallback")
        prices = await fetch_commodities_yfinance()
    for symbol, price in prices.items():
        await _set_price(symbol, price)
    if prices:
        logger.info("Commodity cache refreshed: %s", list(prices.keys()))


def is_market_closed_commodities() -> bool:
    """Commodity markets are closed on weekends (very rough; ignores holidays)."""
    now = datetime.now(timezone.utc)
    return now.weekday() >= 5  # 5=Sat, 6=Sun
