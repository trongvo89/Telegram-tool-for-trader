from bot.locales import en as _en
from bot.locales import vi as _vi

DEFAULT_LANG = "vi"
SUPPORTED = ("vi", "en")

_TABLES: dict[str, dict[str, str]] = {
    "vi": _vi.STRINGS,
    "en": _en.STRINGS,
}


def t(key: str, lang: str | None = None, **kwargs) -> str:
    """Translate a message key. Falls back to VI then to the key itself."""
    lang = lang if lang in SUPPORTED else DEFAULT_LANG
    table = _TABLES.get(lang, _TABLES[DEFAULT_LANG])
    template = table.get(key) or _TABLES[DEFAULT_LANG].get(key) or key
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template


def validate_parity() -> list[str]:
    """Return list of missing keys across locales (for CI check)."""
    vi_keys = set(_TABLES["vi"].keys())
    en_keys = set(_TABLES["en"].keys())
    missing = []
    for k in vi_keys - en_keys:
        missing.append(f"en: missing '{k}'")
    for k in en_keys - vi_keys:
        missing.append(f"vi: missing '{k}'")
    return missing
