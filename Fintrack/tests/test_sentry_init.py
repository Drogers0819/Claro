"""Tests for Sentry error-monitoring init and the gated debug route.

The contracts that matter for beta:
  1. The app starts cleanly with NO DSN — protects local dev and CI. This
     is the most important guarantee: a broken Sentry init must never break
     the app for developers who don't have (or want) a DSN.
  2. The app starts cleanly with a DSN set.
  3. `before_send` strips known sensitive fields from an event.
  4. `/debug/sentry-test` is 404 unless SENTRY_DEBUG_ENABLED=1.
  5. `/debug/sentry-test` raises when SENTRY_DEBUG_ENABLED=1.
"""

import pytest

from app import create_app
from app.observability import (
    _REDACTED,
    _key_is_sensitive,
    before_send,
    init_sentry,
)
from config import TestingConfig


@pytest.fixture
def _restore_sentry():
    """Reset the global Sentry client after a test that initialises it, so
    one test's DSN doesn't leak an active client into the rest of the suite.
    Re-initialising with an empty DSN deactivates the SDK."""
    yield
    import sentry_sdk

    sentry_sdk.init(dsn="")


class TestSentryInitNoOp:

    def test_app_starts_cleanly_without_dsn(self, monkeypatch):
        """Most important: no DSN → app builds, no Sentry, no crash."""
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        app = create_app(TestingConfig)
        assert app is not None
        # The factory ran end-to-end; a route is reachable.
        assert app.test_client().get("/").status_code in (200, 302, 404)

    def test_init_sentry_returns_false_without_dsn(self, monkeypatch):
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        assert init_sentry() is False

    def test_init_sentry_returns_false_for_blank_dsn(self, monkeypatch):
        """A DSN of whitespace is treated as unset, not a malformed DSN."""
        monkeypatch.setenv("SENTRY_DSN", "   ")
        assert init_sentry() is False


class TestSentryInitWithDsn:

    def test_app_starts_cleanly_with_dummy_dsn(self, monkeypatch, _restore_sentry):
        """A well-formed dummy DSN → app builds and Sentry initialises. No
        event is sent because we never trigger an error here."""
        monkeypatch.setenv(
            "SENTRY_DSN", "https://examplekey@o0.ingest.sentry.io/0"
        )
        app = create_app(TestingConfig)
        assert app is not None
        assert app.test_client().get("/").status_code in (200, 302, 404)

    def test_init_sentry_returns_true_with_dummy_dsn(
        self, monkeypatch, _restore_sentry
    ):
        monkeypatch.setenv(
            "SENTRY_DSN", "https://examplekey@o0.ingest.sentry.io/0"
        )
        assert init_sentry() is True


