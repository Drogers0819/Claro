"""
Admin routes — Block 2 Task 2.7.

A small read-only surface for the founder team. There is no
`User.is_admin` column or `@admin_required` decorator in the codebase
yet, so the gate is a hardcoded email match against the founder's
account. This is deliberately limited:

  • Only one route lives here today (the signposting audit page).
  • The gate prevents any logged-in user other than the founder from
    seeing the page.
  • When admin tooling grows beyond this, the right move is a real
    `is_admin` column + decorator + ACL — flagged in
    DEVELOPMENT.md.
"""

from __future__ import annotations

import os
from functools import wraps

from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# Founder email — read from FOUNDER_EMAIL env var at import. Must be set
# in production (Render). If unset, the admin gate denies everyone.
_FOUNDER_EMAIL = os.environ.get("FOUNDER_EMAIL", "").strip().lower()


def _require_founder(view):
    """Lightweight admin gate. Flask-Login provides login_required; this
    decorator adds the founder-email check on top. 404 (not 403) on a
    non-founder so the route's existence isn't leaked to logged-in
    civilian users."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(404)
        if not _FOUNDER_EMAIL:
            abort(404)
        if (current_user.email or "").lower() != _FOUNDER_EMAIL:
            abort(404)
        return view(*args, **kwargs)
    return wrapped


@admin_bp.route("/signposting", methods=["GET"])
@login_required
@_require_founder
def signposting_audit():
    """Read-only audit of the signposting library. Lets non-developers
    spot-check the canonical list without reading Python."""
    from app.services.signposting_library import (
        CATEGORIES, get_all_resources,
    )
    return render_template(
        "admin/signposting_audit.html",
        resources=get_all_resources(),
        categories=CATEGORIES,
    )
