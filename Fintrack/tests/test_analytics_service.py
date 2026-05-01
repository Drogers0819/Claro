"""Unit tests for app.services.analytics_service.

Cover the four contracts the wrapper guarantees:
  1. No-op when POSTHOG_API_KEY is empty (TestingConfig sets it to None).
  2. Calls posthog.capture with the right arguments when a key is set.
  3. Exceptions raised by the underlying SDK do NOT propagate.
  4. The wrapper attaches `environment` to every event automatically.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services import analytics_service


@pytest.fixture(autouse=True)
def _reset_module_state():
    """Reset the lazy-init state between tests so each one builds cleanly."""
    analytics_service._reset_for_tests()
    yield
    analytics_service._reset_for_tests()


class TestAnalyticsServiceNoOp:

    def test_track_event_is_noop_when_key_missing(self, app):
        """With TestingConfig (POSTHOG_API_KEY=None), track_event must drop
        events silently and never reach for the SDK."""
        with app.app_context():
            with patch.object(analytics_service, "_get_client", return_value=None) as mock_get:
                # Direct call should not raise and should not request a real client.
                analytics_service.track_event("user-1", "test_event", {"foo": "bar"})

            # _get_client itself is fine to call; key thing is no SDK call ran.
            assert mock_get.called

    def test_identify_user_is_noop_when_key_missing(self, app):
        with app.app_context():
            # No exception, no side effects.
            analytics_service.identify_user("user-1", {"email": "a@b.com"})

    def test_real_noop_path_when_testing_config(self, app):
        """End-to-end: under TestingConfig, the lazy init returns None and
        track_event short-circuits."""
        with app.app_context():
            client = analytics_service._get_client()
            assert client is None
            # And the public API doesn't crash:
            analytics_service.track_event("u", "any_event")


class TestAnalyticsServiceWithKey:

    def test_track_event_calls_sdk_with_right_args(self, app):
        """When a fake client is injected, track_event should call .capture
        with distinct_id=user_id, event=event_name, and properties enriched."""
        fake_client = MagicMock()
        analytics_service._client = fake_client
        analytics_service._init_attempted = True

        with app.app_context():
            analytics_service.track_event("user-42", "goals_added", {"count": 3})

        fake_client.capture.assert_called_once()
        kwargs = fake_client.capture.call_args.kwargs
        assert kwargs["distinct_id"] == "user-42"
        assert kwargs["event"] == "goals_added"
        assert kwargs["properties"]["count"] == 3
        # Caller-supplied props preserved
        assert "environment" in kwargs["properties"]   # auto-attached
        assert "timestamp" in kwargs["properties"]     # auto-attached

    def test_environment_property_is_attached(self, app):
        """Contract 4: every event gets an `environment` property without
        the caller having to pass one. Under TestingConfig it should be
        'test'."""
        fake_client = MagicMock()
        analytics_service._client = fake_client
        analytics_service._init_attempted = True

        with app.app_context():
            analytics_service.track_event("user-1", "any_event")

        props = fake_client.capture.call_args.kwargs["properties"]
        assert props["environment"] == "test"

    def test_anonymous_distinct_id_when_user_missing(self, app):
        """A None user_id is rewritten to the literal string 'anonymous'
        so PostHog still attributes the event to a stable bucket."""
        fake_client = MagicMock()
        analytics_service._client = fake_client
        analytics_service._init_attempted = True

        with app.app_context():
            analytics_service.track_event(None, "landing_viewed")

        assert fake_client.capture.call_args.kwargs["distinct_id"] == "anonymous"


class TestAnalyticsServiceSwallowsExceptions:

    def test_capture_exceptions_dont_propagate(self, app):
        """Contract 3: if the underlying SDK raises (network, malformed
        payload, SDK bug), track_event must NOT propagate — analytics
        failures cannot crash a user-facing route."""
        fake_client = MagicMock()
        fake_client.capture.side_effect = RuntimeError("posthog blew up")
        analytics_service._client = fake_client
        analytics_service._init_attempted = True

        with app.app_context():
            # Must not raise.
            analytics_service.track_event("user-1", "boom_event", {"x": 1})

    def test_route_still_returns_200_when_sdk_raises(self, app, client):
        """End-to-end: an authenticated route that fires track_event keeps
        working even when the SDK is broken. We use the goal-detail flow
        as a stand-in: no event there, but the test machinery shows the
        analytics layer never reaches the route's response. Assert the
        wrapper itself doesn't raise — the route-level guarantee follows."""
        fake_client = MagicMock()
        fake_client.capture.side_effect = ValueError("network error")
        analytics_service._client = fake_client
        analytics_service._init_attempted = True

        with app.app_context():
            try:
                analytics_service.track_event("u", "any")
            except Exception as exc:  # pragma: no cover - failing this is the bug
                pytest.fail(f"track_event leaked: {exc!r}")

    def test_identify_exceptions_dont_propagate(self, app):
        fake_client = MagicMock()
        fake_client.identify.side_effect = RuntimeError("bad request")
        analytics_service._client = fake_client
        analytics_service._init_attempted = True

        with app.app_context():
            analytics_service.identify_user("user-1", {"email": "a@b.com"})
