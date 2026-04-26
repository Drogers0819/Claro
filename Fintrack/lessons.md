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

## Feature check icons in paywalls = green, not gold

Feature validation lists (checkmark Full financial plan, checkmark AI companion) use `stroke="var(--success)"`. Gold (`--roman-gold`) is reserved for: filled primary CTAs, AI card pulse headers, goal savings progress bars, projections on track. Confirming a feature is delivery/completion = green. Not achievement/brand = not gold.

**Applied**: companion.html paywall — 4 check icons changed from `var(--roman-gold)` to `var(--success)`.

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

## Empty progress bars — do not suppress in goal rows

An empty progress track (0% fill, e.g. birthday at £0.00 of £200.00) on a goal row is a valid, intentional state. It tells the user the goal exists and how much is left to save. Do NOT suppress the track or replace with "Not started" text. The empty grey track + amount labels below is the correct design.

**Ruled out**: Adding `{% if pot.current > 0 %}` guard or replacing with "Not started" text. Victoria objected and reverted both. The track renders even at zero. This was corrected twice in one session — do not attempt again.

---

## Double border — button + following subordinate copy

When a button is followed by a whisper/note/hint, the note must NOT have its own `border-top`. The button's wrapper already has the section separator above it. Two borders box the button in visually and make the note look like a separate section.

**Applied**: overview.html action_whisper wrapper — removed border-top + padding-top, kept margin-top: 10px only. Watch for this pattern recurring on other cards.

---

## Optical spacing vs numerical spacing — same value reads differently by context

Equal pixel values do not create equal optical spacing. A 22px gap after Cormorant Garamond italic at large size reads optically larger than a 22px gap after body-weight Inter, because the serif has more descending visual weight. Rule: reduce gap after heavy/display type by ~25-30% to achieve the same optical breathing room as body copy. Trust the eye, not the ruler.

**Applied**: overview.html whisper card — AI italic text to OVERALL PROGRESS section gap: 22px to 16px (optical balance fix).

---

## Icon alignment in two-line list items — flex-start, not center

When a list item has an icon + two-line text block (title + description), use `align-items: flex-start` on the flex container. `align-items: center` floats the icon between the two lines, which reads as unmoored. `flex-start` anchors the icon to the title (the primary action), which is the correct semantic and visual hierarchy.

**Applied**: life_checkin.html — all 8 choice-card items changed from `align-items: center` to `align-items: flex-start`.

---

## Onboarding/welcome screens — vertical centering, not top-dump

Single-purpose onboarding screens (welcome, plan reveal, etc.) where the user isn't scrolling should have their content vertically placed in the viewport, not top-aligned like a content page. Use `min-height: calc(100vh - 120px); display: flex; flex-direction: column; justify-content: center` on the content wrapper. Top-dumping makes the page feel abandoned at desktop widths.

**Applied**: welcome.html — changed from `padding-top: var(--sp-xl)` to flex centering with min-height.

---

## Brand lockup consistency — all pre-auth screens use icon + wordmark

Login and register were using a large (160-180px) standalone logo icon. After adding the horizontal lockup to the splash, that created inconsistency across pre-auth screens. Rule: all pre-auth screens use the icon + "Claro" wordmark side-by-side. Splash: 40px icon / 1.75rem text. Login/register: 28px icon / 1.3rem text. Scale for context but never use icon alone on these screens.

**Applied**: login.html, register.html — replaced large standalone icons with horizontal lockup.

---

## Logo PNG has significant transparent padding — compensate BOTH sides for centred lockups

`logo.png` is 636×334px. The visible icon circle only spans x=143 to x=436, leaving 143px transparent left and 200px transparent right. At rendered sizes:
- **40px height** (splash): element renders at 76.2px wide, visible circle = 35.1px, left transparent = 17.1px, right transparent = 24.0px
- **28px height** (login/register): element = 53.3px wide, right transparent = 16.8px

**Fix for inline lockups (icon + wordmark side by side)**:
- Compensate right strip with `margin-right: -Npx` so the wordmark sits at the intended gap from the visible icon
- Compensate left strip with `margin-left: -Npx` when the lockup is centred on screen — without it, the visual centre of (icon + wordmark) is shifted right of the container centre
- At 40px: `margin-left: -17px; margin-right: -20px` → lockup visually centres correctly
- At 28px (login/register): only `margin-right: -17px` needed — these are left-aligned, not centred

Do NOT just reduce gap — gap alone cannot close the transparent padding. Negative margin on the img is the right tool.

**Applied**: `.splash-logo { margin-left: -17px; margin-right: -20px }` in main.css; login.html + register.html img inline `margin-right: -17px` (left unchanged — left-aligned context).

---

## Nav/sidebar bg on dark gradient themes — keep transparent, do NOT add a flat colour

The body gradient cannot be approximated with a flat colour. Any flat value — even the dark terminus of the gradient — will look visibly different from the content area because the gradient shifts hue across the viewport. The only value that truly matches the content area is `transparent`, so the body gradient shows through the nav/sidebar identically.

`backdrop-filter: blur(10px)` on `.app-header` and `.sidebar` is sufficient to protect readability when content scrolls behind; the existing `border-bottom`/`border-right` at `0.5px solid var(--glass-border)` provides visual edge separation.

**Do not set `--sidebar-bg` on dark gradient themes** (racing-green, midnight-navy, oxford-saddle, amethyst, rosso, obsidian). Leave the root `--sidebar-bg: transparent` to apply. Only light themes and cobalt (which have a flat `--bg-primary`) need an explicit `--sidebar-bg`.

**Applied**: themes.css — removed all 6 dark gradient theme `--sidebar-bg` overrides.

---

## Page-header conditional overrides — always apply unconditionally when the same spacing is needed in both modes

When a `{% if condition %}style="..."{% endif %}` inline override only applies in one mode, edit mode falls through to the CSS default — which may be stale in the user's browser. Make the inline style unconditional if both modes need the same value. Version-string cache busting alone is not enough during an active session.

**Applied**: factfind.html `.page-header` — removed the `{% if not plan_wizard_complete %}` conditional so `margin-bottom: var(--sp-xl)` applies in both onboarding and edit modes.

---

## CSS `display` on a component overrides the HTML `hidden` attribute — always add a `[hidden]` guard

The HTML `hidden` attribute maps to `[hidden] { display: none }` in the UA stylesheet. Any explicit `display` value in your own CSS (e.g. `.pwa-install-banner { display: flex }`) has higher specificity and silently overrides it — the element stays visible even when `banner.hidden = true` in JS. The computed style returns the CSS value, not `none`, making this very hard to spot.

**Fix**: Always add `.component-name[hidden] { display: none !important }` alongside any component that uses `display` in CSS and `hidden` in JS.

**Applied**: `.pwa-install-banner[hidden] { display: none !important }` in base.html — banner was appearing on desktop despite `banner.hidden = true` because the flex rule won.

---
