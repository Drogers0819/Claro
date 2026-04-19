# Claro — Session Lessons

Learnings that are project- or session-specific and not yet graduated to AGENTS.md or design-standards.md.

---

## Round 4 — 2026-04-19

### Shadow palette — hardcoded values break light themes

All floating UI (popover, custom select, flatpickr, toast) had hardcoded `rgba(0,0,0,0.45)` shadows. On dark themes this reads as depth. On light themes (Ivory, Pearl, Sandstone, Sage, Lavender, Mist) the same value creates a harsh black halo — it looks like a bug, not a shadow.

**Fix applied**: Introduced 3 CSS custom property shadow tokens in `:root` (`--shadow-float`, `--shadow-float-lg`, `--shadow-toast`). All 6 light theme body classes override them to `rgba(0,0,0,0.08–0.10)` in a single grouped selector in `themes.css`. Dark themes inherit the `:root` deep values unchanged.

**Rule**: When adding any new floating surface, always use `box-shadow: var(--shadow-float)` — never hardcode RGBA. The token adapts across all 9 themes automatically.

---

### Chart x-axis label density — short month abbreviations + maxTicksLimit: 4

Long month names ("August 2026") cause label overlap at 375px on multi-year projections. Root cause: 5 ticks × ~56px each = 280px on a 310px chart.

**Fix applied**: Changed `formatDate()` to 3-letter abbreviations (`Jan Feb Mar...`). Set `maxTicksLimit: 4` + `autoSkipPadding: 16`. Result: "Apr 2026 · Jun 2035 · Aug 2044 · Oct 2053" — no overlap at any breakpoint.

---

### Chart legend breathing room — afterFit +24, not +16

Chart.js `afterFit(legend)` at `+16` still left legends visually close to the plot area. `+24` gives the right breathing room. Apply to all charts in simulator.js.

---

### UX debt — "Your Pots" navigation (accepted, documented)

Overview shows "YOUR POTS" label but tapping a pot navigates to `goal_detail.html` (the simulator page) with a "← Goals" back link — not "← Overview". Users who arrived from Overview are dropped on a page whose back link takes them to Goals, not where they came from. This is a label mismatch + wrong context back link.

**Correct fix** (requires backend, out of scope): Pass `?from=overview` query param and conditionally render "← Overview" vs "← Goals" back link. Or rename "Your Pots" to "Your Goals" across Overview.

**Current state**: Accepted UX debt. User recovery: bottom nav Goals tab → then Overview tab. Costs 2 extra taps.

---

### Slider readout — feedback indicator, not hero metric

The goal detail contribution slider showed its current value as `class="metric-value sm"` (1.3rem). A live slider readout is feedback, not a primary metric. 1.3rem created false hierarchy against the projected arrival date (also 1.3rem).

**Fix applied**: Inline `font-size: 1.05rem; font-family: var(--font-sans); font-variant-numeric: tabular-nums; color: var(--text-primary)`.

---

### Double border anti-pattern — button wrapper + whisper wrapper

The "View full plan" button had `border-top` on its own wrapper AND `border-top` on the whisper text wrapper below — creating a visible stroke both above AND below the button. This boxed the button in like a section and made the whisper look like a separate panel.

**Fix applied**: Removed `border-top` and `padding-top` from the whisper wrapper. Kept `margin-top: 10px` only. One clear separator above the button, whisper flows as subordinate context below.

**Rule**: When a button is followed by subordinate copy (a whisper, a note, a hint), the copy should NOT have its own top border. Only the button's section separator matters.

---

### CSS custom property inheritance — body vs :root

CSS custom properties defined on `body.theme-*` override `:root` for all descendants. `getComputedStyle(document.documentElement)` reads `:root` values — use `getComputedStyle(document.body)` to read the active theme's overrides. This matters when debugging token values in Playwright.

---

### [style*="..."] attribute substring selectors — never use

CSS attribute substring selectors like `[style*="font-size: 2.8rem"]` silently match any element in the entire DOM with that string anywhere in its inline style. They caused layout corruption in previous sessions (forced column layout on every flex row with a specific gap value). All removed in Round 3.

**Rule**: Use CSS classes or data-attributes for targeting. Never style via inline-style string matching.

---
