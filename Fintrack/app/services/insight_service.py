from datetime import date, timedelta
from collections import defaultdict
import calendar


def generate_page_insights(page, user_data):
    """
    Generates contextual whisper text for each page based on
    all available data. Returns 1-3 sentences of plain-language
    insight relevant to what the user is looking at.
    
    Every insight answers the implicit question:
    "What do I need to know right now?"
    """
    generators = {
        "overview": _overview_insight,
        "my_money": _my_money_insight,
        "my_goals": _my_goals_insight,
        "my_budgets": _my_budgets_insight,
        "settings": _settings_insight
    }

    generator = generators.get(page, _fallback_insight)
    return generator(user_data)


def _overview_insight(data):
    """
    Dashboard insight — the most important whisper.
    Prioritises: money left, budget status, goal progress, anomalies.
    """
    parts = []
    priority_insight = None

    money_left = data.get("money_left")
    days_remaining = data.get("days_remaining", 0)
    predictions = data.get("predictions", {})
    budget_status = data.get("budget_status", {})
    primary_goal = data.get("primary_goal", {})
    anomalies = data.get("anomalies", {})

    # Money left is always the lead
    if money_left is not None:
        if days_remaining > 0:
            daily = round(money_left / days_remaining, 2)
            if money_left > 0:
                parts.append(f"You have £{money_left:,.2f} left to spend this month — that's £{daily:.2f} per day for {days_remaining} days.")
            else:
                parts.append(f"You've gone £{abs(money_left):,.2f} over your spending allowance this month with {days_remaining} days still to go.")
                priority_insight = "overspending"

    # Budget status — only mention if there's a problem
    status = budget_status.get("status", "")
    if status == "overspending":
        parts.append(budget_status.get("message", "Your predicted spending exceeds your income this month."))
        priority_insight = "overspending"
    elif status == "tight":
        parts.append(budget_status.get("message", "Your spending is running close to your limits."))

    # Goal progress — if no problems, lead with something positive
    if not priority_insight and primary_goal:
        progress = primary_goal.get("progress_percent")
        name = primary_goal.get("name", "your goal")
        if progress is not None and progress > 0:
            parts.append(f"Your {name} is {progress}% funded. Keep going.")

    # Anomalies — flag the most important one
    anomaly_list = anomalies.get("anomalies", [])
    high_anomalies = [a for a in anomaly_list if a.get("severity") == "high"]
    if high_anomalies:
        parts.append(high_anomalies[0].get("message", ""))

    # Quiet period — positive reinforcement
    quiet = [a for a in anomaly_list if a.get("type") == "quiet_period"]
    if quiet and not priority_insight:
        parts.append(quiet[0].get("message", ""))

    if not parts:
        name = data.get("user_name", "")
        parts.append(f"Welcome back{', ' + name if name else ''}. Upload a bank statement or add transactions to unlock your insights.")

    return {
        "whisper": " ".join(parts[:3]),
        "priority": priority_insight or "normal",
        "page": "overview"
    }


def _my_money_insight(data):
    """
    Transactions page insight — spending pace and category highlights.
    """
    parts = []

    predictions = data.get("predictions", {})
    spending = predictions.get("spending_so_far", {})
    comparison = predictions.get("comparison", {})
    category_predictions = predictions.get("predictions", {}).get("by_category", [])
    trends = data.get("trends", [])

    total_spent = spending.get("total", 0)
    txn_count = spending.get("transaction_count", 0)

    if total_spent > 0:
        parts.append(f"You've spent £{total_spent:,.2f} across {txn_count} transactions this month.")

    # Comparison to average
    comp_status = comparison.get("status", "")
    if comp_status == "spending_high":
        diff = comparison.get("difference", 0)
        parts.append(f"That's £{diff:.2f} more than usual at this point in the month.")
    elif comp_status == "spending_low":
        diff = abs(comparison.get("difference", 0))
        parts.append(f"That's £{diff:.2f} less than usual — you're under your average pace.")

    # Biggest category change
    if category_predictions:
        above = [c for c in category_predictions if c.get("status") == "above_average"]
        if above:
            worst = max(above, key=lambda c: c.get("pace_vs_average", 0))
            parts.append(f"Your {worst['category']} spending is {abs(worst['pace_vs_average']):.0f}% above average this month.")

    # Trend from last month
    if trends:
        biggest = trends[0] if trends else None
        if biggest and biggest.get("direction") == "up":
            parts.append(f"{biggest['category']} is up {biggest['change_percent']:.0f}% compared to last month.")
        elif biggest and biggest.get("direction") == "down":
            parts.append(f"Good news: {biggest['category']} is down {abs(biggest['change_percent']):.0f}% compared to last month.")

    if not parts:
        parts.append("Upload a bank statement to see where your money is going this month.")

    return {
        "whisper": " ".join(parts[:3]),
        "priority": "normal",
        "page": "my_money"
    }


