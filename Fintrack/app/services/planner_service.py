"""
Smart Financial Planner — Claro v5

Follows professional financial planning methodology:
  Stage 1: Mini emergency buffer (£1,000 or 1 month essentials)
  Stage 2: Clear ALL debt aggressively
  Stage 3: Full emergency fund (3 months essentials)
  Stage 4: Goals by deadline urgency
  Stage 5: Long-term goals

The user provides 5%. The planner does 95%.

FCA compliance: This is financial guidance (cash flow planning),
not regulated advice. We never recommend specific financial products.
"""

from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import math
from copy import deepcopy


# ─── CONSTANTS ───────────────────────────────────────────────

EMERGENCY_MONTHS = 3
MINI_EMERGENCY = 1000
LIFESTYLE_PERCENT = 0.15
BUFFER_PERCENT = 0.05
MAX_PROJECTION_MONTHS = 120
LIFESTYLE_MIN = 100
BUFFER_MIN = 50


# ─── MAIN ENTRY POINT ───────────────────────────────────────

def generate_financial_plan(user_profile, goals, debts=None, upcoming_expenses=None):
    if not user_profile or not user_profile.get("monthly_income"):
        return {"error": "Monthly income is required to generate a plan"}

    income = float(user_profile["monthly_income"])
    rent = float(user_profile.get("rent_amount") or 0)
    bills = float(user_profile.get("bills_amount") or 0)
    groceries = float(user_profile.get("groceries_estimate") or 0)
    transport = float(user_profile.get("transport_estimate") or 0)
    subscriptions = float(user_profile.get("subscriptions_total") or 0)
    other = float(user_profile.get("other_commitments") or 0)

    essentials = rent + bills + groceries + transport + subscriptions + other
    surplus = income - essentials

    if surplus <= 0:
        return {
            "error": "Your essential costs exceed your income. No surplus available for savings.",
            "income": round(income, 2),
            "essentials": round(essentials, 2),
            "surplus": round(surplus, 2)
        }

    pots = _build_pots(surplus, essentials, goals, debts)
    pots = _staged_allocation(pots, surplus, essentials)
    phases, monthly_projections = _simulate_phases(pots, surplus)
    alerts = _generate_alerts(phases, monthly_projections, pots)

    lifestyle_pot = next((p for p in pots if p["type"] == "lifestyle"), None)
    buffer_pot = next((p for p in pots if p["type"] == "buffer"), None)

    return {
        "income": round(income, 2),
        "essentials": round(essentials, 2),
        "essentials_breakdown": {
            "rent": round(rent, 2),
            "bills": round(bills, 2),
            "groceries": round(groceries, 2),
            "transport": round(transport, 2),
            "subscriptions": round(subscriptions, 2),
            "other_commitments": round(other, 2)
        },
        "surplus": round(surplus, 2),
        "pots": [_pot_to_dict(p) for p in pots],
        "phases": phases,
        "monthly_projections": monthly_projections,
        "alerts": alerts,
        "lifestyle_monthly": round(lifestyle_pot["monthly_amount"], 2) if lifestyle_pot else 0,
        "buffer_monthly": round(buffer_pot["monthly_amount"], 2) if buffer_pot else 0,
        "total_goal_allocation": round(sum(
            p["monthly_amount"] for p in pots if p["type"] not in ("lifestyle", "buffer")
        ), 2),
        "phase_count": len(phases),
        "current_phase": phases[0] if phases else None
    }


# ─── POT BUILDING ───────────────────────────────────────────

def _build_pots(surplus, essentials, goals, debts=None):
    pots = []
    today = date.today()

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
                "priority": 0,
                "completed": False,
                "goal_id": debt.get("goal_id")
            })

    # Emergency fund is now a regular goal — no special pot created here

    user_goals = _parse_goals(goals, today)
    for i, goal in enumerate(user_goals):
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

    pots.append({
        "name": "Lifestyle & family",
        "type": "lifestyle",
        "target": None,
        "current": 0,
        "monthly_amount": 0,
        "deadline": None,
        "priority": 900,
        "completed": False,
        "goal_id": None
    })

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
    parsed = []

    for goal in goals:
        name = goal.get("name", "")
        goal_type = goal.get("type", "savings_target")

        
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
        if _is_debt_goal(name):
            pot_type = "debt"
        elif goal_type == "spending_allocation":
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

    with_deadline = [g for g in parsed if g["months_until_deadline"] is not None]
    without_deadline = [g for g in parsed if g["months_until_deadline"] is None]
    with_deadline.sort(key=lambda g: g["months_until_deadline"])

    return with_deadline + without_deadline


