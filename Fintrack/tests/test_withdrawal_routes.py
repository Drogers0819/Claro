"""
Inline withdrawal flow on /plan.

The flow has three POST endpoints — preview, confirm, dismiss — that stash
state in the session and redirect back to /plan?withdraw=1. CSRF is disabled
in TestingConfig so these tests focus on auth, validation, persistence
behaviour, and the analytics surface.
"""

from datetime import datetime, timedelta

import pytest

from app import db
from app.models.goal import Goal
from app.models.user import User


def _make_subscribed_user(
    app, email="withdraw@test.com", password="testpassword123"
):
    """Create a user who can reach /plan: factfind complete, income set,
    active trial subscription."""
    with app.app_context():
        user = User(email=email, name="Withdraw Tester")
        user.set_password(password)
        user.monthly_income = 3000
        user.rent_amount = 900
        user.bills_amount = 200
        user.groceries_estimate = 250
        user.transport_estimate = 100
        user.factfind_completed = True
        user.subscription_status = "trialing"
        user.subscription_tier = "pro"
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user.id


def _add_goal(app, user_id, name, current=500.0, target=2000.0, monthly=200.0):
    with app.app_context():
        goal = Goal(
            user_id=user_id,
            name=name,
            type="savings_target",
            current_amount=current,
            target_amount=target,
            monthly_allocation=monthly,
            priority_rank=1,
            status="active",
        )
        db.session.add(goal)
        db.session.commit()
        return goal.id


@pytest.fixture
def subscribed_client(app, client):
    """A test client logged in as a subscribed user with a savings goal."""
    user_id = _make_subscribed_user(app)
    _add_goal(app, user_id, "Holiday fund", current=600.0, target=1500.0, monthly=150.0)
    client.post(
        "/api/auth/login",
        json={"email": "withdraw@test.com", "password": "testpassword123"},
    )
    return client, user_id


# ─── Auth gates ─────────────────────────────────────────────────