class TestBeforeSendScrubbing:

    def test_strips_all_known_sensitive_keys(self):
        """Every secret/PII field is redacted wherever it appears in the
        event — request data, stack-frame locals, and `extra`."""
        event = {
            "request": {
                "data": {
                    "email": "user@example.com",
                    "password": "hunter2",
                    "csrf_token": "abc123",
                },
                "cookies": {"session": "secret-session-value"},
                "headers": {
                    "Cookie": "session=secret-session-value",
                    "Authorization": "Bearer tok",
                    "User-Agent": "pytest",
                },
            },
            "extra": {
                "stripe_secret_key": "sk_live_xxx",
                "anthropic_api_key": "sk-ant-xxx",
                "password_hash": "$2b$12$...",
            },
            "exception": {
                "values": [
                    {
                        "stacktrace": {
                            "frames": [
                                {
                                    "vars": {
                                        "password": "leaked",
                                        "amount": "100.00",
                                    }
                                }
                            ]
                        }
                    }
                ]
            },
        }

        scrubbed = before_send(event, {})

        # Sensitive values redacted...
        assert scrubbed["request"]["data"]["password"] == _REDACTED
        assert scrubbed["request"]["data"]["csrf_token"] == _REDACTED
        assert scrubbed["request"]["data"]["email"] == _REDACTED  # PII
        # The "cookies" container key itself matches "cookie", so the whole
        # cookies dict (session value included) is redacted wholesale.
        assert scrubbed["request"]["cookies"] == _REDACTED
        assert scrubbed["request"]["headers"]["Cookie"] == _REDACTED
        assert scrubbed["request"]["headers"]["Authorization"] == _REDACTED
        assert scrubbed["extra"]["stripe_secret_key"] == _REDACTED
        assert scrubbed["extra"]["anthropic_api_key"] == _REDACTED
        assert scrubbed["extra"]["password_hash"] == _REDACTED
        frame_vars = scrubbed["exception"]["values"][0]["stacktrace"]["frames"][0][
            "vars"
        ]
        assert frame_vars["password"] == _REDACTED

        # ...non-sensitive values preserved.
        assert scrubbed["request"]["headers"]["User-Agent"] == "pytest"
        assert frame_vars["amount"] == "100.00"

    def test_strips_pii_substring_variants(self):
        """PII is matched as a case-insensitive SUBSTRING, so prefixed and
        suffixed variants are all caught — not just exact key names."""
        event = {
            "extra": {
                "customer_email": "a@b.com",
                "user_email": "c@d.com",
                "full_name": "Ada Lovelace",
                "first_name": "Ada",
                "last_name": "Lovelace",
                "remote_ip": "1.2.3.4",
                "client_ip": "5.6.7.8",
                "ip_address": "9.10.11.12",
                "x_forwarded_for": "1.1.1.1",
                # non-PII control values that must survive
                "transaction_id": "txn_123",
                "amount": "42.00",
            }
        }
        scrubbed = before_send(event, {})["extra"]

        for redacted_key in (
            "customer_email",
            "user_email",
            "full_name",
            "first_name",
            "last_name",
            "remote_ip",
            "client_ip",
            "ip_address",
            "x_forwarded_for",
        ):
            assert scrubbed[redacted_key] == _REDACTED, redacted_key

        assert scrubbed["transaction_id"] == "txn_123"
        assert scrubbed["amount"] == "42.00"

    def test_matching_is_case_insensitive(self):
        event = {
            "extra": {
                "PASSWORD": "x",
                "Stripe_Secret_Key": "y",
                "Customer_Email": "z@z.com",
                "First_Name": "Grace",
            }
        }
        scrubbed = before_send(event, {})["extra"]
        assert scrubbed["PASSWORD"] == _REDACTED
        assert scrubbed["Stripe_Secret_Key"] == _REDACTED
        assert scrubbed["Customer_Email"] == _REDACTED
        assert scrubbed["First_Name"] == _REDACTED

    def test_handles_lists_and_scalars(self):
        """Lists are walked element-wise; a non-dict event passes through."""
        event = {"breadcrumbs": [{"data": {"password": "x"}}, {"data": {"ok": 1}}]}
        scrubbed = before_send(event, {})
        assert scrubbed["breadcrumbs"][0]["data"]["password"] == _REDACTED
        assert scrubbed["breadcrumbs"][1]["data"]["ok"] == 1

    def test_spec_and_pii_fields_are_all_covered(self):
        """Guard against someone trimming the matcher: every field the spec
        and the PII follow-up require must be flagged sensitive."""
        for field in (
            # original spec set
            "password",
            "password_hash",
            "stripe_secret_key",
            "anthropic_api_key",
            "csrf_token",
            "session",
            # session cookie value also rides in the Cookie header
            "Cookie",
            "Set-Cookie",
            "Authorization",
            # PII follow-up — substring variants
            "email",
            "customer_email",
            "full_name",
            "first_name",
            "last_name",
            "remote_ip",
            "client_ip",
            "ip_address",
            "x_forwarded_for",
        ):
            assert _key_is_sensitive(field), field

    def test_non_sensitive_keys_pass_through(self):
        for field in ("amount", "transaction_id", "category", "status", "url"):
            assert not _key_is_sensitive(field), field


class TestDebugSentryRoute:

    def test_route_is_404_when_flag_unset(self, monkeypatch):
        monkeypatch.delenv("SENTRY_DEBUG_ENABLED", raising=False)
        app = create_app(TestingConfig)
        resp = app.test_client().get("/debug/sentry-test")
        assert resp.status_code == 404

    def test_route_is_404_when_flag_not_one(self, monkeypatch):
        """Only the literal "1" enables the route; "0"/"true" do not."""
        monkeypatch.setenv("SENTRY_DEBUG_ENABLED", "0")
        app = create_app(TestingConfig)
        resp = app.test_client().get("/debug/sentry-test")
        assert resp.status_code == 404

    def test_route_raises_when_flag_enabled(self, monkeypatch):
        """With the flag on, the route raises so Sentry can capture it.
        Under TESTING the exception propagates to the caller."""
        monkeypatch.setenv("SENTRY_DEBUG_ENABLED", "1")
        app = create_app(TestingConfig)
        with pytest.raises(RuntimeError, match="Sentry verification test"):
            app.test_client().get("/debug/sentry-test")
