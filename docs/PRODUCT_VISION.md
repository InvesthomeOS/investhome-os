# Investhome OS — Product Vision

**Document type:** Internal product strategy  
**Last updated:** 2026-07-15  
**Audience:** Engineering, product, leadership

**Related:** [ROADMAP.md](./ROADMAP.md) · [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) · [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

---

## Mission

Build an **AI-native operating system for real estate development** that unifies strategic oversight, sales, capital, construction intelligence, finance, and document workflows into one permission-governed platform — replacing fragmented spreadsheets, siloed CRMs, and disconnected file shares.

---

## Vision

Investhome OS becomes the **single operational brain** for a real estate development company:

- Every project, unit, document, transaction, and party is connected in one domain model
- AI assists extraction, classification, and recommendations — **never bypassing human approval** for consequential actions
- Workspaces tailor views per role (executive, sales, finance, construction) without duplicating data
- Audit trails and confidentiality controls satisfy investor, legal, and compliance requirements

---

## Core Principles

| Principle | Implementation today | Governance |
|-----------|---------------------|------------|
| **Single source of truth** | PostgreSQL + document metadata; no shadow CRMs | [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) |
| **Permission-first** | 225 grants × 11 roles; search/activity respect gates | [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) |
| **Honest AI** | Local heuristics default; UI reflects provider status | [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) |
| **Bilingual by default** | Turkish default, English merge-fallback | [CODING_STANDARDS.md](./CODING_STANDARDS.md) |
| **Audit everything material** | Activity log with sensitive field redaction | [EVENT_MODEL.md](./EVENT_MODEL.md) |
| **Incremental delivery** | Modular monolith; feature flags; blueprint-before-build | [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) |
| **No false completeness** | Placeholders labeled; provider readiness not faked | [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) |

---

## Target Users

| Persona | Primary workspace | Current status |
|---------|-------------------|----------------|
| **Executive / Partner** | Executive Dashboard | Implemented (partial tests) |
| **Sales** | Leads, Projects, Documents | Implemented |
| **Investor Relations** | Investors, Finance, Documents + AI | Implemented |
| **Finance** | Finance, Projects, Reports | Implemented |
| **Construction** | Projects, Documents, Drawing Intelligence | Permissions exist; dedicated workspace **not implemented** |
| **Marketing** | Leads, Projects | Permissions exist; workspace **not implemented** |
| **Operations / Assistant** | Cross-module read/update | Roles seeded; limited demo logins |
| **Legal** | Documents (confidential) | Via documents workspace + permissions |
| **Property / Inventory** | Units & Inventory | **Blueprint only** |
| **Administrator** | Users, Roles, Settings | Implemented (partial tests) |
| **Investor (external)** | Investor portal | **Planned** — not implemented |

---

## Product Layers (as built)

```
┌─────────────────────────────────────────────────────────────┐
│  Workspaces (Executive, Leads, Investors, Projects, Finance, │
│  Documents, Activity, Settings, Admin)                      │
├─────────────────────────────────────────────────────────────┤
│  Platform (Auth, Permissions, Search, Notifications,        │
│  Activity, Company Foundation, Feature Flags)                 │
├─────────────────────────────────────────────────────────────┤
│  Intelligence (Document AI, Drawing Intelligence)             │
├─────────────────────────────────────────────────────────────┤
│  Data (PostgreSQL, Filesystem, Redis queue)                 │
└─────────────────────────────────────────────────────────────┘
```

**Not yet built:** Units & Inventory, Visual Design Studio, Construction workspace, Marketing workspace, Investor portal, event bus, external provider integrations (beyond readiness UI).

---

## Long-term Direction

### Phase A — Foundation (complete)

Core business modules, auth platform, activity/notifications/search, document engine, company foundation, enterprise architecture foundation.

### Phase B — Inventory & Construction (next)

Units & Inventory module ([UNITS_INVENTORY_BLUEPRINT.md](./UNITS_INVENTORY_BLUEPRINT.md)) as canonical inventory layer; drawing-to-unit approval bridge; finance `unit_id` attribution.

### Phase C — Design Intelligence

Visual Design Studio: floor-plan coloring, materials, style presets — **zero implementation today**.

### Phase D — Automation & Integration

Wire `@investhome/events` to n8n; external AI/storage when `FEATURE_EXTERNAL_*` enabled; accounting/banking readiness to verified connections.

### Phase E — AI Brain

Centralized context across entities; recommendation engine with approval gates; embeddings/pgvector for semantic search — **not implemented**.

### Phase F — Multi-company SaaS

Tenant isolation on existing `company_id` schema; per-tenant branding and flags.

---

## Non-goals (near term)

- Full UI redesign
- Automatic currency conversion (exchange rates not implemented — TD-14)
- MLS / external listing syndication
- Production LLM requirement for dev environments
- Microservices extraction

---

## Success Metrics (internal)

| Metric | Target | Current |
|--------|--------|---------|
| API test suite | Green on every commit | 133+ tests passing |
| Module end-to-end | CRUD + activity + search + permissions | Phase 1–2 complete |
| Document pipeline | Async processing in Docker | **Blocked** (TD-01 worker) |
| Governance docs | Constitution established | This release |
| False feature claims | Zero | Enforced via provider status UI |

---

*This document describes intent and direction. Implementation truth is always [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md).*
