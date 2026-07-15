# Investhome OS Design Language (IODL)

**Document type:** Product Design Sprint 2 deliverable  
**Last updated:** 2026-07-15  
**Audience:** Product, design, engineering  
**Status:** Official design language specification (with implementation honesty)

**Related governance:** [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) · [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md) · [UI_GUIDELINES.md](./UI_GUIDELINES.md) · [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) · [HOME_EXPERIENCE.md](./HOME_EXPERIENCE.md) · [WORKSPACE_NAVIGATION.md](./WORKSPACE_NAVIGATION.md) · [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) · [PRODUCT_VISION.md](./PRODUCT_VISION.md) · [CODING_STANDARDS.md](./CODING_STANDARDS.md) · [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

---

## Implementation Legend

| Marker | Meaning |
|--------|---------|
| ✅ **Implemented** | React primitive in `@investhome/ui` and/or production CSS in `globals.css` |
| 🟡 **CSS-only** | Styled in `globals.css` or workspace markup; not yet in `@investhome/ui` |
| 📋 **Spec-only** | Defined in IODL; no production component yet |

**Repository truth always overrides this document.**

---

## SECTION 1 — Design Philosophy

Investhome OS is an **operating system for real estate development** — not a cluttered ERP. The Investhome OS Design Language (IODL) governs every surface: workspaces, Home, global overlays, and AI-assisted flows.

### Core attributes

| Attribute | Meaning for IODL |
|-----------|------------------|
| **Calm** | Low visual noise; generous whitespace; one focal point per region |
| **Professional** | Restrained color; no playful gradients; enterprise trust |
| **Premium** | Subtle depth, crisp typography, polished micro-interactions |
| **Data-first** | Numbers and status legible at a glance; tables and KPIs over decoration |
| **AI-native** | AI assists inline — summaries, recommendations, warnings — without hijacking workflow |
| **Enterprise** | Permission-aware, auditable, scalable to 12+ workspaces |
| **Fast** | Perceived speed via skeletons, progressive load, keyboard paths |
| **Minimal** | Every element earns its place; progressive disclosure over dense forms |
| **Human-centered** | Humans decide; AI recommends; undo and confirmation for mutations |

### Anti-patterns (never)

- Cluttered ERP dashboards with 20 equal-weight widgets
- Multiple competing primary actions on one screen
- Decorative animation, illustration-heavy empty states, or gamification
- AI auto-executing financial, inventory, or approval actions
- Duplicate entity CRUD in Home, Executive, and workspace list views
- Light-mode-only or dark-mode-only assumptions without token strategy

### Alignment with product docs

- **Home ≠ Executive** — personal command center vs strategic KPI dashboard ([HOME_EXPERIENCE.md](./HOME_EXPERIENCE.md) H7, [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) P7)
- **Workspaces = responsibility lenses** — not database modules ([WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md))
- **AI levels disclosed honestly** — L2 heuristic today; L3+ gated ([AI_PRINCIPLES.md](./AI_PRINCIPLES.md))

---

## SECTION 2 — Visual Identity

### Typography

| Role | Spec | Implementation |
|------|------|----------------|
| **Font stack** | Inter, system-ui, Segoe UI, sans-serif | ✅ `globals.css` `html, body` |
| **Page title** | 1.75–2.5rem, weight 700, letter-spacing −0.02em | ✅ `.dashboard__title` |
| **Eyebrow / section label** | 0.75rem, uppercase, letter-spacing 0.04–0.12em, muted | ✅ `.dashboard__eyebrow`, table headers |
| **Body** | 0.875–1rem, line-height 1.5 | ✅ default |
| **Caption / meta** | 0.75–0.8125rem, `--muted` | ✅ `.leads__muted`, `.dashboard__subtitle` |
| **KPI value** | 1.125–1.375rem, weight 700 | 🟡 `.investors__stat-card strong` |
| **Monospace (future)** | Tabular nums for finance tables | 📋 |

Scale reference: [DESIGN_SYSTEM.md § Typography](./DESIGN_SYSTEM.md#typography-scale).

### Spacing

Base unit **4px**. Common steps: 4, 8, 12, 16, 20, 24, 32, 40px.

| Context | Typical spacing | Class pattern |
|---------|-----------------|---------------|
| Page padding | 2.5rem 1.5rem | `.dashboard` |
| Card padding | 1–1.25rem | `.dashboard__card`, `.investors__stat-card` |
| Form field gap | 0.375–0.75rem | `.auth-form__field`, `.leads__field` |
| Grid gap | 1rem | `.dashboard__grid`, stats grids |
| Toolbar margin-bottom | 1–1.25rem | `.leads__toolbar`, `.finance__tabs` |

Full token table: [DESIGN_SYSTEM.md § Spacing](./DESIGN_SYSTEM.md#spacing-scale).

### Grid

| Layout | Columns | Breakpoint behavior |
|--------|---------|---------------------|
| **App shell** | 240px sidebar + fluid content | ✅ `.dashboard-shell` |
| **Module cards** | `auto-fit minmax(220px, 1fr)` | ✅ `.dashboard__grid` |
| **Stats / KPIs** | 2–8 columns by workspace | 🟡 `.investors__stats`, `.finance__stats` |
| **Executive layout** | Main + 280px rail | 🟡 `.executive__layout` |
| **Admin split** | 1.2fr / 1fr | 🟡 `.admin-split` |
| **Content max-width** | 1200px centered | ✅ `.dashboard` |

### Elevation

Investhome uses **border + subtle surface contrast** over heavy shadows.

| Level | Treatment | Usage |
|-------|-----------|-------|
| **L0 — Base** | `--bg` | Page background |
| **L1 — Surface** | `--surface` + 1px `--border` | Cards, panels, inputs |
| **L2 — Raised** | Linear gradient on card (optional) | `.dashboard__card` |
| **L3 — Overlay** | Fixed scrim rgba(3–15, 23, 42, 0.35–0.72) | Modals, drawers, search |
| **L4 — Floating** | Box-shadow on search palette | `.global-search-palette` |

### Border radius

| Token | Value | Usage |
|-------|-------|-------|
| **sm** | 0.375–0.5rem | Inputs, tabs, small chips |
| **md** | 0.625–0.75rem | Buttons, fields, attention items |
| **lg** | 0.875–1rem | Cards, panels, modals |
| **pill** | 999px | Badges, status chips, auth submit |

### Shadow system

Shadows are **sparse**. Primary depth cue is border + scrim.

| Shadow | CSS | Usage |
|--------|-----|-------|
| **Palette** | `0 24px 48px rgba(15, 23, 42, 0.18)` | Global search |
| **Drawer** | `-8px 0 24px rgba(15, 23, 42, 0.12)` | Notification drawer |
| **Focus ring** | `outline: 2px solid var(--accent); outline-offset: 2px` | Keyboard focus ✅ |

### Iconography

| Rule | Status |
|------|--------|
| No standardized icon library yet | 📋 Lucide-style recommended ([INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) E9) |
| Unicode / text abbreviations in search results | 🟡 `.global-search-result__icon` |
| Status dots via CSS pseudo-elements | 🟡 `.dashboard__status::before` |
| Icon + label for nav (target) | 📋 |

### Illustration style

- **Default:** No custom illustrations in product UI
- **Empty states:** Text + optional single-line icon; dashed border container (`.documents-empty`)
- **Marketing / auth:** Minimal; auth uses card-only layout
- **Charts:** CSS bars and grids — not illustration

### Charts

| Type | Style | Status |
|------|-------|--------|
| **Horizontal bar** | 0.5rem height, accent fill, muted track | 🟡 `.executive__pipeline-bar` |
| **Dual bar (cash flow)** | Green in / red out, 2px gap | 🟡 `.executive__cashflow-*` |
| **KPI delta** | 0.75rem muted caption | 🟡 `.executive__card-delta` |
| **Future time-series** | Monochrome lines, status-colored thresholds | 📋 |

No chart library standardized — prefer CSS-native for executive summaries until dedicated viz ADR.

### Cards

| Variant | Purpose | Status |
|---------|---------|--------|
| **Module card** | Workspace launcher link | 🟡 `.dashboard__card` |
| **Stat / KPI card** | Metric + label | 🟡 `.investors__stat-card` |
| **Attention card** | Severity border | 🟡 `.executive__attention-item` |
| **Document card** | Grid tile | 🟡 `.documents-grid__card` |
| **Generic card** | Title + description | ✅ `@investhome/ui` `Card` (📋 `.ih-card` CSS pending) |

### Color usage

| Role | Token | Hex (dark default) |
|------|-------|-------------------|
| Background | `--bg` | `#0b1220` |
| Surface | `--surface` | `#111a2e` |
| Border | `--border` | `#1f2a44` |
| Text | `--text` | `#e8edf7` |
| Muted | `--muted` | `#9aa8c7` |
| Accent | `--accent` | `#3b82f6` |
| Accent muted | `--accent-muted` | `#1d4ed8` |
| Success | `--success` | `#22c55e` |

Brand colors from Company Foundation apply at runtime via settings — not yet global CSS injection ([DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md)).

**Usage rules:**

- Accent for primary actions, active nav, links, unread notification accent
- Muted for secondary text, table headers, meta
- Never use accent for body text blocks
- Status colors only for status — not decoration

### Status colors

See [Section 12 — Status System](#section-12--status-system).

### Dark / light mode

| Mode | Status |
|------|--------|
| **Dark (default)** | ✅ `:root` tokens in `globals.css` |
| **Light** | 📋 Token pair planned; `color-scheme: light dark` declared |
| **System** | 📋 User preference via Home personalization ([HOME_EXPERIENCE.md](./HOME_EXPERIENCE.md) §13) |
| **Brand override** | 🟡 Settings brand preview uses light-oriented preview panel |

Strategy: CSS custom properties with `[data-theme="light"]` / `[data-theme="dark"]` on `html` — see [DESIGN_SYSTEM.md § Theming](./DESIGN_SYSTEM.md#dark--light-mode-strategy).

### Accessibility (visual)

- Minimum 4.5:1 contrast for body text (target WCAG AA)
- Focus visible on all interactive elements
- Color never sole indicator of status — pair with label/icon
- `prefers-reduced-motion` respected for animations (target)

---

## SECTION 3 — Interaction Principles

Thirty rules governing behavior across Investhome OS. Cross-reference [HOME_EXPERIENCE.md](./HOME_EXPERIENCE.md) Home principles and [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) IA principles.

| # | Principle | Implication |
|---|-----------|-------------|
| I1 | **One primary action** | Each view has at most one filled primary button |
| I2 | **Never overload** | Max 5 critical alerts visible; collapse secondary |
| I3 | **Context before action** | Show entity name, project, date before approve/delete |
| I4 | **Progressive disclosure** | Drawers and tabs reveal detail; lists stay scannable |
| I5 | **Keyboard-first** | `Ctrl+K` search; arrow navigation in palettes ✅ |
| I6 | **Undo whenever possible** | Confirm destructive actions; archive over hard delete |
| I7 | **AI assists without interrupting** | Inline panels; no modal AI unless user invokes |
| I8 | **Human approval for mutations** | Finance, inventory, drawing proposals ([AI_PRINCIPLES.md](./AI_PRINCIPLES.md)) |
| I9 | **Permission-first** | Hide unavailable actions; filter search results |
| I10 | **Context preservation** | Overlays don't navigate away ([IA G1](./INFORMATION_ARCHITECTURE.md)) |
| I11 | **Drawer over page** | Entity detail in slide-over; preserve list scroll |
| I12 | **Deep link handoff** | Global results open workspace + drawer |
| I13 | **No duplicate CRUD** | Home links to workspace create flows — no forms on Home |
| I14 | **Escape closes** | Modals, drawers, search palette ✅ |
| I15 | **Loading honesty** | Skeleton or explicit loading — never blank flash |
| I16 | **Error localization** | TR/EN messages; actionable retry |
| I17 | **Empty states guide** | Onboard with next action — never blank screen |
| I18 | **Bilingual always** | TR default; EN merge-fallback ([CODING_STANDARDS.md](./CODING_STANDARDS.md)) |
| I19 | **Desktop-first** | Design 1280px+; degrade gracefully |
| I20 | **Touch targets ≥44px** | Mobile interactive minimum (target) |
| I21 | **Single notification truth** | Bell drawer is canonical; Home aggregates subset |
| I22 | **Search before menus** | `Ctrl+K` promoted in header and Home hint |
| I23 | **Batch with care** | Batch approve only same type + permission |
| I24 | **Streaming AI** | Token stream in AI panels; cancel available (target) |
| I25 | **Activity attribution** | All actions log to Activity ([EVENT_MODEL.md](./EVENT_MODEL.md)) |
| I26 | **Confidentiality follows data** | UI gates match document level |
| I27 | **Demo honesty** | Demo banner when `is_demo` ✅ `.leads__demo-banner` |
| I28 | **Optimistic UI sparingly** | Prefer server confirmation for money/inventory |
| I29 | **Consistent form patterns** | Label above field; trim strings; null optional API fields |
| I30 | **Incremental adoption** | New UI uses `@investhome/ui`; refactor module-by-module |

---

## SECTION 4 — Component Library

Canonical catalog for Investhome OS. Per-component guidelines: [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md). Technical tokens: [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md).

### Foundation components

| Component | Purpose | Status | Notes |
|-----------|---------|--------|-------|
| **Buttons** | Primary, secondary, ghost, danger actions | ✅ `@investhome/ui` | Maps `.leads__button--*` |
| **Inputs** | Text, textarea, labeled fields | ✅ `@investhome/ui` | `.auth-form__field`, `.leads__field` |
| **Dropdowns** | Select filters, language picker | 🟡 CSS-only | Native `<select>` styled |
| **Search** | Global entity search overlay | 🟡 CSS-only | `.global-search-*` ✅ functional |
| **Command Bar** | Search + command + NL (target) | 🟡 Partial | Extends search palette 📋 NL mode |
| **Cards** | Content grouping, KPIs, links | ✅ / 🟡 | `Card` + `.dashboard__card` |
| **Tables** | Dense data lists | ✅ `@investhome/ui` | `.admin-table`, `.leads__table` |
| **Badges** | Status, nav soon, demo tags | ✅ `@investhome/ui` | `.ih-badge--*`, `.leads__demo-tag` |
| **Status Chips** | Inline entity status | 🟡 CSS-only | `.leads__status`, `.notification-priority` |
| **KPIs** | Stat cards with label + value | 🟡 CSS-only | `.investors__stat-card` |
| **Tabs** | Workspace section switching | 🟡 CSS-only | `.finance__tab`, `.documents-tabs__tab` |
| **Breadcrumbs** | Hierarchy navigation | 📋 Spec-only | Back link pattern 🟡 `.dashboard__back` |
| **Dialogs** | Create/edit modals | 🟡 CSS-only | `.leads-modal` |
| **Drawers** | Entity detail slide-overs | 🟡 CSS-only | `.leads-drawer`, `.notification-drawer` |
| **Split View** | List + detail side-by-side | 🟡 CSS-only | `.admin-split` |

### Data visualization & workflow

| Component | Purpose | Status | Notes |
|-----------|---------|--------|-------|
| **Kanban** | Pipeline boards (Sales, Construction) | 📋 Spec-only | Leads uses table today |
| **Timeline** | Activity / audit chronology | 🟡 CSS-only | `.activity-timeline` |
| **Calendar** | Events, meetings, deadlines | 📋 Spec-only | Executive deadlines 🟡 interim |
| **Charts** | Pipeline bars, cash flow | 🟡 CSS-only | Executive workspace |
| **Activity Feed** | Cross-entity event stream | 🟡 CSS-only | Activity workspace + entity panels |
| **Notification Center** | Priority-grouped alerts | 🟡 CSS-only | Header bell + drawer ✅ |

### Domain cards

| Component | Purpose | Status | Notes |
|-----------|---------|--------|-------|
| **Approval Card** | Pending approval row with actions | 📋 Spec-only | Finance approve 🟡; Home widget 📋 |
| **Investor Card** | Investor summary in lists/grids | 🟡 CSS-only | Table rows + stat cards |
| **Inventory Card** | Unit/building tile | 📋 Spec-only | [UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md) |
| **Document Card** | File tile with extension badge | 🟡 CSS-only | `.documents-grid__card` |
| **Task Card** | Assigned work item | 📋 Spec-only | Tasks entity not implemented |
| **AI Insight Card** | AI summary with attribution | 📋 Spec-only | Document intelligence tabs 🟡 |

### Shell & layout

| Component | Purpose | Status |
|-----------|---------|--------|
| **Page Header** | Title, eyebrow, actions | ✅ `@investhome/ui` |
| **Loading State** | Inline loading message | ✅ `@investhome/ui` |
| **Empty State** | Zero-data guidance | ✅ `@investhome/ui` |
| **Error State** | Failure with retry | ✅ `@investhome/ui` |

### Component count summary

| Status | Count (Section 4) |
|--------|-------------------|
| ✅ `@investhome/ui` | 9 primitives |
| 🟡 CSS-only | 18 patterns |
| 📋 Spec-only | 8 components |

---

## SECTION 5 — AI Components

AI surfaces follow [AI_PRINCIPLES.md](./AI_PRINCIPLES.md): honest level disclosure, human approval for mutations, confidentiality gates.

| Component | Purpose | Anatomy | Status |
|-----------|---------|---------|--------|
| **AI Summary** | Condensed entity/document digest | Header + prose + "Generated · L2" footer | 🟡 Document analysis tab |
| **AI Recommendation** | Suggested next action | Icon + text + "Review" link | 🟡 Heuristic bullets in analysis |
| **AI Warning** | Risk or anomaly flag | Amber/red border + severity label | 📋 Dedicated component; notifications 🟡 |
| **AI Explanation** | Why AI ranked/suggested | Collapsible "Because…" list | 📋 Target for Home priorities |
| **AI Confidence** | Score or qualitative band | Badge: High / Medium / Low / Unknown | 📋 Show when L3+; omit for L2 |
| **AI Actions** | Action chips (summarize, extract, ask) | Chip row in document drawer | 🟡 Analyze / Ask tabs |
| **Human Approval** | Approve / reject with audit | Entity context + confirm + permission | 🟡 Drawing proposals, finance approve |

### AI component rules

1. Always show AI level (L0–L4) in footer or tooltip
2. External LLM badge when `FEATURE_EXTERNAL_AI` active
3. Confidential docs: block external AI by default — show inline reason
4. Recommended mutations open confirmation — never one-click execute
5. Regenerate requires explicit user action + activity log `actor_type=ai`

---

## SECTION 6 — Executive Components

Used in `/dashboard/executive` and future Executive Workspace Blueprint. Distinct from Home widgets ([HOME_EXPERIENCE.md](./HOME_EXPERIENCE.md) H7).

| Component | Purpose | Key elements | Status |
|-----------|---------|--------------|--------|
| **Cash Flow** | In/out comparison by period | Label, dual bars, amount columns | 🟡 `.executive__cashflow` |
| **Pipeline** | Leads funnel by stage | Stage label, bar, count, value | 🟡 `.executive__pipeline` |
| **Construction Health** | Projects by construction status | Metric list + health color | 📋 Partial via project health |
| **Investor Health** | Commitments vs funding | Overview section | 🟡 Executive API sections |
| **Portfolio Health** | Project status aggregate | on_track / attention / at_risk colors | 🟡 `.executive__health--*` |
| **Risk Cards** | Attention-required items | Severity border, title, meta, link | 🟡 `.executive__attention-item` |

### Executive layout pattern

```
[Period filters]
[Summary KPI grid — linked cards]
[Main column: Financial | Pipeline | Portfolio]
[Side rail: Deadlines | Activity snippet]
[Attention required list]
```

Skeleton: `.executive__skeleton` with shimmer animation ✅.

---

## SECTION 7 — Workspace Components

Standard anatomy for every workspace ([WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md), [WORKSPACE_NAVIGATION.md](./WORKSPACE_NAVIGATION.md)).

```
┌─────────────────────────────────────────────────────────┐
│ Header (PageHeader): title · subtitle · primary actions │
├─────────────────────────────────────────────────────────┤
│ Toolbar: filters · view toggle · export                 │
├─────────────────────────────────────────────────────────┤
│ Content: stats · table/grid · tabs                        │
├─────────────────────────────────────────────────────────┤
│ Details (drawer): sections · related · documents · AI   │
└─────────────────────────────────────────────────────────┘
         [Optional AI Panel — right rail, future]
```

| Component | Purpose | Implementation | Status |
|-----------|---------|----------------|--------|
| **Header** | Workspace identity + actions | `PageHeader` / `.dashboard__header` | ✅ |
| **Toolbar** | Filters + secondary actions | `.leads__toolbar`, `.activity__toolbar` | 🟡 |
| **Filters** | Field groups, chip filters | `.leads__filters`, `.executive__filters` | 🟡 |
| **Content** | Primary data surface | Tables, grids, tabs | 🟡 |
| **Details** | Entity drawer/modal | `.leads-drawer`, modals | 🟡 |
| **AI Panel** | Contextual Q&A / analysis | Document drawer tabs | 🟡 Partial |
| **Timeline** | Entity-scoped activity | `.activity-timeline` | 🟡 |
| **Related Items** | Cross-entity links | Drawer sections, document panels | 🟡 |

### Workspace CSS naming

BEM-style: `{module}__{element}--{modifier}` — e.g. `.leads__button--primary` ([UI_GUIDELINES.md](./UI_GUIDELINES.md)).

---

## SECTION 8 — Animation

| Rule | Specification |
|------|---------------|
| **Subtle** | Opacity, border-color, background — no bounce |
| **Fast** | 150ms default; 1200ms max for skeleton shimmer |
| **Professional** | Ease standard; no spring physics |
| **No decorative animation** | No confetti, parallax, hero animations |
| **Reduced motion** | `@media (prefers-reduced-motion: reduce)` disables shimmer (target) |

| Animation | Duration | Usage | Status |
|-----------|----------|-------|--------|
| Tab/button hover | 150ms | `.finance__tab` | ✅ |
| Skeleton shimmer | 1.2s loop | `.executive__skeleton` | ✅ |
| Drawer enter | 200ms slide (target) | 📋 CSS transition planned |
| Overlay fade | 150ms | 📋 |

---

## SECTION 9 — Loading

| Pattern | When | Component / class | Status |
|---------|------|-------------------|--------|
| **Skeletons** | Executive sections, widget shells | `.executive__skeleton` | 🟡 |
| **Progressive loading** | Home T0→T3 tiers | [HOME_EXPERIENCE.md §16](./HOME_EXPERIENCE.md) | 📋 |
| **Lazy loading** | Below-fold widgets, document preview | Intersection Observer (target) | 📋 |
| **Streaming AI responses** | Document Q&A, brief generation | Token stream + cancel (target) | 📋 |
| **Inline loading** | Button disabled + wait cursor | `:disabled`, `.dashboard__status--loading` | ✅ |
| **Table loading** | Full-width skeleton rows (target) | 📋 |
| **Spinner** | Avoid — prefer skeleton or text | `LoadingState` text only ✅ |

### Loading hierarchy

1. Shell layout immediately (SSR)
2. Critical data (alerts, list headers)
3. Primary content (table rows)
4. Secondary (AI, related items)

---

## SECTION 10 — Empty States

| Rule | Specification |
|------|---------------|
| **Helpful** | Explain what belongs here + one primary action |
| **Never blank** | Zero rows → `EmptyState` or `.documents-empty` |
| **Honest** | Don't fake data; "Coming soon" for unbuilt modules |
| **Permission-aware** | Hide empty cross-domain widgets on Home |
| **i18n** | TR/EN via message catalogs |

| Context | Message pattern | Status |
|---------|-----------------|--------|
| Empty list | Title + description + CTA button | ✅ `EmptyState` |
| Empty search | "No results" in palette | ✅ `.global-search-palette__state` |
| Empty documents | Dashed border center | ✅ `.documents-empty` |
| First-time user | Welcome checklist | 📋 [HOME_EXPERIENCE.md §15](./HOME_EXPERIENCE.md) |
| No permission | Widget hidden — not empty placeholder | 📋 |

---

## SECTION 11 — Error States

| Rule | Specification |
|------|---------------|
| **Professional** | No stack traces in UI; request ID in logs only |
| **Actionable** | Retry, go back, contact admin |
| **Localized** | TR/EN error strings |
| **Scoped** | Field errors inline; page errors in `ErrorState` |
| **Non-blocking** | Section error doesn't break whole workspace |

| Context | Pattern | Status |
|---------|---------|--------|
| Form validation | `.auth-form__error`, `.leads__error` | ✅ |
| API failure | `ErrorState` component | ✅ |
| Search error | `.global-search-palette__state--error` | ✅ |
| Degraded service | `.dashboard__status--degraded` | ✅ |
| Unavailable | `.dashboard__status--unavailable` | ✅ |

---

## SECTION 12 — Status System

Canonical statuses for Investhome OS. Map to badge tones in [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md).

| Status | Meaning | Color / token | Badge tone | Example |
|--------|---------|---------------|------------|---------|
| **Success** | Completed, healthy, approved | `#22c55e` / `--success` | `success` | Transaction approved |
| **Warning** | Attention needed, due soon | `#f59e0b` | `warning` | Obligation tomorrow |
| **Critical** | Immediate action, at risk | `#ef4444` / `#c0392b` | `danger` | Funding gap |
| **Information** | Neutral awareness | `#3498db` / accent-muted | `info` | Processing complete |
| **Pending** | Awaiting action or processing | `--muted` + pulse (target) | `default` | Drawing proposal |
| **Archived** | Inactive, historical | Muted, reduced opacity | `default` | Archived lead |
| **AI Generated** | Machine-produced content | Accent border + "AI" label | `info` | Analysis summary |
| **Needs Approval** | Human gate required | Accent inset bar | `warning` | Unread notification style |

### Notification priority mapping

| Priority | Home elevation | CSS |
|----------|----------------|-----|
| critical | Always top | `.notification-priority--critical` |
| high | Warning tier | `.notification-priority--high` |
| medium | Info tier | `.notification-priority--medium` |
| low / info | Collapsed | `.notification-priority--low` |

---

## SECTION 13 — Accessibility

Target: **WCAG 2.1 AA** readiness.

| Area | Requirement | Status |
|------|-------------|--------|
| **Keyboard** | All actions reachable; visible focus | 🟡 Search ✅; full audit 📋 |
| **Screen readers** | Semantic landmarks, `aria-label` on nav/dialogs | 🟡 Partial ([UI_GUIDELINES.md](./UI_GUIDELINES.md)) |
| **Contrast** | 4.5:1 body, 3:1 large text | 🟡 Dark theme; light audit 📋 |
| **Focus states** | `focus-visible` outline accent | ✅ Card links, buttons |
| **Dialogs** | `role="dialog"`, `aria-modal="true"`, focus trap | 🟡 Pattern documented |
| **Tables** | `<th scope="col">`, caption or aria-label | 🟡 |
| **Motion** | `prefers-reduced-motion` | 📋 |
| **Language** | `lang` on html from locale | ✅ |

---

## SECTION 14 — Responsive Behavior

**Desktop-first** — design at ≥1280px, degrade gracefully.

| Breakpoint | Layout behavior | Status |
|------------|-----------------|--------|
| **≥1280px (desktop)** | Full sidebar 240px + content + optional AI rail | ✅ |
| **1024–1279px (tablet)** | Collapsible sidebar (target); 2-col stats | 📋 |
| **768–1023px (tablet narrow)** | Sidebar → horizontal nav wrap | 🟡 `.dashboard-shell` stacks at 960px |
| **<768px (mobile)** | Bottom tab bar; full-screen drawers; FAB actions | 📋 [IA §11](./INFORMATION_ARCHITECTURE.md) |

### Responsive component rules

| Component | Desktop | Mobile |
|-----------|---------|--------|
| Tables | Horizontal scroll wrap | Card list (target) or scroll |
| Stats grid | 4–8 columns | 2 columns |
| Drawers | 420–640px slide-over | Full viewport |
| Search trigger | Label + kbd hint | Icon only ✅ |
| Executive pipeline | 4-col grid row | Stacked ✅ @1100px |

---

## SECTION 15 — Design Principles

Thirty immutable IODL principles. Extend IA principles ([INFORMATION_ARCHITECTURE.md §13](./INFORMATION_ARCHITECTURE.md)) and Home principles ([HOME_EXPERIENCE.md §18](./HOME_EXPERIENCE.md)).

| # | Principle |
|---|-----------|
| D1 | Calm over cluttered |
| D2 | Data-first over decorative |
| D3 | One primary action per view |
| D4 | Progressive disclosure over dense forms |
| D5 | Keyboard-first global navigation |
| D6 | AI assists; humans approve |
| D7 | Permission-first visibility |
| D8 | SSOT — one canonical list per entity per workspace |
| D9 | Drawer-over-navigation for entity detail |
| D10 | No dead-end screens |
| D11 | Home ≠ Executive |
| D12 | Workspaces by responsibility, not DB tables |
| D13 | Bilingual TR/EN always |
| D14 | Honest implementation labels (✅/🟡/📋) |
| D15 | Incremental `@investhome/ui` adoption |
| D16 | No second styling system without ADR |
| D17 | BEM-style CSS class naming |
| D18 | i18n for all visible strings |
| D19 | Status color semantics are stable |
| D20 | Empty states guide; never blank |
| D21 | Errors are actionable and localized |
| D22 | Subtle, fast animation only |
| D23 | Desktop-first, mobile-compatible |
| D24 | Confidentiality follows the document |
| D25 | Activity logged for all mutations |
| D26 | Search indexes everything viewable |
| D27 | Brand tokens from Company Foundation — safe fallback |
| D28 | Demo mode clearly bannered |
| D29 | Spec before implementation for new components |
| D30 | Cross-reference governance docs in every deliverable |

---

## SECTION 16 — Acceptance Criteria

Measurable quality standards for IODL compliance in implementation sprints.

| ID | Criterion | Measurement |
|----|-----------|-------------|
| AC-01 | All new UI uses `@investhome/ui` primitives where they exist | Code review checklist |
| AC-02 | No new CSS framework without ADR | Architecture review |
| AC-03 | 100% visible strings in TR + EN | i18n lint / manual audit |
| AC-04 | Primary action count ≤1 per view region | Design review |
| AC-05 | Focus visible on all interactive elements | axe / manual keyboard test |
| AC-06 | Empty states on all list views | QA per workspace |
| AC-07 | Loading state on all async data fetches | QA |
| AC-08 | Error states with retry on API failures | QA |
| AC-09 | Status colors match Section 12 mapping | Visual regression |
| AC-10 | AI surfaces show level attribution | AI Principles audit |
| AC-11 | Mutation flows require confirmation | Security review |
| AC-12 | Responsive: usable at 768px without horizontal page scroll | Device test |
| AC-13 | `Ctrl+K` opens search from all dashboard routes | E2E test |
| AC-14 | Drawers preserve list context on close | UX test |
| AC-15 | Component docs updated when adding to `@investhome/ui` | PR requires doc link |
| AC-16 | DESIGN_SYSTEM.md tokens match globals.css | Diff on token change |

---

## NEXT SPRINT — Executive Workspace Blueprint

**Recommended Sprint 3 (documentation only — no UI implementation)**

### Goal

Produce the **Executive Workspace Blueprint** — a companion spec to IODL that defines every Executive section as a reusable pattern for other strategic dashboards (Marketing analytics, Construction health).

### Deliverables

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | `docs/EXECUTIVE_WORKSPACE_BLUEPRINT.md` | Full section specs: filters, KPIs, charts, drill-downs |
| 2 | **Widget inventory** | Map existing Executive API endpoints → IODL executive components |
| 3 | **Role variants** | CEO vs CFO vs Partner view differences |
| 4 | **Period & filter model** | Presets, comparison periods, project scoping |
| 5 | **Export & print spec** | Board pack layout, PDF sections |
| 6 | **Mobile read-only spec** | Which Executive sections surface on mobile |
| 7 | **AI integration points** | Brief inputs, NL queries, anomaly cards |
| 8 | **Component promotion plan** | Which 🟡 CSS patterns become `@investhome/ui` |
| 9 | **Wireframes** | Desktop + tablet for 8 existing Executive sections |
| 10 | **Acceptance criteria** | Executive-specific AC extending Section 16 |

### Executive Blueprint outline (preview)

1. Purpose & separation from Home
2. Information architecture (sections, priority, layout grid)
3. Filter bar & period presets
4. Summary KPI cards (linked navigation)
5. Financial overview (cash flow, accounts)
6. Leads pipeline (bar chart spec)
7. Investor overview (commitments, health)
8. Project portfolio & health matrix
9. Deadlines & milestones
10. Attention required (risk cards)
11. Embedded activity & notifications
12. Export & sharing
13. Loading & empty/error per section
14. Permissions & confidentiality
15. API ↔ component mapping table
16. Migration from current CSS to design system tokens

### Exit criteria

- Engineering can implement Executive refactor without product ambiguity
- All executive 🟡 components mapped to IODL Section 6
- Cross-references to IODL, IA, Home Experience complete
- Risks and missing decisions documented (extend IA MD-* where relevant)

---

## GOVERNANCE CROSS-REFERENCE

| Topic | Document |
|-------|----------|
| Technical tokens & CSS | [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) |
| Per-component usage | [UI_COMPONENT_GUIDELINES.md](./UI_COMPONENT_GUIDELINES.md) |
| Layout & BEM patterns | [UI_GUIDELINES.md](./UI_GUIDELINES.md) |
| Navigation & IA | [INFORMATION_ARCHITECTURE.md](./INFORMATION_ARCHITECTURE.md) |
| Home widgets | [HOME_EXPERIENCE.md](./HOME_EXPERIENCE.md) |
| Workspace shell | [WORKSPACE_NAVIGATION.md](./WORKSPACE_NAVIGATION.md) |
| AI behavior | [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) |
| Implementation truth | [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) |

---

*Product Design Sprint 2 — Investhome OS Design Language (IODL) v1.0. Documentation only — no UI implementation in this sprint.*
