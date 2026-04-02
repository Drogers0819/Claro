from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models.transaction import Transaction
from app.models.goal import Goal
from app.services.prediction_service import predict_monthly_spending, calculate_budget_status

prediction_bp = Blueprint("prediction", __name__, url_prefix="/api/predictions")


@prediction_bp.route("/monthly", methods=["GET"])
@login_required
def monthly_prediction():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = []
    for t in transactions:
        txn_list.append({
            "amount": float(t.amount),
            "description": t.description,
            "category": t.category_rel.name if t.category_rel else "Other",
            "type": t.type,
            "date": t.date
        })

    result = predict_monthly_spending(txn_list)

    return jsonify(result), 200


@prediction_bp.route("/budget-status", methods=["GET"])
@login_required
def budget_status():
    if not current_user.factfind_completed:
        return jsonify({
            "error": "Complete your financial profile first",
            "factfind_completed": False
        }), 400

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = []
    for t in transactions:
        txn_list.append({
            "amount": float(t.amount),
            "description": t.description,
            "category": t.category_rel.name if t.category_rel else "Other",
            "type": t.type,
            "date": t.date
        })

    predictions = predict_monthly_spending(txn_list)

    goals = Goal.query.filter_by(
        user_id=current_user.id,
        status="active"
    ).all()

    goals_data = []
    for g in goals:
        goals_data.append({
            "id": g.id,
            "name": g.name,
            "monthly_allocation": float(g.monthly_allocation) if g.monthly_allocation else 0
        })

    user_profile = {
        "monthly_income": float(current_user.monthly_income),
        "fixed_commitments": current_user.fixed_commitments
    }

    status = calculate_budget_status(predictions, user_profile, goals_data)

    return jsonify({
        "predictions": predictions,
        "budget_status": status
    }), 200