"""
Claro Action Whisper Service

Zero API cost. Generates one actionable prompt per page load
based on the user's stage in their journey.

Priority order:
1. Post-onboarding standing order setup (days 1-7)
2. Pay day prompts
3. Pre-check-in nudge
4. Goal milestones
5. Life check-in prompt (mid-month)
6. General plan status
"""

from datetime import date, datetime
from dateutil.relativedelta import relativedelta


def generate_action_whisper(user, plan, goals):
    """
    Generate a single action whisper for the overview page.

    Args:
        user: User model instance
        plan: Plan dict from generate_financial_plan() or None
        goals: List of goal dicts

    Returns:
        dict with: message, action_label, action_url, icon, type
        or None if no whisper is appropriate
    """
    if not user.factfind_completed or not plan or "error" in plan:
        return None

    today = date.today()
    pots = plan.get("pots", [])
    active_pots = [p for p in pots if not p.get("completed") and p.get("monthly_amount", 0) > 0
                   and p.get("type") not in ("lifestyle", "buffer")]

    # Calculate days since signup
    days_since_signup = 0
    if user.created_at:
        days_since_signup = (today - user.created_at.date()).days

    # Check each whisper type in priority order
    whisper = None

    # 1. Post-onboarding: standing order setup (first 7 days)
    whisper = _standing_order_whisper(user, pots, active_pots, days_since_signup)
    if whisper:
        return whisper

    # 2. Pay day prompt
    whisper = _payday_whisper(user, plan, pots, today)
    if whisper:
        return whisper

    # 3. Pre-check-in nudge (2 days before month end)
    whisper = _checkin_whisper(today)
    if whisper:
        return whisper

    # 4. Goal milestones (50%, 75%, completed)
    whisper = _milestone_whisper(pots, plan)
    if whisper:
        return whisper

    # 5. Life check-in (mid-month, around 14th-16th)
    whisper = _life_checkin_whisper(today, days_since_signup)
    if whisper:
        return whisper

    # 6. Claro directed £X counter
    whisper = _directed_counter_whisper(user, plan)
    if whisper:
        return whisper

    # 7. Default: plan status
    whisper = _default_whisper(plan, active_pots)
    if whisper:
        return whisper

    return None


# ─── WHISPER GENERATORS ───────────────────────────────────

def _standing_order_whisper(user, pots, active_pots, days_since_signup):
    """Days 1-7: Prompt user to set up standing orders for each pot."""
    if days_since_signup > 7 or not active_pots:
        return None

    income_day = user.income_day or 25
    pay_suffix = _ordinal(income_day)

    if days_since_signup <= 1:
        # Day 0-1: First standing order
        pot = active_pots[0]
        return {
            "message": f"First step: open your banking app and set up a standing order for £{pot['monthly_amount']:,.0f}/month to a \"{pot['name']}\" pot. Set it for the {pay_suffix} — the day after your pay lands.",
            "action_label": "I've done this",
            "action_url": None,
            "icon": "🏦",
            "type": "setup"
        }

    elif days_since_signup <= 3 and len(active_pots) > 1:
        # Day 2-3: Second standing order
        pot = active_pots[1]
        return {
            "message": f"Next: set up £{pot['monthly_amount']:,.0f}/month to your \"{pot['name']}\" pot. Two standing orders and your plan is running on autopilot.",
            "action_label": "Done",
            "action_url": None,
            "icon": "✅",
            "type": "setup"
        }

    elif days_since_signup <= 5:
        # Day 4-5: Confirm setup
        return {
            "message": "Check your bank app — have your standing orders gone through? Once they're running, your plan executes itself every month.",
            "action_label": None,
            "action_url": None,
            "icon": "🔍",
            "type": "setup"
        }

    elif days_since_signup <= 7:
        # Day 6-7: All set message
        total_allocated = sum(p["monthly_amount"] for p in pots)
        return {
            "message": f"You're all set. £{total_allocated:,.0f}/month is now directed across your goals. Your next check-in will be at the end of the month.",
            "action_label": "View my plan",
            "action_url": "/plan",
            "icon": "🎯",
            "type": "setup_complete"
        }

    return None


def _payday_whisper(user, plan, pots, today):
    """Show allocation breakdown on pay day."""
    income_day = user.income_day or 25

    # Show on pay day and day after
    if today.day not in (income_day, income_day + 1 if income_day < 28 else income_day):
        return None

    surplus = plan.get("surplus", 0)
    funded_pots = [p for p in pots if p.get("monthly_amount", 0) > 0
                   and not p.get("completed")
                   and p.get("type") not in ("lifestyle", "buffer")]

    if not funded_pots:
        return None

    # Build allocation list
    allocations = []
    for pot in funded_pots[:3]:  # Show top 3
        allocations.append(f"£{pot['monthly_amount']:,.0f} → {pot['name']}")

    alloc_text = ", ".join(allocations)
    if len(funded_pots) > 3:
        alloc_text += f" + {len(funded_pots) - 3} more"

    return {
        "message": f"It's pay day. Here's where your £{surplus:,.0f} surplus goes: {alloc_text}.",
        "action_label": "View full plan",
        "action_url": "/plan",
        "icon": "💰",
        "type": "payday"
    }


