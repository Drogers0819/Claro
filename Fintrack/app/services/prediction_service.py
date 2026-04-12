from datetime import date, timedelta
from collections import defaultdict
import calendar
import statistics


def predict_monthly_spending(transactions, current_date=None):
    """
    Predicts end-of-month spending based on current pace
    and historical patterns.
    
    Uses two methods:
    1. Linear projection — extrapolates current month's pace
    2. Historical average — uses past months as baseline
    
    Returns a blended prediction with confidence.
    """
    if current_date is None:
        current_date = date.today()

    current_month = current_date.month
    current_year = current_date.year
    days_in_month = calendar.monthrange(current_year, current_month)[1]
    day_of_month = current_date.day
    days_remaining = days_in_month - day_of_month

    # Split transactions into current month and historical
    current_month_txns = []
    historical_months = defaultdict(list)

    for t in transactions:
        txn_date = t["date"] if isinstance(t["date"], date) else date.fromisoformat(str(t["date"]))
        amount = float(t["amount"])
        txn_type = t.get("type", "expense")

        if txn_type != "expense":
            continue

        if txn_date.month == current_month and txn_date.year == current_year:
            current_month_txns.append({
                "amount": amount,
                "date": txn_date,
                "category": t.get("category", "Other"),
                "description": t.get("description", "")
            })
        else:
            key = f"{txn_date.year}-{txn_date.month:02d}"
            historical_months[key].append({
                "amount": amount,
                "date": txn_date,
                "category": t.get("category", "Other")
            })

    # Current month totals
    current_spent = round(sum(t["amount"] for t in current_month_txns), 2)
    current_txn_count = len(current_month_txns)

    # Method 1: Linear projection
    linear_prediction = _linear_projection(
        current_spent, day_of_month, days_in_month
    )

    # Method 2: Historical average
    historical_prediction = _historical_prediction(historical_months)

    # Method 3: Category-level prediction
    category_predictions = _category_prediction(
        current_month_txns, historical_months,
        day_of_month, days_in_month
    )

    # Blend predictions
    blended = _blend_predictions(
        linear_prediction, historical_prediction,
        day_of_month, days_in_month, len(historical_months)
    )

    # Compare to historical average
    comparison = _compare_to_average(
        current_spent, day_of_month, days_in_month,
        historical_prediction
    )

    return {
        "current_month": {
            "month": current_month,
            "year": current_year,
            "month_name": date(current_year, current_month, 1).strftime("%B"),
            "days_elapsed": day_of_month,
            "days_remaining": days_remaining,
            "days_in_month": days_in_month,
            "progress_percent": round((day_of_month / days_in_month) * 100, 1)
        },
        "spending_so_far": {
            "total": current_spent,
            "transaction_count": current_txn_count,
            "daily_average": round(current_spent / day_of_month, 2) if day_of_month > 0 else 0
        },
        "predictions": {
            "linear": linear_prediction,
            "historical": historical_prediction,
            "blended": blended,
            "by_category": category_predictions
        },
        "comparison": comparison,
        "historical_months_available": len(historical_months),
        "insight": _generate_prediction_insight(
            current_spent, blended, comparison,
            day_of_month, days_in_month, category_predictions
        )
    }


def _linear_projection(current_spent, day_of_month, days_in_month):
    """
    Projects end-of-month total based on current daily spending rate.
    Simple but effective for mid-month estimates.
    """
    if day_of_month <= 0:
        return {"predicted_total": 0, "method": "linear", "confidence": 0}

    daily_rate = current_spent / day_of_month
    predicted_total = round(daily_rate * days_in_month, 2)

    # Confidence increases as more of the month has passed
    confidence = round(min(day_of_month / days_in_month, 0.95), 2)

    return {
        "predicted_total": predicted_total,
        "daily_rate": round(daily_rate, 2),
        "method": "linear",
        "confidence": confidence
    }


