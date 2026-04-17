# Lessons — Claro (Fintrack)

<!-- Claude: review before beginning any work. Update immediately after any correction. -->

## Format — use this exactly, every time

```
## YYYY-MM-DD — [Short title of what went wrong]
**Mistake**: What Claude did wrong
**Fix**: What the correct approach is
**Rule**: The principle to prevent it recurring (one sentence, actionable)
```

---

<!-- Entries go below this line, newest first -->

## 2026-04-17 — metric-label class misused for AI card pulse headers across 6 templates
**Mistake**: `goal_detail.html`, `insights.html`, `checkin.html`, `recurring.html`, `macros.html`, `scenario.html` all used `.metric-label` class on AI card header labels (e.g. "Projection", "Prediction", "Savings spotted", "Claro") with a gold color override. `.metric-label` is for ≤3-word noun labels above numbers only — never for AI card headers.
**Fix**: Replaced `.metric-label` + gold override with inline `font-size: 0.65rem; color: var(--roman-gold); text-transform: uppercase; letter-spacing: 0.06em;` — matching the pattern already established in overview.html, plan.html, budgets.html AI cards.
**Rule**: AI card pulse-header labels always use inline style, never `.metric-label` or `.section-label` class. The distinction: classes are semantic (≤3-word noun above a number; structural section divider). AI headers are one-off inline styled elements.

## 2026-04-17 — My Budgets page unreachable from within the app
**Mistake**: My Budgets (/my-budgets) was only linked from `waterfall.html`, which is an unrouted template. No active page linked to it — users could only reach it by knowing the URL.
**Fix**: Added My Budgets as a 4th row in the My Money sub-nav (Insights, Recurring, Analytics, Budgets) with a pie-chart icon. Moved the `border-bottom` from the Analytics row (previously last) to the now-separated Analytics row, and removed it from the new last item (Budgets).
**Rule**: Before shipping any new page, trace the full path from a bottom nav tab to that page. If no path exists, the page doesn't exist for users. Always verify navigation coverage in the active templates, not the static route list.

## 2026-04-17 — gold on inline text links persisting across welcome.html, upload.html, goal_detail.html, settings.html, unsubscribe.html
**Mistake**: After fixing gold inline links on my_money, my_goals, my_budgets, the same violation persisted on 5 more templates. Each new template was written independently without checking the established fix.
**Fix**: Changed all to `color: var(--text-secondary); text-decoration: underline; text-underline-offset: 2px;`.
**Rule**: The gold-on-inline-link grep (`grep -r "roman-gold" templates/ | grep "<a "`) must be part of every audit pass — run it as a command, not a visual check.

## 2026-04-17 — "Done" badge on welcome.html used gold instead of green
**Mistake**: Completed step badges in `welcome.html` used `color: var(--roman-gold); background: rgba(197,163,93,0.1)`. The equivalent badge in `plan.html` uses `color: rgba(72,187,120,0.8); background: rgba(72,187,120,0.1)` (green). Same semantic role, different templates, inconsistent color.
**Fix**: Changed to green to match plan.html. Also changed "Done" to "done" (normal case per copy standards).
**Rule**: Check completion/done badges across all templates for consistency. Green = success/done, not gold. Gold is for achievement/CTA, not status.

## 2026-04-17 — section-label CSS class used roman-gold globally for all structural dividers
**Mistake**: `.section-label` had `color: var(--roman-gold)` in the base CSS, making every section divider on every page appear in gold — a color reserved for CTAs, AI insights, goal highlights, and projections. "MONTHLY BREAKDOWN", "YOUR JOURNEY", "ALLOCATION BREAKDOWN" etc. all shouted in gold when they should recede.
**Fix**: Changed `.section-label` color to `var(--text-tertiary)`. AI card pulse-headers use inline styles, not this class, so they were unaffected. One CSS line corrected 20+ pages simultaneously.
**Rule**: Section dividers are structural elements that should recede — never apply a brand accent color to them. Hero hierarchy comes from size and contrast on the content, not on the label above it.

