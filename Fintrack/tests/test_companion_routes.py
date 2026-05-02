"""
Companion service + route coverage:
 - hybrid routing (existing triggers + new distress markers + simple)
 - rate-limit kind discrimination, per-tier copy, UTC reset
 - effective-limit-key behaviour for trial vs paid
 - companion_rate_limit_hit event firing
 - model_routed property on companion_message_sent
 - rate-limit bubble rendering on the companion page
 - dev-only smoke test route returns 404 in non-debug mode
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app import db
from app.models.user import User
from app.services import companion_service
from app.services.companion_service import (
    HAIKU_MODEL,
    SONNET_MODEL,
    _effective_limit_key,
    _is_complex_query,
    _select_model,
    check_rate_limit,
    seconds_until_utc_midnight,
)


# ─── Fixtures ────────────────────────────────────────────────


def _make_companion_user(
    app,
    email="comp@test.com",
    password="testpassword123",
    tier="pro_plus",
    status="active",
    trial_days=14,
    messages_today=0,
):
    """User wired up so requires_subscription lets them through."""
    with app.app_context():
        user = User(email=email, name="Comp Tester")
        user.set_password(password)
        user.subscription_tier = tier
        user.subscription_status = status
        user.trial_ends_at = datetime.utcnow() + timedelta(days=trial_days)
        user.companion_messages_today = messages_today
        user.companion_last_reset = datetime.utcnow().date()
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def companion_client(app, client):
    user_id = _make_companion_user(app)
    client.post(
        "/api/auth/login",
        json={"email": "comp@test.com", "password": "testpassword123"},
    )
    return client, user_id


# ─── Hybrid classifier ────────────────────────────────────────


class TestClassifier:

    @pytest.mark.parametrize(
        "msg",
        [
            "What if I got a raise?",
            "Should I open a LISA?",
            "Can I afford a holiday in August?",
            "How long until my house deposit is funded?",
            "Help me decide between paying off the credit card or saving",
            "Compare my options here",
        ],
    )
    def test_existing_triggers_route_to_sonnet(self, msg):
        assert _is_complex_query(msg) is True
        assert _select_model(msg) == (SONNET_MODEL, "sonnet")

    @pytest.mark.parametrize(
        "msg",
        [
            "I just lost my job and don't know what to do.",
            "I can't afford rent this month.",
            "I'm struggling to make ends meet.",
            "I'm so worried about my finances.",
            "I'm anxious about money lately.",
            "Feeling really stressed.",
            "I'm scared I'll never save enough.",
            "I'm overwhelmed by all this.",
            "I think I'm in trouble with debt.",
            "I'm broke right now.",
            "I have no money left this month.",
            "I'm behind on my credit card payments.",
            "I missed a payment last month.",
        ],
    )
    def test_distress_markers_route_to_sonnet(self, msg):
        assert _is_complex_query(msg) is True
        assert _select_model(msg) == (SONNET_MODEL, "sonnet")

    @pytest.mark.parametrize(
        "msg",
        [
            "Hello",
            "Show me my plan",
            "Thanks",
            "Yes",
        ],
    )
    def test_simple_messages_route_to_haiku(self, msg):
        assert _is_complex_query(msg) is False
        assert _select_model(msg) == (HAIKU_MODEL, "haiku")


# ─── Effective limit key ─────────────────────────────────────


class TestEffectiveLimitKey:

    def test_trialing_status_overrides_plan_tier(self):
        user = SimpleNamespace(subscription_tier="pro", subscription_status="trialing")
        assert _effective_limit_key(user) == "trial"

    def test_active_paid_tier_uses_plan_tier(self):
        user = SimpleNamespace(subscription_tier="pro_plus", subscription_status="active")
        assert _effective_limit_key(user) == "pro_plus"

    def test_no_subscription_returns_free(self):
        user = SimpleNamespace(subscription_tier=None, subscription_status=None)
        assert _effective_limit_key(user) == "free"

    def test_uppercase_tier_is_lowercased(self):
        user = SimpleNamespace(subscription_tier="PRO_PLUS", subscription_status="active")
        assert _effective_limit_key(user) == "pro_plus"


# ─── Rate-limit logic ─────────────────────────────────────────


class TestCheckRateLimit:

    def test_free_tier_blocked_with_kind_free(self):
        user = SimpleNamespace(
            subscription_tier="free",
            subscription_status="none",
            companion_messages_today=0,
            companion_last_reset=date.today(),
        )
        allowed, reason, kind = check_rate_limit(user)
        assert allowed is False
        assert kind == "free"
        assert "Pro and above" in reason

    def test_pro_under_limit_is_allowed(self):
        user = SimpleNamespace(
            subscription_tier="pro",
            subscription_status="active",
            companion_messages_today=5,
            companion_last_reset=datetime.utcnow().date(),
        )
        allowed, reason, kind = check_rate_limit(user)
        assert allowed is True
        assert kind is None
        assert reason is None

    def test_pro_at_limit_returns_pro_copy(self):
        user = SimpleNamespace(
            subscription_tier="pro",
            subscription_status="active",
            companion_messages_today=10,
            companion_last_reset=datetime.utcnow().date(),
        )
        allowed, reason, kind = check_rate_limit(user)
        assert allowed is False
        assert kind == "rate_limit"
        assert "10 messages" in reason
        assert "Pro+" in reason

    def test_pro_plus_at_limit_returns_pro_plus_copy(self):
        user = SimpleNamespace(
            subscription_tier="pro_plus",
            subscription_status="active",
            companion_messages_today=30,
            companion_last_reset=datetime.utcnow().date(),
        )
        _, reason, kind = check_rate_limit(user)
        assert kind == "rate_limit"
        assert "30 messages" in reason
        assert "midnight UTC" in reason

    def test_joint_at_limit_returns_joint_copy(self):
        user = SimpleNamespace(
            subscription_tier="joint",
            subscription_status="active",
            companion_messages_today=50,
            companion_last_reset=datetime.utcnow().date(),
        )
        _, reason, kind = check_rate_limit(user)
        assert kind == "rate_limit"
        assert "50 messages" in reason

    def test_trial_at_limit_returns_trial_copy(self):
        user = SimpleNamespace(
            subscription_tier="pro",
            subscription_status="trialing",
            companion_messages_today=5,
            companion_last_reset=datetime.utcnow().date(),
        )
        _, reason, kind = check_rate_limit(user)
        assert kind == "rate_limit"
        assert "during your trial" in reason

    def test_resets_counter_on_new_utc_day(self):
        """When companion_last_reset is yesterday, the counter is wiped to 0
        and the user is allowed even if previously at the limit."""
        user = SimpleNamespace(
            subscription_tier="pro_plus",
            subscription_status="active",
            companion_messages_today=30,
            companion_last_reset=datetime.utcnow().date() - timedelta(days=1),
        )
        allowed, _, kind = check_rate_limit(user)
        assert allowed is True
        assert kind is None
        assert user.companion_messages_today == 0


class TestSecondsUntilUtcMidnight:

    def test_returns_positive_seconds_within_a_day(self):
        secs = seconds_until_utc_midnight()
        assert 0 < secs <= 24 * 3600

    def test_known_time_returns_known_seconds(self):
        # 23:00 UTC — one hour to midnight
        fake_now = datetime(2026, 5, 1, 23, 0, 0)
        secs = seconds_until_utc_midnight(now=fake_now)
        assert secs == 3600


# ─── Smoke test route ────────────────────────────────────────


class TestSmokeTestRoute:

    def test_returns_404_in_non_debug_mode(self, client):
        # TestingConfig has DEBUG=False so the route is never registered.
        response = client.get("/dev/companion-smoke-test")
        assert response.status_code == 404


# ─── Companion page rendering ────────────────────────────────


class TestCompanionPageRendersRateLimitBubble:

    def test_bubble_appears_when_limit_already_hit(self, app, client):
        """When a Pro+ user reloads the companion page after hitting their
        cap, the per-tier copy should render as an assistant chat bubble at
        the end of chat-messages, and the input zone should show the resume
        notice instead of the textarea."""
        user_id = _make_companion_user(app, tier="pro_plus", messages_today=30)
        client.post(
            "/api/auth/login",
            json={"email": "comp@test.com", "password": "testpassword123"},
        )
        response = client.get("/companion")
        assert response.status_code == 200
        body = response.data.decode("utf-8")
        assert "rate-limit-bubble" in body
        assert "midnight UTC" in body
        assert "Messaging resumes at midnight UTC" in body

    def test_bubble_absent_when_under_limit(self, app, client):
        _make_companion_user(app, tier="pro_plus", messages_today=5)
        client.post(
            "/api/auth/login",
            json={"email": "comp@test.com", "password": "testpassword123"},
        )
        response = client.get("/companion")
        body = response.data.decode("utf-8")
        # The bubble div is only rendered when limit is hit. The chat-input
        # textarea is only rendered when the user can still send. The
        # "Messaging resumes" string is always in the JS fallback so it's
        # not a useful absence check.
        assert 'id="rate-limit-bubble"' not in body
        assert 'id="chat-input"' in body


# ─── Event firing ────────────────────────────────────────────


class TestCompanionChatEvents:

    def test_rate_limit_hit_fires_event_with_tier_and_seconds(self, app, client):
        _make_companion_user(app, tier="pro_plus", messages_today=30)
        client.post(
            "/api/auth/login",
            json={"email": "comp@test.com", "password": "testpassword123"},
        )

        with patch("app.routes.companion_routes.track_event") as mock_track:
            response = client.post(
                "/api/companion/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == 429
        assert mock_track.called
        # Find the rate-limit-hit call (mock may have other calls)
        calls = [c for c in mock_track.call_args_list if c.args[1] == "companion_rate_limit_hit"]
        assert len(calls) == 1
        props = calls[0].args[2]
        assert props["tier"] == "pro_plus"
        assert isinstance(props["time_until_reset_seconds"], int)
        assert 0 < props["time_until_reset_seconds"] <= 24 * 3600

    def test_message_sent_event_includes_model_routed(self, app, client):
        _make_companion_user(app, tier="pro_plus", messages_today=0)
        client.post(
            "/api/auth/login",
            json={"email": "comp@test.com", "password": "testpassword123"},
        )

        fake_chat_result = {
            "response": "Hi there.",
            "model_used": "haiku",
            "tokens_in": 50,
            "tokens_out": 10,
            "error": None,
        }

        with patch(
            "app.routes.companion_routes.chat", return_value=fake_chat_result
        ), patch("app.routes.companion_routes.track_event") as mock_track:
            response = client.post(
                "/api/companion/chat",
                json={"message": "Hello"},
            )

        assert response.status_code == 200
        calls = [c for c in mock_track.call_args_list if c.args[1] == "companion_message_sent"]
        assert len(calls) == 1
        props = calls[0].args[2]
        assert props["model_routed"] == "haiku"
        assert props["tier"] == "pro_plus"

    def test_free_tier_block_does_not_fire_rate_limit_event(self, app, client):
        """Free-tier blocks are paywall events, not rate-limit events. The
        companion_rate_limit_hit event should only fire when the user has
        actually exhausted their daily allowance."""
        with app.app_context():
            user = User(email="freetier@test.com", name="Free Tester")
            user.set_password("testpassword123")
            user.subscription_tier = "free"
            user.subscription_status = "none"
            user.trial_ends_at = datetime.utcnow() - timedelta(days=1)
            db.session.add(user)
            db.session.commit()

        client.post(
            "/api/auth/login",
            json={"email": "freetier@test.com", "password": "testpassword123"},
        )

        # Free post-trial bounces off requires_subscription before reaching
        # the rate-limit check, so we expect a 302 redirect, not a 429.
        with patch("app.routes.companion_routes.track_event") as mock_track:
            response = client.post(
                "/api/companion/chat",
                json={"message": "Hello"},
            )

        rate_limit_calls = [
            c for c in mock_track.call_args_list
            if c.args[1] == "companion_rate_limit_hit"
        ]
        assert rate_limit_calls == []
        # Either redirected (requires_subscription) or 429 (rate limit) —
        # never a successful 200 for a free post-trial user.
        assert response.status_code != 200
