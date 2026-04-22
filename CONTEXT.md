# CONTEXT.md — Claro
# Last updated: 2026-04-22
# Persona: Product

## Problem statement
Young UK professionals (22–35, £25–60k/year) make daily financial decisions without understanding long-term consequences. Claro is an AI-powered financial planning app that builds a personalised savings plan, allocates every pound to a goal, and acts as an always-on financial companion — filling the gap between passive banking apps and inaccessible financial advisors.

## User
UK renters saving toward 1–3 goals (house deposit, emergency fund, lifestyle goals). They are intelligent and financially responsible but lack forward-looking visibility. They want clarity, not complexity. They distrust jargon and respond to plain language and precise numbers.

## Success criteria
- User sets up plan in <2 minutes and immediately sees where every pound goes
- Monthly check-in takes <60 seconds
- Companion answers financial questions without hallucinating or exceeding guidance guardrails
- UI passes visual audit at Monzo/Notion/Linear bar across all 9 themes and 3 breakpoints

## Current progress
The product is feature-complete for the core loop: onboarding → plan generation → goal tracking → monthly check-in → companion. UI is now at a high polish level following two deep audit sessions. All 9 themes tested and token-compliant. Forms constrained to 560px across all form pages. Section-label spacing standardised. Empty states handled.

## Decisions made
- **CSS token system**: `--sp-*` spacing scale (4px base) is canonical. `--space-*` system removed (2026-04-22)
- **Form max-width**: All form pages capped at `max-width: 560px` — matches add_goal, factfind, upload pattern (2026-04-22)
- **Section-label in flex header rows**: Must always carry `style="margin-bottom: 0; margin-top: 0;"` inline to prevent the class's 16px margin stacking inside the row (2026-04-22)
- **Progress bars**: Empty tracks (pot.current == 0) suppressed — replaced with "Not started" label. No zero-fill renders (2026-04-22)
- **Companion calculators**: Remain on Plan page (all users) AND accessible in Companion (paid only). Not removed (2026-04-17)
- **Check-in "Back to overview" button**: Removed — redundant with nav sidebar (2026-04-22)
- **Nav active state**: `?from=overview` keeps Overview tab active on goal_detail; `?from=plan` keeps Plan tab active (2026-04-18)

## Decisions ruled out
- **Splitting calculators off Plan page**: Rejected — free users have no Companion access, Plan is their only entry point
- **max-width: 560px on data display rows**: Applied briefly to checkin already-done state, then reverted — constraint belongs on forms only, not data tables
- **btn-secondary btn-sm as "Back to overview"**: Removed from check-in done state — nav makes it redundant

## Known constraints
- Flask/Jinja2 server-rendered — no client-side routing, Playwright required for visual verification
- 9 themes must all use CSS token system — hardcoded rgba/hex values silently break non-default themes
- Regulatory: guidance only, never advice. No FCA authorisation at launch.

## Session log

### 2026-04-22 — UI polish audit + spacing/form width sweep
Completed a full optical spacing audit across all active routes. Fixed: form max-width on withdraw, life_checkin, checkin (form state), plan tools section. Fixed section-label double-spacing on checkin (class margin stacking). Removed double border between "What you reported" and History. Applied empty progress bar guard to plan.html and overview.html. Fixed hardcoded hex values in withdraw.html bypassing theme tokens. Cleaned up duplicate spacing token system from main.css. Bumped light theme progress track opacity 0.08→0.12. Fixed life_checkin icon alignment (flex-start). Verified all changes with Playwright at 375/768/1440px. All changes committed and pushed to GitHub.