def _checkin_whisper(today):
    """Nudge 2-3 days before month end."""
    import calendar
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_left = days_in_month - today.day

    if days_left > 3 or days_left < 0:
        return None

    if days_left == 0:
        return {
            "message": "It's the last day of the month. Time for your monthly check-in — how much did you actually put toward each goal?",
            "action_label": "Start check-in",
            "action_url": "/check-in",
            "icon": "📋",
            "type": "checkin"
        }
    else:
        return {
            "message": f"Your monthly check-in is due in {days_left} day{'s' if days_left > 1 else ''}. Have your bank app handy — it takes 2 minutes.",
            "action_label": "Do it now",
            "action_url": "/check-in",
            "icon": "📋",
            "type": "checkin"
        }


def _milestone_whisper(pots, plan):
    """Celebrate goal milestones."""
    for pot in pots:
        if pot.get("completed"):
            continue

        target = pot.get("target", 0)
        current = pot.get("current", 0)
        name = pot.get("name", "")
        pot_type = pot.get("type", "")

        if pot_type in ("lifestyle", "buffer") or target <= 0:
            continue

        progress = current / target

        if progress >= 1.0:
            # Goal just completed — find where money redirects
            next_pot = _find_next_pot(pots, pot)
            redirect_msg = ""
            if next_pot:
                redirect_msg = f" That £{pot.get('monthly_amount', 0):,.0f}/month now redirects to your {next_pot['name']}."

            return {
                "message": f"You did it! {name} is fully funded.{redirect_msg}",
                "action_label": "View goals",
                "action_url": "/my-goals",
                "icon": "🎉",
                "type": "milestone"
            }

        elif progress >= 0.75:
            months = pot.get("months_to_target")
            time_msg = f" ~{months} months to go." if months else ""
            return {
                "message": f"Your {name} is 75% funded — £{current:,.0f} of £{target:,.0f}.{time_msg} You're in the home stretch.",
                "action_label": None,
                "action_url": None,
                "icon": "🔥",
                "type": "milestone"
            }

        elif progress >= 0.5:
            months = pot.get("months_to_target")
            time_msg = f" At this pace, it completes in ~{months} months." if months else ""
            return {
                "message": f"Halfway there! Your {name} is 50% funded — £{current:,.0f} of £{target:,.0f}.{time_msg}",
                "action_label": None,
                "action_url": None,
                "icon": "⭐",
                "type": "milestone"
            }

    return None


def _life_checkin_whisper(today, days_since_signup):
    """Mid-month life check-in prompt."""
    if days_since_signup < 14:  # Don't show in first 2 weeks
        return None

    if 13 <= today.day <= 16:
        return {
            "message": "Anything come up this month we should know about? A birthday, an unexpected bill, or a change at work? Quick updates keep your plan accurate.",
            "action_label": "Something changed",
            "action_url": "/check-in",
            "icon": "💬",
            "type": "life_checkin"
        }

    return None


def _directed_counter_whisper(user, plan):
    """Show total allocated since signup."""
    if not user.created_at:
        return None

    today = date.today()
    months_active = max(1, (today.year - user.created_at.year) * 12 + today.month - user.created_at.month)

    if months_active < 2:
        return None

    surplus = plan.get("surplus", 0)
    total_directed = round(surplus * months_active, 0)

    if total_directed <= 0:
        return None

    return {
        "message": f"Following your plan has directed £{total_directed:,.0f} toward your goals over {months_active} months. That's £{surplus:,.0f}/month working for your future.",
        "action_label": None,
        "action_url": None,
        "icon": "📈",
        "type": "counter"
    }


def _default_whisper(plan, active_pots):
    """Default: show closest-to-completion goal."""
    if not active_pots:
        return None

    # Find pot closest to completion
    closest = None
    closest_pct = 0

    for pot in active_pots:
        target = pot.get("target", 0)
        current = pot.get("current", 0)
        if target > 0:
            pct = current / target
            if pct > closest_pct and pct < 1.0:
                closest = pot
                closest_pct = pct

    if closest:
        months = closest.get("months_to_target")
        time_msg = f" ~{months} months to go." if months else ""
        return {
            "message": f"Your {closest['name']} is {closest_pct:.0%} funded.{time_msg} Your plan is working.",
            "action_label": "View plan",
            "action_url": "/plan",
            "icon": "📊",
            "type": "status"
        }

    # No progress yet — encourage
    total = sum(p["monthly_amount"] for p in active_pots)
    return {
        "message": f"Your plan directs £{total:,.0f}/month across {len(active_pots)} goals. Set up your standing orders and it runs on autopilot.",
        "action_label": "View plan",
        "action_url": "/plan",
        "icon": "🎯",
        "type": "status"
    }


# ─── HELPERS ──────────────────────────────────────────────

def _find_next_pot(pots, completed_pot):
    """Find the next pot that would receive money after a pot completes."""
    active = [p for p in pots if not p.get("completed")
              and p.get("monthly_amount", 0) > 0
              and p.get("type") not in ("lifestyle", "buffer")
              and p.get("name") != completed_pot.get("name")]
    return active[0] if active else None


def _ordinal(n):
    """Return ordinal string for a number: 1st, 2nd, 3rd, etc."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"