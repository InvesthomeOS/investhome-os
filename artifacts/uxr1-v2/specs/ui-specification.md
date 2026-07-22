# UXR1 V2 — Production UI Specification

Engineer-facing specs for sections 04–11. Refine approved layouts; do not redesign.

**Visual SoT:** Design System V2 · white canvas · navy/blue/gray · global card system  
**Principles:** AI First, Human Always · Data reuse · No dark mode this sprint

---

## Shared patterns

### Cards / widgets
- Use `Card` or `WidgetShell` with `--radius-card`, `--shadow-card-premium`, `--border-card`.
- Cards must visually separate from canvas (border + shadow), not whitespace alone.
- KPI / summary widgets on Pipeline and Marketing must match Dashboard language (same MetricCard / KpiCard patterns).

### AI surfaces
- Recommendations appear as editable drafts or suggestion chips.
- Primary actions always allow dismiss / edit / ignore.
- Never block a workflow on AI completion.

### Data reuse
- Project/unit media, specs, pricing, and approved copy are canonical entities reused by web, landing, brochure, email, WhatsApp, and AI generation.

---

## 04 — Dashboard

| Item | Spec |
|------|------|
| Layout | Keep approved grid: Today KPIs → Funnel + Charts → Projects / Marketing / Follow-ups |
| Keep | Funnel, Charts, KPI Cards |
| Defer | Persistent left Sidebar redesign (later) |
| Cards | Improve separation via V2 card tokens |
| Empty | Every widget: empty title + CTA drill target |
| Route | `/dashboard` (migration Phase 2) |

---

## 05 — Customer Profile

| Item | Spec |
|------|------|
| Keep | Quick Actions, Journey Timeline (primary activity), Opportunity, Preferences |
| Hierarchy | Journey Timeline is the primary activity column |
| Cards | V2 card system on all modules |
| Route | Customer / person profile canonical route per IA |

---

## 06 — Sales Pipeline

| Item | Spec |
|------|------|
| Board | Kanban with `PipelineColumn` stage tints (`lead`…`won`/`lost`) |
| Cards | Stronger hierarchy: name, stage meta, next action, value; clear gap between cards |
| Summary | Top widgets match Dashboard KPI language |
| Route | `/dashboard/sales` (or canonical Sales path) |

---

## 07 — Inventory

| Item | Spec |
|------|------|
| Card | Portrait `UnitCard` |
| Required fields | Unit Code, Beds, Baths, Sqft, Price, Estimated Rent, Discount Badge |
| Extension | `aiBadges` slot for future AI badges (no layout rewrite) |
| Detail | Unit Detail must include Location + Market Intelligence panels |

---

## 08 — Project Cards

| Item | Spec |
|------|------|
| Actions | Share, Email, WhatsApp, Generate Proposal, AI Summary |
| Progress | `ProgressPair`: Construction Progress + Sales Progress |
| Gallery | Image-led cards with V2 separation |

---

## 09 — Project Detail

| Item | Spec |
|------|------|
| Main | Overview tab discipline (approved V1 structure) |
| Right rail | Configurable widgets — admin configures set + drag-drop order |
| Widget catalog | Budget, Documents, Risks, AI Insights, Activity, Investors, Tasks |
| Mandatory panels | **Location Intelligence** + **Market Intelligence** (see architecture specs) |
| Persist | Per-tenant rail order in settings API (Phase 2+) |

### Configurable rail behavior
- Admin: enable/disable widgets; drag to reorder.
- User (optional later): personal order override.
- Unknown widget ids ignored (forward compatible).

---

## Location Intelligence (Project + Unit Detail)

**Mandatory capabilities**
- Interactive map: zoom, satellite, street view, directions, nearby places
- Nearby: schools, restaurants, cafes, grocery, metro, parks, universities, hospitals
- Scores: Walk / Transit / Bike
- AI Neighborhood Summary (editable)

**Architecture:** `MapProvider` + `LocationIntelligenceService` in `@investhome/ui`  
**Stub:** `stubMapProvider` — safe for builds without vendor SDK  
**UI:** Map chrome + nearby list + score chips + summary editor  
**Rule:** Do not hardcode a map vendor in product components

---

## Market Intelligence (Project + Unit)

**Mandatory capabilities**
- Comps: sales + rentals
- Trends: rental + price
- Neighborhood stats
- AI Market Summary (editable)

**Architecture:** `MarketDataProvider` + `MarketIntelligenceService`  
**Stub:** `stubMarketDataProvider`  
**Rule:** Provider-agnostic — **not** Zillow-hardcoded; same engine for projects and units

---

## 10 — Marketing Home (Control Center)

| Item | Spec |
|------|------|
| Role | Marketing Control Center |
| Channel Health | Website, SEO, Email, Instagram, Facebook, LinkedIn, Google Ads, Meta Ads, YouTube |
| Metrics per channel | Spend, Leads, Conversions, ROI, Campaign Performance |
| AI Marketing Advisor | Recommendations: budget / pause / publish / SEO / repurpose — always editable, never forced |

---

## 11 — Content Studio

| Item | Spec |
|------|------|
| Top nav | Includes **Landing Pages** |
| Create | **Create with AI** + **Create Manually** |
| Workflow | AI Generate → Human Edit → AI Improve → Human Approve → Publish |
| Editability | Always editable at every step |
| Agents (future) | Writing, Design, SEO, Brand, Compliance, Media — extension points only; no UI rewrite required to add agents |

---

## Production migration note

V2 acceptance = tokens + components + mockups + specs.  
Full workspace route migration = Roadmap Phase 2.  
Showcase may adopt V2 opt-in theme without claiming production migration complete.