## 2026-04-17 — Heading/description size inversion on tool sections in plan.html
**Mistake**: "Can I afford this?", "Habit cost", and "What if?" section labels were `0.72rem text-tertiary` (smaller than their descriptions at `0.85rem text-secondary`). The eye read the description first, inverting the intended hierarchy.
**Fix**: Changed tool headings to `0.9rem text-primary font-weight:500`, descriptions to `0.78rem text-tertiary`. Heading always larger AND higher contrast than its supporting body copy.
**Rule**: Before shipping any label+description pair, verify: heading font-size > description font-size AND heading color contrast > description color contrast. Both must hold simultaneously.

## 2026-04-17 — glass-card wrapping teaser/summary sections on overview
**Mistake**: The "This month" spending snapshot on overview.html was wrapped in a `glass-card`. Per card rules, glass-card is only for discrete financial objects the user acts on as a whole. A spending summary with a "My money" link is a teaser to another page — must be bare.
**Fix**: Replaced `<div class="glass-card">` with a bare div using `padding-top: 20px; border-top: 0.5px solid rgba(255,255,255,0.06)` — same visual pattern as the pots section above it.
**Rule**: Before adding glass-card, ask "is this a discrete financial object the user acts on as a whole?" Summaries, teasers, and cross-page CTAs are always bare.

## 2026-04-17 — Gold on inline text links (my_money, my_goals, my_budgets)
**Mistake**: "or add manually" (my_money), "See your projection" (my_goals), and "Recurring payments" (my_budgets) all used `color: var(--roman-gold)`. Gold must only appear on filled primary CTA buttons, AI card pulse headers, goal progress bars, and on-track projections.
**Fix**: Changed all three to `color: var(--text-secondary)` with `text-decoration: underline` for discoverability on inline links.
**Rule**: Gold on an inline text link is always a violation. Inline links that are secondary/supporting actions use text-secondary + underline.

## 2026-04-17 — border-left gold accent on hero metric cards (insights, analytics)
**Mistake**: `border-left: 3px solid var(--roman-gold)` was used on "Predicted total" and "Total spending" cards to signal hierarchy. Gold on a structural/positional accent is misuse — gold is a semantic color, not a layout tool.
**Fix**: Removed the border-left. The `metric-value hero` class already establishes hierarchy via larger font size — no colour accent needed.
**Rule**: Never use `--roman-gold` as a CSS layout tool (borders, backgrounds). Size and weight create hierarchy. Gold is a semantic signal, not a design flourish.

