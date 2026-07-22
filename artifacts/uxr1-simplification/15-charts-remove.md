# 15 — Charts to Remove

Remove from **normal production surfaces** (or replace with empty/KPI). Keep components in design-system showcase.

---

## Remove / demote

| Chart / pattern | Where today | Why remove |
|-----------------|-------------|------------|
| Decorative donuts without status definition | Older executive production, thin BI domains | No definition/source; conflicts with trend readability |
| Placeholder BI charts with fake/empty series shown as real | `/dashboard/analytics/*` domain pages | Dishonest |
| Duplicate pipeline visualizations | Executive + CRM strip + Sales board showing same funnel thrice | One funnel on Dashboard/Sales |
| Spike charts in TailAdmin / GitHub previews | Admin spikes | Not product |
| Multi-donut grids | Any dense dashboard | Noise |
| Marketing “health” charts when channel disconnected | Marketing dashboards | Fake green |

---

## Do **not** remove (rebuild instead — see 16)

- Sales Funnel (FunnelChart) on Dashboard — intentional
- Unit Availability donut on Dashboard/Inventory summary — **intentional UXR1 exception**
- Time-series monthly sales bars/areas with real closed data
- Project progress bars

---

## Policy clarification

Prior DS guidance (“prefer line/sparkline; avoid oversized donuts”) remains for **Executive trend storytelling**.  
UXR1 **explicitly allows**:

1. Unit status **DonutChart**
2. Sales **FunnelChart**

Documented in `04-wireframe-dashboard.md` and `16-charts-rebuild.md`.