def _historical_prediction(historical_months):
    """
    Predicts based on average of past months' spending.
    """
    if not historical_months:
        return {
            "predicted_total": 0,
            "method": "historical",
            "confidence": 0,
            "months_used": 0
        }

    monthly_totals = []
    for key, txns in historical_months.items():
        total = sum(t["amount"] for t in txns)
        monthly_totals.append(total)

    avg = round(statistics.mean(monthly_totals), 2)
    std = round(statistics.stdev(monthly_totals), 2) if len(monthly_totals) > 1 else 0

    # Confidence based on consistency and sample size
    cv = std / avg if avg > 0 else 1
    consistency = max(0, 1 - cv)
    sample_confidence = min(1, len(monthly_totals) / 6)
    confidence = round(consistency * 0.6 + sample_confidence * 0.4, 2)

    return {
        "predicted_total": avg,
        "monthly_average": avg,
        "monthly_std": std,
        "method": "historical",
        "confidence": confidence,
        "months_used": len(monthly_totals),
        "range_low": round(avg - std, 2) if std > 0 else round(avg * 0.9, 2),
        "range_high": round(avg + std, 2) if std > 0 else round(avg * 1.1, 2)
    }


def _category_prediction(current_txns, historical_months, day_of_month, days_in_month):
    """
    Predicts end-of-month spending per category using both
    current pace and historical baseline.
    """
    # Current month by category
    current_by_cat = defaultdict(float)
    for t in current_txns:
        current_by_cat[t["category"]] += t["amount"]

    # Historical averages by category
    historical_by_cat = defaultdict(list)
    for key, txns in historical_months.items():
        month_cats = defaultdict(float)
        for t in txns:
            month_cats[t["category"]] += t["amount"]
        for cat, total in month_cats.items():
            historical_by_cat[cat].append(total)

    all_categories = set(list(current_by_cat.keys()) + list(historical_by_cat.keys()))

    predictions = []
    for cat in all_categories:
        current_amount = round(current_by_cat.get(cat, 0), 2)
        hist_values = historical_by_cat.get(cat, [])
        hist_avg = round(statistics.mean(hist_values), 2) if hist_values else 0

        # Linear projection for this category
        if day_of_month > 0 and current_amount > 0:
            linear_total = round((current_amount / day_of_month) * days_in_month, 2)
        else:
            linear_total = hist_avg

        # Blend: weight toward linear as month progresses
        month_progress = day_of_month / days_in_month if days_in_month > 0 else 0
        if hist_avg > 0 and linear_total > 0:
            blended = round(
                linear_total * month_progress + hist_avg * (1 - month_progress), 2
            )
        elif linear_total > 0:
            blended = linear_total
        else:
            blended = hist_avg

        # Determine status
        if hist_avg > 0:
            pace_vs_average = round(
                ((current_amount / (day_of_month / days_in_month)) - hist_avg) / hist_avg * 100, 1
            ) if day_of_month > 0 else 0
        else:
            pace_vs_average = 0

        if pace_vs_average > 15:
            status = "above_average"
        elif pace_vs_average < -15:
            status = "below_average"
        else:
            status = "on_track"

        predictions.append({
            "category": cat,
            "spent_so_far": current_amount,
            "predicted_total": blended,
            "historical_average": hist_avg,
            "pace_vs_average": pace_vs_average,
            "status": status
        })

    predictions.sort(key=lambda p: p["predicted_total"], reverse=True)

    return predictions


def _blend_predictions(linear, historical, day_of_month, days_in_month, historical_months_count):
    """
    Blends linear and historical predictions.
    Early in the month: weight historical more (current data is sparse).
    Late in the month: weight linear more (current data is reliable).
    """
    month_progress = day_of_month / days_in_month if days_in_month > 0 else 0

    linear_total = linear.get("predicted_total", 0)
    historical_total = historical.get("predicted_total", 0)

    if historical_months_count == 0:
        return {
            "predicted_total": round(linear_total, 2),
            "method": "linear_only",
            "confidence": linear.get("confidence", 0),
            "note": "No historical data available. Using current pace only."
        }

    if day_of_month <= 3:
        return {
            "predicted_total": round(historical_total, 2),
            "method": "historical_only",
            "confidence": historical.get("confidence", 0),
            "note": "Too early in the month for pace-based prediction. Using historical average."
        }

    # Progressive blending
    linear_weight = month_progress
    historical_weight = 1 - month_progress

    blended_total = round(
        linear_total * linear_weight + historical_total * historical_weight, 2
    )

    blended_confidence = round(
        linear.get("confidence", 0) * linear_weight +
        historical.get("confidence", 0) * historical_weight, 2
    )

    return {
        "predicted_total": blended_total,
        "linear_component": round(linear_total, 2),
        "historical_component": round(historical_total, 2),
        "linear_weight": round(linear_weight, 2),
        "historical_weight": round(historical_weight, 2),
        "method": "blended",
        "confidence": blended_confidence
    }


