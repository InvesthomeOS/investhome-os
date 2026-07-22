# Executive Dashboard — Visual Direction (D1C)

**Product:** INVESTHOME OS  
**Primary language:** Turkish (TR + EN for all visible strings)  
**Prototype route:** `/dashboard/admin/design-system/executive-dashboard`  
**Depends on:** [d1c-visual-review.md](./d1c-visual-review.md), IA, grid, chart matrix, DS v1  

---

## 1. Page frame

| Element | Direction |
|---------|-----------|
| Canvas | Soft warm neutral `--background-canvas` (`#F7F4EF`). **No** full-page gradients. **No** heavy black-gold chrome. |
| Content | `ContentContainer` → `AppPage` with class `ds-exec-proto`. |
| Header | Compact **operational** `PageHeader`: title “Yönetici özeti / Executive overview”, short one-line subtitle, **no** marketing landing eyebrow stack. |
| Actions | `DateRangeControl` + refresh `IconButton` + optional customize `WidgetMenu` / ghost `Button`. Prototype badge (`StatusBadge` warning) + back link. |
| Banner | Persistent caption note: prototype-only demo data; `data-prototype-banner="PROTOTYPE_DEMO_DATA_ONLY"`. |
| Demo QA controls | Collapsed / secondary row below header — never primary visual weight. |

---

## 2. Cards / widgets

| Rule | Spec |
|------|------|
| Surface | White elevated `--surface-default` + `--shadow-card` + border + radius medium |
| Independence | One business question per `WidgetShell` / `MetricCard` |
| Separation | Calendar · Tasks/Approvals · Communications · AI = **four** shells |
| Nesting | No card-in-card for MetricCards inside KPI strip |
| Urgency | Severity via `StatusBadge` (danger/warning/info) — not colored full-card backgrounds |

---

## 3. Typography

| Role | Token / class |
|------|----------------|
| Page title | `ds-type-page-title` (compact operational, not display) |
| Widget title | WidgetShell title (`ds-type-card-title` equivalent) |
| Body / lists | `ds-type-body-small` |
| Captions / meta | `ds-type-caption` |
| Metrics | MetricCard medium size in strip |
| AI item title | Strong body-small; reason/impact as caption |

Avoid display type on executive chrome.

---

## 4. Color

| Role | Use |
|------|-----|
| Brand primary / secondary | Links, primary CTAs, chart series 1–2 — **restrained** |
| Accent teal | Optional series 3; never full-page wash |
| Status success / warning / danger / info | Semantic only |
| Status AI | Small badge / left accent bar (`--status-ai`) — **no purple glow**, no neon |
| Text | `--text-primary` / `--text-secondary` / `--text-muted` |

---

## 5. Charts

| Widget | Type | Height | Notes |
|--------|------|--------|-------|
| `exec.cash_trend` | AreaChart (net) + metric summary strip (liquidity, inflows, outflows, capital) | large | Demo series only; independent shell |
| `exec.sales_funnel` | FunnelChart | standard | Separate from finance |
| `exec.investor_pulse` | DonutChart + caption metrics | compact/standard | Related to sales, **not merged** |
| `exec.projects_progress` | ProgressChart rows + risk badge + milestone | compact per row | Not accounting dump |
| `exec.marketing_pulse` | Compact BarChart or Sparkline + 2–3 metrics | compact | Demo + CTA to Marketing workspace |
| KPI strip | TrendIndicator; optional Sparkline when demo series present | sparkline | ≤5 cards |

Legend + sr-only summaries required. Empty/loading/error via ChartContainer / WidgetShell.

---

## 6. Icons

Use `IhIcon` stroke set only (`alert`, `refresh`, `calendar`, `sparkles`, `finance`, `sales`, `investors`, `projects`, `marketing`, `inbox`, `clock`, `arrowRight`). Size `sm`/`md` in headers. No emoji decoration.

---

## 7. Status

