from app import db


class Budget(db.Model):
    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    monthly_limit = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    category = db.relationship("Category", backref="budgets", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else "Unknown",
            "category_icon": self.category.icon if self.category else "",
            "category_colour": self.category.colour if self.category else "#888",
            "monthly_limit": float(self.monthly_limit),
            "is_active": self.is_active
        }

    def __repr__(self):
        return f"<Budget {self.id}: {self.category.name if self.category else '?'} £{self.monthly_limit}>"