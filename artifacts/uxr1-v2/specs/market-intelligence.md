# Market Intelligence — Architecture

**Scope:** Same engine for **projects** and **units**  
**Principle:** Provider-agnostic comps / trends / stats / AI summary  
**Hard rule:** Do **not** hardcode Zillow (or any single vendor) in UI  
**Code:** `packages/ui/src/intelligence/market-intelligence.ts`

---

## Responsibilities

| Layer | Responsibility |
|-------|----------------|
| UI | Comps tables, trend charts, neighborhood stats, summary editor |
| `MarketIntelligenceService` | Unified payload for project/unit |
| `MarketDataProvider` | External or internal data adapter(s) |
| AI | Draft market summary; human editable |

---

## Payload

- `compsSales` / `compsRentals`
- `rentalTrend` / `priceTrend`
- `neighborhoodStats` (median sale/rent, $/sqft, DOM, inventory, vacancy, YoY)
- `marketSummary` (editable)

---

## Stub

`stubMarketDataProvider` returns empty arrays/objects so panels render empty states without breaking builds.

---

## Multi-provider

Future: compose multiple `MarketDataProvider` instances; UI shows `sourceProviderId` on comps when relevant. Product copy must remain vendor-neutral.

---

## Data reuse

Approved market narratives and stats may feed proposals, landing pages, brochures, and email — store once on the entity intelligence record.
