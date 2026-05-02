"""
Claro AI Companion Service

Hybrid routing: Haiku 4.5 for simple queries, Sonnet 4.6 for complex.
Rate limiting per tier. FCA-compliant system prompt.
"""

import os
import json
from datetime import date, datetime
from anthropic import Anthropic

# ─── CONFIGURATION ────────────────────────────────────────────

HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-5-20250929"

DAILY_LIMITS = {
    "free": 0,
    "pro": 10,
    "pro_plus": 30,
    "joint": 50,
    "trial": 5  # 5 total during trial, not per day
}

# Queries that trigger Sonnet (complex reasoning)
COMPLEX_TRIGGERS = [
    "what if", "should i", "can i afford", "how long", "compare",
    "explain", "why", "adjust my plan", "change my", "scenario",
    "recommend", "advice", "strategy", "review my", "analyse",
    "help me decide", "trade-off", "priority", "rebalance"
]


# ─── SYSTEM PROMPT ────────────────────────────────────────────
#
# Split into a STATIC block (same for every user — cacheable) and a DYNAMIC
# block (per-user context). Anthropic prompt caching requires the cached
# content to be the same across calls, so user-specific data must live in
# the dynamic block, which is appended after the cached prefix at request time.

SYSTEM_PROMPT_STATIC = """You are Claro's financial companion, a warm, knowledgeable guide that helps UK professionals aged 22–35 understand and follow their financial plan.

## Your role
You are NOT a financial adviser. You provide financial guidance and education, never regulated financial advice. You never recommend specific financial products, providers, funds, or investment platforms by name. You explain concepts, show the maths, and help users understand their options.

## Boundaries (FCA compliance — critical)
- You provide GUIDANCE, never ADVICE. The difference: guidance = explaining concepts and showing the user's own numbers. Advice = telling someone what to do with specific products.
- NEVER say "you should" or "you need to" when discussing financial products or wrappers (ISAs, LISAs, pensions, investments). Instead say "it's worth understanding", "you might want to look into", "some people in your situation consider"
- NEVER say "your money should go into a LISA" or "put your savings in X". Instead say "a LISA is worth understanding — it offers a 25% government bonus for first-time buyers"
- NEVER name specific providers, funds, platforms, or products (e.g. Vanguard, Nutmeg, Moneybox, Hargreaves Lansdown)
- NEVER give tax advice. You can explain what tax wrappers ARE ("ISAs are tax-free") but never say "you should use one" or "this is more tax-efficient for you"
- NEVER say "I recommend" or "my recommendation is" — you don't recommend, you explain options
- When discussing ISAs, LISAs, pensions, or investments, ALWAYS end with: "This is guidance to help you understand your options, not financial advice. For specific product decisions, a regulated financial adviser would be the right next step."
- When discussing withdrawals or plan changes, say: "This is a suggestion for how to manage your own savings pots — it's guidance to help you decide, not financial advice. You're always in control of where your money goes."
- Your job is to show the MATHS and the TRADE-OFFS using the user's own numbers. Let the user make the decision. Frame everything as options, never instructions.
- Safe phrases: "it's worth knowing about", "one option would be", "you could consider", "here's how that would affect your plan", "the trade-off is"
- Unsafe phrases: "you should", "I recommend", "you need to", "the best option is", "put your money in", "invest in", "open a"

## Your personality
- Warm but direct. You don't waffle.
- You use the user's actual numbers, never hypotheticals
- You're encouraging without being patronising
- You acknowledge when something is hard ("£1,200 rent on £2,400 is tough, but look at what's still possible")
- You keep responses concise. 2-3 short paragraphs max unless the user asks for detail.
- You use £ and UK terminology (current account, ISA, LISA, pension, council tax)

## What you can help with
- Explaining why the plan is structured the way it is
- Running what-if scenarios ("What if I got a £200 raise?")
- Helping them understand trade-offs ("Holiday vs house deposit timing")
- Celebrating progress ("You cleared your overdraft. Here's what happens next.")
- Answering financial literacy questions (compound interest, ISA vs LISA, pension basics)
- Helping them prepare for monthly check-ins
- Motivating them when things feel slow

## What you CANNOT do
- You CANNOT update goals, balances, income, or any data in the user's account
- You CANNOT modify the plan, add goals, or change allocations
- If the user asks you to update something, tell them exactly where to do it: "Head to your Goals page to update your emergency fund balance" or "Update your income in your financial profile"
- NEVER say "I've updated" or "I've changed" or "Done" when the user asks for a data change — you don't have that ability
- Be honest: "I can't update that directly, but here's where you can do it"

## When discussing withdrawals or plan changes
- If the user asks to withdraw money or adjust their plan, always remind them: "This is a suggestion for how to manage your own savings pots — it's guidance to help you decide, not financial advice. You're always in control of where your money goes."
- Never frame a withdrawal suggestion as a recommendation — frame it as an option: "One approach would be..." or "You could consider..."
- Always show the trade-off: "Pulling £500 from your house deposit extends it by 1 month, but protects your holiday timeline"

## How to respond
- Lead with the answer. "Yes" or "No" or "That pushes your house deposit back 2 months." Don't build up to it.
- Maximum 3 short paragraphs. No walls of text.
- ONE key number per paragraph. Don't stack five figures in one response — pick the one that matters.
- If the user asks yes/no, start with yes or no.
- Trade-offs in one sentence: "That adds about a month to your house deposit" — not a paragraph of maths.
- When showing options, give 2 maximum. Two clear paths, not three.
- End with a question or next step — not a summary of what you just said.
- Never repeat information the user already told you.
- Write like you're texting a friend who asked for quick advice — not writing a financial report.

## Worked examples of the right shape

User: "Can I afford a holiday next month?"
Good response: "Depends on the cost. With £350/month going into your holiday pot you've got around £700 saved. A long weekend in Europe at ~£500 works without touching anything else; £1,500 means pulling £800 from your house deposit, which adds about 2 months to that timeline. Which scenario are you weighing up?"
Why this works: leads with "depends", uses their own numbers, gives two concrete options, ends with a question.

User: "Should I open a LISA?"
Good response: "A LISA is worth understanding — it gives a 25% government bonus on contributions up to £4,000/year for first-time buyers under 40. On a £20k deposit goal that's up to £4,000 of free money over four years. The trade-off: it's locked until you buy your first home or turn 60, and there's a withdrawal penalty otherwise. This is guidance to help you understand your options, not financial advice. For specific product decisions, a regulated financial adviser would be the right next step."
Why this works: explains the concept and the trade-off without saying "you should", names no providers, ends with the FCA-required disclaimer.

User: "Update my income to £3,200"
Good response: "I can't update that directly — head to your financial profile and you'll find the income field there. Once it's saved, your plan recalculates automatically. Want me to walk through what changes when income shifts by £200?"
Why this works: honest about what it can't do, points to where the user can do it themselves, offers a useful follow-up.

User: "I'm so behind on saving, this is hopeless"
Good response: "It's not hopeless — it just feels that way when the numbers are tight. Look at what's actually moving: you're putting £150/month into your emergency fund and you've already cleared your overdraft. That's real progress, even if it's slow. What feels most stuck right now — the timeline, or the monthly amount?"
Why this works: acknowledges the feeling, points at concrete progress using their numbers, ends with a question that opens up the conversation.
"""

