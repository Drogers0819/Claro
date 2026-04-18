from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.models.goal import Goal
from app.models.budget import Budget
from sqlalchemy import func, extract
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from app.services.csv_parser import extract_transactions_from_csv, CSVParseError
from app.services.categoriser_service import categorise_transactions, build_categoriser_for_user
from app.services.allocator_service import generate_waterfall_summary
from app.services.prediction_service import predict_monthly_spending, calculate_budget_status as calc_prediction_budget_status
from app.services.budget_service import calculate_budget_status as calc_budget_status, suggest_budgets
from app.services.recurring_service import detect_recurring_transactions, identify_potential_savings
from app.services.anomaly_service import detect_anomalies
from app.services.insight_service import generate_page_insights
from app.services.simulator_service import (
    project_goal_timeline, calculate_cost_of_habit,
    simulate_scenario, generate_multi_horizon_projection
)
import calendar
from app.services.planner_service import generate_financial_plan, get_plan_summary, can_i_afford
from app.services.whisper_service import generate_action_whisper
from app.services.withdrawal_service import get_withdrawal_options
from app.models.life_checkin import LifeCheckIn
page_bp = Blueprint("pages", __name__)


# ─── HELPERS ──────────────────────────────────────────────

def _build_memory_card(data):
    """
    Builds the 'what Claro has learned' card for the overview.
    Only shown when there's enough data to say something genuinely meaningful.
    Threshold: 20+ transactions so patterns are real, not noise.
    """
    total_txns = data.get("total_transactions", 0)
    if total_txns < 20:
        return None

    # How long the user has been active
    joined = current_user.created_at
    if joined:
        weeks_active = max(1, (date.today() - joined.date()).days // 7)
    else:
        weeks_active = None

    # Most significant category finding
    trends = data.get("trends", [])
    top_trend = None
    if trends:
        # Pick the category with the largest absolute spend movement
        top_trend = trends[0]  # already sorted by abs change_amount desc

    # Recurring intelligence
    recurring = data.get("recurring", {})
    recurring_count = recurring.get("expense_count", 0)
    recurring_total = recurring.get("total_monthly_cost", 0)

    # Spending direction overall
    predictions = data.get("predictions", {})
    comparison = predictions.get("comparison", {})
    spending_status = comparison.get("status", "")
    spending_diff = abs(comparison.get("difference", 0))

    # Anomalies
    anomalies = data.get("anomalies", [])
    anomaly_count = len(anomalies) if anomalies else 0

    # Only return if there's something genuinely worth surfacing
    has_insight = recurring_count > 0 or top_trend or spending_status
    if not has_insight:
        return None

    return {
        "weeks_active": weeks_active,
        "total_transactions": total_txns,
        "recurring_count": recurring_count,
        "recurring_total": recurring_total,
        "top_category": top_trend["category"] if top_trend else None,
        "top_category_direction": top_trend["direction"] if top_trend else None,
        "top_category_change": abs(top_trend["change_amount"]) if top_trend else 0,
        "spending_status": spending_status,
        "spending_diff": spending_diff,
        "anomaly_count": anomaly_count,
    }


def _get_txn_list():
    """Returns all user transactions as dicts."""
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.asc()).all()

    return [{
        "amount": float(t.amount),
        "description": t.description,
        "merchant": t.merchant or t.description,
        "category": t.category_rel.name if t.category_rel else "Other",
        "category_id": t.category_id,
        "type": t.type,
        "date": t.date,
        "id": t.id
    } for t in transactions]


def _get_money_left():
    """Calculates money left to spend this month.
    
    Income minus all expenses, excluding Transfers (money moved
    between accounts is not spending).
    """
    if not current_user.factfind_completed or not current_user.monthly_income:
        return None, 0

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day

    income = float(current_user.monthly_income)

    # Exclude transfers — moving money between accounts is not spending
    transfer_category = db.session.query(Category.id).filter(
        Category.name == "Transfer"
    ).scalar()

    query = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    )

    if transfer_category:
        query = query.filter(Transaction.category_id != transfer_category)

    current_month_expenses = query.scalar()

    money_left = round(income - float(current_month_expenses), 2)

    return money_left, days_remaining

def _ensure_emergency_goal():
    """Emergency fund is now opt-in via goal chips. No auto-creation."""
    return


def _build_whisper_data():
    """Builds the data object used by the insight engine."""
    txn_list = _get_txn_list()
    money_left, days_remaining = _get_money_left()

    predictions = predict_monthly_spending(txn_list)
    anomalies = detect_anomalies(txn_list)

    goals = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()
    goals_list = [g.to_dict() for g in goals]

    primary_goal = goals_list[0] if goals_list else {}

    budgets = Budget.query.filter_by(
        user_id=current_user.id, is_active=True
    ).all()
    budget_list = [b.to_dict() for b in budgets]
    budget_status_result = calc_budget_status(budget_list, txn_list) if budget_list else {"budgets": [], "summary": {}}

    recurring = detect_recurring_transactions(txn_list)
    savings = identify_potential_savings(recurring["recurring"])

    waterfall = {}
    projections = []
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

    # Trends
    today = date.today()
    current_month = today.month
    current_year = today.year
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1

    current_cat = db.session.query(
        Category.name, Category.icon, func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == current_month,
        extract("year", Transaction.date) == current_year
    ).group_by(Category.id, Category.name, Category.icon).all()

    prev_cat = db.session.query(
        Category.name, func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == prev_month,
        extract("year", Transaction.date) == prev_year
    ).group_by(Category.id, Category.name).all()

    prev_dict = {r.name: float(r.total) for r in prev_cat}

    trends = []
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
            "category": r.name, "icon": r.icon,
            "change_amount": round(change, 2), "change_percent": pct,
            "direction": "up" if change > 0 else "down" if change < 0 else "flat"
        })
    trends.sort(key=lambda t: abs(t["change_amount"]), reverse=True)

    return {
        "user_name": current_user.name,
        "money_left": money_left,
        "days_remaining": days_remaining,
        "predictions": predictions,
        "anomalies": anomalies,
        "primary_goal": primary_goal,
        "goals": goals_list,
        "budget_statuses": budget_status_result.get("budgets", []),
        "budget_status": budget_status_result.get("summary", {}),
        "waterfall": waterfall,
        "projections": projections,
        "recurring": recurring,
        "savings_opportunities": savings,
        "trends": trends,
        "total_transactions": Transaction.query.filter_by(user_id=current_user.id).count(),
        "active_goals": len(goals_list)
    }


