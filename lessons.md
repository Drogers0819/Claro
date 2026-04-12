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

## 2026-04-12 — `--text-tertiary` at 0.3 opacity fails WCAG contrast (systematic)
**Mistake**: `--text-tertiary: rgba(255,255,255,0.3)` renders at ~2.5:1 contrast on the dark racing-green background. Used everywhere for whisper/supporting text across all templates. WCAG AA minimum is 4.5:1.
**Fix**: Raised `--text-tertiary` to 0.5 and `--text-secondary` to 0.65 in main.css (root defaults) and in all dark/light theme overrides in themes.css. Token-level fix propagates to all ~40 inline uses automatically without touching templates.
**Rule**: After defining any text colour token, calculate actual contrast against the darkest bg in the theme before shipping. A token that fails contrast fails everywhere it's used.

## 2026-04-12 — Missing `colour` key in analytics trends dict
**Mistake**: The analytics route's `trends.append()` dict included `"icon": r.icon` but not `"colour": r.colour` — even though the query already joined Category and selected `Category.colour`. Template used `t.colour if t.colour else 'var(--text-tertiary)'`, so every "Compared to last month" icon silently fell back to dim gray. The inconsistency with the "Spending by category" section (which did pass colour) was visible but I initially dismissed it incorrectly.
**Fix**: Added `"colour": r.colour` to the trends dict.
**Rule**: When a section renders identically-structured data in two places, verify both code paths include all the same keys. Never dismiss a visual inconsistency without actually reading the data dict that feeds it.

## 2026-04-12 — Em dashes in static copy (systematic)
**Mistake**: `—` appeared in plan.html subtext (`— coffee, subscriptions, takeaways —`) and scenario.html AI card (`after rent and bills —`). Em dashes are the single most recognisable AI writing tell.
**Fix**: Rewrite to remove em dashes entirely. Use commas, full stops, or `·` midpoints for inline separators. Never use `—` in any copy.
**Rule**: Grep for `—` before calling any copy done. Zero tolerance, no exceptions, no "it's just a separator."

## 2026-04-12 — AI slop backend copy: parentheticals and hedge language
**Mistake**: `simulator_service.py` generated `"Redirecting even half (£2,500/month) would grow..."` — formulaic parenthetical. And `"This change doesn't significantly affect your goal timelines."` — hedge language that says nothing.
**Fix**: `"Put £2,500 of that into savings each month and it becomes £X in 10 years."` / `"Your goal dates stay the same with these numbers."` — direct, specific, no hedging.
**Rule**: Backend-generated copy must be audited the same as template copy. Parentheticals, hedge phrases ("doesn't significantly", "may vary"), and formulaic structures are AI tells regardless of where they live.

## 2026-04-12 — Button height mismatch (btn-primary vs btn-secondary)
**Mistake**: `btn-primary` had `border: none`, `btn-secondary` had `border: 1px solid`. Without `box-sizing: border-box`, the border adds 2px to rendered height — visually mismatched at every btn-sm instance in the app.
**Fix**: Added `border: 1px solid transparent` to `btn-primary` and `box-sizing: border-box` to all button base styles.
**Rule**: When introducing multiple button variants, ensure all share identical box model. `border: 1px solid transparent` on filled buttons, `border: 1px solid color` on outlined — same height, same padding, different fill.

## 2026-04-12 — Form field / native select height inconsistency
**Mistake**: Native `<select class="form-select">` rendered taller than `<input class="form-input">` due to browser-injected dropdown arrow padding and no `appearance: none` normalization.
**Fix**: Added `appearance: none; -webkit-appearance: none` to `.form-select`, replaced native arrow with inline SVG background-image, added `min-height: 52px; box-sizing: border-box` to all field types including `.cs-trigger`.
**Rule**: Every form field type (input, select, custom select) must share `min-height` and `box-sizing: border-box`. Native selects must have `appearance: none` or they'll render at browser-determined heights.

## 2026-04-12 — Equal-weight metric grid when one metric is the answer
**Mistake**: Goal funding forecast in insights.html showed Predicted spending, Goal allocations, and Remaining in `grid-3` — equal size, equal weight. Remaining (−£510.34) is the answer to "can you fund your goals?" but got no visual priority over the other two.
**Fix**: Remaining as hero metric (`metric-value md` with danger/success color). Predicted spending + Goal allocations as small supporting row below a border.
**Rule**: In any data grid where one number is the answer and the others are context, the answer gets hero treatment. `grid-3` communicates equal importance — only use it when that's true.

## 2026-04-12 — Hidden pages with no forward navigation path
**Mistake**: /insights, /recurring, and /analytics were all active routed pages with zero entry points from the app. Users could only reach them by typing URLs directly. Core value props (predictions, recurring detection, analytics) were completely invisible.
**Fix**: Added sub-section navigation strip to my_money.html with three tappable rows linking to all three pages.
**Rule**: Before shipping any page, verify every route has at least one forward navigation path from within the app. A page that requires URL knowledge is not a feature — it doesn't exist for users.

