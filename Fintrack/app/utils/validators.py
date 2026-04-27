"""Server-side validation helpers for user-supplied input."""

import re

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_amount(value, field_name, min_val=0, max_val=1_000_000, allow_none=False):
    """Validate a financial amount. Returns a float rounded to 2 dp.

    Raises ValueError with a user-facing message on failure.
    """
    if value in (None, "", b""):
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required")
    try:
        amount = round(float(value), 2)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid number")
    if amount != amount or amount in (float("inf"), float("-inf")):
        raise ValueError(f"{field_name} must be a finite number")
    if amount < min_val:
        raise ValueError(f"{field_name} cannot be below {min_val:g}")
    if amount > max_val:
        raise ValueError(f"{field_name} is too large (max {max_val:g})")
    return amount


def sanitize_string(value, max_length=500):
    """Strip HTML tags and limit length. Returns trimmed string."""
    if not value:
        return ""
    cleaned = _HTML_TAG_RE.sub("", str(value))
    return cleaned[:max_length].strip()


def validate_email(value):
    """Validate an email address shape. Returns the cleaned email."""
    if not value:
        raise ValueError("Email is required")
    email = str(value).strip().lower()
    if len(email) > 254:
        raise ValueError("Email is too long")
    if not _EMAIL_RE.match(email):
        raise ValueError("Enter a valid email address")
    return email


def validate_password(value):
    """Validate a password. Returns the password unchanged on success.

    Rules: at least 8 characters; not just whitespace.
    """
    if value is None:
        raise ValueError("Password is required")
    if not isinstance(value, str):
        value = str(value)
    if not value.strip():
        raise ValueError("Password cannot be blank")
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    return value


def validate_name(value, max_length=100):
    """Strip HTML, trim, and require non-empty within max_length."""
    cleaned = sanitize_string(value, max_length=max_length)
    if not cleaned:
        raise ValueError("Name is required")
    return cleaned


def validate_int(value, field_name, min_val=None, max_val=None, allow_none=True):
    """Validate an integer. Returns int or None if allow_none and empty."""
    if value in (None, "", b""):
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required")
    try:
        n = int(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a whole number")
    if min_val is not None and n < min_val:
        raise ValueError(f"{field_name} cannot be below {min_val}")
    if max_val is not None and n > max_val:
        raise ValueError(f"{field_name} cannot exceed {max_val}")
    return n
