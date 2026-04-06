from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.transaction import Transaction
from app.models.goal import Goal
from app.models.budget import Budget
from app.services.insight_service import generate_page_insights, generate_daily_digest, generate_month_end_summary
from app.services.prediction_service import predict_monthly_spending
from app.services.budget_service import calculate_budget_status as calc_budget_status
from app.services.anomaly_service import detect_anomalies
from app.services.recurring_service import detect_recurring_transactions, identify_potential_savings
from app.services.allocator_service import generate_waterfall_summary
from app.services.simulator_service import project_goal_timeline
from sqlalchemy import func, extract
from datetime import date
import calendar


insight_bp = Blueprint("insights_api", __name__, url_prefix="/api/insights")


def _build_user_data():
    """
    Gathers all data needed for insight generation.
    Single function to avoid duplicating data loading across endpoints.
    """
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = [{
        "amount": float(t.amount),
        "description": t.description,
        "merchant": t.merchant or t.description,
        "category": t.category_rel.name if t.category_rel else "Other",
        "type": t.type,
        "date": t.date
    } for t in transactions]

    goals = Goal.query.filter_by(
        user_id=current_user.id,
        status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    goals_list = [g.to_dict() for g in goals]

    # Predictions
    predictions = predict_monthly_spending(txn_list)

    # Anomalies
    anomalies = detect_anomalies(txn_list)

    # Recurring
    recurring = detect_recurring_transactions(txn_list)
    savings_opps = identify_potential_savings(recurring["recurring"])

    # Budgets
    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    budget_list = [b.to_dict() for b in budgets]
    budget_status = calc_budget_status(budget_list, txn_list) if budget_list else {"budgets": [], "summary": {}}

    # Waterfall
    waterfall = {}
    if current_user.factfind_completed and current_user.monthly_income:
        goals_data = [{
            "id": g.id, "name": g.name, "type": g.type,
            "target_amount": float(g.target_amount) if g.target_amount else None,
            "current_amount": float(g.current_amount) if g.current_amount else 0,
            "monthly_allocation": float(g.monthly_allocation) if g.monthly_allocation else 0,
            "priority_rank": g.priority_rank
        } for g in goals]

        user_profile = {
            "monthly_income": float(current_user.monthly_income),
            "fixed_commitments": current_user.fixed_commitments
        }
        waterfall = generate_waterfall_summary(user_profile, goals_data)

    # Projections
    projections = []
    for g in goals:
        if g.target_amount and g.monthly_allocation:
            proj = project_goal_timeline(
                {"target_amount": float(g.target_amount),
                 "current_amount": float(g.current_amount) if g.current_amount else 0},
                float(g.monthly_allocation)
            )
            proj["goal_name"] = g.name
            proj["goal_id"] = g.id
            projections.append(proj)

    # Money left
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day

    money_left = None
    if current_user.factfind_completed and current_user.monthly_income:
        current_month_expenses = db.session.query(
            func.coalesce(func.sum(Transaction.amount), 0)
        ).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == "expense",
            extract("month", Transaction.date) == today.month,
            extract("year", Transaction.date) == today.year
        ).scalar()

        total_goal_allocation = sum(
            float(g.monthly_allocation) if g.monthly_allocation else 0
            for g in goals
        )
        disposable = current_user.monthly_surplus - total_goal_allocation
        money_left = round(disposable - float(current_month_expenses), 2)

    # Trends
    trends = []
    current_month = today.month
    current_year = today.year
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1

    from app.models.category import Category

    current_cat = db.session.query(
        Category.name, func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == current_month,
        extract("year", Transaction.date) == current_year
    ).group_by(Category.name).all()

    prev_cat = db.session.query(
        Category.name, func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == prev_month,
        extract("year", Transaction.date) == prev_year
    ).group_by(Category.name).all()

    prev_dict = {r.name: float(r.total) for r in prev_cat}

    for r in current_cat:
        current_total = float(r.total)
        prev_total = prev_dict.get(r.name, 0)
        if prev_total > 0:
            change = current_total - prev_total
            pct = round((change / prev_total) * 100, 1)
        else:
            change = current_total
            pct = 100.0

        trends.append({
            "category": r.name,
            "current_month": round(current_total, 2),
            "previous_month": round(prev_total, 2),
            "change_amount": round(change, 2),
            "change_percent": pct,
            "direction": "up" if change > 0 else "down" if change < 0 else "flat"
        })

    trends.sort(key=lambda t: abs(t["change_amount"]), reverse=True)

    return {
        "user_name": current_user.name,
        "money_left": money_left,
        "days_remaining": days_remaining,
        "predictions": predictions,
        "anomalies": anomalies,
        "recurring": recurring,
        "savings_opportunities": savings_opps,
        "budget_statuses": budget_status.get("budgets", []),
        "budget_status": budget_status.get("summary", {}),
        "goals": goals_list,
        "waterfall": waterfall,
        "projections": projections,
        "trends": trends,
        "total_transactions": Transaction.query.filter_by(user_id=current_user.id).count(),
        "active_goals": len(goals_list),
        "member_since": current_user.created_at.strftime("%B %Y") if current_user.created_at else ""
    }


@insight_bp.route("/page/<page_name>", methods=["GET"])
@login_required
def page_insight(page_name):
    user_data = _build_user_data()
    insight = generate_page_insights(page_name, user_data)

    return jsonify(insight), 200


@insight_bp.route("/digest", methods=["GET"])
@login_required
def daily_digest():
    user_data = _build_user_data()
    digest = generate_daily_digest(user_data)

    return jsonify(digest), 200


@insight_bp.route("/month-summary", methods=["GET"])
@login_required
def month_summary():
    user_data = _build_user_data()
    summary = generate_month_end_summary(user_data)

    return jsonify(summary), 200