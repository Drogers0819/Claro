from app import db, bcrypt, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Financial profile
    monthly_income = db.Column(db.Numeric(10, 2), nullable=True)
    rent_amount = db.Column(db.Numeric(10, 2), nullable=True)
    bills_amount = db.Column(db.Numeric(10, 2), nullable=True)
    groceries_estimate = db.Column(db.Numeric(10, 2), nullable=True)
    transport_estimate = db.Column(db.Numeric(10, 2), nullable=True)
    subscriptions_total = db.Column(db.Numeric(10, 2), nullable=True)
    other_commitments = db.Column(db.Numeric(10, 2), nullable=True)
    lifestyle_budget = db.Column(db.Numeric(10, 2), nullable=True)
    income_day = db.Column(db.Integer, nullable=True)
    payday_notification_last_sent = db.Column(db.Date, nullable=True)
    checkin_reminder_1_sent = db.Column(db.Date, nullable=True)
    checkin_reminder_2_sent = db.Column(db.Date, nullable=True)
    checkin_reminder_3_sent = db.Column(db.Date, nullable=True)
    survival_mode_active = db.Column(db.Boolean, default=False, nullable=False)
    survival_mode_started_at = db.Column(db.DateTime, nullable=True)
    subscription_paused_until = db.Column(db.DateTime, nullable=True)
    last_pause_started_at = db.Column(db.DateTime, nullable=True)
    starting_net_worth = db.Column(db.Numeric(12, 2), nullable=True)
    employment_type = db.Column(db.String(30), default="full_time")
    factfind_completed = db.Column(db.Boolean, default=False)
    plan_wizard_complete = db.Column(db.Boolean, default=False)

    skip_emergency_fund = db.Column(db.Boolean, default=False)
    # Subscription
    subscription_tier = db.Column(db.String(20), default="free")
    subscription_status = db.Column(db.String(30), default="none")
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    stripe_customer_id = db.Column(db.String(255), nullable=True)
    stripe_subscription_id = db.Column(db.String(255), nullable=True)
    companion_messages_today = db.Column(db.Integer, default=0)
    companion_last_reset = db.Column(db.Date, nullable=True)
    last_life_checkin = db.Column(db.Date, nullable=True)

    # Preferences
    theme = db.Column(db.String(30), default="obsidian-vault")

    # Relationships — DB-level ON DELETE CASCADE handles the delete in
    # production Postgres; passive_deletes=True tells SQLAlchemy to defer
    # to the database rather than emit per-row DELETEs.
    transactions = db.relationship(
        "Transaction", backref="user", lazy=True,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    goals = db.relationship(
        "Goal", backref="user", lazy=True,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    budgets = db.relationship(
        "Budget", backref="user", lazy=True,
        cascade="all, delete-orphan", passive_deletes=True,
    )
    checkins = db.relationship(
        "CheckIn", backref="user", lazy=True,
        cascade="all, delete-orphan", passive_deletes=True,
    )

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    @property
    def fixed_commitments(self):
        rent = float(self.rent_amount) if self.rent_amount else 0
        bills = float(self.bills_amount) if self.bills_amount else 0
        return rent + bills

    @property
    def total_essentials(self):
        rent = float(self.rent_amount) if self.rent_amount else 0
        bills = float(self.bills_amount) if self.bills_amount else 0
        groceries = float(self.groceries_estimate) if self.groceries_estimate else 0
        transport = float(self.transport_estimate) if self.transport_estimate else 0
        subs = float(self.subscriptions_total) if self.subscriptions_total else 0
        other = float(self.other_commitments) if self.other_commitments else 0
        return rent + bills + groceries + transport + subs + other

    @property
    def monthly_surplus(self):
        income = float(self.monthly_income) if self.monthly_income else 0
        return income - self.fixed_commitments
    @property
    def tier(self):
        tier_labels = {
            "free": "Claro Free",
            "pro": "Claro Plan",
            "pro_plus": "Claro Coach",
            "joint": "Claro Duo"
        }
        return tier_labels.get(self.subscription_tier, "Claro Free")

    @property
    def daily_message_limit(self):
        limits = {"free": 0, "pro": 10, "pro_plus": 30, "joint": 50}
        return limits.get(self.subscription_tier, 0)

    def profile_dict(self):
        return {
            "monthly_income": float(self.monthly_income) if self.monthly_income else None,
            "rent_amount": float(self.rent_amount) if self.rent_amount else None,
            "bills_amount": float(self.bills_amount) if self.bills_amount else None,
            "groceries_estimate": float(self.groceries_estimate) if self.groceries_estimate else None,
            "transport_estimate": float(self.transport_estimate) if self.transport_estimate else None,
            "subscriptions_total": float(self.subscriptions_total) if self.subscriptions_total else None,
            "other_commitments": float(self.other_commitments) if self.other_commitments else None,
            "lifestyle_budget": float(self.lifestyle_budget) if self.lifestyle_budget else None,
            "income_day": self.income_day,
            "employment_type": self.employment_type or "full_time",
            "variable_income": (self.employment_type or "full_time") != "full_time",
            "fixed_commitments": self.fixed_commitments,
            "total_essentials": self.total_essentials,
            "monthly_surplus": self.monthly_surplus,
            "factfind_completed": self.factfind_completed,
            "plan_wizard_complete": self.plan_wizard_complete,
            "theme": self.theme,
            "survival_mode_active": bool(self.survival_mode_active),
        }

    # ─── Whisper helpers (Block 1: Today's Whisper) ────────────────
    # Used by app/services/whisper_service.py to pick a contextual
    # sentence for the user's current state. Each helper is defensive
    # against missing data and never raises.

    def has_active_credit_card_goal_completing_soon(self):
        """True if any active goal whose name contains 'credit card'
        will finish within ~6 months at the current monthly allocation."""
        from app.models.goal import Goal
        goals = Goal.query.filter_by(user_id=self.id, status="active").all()
        for goal in goals:
            name = (goal.name or "").lower()
            if "credit card" not in name:
                continue
            target = float(goal.target_amount or 0)
            current = float(goal.current_amount or 0)
            allocation = float(goal.monthly_allocation or 0)
            if target <= 0 or allocation <= 0:
                continue
            remaining = target - current
            if remaining <= 0:
                continue
            months_left = remaining / allocation
            if months_left < 6:
                return True
        return False

    def get_credit_card_goal_completing_soon(self):
        """Return (months_left, monthly_amount) for the soonest-completing
        credit-card goal, or None. Used to populate whisper templates."""
        from app.models.goal import Goal
        candidates = []
        goals = Goal.query.filter_by(user_id=self.id, status="active").all()
        for goal in goals:
            name = (goal.name or "").lower()
            if "credit card" not in name:
                continue
            target = float(goal.target_amount or 0)
            current = float(goal.current_amount or 0)
            allocation = float(goal.monthly_allocation or 0)
            if target <= 0 or allocation <= 0:
                continue
            remaining = target - current
            if remaining <= 0:
                continue
            months_left = remaining / allocation
            if months_left < 6:
                candidates.append((months_left, allocation))
        if not candidates:
            return None
        candidates.sort(key=lambda c: c[0])
        return candidates[0]

    def is_ahead_of_savings_target(self):
        """True if each of the user's last 2 CheckIn rows totalled
        contributions >= planned. Quiet streak — quietly noticing."""
        from app.models.checkin import CheckIn
        recent = (
            CheckIn.query.filter_by(user_id=self.id)
            .order_by(CheckIn.year.desc(), CheckIn.month.desc())
            .limit(2)
            .all()
        )
        if len(recent) < 2:
            return False
        for ci in recent:
            entries = list(ci.entries) if ci.entries is not None else []
            if not entries:
                return False
            planned = sum(float(e.planned_amount or 0) for e in entries)
            actual = sum(float(e.actual_amount or 0) for e in entries)
            if actual < planned:
                return False
        return True

    def get_savings_streak_months(self):
        """Count consecutive recent CheckIns where actual >= planned.
        Used to fill {streak} in the whisper template."""
        from app.models.checkin import CheckIn
        rows = (
            CheckIn.query.filter_by(user_id=self.id)
            .order_by(CheckIn.year.desc(), CheckIn.month.desc())
            .all()
        )
        streak = 0
        for ci in rows:
            entries = list(ci.entries) if ci.entries is not None else []
            if not entries:
                break
            planned = sum(float(e.planned_amount or 0) for e in entries)
            actual = sum(float(e.actual_amount or 0) for e in entries)
            if actual >= planned and planned > 0:
                streak += 1
            else:
                break
        return streak

    def has_completed_recent_checkin(self):
        """True if the user's most recent CheckIn was completed within
        the last 14 days."""
        from datetime import datetime, timedelta
        from app.models.checkin import CheckIn
        latest = (
            CheckIn.query.filter_by(user_id=self.id)
            .order_by(CheckIn.completed_at.desc())
            .first()
        )
        if latest is None or latest.completed_at is None:
            return False
        return latest.completed_at >= datetime.utcnow() - timedelta(days=14)

    def __repr__(self):
        return f"<User {self.id}>"