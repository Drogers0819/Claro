"""
Stripe webhook handler — regression coverage for SDK object access.

stripe.Webhook.construct_event() returns stripe.* SDK objects
(stripe.Event, stripe.Subscription, ...) which, since stripe-python v5+,
no longer expose dict.get(). The handler used to call event.get(...),
which raised `AttributeError: get` on every live webhook (500s in Render
logs for checkout.session.completed and invoice.paid).

These tests construct *real* stripe.Event SDK objects via
stripe.Event.construct_from(...) and run them through _handle_event to
prove no AttributeError is raised and that user state is updated. Every
Stripe SDK network call (Subscription.retrieve) is mocked — no real
network traffic from this suite.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import stripe

from app import db
from app.models.user import User
from app.routes import billing_routes


# ─── Helpers ─────────────────────────────────────────────────


def _make_user(
    app,
    email="webhook@test.com",
    name="Webhooker",
    *,
    tier="free",
    status="active",
    stripe_subscription_id="sub_test_abc",
    stripe_customer_id="cus_test_xyz",
):
    with app.app_context():
        user = User(email=email, name=name)
        user.set_password("testpassword123")
        user.monthly_income = Decimal("2500")
        user.subscription_tier = tier
        user.subscription_status = status
        user.stripe_subscription_id = stripe_subscription_id
        user.stripe_customer_id = stripe_customer_id
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        db.session.add(user)
        db.session.commit()
        return user.id


def _event(event_type, obj, *, previous_attributes=None, event_id="evt_test_001"):
    """Build a real stripe.Event SDK object, like construct_event() returns."""
    payload = {
        "id": event_id,
        "type": event_type,
        "data": {"object": obj},
    }
    if previous_attributes is not None:
        payload["data"]["previous_attributes"] = previous_attributes
    return stripe.Event.construct_from(payload, "sk_test_dummy")


# ─── The regression these tests guard against ────────────────


class TestWebhookEventAccessPattern:
    """Each handled event type, fed a real stripe.Event SDK object,
    must run through _handle_event without raising AttributeError."""

    def test_event_object_has_no_dict_get(self):
        """Documents the root cause: stripe.Event is not dict-like."""
        event = _event("invoice.paid", {"id": "in_1", "customer": "cus_test_xyz"})
        assert not hasattr(event, "get")
        # Attribute and subscript access both work, .get() does not.
        assert event.type == "invoice.paid"
        assert event["type"] == "invoice.paid"

    def test_checkout_session_completed(self, app):
        uid = _make_user(app)
        sub_obj = stripe.Subscription.construct_from(
            {"id": "sub_test_abc", "items": {"data": [{"price": {"id": "price_x"}}]}},
            "sk_test_dummy",
        )
        event = _event(
            "checkout.session.completed",
            {
                "id": "cs_test_1",
                "customer": "cus_test_xyz",
                "subscription": "sub_test_abc",
                "metadata": {"user_id": str(uid)},
            },
        )
        with app.app_context():
            with patch("stripe.Subscription.retrieve", return_value=sub_obj), \
                 patch("app.routes.billing_routes.tier_for_price_id", return_value="pro"), \
                 patch("app.services.analytics_service.track_event"):
                # Must not raise AttributeError.
                billing_routes._handle_event(event)
            user = db.session.get(User, uid)
            assert user.subscription_status == "trialing"
            assert user.stripe_subscription_id == "sub_test_abc"
            assert user.subscription_tier == "pro"

    def test_customer_subscription_updated(self, app):
        uid = _make_user(app)
        event = _event(
            "customer.subscription.updated",
            {
                "id": "sub_test_abc",
                "customer": "cus_test_xyz",
                "status": "active",
                "pause_collection": None,
                "items": {"data": [{"price": {"id": "price_y"}}]},
            },
            previous_attributes={"status": "trialing"},
        )
        with app.app_context():
            with patch("app.routes.billing_routes.tier_for_price_id", return_value="pro_plus"):
                billing_routes._handle_event(event)
            user = db.session.get(User, uid)
            assert user.subscription_status == "active"
            assert user.subscription_tier == "pro_plus"

    def test_subscription_updated_auto_resume_dispatch(self, app):
        """pause_collection clearing from previous_attributes must reach
        the resume handler — read off a real SDK event object."""
        uid = _make_user(app)
        event = _event(
            "customer.subscription.updated",
            {
                "id": "sub_test_abc",
                "customer": "cus_test_xyz",
                "status": "active",
                "pause_collection": None,
                "items": {"data": []},
            },
            previous_attributes={"pause_collection": {"behavior": "void", "resumes_at": 1234567890}},
            event_id="evt_resume_1",
        )
        with app.app_context():
            with patch("app.services.pause_service.handle_scheduled_resume_webhook") as resume, \
                 patch("app.services.analytics_service.track_event"):
                billing_routes._handle_event(event)
            resume.assert_called_once()
            # stripe_event_id read off the SDK object, not a dict.
            assert resume.call_args.args[1] == "evt_resume_1"

    def test_customer_subscription_deleted(self, app):
        uid = _make_user(app, tier="pro", status="active")
        event = _event(
            "customer.subscription.deleted",
            {"id": "sub_test_abc", "customer": "cus_test_xyz"},
        )
        with app.app_context():
            with patch("app.services.analytics_service.track_event"):
                billing_routes._handle_event(event)
            user = db.session.get(User, uid)
            assert user.subscription_tier == "free"
            assert user.subscription_status == "canceled"
            assert user.stripe_subscription_id is None

    def test_invoice_paid(self, app):
        uid = _make_user(app, status="past_due")
        event = _event("invoice.paid", {"id": "in_1", "customer": "cus_test_xyz"})
        with app.app_context():
            billing_routes._handle_event(event)
            user = db.session.get(User, uid)
            assert user.subscription_status == "active"

    def test_invoice_payment_failed(self, app):
        uid = _make_user(app, status="active")
        event = _event("invoice.payment_failed", {"id": "in_2", "customer": "cus_test_xyz"})
        with app.app_context():
            billing_routes._handle_event(event)
            user = db.session.get(User, uid)
            assert user.subscription_status == "past_due"

    def test_unhandled_event_type_is_noop(self, app):
        """An event type we don't dispatch must not raise."""
        event = _event("customer.created", {"id": "cus_test_xyz"})
        with app.app_context():
            billing_routes._handle_event(event)  # no raise == pass

    def test_checkout_missing_optional_fields(self, app):
        """A checkout event with no subscription/metadata must not raise
        on absent SDK attributes (getattr/subscript safety)."""
        _make_user(app)
        event = _event(
            "checkout.session.completed",
            {"id": "cs_test_2", "customer": "cus_test_xyz"},
        )
        with app.app_context():
            with patch("app.services.analytics_service.track_event"):
                billing_routes._handle_event(event)  # no AttributeError == pass
