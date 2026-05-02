from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt, limiter
from app.utils.validators import (
    sanitize_string,
    validate_amount,
    validate_email,
    validate_int,
    validate_name,
    validate_password,
)
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
from app.services.withdrawal_service import calculate_withdrawal_strategy
from app.models.life_checkin import LifeCheckIn
from app.models.checkin import CheckInEntry
from app.utils.auth import is_subscription_active, requires_subscription
from app.services.analytics_service import track_event, identify_user
from app.services.account_service import delete_user_account
from sqlalchemy.exc import IntegrityError
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


def _auto_complete_finished_goals():
    """Mark any active goal whose current balance has reached its target as
    completed. Idempotent — safe to call on every page load."""
    finished = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).all()
    changed = False
    for g in finished:
        if g.target_amount and g.current_amount is not None:
            try:
                if float(g.current_amount) >= float(g.target_amount):
                    g.status = "completed"
                    changed = True
            except (TypeError, ValueError):
                continue
    if changed:
        db.session.commit()


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
    return render_template("splash.html")


@page_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per minute, 10 per hour", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.overview"))

    if request.method == "POST":
        try:
            name = validate_name(request.form.get("name", ""), max_length=100)
            email = validate_email(request.form.get("email", ""))
            password = validate_password(request.form.get("password", ""))
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("pages.register"))

        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists", "error")
            return redirect(url_for("pages.register"))

        user = User(email=email, name=name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        identify_user(user.id, {
            "email": user.email,
            "name": user.name,
            "tier": user.subscription_tier or "free",
            "signup_date": (user.created_at or datetime.utcnow()).isoformat(),
        })
        track_event(user.id, "user_signed_up", {"email_domain": email.split("@")[-1] if "@" in email else None})
        return redirect(url_for("pages.welcome"))

    return render_template("register.html")


@page_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute, 20 per hour", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.overview"))

    if request.method == "POST":
        email = (request.form.get("email", "") or "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first() if email else None

        if not user or not user.check_password(password):
            flash("Invalid email or password", "error")
            return render_template("login.html", prefill_email=email)

        login_user(user)
        identify_user(user.id, {
            "email": user.email,
            "name": user.name,
            "tier": user.subscription_tier or "free",
            "signup_date": (user.created_at.isoformat() if user.created_at else None),
        })
        if not user.factfind_completed:
            return redirect(url_for("pages.welcome"))
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
    # Auto-complete any active goal whose balance has reached its target.
    # Without this, finished goals (e.g., a fully-paid credit card) keep
    # showing up as active and the plan phase never advances.
    _auto_complete_finished_goals()

    data = _build_whisper_data()
    first_overview = session.pop('first_overview', False)

    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    # TEMPORARY: local fallback — remove when webhooks are live on Render
    if request.args.get("checkout") == "success":
        from datetime import timedelta
        if (current_user.subscription_status or "none") == "none" or (current_user.subscription_tier or "free") == "free":
            current_user.subscription_tier = "pro_plus"
            current_user.subscription_status = "trialing"
            current_user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
            db.session.commit()

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
    plan_status = None
    nearest_milestone = None
    if smart_plan and "error" not in smart_plan:
        action_whisper = generate_action_whisper(current_user, smart_plan, data["goals"])
        if action_whisper:
            if action_whisper.get("type") == "setup":
                plan_status = "setting_up"
            elif action_whisper.get("type") == "payday":
                plan_status = "payday"
        # Nearest milestone: pot with smallest months_to_target > 0 and has a goal_id
        pots_with_timeline = [
            p for p in (smart_plan.get("pots") or [])
            if p.get("goal_id") and p.get("months_to_target") and p["months_to_target"] > 0 and not p.get("completed")
        ]
        if pots_with_timeline:
            nearest_milestone = min(pots_with_timeline, key=lambda p: p["months_to_target"])

    # Total saved toward goals (sum of current balances across all pots with a goal)
    total_saved_toward_goals = 0.0
    debt_allocation = 0.0
    available_surplus = 0.0
    has_debt_goals = False
    if smart_plan and "error" not in smart_plan:
        total_saved_toward_goals = sum(
            float(p.get("current") or 0)
            for p in (smart_plan.get("pots") or [])
            if p.get("goal_id")
        )
        debt_keywords = ("credit card", "overdraft", "loan", "pay off", "debt")
        for pot in (smart_plan.get("pots") or []):
            name_low = (pot.get("name") or "").lower()
            is_debt = pot.get("type") == "debt" or any(k in name_low for k in debt_keywords)
            if is_debt and pot.get("monthly_amount", 0) > 0 and not pot.get("completed"):
                debt_allocation += float(pot.get("monthly_amount") or 0)
                has_debt_goals = True
        plan_surplus = float(smart_plan.get("surplus") or 0)
        available_surplus = round(plan_surplus - debt_allocation, 2)
        debt_allocation = round(debt_allocation, 2)

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

    # Life check-in nudge: show mid-month (days 13-16) once user is ≥14 days old
    # and hasn't done a life check-in this month
    show_life_checkin_nudge = False
    if current_user.created_at:
        days_since_signup = (datetime.now() - current_user.created_at).days
        day_of_month = today.day
        already_checked_in = (
            current_user.last_life_checkin is not None
            and current_user.last_life_checkin.month == today.month
            and current_user.last_life_checkin.year == today.year
        )
        if days_since_signup >= 14 and 13 <= day_of_month <= 16 and not already_checked_in:
            show_life_checkin_nudge = True

    never_started_trial = (
        not current_user.trial_ends_at
        and current_user.subscription_status in (None, "none", "")
    )
    is_frozen = (
        bool(current_user.factfind_completed)
        and (data["active_goals"] or 0) > 0
        and not is_subscription_active(current_user)
        and not never_started_trial
    )

    # ── Directed-toward-goals counter & next check-in line ──
    directed_amount = None
    directed_since = None
    checkin_state = None

    if not is_frozen and current_user.created_at and smart_plan and "error" not in smart_plan:
        signup_dt = current_user.created_at
        signup_date = signup_dt.date() if hasattr(signup_dt, "date") else signup_dt
        delta = relativedelta(today, signup_date)
        months_active = delta.years * 12 + delta.months
        surplus = float(smart_plan.get("surplus") or 0)
        if months_active >= 1 and surplus > 0:
            directed_amount = round(surplus * months_active, 2)
            if signup_dt.year == today.year:
                directed_since = signup_dt.strftime("%B")
            else:
                directed_since = signup_dt.strftime("%B %Y")

        # Next check-in: window is the last 3 days of the current calendar month;
        # the check-in covers the previous month.
        from app.models.checkin import CheckIn
        last_day = calendar.monthrange(today.year, today.month)[1]
        window_start_day = last_day - 2
        if today.month == 1:
            cover_month, cover_year = 12, today.year - 1
        else:
            cover_month, cover_year = today.month - 1, today.year
        already_done = CheckIn.query.filter_by(
            user_id=current_user.id, month=cover_month, year=cover_year
        ).first() is not None

        def _fmt(d):
            return f"{d.day} {d.strftime('%B')}"

        if already_done:
            if today.month == 12:
                nm, ny = 1, today.year + 1
            else:
                nm, ny = today.month + 1, today.year
            nm_last = calendar.monthrange(ny, nm)[1]
            next_date = date(ny, nm, nm_last)
            checkin_state = {
                "completed": True,
                "label": "Check-in complete",
                "next_date_str": _fmt(next_date),
            }
        elif today.day >= window_start_day:
            days_left = last_day - today.day
            if days_left == 0:
                label = "Check-in due today"
            elif days_left == 1:
                label = "Check-in due tomorrow"
            else:
                label = f"Check-in due in {days_left} days"
            checkin_state = {
                "completed": False,
                "label": label,
                "next_date_str": _fmt(date(today.year, today.month, last_day)),
            }
        else:
            next_date = date(today.year, today.month, window_start_day)
            days_until = (next_date - today).days
            checkin_state = {
                "completed": False,
                "label": f"Next check-in in {days_until} day{'s' if days_until != 1 else ''}",
                "next_date_str": _fmt(next_date),
            }

    # ── Savings rate, plan phase, date label, first name (slim shell shell) ──
    first_name = (current_user.name or "").split()[0] if current_user.name else ""
    date_label = today.strftime("%A, %d %B")

    savings_rate = None
    if smart_plan and "error" not in smart_plan:
        income_for_rate = float(current_user.monthly_income or 0)
        plan_surplus = float(smart_plan.get("surplus") or 0)
        if income_for_rate > 0 and plan_surplus > 0:
            savings_rate = round((plan_surplus / income_for_rate) * 100)

    plan_phase = None
    if smart_plan and "error" not in smart_plan:
        phases = smart_plan.get("phases") or []
        if phases:
            current_phase = phases[0]
            plan_phase = {
                "current": int(current_phase.get("phase") or 1),
                "total": len(phases),
                "description": current_phase.get("description", ""),
            }

    # Active goal count for the right-panel stat pill
    active_goals_for_pill = 0
    if smart_plan and "error" not in smart_plan:
        for pot in smart_plan.get("pots") or []:
            if pot.get("goal_id") and pot.get("monthly_amount", 0) > 0 and not pot.get("completed"):
                active_goals_for_pill += 1

    plan_surplus_value = 0.0
    if smart_plan and "error" not in smart_plan:
        plan_surplus_value = float(smart_plan.get("surplus") or 0)

    return render_template("overview.html",
        greeting=greeting,
        first_name=first_name,
        date_label=date_label,
        smart_plan=smart_plan,
        plan_summary=plan_summary,
        money_left=money_left,
        days_remaining=days_remaining,
        has_data=has_data,
        monthly_spending=float(expenses),
        expenses_this_month=float(expenses),
        monthly_income_txn=float(income),
        top_categories=categories,
        primary_goal=data["primary_goal"] if data["primary_goal"] else None,
        active_goals_count=data["active_goals"],
        active_goals_for_pill=active_goals_for_pill,
        action_whisper=action_whisper,
        plan_status=plan_status,
        nearest_milestone=nearest_milestone,
        total_saved_toward_goals=total_saved_toward_goals,
        show_life_checkin_nudge=show_life_checkin_nudge,
        is_frozen=is_frozen,
        first_overview=first_overview,
        directed_amount=directed_amount,
        directed_since=directed_since,
        checkin_state=checkin_state,
        debt_allocation=debt_allocation,
        available_surplus=available_surplus,
        has_debt_goals=has_debt_goals,
        savings_rate=savings_rate,
        plan_phase=plan_phase,
        plan_surplus_value=plan_surplus_value,
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

    never_started_trial = (
        not current_user.trial_ends_at
        and current_user.subscription_status in (None, "none", "")
    )
    is_frozen = (
        bool(current_user.factfind_completed)
        and (data["active_goals"] or 0) > 0
        and not is_subscription_active(current_user)
        and not never_started_trial
    )

    debt_monthly = 0.0
    has_debt_goals = False
    if smart_plan and "error" not in smart_plan:
        debt_keywords = ("credit card", "overdraft", "loan", "pay off", "debt")
        for pot in (smart_plan.get("pots") or []):
            name_low = (pot.get("name") or "").lower()
            is_debt = pot.get("type") == "debt" or any(k in name_low for k in debt_keywords)
            if is_debt and pot.get("monthly_amount", 0) > 0 and not pot.get("completed"):
                debt_monthly += float(pot.get("monthly_amount") or 0)
                has_debt_goals = True
        debt_monthly = round(debt_monthly, 2)

    # Withdrawal section state. The form on /plan submits to one of the
    # /plan/withdraw/* routes which stash the strategy in the session and
    # redirect back here. We render the section when the user has either
    # asked for it (?withdraw=1) or already has a stashed preview pending.
    withdrawal_preview = session.get("withdrawal_preview")
    show_withdraw = request.args.get("withdraw") == "1" or withdrawal_preview is not None
    if show_withdraw and request.args.get("withdraw") == "1" and not withdrawal_preview:
        # First time entering the section — fire the event once per visit.
        track_event(current_user.id, "withdrawal_started")

    return render_template("plan.html",
        waterfall=data["waterfall"],
        projections=data["projections"],
        smart_plan=smart_plan,
        plan_summary=plan_summary,
        afford_result=afford_result,
        habit_result=habit_result,
        habit_amount=habit_amount,
        habit_description=habit_description,
        is_frozen=is_frozen,
        debt_monthly=debt_monthly,
        has_debt_goals=has_debt_goals,
        show_withdraw=show_withdraw,
        withdrawal_preview=withdrawal_preview,
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

    # Edit mode: allow re-submission by deleting the existing record first
    edit_mode = request.args.get("edit") == "1"
    if edit_mode and existing:
        # Pre-fill pots with existing actual amounts so the form shows what was entered
        actual_map = {e["pot_name"]: e["actual_amount"] for e in (existing.to_dict().get("entries") or [])}
        for pot in pots_for_checkin:
            if pot["name"] in actual_map:
                pot["planned"] = actual_map[pot["name"]]

    if request.method == "POST":
        # Delete existing record if re-submitting (edit mode)
        if existing:
            from app.models.checkin import CheckInEntry as CIEntry
            CIEntry.query.filter_by(checkin_id=existing.id).delete()
            CheckIn.query.filter_by(id=existing.id).delete()
            db.session.flush()
            existing = None

        # Variable-income users can update their take-home for the new month.
        # Plan recalculates next page load since it reads current_user.monthly_income.
        if (current_user.employment_type or "full_time") != "full_time":
            raw_income = request.form.get("actual_income")
            if raw_income not in (None, ""):
                try:
                    new_income = validate_amount(
                        raw_income, "Income", min_val=0.01, max_val=1_000_000
                    )
                    current_user.monthly_income = new_income
                except ValueError:
                    pass

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
                actual = validate_amount(
                    request.form.get(form_key, 0) or 0,
                    "Contribution", min_val=0, max_val=1_000_000
                )
            except ValueError:
                actual = 0

            raw_note = request.form.get(f"note_{pot['name'].replace(' ', '_')}", "")
            note = sanitize_string(raw_note, max_length=500) or None

            entry = CheckInEntry(
                checkin_id=checkin_record.id,
                goal_id=pot.get("goal_id"),
                pot_name=pot["name"],
                planned_amount=pot["planned"],
                actual_amount=actual
            )
            db.session.add(entry)

            # Update goal current_amount — verify ownership before mutating
            if pot.get("goal_id") and actual > 0:
                goal = Goal.query.filter_by(
                    id=pot["goal_id"], user_id=current_user.id
                ).first()
                if goal:
                    old_amount = float(goal.current_amount or 0)
                    new_amount = round(old_amount + actual, 2)
                    goal.current_amount = new_amount

                    # Goal milestone tracking — fire when crossing 25/50/75/100% bands
                    if goal.target_amount and float(goal.target_amount) > 0:
                        target_f = float(goal.target_amount)
                        old_pct = (old_amount / target_f) * 100
                        new_pct = (new_amount / target_f) * 100
                        for milestone in (25, 50, 75, 100):
                            if old_pct < milestone <= new_pct:
                                track_event(current_user.id, "goal_milestone_hit", {
                                    "goal_id": goal.id,
                                    "goal_name": goal.name,
                                    "milestone_pct": milestone,
                                })

        db.session.commit()
        track_event(current_user.id, "checkin_completed", {
            "month": checkin_month,
            "year": checkin_year,
            "pots_count": len(pots_for_checkin),
        })
        flash("Check-in complete. Your plan has been updated.", "success")
        return redirect(url_for("pages.checkin"))

    # Get past check-ins for history
    past_checkins = CheckIn.query.filter_by(
        user_id=current_user.id
    ).order_by(CheckIn.year.desc(), CheckIn.month.desc()).limit(6).all()

    if not (existing and not edit_mode):
        track_event(current_user.id, "checkin_started", {
            "month": checkin_month,
            "year": checkin_year,
            "edit_mode": edit_mode,
        })

    return render_template("checkin.html",
        checkin_month=checkin_month_name,
        already_done=(existing is not None) and not edit_mode,
        existing=existing.to_dict() if (existing and not edit_mode) else None,
        pots=pots_for_checkin,
        smart_plan=smart_plan,
        past_checkins=[c.to_dict() for c in past_checkins],
        variable_income=(current_user.employment_type or "full_time") != "full_time",
        current_monthly_income=float(current_user.monthly_income) if current_user.monthly_income else 0
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
        track_event(current_user.id, "onboarding_stage2_completed", {
            "lifestyle_budget": lifestyle,
            "surplus": surplus,
        })

        return redirect(url_for("pages.goal_chips"))

    track_event(current_user.id, "partial_projection_1_viewed", {"surplus": surplus})
    return render_template("surplus_reveal.html",
        profile=profile,
        income=round(income, 2),
        essentials=round(essentials, 2),
        surplus=surplus,
        show_sidebar=False,
        show_header=False
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
            current_amount = 0
            if chip == "emergency":
                name = "Emergency fund"
                target = request.form.get("emergency_custom") or request.form.get("emergency_amount")
                try:
                    current_amount = round(float(request.form.get("emergency_current_savings") or 0), 2)
                except (ValueError, TypeError):
                    current_amount = 0

            elif chip == "house":
                name = "House deposit"
                target = request.form.get("house_custom") or request.form.get("house_amount")
                try:
                    current_amount = round(float(request.form.get("house_current_savings") or 0), 2)
                except (ValueError, TypeError):
                    current_amount = 0
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
                            current_amount=current_amount,
                            deadline=deadline,
                            priority_rank=len(selected)
                        )
                        db.session.add(goal)
                except (ValueError, TypeError):
                    pass

        db.session.commit()

        # ── Onboarding stage 3 + goals_added (multi-goal selection) ──
        ttc_minutes = None
        if current_user.created_at:
            elapsed = datetime.utcnow() - current_user.created_at
            ttc_minutes = round(elapsed.total_seconds() / 60, 2)
        track_event(current_user.id, "onboarding_stage3_completed", {
            "goals_count": len(selected),
            "time_to_onboarding_complete": ttc_minutes,
        })
        if selected:
            track_event(current_user.id, "goals_added", {
                "count": len(selected),
                "types": list(selected),
                "source": "goal_chips",
            })

        return redirect(url_for("pages.plan_reveal"))

    track_event(current_user.id, "partial_projection_2_viewed")
    return render_template("goal_chips.html", show_sidebar=False, show_header=False)


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

    # Build per-pot reasoning (formerly in plan_review)
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

    first_reveal = not current_user.plan_wizard_complete
    if first_reveal:
        current_user.plan_wizard_complete = True
        session['first_overview'] = True
        db.session.commit()
        track_event(current_user.id, "plan_revealed", {
            "phase_count": plan.get("phase_count") if "error" not in plan else None,
            "monthly_surplus": plan.get("surplus") if "error" not in plan else None,
        })

    return render_template("plan_reveal.html",
        plan=plan,
        reasoning=reasoning,
        summary=summary,
        show_sidebar=False,
        show_header=False
    )

# ─── PLAN REVIEW (Onboarding) — redirects to merged plan_reveal ──────────────
@page_bp.route("/onboarding/plan-review")
@login_required
def plan_review():
    return redirect(url_for("pages.plan_reveal"))

# ─── WITHDRAWAL ───────────────────────────────────────────
#
# The withdrawal flow is rendered inline on /plan. The three POST endpoints
# below stash state in the session and redirect back to /plan?withdraw=1.
#
# Lifecycle:
#   preview  -> stash {amount, result, decided=False}, both Yes/No visible
#   confirm  -> apply withdrawal to goals, clear session, flash success
#   dismiss  -> mark decided=True, recommendation stays visible, flash info


def _redirect_to_plan_withdraw():
    return redirect(url_for("pages.plan", withdraw=1))


def _build_user_plan():
    """Generate the current plan dict for the logged-in user."""
    user_profile = current_user.profile_dict()
    goals_data = [g.to_dict() for g in Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()]
    return generate_financial_plan(user_profile, goals_data)


@page_bp.route("/plan/withdraw/preview", methods=["POST"])
@login_required
@requires_subscription
def plan_withdraw_preview():
    if not current_user.factfind_completed or not current_user.monthly_income:
        flash("Complete your financial profile first.", "error")
        return redirect(url_for("pages.factfind"))

    raw_amount = request.form.get("amount", "")
    try:
        amount = round(float(raw_amount), 2)
    except (TypeError, ValueError):
        flash("Please enter a valid amount.", "error")
        return _redirect_to_plan_withdraw()

    if amount <= 0:
        flash("Please enter an amount greater than zero.", "error")
        return _redirect_to_plan_withdraw()

    plan = _build_user_plan()
    if "error" in plan:
        flash("Your plan is not ready yet.", "error")
        return redirect(url_for("pages.plan"))

    result = calculate_withdrawal_strategy(plan.get("pots", []), amount)
    session["withdrawal_preview"] = {
        "amount": amount,
        "result": result,
        "decided": False,
    }
    track_event(current_user.id, "withdrawal_preview_generated", {"amount": amount})
    return _redirect_to_plan_withdraw()


@page_bp.route("/plan/withdraw/confirm", methods=["POST"])
@login_required
@requires_subscription
def plan_withdraw_confirm():
    preview = session.get("withdrawal_preview")
    if not preview or not preview.get("result", {}).get("withdrawals"):
        flash("There's nothing to apply. Enter an amount first.", "error")
        return _redirect_to_plan_withdraw()

    withdrawals = preview["result"]["withdrawals"]
    amount = preview.get("amount")

    # Decrement current_amount on each goal touched by the strategy.
    # Match by goal_id (preferred) or fall back to name match scoped to this user.
    goals_by_id = {g.id: g for g in Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).all()}
    goals_by_name = {g.name: g for g in goals_by_id.values()}

    for w in withdrawals:
        goal = goals_by_id.get(w.get("goal_id")) or goals_by_name.get(w.get("pot_name"))
        if goal is None:
            continue
        current = float(goal.current_amount or 0)
        new_current = max(round(current - float(w.get("amount", 0)), 2), 0)
        goal.current_amount = new_current

    db.session.commit()
    session.pop("withdrawal_preview", None)
    track_event(current_user.id, "withdrawal_confirmed", {"amount": amount})
    flash("Your plan has been updated.", "success")
    return redirect(url_for("pages.plan"))


@page_bp.route("/plan/withdraw/dismiss", methods=["POST"])
@login_required
@requires_subscription
def plan_withdraw_dismiss():
    preview = session.get("withdrawal_preview")
    if preview:
        preview["decided"] = True
        session["withdrawal_preview"] = preview
        track_event(current_user.id, "withdrawal_dismissed", {"amount": preview.get("amount")})
    flash("No changes made. The recommendation is here when you're ready.", "info")
    return _redirect_to_plan_withdraw()

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
            flash("Your plan stays on track.", "success")
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
                flash("Got it. Let us know if you need to budget for it.", "success")
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

        elif checkin_type == "other":
            note = details or "something changed"
            flash(f"Noted: {note}. Your companion can help you work out what to do next.", "success")
            return redirect(url_for("pages.companion"))

        elif checkin_type == "ask_later":
            flash("No problem. We'll check in again soon.", "success")
            return redirect(url_for("pages.overview"))

        return redirect(url_for("pages.overview"))

    return render_template("life_checkin.html")

# ─── UPGRADE PAGE — shown when in-app users hit paywalled features ───────────

@page_bp.route("/upgrade")
@login_required
def upgrade():
    from_page = request.args.get("from", "overview")
    return render_template("upgrade.html", from_page=from_page)

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
        trial_end_date=trial_end,
        show_sidebar=False,
        show_header=False
    )


# ─── PWA SERVICE WORKER ──────────────────────────────────

@page_bp.route("/sw.js")
def service_worker():
    response = send_from_directory(current_app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


# ─── SETTINGS ────────────────────────────────────────────

@page_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")


@page_bp.route("/settings/delete-account", methods=["GET", "POST"])
@login_required
def delete_account():
    if request.method == "POST":
        confirmation = (request.form.get("confirmation") or "").strip()
        reason = (request.form.get("reason") or "").strip() or None

        if confirmation != "DELETE":
            flash("Please type DELETE to confirm.", "error")
            return redirect(url_for("pages.delete_account"))

        user_id = current_user.id
        success = delete_user_account(user_id, reason=reason)

        if not success:
            flash("Something went wrong. Please contact support.", "error")
            return redirect(url_for("pages.settings"))

        logout_user()
        return redirect(url_for("pages.account_deleted"))

    return render_template("delete_account.html")


@page_bp.route("/account-deleted")
def account_deleted():
    return render_template("account_deleted.html")


@page_bp.route("/update-theme", methods=["POST"])
@login_required
def update_theme():
    theme = request.form.get("theme", "racing-green")
    valid = ["obsidian-vault", "soft-modern",
             "racing-green", "midnight-navy", "oxford-saddle", "amethyst",
             "rosso", "cobalt", "obsidian", "ivory", "pearl", "sage", "paper"]
    if theme not in valid:
        theme = "obsidian-vault"

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
            monthly_income = validate_amount(
                request.form.get("monthly_income", 0),
                "Monthly income", min_val=0.01, max_val=1_000_000
            )
            rent_amount = validate_amount(
                request.form.get("rent_amount", 0),
                "Rent", min_val=0, max_val=100_000
            )
            bills_amount = validate_amount(
                request.form.get("bills_amount", 0),
                "Bills", min_val=0, max_val=100_000
            )
            groceries_estimate = validate_amount(
                request.form.get("groceries_estimate", 0) or 0,
                "Groceries", min_val=0, max_val=100_000
            )
            transport_estimate = validate_amount(
                request.form.get("transport_estimate", 0) or 0,
                "Transport", min_val=0, max_val=100_000
            )
            subscriptions_total = validate_amount(
                request.form.get("subscriptions_total", 0) or 0,
                "Subscriptions", min_val=0, max_val=100_000
            )
            other_commitments = validate_amount(
                request.form.get("other_commitments", 0) or 0,
                "Other commitments", min_val=0, max_val=100_000
            )
            income_day = validate_int(
                request.form.get("income_day"),
                "Pay day", min_val=1, max_val=31, allow_none=True
            )
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("pages.factfind"))

        employment_type = request.form.get("employment_type", "full_time")
        if employment_type not in ("full_time", "part_time", "self_employed", "contract"):
            employment_type = "full_time"

        current_user.monthly_income = monthly_income
        current_user.rent_amount = rent_amount
        current_user.bills_amount = bills_amount
        current_user.groceries_estimate = groceries_estimate
        current_user.transport_estimate = transport_estimate
        current_user.subscriptions_total = subscriptions_total
        current_user.other_commitments = other_commitments
        current_user.income_day = income_day
        current_user.employment_type = employment_type
        was_already_completed = current_user.factfind_completed
        current_user.factfind_completed = True

        db.session.commit()
        if not was_already_completed:
            track_event(current_user.id, "onboarding_stage1_completed", {
                "employment_type": employment_type,
                "monthly_income": float(monthly_income),
            })
        flash("Financial profile updated" if was_already_completed else "Financial profile saved", "success")
        if was_already_completed:
            return redirect(url_for("pages.settings"))
        return redirect(url_for("pages.surplus_reveal"))

    if not current_user.factfind_completed:
        track_event(current_user.id, "factfind_started")
    return render_template("factfind.html",
        profile=current_user.profile_dict(),
        show_sidebar=current_user.plan_wizard_complete,
        show_header=current_user.plan_wizard_complete
    )


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
        try:
            name = validate_name(request.form.get("name", ""), max_length=255)
            target_amount = validate_amount(
                request.form.get("target_amount", "") or None,
                "Target amount", min_val=0.01, max_val=10_000_000, allow_none=True
            )
            current_amount = validate_amount(
                request.form.get("current_amount", "") or 0,
                "Current amount", min_val=0, max_val=10_000_000
            )
            monthly_allocation = validate_amount(
                request.form.get("monthly_allocation", "") or None,
                "Monthly allocation", min_val=0, max_val=1_000_000, allow_none=True
            )
            priority_rank = validate_int(
                request.form.get("priority_rank", 1),
                "Priority", min_val=1, max_val=100, allow_none=False
            )
        except ValueError as e:
            flash(str(e), "error")
            return redirect(url_for("pages.add_goal"))

        if target_amount is not None and current_amount > target_amount:
            flash("Current amount cannot exceed target", "error")
            return redirect(url_for("pages.add_goal"))

        goal_type = sanitize_string(request.form.get("type", "savings_target"), max_length=30) or "savings_target"

        deadline = None
        val = (request.form.get("deadline") or "").strip()
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
        track_event(current_user.id, "goals_added", {
            "count": 1,
            "types": [goal_type],
            "has_target": target_amount is not None,
            "has_deadline": deadline is not None,
            "source": "add_goal",
        })
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

    try:
        CheckInEntry.query.filter_by(goal_id=goal.id).delete(synchronize_session=False)
        db.session.delete(goal)
        db.session.commit()
        flash("Goal deleted", "success")
    except IntegrityError:
        db.session.rollback()
        flash("Couldn't delete this goal — it's still referenced by other records.", "error")
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

    from_page = request.args.get("from")

    return render_template("goal_detail.html",
        goal=goal, projection=projection, multi_horizon=multi_horizon,
        max_contribution=max_contribution, slider_percent=slider_percent,
        from_page=from_page
    )


# ─── SCENARIO ────────────────────────────────────────────

@page_bp.route("/scenario", methods=["GET", "POST"])
@login_required
@requires_subscription
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
    if current_user.factfind_completed:
        return redirect(url_for("pages.overview"))
    track_event(current_user.id, "welcome_screen_viewed")
    return render_template("welcome.html", show_sidebar=False, show_header=False)

@page_bp.route("/unsubscribe")
def unsubscribe():
    # TODO: when email preferences are built, mark current_user as opted out here.
    # For now, a polite confirmation page so the link doesn't 404.
    return render_template("unsubscribe.html")


# ─── DESIGN PREVIEW — Direction C: "Soft Modern" ──────────
# Standalone shell that doesn't extend base.html. Lets us prototype a
# native-app-style UI without disturbing the production design system.

@page_bp.route("/preview/modern")
@login_required
def preview_modern():
    today = date.today()
    hour = datetime.now().hour
    greeting = "morning" if hour < 12 else "afternoon" if hour < 18 else "evening"

    goals = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).limit(4).all()

    directed_amount = None
    if current_user.created_at and current_user.factfind_completed:
        signup_date = current_user.created_at.date() if hasattr(current_user.created_at, "date") else current_user.created_at
        delta = relativedelta(today, signup_date)
        months_active = delta.years * 12 + delta.months
        surplus = current_user.monthly_surplus or 0
        if months_active >= 1 and surplus > 0:
            directed_amount = round(float(surplus) * months_active, 2)

    expenses_this_month = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(user_id=current_user.id, type="expense").filter(
        extract("month", Transaction.date) == today.month,
        extract("year", Transaction.date) == today.year
    ).scalar() or 0

    return render_template(
        "preview_modern.html",
        greeting=greeting,
        first_name=(current_user.name or "there").split()[0],
        date_label=f"{today.strftime('%A')}, {today.day} {today.strftime('%B')}",
        goals=goals,
        directed_amount=directed_amount,
        expenses_this_month=float(expenses_this_month),
    )
