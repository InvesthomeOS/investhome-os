# Investhome OS — UI Component Guidelines

**Document type:** Product Design Sprint 2 deliverable  
**Last updated:** 2026-07-15  
**Audience:** Product, design, engineering  
**Status:** Per-component usage reference aligned with IODL

**Related:** [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) · [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) · [UI_GUIDELINES.md](./UI_GUIDELINES.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) · [CODING_STANDARDS.md](./CODING_STANDARDS.md)

---

## How to use this document

Each section covers **when to use**, **anatomy**, **variants**, **states**, **spacing**, **accessibility**, and **i18n** for one component or pattern.

| Marker | Meaning |
|--------|---------|
| ✅ | `@investhome/ui` React primitive |
| 🟡 | CSS-only in `globals.css` |
| 📋 | IODL spec only |

---

## Foundation Components

### Button ✅

**When to use:** Primary actions (save, create, submit), secondary actions (cancel, filter apply), destructive actions (archive, delete), low-emphasis actions (dismiss).

**When not to use:** Navigation between pages (use `<Link>` or nav); icon-only without `aria-label`; multiple primary buttons in one toolbar.

**Anatomy:**

```
[ Button label ]     or     [ Icon + label ]
```

**Variants:**

| Variant | Class | Usage |
|---------|-------|-------|
| Primary | `.leads__button--primary` | One per region — main CTA |
| Secondary | `.leads__button--secondary` | Alternate positive action |
| Ghost | `.leads__button--ghost` | Tertiary, filter reset |
| Danger | `.leads__button--danger` | Irreversible / destructive |

**States:** default · hover · `:disabled` (opacity 0.6, `cursor: not-allowed`) · focus-visible (browser default + accent outline target)

**Spacing:** padding `0.625rem 0.875rem`; gap in button groups `0.5–0.75rem`

**Accessibility:** Native `<button>`; `type="button"` default; loading state via `disabled` + `aria-busy="true"` (target)

**i18n:** All labels in `messages/tr.json` + `en.json`; avoid hardcoded English in workspace components

**Package:** `@investhome/ui` `Button` — `variant` prop maps to classes above

---

### Input / TextArea ✅

**When to use:** Form fields, filter inputs, search within workspace (not global search overlay).

**Anatomy:**

```
Label (optional)
[ Input field                    ]
Helper / error text
```

**Variants:** Single-line `Input`; multi-line `TextArea`; workspace filter fields use `.leads__field` wrapper with label above

**States:** default · `:focus` (border accent target) · `:disabled` · error (pair with `.auth-form__error` or `.leads__error`)

**Spacing:** label gap `0.375rem`; input padding `0.625rem 0.75rem`; field min-width `160px` in filter rows

**Accessibility:** `<label htmlFor>` association ✅ in `Input` component; error text linked via `aria-describedby` (target)

**i18n:** Labels and placeholders translated; API receives trimmed strings, empty → `null` for optional fields

**Package:** `@investhome/ui` `Input`, `TextArea`

---

### Dropdown (Select) 🟡

**When to use:** Fixed choice lists (status, locale, entity type filter); ≤20 options.

**When not to use:** Large searchable lists (use global search or combobox — 📋); multi-select (📋 chip multiselect)

**Anatomy:**

```
Label
[ Selected value        ▼ ]
```

**Classes:** `.leads__field select`, `.dashboard__language-select`, `.global-search-filters__grid select`

**States:** default · `:disabled` · open (native)

**Spacing:** Same as Input; language select uses pill radius `999px`

**Accessibility:** Native `<select>` preferred; ensure visible label; for custom dropdowns (future) use listbox pattern

**i18n:** Option labels translated; values remain API enums

**Promotion:** `@investhome/ui` `Select` — Phase 1 ([DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md))

---

### Search (Global) 🟡

**When to use:** Cross-entity lookup from any dashboard route; primary discovery path ([INFORMATION_ARCHITECTURE.md §7](./INFORMATION_ARCHITECTURE.md)).

**Anatomy:**

