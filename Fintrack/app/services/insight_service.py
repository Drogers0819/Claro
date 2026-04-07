from datetime import date
import calendar


def generate_page_insights(page, user_data):
    """
    Generates a single contextual whisper for each page.
    
    9 core scenarios only:
    1. Money left + daily rate
    2. Budget approaching limit
    3. Budget exceeded
    4. Goal progress
    5. Goal funding conflict
    6. Unallocated surplus
    7. Spending pace vs average
    8. Recurring payments total
    9. Month-end narrative summary
    
    No judgement. No lifestyle advice. Just the numbers
    the user needs, written like a calm friend.
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
    Dashboard: money left, budget problems, goal progress.
    Picks the most important thing and leads with it.
    """
    money_left = data.get("money_left")
    days_remaining = data.get("days_remaining", 0)
    budget_statuses = data.get("budget_statuses", [])
    primary_goal = data.get("primary_goal", {})

    # Money left is always the lead
    if money_left is not None and days_remaining > 0:
        daily = round(money_left / days_remaining, 2)

        if money_left > 0:
            whisper = f"You've got £{money_left:,.2f} left for the next {days_remaining} days. That's about £{daily:.2f} a day."
        else:
            whisper = f"You've spent £{abs(money_left):,.2f} more than planned this month with {days_remaining} days still to go."

        # Add budget problem if there is one
        exceeded = [b for b in budget_statuses if b.get("status") == "exceeded"]
        warning = [b for b in budget_statuses if b.get("status") == "warning"]

        if exceeded:
            name = exceeded[0].get("category_name", "One category")
            over = abs(exceeded[0].get("remaining", 0))
            whisper += f" Your {name} budget is £{over:.2f} over."
        elif warning:
            name = warning[0].get("category_name", "One category")
            left = warning[0].get("remaining", 0)
            whisper += f" Your {name} budget has £{left:.2f} left."

        # Add goal progress if everything else is fine
        if not exceeded and not warning and primary_goal:
            progress = primary_goal.get("progress_percent")
            name = primary_goal.get("name", "your goal")
            if progress and progress > 0:
                whisper += f" {name} is {progress}% done."

        return {"whisper": whisper, "page": "overview"}

    # No financial profile yet
    name = data.get("user_name", "")
    return {
        "whisper": f"Welcome{', ' + name if name else ''}. Complete your financial profile and upload a bank statement to get started.",
        "page": "overview"
    }


def _my_money_insight(data):
    """
    Transactions page: spending pace vs your own average.
    """
    predictions = data.get("predictions", {})
    spending = predictions.get("spending_so_far", {})
    comparison = predictions.get("comparison", {})

    total_spent = spending.get("total", 0)
    txn_count = spending.get("transaction_count", 0)

    if total_spent <= 0:
        return {
            "whisper": "Upload a bank statement and we'll show you exactly where your money is going. It takes about 30 seconds.",
            "page": "my_money"
        }

    whisper = f"You've spent £{total_spent:,.2f} so far this month across {txn_count} transactions."

    comp_status = comparison.get("status", "")
    diff = comparison.get("difference", 0)

    if comp_status == "spending_high" and diff > 0:
        whisper += f" That's £{diff:.2f} more than you'd normally spend by this point."
    elif comp_status == "spending_low" and diff < 0:
        whisper += f" That's £{abs(diff):.2f} less than usual — you're under your average pace."

    return {"whisper": whisper, "page": "my_money"}


def _my_goals_insight(data):
    """
    Goals page: progress, conflicts, unallocated money.
    """
    goals = data.get("goals", [])
    waterfall = data.get("waterfall", {})
    projections = data.get("projections", [])

    active = [g for g in goals if g.get("status") == "active"]

    if not active:
        return {
            "whisper": "You haven't set any goals yet. What are you saving for — a holiday, a deposit, an emergency fund? Pick one and we'll show you when you'll get there.",
            "page": "my_goals"
        }

    parts = []

    # Goal count and primary progress
    primary = active[0]
    progress = primary.get("progress_percent")
    name = primary.get("name", "your goal")

    if progress and progress > 0:
        parts.append(f"{name} is {progress}% done.")
    else:
        parts.append(f"You have {len(active)} goal{'s' if len(active) != 1 else ''} in progress.")

    # Nearest arrival date
    reachable = [p for p in projections if p.get("reachable") is True]
    if reachable:
        soonest = min(reachable, key=lambda p: p.get("months_to_target", 999))
        arrival = soonest.get("completion_date_human", "")
        goal_name = soonest.get("goal_name", "Your nearest goal")
        if arrival:
            parts.append(f"{goal_name} arrives {arrival}.")

    # Conflicts
    conflicts = waterfall.get("conflicts", [])
    if conflicts:
        parts.append(f"Your goals add up to more than you have available — {len(conflicts)} goal{'s' if len(conflicts) != 1 else ''} won't get the full amount.")

    # Unallocated surplus
    unallocated = waterfall.get("unallocated", 0)
    if unallocated > 10 and not conflicts:
        parts.append(f"You have £{unallocated:.2f}/month that isn't assigned to any goal.")

    return {"whisper": " ".join(parts[:3]), "page": "my_goals"}


