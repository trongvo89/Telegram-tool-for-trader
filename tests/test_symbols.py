from bot.services.symbols import COMMODITIES, get_info, normalize_crypto_symbol


def test_normalize_btc_shortform():
    assert normalize_crypto_symbol("btc") == "BTCUSDT"


def test_normalize_already_full():
    assert normalize_crypto_symbol("BTCUSDT") == "BTCUSDT"


def test_normalize_handles_slash():
    assert normalize_crypto_symbol("BTC/USDT") == "BTCUSDT"


def test_normalize_keeps_usd_pair():
    assert normalize_crypto_symbol("BTCUSD") == "BTCUSD"


def test_get_info_for_commodity():
    info = get_info("XAUUSD")
    assert info.asset_class == "metal"
    assert info.source == "twelvedata"
    assert info.yfinance_symbol == "GC=F"


def test_get_info_defaults_to_crypto_for_unknown():
    info = get_info("SOLUSDT")
    assert info.asset_class == "crypto"
    assert info.source == "binance"


def test_all_four_commodities_registered():
    assert set(COMMODITIES.keys()) == {"XAUUSD", "XAGUSD", "WTI", "BRENT"}