```
Trigger: [ 🔍  Search…                    ⌘K ]
Overlay:
  ┌─ Header: [ input ] [ filters ] [ close ] ─┐
  ├─ Filter chips (entity types)              ┤
  ├─ Grouped results                          ┤
  └─ Footer: keyboard hints                   ┘
```

**Classes:** `.global-search-trigger`, `.global-search-overlay`, `.global-search-palette`, `.global-search-result`

**States:** closed · open · loading · empty · error (`.global-search-palette__state--error`) · active result (`.global-search-result--active`)

**Spacing:** palette width `min(42rem, 100%)`; result padding `0.65rem 0.75rem`; overlay padding top `8vh`

**Accessibility:** Focus input on open; arrow key navigation ✅; `Escape` closes; result links must be real `<a>` or buttons with clear name

**i18n:** Placeholder, group headings, empty/error states in message catalogs; highlight marks preserve locale text

**Keyboard:** `Ctrl+K` / `⌘K` ✅; `Enter` navigate; `↑` `↓` select

---

### Command Bar 🟡 / 📋

**When to use:** Extends Global Search with `>` / `/` commands and NL intents ([DESIGN_LANGUAGE.md §4](./DESIGN_LANGUAGE.md)).

**Anatomy:** Same shell as Search + mode indicator + command suggestions list

**States:** search mode ✅ · command mode 📋 · NL mode 📋

**Do:** Reuse `.global-search-palette` shell; show mode in header

**Don't:** Build separate overlay; auto-execute mutations

**Accessibility:** Announce mode change via `aria-live="polite"` (target)

**i18n:** Command hints bilingual; command names stay English keys with translated descriptions (target)

---

### Card ✅ / 🟡

**When to use:** Group related content; KPI display; clickable module launcher tiles.

**Variants:**

| Variant | Class | Usage |
|---------|-------|-------|
| Module card | `.dashboard__card` | Workspace launcher, summary links |
| Stat card | `.investors__stat-card` | KPI label + value |
| Document tile | `.documents-grid__card` | File grid |
| Generic | `.ih-card` (📋 CSS pending) | `Card` component |

**Anatomy (module card):**

```
┌─────────────────────────┐
│ Title                   │
│ Description (muted)     │
└─────────────────────────┘
```

**States:** default · hover (border accent mix) · focus-visible (linked cards)

**Spacing:** padding `1–1.25rem`; radius `0.875rem`; grid gap `1rem`

**Accessibility:** Linked cards wrap in `<a>` with focus ring on card; headings use proper level (`h2`/`h3`)

**Package:** `@investhome/ui` `Card` — prefer after `.ih-card` CSS lands

---

### Table ✅

**When to use:** Dense tabular data — leads, investors, transactions, admin matrices.

**When not to use:** &lt;4 columns on mobile without card fallback (target); timeline data (use Timeline)

**Anatomy:**

```
┌─ wrap (overflow-x) ─────────────────────┐
│ thead: uppercase muted headers          │
│ tbody: rows                             │
└─────────────────────────────────────────┘
```

**Classes:** `Table` → `.admin-table-wrap` + `.admin-table`; Leads uses `.leads__table` with clickable `.leads__row`

**States:** default · hover row · selected row (target) · loading skeleton (target) · empty (use `EmptyState` above table)

**Spacing:** cell padding `0.75–0.875rem`; header `0.75rem` uppercase

**Accessibility:** `<table>`, `<th scope="col">`, caption or `aria-label`; sortable headers need `aria-sort` (target)

**i18n:** Column headers translated; numeric/date formatting locale-aware

---

### Badge ✅

**When to use:** Compact status label, nav "Soon" tag, demo indicator.

**Variants:** `default` · `success` · `warning` · `danger` · `info` — maps to `.ih-badge--*`

**Do:** One badge per status dimension; keep text short (1–2 words)

**Don't:** Use badge as button; stack multiple badges without hierarchy

**Spacing:** padding `0.125rem 0.5rem`; font `0.75rem`; pill radius

**Accessibility:** Text content must be readable; don't rely on color alone

**Package:** `@investhome/ui` `Badge`

---