def _is_debt_goal(name):
    lower = name.lower()
    return any(term in lower for term in [
        "credit card", "loan", "debt", "overdraft", "pay off",
        "pay back", "repay", "owe", "borrowed"
    ])


def _find_existing_savings(goals, goal_type):
    for goal in goals:
        if _is_emergency(goal.get("name", "")):
            return float(goal.get("current_amount") or 0)
    return 0


def _find_goal_id(goals, goal_type):
    for goal in goals:
        if _is_emergency(goal.get("name", "")):
            return goal.get("id") or goal.get("goal_id")
    return None


# ─── STAGED ALLOCATION ──────────────────────────────────────

def _staged_allocation(pots, surplus, essentials):
    """
    Proportional allocation: everything gets funded simultaneously.
    Priority pots (emergency, debt) get higher weight, not exclusive access.
    Phase milestones are descriptive — they don't block other goals.
    """
    lifestyle_amount = max(round(surplus * LIFESTYLE_PERCENT, 2), LIFESTYLE_MIN)
    buffer_amount = max(round(surplus * BUFFER_PERCENT, 2), BUFFER_MIN)

    if lifestyle_amount + buffer_amount > surplus * 0.30:
        lifestyle_amount = round(surplus * 0.20, 2)
        buffer_amount = round(surplus * 0.05, 2)

    for pot in pots:
        if pot["type"] == "lifestyle":
            pot["monthly_amount"] = lifestyle_amount
        elif pot["type"] == "buffer":
            pot["monthly_amount"] = buffer_amount

    available = surplus - lifestyle_amount - buffer_amount
    if available <= 0:
        return pots

    # ── STAGE 0: Must-hit deadline goals (funded before everything) ──
    funded_must_hits = set()
    must_hit_pots = [p for p in pots if "(must-hit)" in p.get("name", "").lower()
                     and p.get("deadline") and not p.get("completed")]
    for pot in must_hit_pots:
        remaining = pot.get("target", 0) - pot.get("current", 0)
        if remaining <= 0:
            continue
        months_left = pot.get("months_until_deadline") or 1
        months_left = max(months_left, 1)
        needed = round(remaining / months_left, 2)
        allocation = min(needed, available)
        if allocation > 0:
            pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + allocation, 2)
            pot["months_to_target"] = months_left
            pot["name"] = pot["name"].replace(" (must-hit)", "").replace(" (Must-hit)", "")
            pot["_stage"] = "must_hit"
            available -= allocation
            funded_must_hits.add(pot.get("goal_id"))
    if available <= 0:
        return pots

    # ── Gather all active pots for proportional allocation ──
    debt_pots = [p for p in pots if (p["type"] == "debt" or _is_debt_goal(p.get("name", "")))
                 and not p.get("completed") and p["type"] not in ("lifestyle", "buffer")]
    goal_pots = [p for p in pots if p["type"] not in ("lifestyle", "buffer", "debt")
                 and not _is_debt_goal(p.get("name", ""))
                 and not p.get("completed")
                 and p.get("goal_id") not in funded_must_hits]

    # Build allocation pool: every active pot with remaining > 0
    pool = []

    for pot in debt_pots + goal_pots:
        if not pot or pot.get("completed"):
            continue
        remaining = max((pot.get("target") or 0) - (pot.get("current") or 0), 0)
        if remaining <= 0:
            continue
        pot["_remaining"] = remaining

        # Calculate monthly need
        months = pot.get("months_until_deadline")
        if months and months > 0:
            monthly_need = remaining / months
        elif pot["type"] == "debt" or _is_debt_goal(pot.get("name", "")):
            # Debt: target aggressive clearance in 3 months
            monthly_need = remaining / 3
        else:
            # No deadline: spread over 12 months as a baseline
            monthly_need = remaining / 12

        # Priority weights
        if pot["type"] == "debt" or _is_debt_goal(pot.get("name", "")):
            weight = 2.0
        elif months and months <= 6:
            weight = 4.0
        elif months and months <= 12:
            weight = 2.5
        elif months and months <= 24:
            weight = 1.5
        else:
            weight = 1.0

        pot["_monthly_need"] = monthly_need
        pot["_weight"] = weight
        pot["_weighted_need"] = monthly_need * weight
        pool.append(pot)

    if not pool:
        # Nothing to allocate — give excess to lifestyle
        for pot in pots:
            if pot["type"] == "lifestyle":
                pot["monthly_amount"] = round(pot["monthly_amount"] + available, 2)
        return pots

    # ── Proportional distribution with caps ──
    remaining_pool = list(pool)
    remaining_available = available

    # Multiple passes to handle cap redistribution
    for _ in range(5):
        if not remaining_pool or remaining_available <= 0:
            break

        total_weighted = sum(p["_weighted_need"] for p in remaining_pool)
        if total_weighted <= 0:
            # Equal split if no weighted needs
            each = round(remaining_available / len(remaining_pool), 2)
            for pot in remaining_pool:
                pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + each, 2)
            remaining_available = 0
            break

        capped = []
        uncapped = []
        spent = 0

        for pot in remaining_pool:
            share = (pot["_weighted_need"] / total_weighted) * remaining_available
            cap = pot["_remaining"]  # Never allocate more than what's remaining

            if share >= cap:
                pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + cap, 2)
                spent += cap
                capped.append(pot)
            else:
                pot["_tentative"] = share
                uncapped.append(pot)

        if not capped:
            # No one hit their cap — finalize all tentative allocations
            for pot in uncapped:
                pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + pot["_tentative"], 2)
            remaining_available = 0
            break
        else:
            remaining_available -= spent
            remaining_pool = uncapped

    # Any leftover goes to lifestyle
    if remaining_available > 0.01:
        for pot in pots:
            if pot["type"] == "lifestyle":
                pot["monthly_amount"] = round(pot["monthly_amount"] + remaining_available, 2)
                break

    # Calculate months_to_target for each funded pot
    for pot in pool:
        if pot["monthly_amount"] > 0 and pot.get("_remaining", 0) > 0:
            pot["months_to_target"] = max(1, round(pot["_remaining"] / pot["monthly_amount"]))

    return pots


