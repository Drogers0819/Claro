from app import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    icon = db.Column(db.String(10), nullable=True)
    colour = db.Column(db.String(7), nullable=True)

    transactions = db.relationship("Transaction", backref="category_rel", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "colour": self.colour
        }

    def __repr__(self):
        return f"<Category {self.id}: {self.name}>"