# Claro (Fintrack) — Agent Rules

Project-specific rules for Claude working on this codebase. These are not design standards — they are Claro-specific patterns, gotchas, and architectural decisions.

---

## Dev environment

- Flask runs on **port 5002** (not the default 5000). Always use `http://localhost:5002`.
- Playwright screenshots use a separate cookie jar — log in via the browser tool, not the host browser session.

---

## Template status

These templates exist in `app/templates/` but are **NOT served by any route**. Do not edit them unless explicitly asked:

- `dashboard.html`
- `budgets.html`
- `goals.html`
- `simulator.html`
- `waterfall.html`

Active templates: `overview`, `my_money`, `my_goals`, `plan`, `my_budgets`, `settings`, `factfind`, `upload`, `add_transaction`, `add_goal`, `edit_goal`, `goal_detail`, `scenario`, `analytics`, `insights`, `recurring`, `welcome`, `login`, `register`, `unsubscribe`.

---

## Navigation active states

- The Settings tab active state must only match `pages.settings`. **Never include `pages.factfind`** — factfind is a standalone onboarding flow, not a Settings sub-page. Including it causes the Settings tab to illuminate when users are on factfind.
- Bottom nav has 6 tabs: Overview, Money, Check-in, Goals, Companion, Plan.

---

## Mobile avatar (`.mobile-settings-btn`)

- Defined in `base.html` as a global fixed element: `position: fixed; top: max(14px, calc(env(safe-area-inset-top) + 8px)); right: 16px; z-index: 500`.
- `viewport-fit=cover` is set in the viewport meta, so `env(safe-area-inset-top)` is non-zero on notched iPhones (typically 47–59px). The avatar and main-content top padding both use the same safe-area-aware calc so they stay aligned on notched and non-notched devices.
- Main content top padding: `max(16px, calc(env(safe-area-inset-top) + 10px))`. Do not add `padding-top` to page-header or this alignment breaks.
- Avatar bottom edge: ~50px (no notch) / ~77px (notch). To push a sub-row (count + CTA) below the avatar zone: increase `margin-bottom` on the page-header. Never use `padding-top` on the header (breaks alignment) or `padding-right` on the sub-row (misaligns right edge with surrounding content).
- Pages with a back-link (`← Money`, `← Goals`) above the header get natural clearance automatically.

---

## Post-action routing

| Action | Routes to |
|---|---|
| Add transaction | `my_money` |
| Add goal | `my_goals` |
| Factfind save | `overview` |
| Upload statement | stays on `upload` (show the wow moment) |
| Edit goal save | `my_goals` |
| Delete budget | stays on `my_budgets` |

---

## CSS rules — forbidden patterns

- **`[style*="..."]` attribute substring selectors**: never use. They silently match every element with that inline style fragment across the entire codebase. Example of what broke: `[style*="display: flex"][style*="gap: 12px"] { flex-direction: column }` forced column layout on every flex row with gap:12px, including the My Money sub-nav. Use CSS classes or explicit inline styles instead.
- **Duplicate CSS class definitions**: if a class is defined twice in main.css, the second wins and silently overrides the first. Before adding a new class block, grep first. Root cause of all empty-state centering inconsistencies was a second `.empty-state` definition with `text-align: center; padding: 40px 20px` overriding the correct first definition.

---

## JavaScript — SVG elements

- SVG elements expose `className` as a read-only `SVGAnimatedString`, not a writable `DOMString`.
- **Never**: `svgElement.className = 'some-class'` — throws TypeError.
- **Always**: `svgElement.setAttribute('class', 'some-class')` or `svgElement.classList.add('some-class')`.

---

## Currency formatting (Jinja2)

- **Always**: `"{:,.2f}".format(value)` — includes thousands comma separator.
- **Never**: `"%.2f" | format(value)` — no comma, produces "£1471.68" instead of "£1,471.68".
- Negative amounts: `−£{{ "{:,.2f}".format(val|abs) }}` — Unicode minus (U+2212) before `£`, never `£-X.XX`.

---

## Auth pages

`glass-card` is acceptable on login and register pages. These pages have no app chrome (no sidebar, no bottom nav), so the form needs a visual container. This is the **only** exception to the no-card-on-forms rule.

---

## Button hierarchy — one primary per page

