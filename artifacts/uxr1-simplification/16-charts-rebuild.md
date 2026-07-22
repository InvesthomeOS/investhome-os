# 16 — Charts to Rebuild

Every rebuilt chart must ship with: **definition · time range · source · drill-down · empty/error states**.

---

## Dashboard (priority)

| Widget | Type | Definition | Time | Source (conceptual) | Drill-down |
|--------|------|------------|------|---------------------|------------|
| New Leads | KPI + optional sparkline | Leads created or assigned unworked | Today / 7d | leads metrics | Customers or Sales |
| Sales Funnel | **FunnelChart** | Open opportunities by stage | Open pipeline | sales pipeline API | `/dashboard/sales` |
| Unit Availability | **DonutChart** | Share by primary availability | As-of now | inventory summary | `/dashboard/inventory` |
| Monthly Sales | BarChart or AreaChart | Won count or volume by month | 6 / 12 months | closed opportunities | Sales / Reports |
| Active Projects | ProgressChart rows | Progress or funding/health | Snapshot | projects summary | Projects |
| Marketing Production | BarChart | Content/campaigns shipped | This week | marketing production | Marketing / Content |

**Exception record:** Donut for unit status + Funnel for sales are intentional overrides of prior “no donut” preference for sales UX.

---

## Domain rebuilds

| Surface | Rebuild | Notes |
|---------|---------|-------|
| Sales home strip | Compact funnel or stage counts | Must match board stages |
| Inventory header | Mini donut or status chips + counts | Same definition as Dashboard |
| Project detail | Progress + optional mini funnel filtered to project | No decorative extras |
| Marketing home | Production bars + channel health | Empty if disconnected |
| Reports | Thin curated set only | No explorer for normals |

---

## Chart types preferred elsewhere

| Use | Type |
|-----|------|
| Trends | Line / Area / Sparkline |
| Categorical volume | Bar |
| Target attainment | Progress |
| Conversion order | Funnel |
| Status mix (units) | Donut (exception) |
| Milestones | Timeline |

---

## Acceptance checklist (per chart)

- [ ] Business question stated
- [ ] Fields listed
- [ ] Time range control or explicit as-of
- [ ] API/source named
- [ ] Drill-down route
- [ ] Empty + error copy (no fake series)
- [ ] Locale formatting (TR default)
