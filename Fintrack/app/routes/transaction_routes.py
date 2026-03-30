from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.category import Category
from datetime import date


transaction_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


@transaction_bp.route("", methods=["POST"])
@login_required
def create_transaction():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    description = data.get("description", "").strip()
    transaction_type = data.get("type", "").strip().lower()
    merchant = data.get("merchant", "").strip() or None

    if not description:
        return jsonify({"error": "Description is required"}), 400

    if transaction_type not in ("income", "expense"):
        return jsonify({"error": "Type must be 'income' or 'expense'"}), 400

    try:
        amount = round(float(data.get("amount", 0)), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "Amount must be a valid number"}), 400

    if amount <= 0:
        return jsonify({"error": "Amount must be greater than zero"}), 400

    try:
        transaction_date = date.fromisoformat(data.get("date", ""))
    except (ValueError, TypeError):
        return jsonify({"error": "Date must be in YYYY-MM-DD format"}), 400

    category_id = data.get("category_id")
    if category_id:
        category = db.session.get(Category, category_id)
        if not category:
            return jsonify({"error": "Invalid category_id"}), 400
    else:
        category = Category.query.filter_by(name="Other").first()
        if not category:
            return jsonify({"error": "Default category not found"}), 500
        category_id = category.id

    transaction = Transaction(
        user_id=current_user.id,
        amount=amount,
        description=description,
        category_id=category_id,
        type=transaction_type,
        date=transaction_date,
        merchant=merchant
    )

    db.session.add(transaction)
    db.session.commit()

    return jsonify({
        "message": "Transaction created successfully",
        "transaction": transaction.to_dict()
    }), 201


@transaction_bp.route("", methods=["GET"])
@login_required
def list_transactions():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).all()

    return jsonify({
        "transactions": [t.to_dict() for t in transactions],
        "count": len(transactions)
    }), 200


@transaction_bp.route("/<int:transaction_id>", methods=["GET"])
@login_required
def get_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()

    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    return jsonify({"transaction": transaction.to_dict()}), 200


@transaction_bp.route("/<int:transaction_id>", methods=["DELETE"])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()

    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    db.session.delete(transaction)
    db.session.commit()

    return jsonify({"message": "Transaction deleted successfully"}), 200