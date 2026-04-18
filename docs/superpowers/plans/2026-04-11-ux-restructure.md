# Claro UX Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure Claro's navigation and page hierarchy so each page owns exactly one job — Overview (status), My Money (history), Transactions (log), Goals (goals only), Plan (new — planning tools), Budgets (limits).

**Architecture:** Template-only changes plus one new route. No backend services, models, or data logic is touched. The `_build_whisper_data()` helper continues to supply all data; we just route it to the correct templates. The new `/plan` route reuses the same habit cost calculator POST handler that currently lives in `my_goals()`.

**Tech Stack:** Flask/Jinja2 templates, Python route handlers in `page_routes.py`, Lucide SVG icons inline in `base.html`.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `Fintrack/app/templates/base.html` | Modify | Add Plan nav link between Goals and Budgets; update Goals active-state list to exclude `pages.plan` and `pages.scenario_page` |
| `Fintrack/app/templates/plan.html` | Create | New page — income waterfall + habit calculator + What if? link |
| `Fintrack/app/routes/page_routes.py` | Modify | Add `/plan` route; strip `my_goals()` of habit POST and waterfall; remove unused `intel` + `whisper` from `overview()` |
| `Fintrack/app/templates/my_goals.html` | Modify | Remove waterfall block, remove planning tools section |
| `Fintrack/app/templates/overview.html` | Modify | Remove `memory_card` ambient line (last vestige of insight block); overview is now status + goal + recent activity only |

---

## Task 1: Add Plan to nav in base.html

**Files:**
- Modify: `Fintrack/app/templates/base.html:33-38`

- [ ] **Step 1: Add Plan nav link between Goals and Budgets**

In `base.html`, find the Goals nav link (line 33) and the Budgets nav link (line 36). Insert the Plan link between them:

```html
<a href="{{ url_for('pages.plan') }}" class="nav-link {% if request.endpoint in ['pages.plan', 'pages.scenario_page'] %}active{% endif %}">
    <span class="nav-icon"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" x2="2" y1="12" y2="12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/><line x1="6" x2="6.01" y1="16" y2="16"/><line x1="10" x2="10.01" y1="16" y2="16"/></svg></span> Plan
</a>
```

- [ ] **Step 2: Remove `pages.scenario_page` from Goals active-state condition**

The Goals nav link currently has:
```html
class="nav-link {% if request.endpoint in ['pages.my_goals', 'pages.add_goal', 'pages.goal_detail', 'pages.scenario_page'] %}active{% endif %}"
```

Change to:
```html
class="nav-link {% if request.endpoint in ['pages.my_goals', 'pages.add_goal', 'pages.goal_detail'] %}active{% endif %}"
```

- [ ] **Step 3: Commit**

```bash
git add Fintrack/app/templates/base.html
git commit -m "feat: add Plan to nav, move scenario_page active state to Plan"
```

---

## Task 2: Create plan.html template

**Files:**
- Create: `Fintrack/app/templates/plan.html`

- [ ] **Step 1: Create the template**

Create `Fintrack/app/templates/plan.html` with the following content. This is the waterfall + habit calculator + What if? block, extracted directly from `my_goals.html`:

