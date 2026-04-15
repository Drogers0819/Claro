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
    income_day = db.Column(db.Integer, nullable=True)
    factfind_completed = db.Column(db.Boolean, default=False)

    # Preferences
    theme = db.Column(db.String(30), default="racing-green")

    # Relationships
    transactions = db.relationship("Transaction", backref="user", lazy=True)
    goals = db.relationship("Goal", backref="user", lazy=True)

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
        return rent + bills + groceries + transport + subs

    @property
    def monthly_surplus(self):
        income = float(self.monthly_income) if self.monthly_income else 0
        return income - self.fixed_commitments
    @property
    def tier(self):
        return "Claro Core"

    def profile_dict(self):
        return {
            "monthly_income": float(self.monthly_income) if self.monthly_income else None,
            "rent_amount": float(self.rent_amount) if self.rent_amount else None,
            "bills_amount": float(self.bills_amount) if self.bills_amount else None,
            "groceries_estimate": float(self.groceries_estimate) if self.groceries_estimate else None,
            "transport_estimate": float(self.transport_estimate) if self.transport_estimate else None,
            "subscriptions_total": float(self.subscriptions_total) if self.subscriptions_total else None,
            "income_day": self.income_day,
            "fixed_commitments": self.fixed_commitments,
            "total_essentials": self.total_essentials,
            "monthly_surplus": self.monthly_surplus,
            "factfind_completed": self.factfind_completed,
            "theme": self.theme
        }

    def __repr__(self):
        return f"<User {self.id}: {self.email}>"