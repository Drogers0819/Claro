from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import math


GROWTH_RATES = {
    "conservative": 0.02,
    "moderate": 0.04,
    "optimistic": 0.06
}

INFLATION_RATE = 0.025


def project_goal_timeline(goal_data, monthly_contribution, growth_rate=None):
    if growth_rate is None:
        growth_rate = GROWTH_RATES["moderate"]

    target = float(goal_data.get("target_amount", 0))
    current = float(goal_data.get("current_amount", 0))
    contribution = float(monthly_contribution)

    if target <= 0:
        return {
            "error": "Target amount must be greater than zero",
            "reachable": False
        }

    if contribution <= 0 and current < target:
        return {
            "reachable": False,
            "current_amount": round(current, 2),
            "target_amount": round(target, 2),
            "remaining": round(target - current, 2),
            "message": "No monthly contribution set. This goal cannot be reached without regular saving."
        }

    monthly_rate = growth_rate / 12
    balance = current
    months = 0
    max_months = 600
    monthly_projections = []
    start_date = date.today()

    while balance < target and months < max_months:
        interest = balance * monthly_rate
        balance += contribution + interest
        months += 1

        projected_date = _add_months(start_date, months)

        monthly_projections.append({
            "month": months,
            "date": projected_date.isoformat(),
            "balance": round(balance, 2),
            "contributions_total": round(current + (contribution * months), 2),
            "interest_earned": round(balance - current - (contribution * months), 2)
        })

    if balance >= target:
        completion_date = _add_months(start_date, months)
        real_value = target / ((1 + INFLATION_RATE) ** (months / 12))

        return {
            "reachable": True,
            "months_to_target": months,
            "years_to_target": round(months / 12, 1),
            "completion_date": completion_date.isoformat(),
            "completion_date_human": completion_date.strftime("%B %Y"),
            "target_amount": round(target, 2),
            "current_amount": round(current, 2),
            "monthly_contribution": round(contribution, 2),
            "total_contributed": round(contribution * months, 2),
            "total_interest_earned": round(balance - current - (contribution * months), 2),
            "final_balance": round(balance, 2),
            "growth_rate_used": growth_rate,
            "inflation_adjusted_value": round(real_value, 2),
            "monthly_projections": monthly_projections,
            "milestones": _calculate_milestones(target, current, monthly_projections)
        }
    else:
        return {
            "reachable": False,
            "months_projected": months,
            "final_balance": round(balance, 2),
            "target_amount": round(target, 2),
            "shortfall": round(target - balance, 2),
            "message": f"At current rate, you'll reach £{round(balance, 2):,.2f} in {months} months, still £{round(target - balance, 2):,.2f} short of your target."
        }


def _calculate_milestones(target, current, projections):
    milestones = []
    milestone_percents = [25, 50, 75, 100]
    achieved = set()

    for p in projections:
        progress = (p["balance"] / target) * 100
        for pct in milestone_percents:
            if pct not in achieved and progress >= pct:
                achieved.add(pct)
                milestones.append({
                    "percent": pct,
                    "date": p["date"],
                    "month": p["month"],
                    "balance": p["balance"]
                })

    return milestones


def calculate_cost_of_habit(monthly_spend, years=10, growth_rate=None):
    if growth_rate is None:
        growth_rate = GROWTH_RATES["moderate"]

    spend = float(monthly_spend)
    if spend <= 0:
        return {"error": "Monthly spend must be greater than zero"}

    monthly_rate = growth_rate / 12
    total_months = years * 12
    horizons = {}

    for horizon_years in [5, 10, 20]:
        months = horizon_years * 12

        simple_cost = spend * months

        future_value = 0
        for m in range(months):
            future_value = (future_value + spend) * (1 + monthly_rate)

        opportunity_cost = round(future_value, 2)
        lost_growth = round(future_value - simple_cost, 2)

        real_opportunity = round(future_value / ((1 + INFLATION_RATE) ** horizon_years), 2)

        horizons[f"{horizon_years}_year"] = {
            "years": horizon_years,
            "simple_cost": round(simple_cost, 2),
            "opportunity_cost": opportunity_cost,
            "lost_growth": lost_growth,
            "inflation_adjusted": real_opportunity,
            "monthly_spend": round(spend, 2)
        }

    return {
        "monthly_spend": round(spend, 2),
        "growth_rate": growth_rate,
        "horizons": horizons,
        "insight": _generate_habit_insight(spend, horizons)
    }


def _generate_habit_insight(monthly_spend, horizons):
    ten_year = horizons.get("10_year")
    if not ten_year:
        return None

    return {
        "headline": f"£{monthly_spend:,.0f}/month costs you £{ten_year['opportunity_cost']:,.0f} over 10 years",
        "detail": f"That's not just £{ten_year['simple_cost']:,.0f} spent. It's also £{ten_year['lost_growth']:,.0f} in growth you never earned.",
        "reframe": f"Put £{monthly_spend/2:,.0f} of that into savings each month and it becomes £{ten_year['opportunity_cost']/2:,.0f} in 10 years."
    }