def _build_whisper_data_for_user(user):
    """
    Same as _build_whisper_data() but takes an explicit user argument.
    Used by the weekly digest scheduler which runs outside a request context.
    """
    from flask_login import current_user as _cu
    # Temporarily swap current_user context for the scheduler
    transactions = Transaction.query.filter_by(
        user_id=user.id
    ).order_by(Transaction.date.asc()).all()

    txn_list = [{
        "amount": float(t.amount),
        "description": t.description,
        "merchant": t.merchant or t.description,
        "category": t.category_rel.name if t.category_rel else "Other",
        "category_id": t.category_id,
        "type": t.type,
        "date": t.date,
        "id": t.id
    } for t in transactions]

    predictions = predict_monthly_spending(txn_list)
    recurring = detect_recurring_transactions(txn_list)
    goals = Goal.query.filter_by(user_id=user.id, status="active").order_by(Goal.priority_rank.asc()).all()
    goals_list = [g.to_dict() for g in goals]
    primary_goal = goals_list[0] if goals_list else {}

    from app.services.insight_service import generate_page_insights
    comparison = predictions.get("comparison", {})
    whisper_input = {
        "user_name": user.name,
        "money_left": None,
        "days_remaining": 0,
        "predictions": predictions,
        "primary_goal": primary_goal,
        "goals": goals_list,
        "budget_statuses": [],
        "recurring": recurring,
    }
    whisper_result = generate_page_insights("overview", whisper_input)

    return {
        "total_transactions": len(txn_list),
        "predictions": predictions,
        "recurring": recurring,
        "goals": goals_list,
        "primary_goal": primary_goal,
        "whisper": whisper_result.get("whisper", ""),
        "budget_statuses": [],
        "trends": [],
        "anomalies": [],
    }


# ─── AUTH ROUTES ──────────────────────────────────────────

@page_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("pages.overview"))
    return redirect(url_for("pages.login"))


@page_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.overview"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for("pages.register"))

        if len(password) < 8:
            flash("Password must be at least 8 characters", "error")
            return redirect(url_for("pages.register"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists", "error")
            return redirect(url_for("pages.register"))

        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        return redirect(url_for("pages.factfind"))

    return render_template("register.html")


@page_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.overview"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password", "error")
            return render_template("login.html", prefill_email=email)

        login_user(user)
        return redirect(url_for("pages.overview"))

    return render_template("login.html")


@page_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been signed out", "success")
    return redirect(url_for("pages.login"))


# ─── OVERVIEW ─────────────────────────────────────────────

@page_bp.route("/overview")
@login_required
def overview():
    data = _build_whisper_data()

    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    # Generate smart plan
    smart_plan = None
    plan_summary = None
    if current_user.factfind_completed and current_user.monthly_income:
        user_profile = current_user.profile_dict()
        goals_data = data["goals"]
        smart_plan = generate_financial_plan(user_profile, goals_data)
        if "error" not in smart_plan:
            plan_summary = get_plan_summary(smart_plan)
            # Generate action whisper
    action_whisper = None
    if smart_plan and "error" not in smart_plan:
        action_whisper = generate_action_whisper(current_user, smart_plan, data["goals"])

    # Money left (secondary stat)
    money_left, days_remaining = _get_money_left()

    # Spending summary this month
    today = date.today()
    income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="income").filter(
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    ).scalar()

    expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="expense").filter(
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    ).scalar()

    # Top 3 spending categories this month
    top_categories = db.session.query(
        Category.name, Category.icon, Category.colour,
        func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    ).group_by(Category.id, Category.name, Category.icon, Category.colour
    ).order_by(func.sum(Transaction.amount).desc()).limit(3).all()

    categories = [{"name": c.name.replace(c.icon, "").strip() if c.icon and c.name.startswith(c.icon) else c.name, "icon": c.icon, "colour": c.colour or "var(--text-tertiary)", "total": float(c.total)} for c in top_categories]

    # Last upload date
    last_transaction = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).first()

    has_data = last_transaction is not None

    return render_template("overview.html",
        greeting=greeting,
        smart_plan=smart_plan,
        plan_summary=plan_summary,
        money_left=money_left,
        days_remaining=days_remaining,
        has_data=has_data,
        monthly_spending=float(expenses),
        top_categories=categories,
        primary_goal=data["primary_goal"] if data["primary_goal"] else None,
        active_goals_count=data["active_goals"],
        action_whisper=action_whisper,
    )


# ─── MY MONEY ────────────────────────────────────────────

@page_bp.route("/my-money")
@login_required
def my_money():
    data = _build_whisper_data()
    whisper_result = generate_page_insights("my_money", data)

    today = date.today()
    month_name = today.strftime("%B")

    # Category breakdown
    results = db.session.query(
        Category.name, Category.icon, Category.colour,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    ).group_by(
        Category.id, Category.name, Category.icon, Category.colour
    ).order_by(func.sum(Transaction.amount).desc()).all()

    total_expenses = sum(float(r.total) for r in results)
    categories = []
    for r in results:
        amount = float(r.total)
        categories.append({
            "name": r.name, "icon": r.icon, "colour": r.colour,
            "total": amount, "count": r.count,
            "percentage": round((amount / total_expenses * 100), 1) if total_expenses > 0 else 0
        })

    all_transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).all()

    all_categories = Category.query.order_by(Category.name).all()

    return render_template("my_money.html",
        whisper=whisper_result["whisper"],
        month_name=month_name,
        total_expenses=total_expenses,
        categories=categories,
        trends=data["trends"],
        transactions=[t.to_dict() for t in all_transactions],
        all_categories=all_categories
    )


# ─── MY GOALS ────────────────────────────────────────────

@page_bp.route("/my-goals")
@login_required
def my_goals():
    _ensure_emergency_goal()
    goals = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    return render_template("my_goals.html",
        goals=[g.to_dict() for g in goals]
    )


# ─── PLAN ────────────────────────────────────────────────