### Status Chip 🟡

**When to use:** Inline entity status in table cells (lead status, notification priority).

**Classes:** `.leads__status`, `.notification-priority--*`, `.dashboard__status`

**Difference from Badge:** Status chips often include dot pseudo-element (`.dashboard__status::before`); tied to entity lifecycle

**i18n:** Status enum labels via i18n map per entity type

---

### KPI / Stat Card 🟡

**When to use:** Workspace stats bar — counts, sums, aggregates at top of list views.

**Anatomy:**

```
Label (muted, small)
VALUE (large, bold)
[ optional delta caption ]
```

**Classes:** `.investors__stat-card`, `.executive__notification-stat`, `.executive__card-delta`

**Grid:** 2–8 columns responsive; gap `1rem`; margin-bottom `1.5rem`

**Do:** Link card to filtered view when clickable (Executive summary cards)

**Don't:** More than 8 KPIs without collapse; duplicate Executive KPIs on Home

---

### Tabs 🟡

**When to use:** Switch related views within one workspace (Finance tabs, Document drawer tabs).

**Classes:** `.finance__tab` / `.finance__tab--active`; `.documents-tabs__tab` / `--active`

**States:** inactive (muted) · hover · active (surface bg + border)

**Spacing:** gap `0.5rem`; padding `0.5rem 1rem`; bottom border on tab bar

**Accessibility:** Use `role="tablist"`, `role="tab"`, `aria-selected` (target refactor); roving `tabindex`

**i18n:** Tab labels translated; tab count badge optional

---

### Breadcrumbs 📋

**When to use:** Deep hierarchy navigation (Inventory: Project → Building → Floor → Unit).

**Interim:** `.dashboard__back` link above page title

**Target anatomy:** `Home / Development / Temple / Units`

**Accessibility:** `<nav aria-label="Breadcrumb">`; current page `aria-current="page"`

---

### Dialog (Modal) 🟡

**When to use:** Create/edit forms; confirmations; focused tasks that block workspace.

**Anatomy:**

```
[ Scrim ]
  ┌─ Dialog ─────────────────┐
  │ Header: title    [close]│
  │ Body: form              │
  │ Footer: actions         │
  └─────────────────────────┘
```

**Classes:** `.leads-modal`, `.leads-modal__dialog`, `.leads-modal__header`, `.leads-modal__footer`

**States:** open · submitting (disable primary) · error inline

**Spacing:** dialog width `min(720px, calc(100vw - 2rem))`; padding `1.25rem`; footer gap `0.75rem`

**Accessibility:** `role="dialog"`, `aria-modal="true"`, focus trap, return focus on close, `Escape` closes

**i18n:** Title, labels, buttons translated

---

### Drawer 🟡

**When to use:** Entity detail read/update; notifications; document preview — preserves list context.

**Anatomy:**

```
[ Scrim ]                    ┌─ Panel ────────┐
                             │ Header         │
                             │ Sections       │
                             │ Footer actions │
                             └────────────────┘
```

**Classes:** `.leads-drawer`, `.leads-drawer__panel`, `--wide` (640px); `.notification-drawer__panel` (28rem)

**States:** open · loading section · error section

**Spacing:** padding `1.25rem`; section gap `1.25rem`; definition list `.leads-drawer__grid`

**Accessibility:** Same as Dialog; scrollable panel; sticky footer optional

**Do:** Include Related Items, Documents, Activity sections per entity pattern

**Don't:** Stack drawer on drawer; use full page for deep wizards

---

### Split View 🟡

**When to use:** Admin permissions matrix — list + detail side-by-side.

**Classes:** `.admin-split` — `1.2fr 1fr`; stacks at `900px`

**When not to use:** Standard workspace lists (prefer drawer-over-list)

---

## Data & Workflow Components

### Kanban 📋

**When to use:** Visual pipeline stages (Sales leads, Construction approvals).

**Target anatomy:** Columns per stage · cards draggable · column count + sum in header

**Interim:** Leads uses **table** view today — Kanban is spec-only

**Accessibility:** Drag alternatives via "Move to…" menu (required)

