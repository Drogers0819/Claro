# Claro — Session Lessons

Staging area. Rules here are new enough that they need another session's worth of validation before graduating to AGENTS.md or DESIGN-SYSTEM.md. Once a rule has been applied consistently (or is blindingly obvious), graduate it and delete from here.

---


## CSS custom property inheritance — always re-declare `--ai-whisper` in fully-custom dark themes

When a theme defines its own `--roman-gold` override (e.g. cobalt uses `#63B3ED`), it must also explicitly re-declare `--ai-whisper: var(--roman-gold)` inside that theme block. Without it, `--ai-whisper` resolves against `:root`'s `--roman-gold` value at cascade time, not the theme's override — producing the wrong colour. This silently worked for all themes that inherit `:root` gold, but broke for cobalt. Fix: add `--ai-whisper: var(--roman-gold);` anywhere `--roman-gold` is redefined to a non-gold value.

**Applied**: `.theme-cobalt` in `themes.css` — added `--ai-whisper: var(--roman-gold)` after the cobalt `--roman-gold: #63B3ED` declaration. Verified whisper text now shows electric blue on cobalt.

---

## Slider readout — always a feedback indicator, never a hero metric

Live interactive readouts (slider values, calculator inputs) should be styled at ~1rem, not `metric-value sm` (1.3rem). 1.3rem creates false hierarchy against the primary metric on the same card.

**Applied**: goal_detail.html slider amount — inline `font-size: 1.05rem; font-variant-numeric: tabular-nums`. Needs to hold through future goal detail changes.

---

## Em-dash audit scope includes routes files, not just service files

When grepping for `—` in backend Python, the scope is `app/routes/*.py` AND `app/services/*.py`. Flash messages in route handlers (e.g. `flash("Great — your plan stays on track.")`) are user-facing copy and carry the same zero-tolerance rule as templates. "Service files only" misses an entire category.

**Applied**: `page_routes.py` — 3 flash messages in the life check-in POST handler. Fixed `—` → `.` in all three.

---

## Badges inline rgba bypass the theme system — always use badge classes

Never hardcode `style="background: rgba(245,158,11,0.12); color: rgba(245,158,11,0.85)"` on a badge. Use `class="badge badge-warning"` (or success/danger/default). The CSS classes use CSS tokens (`var(--roman-gold)`, `var(--roman-gold-dim)`) which are properly overridden per theme in themes.css. Hardcoded rgba values are fixed regardless of theme — they break contrast on Paper, Cobalt, and light themes.

**Applied**: Overview "Setting up" badge — removed inline rgba, replaced with `class="badge badge-warning"`.

---

## Feature check icons in paywalls = green, not gold

Feature validation lists (✓ Full financial plan, ✓ AI companion) use `stroke="var(--success)"`. Gold (`--roman-gold`) is reserved for: filled primary CTAs, AI card pulse headers, goal savings progress bars, projections on track. Confirming a feature is delivery/completion = green. Not achievement/brand = not gold.

**Applied**: companion.html paywall — 4 check icons changed from `var(--roman-gold)` → `var(--success)`.

---

## Nav active state must propagate `?from=` context — both sides

When a sub-page carries `?from=X`, the nav active state must reflect X, not the endpoint's natural parent. Required changes are bilateral: (a) remove the arrival page from the "natural parent" condition, AND (b) add it explicitly to the "source" tab. Doing only one side leaves no tab active.

Rules as of April 2026:
- `?from=plan` → Plan tab active (goal_detail + edit_goal)
- `?from=overview` → Overview tab active (goal_detail)
- anything else → Goals tab active (goal_detail, my_goals, add_goal, edit_goal)

**Applied**: base.html — Goals condition adds `and request.args.get('from') != 'overview'`; Overview condition adds `or (request.endpoint == 'pages.goal_detail' and request.args.get('from') == 'overview')`.

---

## Gold card bg — perceptual contrast, not absolute opacity

Gold card bg opacity must be calibrated against the actual page background hue, not matched numerically across themes. A 15% gold tint on a near-black page reads very differently to 15% on a warm-brown page (Oxford Saddle) — the latter looks muddy.