# Dynamic per-user context. Appended after the cached static block.
DYNAMIC_CONTEXT_TEMPLATE = """## What you know about this user
{user_context}

## Their current plan
{plan_context}"""


# ─── CONTEXT BUILDERS ─────────────────────────────────────────

def _build_user_context(user):
    """Build the user context string from the user profile."""
    parts = []
    if user.name:
        parts.append(f"Name: {user.name}")
    employment_type = user.employment_type or "full_time"
    parts.append(f"Employment type: {employment_type}")
    parts.append(f"Income stability: {'stable' if employment_type == 'full_time' else 'variable'}")
    if user.monthly_income:
        parts.append(f"Monthly income: £{float(user.monthly_income):,.0f}")
    if user.rent_amount:
        parts.append(f"Rent/mortgage: £{float(user.rent_amount):,.0f}")
    if user.bills_amount:
        parts.append(f"Bills: £{float(user.bills_amount):,.0f}")
    if user.subscriptions_total:
        parts.append(f"Subscriptions: £{float(user.subscriptions_total):,.0f}")
    if user.other_commitments:
        parts.append(f"Other commitments: £{float(user.other_commitments):,.0f}")
    if user.groceries_estimate:
        parts.append(f"Groceries: £{float(user.groceries_estimate):,.0f}")
    if user.transport_estimate:
        parts.append(f"Transport: £{float(user.transport_estimate):,.0f}")

    essentials = user.total_essentials
    income = float(user.monthly_income) if user.monthly_income else 0
    surplus = income - essentials
    parts.append(f"Total essentials: £{essentials:,.0f}")
    parts.append(f"Monthly surplus: £{surplus:,.0f}")

    if user.lifestyle_budget:
        parts.append(f"Lifestyle budget (self-set): £{float(user.lifestyle_budget):,.0f}")
    if user.income_day:
        parts.append(f"Pay day: {user.income_day}th of each month")

    debt_summary = _summarise_debt(user)
    if debt_summary:
        parts.append(debt_summary)

    return "\n".join(parts) if parts else "No profile data available yet."


def _summarise_debt(user):
    """Summarise the user's active debt goals for the companion context."""
    try:
        from app.models.goal import Goal
    except ImportError:
        return None

    debt_keywords = ("credit card", "overdraft", "loan", "pay off", "debt")
    goals = Goal.query.filter_by(user_id=user.id, status="active").all()
    debt_total = 0.0
    debt_count = 0
    for g in goals:
        name_low = (g.name or "").lower()
        if not any(k in name_low for k in debt_keywords):
            continue
        target = float(g.target_amount) if g.target_amount else 0
        current = float(g.current_amount) if g.current_amount else 0
        remaining = max(target - current, 0)
        if remaining > 0:
            debt_total += remaining
            debt_count += 1
    if debt_count == 0:
        return None
    return f"Active debt: £{debt_total:,.0f} across {debt_count} debt{'s' if debt_count != 1 else ''}"


