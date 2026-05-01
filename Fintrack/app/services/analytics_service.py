"""
PostHog analytics wrapper — server-side product analytics for Claro.

Design goals:
  • Lazy single-client init — no PostHog calls happen until the first track.
  • No-op when POSTHOG_API_KEY is missing — dev environments without the key
    must not crash. A warning is logged once.
  • Exception-safe — analytics failures (network, SDK bug, malformed payload)
    must NEVER propagate into a user-facing route.
  • Auto-attach environment + user_tier + timestamp to every event so the
    PostHog UI can filter without callers passing them every time.

Public API:
  • track_event(user_id, event_name, properties=None)
  • identify_user(user_id, properties=None)
  • flush()  — flush queued events; intended for tests / shutdown hooks.

Importing this module never touches Flask config; the client is built on
first use from current_app.config (or a fallback that reads os.environ
directly when no app context is available, e.g. a CLI script).
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


# ─── Module-level state ──────────────────────────────────────────────

_client = None             # lazy-init posthog.Posthog instance, or None for no-op
_init_attempted = False    # guards repeated init attempts (and warning spam)


# ─── Internals ───────────────────────────────────────────────────────

def _read_config() -> tuple[str | None, str, str]:
    """Read (api_key, host, environment) from Flask config when available,
    falling back to env vars. Always returns a 3-tuple."""
    api_key: str | None = None
    host = "https://eu.i.posthog.com"
    environment = "development"

    try:
        from flask import current_app
        api_key = current_app.config.get("POSTHOG_API_KEY")
        host = current_app.config.get("POSTHOG_HOST") or host
        if current_app.config.get("TESTING"):
            environment = "test"
        elif current_app.config.get("DEBUG"):
            environment = "development"
        else:
            environment = "production"
    except RuntimeError:
        # No app context — fall back to env vars.
        api_key = os.environ.get("POSTHOG_API_KEY")
        host = os.environ.get("POSTHOG_HOST") or host
        environment = os.environ.get("FLASK_ENV") or "development"

    return api_key, host, environment


def _get_client():
    """Return a configured PostHog client, or None if disabled/unconfigured."""
    global _client, _init_attempted

    if _init_attempted:
        return _client

    _init_attempted = True
    api_key, host, _env = _read_config()

    if not api_key:
        logger.warning(
            "PostHog disabled: POSTHOG_API_KEY not set. "
            "Events will be dropped (no-op mode)."
        )
        _client = None
        return None

    try:
        import posthog as posthog_pkg  # local import so a missing pkg doesn't break import-time
        _client = posthog_pkg.Posthog(project_api_key=api_key, host=host)
        logger.info("PostHog client initialised (host=%s)", host)
    except Exception as exc:  # noqa: BLE001
        logger.exception("PostHog init failed; falling back to no-op: %s", exc)
        _client = None

    return _client


def _enrich(properties: dict[str, Any] | None) -> dict[str, Any]:
    """Attach environment, timestamp, and user_tier (if discoverable)."""
    _key, _host, environment = _read_config()
    out: dict[str, Any] = dict(properties or {})
    out.setdefault("environment", environment)
    out.setdefault("timestamp", datetime.now(timezone.utc).isoformat())

    # Pull current_user.tier opportunistically — never raise if unavailable.
    if "user_tier" not in out:
        try:
            from flask_login import current_user
            if getattr(current_user, "is_authenticated", False):
                tier = getattr(current_user, "subscription_tier", None) or "free"
                out["user_tier"] = tier
        except Exception:  # noqa: BLE001
            pass

    return out


# ─── Public API ──────────────────────────────────────────────────────

def track_event(
    user_id: str | int | None,
    event_name: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Fire a PostHog `capture` event.

    Failures are swallowed and logged — analytics must never crash a route.
    A None/empty `user_id` is allowed for pre-signup events (e.g. landing
    page hits); a synthetic `anonymous` distinct_id is used in that case.
    """
    if not event_name:
        return
    distinct_id = str(user_id) if user_id else "anonymous"

    client = _get_client()
    if client is None:
        return

    try:
        client.capture(
            distinct_id=distinct_id,
            event=event_name,
            properties=_enrich(properties),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("PostHog capture failed (%s): %s", event_name, exc)


def identify_user(
    user_id: str | int,
    properties: dict[str, Any] | None = None,
) -> None:
    """Associate a session/distinct_id with persistent person properties.
    Call after login / signup so funnels can attribute events to a user."""
    if not user_id:
        return

    client = _get_client()
    if client is None:
        return

    try:
        client.identify(distinct_id=str(user_id), properties=_enrich(properties))
    except Exception as exc:  # noqa: BLE001
        logger.warning("PostHog identify failed: %s", exc)


def flush() -> None:
    """Force-flush queued events. Useful for tests and shutdown hooks."""
    client = _get_client()
    if client is None:
        return
    try:
        client.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning("PostHog flush failed: %s", exc)


def _reset_for_tests() -> None:
    """Reset module state. Tests use this to swap clients between cases."""
    global _client, _init_attempted
    _client = None
    _init_attempted = False