Calibrated values as of April 2026 (all in `themes.css` as explicit `.gold-card` overrides):
- Racing Green: 10% bg, 25% border (was 15% — too heavy)
- Oxford Saddle: 9% bg, 22% border (warm page needs lower)
- Midnight Navy: 12% bg, 28% border (cold page, needs explicit override)
- Obsidian: 10% bg, 25% border (pure-black page, fallback was 5% — too subtle)
- Rosso: 13% bg, 30% border
- Cobalt: 10% bg, 22% border
- Amethyst: 13% bg, 30% border
- Light themes: 10-11% bg, 30-32% border (explicit class overrides per theme)

Rule: never rely on `--roman-gold-dim` token alone for gold card bg on themes where that token is set for other purposes. Always use explicit `.theme-X .gold-card` override.

---

## Empty progress bars are a missing state — suppress or replace

A progress bar with zero fill (£0.00 of £200.00, 0% width) looks like a UI glitch, not a valid state. On goal rows where `pot.current == 0`, either suppress the progress bar entirely OR replace with a "Not started" label. Never render a completely empty track.

**Not yet applied.** Flag for next UI audit pass.

---

## Double border — button + following subordinate copy

When a button is followed by a whisper/note/hint, the note must NOT have its own `border-top`. The button's wrapper already has the section separator above it. Two borders box the button in visually and make the note look like a separate section.

**Applied**: overview.html action_whisper wrapper — removed border-top + padding-top, kept margin-top: 10px only. Watch for this pattern recurring on other cards.

---

## Optical spacing vs numerical spacing — same value reads differently by context

Equal pixel values do not create equal optical spacing. A 22px gap after Cormorant Garamond italic at large size reads optically larger than a 22px gap after body-weight Inter, because the serif has more descending visual weight. Rule: reduce gap after heavy/display type by ~25-30% to achieve the same optical breathing room as body copy. Trust the eye, not the ruler.

**Applied**: overview.html whisper card — AI italic text → OVERALL PROGRESS section gap: 22px → 16px (optical balance fix).

---

## Spacing token system — use `--sp-*` not `--space-*`

The canonical spacing scale in `:root` is `--sp-xs: 4px; --sp-sm: 8px; --sp-md: 16px; --sp-lg: 24px; --sp-xl: 32px; --sp-2xl: 48px;`. The old `--space-*` system (8px base, different scale) was removed. Always use `--sp-*` for new spacing declarations.

**Applied**: main.css — removed duplicate `--space-xs/sm/md/lg/xl/2xl` block. `--sp-md` applied to `.page-header margin-bottom` globally.

---

## Progress track on light themes — minimum 12% opacity

`rgba(0,0,0,0.08)` on a white card background is ~4.5% contrast difference — optically invisible. The minimum for an empty track to register as an intentional state (not a glitch) on Paper/Ivory/Pearl/Sage is `rgba(0,0,0,0.12)`. Below this, users cannot tell if the component rendered correctly.

**Applied**: themes.css — all 4 light theme `--progress-track` values bumped from 0.08 → 0.12.

---

## Icon alignment in two-line list items — flex-start, not center

When a list item has an icon + two-line text block (title + description), use `align-items: flex-start` on the flex container. `align-items: center` floats the icon between the two lines, which reads as unmoored. `flex-start` anchors the icon to the title (the primary action), which is the correct semantic and visual hierarchy.

**Applied**: life_checkin.html — all 8 choice-card items changed from `align-items: center` to `align-items: flex-start`.

---

## Hardcoded hex values in conditional Jinja expressions bypass theme tokens

Patterns like `color: {% if x == 'medium' %}#D4A84B{% else %}#CC6B5A{% endif %}` look dynamic but are hardcoded — they break on every non-default theme. Always use CSS token variables inside Jinja conditionals: `var(--roman-gold)` for caution/medium severity, `var(--danger)` for high/error severity.

**Applied**: withdraw.html — severity colour conditions + shortfall callout replaced with `var(--roman-gold)`, `var(--danger)`, `var(--danger-bg)`, `var(--danger-border)`.

---