def _my_budgets_insight(data):
    """
    Budgets page: budget status, recurring total.
    """
    budget_statuses = data.get("budget_statuses", [])
    recurring = data.get("recurring", {})
    days_remaining = data.get("days_remaining", 0)

    # No budgets set
    if not budget_statuses:
        recurring_total = recurring.get("total_monthly_cost", 0)
        recurring_count = recurring.get("count", 0)

        if recurring_count > 0:
            return {
                "whisper": f"You have {recurring_count} regular payments totalling £{recurring_total:.2f}/month. Set spending budgets and we'll track them for you.",
                "page": "my_budgets"
            }

        return {
            "whisper": "Set a spending limit on a category and we'll let you know how you're tracking against it.",
            "page": "my_budgets"
        }

    exceeded = [b for b in budget_statuses if b.get("status") == "exceeded"]
    warning = [b for b in budget_statuses if b.get("status") == "warning"]
    on_track = [b for b in budget_statuses if b.get("status") in ("on_track", "ahead_of_pace")]

    if exceeded:
        b = exceeded[0]
        name = b.get("category_name", "One budget")
        over = abs(b.get("remaining", 0))
        whisper = f"Your {name} budget is £{over:.2f} over this month."

        if on_track:
            whisper += f" Your other {len(on_track)} budget{'s are' if len(on_track) != 1 else ' is'} within limits."

    elif warning:
        b = warning[0]
        name = b.get("category_name", "One budget")
        left = b.get("remaining", 0)
        daily = b.get("daily_remaining", 0)
        whisper = f"Your {name} budget has £{left:.2f} left"
        if daily > 0 and days_remaining > 0:
            whisper += f" — about £{daily:.2f} a day for {days_remaining} days."
        else:
            whisper += "."

    else:
        count = len(on_track)
        whisper = f"All {count} budget{'s are' if count != 1 else ' is'} on track this month."

        # Add tightest budget detail
        if on_track:
            tightest = max(on_track, key=lambda b: b.get("percent_used", 0))
            name = tightest.get("category_name", "")
            left = tightest.get("remaining", 0)
            daily = tightest.get("daily_remaining", 0)
            if daily > 0 and days_remaining > 0:
                whisper += f" Your tightest is {name} — £{left:.2f} left, about £{daily:.2f} a day."

    return {"whisper": whisper, "page": "my_budgets"}


def _settings_insight(data):
    """Settings: light, factual."""
    txn_count = data.get("total_transactions", 0)
    goal_count = data.get("active_goals", 0)

    if txn_count > 0 and goal_count > 0:
        whisper = f"You've recorded {txn_count} transactions and you're tracking {goal_count} goal{'s' if goal_count != 1 else ''}."
    elif txn_count > 0:
        whisper = f"You've recorded {txn_count} transactions so far."
    else:
        whisper = "Personalise your experience with a theme that suits you."

    return {"whisper": whisper, "page": "settings"}


def _fallback_insight(data):
    return {
        "whisper": "Keep tracking your finances to unlock personalised insights.",
        "page": "unknown"
    }


def generate_daily_digest(user_data):
    """
    Structured daily summary. Only includes sections
    where there's something genuinely worth saying.
    """
    sections = []

    # Money left
    money_left = user_data.get("money_left")
    days_remaining = user_data.get("days_remaining", 0)

    if money_left is not None and days_remaining > 0:
        daily = round(money_left / days_remaining, 2)
        sections.append({
            "title": "Your money today",
            "content": f"£{money_left:,.2f} left. That's £{daily:.2f} a day for {days_remaining} days."
        })

    # Budget problems only
    budget_statuses = user_data.get("budget_statuses", [])
    problems = [b for b in budget_statuses if b.get("status") in ("exceeded", "warning")]

    if problems:
        msgs = []
        for b in problems[:2]:
            name = b.get("category_name", "")
            if b["status"] == "exceeded":
                msgs.append(f"{name} is £{abs(b.get('remaining', 0)):.2f} over budget.")
            else:
                msgs.append(f"{name} has £{b.get('remaining', 0):.2f} left.")
        sections.append({
            "title": "Budget update",
            "content": " ".join(msgs)
        })

    # Goal progress
    goals = user_data.get("goals", [])
    active = [g for g in goals if g.get("status") == "active"]
    if active:
        primary = active[0]
        progress = primary.get("progress_percent", 0)
        sections.append({
            "title": "Goal progress",
            "content": f"{primary.get('name', 'Your goal')}: {progress}% done."
        })

    return {
        "sections": sections,
        "section_count": len(sections),
        "has_alerts": any(b.get("status") == "exceeded" for b in budget_statuses),
        "generated_at": date.today().isoformat()
    }


def generate_month_end_summary(user_data):
    """
    Month-end data for the narrative report.
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

    if hist_avg > 0:
        if diff > 0:
            spending_verdict = f"You spent £{total_spent:,.2f} this month — £{diff:.2f} more than your average of £{hist_avg:,.2f}."
        elif diff < 0:
            spending_verdict = f"You spent £{total_spent:,.2f} this month — £{abs(diff):.2f} less than your average. A lighter month."
        else:
            spending_verdict = f"You spent £{total_spent:,.2f} this month — right on your average."
    else:
        spending_verdict = f"You spent £{total_spent:,.2f} this month."

    active_goals = [g for g in goals if g.get("status") == "active"]
    goal_summaries = []
    for g in active_goals:
        progress = g.get("progress_percent")
        if progress is not None:
            goal_summaries.append(f"{g['name']}: {progress}% done")

    exceeded = [b for b in budgets if b.get("status") == "exceeded"]
    on_track = [b for b in budgets if b.get("status") == "on_track"]

    if exceeded:
        budget_verdict = f"{len(exceeded)} budget{'s' if len(exceeded) != 1 else ''} went over this month."
    elif on_track:
        budget_verdict = f"All {len(on_track)} budget{'s' if len(on_track) != 1 else ''} stayed on track."
    else:
        budget_verdict = None

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