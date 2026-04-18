# Claro (Fintrack) — Agent Rules

Project-specific rules for Claude working on this codebase. These are not design standards — they are Claro-specific patterns, gotchas, and architectural decisions.

---

## MANDATORY: Read DESIGN-SYSTEM.md before writing any UI

Before writing or editing any template, read `DESIGN-SYSTEM.md`. It defines every visual pattern: typography, colour, cards, spacing, buttons, forms, icons, navigation, data display, animation. AGENTS.md handles dev/routing rules. DESIGN-SYSTEM.md handles visual decisions.

---

## MANDATORY: Playwright verification after every UI change

**After any change to a template or CSS — run Playwright and screenshot before marking the task done.**

This is not optional. Do not say "done" without Playwright verification. Static code analysis is not sufficient.

Steps:
1. Navigate to the affected page(s) via Playwright MCP
2. Screenshot at 375px and 1440px minimum
3. Review the screenshots visually — check hierarchy, alignment, card usage, colour, spacing
4. Fix anything that looks wrong
5. Then mark done

The server runs on **port 5002**. Log in via Playwright browser (separate cookie jar from host browser).

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

Active templates: `overview`, `my_money`, `my_goals`, `plan`, `my_budgets`, `settings`, `factfind`, `surplus_reveal`, `goal_chips`, `plan_reveal`, `plan_review`, `upload`, `add_transaction`, `add_goal`, `edit_goal`, `goal_detail`, `scenario`, `analytics`, `insights`, `recurring`, `checkin`, `companion`, `welcome`, `login`, `register`, `unsubscribe`.

---

## Navigation active states

- The Settings tab active state must only match `pages.settings`. **Never include `pages.factfind`** — factfind is a standalone onboarding flow, not a Settings sub-page. Including it causes the Settings tab to illuminate when users are on factfind.
- Bottom nav has 5 tabs: Overview, Check-in, Goals, Companion, Plan.

---

## Mobile header bar

- **Layout**: `.mobile-header-bar` is a fixed bar (52px + safe area), `justify-content: space-between`, `padding: 0 16px`. Logo on LEFT, avatar on RIGHT.
- **Logo**: `<a class="mobile-logo">` with `<img style="height:24px;width:auto;">`. PNG is landscape (636×334) — set height only, let width auto. Do NOT match the avatar circle height (36px): the logo mark is optically denser. 24px in a 52px bar gives 14px clear space each side. The avatar letter inside its 36px circle reads much smaller — do not use the circle container as the optical reference.
- **Avatar** (`.mobile-settings-btn`): `position: static` inside the bar on mobile. `viewport-fit=cover` is set in the viewport meta — use `env(safe-area-inset-top)` aware positioning for the bar itself.
- Main content top padding: `max(16px, calc(env(safe-area-inset-top) + 10px))`. Do not add `padding-top` to page-header or this alignment breaks.
- Avatar bottom edge: ~50px (no notch) / ~77px (notch). To push a sub-row (count + CTA) below the avatar zone: increase `margin-bottom` on the page-header. Never use `padding-top` on the header (breaks alignment) or `padding-right` on the sub-row (misaligns right edge with surrounding content).
- Pages with a back-link (`← Goals` etc.) above the header get natural clearance automatically.

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

## Button icon rule

- All CTA buttons and links use **Lucide SVG icons** inline — never Unicode characters (`→`, `←`, `▶`).
- Forward CTAs: Lucide `chevron-right` (`<path d="M9 18l6-6-6-6"/>`) at `width="14" height="14"`.
- Back links: Lucide `chevron-left` (`<path d="m15 18-6-6 6-6"/>`) at `width="10" height="10"`.
- Button layout: `display: flex; align-items: center; justify-content: center; gap: 8px;` — icon is the last child.
- JS-generated button icons: use `document.createElementNS('http://www.w3.org/2000/svg', 'svg')` — never `innerHTML` or `textContent` with SVG strings.

---

## Onboarding wizard

- The 4-step wizard is: `factfind` (step 1) → `surplus_reveal` (step 2) → `goal_chips` (step 3) → `plan_reveal` (step 4) → `plan_review` → `overview`.
- **One progress system**: step bars live only in the wizard pages. Do not add a second progress tracker (e.g. a 2-step checklist on overview or welcome) — competing systems confuse users.
- Step bar layout: `[chevron Back] [bars flex:1] [Step X of 4]` — Back on the LEFT, counter on the RIGHT.
- AI whisper (gold-card) placement: **only on `plan_review`** (before the allocation breakdown). Never on `plan_reveal` — reveal moments are clean.
- The overview no-goals nudge links to `/goals/choose` (wizard), not `/add-goal` (manual form).

---

## Navigation chevron rule

- `>` (chevron-right) icon on a link/button = navigates away from the current page to a different route.
- Form submit buttons = no icon.
- Secondary tool/calculator actions = no icon.
- Consistent across all pages — do not mix icon/no-icon on semantically equivalent actions.

---

## Bottom nav (mobile)

- **5 tabs**: Overview, Check-in, Goals, Companion, Plan. (Money tab was removed in the nav restructure.)

---

## Registration routing

- New users after registration → `/factfind` directly (step 1 of 4 onboarding wizard).
- The `/welcome` page still exists and is reachable but is **not** part of the new-user flow.
- Do not re-add the welcome redirect — the wizard handles full onboarding including goal setup.

---

## UI audit — what to check on every page

Run these checks before marking any UI change done. Static analysis is not enough — use Playwright for visual verification.

**Alignment**
- Page headers (`h1`, `.page-header`) are always **left-aligned**. No centering exceptions, not even for "reveal moments" or emotional milestones.
- All body text, labels, and form fields are left-aligned. `text-align: center` is only valid for footer disclaimer notes (e.g. guidance/legal copy below a CTA).

**Section order**
- Standard page order: back-link (if applicable) → step bar (onboarding only) → page-header → onboarding nudge (if factfind incomplete) → primary content → secondary/explanatory content → CTA.
- Never put explanatory methodology text above financial data. Data first, explanation below.

**Card usage**
- `glass-card` only on discrete financial objects the user acts on as a whole (goal cards, budget rows, transaction lists, metric grids). See Card usage section.
- Analysis summaries, plan overview numbers, methodology text, and empty states must be **bare** (no card wrapper).
- If content explains HOW something works rather than WHAT the user's data is, it does not get a card.

**Text hierarchy**
- Section labels: `.section-label` class — uppercase, letter-spaced, `var(--text-tertiary)`, small size.
- Primary data values: `var(--text-primary)`, `font-weight: 500` or `600`.
- Supporting copy: `var(--text-secondary)`, `0.8rem–0.85rem`.
- Tertiary/helper copy: `var(--text-tertiary)`, `0.75rem–0.78rem`.
- Never use `font-style: italic` outside `gold-card` blocks.
- Never uppercase body copy or data values — only section-label elements.

**Colour consistency**
- Gold (`--roman-gold`) is NOT a general highlight colour. See Colour semantics section.
- All gold in templates must flow from `var(--roman-gold)` or `var(--roman-gold-dim)` — never hardcoded `rgba(197,163,93,...)`.
- Do not use `--success` (green) for anything that is not a real monetary gain.
- Step bars in onboarding wizard: `rgba(255,255,255,0.25)` filled, `rgba(255,255,255,0.08)` unfilled. Never gold.

**Icons and emoji**
- Zero emojis anywhere in templates OR service/route files.
- All icons are inline Lucide SVGs. Icon names in service files must match the Jinja2 mapping in `overview.html`. When adding new icon names, update both the service AND the template mapping simultaneously.

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