```html
{% extends "base.html" %}
{% block title %}Plan — Claro{% endblock %}

{% block content %}
<div class="page-header">
    <h1>Plan</h1>
</div>

<!-- Income waterfall -->
{% if waterfall and not waterfall.error %}
<div class="glass-card" style="margin-bottom: 24px;">
    <div class="metric-label">How your £{{ "%.2f" | format(waterfall.total_income) }}/month is divided</div>

    <div style="margin-top: 12px; padding: 8px 0; border-bottom: 0.5px solid rgba(255,255,255,0.05);">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 0.85rem; color: var(--text-tertiary);">Rent & bills</span>
            <span style="font-size: 0.85rem;">£{{ "%.2f" | format(waterfall.total_commitments) }}</span>
        </div>
    </div>

    {% for a in waterfall.allocations %}
    <div style="padding: 8px 0; {% if not loop.last %}border-bottom: 0.5px solid rgba(255,255,255,0.05);{% endif %}">
        <div style="display: flex; justify-content: space-between;">
            <span style="font-size: 0.85rem;">{{ a.goal_name }}</span>
            <span style="font-size: 0.85rem;
                {% if a.status == 'funded' %}color: var(--text-primary);
                {% elif a.status == 'partially_funded' %}color: var(--roman-gold);
                {% else %}color: var(--text-tertiary);{% endif %}">
                £{{ "%.2f" | format(a.allocated) }}/mo
            </span>
        </div>
        {% if a.projection %}
        <div style="font-size: 0.7rem; color: var(--roman-gold); margin-top: 2px;">
            Reaches target {{ a.projection.projected_date }}
        </div>
        {% endif %}
    </div>
    {% endfor %}

    {% if waterfall.unallocated > 0.01 %}
    <div style="padding: 8px 0; font-size: 0.8rem; color: var(--roman-gold);">
        £{{ "%.2f" | format(waterfall.unallocated) }}/month unassigned
    </div>
    {% endif %}
</div>
{% endif %}

<!-- Habit cost calculator -->
<div class="glass-card" style="margin-bottom: 24px;">
    <div class="metric-label" style="margin-bottom: 12px;">What does your habit really cost?</div>
    <p style="font-size: 0.8rem; color: var(--text-tertiary); margin-bottom: 16px;">
        Enter a monthly spend to see what that money could become over time.
    </p>
    <form method="POST" action="{{ url_for('pages.plan') }}">
        <input type="hidden" name="form_type" value="habit_cost">
        <div class="grid-2">
            <div class="form-group">
                <input type="number" name="habit_amount" class="form-input" step="0.01" min="0.01"
                       placeholder="Monthly amount (£)" value="{{ habit_amount if habit_amount else '' }}" required>
            </div>
            <div class="form-group">
                <input type="text" name="habit_description" class="form-input"
                       placeholder="e.g. Deliveroo" value="{{ habit_description if habit_description else '' }}">
            </div>
        </div>
        <button type="submit" class="btn-secondary btn-sm">Show me</button>
    </form>
</div>

{% if habit_result %}
<div class="gold-card" style="margin-bottom: 24px;">
    <div class="metric-value xs gold" style="margin-bottom: 8px;">
        {{ habit_result.insight.headline }}
    </div>
    <p style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.7;">{{ habit_result.insight.detail }}</p>
    <p style="font-size: 0.8rem; color: var(--roman-gold); font-style: italic; margin-top: 8px;">{{ habit_result.insight.reframe }}</p>
</div>

<div class="grid-3" style="margin-bottom: 24px;">
    {% for key in ["5_year", "10_year", "20_year"] %}
    {% set h = habit_result.horizons[key] %}
    <div class="glass-card" style="text-align: center;">
        <div class="metric-label">{{ h.years }} years</div>
        <div class="metric-value xs">£{{ "{:,.0f}".format(h.opportunity_cost) }}</div>
        <div style="font-size: 0.65rem; color: var(--success);">+£{{ "{:,.0f}".format(h.lost_growth) }} growth</div>
    </div>
    {% endfor %}
</div>
{% endif %}

<!-- What if? -->
<div class="glass-card">
    <div class="metric-label" style="margin-bottom: 12px;">What if?</div>
    <p style="font-size: 0.8rem; color: var(--text-tertiary); margin-bottom: 12px;">
        Change your income, commitments, or goal amounts and see exactly how your future shifts.
    </p>
    <a href="{{ url_for('pages.scenario_page') }}" class="btn-secondary btn-sm">
        Run a scenario <span aria-hidden="true">→</span>
    </a>
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add Fintrack/app/templates/plan.html
git commit -m "feat: add plan.html template with waterfall, habit calculator, what-if"
```

---

## Task 3: Add /plan route to page_routes.py

**Files:**
- Modify: `Fintrack/app/routes/page_routes.py` — add after the `my_goals()` function (around line 574)

- [ ] **Step 1: Add the /plan route**

Find the comment `# ─── MY BUDGETS` (around line 576) and insert the plan route directly above it:

