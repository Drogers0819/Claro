"""Debug-only routes for one-off production verification.

Currently hosts `/debug/sentry-test`, used once after a deploy to confirm
Sentry is wired up correctly (correct environment tag, release tag, no PII).

The route is gated on the `SENTRY_DEBUG_ENABLED=1` environment variable,
checked at request time so it can be toggled via Render env vars. When the
var is unset (the normal state in production and local dev) the route
returns 404 — it can't be hit accidentally.

This route is intentionally temporary: enable `SENTRY_DEBUG_ENABLED` only
long enough to verify Sentry, then remove the env var. The route itself
should be removed in a follow-up commit once verification is stable.
"""

from __future__ import annotations

import os

from flask import Blueprint, abort

debug_bp = Blueprint("debug", __name__)


@debug_bp.route("/debug/sentry-test")
def sentry_test():
    """Raise an unhandled error so Sentry captures it.

    Gated: 404 unless `SENTRY_DEBUG_ENABLED=1`. The env var is read on every
    request, so flipping it in the Render dashboard takes effect on the next
    deploy without a code change.
    """
    if os.environ.get("SENTRY_DEBUG_ENABLED") != "1":
        abort(404)
    raise RuntimeError("Sentry verification test")