- Exactly **one** `btn-primary` (gold filled) per page. Never two simultaneously.
- Inline save/edit actions (e.g. inline budget limit save) → `btn-secondary`.
- Calculator/tool actions that don't submit to the server → `btn-secondary`.
- Forms that create or commit data → `btn-primary`.
- Post-action navigational buttons ("View full plan") → `btn-secondary`.

---

## Colour semantics

- **Gold (`--roman-gold`)** only on: primary CTAs, goal highlights, AI insight headers, savings progress bars, projections on track.
- Gold **not** on: neutral informational display values, "available for goals", tier labels, avatar backgrounds.
- **Green (`--success`)** only on actual monetary gains — never on opportunity costs, potential savings, or lost growth projections.
- **Avatar / identity**: must use neutral glass — `rgba(255,255,255,0.07)` dark, `rgba(0,0,0,0.05)` light. Light-theme overrides live in `themes.css` under each `body.theme-*` selector.

---

## Theme-aware CSS tokens

- **`--progress-track`**: dark fallback defined in `:root` as `rgba(255,255,255,0.1)`. Light themes override in `body.theme-*` selector in `themes.css` as `rgba(0,0,0,0.08)`.
- Pattern for any luminance-dependent value: `:root` = dark default, `body.theme-*` = light override. Never hardcode `rgba(255,255,255,0.1)` directly in templates or component CSS.

---

## Card usage

- `glass-card` **only** on: discrete financial objects the user acts on as a whole — goal cards, budget rows, transaction lists, metric grids, recurring item lists.
- `gold-card` **only** on: AI insight blocks.
- Forms → bare on page background (except login/register).
- Empty states, paywall teasers, cross-page CTAs → bare.
- Section separators → spacing + typography only, not containers.

---

## Profile popover (sidebar)

- Sign-out lives in the Claude-style profile popover — never as a standalone sidebar button.
- Trigger: `.sidebar-profile-trigger` button in `.sidebar-footer { position: relative }`.
- Panel: `.profile-popover` with `position: absolute; bottom: calc(100% + 8px); left: 0; right: 0` — floats above the trigger.
- JS pattern: `stopPropagation()` on trigger click; `document.click` closes if outside; `Escape` key closes and returns focus.

---

## Navigation chevron rule

- `>` (chevron-right) icon on a link/button = navigates away from the current page to a different route.
- Form submit buttons = no icon.
- Secondary tool/calculator actions = no icon.
- Consistent across all pages — do not mix icon/no-icon on semantically equivalent actions.

---

## Bottom nav (mobile)

- **6 tabs**: Overview, Money, Check-in, Goals, Companion, Plan.

---

## Registration routing

- New users after registration → `/welcome` (trial framing + 3-step onboarding overview).
- **Not** `/factfind` — users need context before entering the financial profile form.

---

## Copy rules

- Zero em dashes (—) anywhere — in templates AND service/route files. Use commas, full stops, or `·` midpoints.
- Button labels: present-tense verb ("Set budget", "Record transaction").
- Status labels: normal case ("on track", "over budget") — never "ON TRACK".
- No parenthetical amounts generated by backend (e.g. `(£250/month)` inline).
- No ML confidence scores or model internals exposed.

---

## Italic rule

- `font-style: italic` only inside `gold-card` blocks (AI insight/prediction/summary copy).
- Not on: instruction text, supporting sub-headings, glass-card body copy, hints, or footer notes (use `var(--text-tertiary)` + small font-size instead).
- Acceptable exception: very short tertiary-coloured UI hints (e.g. factfind helper notes, upload hints) where italic signals "this is supplementary context, not a field label."

---

## Progress bar component

- Always use the `.progress-track` CSS class for the container — never inline `height`, `background`, `border-radius`, `overflow` that duplicates the class.
- Use `.progress-fill` for the inner bar — add `background` inline only when the colour is semantic (gold for goals, custom colour for analytics categories, muted for calendar/time progress).
- Height overrides via inline `style="height: Npx"` are allowed when the bar has different semantic weight (e.g. 4px for secondary budget rows, 8px for hero goal detail, 3px for decorative inline bars).
- Do not use `opacity` on `.progress-fill` — use a lower-alpha colour value instead.

---

## Status badge colour map

