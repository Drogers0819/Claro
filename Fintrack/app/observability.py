"""Sentry error monitoring — errors only, PII-stripped.

This module owns the entire Sentry integration so `create_app()` stays
readable: it calls `init_sentry()` once and forgets about it. The design
mirrors `app/services/analytics_service.py` — read config from the
environment, no-op gracefully when the key (here, the DSN) is missing, and
never let the integration break local dev, tests, or CI.

Scope is deliberately minimal for beta:
  • Errors only — `traces_sample_rate=0`, no performance monitoring, no
    session replay.
  • `send_default_pii=False` — Sentry will not auto-capture user emails,
    names, or IP addresses. Non-negotiable given the financial-data context.
  • A `before_send` hook scrubs known sensitive fields from every event as
    a defence-in-depth layer on top of `send_default_pii=False`.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


# Substrings that mark a dict key as sensitive. Matching is
# case-INSENSITIVE and by SUBSTRING (not exact equality), so prefixed and
# suffixed variants are all caught wherever the key appears in the event
# (request data, stack-frame local variables, `extra`, contexts,
# breadcrumbs, headers, ...). For example:
#   "email"   → email, customer_email, user_email
#   "name"    → name, first_name, last_name, full_name
#   "_ip"     → remote_ip, client_ip, source_ip, x_real_ip
#   "secret"  → stripe_secret_key, client_secret
#
# The bias is deliberately toward over-redaction: in a financial app,
# losing a little debug context (e.g. a redacted `category_name` in a
# stack frame) is an acceptable price for guaranteeing PII and secrets
# never reach Sentry. This sits on top of `send_default_pii=False`.
_SENSITIVE_SUBSTRINGS = frozenset(
    {
        # ── secrets / credentials ──
        "password",       # password, password_hash, new_password
        "secret",         # stripe_secret_key, client_secret
        "api_key",        # anthropic_api_key, openai_api_key
        "apikey",
        "token",          # csrf_token, access_token, refresh_token
        "csrf",
        "session",        # session, session_id
        "cookie",         # Cookie / Set-Cookie headers, cookie_*
        "authorization",  # Authorization / Proxy-Authorization headers
        # ── personally identifiable information ──
        "email",          # email, customer_email, user_email
        "name",           # name, first_name, last_name, full_name
        "ip_address",
        "client_ip",
        "remote_ip",
        "forwarded_for",  # x_forwarded_for
        "_ip",            # source_ip, peer_ip, x_real_ip
        "ip_",            # ip_addr, ip_address
    }
)

_REDACTED = "[Filtered]"


def _key_is_sensitive(key):
    """True if a dict key's value should be redacted. Case-insensitive
    substring match against `_SENSITIVE_SUBSTRINGS`. Non-string keys never
    match."""
    if not isinstance(key, str):
        return False
    lowered = key.lower()
    return any(token in lowered for token in _SENSITIVE_SUBSTRINGS)


def _scrub(value):
    """Recursively walk an event and redact sensitive values.

    Returns a scrubbed copy — any dict key flagged by `_key_is_sensitive`
    has its value replaced with `[Filtered]`. Everything else is preserved.
    Lists/tuples are walked element-wise; scalars pass through untouched.
    """
    if isinstance(value, dict):
        cleaned = {}
        for key, val in value.items():
            if _key_is_sensitive(key):
                cleaned[key] = _REDACTED
            else:
                cleaned[key] = _scrub(val)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_scrub(item) for item in value]
    return value


def before_send(event, hint):
    """Sentry `before_send` hook — strip sensitive fields before any event
    leaves the process.

    Wrapped in a try/except so a malformed event can never turn an error
    report into a second error: on any failure we fall back to the original
    event rather than dropping it silently.
    """
    try:
        return _scrub(event)
    except Exception:  # noqa: BLE001 - scrubbing must never raise
        logger.warning("Sentry before_send scrub failed; sending original event")
        return event


def init_sentry():
    """Initialise Sentry if `SENTRY_DSN` is set; otherwise no-op.

    Returns True if Sentry was initialised, False if it was skipped (no DSN
    or the SDK isn't installed). Safe to call unconditionally from
    `create_app()` — local dev, tests, and CI run without a DSN and get the
    no-op path.
    """
    dsn = os.environ.get("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("SENTRY_DSN not set — Sentry error monitoring disabled.")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
    except ImportError:
        logger.warning("sentry-sdk not installed — Sentry error monitoring disabled.")
        return False

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        # Errors only — no performance monitoring, no session replay.
        traces_sample_rate=0,
        # Distinguishes staging from production in the Sentry dashboard.
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        # Render injects RENDER_GIT_COMMIT automatically → per-deploy
        # error attribution. Falls back to "unknown" off-Render.
        release=os.environ.get("RENDER_GIT_COMMIT", "unknown"),
        # PII protection: do not auto-capture emails, names, IPs.
        send_default_pii=False,
        before_send=before_send,
    )
    logger.info(
        "Sentry initialised (environment=%s, release=%s)",
        os.environ.get("SENTRY_ENVIRONMENT", "production"),
        os.environ.get("RENDER_GIT_COMMIT", "unknown"),
    )
    return True
