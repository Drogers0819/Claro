# Claro Design System

The source of truth for every visual decision in the product. Every rule includes a decision condition — the question you ask to decide whether to apply it. When something isn't covered here, define it here before implementing it.

---

## HOW TO USE THIS DOCUMENT

Before writing any UI element, ask:
1. What am I building? (text, a value, a label, a button, a card, a section...)
2. What is it communicating? (most important thing, supporting info, annotation, action...)
3. Find the relevant section below and follow the decision rule.

If two options both seem valid, default to the **less prominent** one. You can always increase emphasis; you can't reduce it once it's set.

---

## 1. Typography

### 1.1 Which font?

**Decision rule:** Is this a page heading (h1), the sidebar logo, or body copy inside a gold-card AI block?
- **Yes** → `var(--font-serif)` (Cormorant Garamond). Always italic in these contexts.
- **No** → `var(--font-sans)` (Inter). Everything else: labels, values, buttons, nav, forms, metadata, badges.

Never use serif for data values, labels, navigation, buttons, or form elements.

---

### 1.2 Which font size?

**Decision rule:** What role does this text play on the page?

| Size | Role | Decision: use this when... |
|---|---|---|
| 2.8rem | Display hero | ONE number is the entire focus of the screen (balance dashboard hero). Only one per screen. |
| 2rem | Large metric | Primary metric inside a card |
| 1.5rem | Medium metric | Secondary metric alongside a larger one |
| 1.2–1.3rem | Small metric | Compact metrics in a row or side-by-side |
| ~1.4rem | Page heading | h1 in `.page-header` — the page title |
| 0.9rem | Body | Standard body text, transaction names, values in rows, form input values |
| 0.85rem | Secondary body | Supporting descriptions, nav link labels, plan item names |
| 0.82rem | Small UI text | Profile items, toast messages, sign-out buttons |
| 0.8rem | Label | Form labels, row sub-labels, button text |
| 0.78rem | Caption | Methodology explanations, help paragraphs — reads as a footnote |
| 0.75rem | Meta | Timestamps, category tags, badge text, `.section-label` supporting text |
| 0.72rem | Micro | Validation error messages, very small category tags |
| 0.7rem | Nano | `.section-label` class text, tight system labels |
| 0.65rem | Tiny | Step counters ("Step 3 of 4"), `.user-tier` label |

**Hard rule:** Use only sizes from this table. No 0.77rem, 0.83rem, 0.87rem, 0.92rem or other off-scale sizes. If you're in between two sizes, use the smaller one.

---

### 1.3 Which font weight?

**Decision rule:** How important is this text within its cluster?

| Weight | Name | Decision: use this when... |
|---|---|---|
| 300 | Light | The text is data the user entered into a form input. Nothing else. |
| 400 | Regular | Default. Use unless there's a reason to deviate. |
| 500 | Medium | This text needs mild emphasis but is not the primary action or total. Use on: total-row labels, active nav links, profile name, medium-importance data values, the "important" label in a label+value pair where label = row title. |
| 600 | Semibold | Maximum emphasis. Use on: primary CTA button text, the main financial total on a row, `.section-label` class, h1 in page-header. Only one thing per visual cluster should be 600. |

**Tests:**
- "Is this the single most important number or label on this row?" → consider 600
- "Is more than one thing at 600 in this cluster?" → reduce one to 500
- "Is this body copy that just needs a bit more presence?" → 500
- "Is this user-typed data?" → 300
- "Is this everything else?" → 400

Never use 700 or 800. Never use 300 outside form inputs.

---

### 1.4 Which text colour?

Three levels. This is the most important rule in the system.

| Token | Value | Decision: use this when... |
|---|---|---|
| `--text-primary` | rgba(255,255,255,0.9) | This is the **most important thing on this row or in this cluster**. The user's eye should land here first. The number, the name, the total, the heading. |
| `--text-secondary` | rgba(255,255,255,0.65) | This matters, but it's not the hero. Supporting information: body copy, descriptions, cost values in a ledger (de-emphasised because they're subtracted), form labels that need presence, inactive nav links. |
| `--text-tertiary` | rgba(255,255,255,0.5) | This annotates or labels something else. Column labels above values, timestamps, metadata, step counter labels, placeholder-like helper text, anything that says what the data IS rather than being the data itself. |

