from app import db
from datetime import date


class CheckIn(db.Model):
    __tablename__ = "checkins"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    completed_at = db.Column(db.DateTime, server_default=db.func.now())

    # Snapshot of plan state at check-in time
    surplus_at_checkin = db.Column(db.Numeric(10, 2), nullable=True)
    phase_at_checkin = db.Column(db.Integer, nullable=True)

    # Relationships
    entries = db.relationship("CheckInEntry", backref="checkin", lazy=True,
                              cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "month": self.month,
            "year": self.year,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "surplus_at_checkin": float(self.surplus_at_checkin) if self.surplus_at_checkin else None,
            "phase_at_checkin": self.phase_at_checkin,
            "entries": [e.to_dict() for e in self.entries]
        }

    def __repr__(self):
        return f"<CheckIn {self.id}: {self.month}/{self.year}>"


class CheckInEntry(db.Model):
    __tablename__ = "checkin_entries"

    id = db.Column(db.Integer, primary_key=True)
    checkin_id = db.Column(db.Integer, db.ForeignKey("checkins.id"), nullable=False)
    goal_id = db.Column(db.Integer, db.ForeignKey("goals.id"), nullable=True)
    pot_name = db.Column(db.String(255), nullable=False)
    planned_amount = db.Column(db.Numeric(10, 2), nullable=False)
    actual_amount = db.Column(db.Numeric(10, 2), nullable=False)
    note = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "goal_id": self.goal_id,
            "pot_name": self.pot_name,
            "planned_amount": float(self.planned_amount),
            "actual_amount": float(self.actual_amount),
            "difference": round(float(self.actual_amount) - float(self.planned_amount), 2),
            "note": self.note
        }