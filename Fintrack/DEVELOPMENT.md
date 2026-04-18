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

*This journal is part of the FinTrack project. It documents genuine learning, not polished retrospection. Mistakes, confusion, and wrong turns are included deliberately — they're where the real growth happened.*