def _my_goals_insight(data):
    """
    Goals page insight — progress, timelines, and waterfall status.
    """
    parts = []

    goals = data.get("goals", [])
    waterfall = data.get("waterfall", {})
    projections = data.get("projections", [])

    active_goals = [g for g in goals if g.get("status") == "active"]

    if not active_goals:
        return {
            "whisper": "You haven't set any financial goals yet. What are you working toward? A house deposit, a holiday, an emergency fund?",
            "priority": "normal",
            "page": "my_goals"
        }

    # Goal count and primary goal
    count = len(active_goals)
    parts.append(f"You have {count} active goal{'s' if count != 1 else ''}.")

    # Primary goal progress
    primary = active_goals[0] if active_goals else None
    if primary and primary.get("progress_percent") is not None:
        parts.append(f"Your {primary['name']} is {primary['progress_percent']}% complete.")

    # Projections — nearest completion
    reachable = [p for p in projections if p.get("reachable") is True]
    if reachable:
        soonest = min(reachable, key=lambda p: p.get("months_to_target", 999))
        parts.append(f"{soonest.get('goal_name', 'Your nearest goal')} arrives in {soonest.get('completion_date_human', 'the future')}.")

    # Waterfall conflicts
    conflicts = waterfall.get("conflicts", [])
    if conflicts:
        parts.append(f"Your budget has {len(conflicts)} conflict{'s' if len(conflicts) != 1 else ''} — some goals may not be fully funded at current allocations.")

    # Unallocated surplus
    unallocated = waterfall.get("unallocated", 0)
    if unallocated > 10:
        parts.append(f"You have £{unallocated:.2f}/month that isn't assigned to any goal.")

    return {
        "whisper": " ".join(parts[:3]),
        "priority": "attention" if conflicts else "normal",
        "page": "my_goals"
    }


def _my_budgets_insight(data):
    """
    Budgets page insight — budget status, alerts, recurring costs.
    """
    parts = []

    budget_statuses = data.get("budget_statuses", [])
    recurring = data.get("recurring", {})
    savings = data.get("savings_opportunities", {})
    days_remaining = data.get("days_remaining", 0)

    if not budget_statuses:
        monthly_cost = recurring.get("total_monthly_cost", 0)
        if monthly_cost > 0:
            parts.append(f"You have {recurring.get('count', 0)} recurring payments totalling £{monthly_cost:.2f}/month. Set budgets to track your spending limits.")
        else:
            parts.append("Set spending budgets to keep your categories in check. We'll track them in real time.")

        return {
            "whisper": " ".join(parts),
            "priority": "normal",
            "page": "my_budgets"
        }

    # Count statuses
    exceeded = sum(1 for b in budget_statuses if b.get("status") == "exceeded")
    warning = sum(1 for b in budget_statuses if b.get("status") == "warning")
    on_track = sum(1 for b in budget_statuses if b.get("status") == "on_track")

    if exceeded > 0:
        parts.append(f"{exceeded} budget{'s' if exceeded != 1 else ''} exceeded this month.")
        priority = "high"
    elif warning > 0:
        parts.append(f"{warning} budget{'s' if warning != 1 else ''} approaching {'their' if warning > 1 else 'its'} limit.")
        priority = "medium"
    else:
        parts.append(f"All {on_track} budget{'s are' if on_track != 1 else ' is'} on track.")
        priority = "normal"

    # Most pressed budget
    active_budgets = [b for b in budget_statuses if b.get("status") in ("exceeded", "warning")]
    if active_budgets:
        worst = max(active_budgets, key=lambda b: b.get("percent_used", 0))
        parts.append(f"{worst['category_name']} is {worst['percent_used']:.0f}% used — £{worst.get('remaining', 0):.2f} left.")

    # Savings opportunities
    opp_count = savings.get("count", 0)
    if opp_count > 0:
        total_saving = savings.get("total_potential_annual_saving", 0)
        parts.append(f"We spotted {opp_count} potential saving{'s' if opp_count != 1 else ''} worth up to £{total_saving:.2f}/year.")

    # Recurring total
    recurring_count = recurring.get("count", 0)
    recurring_cost = recurring.get("total_monthly_cost", 0)
    if recurring_count > 0 and not active_budgets:
        parts.append(f"You have {recurring_count} regular payments totalling £{recurring_cost:.2f}/month.")

    return {
        "whisper": " ".join(parts[:3]),
        "priority": priority,
        "page": "my_budgets"
    }


def _settings_insight(data):
    """
    Settings page — light, informational.
    """
    member_since = data.get("member_since", "")
    txn_count = data.get("total_transactions", 0)
    goals_count = data.get("active_goals", 0)

    parts = []

    if txn_count > 0:
        parts.append(f"You've recorded {txn_count} transactions so far.")

    if goals_count > 0:
        parts.append(f"You're tracking {goals_count} financial goal{'s' if goals_count != 1 else ''}.")

    if not parts:
        parts.append("Personalise your experience by choosing a theme that suits you.")

    return {
        "whisper": " ".join(parts),
        "priority": "normal",
        "page": "settings"
    }