def _distribute_by_deadline(goal_pots, available):
    """Distribute available money across goals.
    
    Professional approach: deadline goals get funded first by urgency.
    No-deadline goals get whatever remains.
    """
    if not goal_pots or available <= 0:
        return

    # Split into deadline and no-deadline groups
    deadline_pots = [p for p in goal_pots if p.get("months_until_deadline") and p["months_until_deadline"] > 0]
    open_pots = [p for p in goal_pots if not p.get("months_until_deadline") or p["months_until_deadline"] is None]

    # Calculate what deadline goals need per month
    for pot in deadline_pots:
        remaining = pot.get("_remaining", pot.get("target", 0) - pot.get("current", 0))
        if remaining <= 0:
            pot["_ideal"] = 0
            continue
        pot["_ideal"] = remaining / pot["months_until_deadline"]

        # Urgency weight
        if pot["months_until_deadline"] <= 6:
            pot["_weight"] = 4.0
        elif pot["months_until_deadline"] <= 12:
            pot["_weight"] = 2.5
        elif pot["months_until_deadline"] <= 24:
            pot["_weight"] = 1.5
        else:
            pot["_weight"] = 1.0

    active_deadline = [p for p in deadline_pots if p.get("_ideal", 0) > 0]
    total_ideal = sum(p["_ideal"] for p in active_deadline)

    # Fund deadline goals first
    if active_deadline:
        if total_ideal <= available:
            # Enough for all deadline goals at their ideal
            for pot in active_deadline:
                pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + pot["_ideal"], 2)
            available -= total_ideal
        else:
            # Not enough — split by urgency weighting
            weighted_total = sum(p["_ideal"] * p["_weight"] for p in active_deadline)
            for pot in active_deadline:
                if weighted_total > 0:
                    share = (pot["_ideal"] * pot["_weight"]) / weighted_total
                    pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + available * share, 2)
                else:
                    pot["monthly_amount"] = round(
                        pot.get("monthly_amount", 0) + available / len(active_deadline), 2
                    )
            available = 0

    # Remaining goes to no-deadline goals
    if available > 0 and open_pots:
        # Spread evenly or by remaining amount
        total_remaining = sum(
            max(p.get("_remaining", p.get("target", 0) - p.get("current", 0)), 0)
            for p in open_pots
        )
        for pot in open_pots:
            remaining = max(pot.get("_remaining", pot.get("target", 0) - pot.get("current", 0)), 0)
            if total_remaining > 0 and remaining > 0:
                share = remaining / total_remaining
                pot["monthly_amount"] = round(pot.get("monthly_amount", 0) + available * share, 2)
            elif open_pots:
                pot["monthly_amount"] = round(
                    pot.get("monthly_amount", 0) + available / len(open_pots), 2
                )

    # Fix rounding across all pots
    all_active = [p for p in goal_pots if p.get("monthly_amount", 0) > 0]
    total_given = sum(p["monthly_amount"] for p in all_active)
    original_available = sum(p["monthly_amount"] for p in goal_pots)
    if all_active and total_given > original_available + 0.01:
        diff = total_given - original_available
        all_active[-1]["monthly_amount"] = round(all_active[-1]["monthly_amount"] - diff, 2)


