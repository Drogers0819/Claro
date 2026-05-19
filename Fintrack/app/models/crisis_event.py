from datetime import datetime

from app import db


class CrisisEvent(db.Model):
    """One row per crisis-flow submission.

    Multi-purpose: lost-income, unexpected-cost, and pause-requested
    events all share this table. The `event_type` column discriminates;
    only the columns relevant to that type are populated. Keeping
    everything in one table makes the support / analytics queries trivial
    ("show me everything that's happened to user X") at the cost of some
    NULLs per row, which is fine at the scale of crisis events.

    The pause-requested type stores no extra data — the row exists so
    support has a record when the user emails in. Tasks 2.5 and 2.6 will
    add resolution tooling that updates `resolved_at` / `resolution_notes`.
    """

    __tablename__ = "crisis_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # "lost_income" | "unexpected_cost" | "pause_requested"
    event_type = db.Column(db.String(20), nullable=False)

    # lost_income only
    income_change_type = db.Column(db.String(30), nullable=True)
    new_monthly_income = db.Column(db.Numeric(10, 2), nullable=True)
    income_unknown = db.Column(db.Boolean, default=False)

    # unexpected_cost only
    cost_description = db.Column(db.String(200), nullable=True)
    cost_amount = db.Column(db.Numeric(10, 2), nullable=True)
    cost_already_paid = db.Column(db.Boolean, nullable=True)

    occurred_on = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Reserved for Tasks 2.5 / 2.6 — manual resolution by support, then
    # later automated resolution from survival mode and hardship pause.
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    user = db.relationship(
        "User", backref=db.backref(
            "crisis_events", lazy=True,
            cascade="all, delete-orphan", passive_deletes=True,
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "income_change_type": self.income_change_type,
            "new_monthly_income": float(self.new_monthly_income) if self.new_monthly_income is not None else None,
            "income_unknown": bool(self.income_unknown) if self.income_unknown is not None else None,
            "cost_description": self.cost_description,
            "cost_amount": float(self.cost_amount) if self.cost_amount is not None else None,
            "cost_already_paid": self.cost_already_paid,
            "occurred_on": self.occurred_on.isoformat() if self.occurred_on else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
        }

    def __repr__(self):
        return f"<CrisisEvent {self.id}: {self.event_type} user={self.user_id}>"
