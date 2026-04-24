from bot.i18n import SUPPORTED, t, validate_parity


def test_parity():
    assert validate_parity() == [], "vi and en locales must have the exact same keys"


def test_supported_languages():
    assert set(SUPPORTED) == {"vi", "en"}


def test_format_with_kwargs():
    msg = t("alert_limit_free", "vi", limit=3)
    assert "3" in msg
    msg_en = t("alert_limit_free", "en", limit=5)
    assert "5" in msg_en


def test_unknown_lang_falls_back_to_vi():
    msg = t("welcome", "xx")
    assert "Trader Bot" in msg  # VI string contains it too


def test_unknown_key_returns_key():
    assert t("nonexistent_key_123", "vi") == "nonexistent_key_123"


def test_missing_kwargs_returns_raw_template():
    # Missing placeholder should not blow up, should return the raw template string
    result = t("alert_limit_free", "vi")
    assert "{limit}" in result
