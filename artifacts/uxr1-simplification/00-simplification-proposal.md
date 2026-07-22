# 00 — Complete Simplification Proposal

**UXR1 · INVESTHOME OS · 2026-07-21**  
**Status:** Proposal for approval only — see [`APPROVAL-GATE.md`](./APPROVAL-GATE.md)

---

## 1. Problem statement

The product currently exposes **~292 App Router pages** across dashboard, workspaces (CRM + Marketing), company, portal, investor, and admin. Daily operators face:

1. **Identity fragmentation** — lead / contact / investor / customer treated as separate apps.
2. **Duplicate commercial surfaces** — Sales kanban, CRM pipeline, Marketing leads, Executive pipeline widgets.
3. **Marketing bloat** — ~82 workspace routes and ~30 nav items; many table-first stubs.
4. **Table-first inventory & projects** — units and projects lack visual-primary UX.
5. **Chart noise** — decorative/unsupported donuts and BI placeholders without definition, source, or empty honesty.
6. **Platform leakage** — data platform, feature flags, API clients, design-system spikes appear near normal work.

Backend and domain APIs are largely sound. UXR1 simplifies **information architecture and daily UX**, not schema deletion.

---

## 2. Canonical product model (design target)

### Primary (normal users)

| Nav item | Purpose | Target route (proposal) |
|----------|---------|-------------------------|
| **Dashboard** | Daily command center | `/dashboard` |
| **Customers** | Unified person journey (lead → buyer → investor) | `/dashboard/customers` |
| **Sales** | Opportunity kanban + matching | `/dashboard/sales` |
| **Inventory** | Visual unit cards + availability | `/dashboard/inventory` |
| **Projects** | Visual project cards + detail | `/dashboard/projects` |
| **Marketing** | Campaign / channel home | `/dashboard/marketing` |
| **Content Studio** | Blog / social / email / assets | `/dashboard/marketing/content` |
| **Calendar** | Cross-module schedule | `/dashboard/calendar` |
| **Tasks** | Cross-module work queue | `/dashboard/tasks` |
| **Documents** | Files + knowledge surface | `/dashboard/documents` |
| **Reports** | Honest operational reports | `/dashboard/reports` |

### Restricted secondary

| Nav item | Audience |
|----------|----------|
| **Finance** | Finance / exec roles |
| **AI** | Permission-gated |
| **Admin** | Admins only |
| **Settings** | Company / settings permission |

### Hidden from normal users (keep backend)

Platform / G15, BI explorer internals, automation engine, design-system spikes, metric catalog, data lineage, API marketplace, external-user admin, contractor/vendor/MGA expansion — see `14-modules-hidden.md`.

---

## 3. Identity journey (Customers)

```
Lead (new) → Qualified prospect → Opportunity (Sales)
                                  ↓
                         Buyer / Reservee
                                  ↓
                         Investor (if capital path)
                                  ↓
                         Customer (active relationship)
```

**One profile shell** with lifecycle badges and role tabs. Do not maintain three separate “apps” for the same person. CRM contacts/companies become detail/relationship layers under Customers, not parallel homes.

---

## 4. Sales stages (kanban)

Align with existing opportunity stages in Sales workspace (keep backend enums):

| Stage | Daily meaning |
|-------|---------------|
| New / Intake | Unworked or marketing-handed leads |
| Qualified | Sales-accepted |
| Meeting scheduled | Appointment booked |
| Proposal sent | Offer out |
| Soft hold | Temporary unit hold |
| Reservation | Formal reservation |
| Deposit pending | Awaiting deposit |
| Contract | Contract in progress |
| Won | Closed won |
| Lost | Closed lost |

Pipeline board is primary; list is secondary. Matching inventory is a first-class panel from the opportunity card/drawer.

---

## 5. Inventory & Projects visual reset

- **Inventory:** card grid primary (photo / floorplate placeholder, unit id, beds/area, price, single primary status + secondary chips). Table = power view toggle.
- **Projects:** card grid primary (cover, name, phase, unit progress, health). Detail = tabs for overview / units / timeline / docs / team — financial projections behind “Details”.

---

## 6. Marketing + Content Studio

- Marketing home = production overview + campaign list + channel health (not 30-item rail).
- Content Studio at `/dashboard/marketing/content` consolidates blog, social, email drafts, templates, assets.
- Deep channel tools (WhatsApp, SMS, advertising, attribution, forecasting) remain as **advanced** / archived-from-nav until needed.

---

## 7. Dashboard chart contract (meaningful only)

Every Dashboard widget must declare: **definition · time range · source · drill-down · empty state**.

| Widget | Chart type | Exception notes |
|--------|------------|-----------------|
| Today | Checklist / agenda strip | Not a chart |
| New Leads | Sparkline or KPI + count | — |
| Follow-Ups | List + overdue count | — |
| Sales Funnel | **FunnelChart** | Intentional; conversion order matters |
| Unit Availability | **DonutChart** (status mix) | **Intentional exception** to prior “no donut” DS preference for sales UX |
| Monthly Sales | Bar or Area (time series) | — |
| Active Projects | Progress rows | — |
| Marketing Production | Bar (content/campaigns by week) | — |
| Calendar | Mini month / agenda | — |
| Tasks | Queue list | — |

Prior G8/G95 “prefer bars/sparklines over donuts” remains for **Executive/BI trends**. Unit status donut + sales funnel are **documented UXR1 exceptions**.

---

## 8. Design direction (visual reset — post-approval)

- Calm real-estate OS: clear hierarchy, generous whitespace, one composition per viewport.
- Brand-forward shell; avoid purple-gradient / cream-serif / broadsheet clichés.
- Cards only where interaction requires them (inventory/project grids, kanban cards).
- Motion: subtle board transitions, card hover lift, chart empty→ready — not decorative noise.
- Typography: distinctive product fonts already in DS; do not introduce Inter/Roboto stacks.

*(Visual polish is post-approval; this package is wireframe-level only.)*

---

## 9. Preserve backend mentally

| Keep (API / domain) | UI treatment |
|---------------------|--------------|
| Leads, Opportunities, Investors, Parties | Unify in Customers + Sales UI |
| Inventory assets, reservations, pricing | Inventory cards + Sales match |
| Projects, milestones, costs | Project cards + detail tabs |
| Marketing campaigns, content, channels | Marketing home + Content Studio |
| Finance, Documents, Knowledge, AI, Automation | Restricted or merged nav |
| Admin platform / G15 entities | Admin-only; no delete |
| Portal / Investor exteriors | Out of UXR1 staff-shell scope; note dual portal risk |

**No schema drops in UXR1.** Archive = hide from nav + redirect; soft-deprecate routes.

---

## 10. Success criteria (when later implemented)

1. Normal user sidebar ≤ ~12 primary items.
2. One Customer profile for lead/buyer/investor journey.
3. Sales kanban is the only commercial board for deals.
4. Inventory and Projects open as visual cards by default.
5. Dashboard widgets all have definition/source/empty/drill-down.
6. Marketing Content Studio is the single content creation home.
7. Platform modules invisible to non-admins.

---

## Related deliverables

See [`README.md`](./README.md) for the full numbered set (01–20 + wireframes).