```python
# ─── PLAN ────────────────────────────────────────────────

@page_bp.route("/plan", methods=["GET", "POST"])
@login_required
def plan():
    data = _build_whisper_data()

    habit_result = None
    habit_amount = None
    habit_description = None

    if request.method == "POST" and request.form.get("form_type") == "habit_cost":
        try:
            habit_amount = round(float(request.form.get("habit_amount", 0)), 2)
            habit_description = request.form.get("habit_description", "").strip() or "This habit"
            if habit_amount > 0:
                habit_result = calculate_cost_of_habit(habit_amount)
                habit_result["description"] = habit_description
        except (ValueError, TypeError):
            flash("Invalid amount", "error")

    return render_template("plan.html",
        waterfall=data["waterfall"],
        projections=data["projections"],
        habit_result=habit_result,
        habit_amount=habit_amount,
        habit_description=habit_description
    )
```

- [ ] **Step 2: Commit**

```bash
git add Fintrack/app/routes/page_routes.py
git commit -m "feat: add /plan route with waterfall and habit calculator"
```

---

## Task 4: Strip my_goals() route and my_goals.html of planning tools

**Files:**
- Modify: `Fintrack/app/routes/page_routes.py:540-573`
- Modify: `Fintrack/app/templates/my_goals.html`

- [ ] **Step 1: Simplify the my_goals() route**

Replace the entire `my_goals()` function (lines 540–573) with:

```python
@page_bp.route("/my-goals")
@login_required
def my_goals():
    goals = Goal.query.filter_by(
        user_id=current_user.id, status="active"
    ).order_by(Goal.priority_rank.asc()).all()

    return render_template("my_goals.html",
        goals=[g.to_dict() for g in goals]
    )
```

Note: The route decorator changes from `methods=["GET", "POST"]` to just GET. The habit POST moves to `/plan`.

- [ ] **Step 2: Strip my_goals.html**

Replace the entire content of `Fintrack/app/templates/my_goals.html` with:

```html
{% extends "base.html" %}
{% block title %}My Goals — Claro{% endblock %}

{% block content %}
<div class="page-header">
    <h1>My Goals</h1>
</div>

{% if goals | length > 0 %}
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
    <span class="metric-label" style="margin-bottom: 0;">{{ goals | length }} active goal{{ "s" if goals | length != 1 else "" }}</span>
    <a href="{{ url_for('pages.add_goal') }}" class="btn-secondary btn-sm">+ Add goal</a>
</div>

<div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px;">
    {% for g in goals %}
    <div class="glass-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div>
                <div style="font-size: 1rem; color: var(--text-primary);">{{ g.name }}</div>
                <div style="font-size: 0.7rem; color: var(--text-tertiary);">
                    {% if g.type == "savings_target" %}Saving toward a target
                    {% elif g.type == "spending_allocation" %}Monthly spending budget
                    {% else %}Building over time{% endif %}
                </div>
            </div>
            <span style="font-size: 0.6rem; color: var(--text-tertiary);">Priority {{ g.priority_rank }}</span>
        </div>

        {% if g.target_amount %}
        <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
            <span class="metric-value xs">£{{ "%.2f" | format(g.current_amount) }}</span>
            <span style="font-size: 0.75rem; color: var(--text-tertiary);">of £{{ "%.2f" | format(g.target_amount) }}</span>
        </div>
        <div class="progress-track" style="margin-bottom: 8px;">
            <div class="progress-fill{% if g.progress_percent >= 90 %} warning{% endif %}" style="width: {{ g.progress_percent if g.progress_percent else 0 }}%;"></div>
        </div>
        {% endif %}

        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px;">
            {% if g.target_amount and g.monthly_allocation %}
            <a href="{{ url_for('pages.goal_detail', goal_id=g.id) }}" style="font-size: 0.75rem; color: var(--roman-gold); text-decoration: none;">
                See your future
            </a>
            {% else %}
            <span></span>
            {% endif %}
            <form action="{{ url_for('pages.delete_goal', goal_id=g.id) }}" method="POST" style="margin: 0;">
                <button type="submit" class="transaction-delete" aria-label="Remove goal">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                </button>
            </form>
        </div>
    </div>
    {% endfor %}
</div>

{% else %}
<div class="glass-card" style="margin-bottom: 24px;">
    <div class="metric-label" style="margin-bottom: 8px;">Your goals</div>
    <div class="empty-state" style="padding: 4px 0 12px; text-align: left;">
        What are you working toward? A house deposit, a holiday, an emergency fund?
    </div>
    <div style="margin-top: 4px;">
        <a href="{{ url_for('pages.add_goal') }}" class="btn-primary btn-sm">Set your first goal</a>
    </div>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add Fintrack/app/routes/page_routes.py Fintrack/app/templates/my_goals.html
git commit -m "refactor: goals page shows goals only, planning tools moved to /plan"
```

