"""Shared parsing helpers."""
from decimal import Decimal, InvalidOperation


def parse_number(raw: str) -> Decimal | None:
    """Parse a number allowing suffixes k/m/b and commas."""
    s = raw.strip().lower().replace(",", "").replace("_", "")
    mult = Decimal(1)
    if s.endswith("k"):
        mult, s = Decimal(1_000), s[:-1]
    elif s.endswith("m"):
        mult, s = Decimal(1_000_000), s[:-1]
    elif s.endswith("b"):
        mult, s = Decimal(1_000_000_000), s[:-1]
    try:
        return Decimal(s) * mult
    except (InvalidOperation, ValueError):
        return None


def fmt(val: Decimal, decimals: int = 2) -> str:
    """Format a Decimal with fixed decimals, stripping trailing zeros beyond the first."""
    q = Decimal(10) ** -decimals
    return f"{val.quantize(q):,}"
