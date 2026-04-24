from decimal import Decimal

from bot.services.alert_engine import _is_triggered


def test_above_triggers_when_price_crosses():
    assert _is_triggered("above", Decimal("70100"), Decimal("70000")) is True


def test_above_triggers_at_exact_target():
    assert _is_triggered("above", Decimal("70000"), Decimal("70000")) is True


def test_above_not_triggered_below_target():
    assert _is_triggered("above", Decimal("69999"), Decimal("70000")) is False


def test_below_triggers_when_price_drops():
    assert _is_triggered("below", Decimal("69999"), Decimal("70000")) is True


def test_below_triggers_at_exact_target():
    assert _is_triggered("below", Decimal("70000"), Decimal("70000")) is True


def test_below_not_triggered_above_target():
    assert _is_triggered("below", Decimal("70001"), Decimal("70000")) is False


def test_unknown_condition_never_triggers():
    assert _is_triggered("wtf", Decimal("100"), Decimal("50")) is False


# ── pct_change ─────────────────────────────────────────────────────────────

def test_pct_change_triggers_on_positive_move():
    # Reference 100, price 104 → +4%, threshold 3% → trigger
    assert _is_triggered("pct_change", Decimal("104"), Decimal("3"), Decimal("100")) is True


def test_pct_change_triggers_on_negative_move():
    # Reference 100, price 96 → -4%, threshold 3% → trigger
    assert _is_triggered("pct_change", Decimal("96"), Decimal("3"), Decimal("100")) is True


def test_pct_change_not_triggered_below_threshold():
    # Reference 100, price 102 → +2%, threshold 3% → no trigger
    assert _is_triggered("pct_change", Decimal("102"), Decimal("3"), Decimal("100")) is False


def test_pct_change_triggers_at_exact_threshold():
    # Reference 100, price 103 → exactly 3%
    assert _is_triggered("pct_change", Decimal("103"), Decimal("3"), Decimal("100")) is True


def test_pct_change_no_reference_never_triggers():
    assert _is_triggered("pct_change", Decimal("103"), Decimal("3"), None) is False


def test_pct_change_zero_reference_never_triggers():
    assert _is_triggered("pct_change", Decimal("103"), Decimal("3"), Decimal("0")) is False
