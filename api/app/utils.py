"""Небольшие независимые хелперы: нормализация телефона КР, санитизация текста."""
from __future__ import annotations

import re

_DIGITS_RE = re.compile(r"\D")
_HTML_TAG_RE = re.compile(r"<[^>]*>")


class InvalidPhoneError(ValueError):
    pass


def normalize_kg_phone(raw: str) -> str:
    """Приводит номер к формату +996XXXXXXXXX.

    Принимает: '0555123456', '996555123456', '+996 555 12-34-56', '555123456'.
    """
    digits = _DIGITS_RE.sub("", raw or "")

    if digits.startswith("996") and len(digits) == 12:
        normalized = digits
    elif digits.startswith("8996") and len(digits) == 13:
        normalized = digits[1:]
    elif digits.startswith("0") and len(digits) == 10:
        normalized = "996" + digits[1:]
    elif len(digits) == 9:
        normalized = "996" + digits
    else:
        raise InvalidPhoneError(f"Не удалось распознать номер телефона: {raw!r}")

    if len(normalized) != 12 or not normalized.startswith("996"):
        raise InvalidPhoneError(f"Не удалось распознать номер телефона: {raw!r}")

    return "+" + normalized


def strip_html(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = _HTML_TAG_RE.sub("", text).strip()
    return cleaned or None