---

## Task 5: Clean up overview route

The overview route currently passes `whisper` and `intel` — neither is referenced in `overview.html`. Remove both to keep the route honest.

**Files:**
- Modify: `Fintrack/app/routes/page_routes.py:383-486`

- [ ] **Step 1: Remove whisper computation and intel block from overview()**

Find the `overview()` function. Remove these two lines near the top:
```python
data = _build_whisper_data()  # ← keep this, other things depend on it
whisper_result = generate_page_insights("overview", data)  # ← remove this line
```

Then find the `intel` dict construction (around line 434) and remove the entire block:
```python
# Month-context framing
month_context = None
if day_of_month <= 7:
    month_context = "start"
elif day_of_month >= days_in_month - 4:
    month_context = "end"

intel = {
    "recurring_count": recurring_count,
    ...
} if recurring_count > 0 or spending_direction else None
```

Also remove only the variables that exclusively fed `intel` and are not used elsewhere:
```python
# Remove these — only used by intel:
month_context = None
if day_of_month <= 7:
    month_context = "start"
elif day_of_month >= days_in_month - 4:
    month_context = "end"
```

**Keep** `recurring_data`, `recurring_count`, `recurring_total`, `predictions`, `comparison`, `spending_direction`, `spending_diff`, `today`, `day_of_month`, `days_in_month` — these are all used by the `timeline_note` logic below the `intel` block and must stay.

In `render_template("overview.html", ...)`, remove `whisper=whisper_result["whisper"]` and `intel=intel` from the call.

- [ ] **Step 2: Remove memory_card ambient line from overview.html**

In `Fintrack/app/templates/overview.html`, remove the entire `memory_card` block (lines 111–127):

```html
<!-- 3 · Single ambient insight — no card, just a line -->
{% if memory_card %}
<div style="margin-bottom: 20px; font-size: 0.82rem; color: var(--text-tertiary); padding: 0 2px;">
{% if memory_card.anomaly_count > 0 %}
    ...
{% endif %}
</div>
{% endif %}
```

After removal, the overview template structure is exactly: status card → goal card → recent activity. Nothing else.

- [ ] **Step 3: Remove memory_card from overview() render call in page_routes.py**

Remove `memory_card=memory_card` from the `render_template` call, and remove the `memory_card = _build_memory_card(data)` line above it.

- [ ] **Step 4: Commit**

```bash
git add Fintrack/app/routes/page_routes.py Fintrack/app/templates/overview.html
git commit -m "refactor: strip overview route and template to status + goal + activity only"
```

---

## Task 6: Smoke test and push

- [ ] **Step 1: Restart the server**

```bash
pkill -f "python3 run.py"; cd /Users/victoriataiwo/Documents/claro/Fintrack && python3 run.py &
```

- [ ] **Step 2: Visit each page and verify**

| URL | Expected |
|---|---|
| `/overview` | Greeting → status card → goal card → recent activity. No insight block. |
| `/my-goals` | Goal cards only. No waterfall. No habit calculator. |
| `/plan` | Income waterfall → habit calculator → What if? link |
| `/plan` (POST habit form) | Habit result appears below calculator |
| `/budgets` | Unchanged |
| `/my-money` | Unchanged |

- [ ] **Step 3: Verify Plan is active in nav when on `/plan` and `/scenario`**

Navigate to `/plan` — Plan nav item should be gold. Navigate to `/scenario` — Plan nav item should be gold. Goals nav item should NOT be gold on either.

- [ ] **Step 4: Push to remote**

```bash
git push origin main
```
