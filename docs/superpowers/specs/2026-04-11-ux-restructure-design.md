# Claro UX Restructure — Design Spec
**Date:** 2026-04-11
**Status:** Approved

---

## Problem

The current page structure distributes information by feature type rather than by user intent. This creates three concrete failures:

1. **Overview is overloaded.** Five competing sections before the user can scroll — whisper card, money-left card, overspending card, insight block, recurring strip — then the goal is buried below all of them. The whisper card and insight block say the same things twice.
2. **Pages don't own a single job.** Goals page contains income waterfall, habit calculator, and what-if scenarios. Budgets page contains recurring payments. Users can't build a mental model because each page does multiple unrelated things.
3. **The app gives information, not conclusions.** The user is handed data and left to interpret it. The app should do the work — surface one clear conclusion per section and tell the user what it means.

---

## Design Principles (for this restructure)

- **One page, one job.** Each page answers exactly one question.
- **One conclusion per section.** Every card or block should end with something the user understands without effort.
- **Overview is a dashboard, not a report.** Three things max. Everything else lives on its own page.
- **Tools have a home.** Calculators and simulators belong on a dedicated Plan page, not bolted onto content pages.

---

## Navigation Restructure

### Current nav (5 items)
Overview · My Money · Goals · Budgets · Transactions

### New nav (6 items)
Overview · My Money · Transactions · Goals · Plan · Budgets

**Rationale for order:** Transactions moves next to My Money because they're both about what already happened. Goals and Plan sit together because they're both forward-looking. Budgets is last — a configuration/control page, not a daily-use page.

---

## Page-by-Page Redesign

### 1. Overview
**Question it answers:** "How am I doing right now?"

**Sections (in order):**
1. **Status card** — money left this month + daily rate + budget health badge. Merged from the current two separate cards (money-left + overspending). One card, one verdict.
2. **Primary goal** — goal name, progress bar, amount, projected completion date. Exactly as it is now but in position 2, not buried.
3. **Recent activity** — last 3–5 transactions. No section header needed. Just the list.

**Remove from Overview:**
- Whisper/insight card (redundant with status card)
- Standalone recurring strip (redundant with Budgets page)
- Money in / Money out / Balance **three-column grid** — the grid treatment goes, but the money-left figure stays inside the status hero card. A user should see one number (money left this month) without navigating away. My Money gets the full category and trend breakdown.
- Separate OVERSPENDING card (absorbed into status card)

---

### 2. My Money
**Question it answers:** "Where did my money go?"

No structural change needed. This page already does one job well:
- Spending by category (current month)
- Compared to last month

Keep as-is.

---

### 3. Transactions
**Question it answers:** "What are all my transactions?"

No structural change needed. Clean list, upload/add manually actions in header. Keep as-is.

---

### 4. Goals
**Question it answers:** "Am I on track for my goals?"

**Sections (in order):**
1. Your goals list (existing goal cards)
2. Add goal CTA

**Remove from Goals:**
- Income waterfall ("How your £3,200/month is divided") → moves to Plan
- Habit cost calculator → moves to Plan
- "What if?" scenario tool → moves to Plan

---

### 5. Plan (new page)
**Question it answers:** "What happens if I change something?"

**Sections (in order):**
1. **Income waterfall** — how monthly income is divided (rent + bills + goals + unassigned). Moved from Goals.
2. **Habit cost calculator** — "what does your habit really cost?" Moved from Goals.
3. **What if? scenario tool** — change income/commitments and see how your future shifts. Moved from Goals.

**Route:** `/plan`
**Nav label:** Plan
**Nav icon:** existing scenario/simulator Lucide icon

---

### 6. Budgets
**Question it answers:** "Am I staying within my spending limits?"

No structural change to the budgets section itself (spending limits per category).

**Add to Budgets (moved from elsewhere):**
- Recurring payments list — belongs here because recurring = committed spend = directly relevant to whether budgets are achievable.
- Potential savings spotted — keep here, it's relevant to budget review.

**Note:** Currently recurring payments and budgets are already on the same page. This is correct — no move needed. Just remove them from wherever else they appear (Overview recurring strip).

---

## What Changes, What Stays

| Area | Change |
|---|---|
| `overview.html` | Strip to 3 sections: status card, goal, recent activity |
| `goals.html` | Remove planning tools and income waterfall sections |
| `plan.html` | New page — income waterfall + habit calc + what if |
| `page_routes.py` | Add `/plan` route, update overview route to remove excess data |
| `base.html` | Add Plan to nav (icon + label) |
| `my_money.html` | No change |
| `transactions.html` | No change |
| `budgets.html` | No change |

---

## What This Is Not

- Not a visual redesign. Colours, typography, card styles all stay the same.
- Not a backend change. No new services, no new models, no new data.
- Not removing features. Everything that exists still exists — it just lives in the right place.

---

## Success Criteria

- Overview scrolls to recent activity without the user needing to process 5+ competing blocks
- Goals page contains only goals
- Planning tools are findable in one place (Plan)
- A new user landing on any page can immediately understand what that page is for
