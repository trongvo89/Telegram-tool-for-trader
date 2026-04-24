"""Symbol registry for multi-asset support.

Crypto symbols are validated dynamically against Binance.
Commodity symbols are a fixed set mapped to their data source tickers.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolInfo:
    symbol: str            # canonical symbol used in DB / UI
    asset_class: str       # 'crypto' | 'metal' | 'energy'
    source: str            # 'binance' | 'twelvedata' | 'yfinance'
    twelvedata_symbol: str | None = None
    yfinance_symbol: str | None = None
    decimals: int = 2


COMMODITIES: dict[str, SymbolInfo] = {
    "XAUUSD": SymbolInfo(
        symbol="XAUUSD", asset_class="metal", source="twelvedata",
        twelvedata_symbol="XAU/USD", yfinance_symbol="GC=F", decimals=2,
    ),
    "XAGUSD": SymbolInfo(
        symbol="XAGUSD", asset_class="metal", source="twelvedata",
        twelvedata_symbol="XAG/USD", yfinance_symbol="SI=F", decimals=3,
    ),
    "WTI": SymbolInfo(
        symbol="WTI", asset_class="energy", source="twelvedata",
        twelvedata_symbol="WTI/USD", yfinance_symbol="CL=F", decimals=2,
    ),
    "BRENT": SymbolInfo(
        symbol="BRENT", asset_class="energy", source="twelvedata",
        twelvedata_symbol="BRENT/USD", yfinance_symbol="BZ=F", decimals=2,
    ),
}


def normalize_crypto_symbol(raw: str) -> str:
    """Normalize user input like 'btc', 'btcusdt', 'BTC/USDT' to 'BTCUSDT'."""
    s = raw.strip().upper().replace("/", "").replace("-", "").replace("_", "")
    if not s.endswith("USDT") and not s.endswith("USD") and not s.endswith("BUSD"):
        s = s + "USDT"
    return s


def get_info(symbol: str) -> SymbolInfo:
    """Return SymbolInfo; crypto symbols are assumed valid Binance USDT pairs."""
    if symbol in COMMODITIES:
        return COMMODITIES[symbol]
    # assume crypto
    return SymbolInfo(symbol=symbol, asset_class="crypto", source="binance", decimals=8)


def all_commodities() -> list[SymbolInfo]:
    return list(COMMODITIES.values())