**Decision questions:**
- "If I removed this text, would the user lose the main meaning?" → text-primary
- "Is this a label that identifies a value?" → text-tertiary
- "Is this supporting copy that adds context?" → text-secondary
- "Is this a cost/deduction row (a negative in a ledger)?" → text-secondary for the value (it's intentionally de-emphasised vs text-primary income values)
- "Is this a total or summary row?" → text-primary for both label (weight 500) and value (weight 600)

**Label+value pair patterns:**

```
Standard row:
  Label  → text-tertiary, 0.8rem, weight 400
  Value  → text-primary, 0.9rem, weight 400

Cost/deduction row (money going out):
  Label  → text-tertiary, 0.8rem, weight 400
  Value  → text-secondary, 0.9rem, weight 400  ← intentionally dimmed

Total/summary row — ledger context (e.g. plan.html monthly breakdown):
  Label  → text-primary, 0.85rem, weight 500
  Value  → text-primary, 1.1rem, weight 600

Total as hero (e.g. plan_review.html surplus, surplus_reveal.html):
  Supporting rows → recede: text-tertiary labels, text-secondary or text-tertiary values, 0.78rem uniform
  Total label → text-tertiary, 0.65rem, uppercase (annotation above the number)
  Total value → text-primary, 2rem, weight 600 (the number is the moment — make it land)
  Unit (/mo)  → text-tertiary, 0.8rem, weight 400, inline beside the value
  Rule: if this number is the ANSWER the user came to see, treat it as a display hero, not a "slightly bigger" ledger row

Secondary row (supporting detail):
  Label  → text-tertiary, 0.75rem, weight 400
  Value  → text-secondary, 0.85rem, weight 400
```

---

### 1.5 When is text uppercase?

**Decision rule:** Is this text a structural divider label — the thing that names a section of content, not the content itself?

- **Use UPPERCASE + letter-spacing when:** `.section-label` class, `.user-tier`, `.sidebar-subtitle`, step counter labels, any label that is purely structural (names the section, not the content)
- **Never uppercase:** headings, data values, body copy, button labels, status badges text, nav links, anything a user reads as a sentence or a value
- **Never Title Case** for anything (not headings, not button labels, not nav items)

Always sentence case for everything that isn't a structural section marker.

---

### 1.6 When is text italic?

**Decision rule:** Is this text in one of exactly three locations?

- **Italic:** h1 inside `.page-header` (Cormorant Garamond editorial feel) · `.sidebar-logo` · body copy inside `.gold-card` (Claro AI voice)
- **Not italic:** labels, values, descriptions, helper text, badges, buttons, nav links, form elements, any instructional copy

If it "feels nice" italic outside these three contexts — don't do it.

---

### 1.7 When does text get underline?

**Decision rule:** Is this an inline text link that is NOT a primary or secondary CTA button?

- **Underline:** Inline text links that are secondary/supporting actions (e.g. "or add manually", "See your projection"). Style: `text-decoration: underline; text-underline-offset: 2px; color: var(--text-secondary)`
- **No underline:** Navigation links, `.btn-primary`, `.btn-secondary`, back links
- **Never gold on inline links** — gold is for CTAs and AI, not inline text links

---

## 2. Colour

### 2.1 When is gold used?

`var(--roman-gold)` (#C5A35D)

**Use gold when:**
- This is the primary CTA button (`.btn-primary` background)
- This is a goal savings progress bar fill (achievement colour)
- This is the AI pulse header label ("CLARO") and the `.ai-pulse` dot
- This is the active state on a nav link or chip selection border
- This is a projection or plan status that is on track
- This is the focused state on a form input border
- This is a `.btn-secondary` border and text

**Never use gold when:**
- Inline text links (use text-secondary + underline)
- Neutral informational values (income amounts, balance displays)
- Section divider labels (`.section-label` uses text-tertiary)
- Step progress bars in the onboarding wizard
- Time/month progress bars (neutral white fill)
- Running totals or subtotals (neutral financial data)
- Avatar backgrounds
- Running tally values or plan numbers
- Font-weight differences can communicate hierarchy instead

**All gold must use `var(--roman-gold)` or `var(--roman-gold-dim)` — never hardcoded `rgba(197,163,93,...)`.**

---

### 2.2 When is green (success) used?

`var(--success)` (#68D391)

**Use green when:** Real monetary gains have occurred. Income received, positive balance delta, a goal actually completed, a budget actually under limit.

**Never use green when:**
- Projecting future savings ("you could save £X")
- Something is neutral or just "on track" (use badge-default instead)
- A metric is healthy but hasn't gained anything (use badge-success for status, not a green value)
- It's an opportunity cost calculation

---

### 2.3 When is red (danger) used?

`var(--danger)` (#FC8181)

**Use red when:** A destructive action is being taken or confirmed (delete, sign out), a form field fails validation, a budget has been exceeded, a balance is negative.

**Never use red when:** Something is approaching a limit but hasn't crossed it (use warning/gold), or something is merely secondary/supporting.

---

### 2.4 Background colours — decision table

| Background | Value | Use when... |
|---|---|---|
| Page | `var(--bg-primary)` | Always for page body |
| Glass card | `var(--glass)` = rgba(255,255,255,0.03) | `.glass-card` only |
| Gold card | rgba(197,163,93,0.05) | `.gold-card` only |
| Whisper/nudge | rgba(197,163,93,0.04) | Action whisper box, factfind nudge |
| Form input | rgba(255,255,255,0.03) | `.form-input`, `.form-select` |
| Row hover | rgba(255,255,255,0.025) | Transaction row, nav link hover |
| Subtle box | rgba(255,255,255,0.02) | Must-hit disclaimer box, very faint context block |
| Avatar | rgba(255,255,255,0.07) | `.user-avatar` on dark themes only |

---

### 2.5 Border colours — decision table

| Border | Value | Use when... |
|---|---|---|
| `var(--glass-border)` | rgba(197,163,93,0.12) | Glass cards, form inputs, popovers, dropdowns |
| Subtle divider | rgba(255,255,255,0.06) | Row separators between data rows in a list |
| Very faint divider | rgba(255,255,255,0.04) | Paused/secondary rows, barely-there separators |
| Gold focus | `var(--roman-gold)` | Focused form input only |
| Danger | `var(--danger)` at 0.28 opacity | `.card-danger`, error form fields |
| Step bar filled | rgba(255,255,255,0.25) | Onboarding wizard completed steps |
| Step bar unfilled | rgba(255,255,255,0.08) | Onboarding wizard upcoming steps |

---

## 3. Cards and Elevation

**The single decision question:** Does the user interact with this as a single, discrete unit — clicking it, editing it, or tracking it as one thing?

### 3.1 `.glass-card` — use when:
- This is a discrete financial object: goal card, budget row, transaction list, metric grid, recurring item list
- This is the login or register form (only exception to no-card-on-forms rule — no app chrome surrounds it)

**Do NOT use `.glass-card` on:**
- Methodology text or plan explanations
- Plan overview number summaries
- Forms inside the app (factfind, add/edit goal, settings fields, checkin)
- Empty states
- Cross-page CTA sections
- Anything that explains HOW the system works

### 3.2 `.gold-card` — use when:
- This block contains Claro AI commentary — always accompanied by `.ai-pulse` + "CLARO" label + italic body copy
- This is the ONLY type of gold card in the app

**Gold-card anatomy — always this structure:**
```
.ai-pulse dot + "CLARO" label → font-size: 0.65rem, color: var(--roman-gold), uppercase, letter-spacing
Body text → font-size: 0.9rem, color: var(--text-secondary), font-style: italic, line-height: 1.7
```
Never use `var(--text-primary)` on gold-card body text. The italic + gold border provides the emphasis — the text itself should be secondary weight.

**Do NOT use `.gold-card` on:**
- Non-AI content
- Call-out boxes or highlighted sections
- Anything without the CLARO label + pulse

### 3.3 Bare (no card) — use when:
- Forms inside the app
- Methodology and explanatory text
- Empty states
- Onboarding wizard steps
- Plan overview numbers
- Whisper/nudge messages (these use the custom whisper div, not glass-card)
- Any content that explains how things work rather than showing the user's own data

---

## 4. Buttons

### 4.1 Which button class?

**Decision rule:** What is this action doing and how important is it?

| Class | Decision: use when... |
|---|---|
| `.btn-primary` | This is the single most important action on the page. One per page only. Form submits, onboarding CTAs. |
| `.btn-secondary` | This is a secondary action — navigational, supplementary, or a tool action. "View full plan", inline calculator actions, post-action navigation. |
| `.btn-danger` | This confirms a destructive action inside a dialog (delete confirmation). |
| `.btn-destructive` | This is an inline destructive row action (delete row button — compact, appears in situ). |
| Plain text link | This is Cancel adjacent to a form submit. `font-size: 0.82rem; color: var(--text-tertiary)`. |

**If two primary actions exist on the same page:** one of them is wrong. Make the less critical one `.btn-secondary` or remove it.

### 4.2 Which button size?

**Decision rule:** Where is this button sitting?

| Size | Decision: use when... |
|---|---|
| Standard (no modifier) | Full-page standalone forms and onboarding CTAs |
| `.btn-sm` | Compact sub-forms inside accordions (settings panels), inline tool actions |
| `.btn-full` | The button is the sole CTA and should span full width (onboarding, single-action pages) |

### 4.3 Does this button need an icon?

**Decision rule:** Does clicking this button navigate to a different page or submit a form?

- **Yes, navigates forward** → Lucide `chevron-right` as last child (`<path d="M9 18l6-6-6-6"/>`, `stroke-width="1.5"`)
- **Yes, navigates back** → This is a link, not a button. Use `chevron-left`.
- **No, submits form / triggers in-place action** → No icon
- **It's a tool/calculator action** → No icon

Never use Unicode `→`, `←`, `▶`. Never use emoji.

### 4.4 Primary + Cancel button pairs

**Rule:** Never place a primary button and a cancel link side-by-side at unequal visual weights. The result looks broken — one element dominates and the other reads as orphaned text.

**Correct pattern — stacked:**
```html
<div style="display: flex; flex-direction: column; gap: 10px; margin-top: 4px;">
    <button type="submit" class="btn-primary btn-full">Save changes</button>
    <a href="..." style="text-align: center; font-size: 0.82rem; color: var(--text-tertiary); text-decoration: none;">Cancel</a>
</div>
```
- Primary button: full-width (`.btn-full`), clearly the main action
- Cancel: centered text link below — understated, unambiguous escape

**Why not side-by-side:** `btn-primary` is `inline-flex` so it takes natural content width. A plain text Cancel link alongside it creates a mismatched pair where the primary button either looks cramped or the cancel looks abandoned.

---

## 5. Forms

### 5.1 Does this field need a label?

**Always.** Every `<input>` must have an associated `<label class="form-label">`. No exceptions.

### 5.2 Does this field need "(optional)"?

**Decision rule:** Would the form submit and work correctly if this field is left blank?
- **Yes** → Add `(optional)` in text-tertiary inside the label
- **No** → No marker needed (required is the default expectation)

### 5.3 Which input size?

Two variants. Default is standard — only use small when the field is secondary or inline.

| Class | Padding | Min-height | Font | When to use |
|---|---|---|---|---|
| `.form-input` (standard) | 14px 18px | 52px | 0.9rem | Primary required fields — income, rent, bills, goal amounts. Any field the user MUST fill. |
| `.form-input form-input-sm` | 10px 14px | 40px | 0.85rem | Secondary/optional helpers — "enter your own amount", inline search, compact paired inputs where the full height would feel heavy relative to its importance. |

Never use standard size for decorative or trivial fields. Never use small for required primary fields — it visually signals the field is unimportant.

**Field types available:**
- `<input type="text/number/email/password">` + `.form-input` — single-line text or numeric
- `<select>` + `.form-select` — dropdown (same visual as form-input, built-in chevron)
- `<textarea>` + `.form-input` — multi-line (add `rows` attribute; no min-height override needed)
- Chip row (`<label class="amt-opt"><input type="radio">`) — single-select preset options
- Chip row (`<label><input type="checkbox" class="sub-chip">`) — multi-select toggles
- `<input type="checkbox">` — single boolean with label, styled gold when checked

No "large" variant exists — if a field feels small, use standard. If standard looks huge for context, use sm.

**Mobile font-size rule (iOS Safari):** Any `<input>` or `<select>` with `font-size < 16px` triggers automatic page zoom on iOS Safari when focused. Both `form-input` and `form-input-sm` must override to `font-size: 16px` inside the `@media (max-width: 768px)` breakpoint — visual compactness is achieved through padding reduction, not font-size reduction.

### 5.4 Validation error messages

Never rely on the browser's default "Please fill in this field" / "required" message — it is generic, unhelpful, and looks inconsistent across browsers.

Every `required` field must have a custom `oninvalid` message that explains what belongs there:
```html
<input type="text" name="name" class="form-input" required
    oninvalid="this.setCustomValidity('Please enter a name for your goal')"
    oninput="this.setCustomValidity('')">
```
- `oninvalid`: message shown when submit is triggered on an empty field
- `oninput`: clears the message as soon as the user starts typing (prevents the error persisting mid-edit)
- Message format: "Please [action] — [brief why if needed]". Sentence case, no period.

### 5.5 Should this form be in a card?

**Decision rule:** Does this page have app chrome (sidebar, bottom nav)?
- **No app chrome** (login, register) → `.glass-card` wrapper acceptable — the card provides the visual container
- **Has app chrome** → bare, no card wrapper

---

## 6. Badges

### 6.1 When does something get a badge at all?

**Decision rule:** Is this a STATUS on a financial object (goal, budget, transaction, plan)?
- **Yes** → Use a badge
- **No** → Use colour on the value directly (danger for negative balance, success for positive) or no badge

### 6.2 Which badge colour?

**Decision rule:** What is the status?

| Badge | Decision: use when... |
|---|---|
| `.badge-success` | Status is actively positive: goal on track to complete, budget healthy, spending below average |
| `.badge-warning` | Status is caution — approaching a limit, slightly behind, tight but not broken |
| `.badge-danger` | Status is bad: budget exceeded, goal behind by more than a month, negative delta |
| `.badge-default` | Status is neutral: "on track" with no action needed, a count, a tier label |

**Badge text is always lowercase.** The badge class communicates weight. The text communicates meaning. Never "ON TRACK" — "on track".

---

## 7. Progress Bars

### 7.1 When does something get a progress bar?

**Decision rule:** Is there a measurable quantity with a known target or maximum?
- **Goal savings** → Progress bar, fill = `var(--roman-gold)` (achievement)
- **Budget consumption** → Progress bar, fill = green (healthy) / warning / danger based on threshold
- **Month/time progress** → Progress bar, fill = `rgba(255,255,255,0.18)` (neutral, just shows time)
- **Category breakdown** → Progress bar, fill = category's assigned colour

### 7.2 Which height?

| Height | Decision: use when... |
|---|---|
| 3px | Decorative, supplementary |
| 4px | Secondary rows (budget list items) |
| 5px | Default (`.progress-track` base) |
| 8px | Hero — this is the primary metric on the page (goal detail page) |

---

## 8. Icons

### 8.1 When does an element get an icon?

**Decision rule:** Does adding an icon add meaning or aid recognition, or is it decoration?
- **Navigation links** → icon aids recognition in a list of similar items. Always icon.
- **CTA buttons** → icon only when navigating (arrow-right). See button rules.
- **Row items in a list** → icon when the type varies and the icon distinguishes the type (goal type icons, pot type icons)
- **Section labels** → no icon. The label text is sufficient.
- **Standalone body copy** → no icon.

### 8.2 What colour is the icon?

**Decision rule:** What is the icon communicating?

| Context | Colour |
|---|---|
| Navigation icon (inactive) | Inherits text-secondary from nav link |
| Navigation icon (active) | Inherits roman-gold from nav link |
| CTA button icon | `currentColor` — inherits from button text |
| Whisper / nudge icon | `var(--roman-gold)` at opacity 0.7 |
| Form icons | `var(--text-tertiary)` |
| Destructive action icon | `var(--danger)` |
| Neutral row icon | `var(--text-tertiary)` at opacity 0.5 |

### 8.3 Icon semantic map — always use these exact paths

One icon per semantic meaning, everywhere in the app. If the meaning isn't listed, add it here before implementing.

All icons: `stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"`.
Default size `width="14" height="14"` unless noted. Whisper icons use `width="16" height="16"`.

#### Navigation & Page Flow

| Meaning | Name | SVG paths |
|---|---|---|
| Back / previous | `chevron-left` | `<path d="M15 18l-6-6 6-6"/>` |
| Forward / continue | `chevron-right` | `<path d="M9 18l6-6-6-6"/>` |
| External link / open | `external-link` | `<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>` |

#### Actions

| Meaning | Name | SVG paths |
|---|---|---|
| Edit / modify | `edit` | `<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>` |
| Delete / remove | `trash-2` | `<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>` |
| Upload / import | `upload` | `<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>` |
| Refresh / retry | `refresh-cw` | `<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>` |
| Search | `search` | `<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>` |
| Add / new | `plus` | `<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>` |
| Close / dismiss | `x` | `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>` |
| Sign out / log out | `log-out` | `<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>` |

#### Status & Feedback

| Meaning | Name | SVG paths |
|---|---|---|
| Success / complete | `check-circle` | `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>` |
| Simple tick | `check` | `<polyline points="20 6 9 17 4 12"/>` |
| Error / critical | `x-circle` | `<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>` |
| Warning | `alert-triangle` | `<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>` |
| Info / neutral notice | `info` | `<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>` |
| Trending up / positive | `trending-up` | `<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>` |
| Trending down / negative | `trending-down` | `<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>` |

#### Sidebar Navigation (size `width="18" height="18"`)

| Tab | Name | SVG paths |
|---|---|---|
| Overview | `layout-dashboard` | `<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>` |
| Goals | `target` | `<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>` |
| Plan | `map` | `<polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/>` |
| Insights/Analytics | `bar-chart-2` | `<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>` |
| Companion | `message-circle` | `<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>` |

#### Financial Concepts (Whisper icons — size `width="16" height="16"`)

| Meaning | Name | SVG paths |
|---|---|---|
| Bank account / savings | `bank` (landmark) | `<path d="M12 2l10 5H2l10-5z"/><line x1="2" y1="7" x2="22" y2="7"/><line x1="6" y1="7" x2="6" y2="18"/><line x1="10" y1="7" x2="10" y2="18"/><line x1="14" y1="7" x2="14" y2="18"/><line x1="18" y1="7" x2="18" y2="18"/><line x1="3" y1="22" x2="21" y2="22"/>` — use `<path>` with `z` close for the roof triangle (draws all three edges); `<polyline>` only draws left slope + base, missing the right slope |
| Goal / target | `target` | `<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>` |
| Money / income / growth | `trending-up` | `<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>` |
| Recurring / scheduled | `repeat` | `<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>` |
| Budgets / categories | `pie-chart` | `<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>` |
| Analytics / breakdown | `bar-chart-2` | `<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>` |
| Plan / checklist | `clipboard-list` | `<rect x="9" y="2" width="6" height="4" rx="1"/><path d="M9 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2h-3"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/>` |
| Achievement / milestone | `award` | `<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89L17 22l-5-3-5 3 1.523-9.11"/>` |
| Momentum / streak | `zap` | `<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>` |
| Highlight / featured | `star` | `<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>` |
| Companion / AI chat | `message-circle` | `<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>` |
| Check-in / review | `check-circle` | `<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>` |
| Scenario / what-if | `search` | `<circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>` |

#### Account & Settings

| Meaning | Name | SVG paths |
|---|---|---|
| User profile | `user` | `<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>` |
| Settings / preferences | `settings` | `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>` |
| Help / FAQ | `help-circle` | `<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>` |
| Security / password | `lock` | `<rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>` |
| Password visible | `eye` | `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>` |
| Password hidden | `eye-off` | `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>` |
| Trial / security badge | `shield` | `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>` |
| Theme / appearance | `sun` | `<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>` |
| Financial profile | `trending-up` | `<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>` |

#### Onboarding / Stacked-layers icon

| Meaning | Name | SVG paths |
|---|---|---|
| Steps / layers | `layers` | `<path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>` |

---

## 9. Section Structure

### 9.1 Page order — always this sequence:

```
1. Back link          (if this page has a parent — always for: add_goal, edit_goal, goal_detail,
                        plan_review, checkin, upload, add_transaction, surplus_reveal, goal_chips,
                        plan_reveal, plan_review)
2. Step bar           (onboarding wizard pages ONLY: factfind, surplus_reveal, goal_chips, plan_reveal)
3. Factfind nudge     (ONLY on: overview, my_money, my_budgets, settings — and only if factfind incomplete)
4. .page-header       (h1 + optional sub-text)
5. Primary content    (data — cards, lists, forms)
6. Secondary content  (explanatory/methodology text — always after data, never before)
7. CTA                (primary button — always last, after all content)
8. Footer note        (legal/guidance disclaimer — 0.7rem, text-tertiary, centred — below CTA)
```

**Header alignment:** Always left. No centering. No exceptions. Not for reveals, not for emotional moments. Consistency IS the quality signal.

### 9.2 When is a section separator a border vs spacing?

**Decision rule:** Are these two things semantically different sections, or the same kind of content?

- **Different sections** → `border-top: 0.5px solid rgba(255,255,255,0.06)` + margin above
- **Same type of content in a list** → `border-bottom: 0.5px solid rgba(255,255,255,0.06)` on each row
- **Sign-out / destructive action separated from settings** → `margin-top: 48px` only, no border. Use colour (danger) to create the semantic separation instead.
- **Total row at bottom of ledger** → `border-top: 0.5px solid var(--glass-border)` + `padding-top` + `margin-top`

---

## 10. Navigation

### 10.1 When is a nav item active?

**Decision rule:** Is the current page URL a match for this tab's route?
- Exact match → active state (roman-gold text, roman-gold-dim background)
- Parent route match → active (e.g. `/my-money/*` keeps Money tab active)
- Different route → inactive (text-secondary)

**Never** apply active state to two items simultaneously.

Settings tab active state matches `pages.settings` **only**. Never `pages.factfind` — factfind is an onboarding flow, not a settings sub-page.

### 10.2 Sub-nav active item

- Active: `border-bottom: 1.5px solid var(--roman-gold); color: var(--roman-gold)`
- Inactive: `color: var(--text-tertiary)`

---

## 11. Empty States

### 11.1 Which empty state type?

**Decision rule:** Is there OTHER content on this page, or is the empty state all there is?

- **Nothing else on the page** → `.empty-page-center` — vertically and horizontally centred, `min-height: 50vh`
- **Other content exists** → inline section-level empty state — `padding: 8px 0 32px`, left-aligned

Both require:
- Headline: 0.95rem, text-primary, weight 500
- Subtext: 0.8rem, text-tertiary, line-height 1.6 — answers "why empty" + "what to do"
- CTA: `.btn-primary.btn-sm`
- No card wrapper

---

## 12. Interactive States

### 12.1 Every interactive element must have:

- `:hover` state — visible change (background, colour, or border)
- `:focus-visible` — 2px gold outline (set globally, do not override)
- `:disabled` — opacity 0.5, cursor not-allowed, no hover effects

### 12.2 When is a CTA disabled vs hidden?

**Decision rule:** Is there a condition the user must meet before the action becomes valid?
- **Yes** → Show the button disabled with instructional text ("Select a goal above to continue"), not hidden
- Never hide the primary CTA. Disabled + instruction = clear path. Hidden = dead end.

---

## 13. Notifications and Feedback

### 13.1 Which toast type?

**Decision rule:** What just happened?

| Type | Decision: use when... |
|---|---|
| `.flash-success` | An action completed successfully — transaction saved, goal created, settings updated |
| `.flash-error` | An action failed — validation error, server error, save failed |
| `.flash-warning` | An action succeeded but with a caveat — plan updated but some goals paused |
| `.flash-info` | Neutral information the user should know but needn't act on |

### 13.2 When is a confirmation dialog required?

**Decision rule:** Is this action irreversible AND will the user lose data?
- **Yes** → Show `.confirm-overlay` dialog before executing
- **Irreversible but recoverable** → Allow undo via toast (with action link) instead of blocking dialog
- **Reversible** → No dialog needed

---

## 14. Onboarding Wizard

### 14.1 When do wizard step bars appear?

Only on the 4 wizard pages: `factfind`, `surplus_reveal`, `goal_chips`, `plan_reveal`. Never on `plan_review` (it's a detail page, not a wizard step) or anywhere else.

### 14.2 Where does the AI whisper (gold-card) appear?

Only on `plan_review` — before the allocation breakdown. Decision: the user is reading and comparing. That's the right moment for commentary.

Never on `plan_reveal` — reveal moments are clean. Never on factfind, surplus_reveal, or goal_chips — the user is inputting, not reading.

---

## 15. Animation and Motion

### 15.1 When does something animate?

**Decision rule:** Is this a state change the user triggered, or a page that reveals information progressively?

- **User triggered state change** (button hover, input focus, row hover) → CSS transition, 0.1–0.3s ease
- **Page that reveals content progressively** (plan_reveal) → `fadeUp` stagger animation
- **System notification arriving** → `toastIn` cubic-bezier
- **Everything else** → no animation

### 15.2 Which duration?

| Duration | Use when... |
|---|---|
| 0.1s | Instantaneous feel — popover item hover |
| 0.15s | Fast interactive — row hover, delete button reveal |
| 0.2s | Standard — buttons, nav, card borders |
| 0.3s | Considered — form focus |
| 0.4s | Deliberate — progress bar fill (feels watched) |

---

## 16. Copy Rules

### 16.1 Em dashes
Never. Use commas, full stops, or `·` midpoints.

### 16.2 Emoji
Never. Anywhere. Templates, service files, route files.

### 16.3 Button labels
Present-tense verb. "Set budget" not "Budget settings". "Record transaction" not "New transaction".

### 16.4 Status labels
Sentence case. "on track" not "ON TRACK". The badge provides weight. The text provides meaning.

### 16.5 Numbers
Always comma-separated thousands: `"{:,.0f}".format(value)`. Negative amounts: Unicode minus (U+2212, `−`) before `£`, never ASCII hyphen.

---

## 17. Logo & Mobile Header

### 17.1 Logo sizing

| Context | Size | Rule |
|---|---|---|
| Desktop sidebar | 40×40px | `object-fit: contain` — compact mark only, no text |
| Mobile header | `height: 24px; width: auto` | Mark has breathing room within 52px bar — never fill the full bar height |

The logo PNG is landscape (636×334). Always set `height` explicitly and let `width: auto` handle aspect ratio. Do not use a square container — `object-fit: contain` constrains by width and makes the mark shorter than expected.

**Optical sizing rule:** The logo mark is a dense visual object — it needs proportionally more clear space than a circle avatar. In a 52px bar, `height: 24px` leaves 14px above and below (27% padding each side). `height: 36px` only leaves 8px (15%) — visually cramped even though the avatar circle is also 36px. The letter inside the avatar circle optically reads much smaller than 36px, creating a misleading reference point.

### 17.2 Mobile header bar layout

- **Structure**: `.mobile-header-bar` — fixed bar, `justify-content: space-between`, `padding: 0 16px`.
- **Left**: `<a class="mobile-logo">` with `<img style="height:36px;width:auto;">` — links to overview.
- **Right**: `.mobile-settings-btn` avatar circle (36×36) — links to settings.
- Setting logo `height: 36px` matches the avatar's visual circle height. Don't use a square container — the PNG is landscape and `object-fit: contain` in a square would make the mark appear shorter than the avatar.
- The bar is hidden on desktop (`display: none` above 768px breakpoint).

---

## 18. Compliance Checks — Run These Before Marking Any UI Done

1. **Playwright verify** — screenshot at 375px and 1440px
2. **Gold grep** — `grep -r "rgba(197,163,93" templates/` → should return zero results
3. **Em dash grep** — `grep -rn "—" templates/ app/services/` → should return zero results
4. **Emoji grep** — `grep -Pn "[\x{1F300}-\x{1FFFF}]" templates/` → should return zero results
5. **Centering check** — `grep -n "text-align: center" templates/` → only valid in footer notes
6. **Double primary CTA check** — search for `btn-primary` count per template → max 1
7. **Hardcoded inline uppercase check** — `grep -n "text-transform: uppercase" templates/` → must also use `.section-label` class, not raw inline

---

## 18. What Goes Where

| Rule type | File |
|---|---|
| Visual patterns — ALL of the above | `Fintrack/DESIGN-SYSTEM.md` (this file) |
| Dev rules — routing, gotchas, post-action flows, Playwright | `Fintrack/AGENTS.md` |
| Project decisions and session log | `Fintrack/DEVELOPMENT.md` |
| Corrections and lessons | `lessons.md` |
| Memory across sessions | `~/.claude/projects/.../memory/` |
| Universal design principles | `~/.claude/design-standards.md` |

When a pattern changes in code, update this document in the same commit.

---

*Source of truth as of 18 April 2026. Built from full audit of main.css, themes.css, and all 25 active templates.*
