"""Tests for GDPR data-export route: /settings/export-data.

Covers:
  • Unauthenticated request is rejected (redirected to login).
  • Authenticated request returns the user's data as downloadable JSON.
  • password_hash never appears in the response — neither the literal
    string "password_hash" nor the actual hash value, scanned across
    the whole body at any nesting depth.
"""

import json

from app import db
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.goal import Goal


def _make_user(email="export@test.com"):
    user = User(email=email, name="Export User")
    user.set_password("testpassword123")
    db.session.add(user)
    db.session.commit()
    return user


def _login(client, email="export@test.com", password="testpassword123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


class TestExportDataAuth:

    def test_unauthenticated_request_is_rejected(self, client):
        resp = client.get("/settings/export-data")
        assert resp.status_code in (302, 401)
        if resp.status_code == 302:
            assert "/login" in resp.headers.get("Location", "")


class TestExportDataContent:

    def test_authenticated_user_gets_their_data(self, app, client):
        with app.app_context():
            user = _make_user()
            food = Category.query.filter_by(name="Food").first()
            from datetime import date
            db.session.add(Transaction(
                user_id=user.id, amount=12.50, description="Lunch",
                category_id=food.id, type="expense", date=date(2026, 5, 1),
            ))
            db.session.add(Goal(
                user_id=user.id, name="Emergency Fund", type="savings",
                target_amount=1000, current_amount=200,
            ))
            db.session.commit()

        _login(client)
        resp = client.get("/settings/export-data")

        assert resp.status_code == 200
        assert resp.mimetype == "application/json"
        disposition = resp.headers.get("Content-Disposition", "")
        assert "attachment" in disposition
        assert ".json" in disposition

        body_text = resp.get_data(as_text=True)
        payload = json.loads(body_text)

        assert payload["user"]["email"] == "export@test.com"
        assert payload["user"]["name"] == "Export User"
        assert payload["schema_version"] == 1
        assert "export_generated_at" in payload

        assert len(payload["transactions"]) == 1
        assert payload["transactions"][0]["description"] == "Lunch"
        assert len(payload["goals"]) == 1
        assert payload["goals"][0]["name"] == "Emergency Fund"

        for key in (
            "budgets", "checkins", "life_checkins", "crisis_events",
            "subscription_events", "recurring_contributions", "chat_messages",
        ):
            assert key in payload
            assert isinstance(payload[key], list)

    def test_password_hash_never_appears_anywhere_in_body(self, app, client):
        with app.app_context():
            user = _make_user(email="leak@test.com")
            hash_value = user.password_hash
            assert hash_value, "fixture must have a real hash"

        _login(client, email="leak@test.com")
        resp = client.get("/settings/export-data")
        assert resp.status_code == 200

        body_text = resp.get_data(as_text=True)

        assert "password_hash" not in body_text, (
            "the literal string 'password_hash' must not appear in the export"
        )
        assert hash_value not in body_text, (
            "the actual password hash value must not appear in the export"
        )

        def _walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    assert "password" not in str(k).lower(), (
                        f"forbidden key surfaced at depth: {k!r}"
                    )
                    _walk(v)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)
            elif isinstance(node, str):
                assert hash_value not in node, (
                    "hash value leaked inside a string value"
                )

        _walk(json.loads(body_text))
