# FinTrack — Development Journal

This document tracks my learning journey building FinTrack from the ground up. Updated weekly with what I learned, what was hard, what decisions I made, and what's next.

---

## Week 0 — Planning & Architecture

**Date:** March 2026

### What I did this week

- Created PROJECT_PLAN.md with full technical decisions documented and reasoned
- Designed database schema: users, transactions, categories, goals, budgets, anomalies
- Planned v1 API endpoints (7 endpoints: 3 auth + 4 transaction CRUD)
- Created complete folder structure following layered architecture (routes/services/pipelines/models/ml_engine)
- Initialised git repository with conventional commit format
- Set up professional README with version roadmap, tech stack table, and architecture diagram
- Registered Ltd company through Companies House
- Opened business bank account (Monzo Business)
- Registered with ICO for data processing
- Applied for SEIS advance assurance from HMRC
- Started Twitter/X account documenting the build journey
- Created .gitignore, .env.example, config.py, requirements.txt

### Key decisions and reasoning

**Why Flask over Django?**

<!-- GUIDANCE: Your answer should cover these points in YOUR OWN WORDS:
     - Flask gives you control over architectural decisions (Django makes them for you)
     - You WANT to make decisions like "where does auth go" and "how do I structure services" because learning those decisions is the point
     - Django's built-in admin, ORM, and auth would hide the engineering work you're trying to demonstrate
     - Flask is industry-standard for APIs — it's not a "lesser" choice, it's the right tool for this job
     - You considered FastAPI but async adds complexity that doesn't solve a real problem at this scale
     Write 3-4 sentences. Be specific. -->

[YOUR REASONING HERE]

**Why SQLite for development, PostgreSQL for production?**

<!-- GUIDANCE: Your answer should cover:
     - SQLite requires zero setup — no server, no configuration, just a file
     - Perfect for rapid iteration during development (easy to reset, portable)
     - PostgreSQL is needed in production for concurrent users, reliability, and scalability
     - SQLAlchemy makes the switch painless — only the connection string changes
     - This is a deliberate engineering strategy: start simple, upgrade when needed
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why SQLAlchemy ORM instead of raw SQL?**

<!-- GUIDANCE: Your answer should cover:
     - Database-agnostic — same code works with SQLite and PostgreSQL (critical for your migration strategy)
     - Prevents SQL injection automatically through parameterised queries
     - Industry standard with Alembic for schema migrations
     - You mitigate the "hides SQL" downside by using echo=True in development to see every generated query
     - Raw SQL would be more verbose, database-specific, and harder to migrate
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why Decimal for money and not Float?**

<!-- GUIDANCE: Your answer should cover:
     - Floating point arithmetic has rounding errors: 0.1 + 0.2 = 0.30000000000000004
     - Financial calculations require exact precision — you cannot be off by fractions of a penny
     - Decimal type is designed specifically for exact decimal arithmetic
     - This is a professional decision that shows understanding of data types in financial systems
     Write 2-3 sentences. -->

[YOUR REASONING HERE]

**Why user authentication from v1 instead of adding it later?**

<!-- GUIDANCE: Your answer should cover:
     - This is a real product, not a single-user demo — users must exist from day one
     - Every transaction needs a user_id foreign key for data isolation
     - Retrofitting auth onto an existing codebase is significantly harder than building it from the start
     - Without auth, you'd have to restructure every query and every route when you add it later
     - Security is a foundation, not a feature you bolt on
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why Jinja2 templates first instead of React?**

<!-- GUIDANCE: Your answer should cover:
     - Jinja2 lets you ship a working product in one codebase without learning a frontend framework simultaneously
     - The backend is built as a REST API from day one, so React can replace templates later without changing any backend code
     - Starting with React would double development time at a stage where speed matters most
     - This shows engineering maturity: ship with simple tools first, modernise when the foundation is solid
     Write 3-4 sentences. -->

[YOUR REASONING HERE]

**Why no PUT/update endpoint in v1?**

<!-- GUIDANCE: Your answer should cover:
     - MVP scope discipline — add, view, and delete are sufficient for v1
     - Users can delete and re-add to correct mistakes
     - PUT adds form complexity (pre-populate fields, handle partial updates) that doesn't change core value
     - Deliberately deferred to v2 — this shows intentional prioritisation, not an oversight
     Write 2-3 sentences. -->

