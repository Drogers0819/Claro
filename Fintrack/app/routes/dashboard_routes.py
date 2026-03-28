from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from sqlalchemy import func

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("", methods=["GET"])
@login_required
def get_dashboard():
    income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(
        user_id=current_user.id,
        type="income"
    ).scalar()

    expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(
        user_id=current_user.id,
        type="expense"
    ).scalar()

    balance = float(income) - float(expenses)

    transaction_count = Transaction.query.filter_by(
        user_id=current_user.id
    ).count()

    recent_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(
        Transaction.date.desc()
    ).limit(5).all()

    return jsonify({
        "summary": {
            "total_income": float(income),
            "total_expenses": float(expenses),
            "balance": balance,
            "transaction_count": transaction_count
        },
        "recent_transactions": [t.to_dict() for t in recent_transactions]
    }), 200