# Location Intelligence — Architecture

**Scope:** Project Detail + Unit Detail (mandatory)  
**Principle:** Provider-agnostic map + places + scores + AI neighborhood summary  
**Code:** `packages/ui/src/intelligence/location-intelligence.ts`

---

## Responsibilities

| Layer | Responsibility |
|-------|----------------|
| UI | Map chrome, nearby filters, score chips, summary editor |
| `LocationIntelligenceService` | Aggregate payload for project/unit |
| `MapProvider` | Vendor SDK adapter (render, places, directions, street view) |
| AI | Draft neighborhood summary; human always edits before publish |

---

## UI requirements

1. **Interactive map** — zoom; modes: roadmap / satellite / street / hybrid  
2. **Directions** — open provider directions URL or in-app panel  
3. **Nearby places** — schools, restaurants, cafes, grocery, metro, parks, universities, hospitals  
4. **Mobility scores** — Walk / Transit / Bike (nullable when unavailable)  
5. **AI Neighborhood Summary** — shown as editable text; source `ai | human | hybrid`

---

## Stub

`stubMapProvider` mounts a labeled placeholder, returns empty nearby/scores, and builds a generic directions URL. Safe for CI and design-system showcase.

---

## Integration sketch

```ts
import { stubMapProvider, type LocationIntelligenceService } from '@investhome/ui';

const map = stubMapProvider; // swap for Google/Mapbox/etc. adapter
```

Do **not** import a vendor SDK from React feature components — inject `MapProvider`.

---

## Persistence

- Project/unit geo center stored once on the entity  
- Cached nearby + scores keyed by entity + provider id  
- Human-edited summary stored as canonical content (data reuse)