def simulate_scenario(current_state, proposed_changes):
    results = {
        "current_path": [],
        "proposed_path": [],
        "comparison": [],
        "summary": {}
    }

    goals = current_state.get("goals", [])
    income = float(current_state.get("monthly_income", 0))
    commitments = float(current_state.get("fixed_commitments", 0))
    surplus = income - commitments

    proposed_income = float(proposed_changes.get("monthly_income", income))
    proposed_commitments = float(proposed_changes.get("fixed_commitments", commitments))
    proposed_surplus = proposed_income - proposed_commitments

    spending_changes = proposed_changes.get("spending_changes", {})

    total_current_allocation = 0
    total_proposed_allocation = 0

    for goal in goals:
        goal_id = goal.get("id")
        goal_name = goal.get("name")
        goal_type = goal.get("type")
        current_allocation = float(goal.get("monthly_allocation", 0))

        proposed_allocation = current_allocation
        change_for_goal = spending_changes.get(str(goal_id))
        if change_for_goal is not None:
            proposed_allocation = float(change_for_goal)

        total_current_allocation += current_allocation
        total_proposed_allocation += proposed_allocation

        if goal_type == "savings_target" and goal.get("target_amount"):
            current_projection = project_goal_timeline(goal, current_allocation)
            proposed_projection = project_goal_timeline(goal, proposed_allocation)
        else:
            current_projection = {"type": goal_type, "allocation": current_allocation}
            proposed_projection = {"type": goal_type, "allocation": proposed_allocation}

        current_months = current_projection.get("months_to_target", 0)
        proposed_months = proposed_projection.get("months_to_target", 0)
        months_difference = current_months - proposed_months

        comparison = {
            "goal_id": goal_id,
            "goal_name": goal_name,
            "goal_type": goal_type,
            "current_allocation": round(current_allocation, 2),
            "proposed_allocation": round(proposed_allocation, 2),
            "allocation_change": round(proposed_allocation - current_allocation, 2),
            "current_months": current_months,
            "proposed_months": proposed_months,
            "months_saved": months_difference,
            "current_date": current_projection.get("completion_date_human", "N/A"),
            "proposed_date": proposed_projection.get("completion_date_human", "N/A"),
            "impact": _describe_impact(months_difference, goal_name)
        }

        results["current_path"].append(current_projection)
        results["proposed_path"].append(proposed_projection)
        results["comparison"].append(comparison)

    freed_surplus = proposed_surplus - surplus
    freed_from_reallocation = total_current_allocation - total_proposed_allocation

    results["summary"] = {
        "current_surplus": round(surplus, 2),
        "proposed_surplus": round(proposed_surplus, 2),
        "surplus_change": round(freed_surplus, 2),
        "total_current_allocation": round(total_current_allocation, 2),
        "total_proposed_allocation": round(total_proposed_allocation, 2),
        "freed_monthly": round(freed_surplus + freed_from_reallocation, 2),
        "goals_affected": len(goals),
        "goals_accelerated": sum(1 for c in results["comparison"] if c["months_saved"] > 0),
        "goals_delayed": sum(1 for c in results["comparison"] if c["months_saved"] < 0),
        "net_insight": _generate_scenario_insight(results["comparison"])
    }

    return results


def _describe_impact(months_difference, goal_name):
    if months_difference > 0:
        if months_difference == 1:
            return f"{goal_name} arrives 1 month sooner"
        elif months_difference < 12:
            return f"{goal_name} arrives {months_difference} months sooner"
        else:
            years = months_difference // 12
            remaining_months = months_difference % 12
            if remaining_months == 0:
                return f"{goal_name} arrives {years} year{'s' if years > 1 else ''} sooner"
            return f"{goal_name} arrives {years} year{'s' if years > 1 else ''} and {remaining_months} month{'s' if remaining_months > 1 else ''} sooner"
    elif months_difference < 0:
        delay = abs(months_difference)
        if delay == 1:
            return f"{goal_name} is delayed by 1 month"
        elif delay < 12:
            return f"{goal_name} is delayed by {delay} months"
        else:
            years = delay // 12
            remaining_months = delay % 12
            if remaining_months == 0:
                return f"{goal_name} is delayed by {years} year{'s' if years > 1 else ''}"
            return f"{goal_name} is delayed by {years} year{'s' if years > 1 else ''} and {remaining_months} month{'s' if remaining_months > 1 else ''}"
    else:
        return f"{goal_name} is unchanged"


def _generate_scenario_insight(comparisons):
    accelerated = [c for c in comparisons if c["months_saved"] > 0]
    delayed = [c for c in comparisons if c["months_saved"] < 0]

    parts = []

    if accelerated:
        best = max(accelerated, key=lambda c: c["months_saved"])
        parts.append(f"Best outcome: {best['impact']}.")

    if delayed:
        worst = min(delayed, key=lambda c: c["months_saved"])
        parts.append(f"Trade-off: {worst['impact']}.")

    if not accelerated and not delayed:
        parts.append("Your goal dates stay the same with these numbers.")

    return " ".join(parts)


def generate_multi_horizon_projection(goal_data, monthly_contribution):
    results = {}

    for horizon in [5, 10, 20]:
        results[f"{horizon}_year"] = {}

        for scenario_name, rate in GROWTH_RATES.items():
            target = float(goal_data.get("target_amount", 0))
            current = float(goal_data.get("current_amount", 0))
            contribution = float(monthly_contribution)

            monthly_rate = rate / 12
            months = horizon * 12
            balance = current

            for m in range(months):
                interest = balance * monthly_rate
                balance += contribution + interest

            reached_target = balance >= target if target > 0 else False

            results[f"{horizon}_year"][scenario_name] = {
                "final_balance": round(balance, 2),
                "total_contributed": round(current + (contribution * months), 2),
                "interest_earned": round(balance - current - (contribution * months), 2),
                "growth_rate": rate,
                "reached_target": reached_target,
                "balance_vs_target": round(balance - target, 2) if target > 0 else None
            }

    return results


def _add_months(start_date, months):
    month = start_date.month - 1 + months
    year = start_date.year + month // 12
    month = month % 12 + 1
    day = min(start_date.day, 28)
    return date(year, month, day)