[YOUR REASONING HERE]

### What I learned

<!-- GUIDANCE: Be specific. Not "I learned about databases" but specific insights like:
     - "I learned that Float types have binary representation issues that make them unsuitable for money"
     - "I learned that Flask blueprints let you organise routes into separate files"
     - "I learned that .gitignore needs to include .env to prevent committing secrets"
     - "I learned that normalising categories into a separate table prevents data inconsistency"
     - "I was surprised by how much planning is involved before writing any code"
     List 4-6 specific things. -->

- [SPECIFIC LEARNING 1]
- [SPECIFIC LEARNING 2]
- [SPECIFIC LEARNING 3]
- [SPECIFIC LEARNING 4]
- [SPECIFIC LEARNING 5]

### What was hard

<!-- GUIDANCE: Be honest. This is what makes the journal valuable. Examples:
     - "Designing the database schema took much longer than expected — deciding whether category should be text or a FK required thinking through v2 implications"
     - "Understanding the difference between guidance and regulated financial advice required research into FCA rules"
     - "Choosing between Flask and Django required reading documentation for both before I felt confident in the decision"
     - "Figuring out what belongs in v1 vs later versions was difficult — I kept wanting to add more features"
     List 2-4 honest challenges. -->

- [HONEST CHALLENGE 1]
- [HONEST CHALLENGE 2]
- [HONEST CHALLENGE 3]

### What's next

- Week 1: Build User model with Flask-Login + Bcrypt
- Week 1: Build auth routes (register, login, logout)
- Week 1: Build Transaction model with user_id foreign key
- Week 1: Build transaction CRUD endpoints
- Week 1: Deploy initial version to Render

---

## Week 1 — Auth + Database + First API

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Key decisions and reasoning

- [Document every technical choice — for example: "I chose to use Flask Blueprints to organise routes because..." ]

### What I learned

- [Be specific — not "learned Flask" but "learned how Flask-Login's user_loader callback maintains sessions across requests by storing the user ID in the session cookie"]

### What was hard

