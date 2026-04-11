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
    """Calculates money left to spend this month."""
    if not current_user.factfind_completed or not current_user.monthly_income:
        return None, 0

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_remaining = days_in_month - today.day

    current_month_expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == current_user.id,
        Transaction.type == "expense",
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    ).scalar()

    goals = Goal.query.filter_by(user_id=current_user.id, status="active").all()
    total_goal_allocation = sum(
        float(g.monthly_allocation) if g.monthly_allocation else 0
        for g in goals
    )

    disposable = current_user.monthly_surplus - total_goal_allocation
    money_left = round(disposable - float(current_month_expenses), 2)

    return money_left, days_remaining


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
        flash("Account created successfully", "success")
        return redirect(url_for("pages.welcome"))

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
            return redirect(url_for("pages.login"))

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
    whisper_result = generate_page_insights("overview", data)

    income = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="income").scalar()

    expenses = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="expense").scalar()

    recent = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.date.desc()).limit(5).all()

    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    budget_status = None
    if current_user.monthly_income:
        budget_status = calc_prediction_budget_status(
            data["predictions"],
            {"monthly_income": float(current_user.monthly_income),
             "fixed_commitments": current_user.fixed_commitments},
            [{"id": g["id"], "name": g["name"],
              "monthly_allocation": g.get("monthly_allocation", 0)}
             for g in data["goals"]]
        )

    # Intelligence summary — ambient AI layer
    today = date.today()
    day_of_month = today.day
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    recurring_data = data.get("recurring", {})
    recurring_count = recurring_data.get("expense_count", 0)
    recurring_total = recurring_data.get("total_monthly_cost", 0)

    predictions = data.get("predictions", {})
    comparison = predictions.get("comparison", {})
    spending_direction = comparison.get("status", "")  # "spending_high" | "spending_low" | "on_track"
    spending_diff = comparison.get("difference", 0)

    # Month-context framing
    month_context = None
    if day_of_month <= 7:
        month_context = "start"  # "here's how last month went"
    elif day_of_month >= days_in_month - 4:
        month_context = "end"    # "X days left"

    intel = {
        "recurring_count": recurring_count,
        "recurring_total": recurring_total,
        "spending_direction": spending_direction,
        "spending_diff": abs(spending_diff) if spending_diff else 0,
        "month_context": month_context,
        "days_remaining": data["days_remaining"],
    } if recurring_count > 0 or spending_direction else None

    memory_card = _build_memory_card(data)

    # Goal projection hero — pick the primary goal's projection if reachable
    projections = data.get("projections", [])
    primary_projection = None
    if projections and data["primary_goal"]:
        primary_goal_id = data["primary_goal"].get("id")
        for p in projections:
            if p.get("goal_id") == primary_goal_id and p.get("reachable"):
                primary_projection = p
                break

    # One-sentence timeline driver — what's pushing or pulling the date
    timeline_note = None
    if primary_projection:
        trends = data.get("trends", [])
        if spending_direction == "spending_high" and spending_diff and spending_diff > 0:
            timeline_note = f"Your current spending pace is pushing this date back."
        elif spending_direction == "spending_low" and spending_diff and spending_diff > 0:
            timeline_note = f"You're under your usual pace — this could arrive sooner."
        elif trends:
            top = trends[0]
            if top["direction"] == "up" and top["change_amount"] > 20:
                timeline_note = f"Your {top['category'].lower()} spend is up this month — worth keeping an eye on."

    return render_template("overview.html",
        greeting=greeting,
        whisper=whisper_result["whisper"],
        money_left=data["money_left"],
        days_remaining=data["days_remaining"],
        budget_status=budget_status,
        primary_goal=data["primary_goal"] if data["primary_goal"] else None,
        active_goals_count=data["active_goals"],
        intel=intel,
        memory_card=memory_card,
        primary_projection=primary_projection,
        timeline_note=timeline_note,
        summary={
            "total_income": float(income),
            "total_expenses": float(expenses),
            "balance": float(income) - float(expenses)
        },
        recent_transactions=[t.to_dict() for t in recent]
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

    return render_template("my_money.html",
        whisper=whisper_result["whisper"],
        month_name=month_name,
        total_expenses=total_expenses,
        categories=categories,
        trends=data["trends"],
        transactions=[t.to_dict() for t in all_transactions]
    )


# ─── MY GOALS ────────────────────────────────────────────

@page_bp.route("/my-goals", methods=["GET", "POST"])
@login_required
def my_goals():
    data = _build_whisper_data()
    whisper_result = generate_page_insights("my_goals", data)

    goals = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    # Habit cost calculator
    habit_result = None
    habit_amount = None
    habit_description = None

    if request.method == "POST" and request.form.get("form_type") == "habit_cost":
        try:
            habit_amount = round(float(request.form.get("habit_amount", 0)), 2)
            habit_description = request.form.get("habit_description", "").strip() or "This habit"
            if habit_amount > 0:
                habit_result = calculate_cost_of_habit(habit_amount)
                habit_result["description"] = habit_description
        except (ValueError, TypeError):
            flash("Invalid amount", "error")

    return render_template("my_goals.html",
        whisper=whisper_result["whisper"],
        goals=[g.to_dict() for g in goals],
        waterfall=data["waterfall"],
        projections=data["projections"],
        habit_result=habit_result,
        habit_amount=habit_amount,
        habit_description=habit_description
    )


# ─── PLAN ────────────────────────────────────────────────

@page_bp.route("/plan", methods=["GET", "POST"])
@login_required
def plan():
    data = _build_whisper_data()

    habit_result = None
    habit_amount = None
    habit_description = None

    if request.method == "POST" and request.form.get("form_type") == "habit_cost":
        try:
            habit_amount = round(float(request.form.get("habit_amount", 0)), 2)
            habit_description = request.form.get("habit_description", "").strip() or "This habit"
            if habit_amount > 0:
                habit_result = calculate_cost_of_habit(habit_amount)
                habit_result["description"] = habit_description
        except (ValueError, TypeError):
            flash("Invalid amount", "error")

    return render_template("plan.html",
        waterfall=data["waterfall"],
        projections=data["projections"],
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

        current_user.monthly_income = monthly_income
        current_user.rent_amount = rent_amount
        current_user.bills_amount = bills_amount
        current_user.income_day = income_day
        current_user.factfind_completed = True

        db.session.commit()
        flash("Financial profile saved", "success")
        return redirect(url_for("pages.overview"))

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
            "category": r.name, "icon": r.icon,
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
             "fixed_commitments": current_user.fixed_commitments},
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

    if form_type == "change_email":
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
        has_transactions,
        has_goals
    ])

    if steps_done == 3:
        return redirect(url_for("pages.overview"))

    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    return render_template("welcome.html",
        greeting=greeting,
        profile_done=current_user.factfind_completed,
        transactions_done=has_transactions,
        goals_done=has_goals,
        steps_done=steps_done
    )

@page_bp.route("/unsubscribe")
def unsubscribe():
    # TODO: when email preferences are built, mark current_user as opted out here.
    # For now, a polite confirmation page so the link doesn't 404.
    return render_template("unsubscribe.html")