def _compare_to_average(current_spent, day_of_month, days_in_month, historical):
    """
    Compares current spending pace to historical average.
    """
    hist_avg = historical.get("monthly_average", 0)

    if hist_avg <= 0 or day_of_month <= 0:
        return {
            "status": "no_comparison",
            "message": "Not enough historical data for comparison."
        }

    expected_at_this_point = round(hist_avg * (day_of_month / days_in_month), 2)
    difference = round(current_spent - expected_at_this_point, 2)
    percent_difference = round((difference / expected_at_this_point) * 100, 1) if expected_at_this_point > 0 else 0

    if percent_difference > 15:
        status = "spending_high"
        message = f"You've spent £{current_spent:.2f} so far, which is £{difference:.2f} more than usual at this point in the month."
    elif percent_difference < -15:
        status = "spending_low"
        message = f"You've spent £{current_spent:.2f} so far, which is £{abs(difference):.2f} less than usual. You're under budget."
    else:
        status = "on_track"
        message = f"You've spent £{current_spent:.2f} so far, right in line with your usual pace."

    return {
        "status": status,
        "current_spent": current_spent,
        "expected_at_this_point": expected_at_this_point,
        "difference": difference,
        "percent_difference": percent_difference,
        "historical_average": hist_avg,
        "message": message
    }


def _generate_prediction_insight(current_spent, blended, comparison, day_of_month, days_in_month, category_predictions):
    """
    Generates human-readable insights for the AI companion
    and the dashboard.
    """
    parts = []

    predicted = blended.get("predicted_total", 0)
    if predicted > 0:
        parts.append(f"You're on track to spend £{predicted:,.2f} this month.")

    comp_status = comparison.get("status", "no_comparison")
    if comp_status == "spending_high":
        diff = comparison.get("difference", 0)
        parts.append(f"That's £{diff:.2f} above your usual pace at this point.")
    elif comp_status == "spending_low":
        diff = abs(comparison.get("difference", 0))
        parts.append(f"You're £{diff:.2f} under your usual pace. Nice work.")

    # Find the category furthest above average
    above_avg = [p for p in category_predictions if p["status"] == "above_average"]
    if above_avg:
        worst = max(above_avg, key=lambda p: p["pace_vs_average"])
        parts.append(
            f"Your {worst['category']} spending is {worst['pace_vs_average']:.0f}% above average this month."
        )

    # Find the category furthest below average
    below_avg = [p for p in category_predictions if p["status"] == "below_average"]
    if below_avg:
        best = min(below_avg, key=lambda p: p["pace_vs_average"])
        parts.append(
            f"Good news: {best['category']} spending is {abs(best['pace_vs_average']):.0f}% below average."
        )

    return {
        "summary": " ".join(parts) if parts else "Keep tracking your spending to unlock predictions.",
        "predicted_total": round(predicted, 2),
        "status": comp_status,
        "days_remaining": days_in_month - day_of_month
    }


def calculate_budget_status(predictions, user_profile, goals_data):
    """
    Connects predictions to the budget waterfall — shows whether
    predicted spending leaves enough surplus for goals.
    """
    predicted_expenses = predictions["predictions"]["blended"].get("predicted_total", 0)
    income = float(user_profile.get("monthly_income", 0))
    commitments = float(user_profile.get("fixed_commitments", 0))

    predicted_surplus = round(income - commitments - predicted_expenses, 2)
    planned_surplus = round(income - commitments, 2)

    total_goal_allocation = sum(
        float(g.get("monthly_allocation", 0))
        for g in goals_data
    )

    surplus_after_goals = round(predicted_surplus - total_goal_allocation, 2)

    if surplus_after_goals >= 0:
        status = "healthy"
        message = f"On track — you'll have £{surplus_after_goals:.0f} left after all your goals this month."
    elif predicted_surplus >= 0:
        status = "tight"
        shortfall = abs(surplus_after_goals)
        message = f"A little tight — you're about £{shortfall:.0f} short of fully funding your goals this month."
    else:
        status = "over budget"
        message = f"You're on track to overspend by £{abs(predicted_surplus):.0f} this month. Small cuts now will help."

    return {
        "status": status,
        "predicted_expenses": round(predicted_expenses, 2),
        "predicted_surplus": predicted_surplus,
        "planned_surplus": planned_surplus,
        "total_goal_allocation": round(total_goal_allocation, 2),
        "surplus_after_goals": surplus_after_goals,
        "message": message
    }