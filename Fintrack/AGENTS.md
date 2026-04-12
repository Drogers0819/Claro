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
- Bottom nav has 5 tabs. Do not add a 6th — the design was explicitly rejected.

---

## Mobile avatar (`.mobile-settings-btn`)

- Defined in `base.html` as a global fixed element: `position: fixed; top: 14px; right: 16px; z-index: 500`.
- This puts its bottom edge at ~50px. Main content starts at `padding-top: 16px`, so the page-header `h1` at ~16px naturally aligns with the avatar at `top: 14px` — they share the same baseline. Do not add `padding-top` to page-header or this alignment breaks.
- To push a sub-row (count + CTA) below the avatar zone: increase `margin-bottom` on the page-header. Never use `padding-top` on the header (breaks alignment) or `padding-right` on the sub-row (misaligns right edge with surrounding content).
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