- [Be honest — debugging, confusion, things that didn't work the first time]

### What's next

- [Specific tasks for week 2]

---

## Week 2 — Frontend + Ship v1.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### v1.0 shipped!

- **What works:** [List everything that works]
- **What's ugly:** [Be honest about what needs improvement — this shows self-awareness]
- **What I'd do differently:** [Reflection on the first two weeks]
- **Git tag:** v1.0

---

## Week 3 — Goals + Analytics + Ship v2.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Key decisions

- [Why did you structure the service layer this way?]
- [How did you decide what analytics to build first?]
- [How did you design the fact-find questionnaire?]

### v2.0 shipped!

- **Git tag:** v2.0

---

## Week 4 — Simulator + ML Categorisation

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### ML decisions

- [What approach did you take for auto-categorisation and why?]
- [How did you prepare training data?]
- [What accuracy did you achieve? Is that good enough? Why?]

### Simulator design

- [How does the projection engine work?]
- [What assumptions does it make?]
- [How does scenario modelling differ from baseline projection?]

---

## Week 5 — Intelligence Layer + Ship v3.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### v3.0 shipped!

- **Git tag:** v3.0
- **This is the version that makes people say "wow"**

---

## Week 6 — Nudges + Budgets + Ship v4.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Nudge system design

- [How does the ML identify high-spend days?]
- [What tone did you choose for nudge messages and why?]
- [How do you avoid making users feel guilty?]

### v4.0 shipped!

- **Git tag:** v4.0

---

## Weeks 7–8 — Stripe + Chatbot

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Stripe integration

- [How do webhooks work and why are they necessary?]
- [How does the 14-day trial expire technically?]
- [What happens when a payment fails?]

### Chatbot design

- [What goes into the system prompt?]
- [How does the context builder assemble user data?]
- [How did you test compliance boundaries?]
- [What adversarial questions did you try and what happened?]

---

## Session — Affordance Audit, Trial Gate Fixes, Doc System Hardening

**Date:** 18 Apr 2026

### What was done

Third audit pass focused on interactive affordance, button vocabulary enforcement, centering island removal, and CSS variable scoping. Identified and fixed a class of issues that wouldn't show in static analysis: mixed tappable/non-tappable lists, invisible section CTAs, custom pill button classes, lone btn-secondary CTAs, and rgba values hardcoded outside the CSS token system.

### Fixes shipped

- **trial_gate.html:** Removed decorative circular icon above h1, removed all `text-align: center` (header, value framing, CTA card title, fine print, trust signals), fixed CTA card to use CSS variables, changed button to `btn-primary btn-full`, removed centering island wrapper, removed orphaned `</div>`.
- **CSS variables:** Added `--gold-whisper-bg` and `--gold-whisper-border` to `:root` in `main.css` so all themes inherit them. Added ivory and cobalt overrides to `themes.css`. Previously only existed on `body.theme-racing-green` — other themes got `undefined`.
- **Section CTAs (overview.html):** "My goals" and "My money" section CTAs changed from invisible plain-text links → custom pill class (wrong) → `btn-secondary btn-sm` with Lucide chevron-right. Now have clear interactive affordance.
- **Overview pots list:** Removed Lifestyle & Buffer allocation rows — they have no detail pages and were mixing non-tappable rows into a tappable list. All remaining pot rows navigate to goal detail. List is now homogenous.
- **goal_detail.html unreachable state:** Added "No contribution set" heading, changed `btn-secondary` → `btn-primary btn-sm`, changed label from "Adjust this goal" → "Edit this goal", fixed link target (was incorrectly pointing to `my_goals`, now points to `edit_goal`).
- **withdraw.html:** Replaced custom `.withdraw-preset` pill-shaped class with `btn-secondary btn-sm`. Deleted the entire `<style>` block defining it.
- **Centering islands removed:** `surplus_reveal.html`, `plan_reveal.html`, `plan_review.html`, `goal_chips.html` — outer `max-width: 560px; margin: 0 auto` wrappers removed from all four.
- **companion.html:** Removed `text-align: center` from daily limit reached message.
- **plan_review.html:** Removed `text-align: center` from guidance footer paragraph.
- **budgets.html:** Fixed hardcoded `rgba(197,163,93,0.2)` → `var(--roman-gold-glow)`.
- **DESIGN-SYSTEM.md:** Added §4.5 Section CTAs, §12.0 List affordance rule, 4 new compliance checks (centering island, lone secondary CTA, custom pill button, fix-everywhere rule).
- **AGENTS.md:** Added full UI audit subsections — Button vocabulary, Section CTAs, Affordance (list homogeneity), Centering islands, Colour hardcoded rgba, Empty/unreachable states, Audit scope.
- **lessons.md:** 8 new entries added. Duplicate "mixed tappable/non-tappable" entry merged into one with the correct final rule.

### Outstanding

- Playwright stress test blocked by MCP server disconnect — prompt ready for next session to resume immediately
- Backend: wire `show_life_checkin_nudge` variable in overview route (Dan's task, unchanged)

---

## Session — Onboarding UX Audit: Chip States, CTA Patterns, Wizard Flow, AI Whisper Placement

**Date:** 18 Apr 2026

### What was done

Second UI audit pass focused on the onboarding wizard and post-onboarding overview experience. Identified and fixed structural and interaction-level UX failures: competing progress systems (welcome 2-step checklist vs. 4-step wizard), invisible chip selected states, hidden primary CTAs, AI commentary on the wrong page, and inconsistent Lucide icon usage across CTA buttons.

### Fixes shipped

- **Onboarding architecture:** Removed welcome page from new-user flow. Register now routes directly to factfind (step 1 of 4). The wizard handles complete onboarding. Competing progress systems eliminated.
- **Chip selected states:** `goal_chips`, `factfind`, `surplus_reveal` — selected chips now use `var(--roman-gold)` border, replacing the near-invisible `rgba(255,255,255,0.3)`.
- **CTA pattern:** goal_chips "Build my plan" button changed from `display:none` (hidden until selection) to always-visible disabled state with instructional text. Enables + gains arrow icon on selection.
- **AI whisper placement:** Removed gold-card commentary from `plan_reveal` (reveal/hero moment). Added to `plan_review` (detail/confirmation step) where it's contextually appropriate.
- **Lucide icons:** All CTA arrow icons standardised to Lucide `arrow-right` SVG. Back links use Lucide `chevron-left`. DOM construction via `createElementNS` (innerHTML blocked by security hook).
- **Step bar layout:** Back link moved to LEFT of bars on `goal_chips`, `surplus_reveal`, `plan_reveal`. Step counter stays RIGHT.
- **Password strength (register):** Upgraded from 3-bar (length-only) to 4-bar system + per-requirement chips (8+ chars, Uppercase, Number, Symbol) — matches settings.html pattern.
- **Settings:** Financial Profile section stripped of `glass-card` wrapper — now a flat bare section matching Account and Appearance.
- **Optional fields:** `(optional)` indicators added to Target amount, Already saved, Monthly contribution, Target date on add_goal and edit_goal forms.
- **Overview nudge:** No-goals nudge removed old 2-step progress bars and now links to `/goals/choose` (wizard) instead of the manual add-goal form.
- **AGENTS.md:** Updated with registration routing rule, button icon rule, onboarding wizard architecture, and wizard page sequence.
- **lessons.md:** Four new lessons added (chip states, hidden CTAs, AI whisper placement, competing progress systems).

### Branch

`test/onboarding-ui-audit` — pushed for Dan's review. May have conflicts with Dan's concurrent changes; resolve in next session.

---

## Session — UI Audit: Colour Semantics, Card Usage, Hierarchy (All Active Routes)

**Date:** 17 Apr 2026

### What was done

Ran a comprehensive end-to-end UI audit against the full `/ui-audit` checklist across all 25 active Claro templates. Every confirmed violation was fixed in the same session. Key areas resolved: gold colour overuse (hardcoded `rgba(197,163,93,...)` bypassing CSS tokens broke all non-default themes), card misuse on non-financial analysis sections, CRUD completeness gap on goal detail, missing back-links on plan and check-in pages, and onboarding progress bars incorrectly using gold instead of neutral white.

### Fixes shipped

- **Gold token sweep:** Eliminated all hardcoded `rgba(197,163,93,...)` across 8 templates. All gold now flows from `var(--roman-gold)` or `var(--roman-gold-dim)` tokens, meaning Cobalt and light themes no longer break.
- **Card overuse:** Removed `glass-card` wrappers from analysis/comparison sections in `insights.html` and all 9 form sections in `goal_chips.html`. Cards are now only on discrete financial objects.
- **Onboarding progress bars:** All 4 step-indicator bars across `factfind`, `surplus_reveal`, `goal_chips`, `plan_reveal` changed from gold to `rgba(255,255,255,0.25)`. Gold progress bars are now strictly goal savings bars only.
- **CRUD completeness:** Added Edit button to `goal_detail.html`. Users can now reach goal editing from the detail page, not just the goals list.
- **Navigation:** Added ← Overview back links to `plan.html` and `checkin.html`.
- **Copy:** Fixed em dash in `insights.html` body copy and `simulator_routes.py` user-facing message. Done icon circles on `welcome.html` changed from gold to green (matching the "done" badge convention).
- **Chip selection states:** Factfind subscription chips, goal chips, and lifestyle budget options — gold selected state replaced with neutral white across `factfind.html`, `goal_chips.html`, `surplus_reveal.html`.

### Outstanding

- Playwright visual verification still needed (MCP was unavailable during session — prompts ready for next session)
- Settings accordion cards (Appearance, Account) — design decision deferred on whether to convert to bare sections

---

## Week 9 — Deploy + Launch + Ship v5.0

**Date:** [INSERT DATE]

### What I did this week

- [Fill in as you go]

### Launch checklist completed

- [ ] PostgreSQL migration verified
- [ ] All tests passing in CI/CD
- [ ] Stripe in live mode
- [ ] Security audit complete
- [ ] Documentation complete
- [ ] README with screenshots and live demo link
- [ ] Waitlist landing page live

### v5.0 shipped!

- **Git tag:** v5.0
- **Live URL:** [INSERT URL]

---

## Final Reflection

**Most important thing I learned across the whole project:**

[Write a genuine reflection — what changed about how you think about software engineering?]

**Hardest challenge and how I overcame it:**

[Be specific about a particular problem, not generic]

**What I'm most proud of:**

[What would you show someone first?]

**What I'd do differently if I started over:**

[This shows growth — employers value honest reflection over claims of perfection]

**What's next for FinTrack:**

[What's on the v6 roadmap? What did users ask for that you haven't built yet?]

---

## 2026-05-01 — Account deletion (UK GDPR Article 17) + FK cascade

### What I did

- **Cascade on every user-referencing FK.** Updated `transactions`, `goals`,
  `budgets`, `chat_messages`, `life_checkins`, `checkins`, and
  `checkin_entries` so deleting a user (or a parent check-in) doesn't fail
  on FK violations. Models now use `ondelete="CASCADE"`; relationships use
  `cascade="all, delete-orphan"` and `passive_deletes=True` so SQLAlchemy
  defers to the DB instead of issuing per-row DELETEs.
- **Idempotent migration in `app/__init__.py`.** Postgres-only block that
  reads `information_schema.referential_constraints`, drops + recreates any
  FK whose `delete_rule` isn't already `CASCADE` (or `SET NULL` for
  `checkin_entries.goal_id`). Safe to redeploy — once the cascade is in
  place, the block becomes a no-op. SQLite local dev relies on ORM-level
  cascade plus `PRAGMA foreign_keys = ON` (added as a connect-event hook).
- **Deletion service.** `app/services/account_service.py` —
  `delete_user_account(user_id, reason=None)`. Cancels the Stripe
  subscription immediately, fires `account_deleted` to PostHog *before* the
  row is removed (so the distinct_id still resolves), then deletes the user.
  Stripe failures are caught and logged but do not abort the DB delete —
  data erasure is the GDPR obligation; an orphaned subscription is the
  lesser harm. Idempotent: deleting an already-absent user returns True.
- **Settings UX.** A subtle "Danger zone" link at the bottom of
  `/settings` opens a dedicated `/settings/delete-account` page (not a
  modal — account deletion deserves a full-page moment). The page explains
  what is removed, takes an optional reason, and uses GitHub's "type
  DELETE to confirm" pattern to arm the destructive button. After
  deletion the user is logged out and lands on `/account-deleted` with a
  short confirmation and a link to register again.
- **9 new tests** covering the service (DB delete, cascade, Stripe call,
  Stripe failure, PostHog ordering, idempotency) and the route (auth
  required, wrong confirmation rejected, happy path). Suite goes
  407 → 416 passing.

### GDPR status

- **Article 17 (right to erasure):** ✅ in place from this PR.
- **Article 20 (right to data portability / export):** ❌ still TODO.
  When a user deletes their account they're also entitled to a copy of
  their data first. Half-day of work. Pre-launch backlog.

### Schema management note

Migrations are still managed by `db.create_all()` + the idempotent
`ALTER TABLE` block in `app/__init__.py`. Bootstrapping
Flask-Migrate / Alembic is recommended within the next 2 weeks
pre-launch (separate PR — needs `flask db stamp head` against prod
before the first `flask db upgrade`).

---

## 2026-05-01 — Server-side PostHog instrumentation

### What I did

- Added the `posthog==7.13.2` Python SDK + `backoff==2.2.1` dep to `requirements.txt`.
- Built `app/services/analytics_service.py` — a thin lazy-init wrapper around the
  PostHog SDK with three public functions: `track_event(user_id, event_name, properties=None)`,
  `identify_user(user_id, properties=None)`, and `flush()`. The wrapper:
  - Reads `POSTHOG_API_KEY` and `POSTHOG_HOST` from Flask config (or env vars when no app context).
  - Drops events silently and logs a single warning when the key is missing — dev environments without it don't crash.
  - Catches every SDK exception so analytics failures NEVER propagate into a user-facing route.
  - Auto-attaches `environment` (test/dev/prod), `timestamp`, and `user_tier` (when discoverable from `current_user`) to every captured event.
- Wired the agreed taxonomy server-side at the natural firing point in each route handler. **Server-side capture only — no JS snippet in `base.html`.**

### Events instrumented (where they fire)

| Event | Location |
|------|---------|
| `user_signed_up` | `pages.register` POST + `auth.register` POST (API) |
| `welcome_screen_viewed` | `pages.welcome` GET |
| `factfind_started` | `pages.factfind` GET when `factfind_completed=False` |
| `onboarding_stage1_completed` | `pages.factfind` POST success (first time only) |
| `partial_projection_1_viewed` | `pages.surplus_reveal` GET |
| `onboarding_stage2_completed` | `pages.surplus_reveal` POST success |
| `partial_projection_2_viewed` | `pages.goal_chips` GET |
| `onboarding_stage3_completed` | `pages.goal_chips` POST success — includes `time_to_onboarding_complete` (minutes since signup) |
| `goals_added` | `pages.goal_chips` POST + `pages.add_goal` POST (with `count`, `types`, `source`) |
| `plan_revealed` | `pages.plan_reveal` GET when `plan_wizard_complete` is being set true (first reveal only) |
| `credit_card_added` | Stripe `checkout.session.completed` webhook |
| `trial_started` | Same handler — Stripe Checkout requires a card before the subscription, so they fire together |
| `checkin_started` | `pages.checkin` GET when not already done |
| `checkin_completed` | `pages.checkin` POST success |
| `goal_milestone_hit` | Inside `pages.checkin` POST loop — fires when a goal's progress crosses 25/50/75/100% |
| `companion_message_sent` | `companion.companion_chat` after successful response — properties: `tier`, `message_count_today`, `tokens_in/out`, `model_routed` (`haiku` or `sonnet`) |
| `companion_rate_limit_hit` | `companion.companion_chat` and `.edit_message` when daily limit reached — properties: `tier` (effective rate-limit key, e.g. `pro`/`pro_plus`/`joint`/`trial`), `time_until_reset_seconds` |
| `withdrawal_started` | `pages.plan` GET when `?withdraw=1` first opens the inline section |
| `withdrawal_preview_generated` | `pages.plan_withdraw_preview` POST success — properties: `amount` |
| `withdrawal_confirmed` | `pages.plan_withdraw_confirm` POST success — properties: `amount` (the plan was applied to goals) |
| `withdrawal_dismissed` | `pages.plan_withdraw_dismiss` POST — user clicked "No, just show me"; properties: `amount` |
| `cancel_confirmed` | Stripe `customer.subscription.deleted` webhook |
| `account_deleted` | `account_service.delete_user_account` — fires before the User row is removed; properties: `reason` (optional free text from the user) |
| `dev_test_event` | `/dev/posthog-test` (debug-only smoke test) |

`identify_user(user_id, {email, name, tier, signup_date})` also fires on every register and login so funnels attribute to a stable distinct ID.

### Events NOT yet instrumented (TODO)

- `email_verified` — no email verification flow exists yet. Add when that ships.
- `crisis_flow_entered` — no crisis flow page exists yet.
- `cancel_clicked` / `cancel_dismissed` — Stripe customer-portal hosts the cancel UI off-app, so we don't see the click. When an in-app cancel page ships, instrument these there. Marked with `TODO PostHog:` comments in `billing_routes.py`.

### Tests

Added `tests/test_analytics_service.py` (9 tests) covering the four contracts:
1. No-op when key missing
2. SDK called with right args when key set
3. Exceptions don't propagate (wrapper + integration)
4. `environment` auto-attached to every event

Total suite: **407 passing** (398 original + 9 new).

### What's deliberately NOT done

- **No JS snippet in `base.html`.** Server-side capture only — keeps the data clean, avoids consent-banner complexity at MVP stage. When we need session replay or autocapture, revisit.
- **Git remote update** (`Drogers0819/Fintrack.git → Drogers0819/Claro.git`) is a user action; left for Daniel to run manually.
- **Render env vars** must still be set in the dashboard before the next deploy or events fail silently in prod.

### Hard lessons / decisions

- **Lazy single-client init** — easier than wiring a Flask extension. The first call to `track_event` triggers init via `current_app.config`; subsequent calls hit a cached client. Guards against repeat warning spam when the key is missing.
- **Exception swallowing is non-negotiable** — `except Exception` in tracking code is normally a smell, but here the contract is explicit: analytics is auxiliary, must not break product features.
- **`time_to_onboarding_complete` is computed at the firing point** rather than stored on the user — keeps the event self-describing and avoids a migration. Computed as `(datetime.utcnow() - user.created_at).total_seconds() / 60` at the moment stage 3 completes.

---

## 2026-05-02 — Companion live in production

### What I did

- **UTC rate-limit reset.** `check_rate_limit` and `increment_message_count` in `companion_service.py` now compare against `datetime.utcnow().date()` instead of `date.today()`. No schema change — the existing `companion_last_reset` Date column is reused, the comparison is just explicit about timezone. On Render the server is UTC anyway; this just decouples behaviour from server local time.
- **Per-tier rate-limit chat bubble.** `check_rate_limit` returns a 3-tuple `(allowed, reason, kind)` where `kind` is `'free'` (paywall), `'rate_limit'` (daily cap), or `None` (allowed). Per-tier copy lives in `_RATE_LIMIT_COPY` in `companion_service.py`. Pro / Pro+ / Joint / Trial each get tailored wording. The bubble renders at the end of chat history (page-load path) or via the existing 429 JS handler (mid-chat path); not persisted as a `chat_messages` row. Below the bubble, the input zone is replaced with "Messaging resumes at midnight UTC."
- **Companion nav visibility.** Added `_inject_companion_access` context processor in `app/__init__.py` exposing `can_access_companion = is_subscription_active(current_user)`. Wraps the four companion nav slots in `base.html` (slim sidebar, legacy desktop sidebar, slim mobile tabs, legacy mobile tabs) plus the overview prompt + chips. Free post-trial users no longer see a link they can't follow.
- **Hybrid classifier enriched.** `COMPLEX_TRIGGERS` extended with distress markers (`lost my job`, `can't afford`, `struggling`, `worried`, `anxious`, `stressed`, `scared`, `overwhelmed`, `in trouble`, `broke`, `no money`, `behind on`, `missed a payment`). Routes these to Sonnet because its judgement and warmth on emotionally-loaded financial situations is materially better than Haiku's. Skipped the conversation-history continuation and length-based heuristic — the keyword list is sufficient at this stage and we'll revisit after the 25-scenario sprint.
- **Effective limit key.** Added `_effective_limit_key(user)` so trial users (status=`trialing`) hit the trial limit (5/day) regardless of their plan tier. Previously a Pro-tier user mid-trial would have got the Pro limit (10/day) — minor but the per-tier copy depends on it.
- **Smoke test route.** `/dev/companion-smoke-test` registered only when `app.debug` is true. Calls `companion_service.smoke_test_chat()` which bypasses user context, rate limits, and persistence — just hits the API with the cached static system prompt and returns `success`, `response_text`, `model_used`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `cache_hit`, `latency_ms`. Hit it twice within 5 minutes locally to verify caching engages: first call shows `cache_creation_input_tokens > 0`, second shows `cache_read_input_tokens > 0`. **Remove in a follow-up commit (`chore: remove companion smoke test route once verified`) after one-off verification.**

### Events instrumented

- `companion_message_sent` — added `model_routed` property (`haiku` or `sonnet`) so we can track the routing split in PostHog and compare against the 70/30 cost model.
- `companion_rate_limit_hit` (new) — fires from `companion.companion_chat` and `.edit_message` when the daily cap is reached. Properties: `tier` (effective rate-limit key) and `time_until_reset_seconds` (computed from next UTC midnight). Helps quantify how often users hit the cap and inform whether 30/day on Pro+ is the right number.

### What's deliberately NOT done

- **No `@requires_companion_access` decorator and no `/companion/upgrade-needed` page.** `@requires_subscription` already gates the only fully-blocked case (free post-trial). Pro tier keeps its 10 messages/day. The pricing page handles tier-feature messaging ("AI companion (limited)" vs "(full)") rather than the gating logic.
- **No schema change for `companion_messages_reset_at`.** The existing `companion_last_reset` Date column does the job once UTC is wired in. Adding a DateTime column would have been the same behaviour on Render with extra migration risk.
- **No conversation-history or length-based heuristic in the classifier.** Keyword list is enough for now; revisit after the 25-scenario evaluation sprint.

### Tests

Added `tests/test_companion_routes.py` covering classifier (existing triggers + distress markers + simple), rate-limit (UTC reset, per-tier copy, kind discrimination, free-tier blocking), per-tier `_effective_limit_key`, smoke-test 404 in non-debug mode, and the rate-limit chat-bubble rendering on page load.

### Manual verification still needed

- Confirm `ANTHROPIC_API_KEY` and `POSTHOG_API_KEY` are set in Render.
- Hit `/dev/companion-smoke-test` locally twice within 5 minutes to confirm caching engages.
- Send a real message in production with a Pro+ test account; check PostHog for `companion_message_sent` with `model_routed` populated.
- Verify a free post-trial test account does NOT see the Companion nav link in any of the four nav slots.
- Verify the rate-limit bubble appears (lower the limit temporarily to 1 if needed for the test).
- After verification, delete the smoke test route in a follow-up commit.

---

*This journal is part of the FinTrack project. It documents genuine learning, not polished retrospection. Mistakes, confusion, and wrong turns are included deliberately — they're where the real growth happened.*