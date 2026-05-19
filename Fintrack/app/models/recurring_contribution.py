"""
RecurringContribution — one row per chip-level contribution on factfind.

Today's factfind sums sub-chips (Netflix, LISA, Childcare, etc.)
client-side in JavaScript and POSTs a single scalar per source
(`subscriptions_total`, `other_commitments`). Chip identity is lost
the moment the form submits.

This model fixes that: each chip-selection persists as a row, with
optional linkage to a Goal (`linked_goal_id`). The existing scalar
columns on User stay as cached aggregates — populated automatically
when the sync service writes rows — so the 12+ downstream consumers
of the scalars continue working unchanged.

source
------
"subscriptions" | "other_commitments". Mirrors which factfind section
the chip came from. Drives which User column the cached aggregate is
written back to.

chip_id
-------
Standard chip's internal ID ("lisa", "netflix", "childcare", ...) for
chips that match the predefined catalogue. NULL for user-typed custom
entries — those carry their identity in `label`.

label
-----
Human-readable label. For standard chips, the catalogue's display
label (e.g. "LISA contributions"). For custom entries, the user's
own text.

linked_goal_id
--------------
Optional FK to a Goal. When set, the contribution appears in the
"Towards your goals" subsection of the Overview commitments panel
and is mentioned in the companion's context as "{label} → {goal name}".
When NULL, the contribution stays in the Estimated Spend section.
ON DELETE SET NULL — deleting a goal unlinks any contributions it had.
"""

from datetime import datetime

from app import db


SOURCE_SUBSCRIPTIONS = "subscriptions"
SOURCE_OTHER_COMMITMENTS = "other_commitments"
VALID_SOURCES = (SOURCE_SUBSCRIPTIONS, SOURCE_OTHER_COMMITMENTS)


class RecurringContribution(db.Model):
    __tablename__ = "recurring_contributions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source = db.Column(db.String(40), nullable=False, index=True)

    # NULL for user-typed custom entries.
    chip_id = db.Column(db.String(60), nullable=True)
    label = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)

    linked_goal_id = db.Column(
        db.Integer,
        db.ForeignKey("goals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "recurring_contributions",
            lazy=True,
            cascade="all, delete-orphan",
            passive_deletes=True,
        ),
    )
    linked_goal = db.relationship("Goal", lazy=True)

    __table_args__ = (
        db.Index(
            "ix_recurring_contributions_user_source",
            "user_id", "source",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "source": self.source,
            "chip_id": self.chip_id,
            "label": self.label,
            "amount": float(self.amount) if self.amount is not None else None,
            "linked_goal_id": self.linked_goal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self):
        chip = self.chip_id or "<custom>"
        return (
            f"<RecurringContribution {self.id}: "
            f"user={self.user_id} source={self.source} chip={chip} "
            f"label={self.label!r} amount={self.amount}>"
        )
