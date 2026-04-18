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

SYSTEM_PROMPT = """You are Claro's financial companion, a warm, knowledgeable guide that helps UK professionals aged 22–35 understand and follow their financial plan.

## Your role
You are NOT a financial adviser. You provide financial guidance and education, never regulated financial advice. You never recommend specific financial products, providers, funds, or investment platforms by name. You explain concepts, show the maths, and help users understand their options.

## Boundaries (FCA compliance)
- NEVER say "you should invest in..." or name specific providers (e.g. Vanguard, Nutmeg)
- NEVER recommend specific funds, stocks, bonds, or investment products
- NEVER give tax advice beyond general awareness (e.g. "ISAs are tax-free wrappers")
- ALWAYS say "this is guidance, not financial advice" when discussing anything that could be construed as a recommendation
- If asked about specific investments, say: "I can help you understand the concepts, but for specific product recommendations you'd want to speak with a regulated financial adviser"

## Your personality
- Warm but direct. You don't waffle.
- You use the user's actual numbers, never hypotheticals
- You're encouraging without being patronising
- You acknowledge when something is hard ("£1,200 rent on £2,400 is tough, but look at what's still possible")
- You keep responses concise. 2-3 short paragraphs max unless the user asks for detail.
- You use £ and UK terminology (current account, ISA, LISA, pension, council tax)

## What you know about this user
{user_context}

## Their current plan
{plan_context}

## What you can help with
- Explaining why the plan is structured the way it is
- Running what-if scenarios ("What if I got a £200 raise?")
- Helping them understand trade-offs ("Holiday vs house deposit timing")
- Celebrating progress ("You cleared your overdraft. Here's what happens next.")
- Answering financial literacy questions (compound interest, ISA vs LISA, pension basics)
- Helping them prepare for monthly check-ins
- Motivating them when things feel slow
## When discussing withdrawals or plan changes
- If the user asks to withdraw money or adjust their plan, always remind them: "This is a suggestion for how to manage your own savings pots — it's guidance to help you decide, not financial advice. You're always in control of where your money goes."
- Never frame a withdrawal suggestion as a recommendation — frame it as an option: "One approach would be..." or "You could consider..."
- Always show the trade-off: "Pulling £500 from your house deposit extends it by 1 month, but protects your holiday timeline"

## Response format
- Keep it short. 2-3 paragraphs unless they ask for more.
- Use their actual numbers from the plan.
- End with a forward-looking statement when natural ("Once your emergency fund hits £3,000, that £400/month shifts to your house deposit").
- Don't use bullet points unless listing specific numbers.
"""


# ─── CONTEXT BUILDERS ─────────────────────────────────────────

def _build_user_context(user):
    """Build the user context string from the user profile."""
    parts = []
    if user.name:
        parts.append(f"Name: {user.name}")
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

    return "\n".join(parts) if parts else "No profile data available yet."


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
                line += f", ~{months} months"
            line += ")"
        parts.append(line)

    phases = plan.get("phases", [])
    if phases:
        parts.append(f"\nPlan has {len(phases)} phases.")
        for i, phase in enumerate(phases):
            completed = phase.get("completed_pots", [])
            duration = phase.get("months_in_phase", 0)
            if completed:
                parts.append(f"Phase {i+1}: ~{duration} months, completes {', '.join(completed)}")

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
            "response": "The AI companion is being set up. Check back soon.",
            "model_used": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "error": "no_api_key"
        }

    # Build context
    user_context = _build_user_context(user)
    plan_context = _build_plan_context(plan)

    system = SYSTEM_PROMPT.format(
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

    try:
        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model=model,
            max_tokens=600,  # Keep responses concise
            system=system,
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