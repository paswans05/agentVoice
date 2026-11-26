"""Lead validation, phone normalization, privacy masking, and CSV formula safety."""

from __future__ import annotations

import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_phone(raw: str | None) -> str | None:
    """Normalize phone digits while preserving leading '+' if present; never guesses country code."""
    if not raw:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None
    has_plus = cleaned.startswith("+")
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) < 6 or len(digits) > 15:
        return None
    return f"+{digits}" if has_plus else digits


def is_valid_phone(raw: str | None) -> bool:
    if not raw or not raw.strip():
        return True
    return normalize_phone(raw) is not None


def is_valid_email(raw: str | None) -> bool:
    if not raw or not raw.strip():
        return True
    return bool(EMAIL_RE.match(raw.strip()))


def mask_phone(raw: str | None) -> str:
    if not raw:
        return ""
    s = raw.strip()
    if len(s) <= 4:
        return "****"
    return f"{'*' * (len(s) - 4)}{s[-4:]}"


def mask_email(raw: str | None) -> str:
    if not raw or "@" not in raw:
        return ""
    local, domain = raw.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"


def sanitize_csv_cell(value: object) -> str:
    """Prevent CSV formula injection in spreadsheet applications."""
    text = "" if value is None else str(value)
    if text and text[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{text}"
    return text
