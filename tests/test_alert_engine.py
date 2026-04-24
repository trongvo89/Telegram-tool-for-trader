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