---

### Timeline 🟡

**When to use:** Activity history, entity audit trail, executive recent events.

**Classes:** `.activity-timeline`, `.activity-timeline__item`, `.activity-timeline__card`

**Anatomy:**

```
[ Time column ]  [ Summary + actor + changes ]
```

**Spacing:** 2-column grid `11rem 1fr`; gap `0.75rem`; border-top separator

**Accessibility:** List semantics `<ul>`; time in `<time datetime>` (target)

---

### Calendar 📋

**When to use:** Meetings, milestones, obligation due dates visualization.

**Interim:** Executive Deadlines API + Home Meetings widget stub

**Target:** Month/week/day views; entity-linked events

---

### Charts 🟡

**When to use:** Executive pipeline, cash flow comparison — at-a-glance quantitative patterns.

**Types:**

| Chart | Class | Data |
|-------|-------|------|
| Horizontal bar | `.executive__pipeline-bar` | Stage count |
| Dual bar | `.executive__cashflow-in/out` | In vs out |
| Health indicator | `.executive__health--*` | Text color only |

**Do:** Label every bar; provide table fallback

**Don't:** Introduce chart library without ADR; animate bars on load

---

### Activity Feed 🟡

**When to use:** Global Activity workspace; embedded feeds in Executive and entity drawers.

**Classes:** `.activity-timeline__list--page`, `.executive__activity-link`

**States:** loading · empty · filtered empty

---

### Notification Center 🟡

**When to use:** User alerts, approval requests, system signals — header bell on all routes.

**Anatomy:**

```
Bell [badge count]
  → Drawer:
      Groups by priority/date
      Notification item: priority · title · body · actions
```

**Classes:** `.notification-bell`, `.notification-drawer`, `.notification-item`, `.notification-item--unread`

**Unread style:** accent border + inset bar `box-shadow: inset 3px 0 0 var(--accent)`

**Accessibility:** Bell `aria-label` with count; drawer focus trap

**i18n:** Priority labels, action buttons translated

---

## Domain Cards

### Approval Card 📋

**When to use:** Home Approval Center; Construction/Finance approval queues.

**Target anatomy:**

```
[Type icon] Title · context          [Age]  [Review →]
```

**Interim:** Finance approve in transaction drawer; drawing proposal in document drawer

**Rules:** FIFO within priority; batch approve same type only ([AI_PRINCIPLES.md](./AI_PRINCIPLES.md))

---

### Investor Card 🟡

**When to use:** Investor list rows; stats; future card grid view.

**Interim:** Table rows with name, type, commitment summary — not standalone card component

---

### Inventory Card 📋

**When to use:** Unit/building tiles in Inventory workspace.

**Spec:** [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) — status dimensions, price, sqm

---

### Document Card 🟡

**When to use:** Document grid view; recent documents widget.

**Classes:** `.documents-grid__card`, `.documents-grid__ext`

**Anatomy:** extension badge · filename · metadata · optional processing badge

---

### Task Card 📋

**When to use:** Home Tasks widget; future `/dashboard/tasks`.

**Target anatomy:** checkbox · title · due date · entity link · priority

---

### AI Insight Card 📋 / 🟡

**When to use:** Document analysis results; Home AI brief sections; drawing detections.

**Interim:** Document drawer intelligence tabs (analysis, ask, drawing)

**Anatomy:**

```
┌─ AI Insight ────────────────────┐
│ [Optional severity icon]        │
│ Summary / recommendation text   │
│ Footer: L2 heuristic · HH:MM   │
│ [Review] [Dismiss]              │
└─────────────────────────────────┘
```

**Rules:** Show AI level; no auto-execute; confidential badge when external AI blocked

---

## AI Components

### AI Summary 🟡

**When to use:** Document analysis tab; future Home Morning Brief sections.

**Content:** Template-based prose from heuristic pipeline; omit section if API fails

**Footer:** `"Generated from your permissions · L2 heuristic · HH:MM"`

---

### AI Recommendation 🟡

**When to use:** Suggested next steps in analysis metadata; drawing proposal hints.