# ─── PHASE SIMULATION ────────────────────────────────────────

def _simulate_phases(pots, surplus):
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

        for pot in sim_pots:
            if pot.get("completed"):
                continue
            pot["current"] = round(pot["current"] + pot["monthly_amount"], 2)
            if pot["target"] and pot["current"] >= pot["target"]:
                pot["current"] = pot["target"]
                pot["completed"] = True
                pot["completed_month"] = month + 1
                pot["completed_date"] = current_date.isoformat()

        for pot in sim_pots:
            month_data["pots"][pot["name"]] = {
                "balance": round(pot["current"], 2),
                "monthly_amount": round(pot["monthly_amount"], 2),
                "completed": pot.get("completed", False),
                "target": pot.get("target")
            }

        monthly_projections.append(month_data)

        newly_completed = [p for p in sim_pots
                          if p.get("completed") and p.get("completed_month") == month + 1]

        if newly_completed:
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
                "description": _phase_description(phase_number, current_phase_pots, completed_names, sim_pots)
            })

            _redistribute(sim_pots, freed_amount)

            phase_number += 1
            phase_start_month = month + 1
            current_phase_pots = _get_active_pot_names(sim_pots)

        active_goals = [p for p in sim_pots
                       if p["type"] not in ("lifestyle", "buffer") and not p.get("completed")]
        if not active_goals:
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
                    "description": "All goals reached. Your full surplus is now available."
                })
            break

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
            if pot["type"] in ("lifestyle", "buffer"):
                pot["current"] = round(pot["current"] + pot["monthly_amount"], 2)
            month_data["pots"][pot["name"]] = {
                "balance": round(pot["current"], 2),
                "monthly_amount": round(pot["monthly_amount"], 2),
                "completed": pot.get("completed", False),
                "target": pot.get("target")
            }
        monthly_projections.append(month_data)

    last_completion = max((p.get("completed_month", 0) for p in sim_pots), default=0)
    trim_to = min(last_completion + 12, len(monthly_projections))
    trim_to = max(trim_to, 24)
    monthly_projections = monthly_projections[:trim_to]

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
                "description": _phase_description(phase_number, current_phase_pots, [], sim_pots)
            })

    return phases, monthly_projections


def _redistribute(pots, freed_amount):
    remaining_goals = [p for p in pots
                      if p["type"] not in ("lifestyle", "buffer") and not p.get("completed")]

    if not remaining_goals:
        for pot in pots:
            if pot["type"] == "lifestyle":
                pot["monthly_amount"] = round(pot["monthly_amount"] + freed_amount, 2)
        return

    remaining_goals.sort(key=lambda p: p["priority"])

    for goal in remaining_goals:
        remaining_needed = (goal["target"] - goal["current"]) if goal["target"] else float("inf")
        if remaining_needed <= 0:
            continue

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

    if freed_amount > 0 and remaining_goals:
        remaining_goals[0]["monthly_amount"] = round(
            remaining_goals[0]["monthly_amount"] + freed_amount, 2
        )