## 2026-04-12 — metric-label on plan page sentence header
**Mistake**: Used `class="metric-label"` on "How your £X,XXX/month is divided" in plan.html — a full sentence with an embedded variable, rendering all-caps.
**Fix**: Plain `font-size: 0.72rem; color: var(--text-tertiary)` — no class, no uppercase.
**Rule**: If the string contains a number variable or reads as a sentence, it's never a metric-label. Metric-label = short static noun phrase only.

## 2026-04-12 — "%.2f" format lacks thousands comma separator
**Mistake**: `"%.2f" | format(value)` used for amounts that can exceed £1,000 (e.g. £1471.68, £2280.34 on insights page, goal amounts on overview). No comma means "£1471.68" instead of "£1,471.68" — harder to read at a glance.
**Fix**: Use `"{:,.2f}".format(value)` for all amounts that can reach four digits. Remaining `"%.2f"` usages are acceptable only for amounts reliably under £1,000 (daily rates, small deltas).
**Rule**: Hero metrics and any amount that could exceed £999 must use `"{:,.2f}".format()`. Daily rates, small deltas, and form default values can use `"%.2f"`.

## 2026-04-12 — ASCII hyphen before £ on transaction amounts (systematic)
**Mistake**: `{% if t.type == "income" %}+{% else %}-{% endif %}£{{ ... }}` — renders "-£34.50" instead of "−£34.50". This pattern appeared in overview.html, my_money.html, transactions.html, recurring.html, dashboard.html, and scenario.html.
**Fix**: `{% if t.type == "income" %}+£{{ ... }}{% else %}−£{{ ... }}{% endif %}` — Unicode minus before £, format call inside the correct branch.
**Rule**: Every sign-prefixed currency output must use the `{% if %}+£{% else %}−£{% endif %}` pattern — never append a sign character before `£`.

## 2026-04-12 — metric-label on form section headers
**Mistake**: Used `class="metric-label"` on "Income" and "Commitments" in factfind.html, and on "Change email" / "Change password" in settings.html. metric-label is for noun-form labels above numbers only. "Income" and "Commitments" are section dividers inside a form; "Change email" is an action phrase.
**Fix**: Form section headers that are short noun phrases → `class="section-label"`. Action phrases ("Change email", "Change password", "How to export your CSV") → plain inline style `font-size: 0.72rem; color: var(--text-tertiary)`.
**Rule**: metric-label ≤3-word noun above a number. section-label = short noun divider (no action verb). Action phrases = plain tertiary text, no class.

## 2026-04-12 — SVG className is not writable
**Mistake**: Set `svgElement.className = 'cs-chevron'` in custom-select.js — throws TypeError because SVG elements expose `className` as a read-only `SVGAnimatedString`, not a writable `DOMString`.
**Fix**: Use `element.setAttribute('class', 'cs-chevron')` or `element.classList.add('cs-chevron')` for SVG elements.
**Rule**: Never assign `.className` directly on elements created with `createElementNS` — always use `setAttribute('class', ...)`.

## 2026-04-12 — section-label on question sentences
**Mistake**: Used `class="section-label"` on "What if you changed your contribution?" — section-label applies gold uppercase rendering, making it ALL CAPS on a full question.
**Fix**: Changed to `style="font-size: 0.72rem; color: var(--text-tertiary); margin-bottom: 8px;"` — plain small text, no uppercase.
**Rule**: section-label = short noun-phrase page section dividers only. If it reads as a sentence, question, or instruction, it's not a section-label.

## 2026-04-12 — Negative currency sign placement
**Mistake**: Rendered negative amounts as "£-510.34" and "(£-63.00)" — the pound sign belongs before the sign, not after.
**Fix**: `{% if val < 0 %}−£{{ "%.2f"|format(val|abs) }}{% else %}£{{ "%.2f"|format(val) }}{% endif %}`. Use Unicode minus `−` not ASCII hyphen `-`.
**Rule**: UK currency format for negatives: −£X.XX. Never £-X.XX or £−X.XX.

## 2026-04-12 — metric-label on instruction phrases
**Mistake**: Used `class="metric-label"` on "Set a spending limit" — a 4-word action phrase. metric-label applies text-transform: uppercase, making it "SET A SPENDING LIMIT".
**Fix**: Changed to plain inline style `font-size: 0.72rem; color: var(--text-tertiary)` — no uppercase.
**Rule**: metric-label is for noun-form labels above numbers only (≤3 words, noun form). "Set a spending limit" is an instruction, not a metric. Use plain tertiary text instead.

## 2026-04-12 — Auth page glass-card is an acceptable exception
**Learning**: The no-card-on-forms rule has one exception: auth pages (login, register). These pages have no app chrome (no sidebar, no bottom nav), so the form needs a visual container against the bare page background. glass-card is acceptable here.
**Rule**: glass-card on forms = violation everywhere except auth pages. Auth pages are bare-page contexts where a visual boundary earns its place.