**Presentation:** Bulleted list with "Review" deep link — not auto-applied

---

### AI Warning 📋

**When to use:** Risk flags in analysis; anomaly detection on Executive.

**Visual:** Amber/red left border; severity label; link to evidence

---

### AI Explanation 📋

**When to use:** Home Today's Priorities ranking; search result "why matched"

**Pattern:** Collapsible "Because:" list — explainability required for rankings

---

### AI Confidence 📋

**When to use:** L3+ external LLM outputs where score available.

**Values:** High · Medium · Low · Unknown — omit for L2 heuristic

---

### AI Actions 🟡

**When to use:** Document drawer — Analyze, Reprocess, Ask.

**Permissions:** `documents.analyze`, `documents.ask`, `documents.reprocess`

---

### Human Approval 🟡

**When to use:** Drawing unit proposals; finance transactions; future inventory price changes.

**Anatomy:** Entity context · diff/summary · Approve / Reject · permission gate

**Audit:** Activity `APPROVED` / `REJECTED`; actor `USER`

---

## Executive Components

### Cash Flow 🟡

**When to use:** Executive financial section — period comparison of inflows/outflows.

**Classes:** `.executive__cashflow`, `.executive__cashflow-row`, `.executive__cashflow-in/out`

**Do:** Green in, red out; numeric column right-aligned

---

### Pipeline 🟡

**When to use:** Leads funnel by stage in Executive workspace.

**Classes:** `.executive__pipeline-row` — grid `140px 1fr 40px 120px`

**Interaction:** Row links to filtered Sales workspace (target)

---

### Construction Health 📋 / 🟡

**When to use:** Portfolio construction status overview.

**Interim:** Project health section partial; full construction workspace 📋

---

### Investor Health 🟡

**When to use:** Executive investor overview — commitments, funding gaps.

**Data:** Executive API investor section

---

### Portfolio Health 🟡

**When to use:** Project status rollup — on track / attention / at risk.

**Classes:** `.executive__health--on_track`, `--attention`, `--at_risk`

---

### Risk Card (Attention Item) 🟡

**When to use:** Executive "Attention Required" — critical/warning items.

**Classes:** `.executive__attention-item`, `--critical`, `--warning`

**Anatomy:** severity label · title · meta · full-row link

---

## Workspace Components

### Header (PageHeader) ✅

**When to use:** Top of every workspace page.

**Anatomy:** eyebrow (optional) · title · subtitle (optional) · actions slot (right)

**Package:** `@investhome/ui` `PageHeader`

**i18n:** Title from `navigation.modules.*` or page-specific keys

---

### Toolbar 🟡

**When to use:** Filters + view toggles + secondary actions below header.

**Classes:** `.leads__toolbar`, `.activity__toolbar`

**Layout:** flex wrap; space-between; align flex-end for filter baseline

---

### Filters 🟡

**When to use:** List narrowing — status, date, project, assignee.

**Classes:** `.leads__filters`, `.executive__filters`, `.global-search-filters`

**Do:** Provide "Reset" ghost button; persist in localStorage for Executive ✅

**Don't:** Hide filters that gate permission-sensitive data without label

---

### Content 🟡

**When to use:** Primary workspace body — stats + table/grid + tabs.

**Pattern:** stats bar → tabs (optional) → table → pagination

---

### Details (Drawer) 🟡

**When to use:** Entity drill-down from list, search, notification.

**Standard sections:** Overview · Related entities · Documents · Activity · AI (if permitted)

**Cross-workspace links:** "Open in Finance" when records exist ([INFORMATION_ARCHITECTURE.md §6](./INFORMATION_ARCHITECTURE.md))

---

### AI Panel 📋

**When to use:** Optional right rail — contextual Q&A for open entity.

**Interim:** AI lives in document drawer tabs only

**Target width:** 280–320px; collapsible; docked on ≥1280px

---

### Timeline (entity-scoped) 🟡

**When to use:** Inside entity drawers — same pattern as Activity workspace at smaller scope.

**Component:** Reuse `.activity-timeline` with entity filter

---