| Status | Badge class |
|---|---|
| On track, no action needed | `badge-default` |
| Healthy (positive health indicator) | `badge-success` |
| Below average spending (good) | `badge-success` |
| Tight / caution | `badge-warning` |
| Above average / over budget / danger | `badge-danger` |
| Neutral count / tier label | `badge-default` |

---

## Onboarding nudge (factfind incomplete banner)

- Always positioned **immediately after the `page-header` block**, before any content cards or sections.
- Never sandwiched between content sections — it must be the first thing a user sees on the page.
- Appears on: `overview`, `my_money`, `my_budgets`, `settings`.
- Component: tappable row, `background: rgba(197,163,93,0.07)`, gold border, gold info icon, chevron right.

---

## Empty state rules

Two tiers — use the right one based on context:

**Full-page empty states** (the page has nothing else to show — Goals with no goals, Check-in locked, Companion paywall, 404, 500): use `.empty-page-center` class. Horizontally + vertically centred, centred text, max-width 280px on `<p>` elements.

**Section-level empty states** (within a page that has other content — Overview "No transactions yet", Plan "Build your plan" with calculators below): use `padding: 8px 0 32px`, left-aligned.

Both tiers require the same anatomy:
- Headline: `font-size: 0.95rem; color: var(--text-primary); font-weight: 500; margin-bottom: 8px`
- Subtext: `font-size: 0.8rem; color: var(--text-tertiary); line-height: 1.6; margin-bottom: 20px`
- CTA: `btn-primary btn-sm`
- Never wrap in a card or container.
- Subtext answers: why is this empty + what should the user do.

---

## Form patterns

- **Cancel button rule**: Every form that creates or edits data must have Cancel next to the primary submit button. Cancel is always a plain text element styled as `font-size: 0.82rem; color: var(--text-tertiary); text-decoration: none;` in a flex container with `gap: 14px`. For `<a>` elements use anchor tag; for inline accordion forms use `<button type="button">` with matching inline styles. Never use `btn-secondary` for Cancel.
- **Form label rule**: Every `<input>` must have an associated `<label class="form-label">`. For ledger-style inputs (checkin, inline edit), add `for`/`id` pair even when the label is visually part of the row.
- **Button sizing rule**: Submit buttons on full-page standalone forms use `.btn-primary` (standard size) — never `.btn-sm`. Exception: compact inline sub-forms inside accordions (e.g. settings change-email, change-password panels) may use `.btn-primary.btn-sm` because the compact context demands it. Calculator/tool actions that don't commit data use `.btn-secondary.btn-sm`.
- **Placeholder format**: Number inputs use `"e.g. 250"` or `"e.g. 1700"` format. Text inputs use descriptive examples.
- **Accordion form sub-headers**: Do not add an inner sub-header repeating the accordion's own title. The accordion trigger IS the header. If a panel contains only one form, go straight to the fields.
- **Settings Account accordion**: Account and Security/Password are merged into a single "Account" accordion. Inside, use inline-edit rows — read-only by default, one row expands at a time via `toggleEdit(field)`. Never show forms by default. Three editable fields: Name (pre-filled with current value), Email (empty input, confirm password required), Password (3-field change form). Member since is read-only. Backend route `update_account` handles `change_name`, `change_email`, `change_password` form types.

---

## Mobile-specific patterns

- **Sign out**: Only available via sidebar profile popover on desktop. On mobile (≤768px), settings.html shows a sign-out button at the bottom of the page using `.mobile-only` class. Desktop keeps it in popover only.
- **`.mobile-only`**: `display: none` by default, `display: block` at ≤768px.
- **`.desktop-only`**: `display: block` by default, `display: none` at ≤768px.

---

## Popover colour tokens

- `--popover-bg` is NOT neutral `#1c1c1e` — each dark theme has its own hue-matched elevated surface:
  - `theme-racing-green`: `#101e15`
  - `theme-midnight-navy`: `#0d1620`
  - `theme-oxford-saddle`: `#1a1008`
  - `theme-amethyst`: `#14091e`
  - `theme-rosso`: `#1a0808`
  - `theme-cobalt`: `#0c1220`
- Light themes use their respective solid surface colours.
- Applies to: profile popover, custom select dropdown, flatpickr calendar.