## 2026-04-12 — metric-label class applied to sentence-form text
**Mistake**: Used `class="metric-label"` on full question sentences ("Can you fund your goals this month?") — metric-label has `text-transform: uppercase; letter-spacing: 0.2em` so the question became "CAN YOU FUND YOUR GOALS THIS MONTH?" which reads as shouting.
**Fix**: metric-label is only for short noun-form metric titles (SPENT SO FAR, PREDICTED TOTAL). Sentences and questions use plain `font-size: 0.8rem; color: var(--text-primary)` or similar.
**Rule**: metric-label = noun labels above numbers only. If it reads as a sentence or question, it's not a metric-label.

## 2026-04-12 — Agreeing instead of pushing back
**Mistake**: When asked "is individual cards per budget fine?", said yes ("budget content depth justifies cards") without critically evaluating the pattern. The correct answer was no — budget categories are list data, not financial objects.
**Fix**: Always critically evaluate the question, not just validate what was asked. If something looks like list data (categories, transactions, rows), it's a row. If it's a financial object the user manages as a whole (goal, account), it's a card. Say so even if the user seems to expect agreement.
**Rule**: Push back candidly whenever you disagree — this is a real product with real users; blind agreement is more damaging than an uncomfortable correction.

## 2026-04-12 — Cards used as universal container (AI slop tell)
**Mistake**: glass-card used for forms, page sections, empty states, and teasers — not just discrete scannable items. Every section was boxed, making the page read as a grid of containers with no hierarchy.
**Fix**: Cards only for discrete list items a user acts on as a whole (budget cards, goal cards) and AI insight blocks (gold-card). Forms, page sections, empty states, and teasers sit directly on the page background, separated by spacing and type hierarchy.
**Rule**: Ask "is this a discrete unit the user acts on as a whole?" If no, it's not a card — use spacing and labels instead.

## 2026-04-12 — Green color on opportunity cost figures
**Mistake**: Used `var(--success)` and a "+" prefix on `lost_growth` figures — the money a user did NOT earn by spending instead of investing. Green + "+" reads as gain, which is the exact opposite of the intended message.
**Fix**: Change to `var(--text-tertiary)` and label as "incl. £X growth" — muted, no prefix. The figure is context, not a positive outcome.
**Rule**: Green is gain. If a figure represents a cost, a loss, or an opportunity cost, it must never be green.

## 2026-04-12 — Status badges using ALL CAPS
**Mistake**: `.badge` had `text-transform: uppercase; letter-spacing: 0.08em` — made every status badge ("OVER BUDGET", "ON TRACK") shout. Aggressive tone, inverted hierarchy relative to the content around it.
**Fix**: Removed `text-transform` and `letter-spacing` from `.badge` globally. Badges are now normal case ("Over budget", "On track") — informative, not alarming.
**Rule**: Badges communicate status, not alerts. Normal case, no letter-spacing. ALL CAPS is for headings only.

## 2026-04-12 — Triple redundancy in status communication
**Mistake**: Over-budget state on budget cards was communicated three times: badge ("OVER BUDGET") + red progress bar + red text ("£X over budget"). Only the text added new information (the amount).
**Fix**: Suppressed the badge when status is 'exceeded' — bar color + text is sufficient. Badge is kept for non-exceeded states where it provides quick-scan value without redundancy.
**Rule**: Each UI channel (color, badge, text) must add distinct information. If two channels say the same thing, remove one.

## 2026-04-11 — Banner CTA competing with page primary action
**Mistake**: Added a factfind nudge banner with `btn-primary btn-sm` inside it — rendered as a full-width gold button, creating two competing primary CTAs on screen (the banner "Set up" + the page's own primary action like "Set budget" or "Upload statement").
**Fix**: Make the entire banner a slim tappable `<a>` strip — info icon + single line of text + chevron. No separate button. The whole row is the link.
**Rule**: A page can only have one primary CTA (gold/filled button); persistent nudge banners must use a tappable strip pattern, never a button.

## 2026-04-11 — Floating action button between content sections
**Mistake**: Upload statement / Add manually CTA was a standalone floating div between the whisper card and the spending breakdown — unanchored, interrupting data flow, and dominating empty state.
**Fix**: Move upload/add actions into the "All transactions" card header, positioned next to the section label. Actions belong adjacent to the data they create.
**Rule**: Actions should anchor to the section they affect — never float standalone between content sections.

## 2026-04-11 — Settings nav active state leaking to factfind page
**Mistake**: `pages.factfind` was included in the Settings nav active-state condition, so the Settings tab lit up gold when users were on the factfind page — making them think they were on Settings.
**Fix**: Remove `pages.factfind` from the Settings active endpoint list. Factfind is a standalone onboarding flow, not a Settings sub-page.
**Rule**: Nav active states should only highlight the tab that directly owns that route — never highlight a parent tab for an unrelated onboarding flow.

## 2026-04-11 — Factfind banner placed on unreachable page
**Mistake**: Added factfind setup banner to `overview.html`, but the `/overview` route redirects pre-factfind users to `/factfind` — making the banner on Overview unreachable.
**Fix**: Place the banner on the three pages users CAN actually reach before completing factfind: Money, Goals, Budgets.
**Rule**: Before adding UI to a page, verify the route renders that page for the target user state — check Flask routes for conditional redirects.