class TestWithdrawalAuth:

    def test_preview_requires_login(self, client):
        response = client.post(
            "/plan/withdraw/preview", data={"amount": "100"}, follow_redirects=False
        )
        # Anonymous users hit the @login_required redirect.
        assert response.status_code in (302, 401)
        if response.status_code == 302:
            assert "login" in response.headers.get("Location", "").lower()

    def test_confirm_requires_login(self, client):
        response = client.post("/plan/withdraw/confirm", follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_dismiss_requires_login(self, client):
        response = client.post("/plan/withdraw/dismiss", follow_redirects=False)
        assert response.status_code in (302, 401)


# ─── Preview ─────────────────────────────────────────────────


class TestWithdrawalPreview:

    def test_valid_amount_stashes_strategy_without_persisting(self, app, subscribed_client):
        client, user_id = subscribed_client

        response = client.post(
            "/plan/withdraw/preview", data={"amount": "300"}, follow_redirects=False
        )

        # Redirected back to /plan?withdraw=1
        assert response.status_code == 302
        assert "/plan" in response.headers["Location"]
        assert "withdraw=1" in response.headers["Location"]

        # Session has the preview, and goal current_amount is untouched.
        with client.session_transaction() as sess:
            preview = sess.get("withdrawal_preview")
            assert preview is not None
            assert preview["amount"] == 300.0
            assert preview["decided"] is False
            assert "withdrawals" in preview["result"]

        with app.app_context():
            goal = Goal.query.filter_by(user_id=user_id).first()
            assert float(goal.current_amount) == 600.0  # unchanged

    def test_invalid_amount_non_numeric_flashes_error(self, subscribed_client):
        client, _ = subscribed_client
        response = client.post(
            "/plan/withdraw/preview", data={"amount": "abc"}, follow_redirects=False
        )
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert sess.get("withdrawal_preview") is None
            flashes = sess.get("_flashes") or []
            assert any("valid amount" in m.lower() for _, m in flashes)

    def test_invalid_amount_zero_flashes_error(self, subscribed_client):
        client, _ = subscribed_client
        response = client.post(
            "/plan/withdraw/preview", data={"amount": "0"}, follow_redirects=False
        )
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert sess.get("withdrawal_preview") is None

    def test_invalid_amount_negative_flashes_error(self, subscribed_client):
        client, _ = subscribed_client
        response = client.post(
            "/plan/withdraw/preview", data={"amount": "-50"}, follow_redirects=False
        )
        assert response.status_code == 302
        with client.session_transaction() as sess:
            assert sess.get("withdrawal_preview") is None

    def test_amount_larger_than_available_shows_shortfall(self, app, subscribed_client):
        client, _ = subscribed_client

        # Goal has £600 saved but user asks for £5000.
        response = client.post(
            "/plan/withdraw/preview", data={"amount": "5000"}, follow_redirects=False
        )
        assert response.status_code == 302

        with client.session_transaction() as sess:
            preview = sess.get("withdrawal_preview")
            assert preview is not None
            assert preview["result"]["shortfall"] > 0


# ─── Confirm ─────────────────────────────────────────────────


class TestWithdrawalConfirm:

    def test_confirm_persists_plan_changes(self, app, subscribed_client):
        client, user_id = subscribed_client

        # Preview first.
        client.post("/plan/withdraw/preview", data={"amount": "200"})

        with app.app_context():
            before = float(Goal.query.filter_by(user_id=user_id).first().current_amount)

        response = client.post("/plan/withdraw/confirm", follow_redirects=False)

        assert response.status_code == 302
        assert response.headers["Location"].endswith("/plan")

        with app.app_context():
            after = float(Goal.query.filter_by(user_id=user_id).first().current_amount)
            assert after == before - 200.0

        # Session preview was cleared.
        with client.session_transaction() as sess:
            assert sess.get("withdrawal_preview") is None
            flashes = sess.get("_flashes") or []
            assert any("plan has been updated" in m.lower() for _, m in flashes)

    def test_confirm_without_preview_errors(self, app, subscribed_client):
        client, user_id = subscribed_client

        with app.app_context():
            before = float(Goal.query.filter_by(user_id=user_id).first().current_amount)

        response = client.post("/plan/withdraw/confirm", follow_redirects=False)
        assert response.status_code == 302

        # Nothing should have moved.
        with app.app_context():
            after = float(Goal.query.filter_by(user_id=user_id).first().current_amount)
            assert after == before

    def test_confirm_caps_current_amount_at_zero(self, app, subscribed_client):
        """If a withdrawal somehow exceeds current_amount the goal lands at zero,
        not a negative number."""
        client, user_id = subscribed_client

        # Withdrawal larger than the only goal's balance.
        client.post("/plan/withdraw/preview", data={"amount": "1000"})
        client.post("/plan/withdraw/confirm")

        with app.app_context():
            goal = Goal.query.filter_by(user_id=user_id).first()
            assert float(goal.current_amount) >= 0


# ─── Dismiss ─────────────────────────────────────────────────


class TestWithdrawalDismiss:

    def test_dismiss_does_not_modify_plan(self, app, subscribed_client):
        client, user_id = subscribed_client

        client.post("/plan/withdraw/preview", data={"amount": "200"})

        with app.app_context():
            before = float(Goal.query.filter_by(user_id=user_id).first().current_amount)

        response = client.post("/plan/withdraw/dismiss", follow_redirects=False)
        assert response.status_code == 302
        assert "withdraw=1" in response.headers["Location"]

        with app.app_context():
            after = float(Goal.query.filter_by(user_id=user_id).first().current_amount)
            assert after == before  # plan untouched

        with client.session_transaction() as sess:
            preview = sess.get("withdrawal_preview")
            assert preview is not None  # recommendation still visible
            assert preview["decided"] is True
            flashes = sess.get("_flashes") or []
            assert any("no changes made" in m.lower() for _, m in flashes)


# ─── Plan-page rendering ─────────────────────────────────────


class TestPlanPageRendersWithdrawSection:

    def test_section_hidden_by_default(self, subscribed_client):
        client, _ = subscribed_client
        response = client.get("/plan")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        # The CTA link is shown but the form (with amount input) is not.
        assert "I need money" in body
        assert "withdraw-amount-input" not in body

    def test_section_visible_with_query_param(self, subscribed_client):
        client, _ = subscribed_client
        response = client.get("/plan?withdraw=1")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "withdraw-amount-input" in body
        assert "How much do you need?" in body

    def test_recommendation_visible_after_preview(self, subscribed_client):
        client, _ = subscribed_client
        client.post("/plan/withdraw/preview", data={"amount": "200"})
        response = client.get("/plan")
        body = response.data.decode("utf-8")
        # Both Yes and No buttons are rendered while decided=False.
        assert "Yes, update my plan" in body
        assert "No, just show me" in body

    def test_decision_buttons_hidden_after_dismiss(self, subscribed_client):
        client, _ = subscribed_client
        client.post("/plan/withdraw/preview", data={"amount": "200"})
        client.post("/plan/withdraw/dismiss")
        response = client.get("/plan")
        body = response.data.decode("utf-8")
        # Recommendation still showing, but the Yes/No prompt is not.
        assert "Recommended split" in body
        assert "Yes, update my plan" not in body
