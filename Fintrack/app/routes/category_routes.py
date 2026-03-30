from flask import Blueprint, jsonify
from flask_login import login_required
from app.models.category import Category

category_bp = Blueprint("categories", __name__, url_prefix="/api/categories")


@category_bp.route("", methods=["GET"])
@login_required
def list_categories():
    categories = Category.query.order_by(Category.name).all()

    return jsonify({
        "categories": [c.to_dict() for c in categories],
        "count": len(categories)
    }), 200