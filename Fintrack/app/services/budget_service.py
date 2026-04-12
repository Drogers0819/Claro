from datetime import date
from collections import defaultdict
import calendar


def calculate_budget_status(budgets, transactions, current_date=None):
    """
    Calculates real-time status for all active budgets.
    
    Compares actual spending per category against budget limits
    for the current month.
    """
    if current_date is None:
        current_date = date.today()

    current_month = current_date.month
    current_year = current_date.year
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    day_of_month = current_date.day
    days_remaining = days_in_month - day_of_month
    month_progress = day_of_month / days_in_month

    # Sum spending per category for current month
    spending_by_category = defaultdict(float)
    txn_count_by_category = defaultdict(int)

    for t in transactions:
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))

        if txn_date.month == current_month and txn_date.year == current_year:
            if t.get("type") == "expense":
                cat = t.get("category", "Other")
                spending_by_category[cat] += float(t["amount"])
                txn_count_by_category[cat] += 1

    statuses = []
    total_budgeted = 0
    total_spent = 0
    alerts = []

    for b in budgets:
        if not b.get("is_active", True):
            continue

        category_name = b["category_name"]
        limit = float(b["monthly_limit"])
        spent = round(spending_by_category.get(category_name, 0), 2)
        remaining = round(limit - spent, 2)
        percent_used = round((spent / limit * 100), 1) if limit > 0 else 0
        txn_count = txn_count_by_category.get(category_name, 0)

        total_budgeted += limit
        total_spent += spent

        # Calculate daily budget remaining
        daily_remaining = round(remaining / days_remaining, 2) if days_remaining > 0 else 0

        # Determine status
        if percent_used >= 100:
            status = "exceeded"
            severity = "high"
        elif percent_used >= 85:
            status = "warning"
            severity = "medium"
        elif percent_used > month_progress * 100 + 10:
            status = "ahead_of_pace"
            severity = "low"
        else:
            status = "on_track"
            severity = "none"

        # Projected end-of-month
        if day_of_month > 0 and spent > 0:
            daily_rate = spent / day_of_month
            projected_total = round(daily_rate * days_in_month, 2)
            projected_over = round(projected_total - limit, 2)
            will_exceed = projected_total > limit
        else:
            projected_total = 0
            projected_over = 0
            will_exceed = False

        budget_status = {
            "budget_id": b["id"],
            "category_name": category_name,
            "category_icon": b.get("category_icon", ""),
            "category_colour": b.get("category_colour", "#888"),
            "monthly_limit": limit,
            "spent": spent,
            "remaining": remaining,
            "percent_used": percent_used,
            "transaction_count": txn_count,
            "daily_remaining": daily_remaining,
            "status": status,
            "severity": severity,
            "projected_total": projected_total,
            "projected_over": projected_over,
            "will_exceed": will_exceed,
            "insight": _generate_budget_insight(
                category_name, spent, limit, remaining,
                percent_used, daily_remaining, days_remaining,
                status, projected_total, will_exceed
            )
        }

        statuses.append(budget_status)

        # Generate alerts for problematic budgets
        if status == "exceeded":
            alerts.append({
                "category": category_name,
                "severity": "high",
                "message": f"Your {category_name} budget is exceeded by £{abs(remaining):.2f}.",
                "type": "budget_exceeded"
            })
        elif status == "warning":
            alerts.append({
                "category": category_name,
                "severity": "medium",
                "message": f"Your {category_name} budget is {percent_used:.0f}% used with {days_remaining} days remaining.",
                "type": "budget_warning"
            })
        elif will_exceed and status != "exceeded":
            alerts.append({
                "category": category_name,
                "severity": "medium",
                "message": f"At current pace, your {category_name} spending will exceed budget by £{projected_over:.2f}.",
                "type": "budget_projected_exceed"
            })

    # Sort by percent used descending — most pressed budgets first
    statuses.sort(key=lambda s: s["percent_used"], reverse=True)

    total_remaining = round(total_budgeted - total_spent, 2)

    return {
        "budgets": statuses,
        "summary": {
            "total_budgeted": round(total_budgeted, 2),
            "total_spent": round(total_spent, 2),
            "total_remaining": total_remaining,
            "overall_percent": round((total_spent / total_budgeted * 100), 1) if total_budgeted > 0 else 0,
            "budget_count": len(statuses),
            "exceeded_count": sum(1 for s in statuses if s["status"] == "exceeded"),
            "warning_count": sum(1 for s in statuses if s["status"] == "warning"),
            "on_track_count": sum(1 for s in statuses if s["status"] == "on_track")
        },
        "alerts": alerts,
        "month_context": {
            "month": current_month,
            "year": current_year,
            "month_name": date(current_year, current_month, 1).strftime("%B"),
            "day_of_month": day_of_month,
            "days_remaining": days_remaining,
            "days_in_month": days_in_month,
            "progress_percent": round(month_progress * 100, 1)
        }
    }


def _generate_budget_insight(category, spent, limit, remaining, percent_used, daily_remaining, days_remaining, status, projected_total, will_exceed):
    """
    Generates human-readable insight for each budget.
    """
    if status == "exceeded":
        return f"You've gone £{abs(remaining):.2f} over your {category} budget this month."
    elif status == "warning":
        return f"You have £{remaining:.2f} left for {category} with {days_remaining} days to go. That's £{daily_remaining:.2f}/day."
    elif will_exceed:
        return f"At your current pace, you'll spend £{projected_total:.2f} on {category}, £{projected_total - limit:.2f} over your limit."
    elif status == "ahead_of_pace":
        return f"Your {category} spending is slightly ahead of pace but still within budget. £{remaining:.2f} remaining."
    else:
        return f"Your {category} budget is on track. £{remaining:.2f} left (£{daily_remaining:.2f}/day for {days_remaining} days)."


def suggest_budgets(transactions, current_date=None):
    """
    Analyses historical spending and suggests budget amounts
    based on average monthly spending per category.
    """
    if current_date is None:
        current_date = date.today()

    # Group historical expenses by category and month
    monthly_by_cat = defaultdict(lambda: defaultdict(float))

    for t in transactions:
        if t.get("type") != "expense":
            continue

        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))

        # Exclude current month — only use completed months
        if txn_date.month == current_date.month and txn_date.year == current_date.year:
            continue

        key = f"{txn_date.year}-{txn_date.month:02d}"
        cat = t.get("category", "Other")
        monthly_by_cat[cat][key] += float(t["amount"])

    suggestions = []

    for category, months in monthly_by_cat.items():
        if not months:
            continue

        totals = list(months.values())
        avg = round(sum(totals) / len(totals), 2)

        if avg < 5:
            continue

        # Suggest slightly above average to give breathing room
        suggested = round(avg * 1.1, -1)  # Round to nearest 10
        if suggested < 10:
            suggested = 10

        suggestions.append({
            "category": category,
            "average_monthly": avg,
            "suggested_limit": suggested,
            "months_of_data": len(totals),
            "highest_month": round(max(totals), 2),
            "lowest_month": round(min(totals), 2)
        })

    suggestions.sort(key=lambda s: s["average_monthly"], reverse=True)

    return {
        "suggestions": suggestions,
        "total_suggested": round(sum(s["suggested_limit"] for s in suggestions), 2)
    }