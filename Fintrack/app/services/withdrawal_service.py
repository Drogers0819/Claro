"""
Claro Withdrawal Intelligence Service

Determines the optimal withdrawal strategy when a user needs money,
minimising damage to their financial plan.

Principle: Protect deadline goals, absorb from flexible pots first.
"""

import math


# Withdrawal priority order (lower = pull from first)
WITHDRAWAL_PRIORITY = {
    "buffer": 1,        # Built for this — no timeline impact
    "lifestyle": 2,     # Reduces fun money, replenishes next month
    "savings": 3,       # General savings — ranked by timeline flexibility
    "emergency": 4,     # Only if user opted in and has surplus
    "debt": 99,         # Never touch — interest compounds
    "must_hit": 99,     # Never touch — user marked as non-negotiable
}


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

    # Build withdrawal candidates
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

        # Determine available balance for withdrawal
        if pot_type == "buffer":
            available = monthly  # This month's buffer allocation
            priority = WITHDRAWAL_PRIORITY["buffer"]
            impact_per_pound = 0  # No lasting impact
        elif pot_type == "lifestyle":
            available = monthly  # This month's lifestyle allocation
            priority = WITHDRAWAL_PRIORITY["lifestyle"]
            impact_per_pound = 0.1  # Minor — replenishes next month
        elif "(must-hit)" in name.lower() or pot.get("_stage") == "must_hit":
            continue  # Never touch must-hit goals
        elif pot_type == "debt" or "pay off" in name.lower() or "credit" in name.lower():
            continue  # Never touch debt payments
        else:
            # Regular savings goal — available is current balance
            available = current
            priority = WITHDRAWAL_PRIORITY.get(pot_type, 3)

            # Calculate impact: how much does pulling money extend the timeline?
            if months_until_deadline and months_until_deadline > 0:
                # Deadline goals: tighter deadline = higher cost to withdraw
                urgency = 12 / max(months_until_deadline, 1)
                impact_per_pound = urgency
            elif months_to_target and months_to_target > 0:
                # No deadline: longer timeline = safer to withdraw from
                impact_per_pound = 1 / max(months_to_target, 1)
            else:
                impact_per_pound = 0.5

        if available <= 0:
            continue

        candidates.append({
            "name": name,
            "type": pot_type,
            "available": round(available, 2),
            "priority": priority,
            "impact_per_pound": impact_per_pound,
            "monthly_amount": monthly,
            "current": current,
            "target": target,
            "months_to_target": months_to_target,
            "months_until_deadline": months_until_deadline
        })

    # Sort by priority first, then by impact (lowest damage first)
    candidates.sort(key=lambda c: (c["priority"], c["impact_per_pound"]))

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
            f"There's a £{shortfall:,.0f} shortfall — you may need to adjust a goal target or timeline."
        )
    elif len(withdrawals) == 1 and withdrawals[0]["pot_type"] == "buffer":
        summary = (
            f"Good news — your buffer covers this entirely. "
            f"No impact on any of your goals. The buffer replenishes next month."
        )
    else:
        affected_goals = [w["pot_name"] for w in withdrawals
                          if w["pot_type"] not in ("buffer", "lifestyle")]
        if affected_goals:
            names = " and ".join(affected_goals)
            summary = (
                f"This withdrawal is spread across {len(withdrawals)} pots to minimise impact. "
                f"Your {names} timeline{'s' if len(affected_goals) > 1 else ''} will extend slightly. "
                f"The plan recalculates automatically at your next check-in."
            )
        else:
            summary = (
                f"Covered from your buffer and lifestyle pots. "
                f"No impact on your goal timelines."
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

    if pot_type == "buffer":
        return "No impact — your buffer is designed for this. It replenishes next month."

    if pot_type == "lifestyle":
        remaining = candidate["monthly_amount"] - amount
        if remaining <= 0:
            return "Your lifestyle budget is fully used this month. It resets next month."
        return f"You'll have £{remaining:,.0f} left for lifestyle spending this month."

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
            return f"Minimal impact — your {name} timeline stays roughly the same."
        elif added == 1:
            return f"Your {name} extends by about 1 month."
        else:
            return f"Your {name} extends by about {added} months."

    return f"£{amount:,.0f} withdrawn from {name}."


def _severity(candidate, amount):
    """Return impact severity: low, medium, high."""
    pot_type = candidate["type"]

    if pot_type in ("buffer", "lifestyle"):
        return "low"

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