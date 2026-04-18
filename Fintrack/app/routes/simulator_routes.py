from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.models.goal import Goal
from app.services.simulator_service import (
    project_goal_timeline,
    calculate_cost_of_habit,
    simulate_scenario,
    generate_multi_horizon_projection,
    GROWTH_RATES
)

simulator_bp = Blueprint("simulator", __name__, url_prefix="/api/simulator")


@simulator_bp.route("/project/<int:goal_id>", methods=["GET"])
@login_required
def project_goal(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    if not goal.target_amount:
        return jsonify({"error": "This goal has no target amount to project against"}), 400

    growth_rate_name = request.args.get("growth", "moderate")
    growth_rate = GROWTH_RATES.get(growth_rate_name, GROWTH_RATES["moderate"])

    contribution = float(goal.monthly_allocation) if goal.monthly_allocation else 0

    goal_data = {
        "target_amount": float(goal.target_amount),
        "current_amount": float(goal.current_amount) if goal.current_amount else 0
    }

    projection = project_goal_timeline(goal_data, contribution, growth_rate)

    projection["goal_name"] = goal.name
    projection["goal_id"] = goal.id

    return jsonify(projection), 200


@simulator_bp.route("/project-all", methods=["GET"])
@login_required
def project_all_goals():
    goals = Goal.query.filter_by(
        user_id=current_user.id,
        status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    if not goals:
        return jsonify({
            "projections": [],
            "message": "No active goals to project"
        }), 200

    growth_rate_name = request.args.get("growth", "moderate")
    growth_rate = GROWTH_RATES.get(growth_rate_name, GROWTH_RATES["moderate"])

    projections = []

    for goal in goals:
        if not goal.target_amount:
            projections.append({
                "goal_id": goal.id,
                "goal_name": goal.name,
                "type": goal.type,
                "message": "No target amount. Ongoing allocation.",
                "monthly_allocation": float(goal.monthly_allocation) if goal.monthly_allocation else 0
            })
            continue

        contribution = float(goal.monthly_allocation) if goal.monthly_allocation else 0

        goal_data = {
            "target_amount": float(goal.target_amount),
            "current_amount": float(goal.current_amount) if goal.current_amount else 0
        }

        projection = project_goal_timeline(goal_data, contribution, growth_rate)
        projection["goal_name"] = goal.name
        projection["goal_id"] = goal.id
        projection["goal_type"] = goal.type

        # Strip monthly_projections for the overview to keep response size manageable
        if "monthly_projections" in projection:
            del projection["monthly_projections"]

        projections.append(projection)

    reachable_count = sum(1 for p in projections if p.get("reachable") is True)

    return jsonify({
        "projections": projections,
        "total_goals": len(projections),
        "reachable_goals": reachable_count,
        "growth_rate": growth_rate_name
    }), 200


@simulator_bp.route("/habit-cost", methods=["POST"])
@login_required
def habit_cost():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    monthly_spend = data.get("monthly_spend")
    if monthly_spend is None:
        return jsonify({"error": "monthly_spend is required"}), 400

    try:
        monthly_spend = round(float(monthly_spend), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "monthly_spend must be a valid number"}), 400

    if monthly_spend <= 0:
        return jsonify({"error": "monthly_spend must be greater than zero"}), 400

    growth_rate_name = data.get("growth_rate", "moderate")
    growth_rate = GROWTH_RATES.get(growth_rate_name, GROWTH_RATES["moderate"])

    description = data.get("description", "This habit")

    result = calculate_cost_of_habit(monthly_spend, growth_rate=growth_rate)
    result["description"] = description

    return jsonify(result), 200


@simulator_bp.route("/scenario", methods=["POST"])
@login_required
def run_scenario():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400

    goals = Goal.query.filter_by(
        user_id=current_user.id,
        status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    if not goals:
        return jsonify({"error": "No active goals to simulate against"}), 400

    if not current_user.factfind_completed:
        return jsonify({"error": "Complete your financial profile first"}), 400

    goals_data = []
    for g in goals:
        goals_data.append({
            "id": g.id,
            "name": g.name,
            "type": g.type,
            "target_amount": float(g.target_amount) if g.target_amount else None,
            "current_amount": float(g.current_amount) if g.current_amount else 0,
            "monthly_allocation": float(g.monthly_allocation) if g.monthly_allocation else 0,
            "priority_rank": g.priority_rank
        })

    current_state = {
        "monthly_income": float(current_user.monthly_income),
        "fixed_commitments": current_user.fixed_commitments,
        "goals": goals_data
    }

    proposed_changes = {
        "monthly_income": float(data.get("monthly_income", current_user.monthly_income)),
        "fixed_commitments": float(data.get("fixed_commitments", current_user.fixed_commitments)),
        "spending_changes": data.get("spending_changes", {})
    }

    result = simulate_scenario(current_state, proposed_changes)

    return jsonify(result), 200


@simulator_bp.route("/multi-horizon/<int:goal_id>", methods=["GET"])
@login_required
def multi_horizon(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first()

    if not goal:
        return jsonify({"error": "Goal not found"}), 404

    contribution = float(goal.monthly_allocation) if goal.monthly_allocation else 0

    goal_data = {
        "target_amount": float(goal.target_amount) if goal.target_amount else 0,
        "current_amount": float(goal.current_amount) if goal.current_amount else 0
    }

    result = generate_multi_horizon_projection(goal_data, contribution)
    result["goal_name"] = goal.name
    result["goal_id"] = goal.id
    result["monthly_contribution"] = contribution

    return jsonify(result), 200