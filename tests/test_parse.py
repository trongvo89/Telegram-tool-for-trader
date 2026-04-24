from decimal import Decimal

from bot.utils.parse import fmt, parse_number


def test_parse_plain_number():
    assert parse_number("123.45") == Decimal("123.45")


def test_parse_with_comma_separator():
    assert parse_number("1,234.56") == Decimal("1234.56")


def test_parse_k_suffix():
    assert parse_number("70k") == Decimal(70_000)
    assert parse_number("1.5k") == Decimal("1500")


def test_parse_m_suffix():
    assert parse_number("2m") == Decimal(2_000_000)


def test_parse_b_suffix():
    assert parse_number("1b") == Decimal(1_000_000_000)


def test_parse_invalid_returns_none():
    assert parse_number("abc") is None
    assert parse_number("") is None


def test_parse_strips_whitespace():
    assert parse_number("  42  ") == Decimal(42)


def test_fmt_basic():
    assert fmt(Decimal("1234.5"), 2) == "1,234.50"


def test_fmt_custom_decimals():
    assert fmt(Decimal("0.123456"), 4) == "0.1235"