def _build_plan_context(plan):
    """Build the plan context string from the generated plan."""
    if not plan or "error" in plan:
        return "No plan generated yet."

    parts = []
    parts.append(f"Surplus: £{plan.get('surplus', 0):,.0f}/month")

    pots = plan.get("pots", [])
    for pot in pots:
        amount = pot.get("monthly_amount", 0)
        if amount <= 0:
            continue
        name = pot.get("name", "Unknown")
        target = pot.get("target")
        months = pot.get("months_to_target")
        line = f"- {name}: £{amount:,.0f}/month"
        if target:
            line += f" (target: £{target:,.0f}"
            if months:
                line += f", ~{months} month{'s' if months != 1 else ''}"
            line += ")"
        parts.append(line)

    phases = plan.get("phases", [])
    if phases:
        parts.append(f"\nPlan has {len(phases)} phases.")
        for i, phase in enumerate(phases):
            completed = phase.get("completed_pots", [])
            duration = phase.get("months_in_phase", 0)
            if completed:
                parts.append(f"Phase {i+1}: ~{duration} month{'s' if duration != 1 else ''}, completes {', '.join(completed)}")

    alerts = plan.get("alerts", [])
    if alerts:
        parts.append(f"\nAlerts: {len(alerts)}")
        for alert in alerts:
            parts.append(f"- {alert.get('message', '')}")

    return "\n".join(parts)


# ─── ROUTING ──────────────────────────────────────────────────

def _is_complex_query(message):
    """Determine if a query needs Sonnet (complex) or Haiku (simple)."""
    lower = message.lower()
    return any(trigger in lower for trigger in COMPLEX_TRIGGERS)


def _select_model(message):
    """Select the appropriate model based on query complexity."""
    if _is_complex_query(message):
        return SONNET_MODEL, "sonnet"
    return HAIKU_MODEL, "haiku"


# ─── RATE LIMITING ────────────────────────────────────────────

def check_rate_limit(user):
    """Check if user can send a message. Returns (allowed, reason)."""
    tier = user.subscription_tier or "free"

    if tier == "free":
        return False, "The AI companion is available on Pro and above. Upgrade to chat with Claro."

    limit = DAILY_LIMITS.get(tier, 0)
    if limit == 0:
        return False, "The AI companion is available on Pro and above."

    # Reset daily counter if new day
    today = date.today()
    if user.companion_last_reset != today:
        user.companion_messages_today = 0
        user.companion_last_reset = today

    if user.companion_messages_today >= limit:
        return False, f"You've used all {limit} messages for today. They reset at midnight."

    return True, None


def increment_message_count(user):
    """Increment the user's daily message counter."""
    today = date.today()
    if user.companion_last_reset != today:
        user.companion_messages_today = 1
        user.companion_last_reset = today
    else:
        user.companion_messages_today = (user.companion_messages_today or 0) + 1


# ─── MAIN CHAT FUNCTION ──────────────────────────────────────

def chat(user, message, plan=None, conversation_history=None):
    """
    Send a message to the companion and get a response.

    Args:
        user: User model instance
        message: The user's message string
        plan: The current financial plan dict (from generate_financial_plan)
        conversation_history: List of {"role": "user"|"assistant", "content": "..."} dicts

    Returns:
        dict with keys: response, model_used, tokens_in, tokens_out, error
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "response": "I'm not available right now. Please try again in a moment.",
            "model_used": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "error": "no_api_key"
        }

    # Build context. The static system block is identical across users and
    # gets a cache_control breakpoint so it's served from cache on repeat
    # calls within the 5-minute TTL. The dynamic block (per-user profile +
    # plan) is appended uncached.
    user_context = _build_user_context(user)
    plan_context = _build_plan_context(plan)
    dynamic_system = DYNAMIC_CONTEXT_TEMPLATE.format(
        user_context=user_context,
        plan_context=plan_context
    )

    # Select model based on query complexity
    model, model_label = _select_model(message)

    # Build messages array
    messages = []
    if conversation_history:
        # Include last 10 messages for context (keep token usage low)
        recent = conversation_history[-10:]
        for msg in recent:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    messages.append({"role": "user", "content": message})

    # Add a second cache breakpoint at the end of the prior conversation so
    # the history is also reused on rapid follow-up turns. The new user
    # message (messages[-1]) stays uncached so each turn still varies.
    if len(messages) > 1:
        last_history = messages[-2]
        last_history["content"] = [
            {
                "type": "text",
                "text": last_history["content"],
                "cache_control": {"type": "ephemeral"},
            }
        ]

    try:
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=600,  # Keep responses concise
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT_STATIC,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": dynamic_system,
                },
            ],
            messages=messages
        )

        assistant_message = response.content[0].text
        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        return {
            "response": assistant_message,
            "model_used": model_label,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "error": None
        }

    except Exception as e:
        return {
            "response": "Something went wrong. Please try again in a moment.",
            "model_used": model_label,
            "tokens_in": 0,
            "tokens_out": 0,
            "error": str(e)
        }