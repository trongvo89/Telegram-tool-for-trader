from decimal import Decimal

from bot.services.journal_stats import pnl_of


def test_long_profit():
    # Bought 1 unit at 100, sold at 110 -> +10
    assert pnl_of("long", Decimal(100), Decimal(110), Decimal(1)) == Decimal(10)


def test_long_loss():
    assert pnl_of("long", Decimal(100), Decimal(90), Decimal(1)) == Decimal(-10)


def test_short_profit():
    # Shorted 1 unit at 100, covered at 90 -> +10
    assert pnl_of("short", Decimal(100), Decimal(90), Decimal(1)) == Decimal(10)


def test_short_loss():
    assert pnl_of("short", Decimal(100), Decimal(110), Decimal(1)) == Decimal(-10)


def test_scales_by_size():
    assert pnl_of("long", Decimal(100), Decimal(101), Decimal(5)) == Decimal(5)