@page_bp.route("/plan", methods=["GET", "POST"])
@login_required
def plan():
    data = _build_whisper_data()

    # Generate the smart plan
    smart_plan = None
    plan_summary = None
    if current_user.factfind_completed and current_user.monthly_income:
        _ensure_emergency_goal()
        user_profile = current_user.profile_dict()
        goals_data = data["goals"]
        smart_plan = generate_financial_plan(user_profile, goals_data)


    # Habit cost calculator
    habit_result = None
    habit_amount = None
    habit_description = None

    # Affordability check
    afford_result = None

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "habit_cost":
            try:
                habit_amount = round(float(request.form.get("habit_amount", 0)), 2)
                habit_description = request.form.get("habit_description", "").strip() or "This habit"
                if habit_amount > 0:
                    habit_result = calculate_cost_of_habit(habit_amount)
                    habit_result["description"] = habit_description
            except (ValueError, TypeError):
                flash("Invalid amount", "error")

        elif form_type == "afford_check" and smart_plan and "error" not in smart_plan:
            try:
                expense_name = request.form.get("expense_name", "").strip() or "This expense"
                expense_amount = round(float(request.form.get("expense_amount", 0)), 2)
                target_month = request.form.get("target_month", type=int) or 1
                if expense_amount > 0:
                    afford_result = can_i_afford(smart_plan, expense_name, expense_amount, target_month)
            except (ValueError, TypeError):
                flash("Invalid amount", "error")

    return render_template("plan.html",
        waterfall=data["waterfall"],
        projections=data["projections"],
        smart_plan=smart_plan,
        plan_summary=plan_summary,
        afford_result=afford_result,
        habit_result=habit_result,
        habit_amount=habit_amount,
        habit_description=habit_description
    )


# ─── MY BUDGETS ──────────────────────────────────────────

@page_bp.route("/my-budgets")
@login_required
def my_budgets():
    data = _build_whisper_data()
    whisper_result = generate_page_insights("my_budgets", data)

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    month_progress = round((today.day / days_in_month) * 100, 1)
    days_remaining = days_in_month - today.day

    budgeted_cat_ids = [b.category_id for b in Budget.query.filter_by(
        user_id=current_user.id, is_active=True).all()]
    available_categories = Category.query.filter(
        ~Category.id.in_(budgeted_cat_ids) if budgeted_cat_ids else Category.id > 0
    ).order_by(Category.name).all()

    return render_template("my_budgets.html",
        whisper=whisper_result["whisper"],
        budget_statuses=data["budget_statuses"],
        month_progress=month_progress,
        days_remaining=days_remaining,
        available_categories=available_categories,
        recurring=data["recurring"],
        savings=data["savings_opportunities"]
    )

# ─── CHECK-IN ────────────────────────────────────────────────

@page_bp.route("/check-in", methods=["GET", "POST"])
@login_required
def checkin():
    from app.models.checkin import CheckIn, CheckInEntry

    today = date.today()

    # Determine which month to check in for (previous month)
    if today.month == 1:
        checkin_month = 12
        checkin_year = today.year - 1
    else:
        checkin_month = today.month - 1
        checkin_year = today.year

    checkin_month_name = date(checkin_year, checkin_month, 1).strftime("%B %Y")

    # Check if already completed
    existing = CheckIn.query.filter_by(
        user_id=current_user.id,
        month=checkin_month,
        year=checkin_year
    ).first()

    # Get the current plan for planned amounts
    smart_plan = None
    pots_for_checkin = []
    if current_user.factfind_completed and current_user.monthly_income:
        _ensure_emergency_goal()
        user_profile = current_user.profile_dict()
        goals_data = [g.to_dict() for g in Goal.query.filter_by(
            user_id=current_user.id, status="active"
        ).order_by(Goal.priority_rank.asc()).all()]
        smart_plan = generate_financial_plan(user_profile, goals_data)

        if "error" not in smart_plan:
            for pot in smart_plan["pots"]:
                if pot["type"] not in ("lifestyle", "buffer") and not pot.get("completed"):
                    pots_for_checkin.append({
                        "name": pot["name"],
                        "planned": pot["monthly_amount"],
                        "goal_id": pot.get("goal_id"),
                        "target": pot.get("target"),
                        "current": pot.get("current", 0),
                        "type": pot["type"],
                        "paused": pot["monthly_amount"] == 0
                    })

    if request.method == "POST" and not existing:
        checkin_record = CheckIn(
            user_id=current_user.id,
            month=checkin_month,
            year=checkin_year,
            surplus_at_checkin=smart_plan["surplus"] if smart_plan and "error" not in smart_plan else None,
            phase_at_checkin=smart_plan["current_phase"]["phase"] if smart_plan and smart_plan.get("current_phase") else None
        )
        db.session.add(checkin_record)
        db.session.flush()  # Get the ID

        for pot in pots_for_checkin:
            form_key = f"actual_{pot['name'].replace(' ', '_')}"
            try:
                actual = round(float(request.form.get(form_key, 0)), 2)
            except (ValueError, TypeError):
                actual = 0

            note = request.form.get(f"note_{pot['name'].replace(' ', '_')}", "").strip() or None

            entry = CheckInEntry(
                checkin_id=checkin_record.id,
                goal_id=pot.get("goal_id"),
                pot_name=pot["name"],
                planned_amount=pot["planned"],
                actual_amount=actual
            )
            db.session.add(entry)

            # Update goal current_amount
            if pot.get("goal_id") and actual > 0:
                goal = Goal.query.get(pot["goal_id"])
                if goal:
                    goal.current_amount = round(
                        float(goal.current_amount or 0) + actual, 2
                    )

        db.session.commit()
        flash("Check-in complete. Your plan has been updated.", "success")
        return redirect(url_for("pages.checkin"))

    # Get past check-ins for history
    past_checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.year.desc(), CheckIn.month.desc()).limit(6).all()

    return render_template("checkin.html",
        checkin_month=checkin_month_name,
        already_done=existing is not None,
        existing=existing.to_dict() if existing else None,
        pots=pots_for_checkin,
        smart_plan=smart_plan,
        past_checkins=[c.to_dict() for c in past_checkins]
    )

# ─── SURPLUS REVEAL (Onboarding) ─────────────────────────────
@page_bp.route("/onboarding/surplus", methods=["GET", "POST"])
@login_required
def surplus_reveal():
    if not current_user.factfind_completed:
        return redirect(url_for("pages.factfind"))

    profile = current_user.profile_dict()
    income = float(current_user.monthly_income or 0)
    essentials = current_user.total_essentials

    surplus = round(income - essentials, 2)

    if request.method == "POST":
        try:
            lifestyle = round(float(request.form.get("lifestyle_budget", 0)), 2)
        except (ValueError, TypeError):
            lifestyle = 0

        current_user.lifestyle_budget = lifestyle
        db.session.commit()

        return redirect(url_for("pages.goal_chips"))

    return render_template("surplus_reveal.html",
        profile=profile,
        income=round(income, 2),
        essentials=round(essentials, 2),
        surplus=surplus
    )

# ─── GOAL CHIPS (Onboarding) ─────────────────────────────────
# Add this to app/routes/page_routes.py