def _fallback_insight(data):
    """
    Default insight when the page doesn't have a specific generator.
    """
    return {
        "whisper": "Keep tracking your finances to unlock personalised insights.",
        "priority": "normal",
        "page": "unknown"
    }


def generate_daily_digest(user_data):
    """
    Generates a comprehensive daily digest combining insights
    from all services. Used by the companion and notifications.
    """
    sections = []

    # Money status
    money_left = user_data.get("money_left")
    days_remaining = user_data.get("days_remaining", 0)
    if money_left is not None and days_remaining > 0:
        daily = round(money_left / days_remaining, 2)
        sections.append({
            "title": "Your money today",
            "content": f"£{money_left:,.2f} left to spend. That's £{daily:.2f}/day for {days_remaining} days.",
            "priority": "high" if money_left < 0 else "normal"
        })

    # Budget alerts
    budget_statuses = user_data.get("budget_statuses", [])
    alerts = [b for b in budget_statuses if b.get("status") in ("exceeded", "warning")]
    if alerts:
        alert_msgs = [f"{a['category_name']}: {a['insight']}" for a in alerts[:3]]
        sections.append({
            "title": "Budget alerts",
            "content": " ".join(alert_msgs),
            "priority": "high" if any(a["status"] == "exceeded" for a in alerts) else "medium"
        })

    # Goal updates
    goals = user_data.get("goals", [])
    active = [g for g in goals if g.get("status") == "active"]
    if active:
        primary = active[0]
        progress = primary.get("progress_percent", 0)
        sections.append({
            "title": "Goal progress",
            "content": f"{primary['name']}: {progress}% complete.",
            "priority": "normal"
        })

    # Anomalies
    anomalies = user_data.get("anomalies", {}).get("anomalies", [])
    important = [a for a in anomalies if a.get("severity") in ("high", "medium")]
    if important:
        sections.append({
            "title": "Unusual activity",
            "content": important[0].get("message", ""),
            "priority": important[0].get("severity", "medium")
        })

    # Positive reinforcement
    quiet = [a for a in anomalies if a.get("type") == "quiet_period"]
    if quiet:
        sections.append({
            "title": "Nice work",
            "content": quiet[0].get("message", ""),
            "priority": "positive"
        })

    return {
        "sections": sections,
        "section_count": len(sections),
        "has_alerts": any(s["priority"] in ("high", "medium") for s in sections),
        "generated_at": date.today().isoformat()
    }


def generate_month_end_summary(user_data):
    """
    Generates the end-of-month summary that feeds the monthly
    narrative report. Pulls together the complete picture.
    """
    predictions = user_data.get("predictions", {})
    spending = predictions.get("spending_so_far", {})
    comparison = predictions.get("comparison", {})
    goals = user_data.get("goals", [])
    budgets = user_data.get("budget_statuses", [])
    recurring = user_data.get("recurring", {})

    total_spent = spending.get("total", 0)
    hist_avg = comparison.get("historical_average", 0)
    diff = comparison.get("difference", 0)

    # Spending summary
    if hist_avg > 0:
        if diff > 0:
            spending_verdict = f"You spent £{total_spent:,.2f} this month — £{diff:.2f} more than your average of £{hist_avg:,.2f}."
        elif diff < 0:
            spending_verdict = f"You spent £{total_spent:,.2f} this month — £{abs(diff):.2f} less than your average of £{hist_avg:,.2f}. Well done."
        else:
            spending_verdict = f"You spent £{total_spent:,.2f} this month — right on your average."
    else:
        spending_verdict = f"You spent £{total_spent:,.2f} this month."

    # Goal progress
    active_goals = [g for g in goals if g.get("status") == "active"]
    goal_summaries = []
    for g in active_goals:
        progress = g.get("progress_percent")
        if progress is not None:
            goal_summaries.append(f"{g['name']}: {progress}% complete")

    # Budget performance
    exceeded = [b for b in budgets if b.get("status") == "exceeded"]
    on_track = [b for b in budgets if b.get("status") == "on_track"]

    if exceeded:
        budget_verdict = f"{len(exceeded)} budget{'s' if len(exceeded) != 1 else ''} exceeded this month."
    elif on_track:
        budget_verdict = f"All {len(on_track)} budget{'s' if len(on_track) != 1 else ''} stayed on track."
    else:
        budget_verdict = None

    # Recurring costs
    recurring_total = recurring.get("total_monthly_cost", 0)

    return {
        "spending_verdict": spending_verdict,
        "total_spent": round(total_spent, 2),
        "vs_average": round(diff, 2),
        "goal_summaries": goal_summaries,
        "budget_verdict": budget_verdict,
        "budgets_exceeded": len(exceeded),
        "budgets_on_track": len(on_track),
        "recurring_total": round(recurring_total, 2),
        "month_name": date.today().strftime("%B"),
        "year": date.today().year
    }