from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.services.budget_service import calculate_budget_status, suggest_budgets

budget_bp = Blueprint("budgets", __name__, url_prefix="/api/budgets")


@budget_bp.route("", methods=["POST"])
@login_required
def create_budget():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    category_id = data.get("category_id")
    if not category_id:
        return jsonify({"error": "category_id is required"}), 400

    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"error": "Invalid category_id"}), 400

    try:
        monthly_limit = round(float(data.get("monthly_limit", 0)), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "monthly_limit must be a valid number"}), 400

    if monthly_limit <= 0:
        return jsonify({"error": "monthly_limit must be greater than zero"}), 400

    # Check for existing budget on this category
    existing = Budget.query.filter_by(
        user_id=current_user.id,
        category_id=category_id,
        is_active=True
    ).first()

    if existing:
        return jsonify({"error": f"An active budget already exists for {category.name}. Update it instead."}), 409

    budget = Budget(
        user_id=current_user.id,
        category_id=category_id,
        monthly_limit=monthly_limit
    )

    db.session.add(budget)
    db.session.commit()

    return jsonify({
        "message": "Budget created successfully",
        "budget": budget.to_dict()
    }), 201


@budget_bp.route("", methods=["GET"])
@login_required
def list_budgets():
    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    return jsonify({
        "budgets": [b.to_dict() for b in budgets],
        "count": len(budgets)
    }), 200


@budget_bp.route("/<int:budget_id>", methods=["PUT"])
@login_required
def update_budget(budget_id):
    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first()

    if not budget:
        return jsonify({"error": "Budget not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    if "monthly_limit" in data:
        try:
            limit = round(float(data["monthly_limit"]), 2)
        except (ValueError, TypeError):
            return jsonify({"error": "monthly_limit must be a valid number"}), 400

        if limit <= 0:
            return jsonify({"error": "monthly_limit must be greater than zero"}), 400

        budget.monthly_limit = limit

    if "is_active" in data:
        budget.is_active = bool(data["is_active"])

    db.session.commit()

    return jsonify({
        "message": "Budget updated",
        "budget": budget.to_dict()
    }), 200


@budget_bp.route("/<int:budget_id>", methods=["DELETE"])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(
        id=budget_id,
        user_id=current_user.id
    ).first()

    if not budget:
        return jsonify({"error": "Budget not found"}), 404

    db.session.delete(budget)
    db.session.commit()

    return jsonify({"message": "Budget deleted"}), 200


@budget_bp.route("/status", methods=["GET"])
@login_required
def get_budget_status():
    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()

    if not budgets:
        return jsonify({
            "budgets": [],
            "summary": {"budget_count": 0},
            "alerts": [],
            "message": "No active budgets. Create budgets to track your spending limits."
        }), 200

    budget_list = [b.to_dict() for b in budgets]

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    txn_list = [{
        "amount": float(t.amount),
        "category": t.category_rel.name if t.category_rel else "Other",
        "type": t.type,
        "date": t.date
    } for t in transactions]

    result = calculate_budget_status(budget_list, txn_list)

    return jsonify(result), 200


@budget_bp.route("/suggestions", methods=["GET"])
@login_required
def get_suggestions():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    txn_list = [{
        "amount": float(t.amount),
        "category": t.category_rel.name if t.category_rel else "Other",
        "type": t.type,
        "date": t.date
    } for t in transactions]

    result = suggest_budgets(txn_list)

    return jsonify(result), 200