@page_bp.route("/goals/choose", methods=["GET", "POST"])
@login_required
def goal_chips():
    if not current_user.factfind_completed:
        return redirect(url_for("pages.factfind"))

    if request.method == "POST":
        selected = request.form.getlist("goals")
        today = date.today()

        # Clear any goals from previous onboarding attempts
        Goal.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        for chip in selected:
            name = None
            target = None
            deadline = None
            must_hit = False
            if chip == "emergency":
                name = "Emergency fund"
                target = request.form.get("emergency_custom") or request.form.get("emergency_amount")


            elif chip == "house":
                name = "House deposit"
                target = request.form.get("house_custom") or request.form.get("house_amount")
                months = request.form.get("house_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("house_must_hit"))

            elif chip == "holiday":
                name = "Holiday"
                target = request.form.get("holiday_amount")
                months = request.form.get("holiday_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("holiday_must_hit"))

            elif chip == "baby":
                name = "Baby fund"
                target = request.form.get("baby_amount")
                months = request.form.get("baby_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("baby_must_hit"))

            elif chip == "debt":
                name = request.form.get("debt_name", "").strip()
                if not name:
                    name = "Pay off debt"
                elif not any(w in name.lower() for w in ["pay off", "clear", "debt", "loan", "credit", "overdraft"]):
                    name = f"Pay off {name}"
                target = request.form.get("debt_amount")
                months = request.form.get("debt_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("debt_must_hit"))

            elif chip == "car":
                name = "Car"
                target = request.form.get("car_amount")
                months = request.form.get("car_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("car_must_hit"))

            elif chip == "wedding":
                name = "Wedding"
                target = request.form.get("wedding_custom") or request.form.get("wedding_amount")
                months = request.form.get("wedding_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("wedding_must_hit"))

            elif chip == "student":
                name = "Pay off student loan"
                target = request.form.get("student_amount")
                months = request.form.get("student_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("student_must_hit"))

            elif chip == "purchase":
                name = request.form.get("purchase_name", "").strip() or "New purchase"
                target = request.form.get("purchase_amount")
                months = request.form.get("purchase_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("purchase_must_hit"))

            elif chip == "custom":
                name = request.form.get("custom_name", "").strip() or "Custom goal"
                target = request.form.get("custom_amount")
                months = request.form.get("custom_timeline", type=int)
                if months and months > 0:
                    deadline = today + relativedelta(months=months)
                must_hit = bool(request.form.get("custom_must_hit"))

            if must_hit and name:
                name = f"{name} (must-hit)"

            if name and target:
                try:
                    target_amount = round(float(target), 2)
                    if target_amount > 0:
                        goal = Goal(
                            user_id=current_user.id,
                            name=name,
                            type="savings_target",
                            target_amount=target_amount,
                            current_amount=0,
                            deadline=deadline,
                            priority_rank=len(selected)
                        )
                        db.session.add(goal)
                except (ValueError, TypeError):
                    pass

        db.session.commit()


        return redirect(url_for("pages.plan_reveal"))

    return render_template("goal_chips.html")


# ─── PLAN REVEAL (Onboarding) ────────────────────────────────

@page_bp.route("/plan-reveal")
@login_required
def plan_reveal():
    if not current_user.factfind_completed:
        return redirect(url_for("pages.factfind"))

    _ensure_emergency_goal()

    # Apply emergency savings from goal chips if provided
    emergency_savings = session.pop("emergency_savings", None)
    if emergency_savings:
        emergency = Goal.query.filter_by(
            user_id=current_user.id
        ).filter(Goal.name.ilike("%emergency%")).first()
        if emergency:
            emergency.current_amount = emergency_savings
            db.session.commit()

    user_profile = current_user.profile_dict()
    goals_data = [g.to_dict() for g in Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()]

    plan = generate_financial_plan(user_profile, goals_data)
    summary = get_plan_summary(plan) if "error" not in plan else plan.get("error", "")

    return render_template("plan_reveal.html",
        plan=plan,
        summary=summary
    )

# ─── PLAN REVIEW (Onboarding) ────────────────────────────────
@page_bp.route("/onboarding/plan-review")
@login_required
def plan_review():
    if not current_user.factfind_completed:
        return redirect(url_for("pages.factfind"))

    _ensure_emergency_goal()

    user_profile = current_user.profile_dict()
    goals_data = [g.to_dict() for g in Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()]

    plan = generate_financial_plan(user_profile, goals_data)

    # Build reasoning for each pot
    reasoning = []
    if "error" not in plan:
        for pot in plan["pots"]:
            name = pot.get("name", "")
            monthly = pot.get("monthly_amount", 0)
            pot_type = pot.get("type", "")
            target = pot.get("target")
            months = pot.get("months_to_target")

            if monthly <= 0:
                continue

            if pot_type == "emergency":
                reason = "Your emergency fund is the foundation of financial security. We target 3 months of essential costs so an unexpected expense doesn't derail your goals."
                if target and months:
                    reason += f" At £{monthly:,.0f}/month, you'll reach your £{target:,.0f} target in approximately {months} months."
            elif pot_type == "debt" or "pay off" in name.lower() or "credit" in name.lower():
                reason = "Debt is prioritised because interest compounds against you. Clearing it first frees up money for everything else."
                if target and months:
                    reason += f" At £{monthly:,.0f}/month, this clears in approximately {months} months."
            elif pot_type == "lifestyle":
                reason = "Your lifestyle pot keeps the plan sustainable. This is the money that lets you enjoy the month: meals out, social plans, hobbies. Without it, plans get abandoned."
            elif pot_type == "buffer":
                reason = "A small buffer protects against minor overspending without touching your goals. Think of it as your plan's shock absorber."
            else:
                deadline = pot.get("deadline")
                if deadline and months:
                    reason = f"Based on your timeline, £{monthly:,.0f}/month gets you to your £{target:,.0f} target in approximately {months} months."
                    if "(must-hit)" in name.lower() or pot.get("_stage") == "must_hit":
                        reason += " You marked this as must-hit, so it's funded before other goals."
                elif target and months:
                    reason = f"With no fixed deadline, we've spread this across {months} months at £{monthly:,.0f}/month. As other goals complete, this will accelerate."
                else:
                    reason = f"Allocated £{monthly:,.0f}/month based on priority weighting across all your goals."

            reasoning.append({
                "name": name,
                "monthly": monthly,
                "type": pot_type,
                "target": target,
                "months": months,
                "reason": reason
            })

    summary = get_plan_summary(plan) if "error" not in plan else ""

    return render_template("plan_review.html",
        plan=plan,
        reasoning=reasoning,
        profile=user_profile,
        summary=summary
    )

# ─── WITHDRAWAL ───────────────────────────────────────────

@page_bp.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
    if not current_user.factfind_completed or not current_user.monthly_income:
        flash("Complete your financial profile first.", "error")
        return redirect(url_for("pages.factfind"))

    user_profile = current_user.profile_dict()
    goals_data = [g.to_dict() for g in Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()]

    plan = generate_financial_plan(user_profile, goals_data)
    result = None

    if request.method == "POST" and "error" not in plan:
        try:
            amount = round(float(request.form.get("amount", 0)), 2)
            if amount > 0:
                result = get_withdrawal_options(plan, amount)
        except (ValueError, TypeError):
            flash("Please enter a valid amount.", "error")

    return render_template("withdraw.html", plan=plan, result=result)

# ─── LIFE CHECK-IN ────────────────────────────────────────

@page_bp.route("/life-checkin", methods=["GET", "POST"])
@login_required
def life_checkin():
    today = date.today()

    if request.method == "POST":
        checkin_type = request.form.get("checkin_type", "all_good")
        details = request.form.get("details", "").strip() or None
        amount = None

        try:
            amt = request.form.get("amount", "")
            if amt:
                amount = round(float(amt), 2)
        except (ValueError, TypeError):
            pass

        life_ci = LifeCheckIn(
            user_id=current_user.id,
            checkin_type=checkin_type,
            details=details,
            amount=amount
        )
        db.session.add(life_ci)

        current_user.last_life_checkin = today
        db.session.commit()

        if checkin_type == "all_good":
            flash("Great — your plan stays on track.", "success")
            return redirect(url_for("pages.overview"))

        elif checkin_type == "birthday":
            if amount and amount > 0:
                event_name = details or "Birthday / event"
                deadline = today + relativedelta(months=1)
                goal = Goal(
                    user_id=current_user.id,
                    name=event_name,
                    type="savings_target",
                    target_amount=amount,
                    current_amount=0,
                    deadline=deadline,
                    priority_rank=99
                )
                db.session.add(goal)
                life_ci.plan_adjusted = True
                db.session.commit()
                flash(f"Added '{event_name}' to your goals. Your plan has adjusted.", "success")
            else:
                flash("Got it — let us know if you need to budget for it.", "success")
            return redirect(url_for("pages.overview"))

        elif checkin_type == "unexpected_expense":
            if amount and amount > 0:
                flash(f"Noted: £{amount:,.0f} unexpected expense. Use the companion to work out the best way to cover it.", "success")
            else:
                flash("Got it. If you need to pull money from your plan, the companion can help.", "success")
            return redirect(url_for("pages.overview"))

        elif checkin_type == "income_changed":
            if amount and amount > 0:
                current_user.monthly_income = amount
                life_ci.plan_adjusted = True
                db.session.commit()
                flash(f"Income updated to £{amount:,.0f}. Your plan has recalculated.", "success")
            else:
                flash("Head to your profile to update your income.", "success")
                return redirect(url_for("pages.factfind"))
            return redirect(url_for("pages.overview"))

        elif checkin_type == "new_goal":
            return redirect(url_for("pages.goal_chips"))

        elif checkin_type == "bill_changed":
            flash("Update your bills in your financial profile.", "success")
            return redirect(url_for("pages.factfind"))

        elif checkin_type == "ask_later":
            flash("No problem — we'll check in again soon.", "success")
            return redirect(url_for("pages.overview"))

        return redirect(url_for("pages.overview"))

    return render_template("life_checkin.html")

# ─── TRIAL GATE ───────────────────────────────────────────

@page_bp.route("/trial")
@login_required
def trial_gate():
    if not current_user.factfind_completed:
        return redirect(url_for("pages.factfind"))

    user_profile = current_user.profile_dict()
    goals_data = [g.to_dict() for g in Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()]

    plan = generate_financial_plan(user_profile, goals_data)

    # Calculate trial end date (14 days from now)
    from datetime import timedelta
    trial_end = (date.today() + timedelta(days=14)).strftime("%d %B %Y")

    return render_template("trial_gate.html",
        plan=plan,
        trial_end_date=trial_end
    )


@page_bp.route("/checkout")
@login_required
def checkout():
    # Placeholder — Stripe integration goes here
    # For now, set user to trial and redirect to overview
    from datetime import timedelta
    current_user.subscription_tier = "pro_plus"
    current_user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
    db.session.commit()
    flash("Your 14-day Pro+ trial has started.", "success")
    return redirect(url_for("pages.overview"))

# ─── SETTINGS ────────────────────────────────────────────

@page_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@page_bp.route("/update-theme", methods=["POST"])
@login_required
def update_theme():
    theme = request.form.get("theme", "racing-green")
    valid = ["racing-green", "midnight-navy", "oxford-saddle", "amethyst",
             "rosso", "cobalt", "ivory", "pearl", "sandstone", "sage", "lavender", "mist"]
    if theme not in valid:
        theme = "racing-green"

    current_user.theme = theme
    db.session.commit()
    flash("Theme updated", "success")
    return redirect(url_for("pages.settings"))


# ─── FACTFIND ────────────────────────────────────────────

@page_bp.route("/factfind", methods=["GET", "POST"])
@login_required
def factfind():
    if request.method == "POST":
        try:
            monthly_income = round(float(request.form.get("monthly_income", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid income amount", "error")
            return redirect(url_for("pages.factfind"))

        if monthly_income <= 0:
            flash("Monthly income must be greater than zero", "error")
            return redirect(url_for("pages.factfind"))

        try:
            rent_amount = round(float(request.form.get("rent_amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid rent amount", "error")
            return redirect(url_for("pages.factfind"))

        try:
            bills_amount = round(float(request.form.get("bills_amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid bills amount", "error")
            return redirect(url_for("pages.factfind"))

        income_day = request.form.get("income_day", type=int)

        try:
            groceries_estimate = round(float(request.form.get("groceries_estimate", 0)), 2)
        except (ValueError, TypeError):
            groceries_estimate = 0

        try:
            transport_estimate = round(float(request.form.get("transport_estimate", 0)), 2)
        except (ValueError, TypeError):
            transport_estimate = 0

        current_user.monthly_income = monthly_income
        current_user.rent_amount = rent_amount
        current_user.bills_amount = bills_amount
        current_user.groceries_estimate = groceries_estimate
        current_user.transport_estimate = transport_estimate
        try:
            subscriptions_total = round(float(request.form.get("subscriptions_total", 0)), 2)
        except (ValueError, TypeError): 
            subscriptions_total = 0
        current_user.subscriptions_total = subscriptions_total
        try:
            other_commitments = round(float(request.form.get("other_commitments", 0)), 2)
        except (ValueError, TypeError):
            other_commitments = 0
        current_user.other_commitments = other_commitments
        current_user.income_day = income_day
        was_already_completed = current_user.factfind_completed
        current_user.factfind_completed = True

        db.session.commit()
        flash("Financial profile updated" if was_already_completed else "Financial profile saved", "success")
        if was_already_completed:
            return redirect(url_for("pages.settings"))
        return redirect(url_for("pages.surplus_reveal"))

    return render_template("factfind.html", profile=current_user.profile_dict())


# ─── UPLOAD & ADD ────────────────────────────────────────

@page_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_statement():
    result = None

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file provided", "error")
            return redirect(url_for("pages.upload_statement"))

        file = request.files["file"]
        if file.filename == "":
            flash("No file selected", "error")
            return redirect(url_for("pages.upload_statement"))

        if not file.filename.lower().endswith(".csv"):
            flash("File must be a CSV", "error")
            return redirect(url_for("pages.upload_statement"))

        file_content = file.read()
        if len(file_content) == 0:
            flash("File is empty", "error")
            return redirect(url_for("pages.upload_statement"))

        if len(file_content) > 5 * 1024 * 1024:
            flash("File too large", "error")
            return redirect(url_for("pages.upload_statement"))

        try:
            parse_result = extract_transactions_from_csv(file_content)
        except CSVParseError as e:
            flash(str(e), "error")
            return redirect(url_for("pages.upload_statement"))

        if not parse_result["transactions"]:
            flash("No valid transactions found", "error")
            return redirect(url_for("pages.upload_statement"))

        other_category = Category.query.filter_by(name="Other").first()
        other_id = other_category.id if other_category else 1

        existing = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id != other_id
        ).all()

        training_data = [{"description": t.description, "category": t.category_rel.name}
                         for t in existing if t.category_rel]

        categoriser = build_categoriser_for_user(training_data) if training_data else None
        categorised = categorise_transactions(parse_result["transactions"], categoriser)

        categories_all = Category.query.all()
        category_lookup = {c.name: c.id for c in categories_all}

        created_count = 0
        skipped_count = 0
        auto_categorised_count = 0

        for t in categorised:
            existing_t = Transaction.query.filter_by(
                user_id=current_user.id, amount=t["amount"],
                description=t["description"], date=t["date"], type=t["type"]
            ).first()

            if existing_t:
                skipped_count += 1
                continue

            suggested = t.get("suggested_category", "Other")
            category_id = category_lookup.get(suggested, other_id)
            if suggested != "Other":
                auto_categorised_count += 1

            transaction = Transaction(
                user_id=current_user.id, amount=t["amount"],
                description=t["description"], category_id=category_id,
                type=t["type"], date=t["date"], merchant=t.get("merchant")
            )
            db.session.add(transaction)
            created_count += 1

        db.session.commit()

        # Run insight analysis on the full dataset (including just-imported transactions)
        txn_list_post = _get_txn_list()
        recurring_result = detect_recurring_transactions(txn_list_post)
        savings_result = identify_potential_savings(recurring_result["recurring"])

        # Build personalised "what we found" summary
        recurring_count = recurring_result.get("expense_count", 0)
        recurring_total = recurring_result.get("total_monthly_cost", 0)
        savings_count = savings_result.get("count", 0)
        top_savings = savings_result.get("opportunities", [])[:2]

        # Date range of imported transactions
        imported_dates = [t["date"] for t in categorised if t.get("date")]
        date_range = None
        if imported_dates:
            earliest = min(imported_dates)
            latest = max(imported_dates)
            if earliest != latest:
                date_range = f"{earliest.strftime('%b %Y')} – {latest.strftime('%b %Y')}"

        result = {
            "bank_detected": parse_result["bank_detected"],
            "created": created_count, "skipped": skipped_count,
            "auto_categorised": auto_categorised_count,
            "errors": parse_result["errors"],
            "error_count": parse_result["error_count"],
            # Personalised insight data
            "recurring_count": recurring_count,
            "recurring_total": recurring_total,
            "savings_count": savings_count,
            "top_savings": top_savings,
            "date_range": date_range,
        }

    return render_template("upload.html", result=result)


@page_bp.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == "POST":
        try:
            amount = round(float(request.form.get("amount", 0)), 2)
        except (ValueError, TypeError):
            flash("Invalid amount", "error")
            return redirect(url_for("pages.add_transaction"))

        if amount <= 0:
            flash("Amount must be greater than zero", "error")
            return redirect(url_for("pages.add_transaction"))

        description = request.form.get("description", "").strip()
        if not description:
            flash("Description is required", "error")
            return redirect(url_for("pages.add_transaction"))

        transaction_type = request.form.get("type", "expense")
        category_id = request.form.get("category_id", type=int)
        merchant = request.form.get("merchant", "").strip() or None

        if not category_id:
            other = Category.query.filter_by(name="Other").first()
            category_id = other.id if other else 1

        try:
            transaction_date = date.fromisoformat(request.form.get("date", ""))
        except (ValueError, TypeError):
            flash("Invalid date", "error")
            return redirect(url_for("pages.add_transaction"))

        transaction = Transaction(
            user_id=current_user.id, amount=amount, description=description,
            category_id=category_id, type=transaction_type,
            date=transaction_date, merchant=merchant
        )
        db.session.add(transaction)
        db.session.commit()
        flash("Transaction recorded", "success")
        return redirect(url_for("pages.my_money"))

    categories = Category.query.order_by(Category.name).all()
    return render_template("add_transaction.html", categories=categories)


@page_bp.route("/delete-transaction/<int:transaction_id>", methods=["POST"])
@login_required
def delete_transaction(transaction_id):
    transaction = Transaction.query.filter_by(
        id=transaction_id, user_id=current_user.id).first()
    if not transaction:
        flash("Transaction not found", "error")
        return redirect(url_for("pages.my_money"))

    db.session.delete(transaction)
    db.session.commit()
    flash("Transaction deleted", "success")
    return redirect(url_for("pages.my_money"))


# ─── GOALS ────────────────────────────────────────────────

@page_bp.route("/add-goal", methods=["GET", "POST"])
@login_required
def add_goal():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        goal_type = request.form.get("type", "savings_target")
        priority_rank = request.form.get("priority_rank", 1, type=int)

        if not name:
            flash("Goal name is required", "error")
            return redirect(url_for("pages.add_goal"))

        target_amount = None
        val = request.form.get("target_amount", "").strip()
        if val:
            try:
                target_amount = round(float(val), 2)
            except ValueError:
                pass

        current_amount = 0
        val = request.form.get("current_amount", "").strip()
        if val:
            try:
                current_amount = round(float(val), 2)
            except ValueError:
                pass

        monthly_allocation = None
        val = request.form.get("monthly_allocation", "").strip()
        if val:
            try:
                monthly_allocation = round(float(val), 2)
            except ValueError:
                pass

        deadline = None
        val = request.form.get("deadline", "").strip()
        if val:
            try:
                deadline = date.fromisoformat(val)
            except ValueError:
                pass

        goal = Goal(
            user_id=current_user.id, name=name, type=goal_type,
            target_amount=target_amount, current_amount=current_amount,
            monthly_allocation=monthly_allocation, deadline=deadline,
            priority_rank=priority_rank
        )
        db.session.add(goal)
        db.session.commit()
        flash("Goal created", "success")
        return redirect(url_for("pages.my_goals"))

    return render_template("add_goal.html")


@page_bp.route("/delete-goal/<int:goal_id>", methods=["POST"])
@login_required
def delete_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()
    if not goal:
        flash("Goal not found", "error")
        return redirect(url_for("pages.my_goals"))

    db.session.delete(goal)
    db.session.commit()
    flash("Goal deleted", "success")
    return redirect(url_for("pages.my_goals"))


@page_bp.route("/goal/<int:goal_id>/edit", methods=["GET", "POST"])
@login_required
def edit_goal(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Goal name is required", "error")
            return redirect(url_for("pages.edit_goal", goal_id=goal_id))

        goal.name = name

        val = request.form.get("target_amount", "").strip()
        goal.target_amount = round(float(val), 2) if val else None

        val = request.form.get("current_amount", "").strip()
        if val:
            try:
                goal.current_amount = round(float(val), 2)
            except ValueError:
                pass

        val = request.form.get("monthly_allocation", "").strip()
        goal.monthly_allocation = round(float(val), 2) if val else None

        val = request.form.get("deadline", "").strip()
        if val:
            try:
                goal.deadline = date.fromisoformat(val)
            except ValueError:
                goal.deadline = None
        else:
            goal.deadline = None

        priority = request.form.get("priority_rank", type=int)
        if priority and priority >= 1:
            goal.priority_rank = priority

        db.session.commit()
        flash("Goal updated", "success")
        return redirect(url_for("pages.my_goals"))

    return render_template("edit_goal.html", goal=goal)


@page_bp.route("/simulator/goal/<int:goal_id>")
@login_required
def goal_detail(goal_id):
    goal = Goal.query.filter_by(id=goal_id, user_id=current_user.id).first()

    if not goal:
        flash("Goal not found", "error")
        return redirect(url_for("pages.my_goals"))

    if not goal.target_amount:
        flash("This goal has no target to project", "error")
        return redirect(url_for("pages.my_goals"))

    contribution = float(goal.monthly_allocation) if goal.monthly_allocation else 0
    goal_data = {
        "target_amount": float(goal.target_amount),
        "current_amount": float(goal.current_amount) if goal.current_amount else 0
    }

    projection = project_goal_timeline(goal_data, contribution)
    multi_horizon = generate_multi_horizon_projection(goal_data, contribution)

    if current_user.factfind_completed and current_user.monthly_income:
        max_contribution = max(contribution * 2.5, current_user.monthly_surplus, 500)
    else:
        max_contribution = max(contribution * 2.5, 1000)

    max_contribution = round(max_contribution / 10) * 10
    slider_percent = round((contribution / max_contribution * 100), 1) if max_contribution > 0 else 50

    return render_template("goal_detail.html",
        goal=goal, projection=projection, multi_horizon=multi_horizon,
        max_contribution=max_contribution, slider_percent=slider_percent
    )


# ─── SCENARIO ────────────────────────────────────────────

@page_bp.route("/scenario", methods=["GET", "POST"])
@login_required
def scenario_page():
    if not current_user.factfind_completed:
        flash("Complete your financial profile first", "error")
        return redirect(url_for("pages.factfind"))

    goals = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    goals_list = [{
        "id": g.id, "name": g.name, "type": g.type,
        "target_amount": float(g.target_amount) if g.target_amount else None,
        "current_amount": float(g.current_amount) if g.current_amount else 0,
        "monthly_allocation": float(g.monthly_allocation) if g.monthly_allocation else 0,
        "priority_rank": g.priority_rank
    } for g in goals]

    current_income = float(current_user.monthly_income)
    current_commitments = current_user.fixed_commitments

    scenario_result = None

    if request.method == "POST":
        try:
            proposed_income = round(float(request.form.get("monthly_income", current_income)), 2)
            proposed_commitments = round(float(request.form.get("fixed_commitments", current_commitments)), 2)
        except (ValueError, TypeError):
            flash("Invalid numbers", "error")
            return redirect(url_for("pages.scenario_page"))

        spending_changes = {}
        for g in goals_list:
            form_value = request.form.get(f"goal_{g['id']}")
            if form_value:
                try:
                    spending_changes[str(g["id"])] = round(float(form_value), 2)
                except (ValueError, TypeError):
                    pass

        current_state = {
            "monthly_income": current_income,
            "fixed_commitments": current_commitments,
            "goals": goals_list
        }

        proposed_changes = {
            "monthly_income": proposed_income,
            "fixed_commitments": proposed_commitments,
            "spending_changes": spending_changes
        }

        scenario_result = simulate_scenario(current_state, proposed_changes)

    return render_template("scenario.html",
        goals=goals_list, current_income=current_income,
        current_commitments=current_commitments,
        scenario_result=scenario_result
    )


# ─── BUDGETS ─────────────────────────────────────────────

@page_bp.route("/budgets/create", methods=["POST"])
@login_required
def create_budget_page():
    category_id = request.form.get("category_id", type=int)
    monthly_limit = request.form.get("monthly_limit", type=float)

    if not category_id or not monthly_limit or monthly_limit <= 0:
        flash("Please select a category and enter a valid limit", "error")
        return redirect(url_for("pages.my_budgets"))

    existing = Budget.query.filter_by(
        user_id=current_user.id, category_id=category_id, is_active=True).first()
    if existing:
        flash("A budget already exists for this category", "error")
        return redirect(url_for("pages.my_budgets"))

    budget = Budget(
        user_id=current_user.id, category_id=category_id,
        monthly_limit=round(monthly_limit, 2)
    )
    db.session.add(budget)
    db.session.commit()
    flash("Budget created", "success")
    return redirect(url_for("pages.my_budgets"))


@page_bp.route("/budgets/<int:budget_id>/delete", methods=["POST"])
@login_required
def delete_budget(budget_id):
    budget = Budget.query.filter_by(
        id=budget_id, user_id=current_user.id).first()
    if not budget:
        flash("Budget not found", "error")
        return redirect(url_for("pages.my_budgets"))

    db.session.delete(budget)
    db.session.commit()
    flash("Budget removed", "success")
    return redirect(url_for("pages.my_budgets"))


# ─── ANALYTICS ────────────────────────────────────────────

@page_bp.route("/analytics")
@login_required
def analytics():
    today = date.today()
    month_name = today.strftime("%B")
    year = today.year

    current_month = today.month
    current_year = today.year
    prev_month = current_month - 1 if current_month > 1 else 12
    prev_year = current_year if current_month > 1 else current_year - 1

    results = db.session.query(
        Category.name, Category.icon, Category.colour,
        func.sum(Transaction.amount).label("total"),
        func.count(Transaction.id).label("count")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == current_month,
        extract("year", Transaction.date) == current_year
    ).group_by(
        Category.id, Category.name, Category.icon, Category.colour
    ).order_by(func.sum(Transaction.amount).desc()).all()

    total_expenses = sum(float(r.total) for r in results)
    categories = []
    for r in results:
        amount = float(r.total)
        categories.append({
            "name": r.name, "icon": r.icon, "colour": r.colour,
            "total": amount, "count": r.count,
            "percentage": round((amount / total_expenses * 100), 1) if total_expenses > 0 else 0
        })

    prev_cat = db.session.query(
        Category.name, func.sum(Transaction.amount).label("total")
    ).join(Category, Transaction.category_id == Category.id).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == prev_month,
        extract("year", Transaction.date) == prev_year
    ).group_by(Category.id, Category.name).all()

    prev_dict = {r.name: float(r.total) for r in prev_cat}

    trends = []
    for r in results:
        current_total = float(r.total)
        prev_total = prev_dict.get(r.name, 0)
        if prev_total > 0:
            change = current_total - prev_total
            pct = round((change / prev_total) * 100, 1)
        else:
            change = current_total
            pct = 100.0
        trends.append({
            "category": r.name, "icon": r.icon, "colour": r.colour,
            "current_month": round(current_total, 2),
            "previous_month": round(prev_total, 2),
            "change_amount": round(change, 2),
            "change_percent": pct,
            "direction": "up" if change > 0 else "down" if change < 0 else "flat"
        })
    trends.sort(key=lambda t: abs(t["change_amount"]), reverse=True)

    return render_template("analytics.html",
        month_name=month_name, year=year,
        total_expenses=total_expenses,
        categories=categories,
        trends=trends
    )


# ─── INSIGHTS ─────────────────────────────────────────────

@page_bp.route("/insights")
@login_required
def insights():
    data = _build_whisper_data()

    budget_status = None
    if current_user.factfind_completed and current_user.monthly_income:
        budget_status = calc_prediction_budget_status(
            data["predictions"],
            {"monthly_income": float(current_user.monthly_income),
             "fixed_commitments": current_user.fixed_commitments or 0},
            [{"id": g["id"], "name": g["name"],
              "monthly_allocation": g.get("monthly_allocation", 0)}
             for g in data["goals"]]
        )

    return render_template("insights.html",
        predictions=data["predictions"],
        budget_status=budget_status
    )


# ─── RECURRING ────────────────────────────────────────────

@page_bp.route("/recurring")
@login_required
def recurring():
    data = _build_whisper_data()
    return render_template("recurring.html",
        recurring=data["recurring"],
        savings=data["savings_opportunities"]
    )


# ─── ACCOUNT SETTINGS ─────────────────────────────────────

@page_bp.route("/update-account", methods=["POST"])
@login_required
def update_account():
    form_type = request.form.get("form_type")

    if form_type == "change_name":
        new_name = request.form.get("new_name", "").strip()
        if not new_name:
            flash("Name is required", "error")
            return redirect(url_for("pages.settings"))
        if len(new_name) > 100:
            flash("Name is too long", "error")
            return redirect(url_for("pages.settings"))
        current_user.name = new_name
        db.session.commit()
        flash("Name updated", "success")

    elif form_type == "change_email":
        new_email = request.form.get("new_email", "").strip()
        password = request.form.get("confirm_password_email", "")

        if not new_email:
            flash("Email address is required", "error")
            return redirect(url_for("pages.settings"))

        if not current_user.check_password(password):
            flash("Incorrect password", "error")
            return redirect(url_for("pages.settings"))

        if User.query.filter(User.email == new_email, User.id != current_user.id).first():
            flash("That email is already in use", "error")
            return redirect(url_for("pages.settings"))

        current_user.email = new_email
        db.session.commit()
        flash("Email updated", "success")

    elif form_type == "change_password":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_user.check_password(current_password):
            flash("Current password is incorrect", "error")
            return redirect(url_for("pages.settings"))

        if len(new_password) < 8:
            flash("New password must be at least 8 characters", "error")
            return redirect(url_for("pages.settings"))

        if new_password != confirm_password:
            flash("Passwords do not match", "error")
            return redirect(url_for("pages.settings"))

        current_user.set_password(new_password)
        db.session.commit()
        flash("Password updated", "success")

    return redirect(url_for("pages.settings"))


# ─── ONBOARDING ───────────────────────────────────────────

@page_bp.route("/welcome")
@login_required
def welcome():
    has_transactions = Transaction.query.filter_by(user_id=current_user.id).first() is not None
    has_goals = Goal.query.filter_by(user_id=current_user.id).first() is not None

    steps_done = sum([
        current_user.factfind_completed,
        has_goals
    ])

    if steps_done == 2:
        return redirect(url_for("pages.overview"))

    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    return render_template("welcome.html",
        greeting=greeting,
        profile_done=current_user.factfind_completed,
        goals_done=has_goals,
        steps_done=steps_done
    )

@page_bp.route("/unsubscribe")
def unsubscribe():
    # TODO: when email preferences are built, mark current_user as opted out here.
    # For now, a polite confirmation page so the link doesn't 404.
    return render_template("unsubscribe.html")
