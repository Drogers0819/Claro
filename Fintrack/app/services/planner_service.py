"""
Smart Financial Planner — Claro v5

Takes a user's income, expenses, goals, and timelines.
Returns a complete phased financial plan with:
- Recommended pot structure (no presets — built from user goals)
- Optimal monthly allocations calculated from deadlines
- Phased plan with automatic milestone-based reallocation
- Month-by-month projections for every pot simultaneously
- Alerts for upcoming phase changes

The user provides 5%. The planner does 95%.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import math
from copy import deepcopy


# ─── CONSTANTS ───────────────────────────────────────────────

EMERGENCY_MONTHS = 3          # Target: 3 months of essentials
LIFESTYLE_PERCENT = 0.15      # 15% of surplus goes to lifestyle minimum
BUFFER_PERCENT = 0.05         # 5% buffer always maintained
MAX_PROJECTION_MONTHS = 120   # 10 years max projection
LIFESTYLE_MIN = 100           # Minimum lifestyle allowance (£)
BUFFER_MIN = 50               # Minimum buffer (£)


# ─── MAIN ENTRY POINT ───────────────────────────────────────

def generate_financial_plan(user_profile, goals, debts=None, upcoming_expenses=None):
    """
    Generate a complete phased financial plan.

    Args:
        user_profile: dict with monthly_income, rent_amount, bills_amount,
                      groceries_estimate, transport_estimate (optional fields)
        goals: list of dicts with name, target_amount, current_amount,
               deadline (date or ISO string), type, goal_id
        debts: list of dicts with name, amount, min_payment (optional)
        upcoming_expenses: list of dicts with name, amount, due_date (optional)

    Returns:
        dict with plan phases, pot allocations, monthly projections, alerts
    """
    if not user_profile or not user_profile.get("monthly_income"):
        return {"error": "Monthly income is required to generate a plan"}

    income = float(user_profile["monthly_income"])
    rent = float(user_profile.get("rent_amount") or 0)
    bills = float(user_profile.get("bills_amount") or 0)
    groceries = float(user_profile.get("groceries_estimate") or 0)
    transport = float(user_profile.get("transport_estimate") or 0)

    essentials = rent + bills + groceries + transport
    surplus = income - essentials

    if surplus <= 0:
        return {
            "error": "Your essential costs exceed your income. No surplus available for savings.",
            "income": round(income, 2),
            "essentials": round(essentials, 2),
            "surplus": round(surplus, 2)
        }

    # Build the pot structure
    pots = _build_pots(surplus, essentials, goals, debts)

    # Calculate optimal allocations
    pots = _calculate_allocations(pots, surplus)

    # Run the month-by-month simulation with phased reallocation
    phases, monthly_projections = _simulate_phases(pots, surplus)

    # Generate alerts
    alerts = _generate_alerts(phases, monthly_projections, pots)

    # Summary stats
    total_allocated = sum(p["monthly_amount"] for p in pots if p["type"] != "lifestyle" and p["type"] != "buffer")
    lifestyle_pot = next((p for p in pots if p["type"] == "lifestyle"), None)
    buffer_pot = next((p for p in pots if p["type"] == "buffer"), None)

    return {
        "income": round(income, 2),
        "essentials": round(essentials, 2),
        "essentials_breakdown": {
            "rent": round(rent, 2),
            "bills": round(bills, 2),
            "groceries": round(groceries, 2),
            "transport": round(transport, 2)
        },
        "surplus": round(surplus, 2),
        "pots": [_pot_to_dict(p) for p in pots],
        "phases": phases,
        "monthly_projections": monthly_projections,
        "alerts": alerts,
        "lifestyle_monthly": round(lifestyle_pot["monthly_amount"], 2) if lifestyle_pot else 0,
        "buffer_monthly": round(buffer_pot["monthly_amount"], 2) if buffer_pot else 0,
        "total_goal_allocation": round(total_allocated, 2),
        "phase_count": len(phases),
        "current_phase": phases[0] if phases else None
    }


# ─── POT BUILDING ───────────────────────────────────────────

def _build_pots(surplus, essentials, goals, debts=None):
    """Build the pot structure from user goals. No presets — everything from input."""
    pots = []
    today = date.today()

    # 1. Debt pots (always first priority)
    if debts:
        for i, debt in enumerate(debts):
            pots.append({
                "name": debt.get("name", f"Debt {i+1}"),
                "type": "debt",
                "target": float(debt.get("amount", 0)),
                "current": 0,
                "monthly_amount": 0,
                "min_payment": float(debt.get("min_payment", 0)),
                "deadline": None,
                "priority": 0,  # Highest priority
                "completed": False,
                "goal_id": debt.get("goal_id")
            })

    # 2. Emergency fund (always included)
    emergency_target = round(essentials * EMERGENCY_MONTHS, 2)
    existing_emergency = _find_existing_savings(goals, "emergency")

    pots.append({
        "name": "Emergency fund",
        "type": "emergency",
        "target": emergency_target,
        "current": existing_emergency,
        "monthly_amount": 0,
        "deadline": None,
        "priority": 1,
        "completed": existing_emergency >= emergency_target,
        "goal_id": _find_goal_id(goals, "emergency")
    })

    # 3. User goals sorted by deadline urgency
    user_goals = _parse_goals(goals, today)
    for i, goal in enumerate(user_goals):
        if goal["type"] == "emergency":
            continue  # Already handled
        pots.append({
            "name": goal["name"],
            "type": goal.get("pot_type", "savings"),
            "target": goal.get("target", 0),
            "current": goal.get("current", 0),
            "monthly_amount": 0,
            "deadline": goal.get("deadline"),
            "months_until_deadline": goal.get("months_until_deadline"),
            "priority": 2 + i,
            "completed": False,
            "goal_id": goal.get("goal_id")
        })

    # 4. Lifestyle (always included — calculated, not guessed)
    pots.append({
        "name": "Lifestyle & family",
        "type": "lifestyle",
        "target": None,  # No target — ongoing
        "current": 0,
        "monthly_amount": 0,
        "deadline": None,
        "priority": 900,
        "completed": False,
        "goal_id": None
    })

    # 5. Buffer (always included)
    pots.append({
        "name": "Buffer",
        "type": "buffer",
        "target": None,
        "current": 0,
        "monthly_amount": 0,
        "deadline": None,
        "priority": 999,
        "completed": False,
        "goal_id": None
    })

    return pots


def _parse_goals(goals, today):
    """Parse user goals into a standardised format sorted by deadline urgency."""
    parsed = []

    for goal in goals:
        name = goal.get("name", "")
        goal_type = goal.get("type", "savings_target")

        # Detect emergency fund goals by name
        if _is_emergency(name):
            parsed.append({
                "name": name,
                "type": "emergency",
                "target": float(goal.get("target_amount") or 0),
                "current": float(goal.get("current_amount") or 0),
                "goal_id": goal.get("id") or goal.get("goal_id"),
                "deadline": None,
                "months_until_deadline": None,
                "pot_type": "emergency"
            })
            continue

        deadline = goal.get("deadline")
        if isinstance(deadline, str) and deadline:
            try:
                deadline = date.fromisoformat(deadline)
            except (ValueError, TypeError):
                deadline = None

        months_until = None
        if deadline and deadline > today:
            delta = relativedelta(deadline, today)
            months_until = delta.years * 12 + delta.months
            if months_until == 0:
                months_until = 1

        target = float(goal.get("target_amount") or 0)
        current = float(goal.get("current_amount") or 0)

        pot_type = "savings"
        if goal_type == "spending_allocation":
            pot_type = "spending"
        elif goal_type == "accumulation":
            pot_type = "accumulation"

        parsed.append({
            "name": name,
            "type": goal_type,
            "target": target,
            "current": current,
            "goal_id": goal.get("id") or goal.get("goal_id"),
            "deadline": deadline,
            "months_until_deadline": months_until,
            "pot_type": pot_type
        })

    # Sort: goals with deadlines first (soonest first), then goals without deadlines
    with_deadline = [g for g in parsed if g["months_until_deadline"] is not None]
    without_deadline = [g for g in parsed if g["months_until_deadline"] is None and g["type"] != "emergency"]

    with_deadline.sort(key=lambda g: g["months_until_deadline"])

    return with_deadline + without_deadline


def _is_emergency(name):
    """Check if a goal name refers to an emergency fund."""
    lower = name.lower()
    return any(term in lower for term in ["emergency", "rainy day", "safety net", "safety fund"])


def _find_existing_savings(goals, goal_type):
    """Find existing savings for a goal type."""
    for goal in goals:
        if _is_emergency(goal.get("name", "")):
            return float(goal.get("current_amount") or 0)
    return 0


def _find_goal_id(goals, goal_type):
    """Find goal_id for a specific type."""
    for goal in goals:
        if _is_emergency(goal.get("name", "")):
            return goal.get("id") or goal.get("goal_id")
    return None


# ─── ALLOCATION CALCULATION ──────────────────────────────────

def _calculate_allocations(pots, surplus):
    """Calculate optimal monthly allocation for each pot."""
    # Reserve lifestyle and buffer first
    lifestyle_amount = max(round(surplus * LIFESTYLE_PERCENT, 2), LIFESTYLE_MIN)
    buffer_amount = max(round(surplus * BUFFER_PERCENT, 2), BUFFER_MIN)

    # Cap lifestyle + buffer at 30% of surplus
    if lifestyle_amount + buffer_amount > surplus * 0.30:
        lifestyle_amount = round(surplus * 0.20, 2)
        buffer_amount = round(surplus * 0.05, 2)

    available_for_goals = surplus - lifestyle_amount - buffer_amount

    if available_for_goals <= 0:
        # Surplus too small — just split it
        for pot in pots:
            if pot["type"] == "lifestyle":
                pot["monthly_amount"] = max(surplus * 0.60, 0)
            elif pot["type"] == "buffer":
                pot["monthly_amount"] = max(surplus * 0.10, 0)
        return pots

    # Assign lifestyle and buffer
    for pot in pots:
        if pot["type"] == "lifestyle":
            pot["monthly_amount"] = lifestyle_amount
        elif pot["type"] == "buffer":
            pot["monthly_amount"] = buffer_amount

    # Allocate to goal pots
    goal_pots = [p for p in pots if p["type"] not in ("lifestyle", "buffer") and not p["completed"]]

    if not goal_pots:
        # No goals — everything to lifestyle
        for pot in pots:
            if pot["type"] == "lifestyle":
                pot["monthly_amount"] += available_for_goals
        return pots

    # Calculate ideal monthly amount for each goal based on deadline
    for pot in goal_pots:
        remaining = pot["target"] - pot["current"] if pot["target"] else 0
        if remaining <= 0:
            pot["ideal_monthly"] = 0
            pot["completed"] = True
            continue

        if pot["type"] == "debt":
            # Debts: pay off as fast as possible, minimum 2x min payment
            pot["ideal_monthly"] = max(pot.get("min_payment", 0) * 2, remaining / 6)
        elif pot.get("months_until_deadline") and pot["months_until_deadline"] > 0:
            # Goal with deadline: calculate exact amount needed
            pot["ideal_monthly"] = remaining / pot["months_until_deadline"]
        elif pot["type"] == "emergency":
            # Emergency: target 6-9 months to fill
            pot["ideal_monthly"] = remaining / 7
        else:
            # No deadline: spread over 24 months default
            pot["ideal_monthly"] = remaining / 24 if remaining > 0 else 0

    # Sort by priority (debts first, then emergency, then deadline urgency)
    goal_pots.sort(key=lambda p: p["priority"])

    # Allocate available money to goals in priority order
    remaining_budget = available_for_goals

    for pot in goal_pots:
        if pot.get("completed"):
            continue

        ideal = pot.get("ideal_monthly", 0)
        if ideal <= 0:
            continue

        allocated = min(ideal, remaining_budget)
        pot["monthly_amount"] = round(allocated, 2)
        remaining_budget -= allocated

        if remaining_budget <= 0:
            break

    # If there's money left over, distribute to goals proportionally
    if remaining_budget > 1:
        active_pots = [p for p in goal_pots if p["monthly_amount"] > 0 and not p.get("completed")]
        if active_pots:
            # Give extra to the highest priority pot
            active_pots[0]["monthly_amount"] = round(
                active_pots[0]["monthly_amount"] + remaining_budget, 2
            )
        else:
            # No active goals — add to lifestyle
            for pot in pots:
                if pot["type"] == "lifestyle":
                    pot["monthly_amount"] = round(pot["monthly_amount"] + remaining_budget, 2)

    return pots


# ─── PHASE SIMULATION ────────────────────────────────────────

def _simulate_phases(pots, surplus):
    """
    Run month-by-month simulation. When a pot hits its target,
    redistribute its allocation to remaining goals.
    Returns phases list and monthly projections.
    """
    today = date.today()
    sim_pots = deepcopy(pots)
    phases = []
    monthly_projections = []
    current_phase_pots = _get_active_pot_names(sim_pots)

    phase_start_month = 0
    phase_number = 1

    for month in range(MAX_PROJECTION_MONTHS):
        current_date = today + relativedelta(months=month)
        month_data = {
            "month": month + 1,
            "date": current_date.isoformat(),
            "date_display": current_date.strftime("%b %Y"),
            "pots": {}
        }

        # Apply monthly contributions
        for pot in sim_pots:
            if pot.get("completed"):
                continue

            pot["current"] = round(pot["current"] + pot["monthly_amount"], 2)

            # Check if pot hit target
            if pot["target"] and pot["current"] >= pot["target"]:
                pot["current"] = pot["target"]
                pot["completed"] = True
                pot["completed_month"] = month + 1
                pot["completed_date"] = current_date.isoformat()

        # Record balances
        for pot in sim_pots:
            month_data["pots"][pot["name"]] = {
                "balance": round(pot["current"], 2),
                "monthly_amount": round(pot["monthly_amount"], 2),
                "completed": pot.get("completed", False),
                "target": pot.get("target")
            }

        monthly_projections.append(month_data)

        # Check if any pot completed this month — trigger reallocation
        newly_completed = [p for p in sim_pots
                          if p.get("completed") and p.get("completed_month") == month + 1]

        if newly_completed:
            # Close current phase
            freed_amount = sum(p["monthly_amount"] for p in newly_completed)
            completed_names = [p["name"] for p in newly_completed]

            phases.append({
                "phase": phase_number,
                "start_month": phase_start_month + 1,
                "end_month": month + 1,
                "start_date": (today + relativedelta(months=phase_start_month)).isoformat(),
                "end_date": current_date.isoformat(),
                "duration_months": month + 1 - phase_start_month,
                "active_pots": current_phase_pots,
                "completed_pots": completed_names,
                "description": _phase_description(phase_number, current_phase_pots, completed_names)
            })

            # Redistribute freed money
            _redistribute(sim_pots, freed_amount)

            # Start new phase
            phase_number += 1
            phase_start_month = month + 1
            current_phase_pots = _get_active_pot_names(sim_pots)

        # Check if all goals are complete
        active_goals = [p for p in sim_pots
                       if p["type"] not in ("lifestyle", "buffer") and not p.get("completed")]
        if not active_goals:
            # Final phase
            if phase_start_month <= month:
                phases.append({
                    "phase": phase_number,
                    "start_month": phase_start_month + 1,
                    "end_month": month + 1,
                    "start_date": (today + relativedelta(months=phase_start_month)).isoformat(),
                    "end_date": current_date.isoformat(),
                    "duration_months": month + 1 - phase_start_month,
                    "active_pots": current_phase_pots,
                    "completed_pots": [p["name"] for p in newly_completed] if newly_completed else [],
                    "description": "All goals reached. Surplus redirected to lifestyle and growth."
                })
            break

    # If we hit MAX months without completing, close the open phase
    if not phases or phases[-1]["end_month"] < len(monthly_projections):
        remaining_goals = [p for p in sim_pots
                          if p["type"] not in ("lifestyle", "buffer") and not p.get("completed")]
        if remaining_goals:
            phases.append({
                "phase": phase_number,
                "start_month": phase_start_month + 1,
                "end_month": len(monthly_projections),
                "start_date": (today + relativedelta(months=phase_start_month)).isoformat(),
                "end_date": monthly_projections[-1]["date"],
                "duration_months": len(monthly_projections) - phase_start_month,
                "active_pots": current_phase_pots,
                "completed_pots": [],
                "description": _phase_description(phase_number, current_phase_pots, []),
                "note": "Some goals extend beyond the 10-year projection window"
            })

    # Pad to at least 24 months if simulation ended early
    while len(monthly_projections) < 24:
        month_idx = len(monthly_projections)
        current_date = today + relativedelta(months=month_idx)
        month_data = {
            "month": month_idx + 1,
            "date": current_date.isoformat(),
            "date_display": current_date.strftime("%b %Y"),
            "pots": {}
        }
        for pot in sim_pots:
            # Lifestyle and buffer keep accumulating, goals stay at target
            if pot["type"] in ("lifestyle", "buffer"):
                pot["current"] = round(pot["current"] + pot["monthly_amount"], 2)
            month_data["pots"][pot["name"]] = {
                "balance": round(pot["current"], 2),
                "monthly_amount": round(pot["monthly_amount"], 2),
                "completed": pot.get("completed", False),
                "target": pot.get("target")
            }
        monthly_projections.append(month_data)

    # Trim to relevant period (up to 12 months after last completion)
    last_completion = max((p.get("completed_month", 0) for p in sim_pots), default=0)
    trim_to = min(last_completion + 12, len(monthly_projections))
    trim_to = max(trim_to, 24)
    monthly_projections = monthly_projections[:trim_to]

    return phases, monthly_projections


def _redistribute(pots, freed_amount):
    """Redistribute freed money from completed pots to remaining goals."""
    remaining_goals = [p for p in pots
                      if p["type"] not in ("lifestyle", "buffer") and not p.get("completed")]

    if not remaining_goals:
        # All goals done — add to lifestyle
        for pot in pots:
            if pot["type"] == "lifestyle":
                pot["monthly_amount"] = round(pot["monthly_amount"] + freed_amount, 2)
        return

    # Sort by priority
    remaining_goals.sort(key=lambda p: p["priority"])

    # Give to highest priority remaining goal first
    # If that goal has a deadline, check if it needs the full amount
    for goal in remaining_goals:
        remaining_needed = (goal["target"] - goal["current"]) if goal["target"] else float("inf")
        if remaining_needed <= 0:
            continue

        # Calculate how much this goal could use
        if goal.get("months_until_deadline") and goal["months_until_deadline"] > 0:
            ideal = remaining_needed / max(goal["months_until_deadline"] - (goal.get("completed_month", 0) or 0), 1)
            can_use = max(ideal - goal["monthly_amount"], 0)
        else:
            can_use = freed_amount

        give = min(freed_amount, can_use)
        goal["monthly_amount"] = round(goal["monthly_amount"] + give, 2)
        freed_amount -= give

        if freed_amount <= 0:
            break

    # Any remaining freed amount goes to the first active goal
    if freed_amount > 0 and remaining_goals:
        remaining_goals[0]["monthly_amount"] = round(
            remaining_goals[0]["monthly_amount"] + freed_amount, 2
        )


def _get_active_pot_names(pots):
    """Get names of pots that are actively receiving contributions."""
    return [p["name"] for p in pots
            if p["monthly_amount"] > 0 and not p.get("completed")]


def _phase_description(phase_num, active_pots, completed_pots):
    """Generate a human-readable phase description."""
    goal_pots = [p for p in active_pots if p not in ("Lifestyle & family", "Buffer")]

    if completed_pots:
        completed_str = " and ".join(completed_pots)
        if len(goal_pots) <= 1:
            focus = goal_pots[0] if goal_pots else "your goals"
        else:
            focus = ", ".join(goal_pots[:-1]) + " and " + goal_pots[-1]
        return f"Building {focus}. {completed_str} completed at end of phase."
    else:
        if not goal_pots:
            return "All goals on track."
        if len(goal_pots) == 1:
            return f"Focus: {goal_pots[0]}."
        return f"Building {', '.join(goal_pots[:-1])} and {goal_pots[-1]}."


# ─── ALERTS ──────────────────────────────────────────────────

def _generate_alerts(phases, monthly_projections, pots):
    """Generate alerts about the plan."""
    alerts = []

    # Alert: upcoming phase change
    if len(phases) > 1:
        next_change = phases[0].get("end_month", 0)
        if next_change <= 3:
            completed = phases[0].get("completed_pots", [])
            if completed:
                alerts.append({
                    "type": "phase_change_soon",
                    "severity": "info",
                    "message": f"Your {' and '.join(completed)} will be fully funded in {next_change} month{'s' if next_change != 1 else ''}. "
                              f"That money will automatically redirect to your next priority."
                })

    # Alert: goal won't hit deadline
    for pot in pots:
        if pot.get("deadline") and not pot.get("completed"):
            remaining = pot["target"] - pot["current"]
            if pot["monthly_amount"] > 0:
                months_needed = math.ceil(remaining / pot["monthly_amount"])
                months_available = pot.get("months_until_deadline", months_needed)
                if months_available and months_needed > months_available:
                    alerts.append({
                        "type": "deadline_risk",
                        "severity": "warning",
                        "message": f"'{pot['name']}' needs {months_needed} months at current pace but deadline is in {months_available} months. "
                                  f"Consider increasing the allocation or extending the deadline."
                    })

    # Alert: no emergency fund
    emergency = next((p for p in pots if p["type"] == "emergency"), None)
    if emergency and emergency["current"] < emergency["target"] * 0.5:
        alerts.append({
            "type": "low_emergency_fund",
            "severity": "warning",
            "message": f"Your emergency fund is below 50%. The plan prioritises building this to "
                      f"£{emergency['target']:,.0f} ({EMERGENCY_MONTHS} months of essentials)."
        })

    return alerts


# ─── AFFORDABILITY CHECK ─────────────────────────────────────

def can_i_afford(plan, expense_name, amount, target_month=None):
    """
    Check if a one-off expense is affordable against the plan.

    Args:
        plan: the output of generate_financial_plan()
        expense_name: description of the expense
        amount: cost in pounds
        target_month: which month (1-indexed) to check, defaults to current

    Returns:
        dict with verdict, impact on plan, and suggestions
    """
    if "error" in plan:
        return {"affordable": False, "reason": plan["error"]}

    lifestyle_pot = next((p for p in plan["pots"] if p["type"] == "lifestyle"), None)
    if not lifestyle_pot:
        return {"affordable": False, "reason": "No lifestyle allocation in plan"}

    monthly_lifestyle = lifestyle_pot["monthly_amount"]

    # Check target month's projected lifestyle balance
    if target_month and target_month <= len(plan.get("monthly_projections", [])):
        proj = plan["monthly_projections"][target_month - 1]
        lifestyle_balance = proj["pots"].get("Lifestyle & family", {}).get("balance", 0)
    else:
        lifestyle_balance = monthly_lifestyle

    if amount <= lifestyle_balance:
        remaining_after = lifestyle_balance - amount
        return {
            "affordable": True,
            "expense": expense_name,
            "amount": round(amount, 2),
            "source": "Lifestyle & family pot",
            "balance_before": round(lifestyle_balance, 2),
            "balance_after": round(remaining_after, 2),
            "message": f"Yes, your lifestyle pot will have £{lifestyle_balance:,.0f} by then. "
                      f"After the {expense_name} you'll have £{remaining_after:,.0f} left.",
            "impact": "none"
        }
    elif amount <= lifestyle_balance + plan.get("buffer_monthly", 0) * 2:
        shortfall = amount - lifestyle_balance
        return {
            "affordable": True,
            "expense": expense_name,
            "amount": round(amount, 2),
            "source": "Lifestyle + buffer",
            "balance_before": round(lifestyle_balance, 2),
            "shortfall": round(shortfall, 2),
            "message": f"Tight but doable. Your lifestyle pot covers £{lifestyle_balance:,.0f}. "
                      f"The remaining £{shortfall:,.0f} would come from your buffer.",
            "impact": "minor"
        }
    else:
        return {
            "affordable": False,
            "expense": expense_name,
            "amount": round(amount, 2),
            "balance_available": round(lifestyle_balance, 2),
            "shortfall": round(amount - lifestyle_balance, 2),
            "message": f"{expense_name} costs £{amount:,.0f} and your lifestyle pot has £{lifestyle_balance:,.0f}. "
                      f"You'd need to pause a goal contribution for a month to cover the £{amount - lifestyle_balance:,.0f} gap.",
            "impact": "significant"
        }


# ─── REPLAN ON LIFE EVENTS ───────────────────────────────────

def replan_with_change(user_profile, goals, change_type, change_data, debts=None):
    """
    Regenerate the plan with a life event applied.

    Args:
        change_type: "raise", "job_loss", "new_goal", "remove_goal", "income_change"
        change_data: dict with relevant change info

    Returns:
        dict with new_plan and comparison to old plan
    """
    old_plan = generate_financial_plan(user_profile, goals, debts)

    modified_profile = deepcopy(user_profile)
    modified_goals = deepcopy(goals)

    if change_type == "raise":
        amount = float(change_data.get("amount", 0))
        modified_profile["monthly_income"] = float(modified_profile["monthly_income"]) + amount

    elif change_type == "income_change":
        modified_profile["monthly_income"] = float(change_data.get("new_income", 0))

    elif change_type == "job_loss":
        modified_profile["monthly_income"] = float(change_data.get("partner_income", 0))

    elif change_type == "new_goal":
        modified_goals.append(change_data.get("goal", {}))

    elif change_type == "remove_goal":
        goal_id = change_data.get("goal_id")
        modified_goals = [g for g in modified_goals if g.get("id") != goal_id]

    new_plan = generate_financial_plan(modified_profile, modified_goals, debts)

    # Compare key metrics
    comparison = {}
    if "error" not in old_plan and "error" not in new_plan:
        comparison = {
            "surplus_change": round(new_plan["surplus"] - old_plan["surplus"], 2),
            "lifestyle_change": round(new_plan["lifestyle_monthly"] - old_plan["lifestyle_monthly"], 2),
            "phase_count_change": new_plan["phase_count"] - old_plan["phase_count"]
        }

    return {
        "new_plan": new_plan,
        "previous_plan_summary": {
            "surplus": old_plan.get("surplus"),
            "phase_count": old_plan.get("phase_count"),
            "lifestyle_monthly": old_plan.get("lifestyle_monthly")
        },
        "comparison": comparison,
        "change_applied": change_type
    }


# ─── PLAN SUMMARY (for whispers and overview) ────────────────

def get_plan_summary(plan):
    """Generate a one-paragraph summary of the current plan state."""
    if "error" in plan:
        return plan["error"]

    current_phase = plan.get("current_phase")
    if not current_phase:
        return "Your financial plan is being calculated."

    phase_num = current_phase.get("phase", 1)
    total_phases = plan.get("phase_count", 1)
    active_pots = [p for p in current_phase.get("active_pots", [])
                   if p not in ("Lifestyle & family", "Buffer")]
    duration = current_phase.get("duration_months", 0)
    completed = current_phase.get("completed_pots", [])

    if active_pots:
        focus = " and ".join(active_pots)
    else:
        focus = "your goals"

    summary = f"Phase {phase_num} of {total_phases}, building {focus}."

    if completed:
        summary += f" {' and '.join(completed)} will be done in {duration} month{'s' if duration != 1 else ''}."

    surplus_pots = [p for p in plan.get("pots", [])
                    if p["type"] not in ("lifestyle", "buffer") and not p.get("completed")]
    if surplus_pots:
        remaining_total = sum(
            (p.get("target", 0) - p.get("current", 0)) for p in surplus_pots if p.get("target")
        )
        if remaining_total > 0:
            summary += f" £{remaining_total:,.0f} to go across all goals."

    return summary


# ─── HELPERS ─────────────────────────────────────────────────

def _pot_to_dict(pot):
    """Convert a pot to a clean dict for API responses."""
    result = {
        "name": pot["name"],
        "type": pot["type"],
        "target": round(pot["target"], 2) if pot["target"] else None,
        "current": round(pot["current"], 2),
        "monthly_amount": round(pot["monthly_amount"], 2),
        "completed": pot.get("completed", False),
        "priority": pot.get("priority", 99),
        "goal_id": pot.get("goal_id")
    }

    if pot.get("deadline"):
        result["deadline"] = pot["deadline"].isoformat() if isinstance(pot["deadline"], date) else pot["deadline"]

    if pot.get("completed_month"):
        result["completed_month"] = pot["completed_month"]
        result["completed_date"] = pot.get("completed_date")

    if pot.get("months_until_deadline"):
        result["months_until_deadline"] = pot["months_until_deadline"]

    # Calculate months to target at current rate
    if pot["target"] and pot["monthly_amount"] > 0 and not pot.get("completed"):
        remaining = pot["target"] - pot["current"]
        if remaining > 0:
            result["months_to_target"] = math.ceil(remaining / pot["monthly_amount"])

    return result