def _get_active_pot_names(pots):
    return [p["name"] for p in pots
            if p["monthly_amount"] > 0 and not p.get("completed")]


def _phase_description(phase_num, active_pots, completed_pots, all_pots=None):
    goal_pots = [p for p in active_pots if p not in ("Lifestyle & family", "Buffer")]

    debt_active = []
    if all_pots:
        debt_active = [p["name"] for p in all_pots
                      if (p["type"] == "debt" or _is_debt_goal(p.get("name", "")))
                      and not p.get("completed") and p["monthly_amount"] > 0]

    if debt_active and not completed_pots:
        debt_str = " and ".join(debt_active)
        return f"Clearing {debt_str}. Other goals begin once debt is gone."

    if completed_pots:
        completed_str = " and ".join(completed_pots)
        if debt_active:
            return f"Clearing debt. {completed_str} completed at end of phase."
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
    alerts = []

    debt_pots = [p for p in pots if (p["type"] == "debt" or _is_debt_goal(p.get("name", "")))
                 and not p.get("completed") and p["monthly_amount"] > 0]
    if debt_pots:
        debt_names = " and ".join(p["name"] for p in debt_pots)
        months_to_clear = max(
            (math.ceil((p["target"] - p["current"]) / p["monthly_amount"]) if p["monthly_amount"] > 0 else 0)
            for p in debt_pots
        )
        alerts.append({
            "type": "debt_priority",
            "severity": "info",
            "message": f"Your surplus is focused on clearing {debt_names} first. "
                      f"Clearing debt before saving is the fastest way to improve your position. "
                      f"Once cleared (~{int(months_to_clear)} months), that money goes straight to your goals."
        })

    if len(phases) > 1:
        next_change = phases[0].get("end_month", 0)
        if next_change <= 3:
            # Only mention pots that are still active and funded
            active_names = {p["name"] for p in pots if not p.get("completed") and p.get("monthly_amount", 0) > 0}
            completed = [name for name in phases[0].get("completed_pots", []) if name in active_names]
            if completed:
                alerts.append({
                    "type": "phase_change_soon",
                    "severity": "info",
                    "message": f"Your {' and '.join(completed)} will be fully funded in "
                              f"{next_change} month{'s' if next_change != 1 else ''}. "
                              f"That money will automatically redirect to your next priority."
                })

    for pot in pots:
        if pot.get("deadline") and not pot.get("completed") and pot["monthly_amount"] > 0:
            remaining = pot["target"] - pot["current"]
            if pot["monthly_amount"] > 0:
                months_needed = math.ceil(remaining / pot["monthly_amount"])
                months_available = pot.get("months_until_deadline", months_needed)
                if months_available and months_needed > months_available:
                    alerts.append({
                        "type": "deadline_risk",
                        "severity": "warning",
                        "message": f"'{pot['name']}' needs {months_needed} months at current pace "
                                  f"but deadline is in {months_available} months. "
                                  f"Consider extending the deadline or adjusting the target."
                    })

    paused_goals = [p for p in pots if p["type"] not in ("lifestyle", "buffer", "debt")
                    and not _is_debt_goal(p.get("name", ""))
                    and p["monthly_amount"] == 0 and not p.get("completed")]
    if paused_goals and debt_pots:
        names = ", ".join(p["name"] for p in paused_goals)
        alerts.append({
            "type": "goals_paused",
            "severity": "info",
            "message": f"Your {names} {'is' if len(paused_goals) == 1 else 'are'} paused while debt is being cleared. "
                      f"This is the fastest way to free up money for your goals."
        })

    return alerts


# ─── AFFORDABILITY CHECK ─────────────────────────────────────

