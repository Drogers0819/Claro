"""
SubscriptionEvent — Block 2 Task 2.6.

One row per pause-related state change on a Stripe subscription:
manual pause requests, scheduled auto-resumes, manual resumes,
failed pause attempts. The audit table answers "what happened to
this user's subscription, and when" without trawling Stripe events.

Idempotency
-----------
The unique constraint on stripe_event_id is the load-bearing piece.
Stripe sometimes delivers the same webhook twice — the duplicate
INSERT raises IntegrityError and the webhook handler treats that
as "already processed" rather than re-running the state mutation.

Schema choice
-------------
metadata_json is a plain Text column rather than a JSON / JSONB
type so the same model boots cleanly on SQLite locally and Postgres
in production. Volume is low and we never query into the JSON; we
only read it when manually inspecting an audit trail.
"""

from datetime import datetime

from app import db


class SubscriptionEvent(db.Model):
    __tablename__ = "subscription_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "paused" | "resumed_scheduled" | "resumed_manual" | "pause_failed"
    event_type = db.Column(db.String(40), nullable=False)

    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    # Idempotency anchor for webhook deliveries. Manual events leave
    # this NULL; the unique constraint accepts multiple NULLs in both
    # SQLite and Postgres.
    stripe_event_id = db.Column(db.String(100), nullable=True)

    pause_duration_days = db.Column(db.Integer, nullable=True)
    pause_started_at = db.Column(db.DateTime, nullable=True)
    pause_ends_at = db.Column(db.DateTime, nullable=True)

    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship(
        "User", backref=db.backref(
            "subscription_events", lazy=True,
            cascade="all, delete-orphan", passive_deletes=True,
        ),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "stripe_event_id",
            name="uq_subscription_events_stripe_event_id",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "stripe_subscription_id": self.stripe_subscription_id,
            "stripe_event_id": self.stripe_event_id,
            "pause_duration_days": self.pause_duration_days,
            "pause_started_at": self.pause_started_at.isoformat() if self.pause_started_at else None,
            "pause_ends_at": self.pause_ends_at.isoformat() if self.pause_ends_at else None,
            "metadata_json": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<SubscriptionEvent {self.id}: {self.event_type} user={self.user_id}>"