## 2026-04-17 — Gold fill on month progress bar (insights)
**Mistake**: The "Month progress" bar in insights.html used `background: var(--roman-gold)`. A time-based progress indicator is a neutral UI element — it shows time passing, not achievement. Gold implies achievement or "on track."
**Fix**: Changed to `background: rgba(255,255,255,0.18)` — a muted neutral fill.
**Rule**: Gold progress bar fills are ONLY for goal savings progress bars (the user's savings vs. their target). All other progress bars (time, month, budget consumption) use a neutral color.

## 2026-04-17 — "Surplus" label confusing in plan breakdown total row
**Mistake**: The total row at the bottom of the monthly breakdown was labeled "Surplus" in text-tertiary. Users couldn't understand why a "surplus" appeared at the bottom of a list of allocated pots — it sounded like leftover money rather than the total being allocated.
**Fix**: Renamed to "Total allocated" with text-secondary font-weight:500 on label and text-primary font-weight:600 on amount — clearly reads as a ledger total row.
**Rule**: Label financial summary rows to communicate what's happening, not the technical backend field name. "Surplus" is a calculation concept; "Total allocated" is what the user cares about.

## 2026-04-17 — New template pages not covered by ui-audit scope definition
**Mistake**: The ui-audit skill listed active routes but didn't include new routes added in the recent pull (companion, checkin, plan_reveal, plan_review, surplus_reveal, goal_chips). These were missed in the initial audit pass.
**Fix**: At the start of every audit, run `flask routes` (or equivalent) to list all active routes and compare against the audit scope list. Any route not in the list must be added.
**Rule**: Before running /ui-audit, always enumerate all app routes programmatically — never trust a static list in the skill file.

## 2026-04-17 — Emojis in new onboarding templates (goal_chips, plan_review)
**Mistake**: goal_chips.html used emojis both in chip labels (🏠 ✈️ 👶) and in goal-detail section headers ("🏠 House deposit — roughly how much?"). plan_review.html used pot-type icons (🛡️ 💳 🎉 🔄 🎯) in allocation cards.
**Fix**: Removed all emojis. Chip labels became plain text. Detail headers use plain copy with a colon instead of em dash ("House deposit: roughly how much?"). Plan review allocation cards use only the pot name.
**Rule**: Zero emojis everywhere — including onboarding flows and chip UI. Labels, detail headers, and allocation cards must be text-only.

## 2026-04-17 — Subagent Edit permission was blocked in session
**Mistake**: Two background agents (em dash fixer, template UI fixer) were dispatched but both had the Edit tool blocked — all their fixes were no-ops. The task appeared completed but no changes were made.
**Fix**: After any agent completes, always verify by reading the output file AND checking the actual files for the expected change. If agent was blocked, make the edits directly.
**Rule**: Never assume background agent edits succeeded — always read the output file and spot-check a key file before moving on.

## 2026-04-17 — Em dashes in goal detail section headers used em dash AND emoji together
**Mistake**: goal_chips.html detail headers had both an emoji and an em dash: "🏠 House deposit — roughly how much?" — two violations in one string.
**Fix**: "House deposit: roughly how much?" — no emoji, colon replaces em dash.
**Rule**: When fixing em dashes in templates, also scan for adjacent emojis in the same element — they often co-occur.

## 2026-04-17 — inline `text-transform: uppercase; letter-spacing` on section dividers in new templates
**Mistake**: plan_reveal.html, plan_review.html, checkin.html, plan.html all had inline `style="font-size: 0.65rem; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.06em;"` instead of `class="section-label"`. Each new template introduced the violation independently.
**Fix**: Replace all inline uppercase+letter-spacing combos with `class="section-label"` and a single remaining style attribute (e.g. margin-bottom only).
**Rule**: Any time a new template is written, the first thing to audit is whether section dividers use `class="section-label"` — never inline uppercase style.

## 2026-04-17 — Gold on neutral sub-total displays in factfind
**Mistake**: factfind.html used `color: var(--roman-gold)` on the "Subscriptions total" and "Other payments total" running totals — these are neutral calculated values, not projections on track, not AI insights, not primary CTAs.
**Fix**: Changed to `color: var(--text-primary)` on both span elements. Confirmed JS updates only .textContent so the color fix persists dynamically.
**Rule**: Running totals, subtotals, and calculated field displays are neutral informational values — always text-primary, never gold.

## 2026-04-17 — Settings forms lacked Cancel buttons
**Mistake**: The "Change email" and "Change password" forms inside Settings accordions had only a primary submit button. The edit rule requires: "Edit pages always have Save changes (primary) AND Cancel (secondary) — never primary alone."
**Fix**: Added Cancel buttons that call `toggleSettings(key)` to collapse the accordion without submitting. Wrapped both buttons in a flex row.
**Rule**: Any form inside an accordion or expandable panel needs a Cancel button that reverses the open action (closes the panel), not just a page navigation link.

<!-- Graduated 2026-04-12: all entries from the 2026-04-12 session moved to:
     - Universal design principles → ~/.claude/design-standards.md
     - Claro-specific dev rules → Fintrack/AGENTS.md
     - UX/product rules → memory/feedback_ui_quality_bar.md
-->