def can_i_afford(plan, expense_name, amount, target_month=None):
    if "error" in plan:
        return {"affordable": False, "reason": plan["error"]}

    lifestyle_pot = next((p for p in plan["pots"] if p["type"] == "lifestyle"), None)
    if not lifestyle_pot:
        return {"affordable": False, "reason": "No lifestyle allocation in plan"}

    monthly_lifestyle = lifestyle_pot["monthly_amount"]

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
            "message": f"The {expense_name} (£{amount:,.0f}) exceeds your lifestyle pot "
                      f"(£{lifestyle_balance:,.0f}). You'd need to pause a goal contribution "
                      f"for a month to cover the difference.",
            "impact": "significant"
        }


# ─── REPLAN ON LIFE EVENTS ───────────────────────────────────

def replan_with_change(user_profile, goals, change_type, change_data, debts=None):
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


# ─── PLAN SUMMARY ────────────────────────────────────────────

def get_plan_summary(plan):
    if "error" in plan:
        return plan["error"]

    phases = plan.get("phases", [])
    pots = plan.get("pots", [])
    if not phases:
        return "Your financial plan is being calculated."

    # Find all active funded pots (not lifestyle/buffer)
    active_pots = [p for p in pots if p.get("monthly_amount", 0) > 0
                   and p["type"] not in ("lifestyle", "buffer")
                   and not p.get("completed")]

    if not active_pots:
        return "All your goals are on track. Your surplus is free."

    # Find the pot closest to completion
    completing_soon = None
    for pot in active_pots:
        months = pot.get("months_to_target")
        if months and months > 0:
            if not completing_soon or months < completing_soon.get("months_to_target", 999):
                completing_soon = pot

    # Find the next pot that would benefit from the redirect
    if completing_soon:
        remaining_pots = [p for p in active_pots
                          if p.get("goal_id") != completing_soon.get("goal_id")
                          and p.get("name") != completing_soon.get("name")]

        # Sort by: deadline urgency first, then largest remaining amount
        remaining_pots.sort(key=lambda p: (
            p.get("months_until_deadline") or 999,
            -(p.get("target", 0) - p.get("current", 0))
        ))

        next_pot = remaining_pots[0] if remaining_pots else None
        soon_name = completing_soon["name"]
        soon_months = completing_soon.get("months_to_target", 0)
        soon_amount = completing_soon.get("monthly_amount", 0)

        if next_pot:
            next_name = next_pot["name"]
            return (
                f"Your {soon_name} is closest to completion (~{soon_months} months). "
                f"Once done, that £{soon_amount:,.0f}/month redirects to your {next_name}, "
                f"accelerating it automatically."
            )
        else:
            return (
                f"Your {soon_name} completes in ~{soon_months} months. "
                f"After that, your £{soon_amount:,.0f}/month surplus frees up entirely."
            )

    # Fallback: underfunded goals warning
    underfunded = []
    for pot in pots:
        if (pot.get("months_to_target") and pot.get("months_until_deadline")
                and pot["months_to_target"] > pot["months_until_deadline"]
                and not pot.get("completed")):
            underfunded.append({
                "name": pot["name"],
                "months_needed": pot["months_to_target"],
                "months_available": pot["months_until_deadline"]
            })

    if underfunded:
        most_urgent = min(underfunded, key=lambda u: u["months_available"])
        if len(underfunded) == 1:
            return (
                f"Your {most_urgent['name']} is tight. At current pace it needs "
                f"{most_urgent['months_needed']} months but the deadline is in "
                f"{most_urgent['months_available']}. Consider adjusting the target or timeline."
            )
        else:
            names = " and ".join(u["name"] for u in underfunded)
            return (
                f"{len(underfunded)} goals are tight for their deadlines: {names}. "
                f"The most urgent is {most_urgent['name']}: needs "
                f"{most_urgent['months_needed']} months but deadline is in "
                f"{most_urgent['months_available']}."
            )

    # Default: healthy plan
    return "Your plan is on track. Every goal is funded and progressing."

# ─── HELPERS ─────────────────────────────────────────────────

def _pot_to_dict(pot):
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

    if pot["target"] and pot["monthly_amount"] > 0 and not pot.get("completed"):
        remaining = pot["target"] - pot["current"]
        if remaining > 0:
            result["months_to_target"] = math.ceil(remaining / pot["monthly_amount"])

    return result