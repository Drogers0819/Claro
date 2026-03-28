from app import db


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="Other")
    type = db.Column(db.String(10), nullable=False)
    date = db.Column(db.Date, nullable=False)
    merchant = db.Column(db.String(255), nullable=True)
    is_recurring = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "amount": float(self.amount),
            "description": self.description,
            "category": self.category,
            "type": self.type,
            "date": self.date.isoformat(),
            "merchant": self.merchant,
            "is_recurring": self.is_recurring,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Transaction {self.id}: £{self.amount} - {self.description}>"