| Tone | When |
|------|------|
| danger | Critical alerts, at-risk projects |
| warning | Funding gaps, overdue soft signals, prototype banner |
| info | Informational alerts, advisory meta |
| ai | AI Decision Center badge only |
| success | On-track project health |
| neutral | Calm empty “no exceptions” |

---

## 8. AI Decision Center

- **Not a chat.** Prioritized decision items.
- Each item: kind badge (priority / risk / opportunity) · title · **reason** · **impact** · **action** link to existing route (`/dashboard/finance`, `/dashboard/sales`, `/dashboard/projects`, `/dashboard/investors`).
- Visual: left AI accent bar (2px `--status-ai`) on item row; small `StatusBadge tone="ai"` on shell.
- Never merge with tasks, calendar, or communications.

---

## 9. Warning / empty / loading

| State | Treatment |
|-------|-----------|
| Warning banner | Prototype demo notice (caption + badge) |
| Empty | Calm EmptyState / MetricCard emptyLabel — no celebration |
| Loading | SkeletonState / MetricCard skeleton / ChartContainer loading |
| Error | ErrorState compact + Retry affordance (demo setState) |
| Permission denied | Communications widget shows restricted copy when demo permission off |

---

## 10. Spacing

| Token | Use |
|-------|-----|
| 24px (`--ds-grid-gap-desktop`) | Desktop/tablet grid gap |
| 16px (`--ds-grid-gap-mobile`) | Mobile gap |
| 8 / 12 | List item internal gaps |
| 16 / 20 | Widget body padding (shell default) |
| Reduce | Extra PageSection padding where redundant |

---

## 11. Right rail (≥1440 optional)

- `RightRail` + `RightRailCard`: quick actions + footnotes.
- Never steals L1/L2 priority; stacks under main on tablet/mobile.
- AI stays in main grid (span 4 beside cash trend), not inside rail mail/tasks.

---

## Desktop layouts (visual)

### 1440

```
Header (title · DateRange · refresh · customize · demo badge)
Alerts span 12
KPI ×5
Cash trend span 8 | AI Decision span 4
Tasks span 6 | Calendar span 6
Sales span 6 | Investors span 6
Projects span 6 | Marketing span 6
Communications span 4 | RightRail quick actions (optional)
```

### 1280

Same IA; AI may tighten description; KPIs wrap 3+2; rail stacks or hides if crowding.

### Tablet (8-col)

Full-width stack after KPIs: cash → AI → tasks → calendar → sales → investors → projects → marketing → comms.

### Mobile order (final D1C)

| Order | Widget ID |
|------:|-----------|
| 1 | `exec.alerts` |
| 2 | `exec.kpi_cash` |
| 3 | `exec.kpi_pipeline` |
| 4 | `exec.kpi_investors` |
| 5 | `exec.kpi_open_deals` |
| 6 | `exec.kpi_projects` |
| 7 | `exec.ai_decision` |
| 8 | `exec.cash_trend` |
| 9 | `exec.tasks_approvals` |
| 10 | `exec.calendar_deadlines` |
| 11 | `exec.sales_funnel` |
| 12 | `exec.investor_pulse` |
| 13 | `exec.projects_progress` |
| 14 | `exec.marketing_pulse` |
| 15 | `exec.communications` |
| 16 | `exec.quick_actions` (rail) |

---

## Interaction

- Canonical `Button`, `IconButton`, `DateRangeControl`, `WidgetMenu`, `Link` drill-downs.
- Restrained transitions: opacity/shadow on shell hover via existing DS motion; respect `prefers-reduced-motion`.
- Refresh toggles demo “last refreshed” caption only — **no** production API calls.

---

## Out of scope

- Production executive implementation / API wiring  
- Invented nav routes  
- Merging calendar+tasks+mail+AI  
- Competing design system or new chart libraries  
- Fake data on production routes  

---

*Approved visual direction for D1C prototype refinement.*