### Related Items 🟡

**When to use:** Drawer section — linked projects, investors, leads, transactions.

**Pattern:** Clickable chips or definition list linking to other drawers

**Rule:** No dead ends ([DESIGN_LANGUAGE.md D10](./DESIGN_LANGUAGE.md))

---

## State Components

### LoadingState ✅

**When to use:** Inline loading for page section or button wait.

**Don't:** Full-page spinner without skeleton for layout regions

**Package:** `@investhome/ui` `LoadingState` — pass translated `label`

**Prefer:** `.executive__skeleton` for layout-preserving load in Executive

---

### EmptyState ✅

**When to use:** Zero rows in list; empty search within workspace; no documents attached.

**Anatomy:** title · description · optional action button/link

**Package:** `@investhome/ui` `EmptyState` — maps `.documents-empty`

---

### ErrorState ✅

**When to use:** Section or page API failure; form-level fatal error.

**Anatomy:** title · message · retry action

**Package:** `@investhome/ui` `ErrorState`

**Pair with:** localized API error message; log `request_id` server-side only

---

## Component Index

| Component | Status | Guideline section |
|-----------|--------|-------------------|
| Button | ✅ | Button |
| Input / TextArea | ✅ | Input |
| Dropdown | 🟡 | Dropdown |
| Search | 🟡 | Search |
| Command Bar | 🟡/📋 | Command Bar |
| Card | ✅/🟡 | Card |
| Table | ✅ | Table |
| Badge | ✅ | Badge |
| Status Chip | 🟡 | Status Chip |
| KPI | 🟡 | KPI |
| Tabs | 🟡 | Tabs |
| Breadcrumbs | 📋 | Breadcrumbs |
| Dialog | 🟡 | Dialog |
| Drawer | 🟡 | Drawer |
| Split View | 🟡 | Split View |
| Kanban | 📋 | Kanban |
| Timeline | 🟡 | Timeline |
| Calendar | 📋 | Calendar |
| Charts | 🟡 | Charts |
| Activity Feed | 🟡 | Activity Feed |
| Notification Center | 🟡 | Notification Center |
| Approval Card | 📋 | Approval Card |
| Investor Card | 🟡 | Investor Card |
| Inventory Card | 📋 | Inventory Card |
| Document Card | 🟡 | Document Card |
| Task Card | 📋 | Task Card |
| AI Insight Card | 📋/🟡 | AI Insight Card |
| AI Summary | 🟡 | AI Summary |
| AI Recommendation | 🟡 | AI Recommendation |
| AI Warning | 📋 | AI Warning |
| AI Explanation | 📋 | AI Explanation |
| AI Confidence | 📋 | AI Confidence |
| AI Actions | 🟡 | AI Actions |
| Human Approval | 🟡 | Human Approval |
| Cash Flow | 🟡 | Cash Flow |
| Pipeline | 🟡 | Pipeline |
| Construction Health | 📋/🟡 | Construction Health |
| Investor Health | 🟡 | Investor Health |
| Portfolio Health | 🟡 | Portfolio Health |
| Risk Card | 🟡 | Risk Card |
| PageHeader | ✅ | Header |
| Toolbar | 🟡 | Toolbar |
| Filters | 🟡 | Filters |
| Content | 🟡 | Content |
| Details | 🟡 | Details |
| AI Panel | 📋 | AI Panel |
| LoadingState | ✅ | LoadingState |
| EmptyState | ✅ | EmptyState |
| ErrorState | ✅ | ErrorState |

**Totals:** ✅ 9 · 🟡 32 · 📋 12 (some dual 🟡/📋)

---

## GOVERNANCE CROSS-REFERENCE

| Topic | Document |
|-------|----------|
| IODL philosophy & acceptance | [DESIGN_LANGUAGE.md](./DESIGN_LANGUAGE.md) |
| Tokens & CSS map | [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) |
| Layout & forms | [UI_GUIDELINES.md](./UI_GUIDELINES.md) |
| AI behavior | [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) |

---

*Product Design Sprint 2 — UI Component Guidelines v1.0. Documentation only.*
