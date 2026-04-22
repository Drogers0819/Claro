"""
Claro Withdrawal Intelligence Service

Determines the optimal withdrawal strategy when a user needs money,
minimising damage to their financial plan.

Principle: Protect deadline goals, absorb from flexible pots first.
"""

import math


# Withdrawal priority: only from goal pots, ranked by least damage
# Lifestyle and buffer are NEVER touched — user already budgeted their spending
# Debt is NEVER touched — interest compounds
# Must-hit goals are NEVER touched — user marked as non-negotiable


def calculate_withdrawal_strategy(pots, amount_needed, user_goals=None):
    """
    Given the current plan pots and an amount needed, calculate the
    optimal withdrawal strategy that does the least damage.

    Args:
        pots: List of pot dicts from generate_financial_plan()
        amount_needed: Float, how much the user needs
        user_goals: Optional list of goal dicts for additional context

    Returns:
        dict with:
            - withdrawals: list of {pot_name, amount, impact_description}
            - total_covered: float
            - shortfall: float (if plan can't cover the full amount)
            - plan_impact_summary: string describing overall impact
    """
    if amount_needed <= 0:
        return {
            "withdrawals": [],
            "total_covered": 0,
            "shortfall": 0,
            "plan_impact_summary": "No withdrawal needed."
        }

    # Build withdrawal candidates — ONLY from goal pots
    # Never touch: lifestyle, buffer, debt, must-hit goals
    candidates = []
    for pot in pots:
        name = pot.get("name", "")
        pot_type = pot.get("type", "savings")
        current = float(pot.get("current", 0))
        monthly = float(pot.get("monthly_amount", 0))
        target = float(pot.get("target") or 0)
        months_to_target = pot.get("months_to_target")
        deadline = pot.get("deadline")
        months_until_deadline = pot.get("months_until_deadline")

        # Skip completed pots
        if pot.get("completed"):
            continue

        # Never touch lifestyle or buffer — user already budgeted their spending
        if pot_type in ("lifestyle", "buffer"):
            continue

        # Never touch must-hit goals
        if "(must-hit)" in name.lower() or pot.get("_stage") == "must_hit":
            continue

        # Never touch debt payments — interest compounds
        if pot_type == "debt" or "pay off" in name.lower() or "credit" in name.lower():
            continue

        # Only withdraw from pots that have a current balance
        available = current
        if available <= 0:
            continue

        # Calculate impact: how much damage does pulling from this pot cause?
        if months_until_deadline and months_until_deadline > 0:
            # Deadline goals: tighter deadline = more damage
            # A goal due in 3 months is 4× more costly to withdraw from than one due in 12
            impact_per_pound = 12 / max(months_until_deadline, 1)
        elif months_to_target and months_to_target > 0:
            # No deadline: longer timeline = safer to withdraw from
            # A goal taking 24 months barely notices, one taking 3 months does
            impact_per_pound = 1 / max(months_to_target, 1)
        else:
            impact_per_pound = 0.5

        candidates.append({
            "name": name,
            "type": pot_type,
            "available": round(available, 2),
            "priority": 1,  # All goal pots have equal base priority
            "impact_per_pound": impact_per_pound,
            "monthly_amount": monthly,
            "current": current,
            "target": target,
            "months_to_target": months_to_target,
            "months_until_deadline": months_until_deadline
        })

    # Sort by impact — least damaging first (furthest from deadline, longest timeline)
    candidates.sort(key=lambda c: c["impact_per_pound"])

    # Allocate withdrawal across candidates
    remaining = amount_needed
    withdrawals = []

    for candidate in candidates:
        if remaining <= 0:
            break

        pull = min(remaining, candidate["available"])
        if pull <= 0:
            continue

        # Calculate impact description
        impact = _describe_impact(candidate, pull)

        withdrawals.append({
            "pot_name": candidate["name"],
            "pot_type": candidate["type"],
            "amount": round(pull, 2),
            "impact": impact,
            "impact_severity": _severity(candidate, pull)
        })

        remaining -= pull

    total_covered = round(amount_needed - remaining, 2)
    shortfall = round(max(remaining, 0), 2)

    # Build summary
    if shortfall > 0:
        summary = (
            f"Your plan can cover £{total_covered:,.0f} of the £{amount_needed:,.0f} needed. "
            f"There's a £{shortfall:,.0f} shortfall. You may need to adjust a goal target or timeline."
        )
    else:
        if len(withdrawals) == 1:
            name = withdrawals[0]["pot_name"]
            summary = (
                f"Pulling £{amount_needed:,.0f} from your {name} is the least damaging option. "
                f"Your other goals are untouched."
            )
        else:
            names = [w["pot_name"] for w in withdrawals]
            summary = (
                f"This withdrawal is spread across {len(withdrawals)} goals to minimise impact: "
                f"{', '.join(names[:-1])} and {names[-1]}. "
                f"The plan recalculates automatically at your next check-in."
            )

    return {
        "withdrawals": withdrawals,
        "total_covered": total_covered,
        "shortfall": shortfall,
        "plan_impact_summary": summary
    }


def _describe_impact(candidate, amount):
    """Generate a human-readable impact description for a withdrawal."""
    name = candidate["name"]
    pot_type = candidate["type"]

    # Savings goal
    current_after = candidate["current"] - amount
    if current_after < 0:
        current_after = 0

    monthly = candidate["monthly_amount"]
    target = candidate["target"]

    if monthly > 0 and target > 0:
        remaining_after = target - current_after
        if remaining_after <= 0:
            return f"Still fully funded even after this withdrawal."

        new_months = math.ceil(remaining_after / monthly)
        old_months = candidate.get("months_to_target", new_months)
        added = new_months - (old_months or new_months)

        if added <= 0:
            return f"Minimal impact. Your {name} timeline stays roughly the same."
        elif added == 1:
            return f"Your {name} extends by about 1 month."
        else:
            return f"Your {name} extends by about {added} months."

    return f"£{amount:,.0f} withdrawn from {name}."


def _severity(candidate, amount):
    """Return impact severity: low, medium, high."""
    pot_type = candidate["type"]


    # Check if this significantly impacts a deadline goal
    months_until = candidate.get("months_until_deadline")
    if months_until and months_until <= 6:
        return "high"

    # Check if withdrawal is >50% of current balance
    current = candidate.get("current", 0)
    if current > 0 and amount / current > 0.5:
        return "medium"

    return "low"


def get_withdrawal_options(plan, amount_needed):
    """
    Convenience function that takes a full plan dict and returns withdrawal options.

    Args:
        plan: The plan dict from generate_financial_plan()
        amount_needed: How much the user needs

    Returns:
        Withdrawal strategy dict
    """
    if "error" in plan:
        return {
            "withdrawals": [],
            "total_covered": 0,
            "shortfall": amount_needed,
            "plan_impact_summary": "No active plan to withdraw from."
        }

    pots = plan.get("pots", [])
    return calculate_withdrawal_strategy(pots, amount_needed)