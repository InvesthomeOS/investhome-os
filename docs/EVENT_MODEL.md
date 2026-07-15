# Investhome OS — Event Model

**Last updated:** 2026-07-15

This document defines three distinct event concepts in Investhome OS and how they relate. **Do not conflate them.**

**Related:** [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) (IAD-008) · [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) · [AUTOMATION_PRINCIPLES.md](./AUTOMATION_PRINCIPLES.md)

---

## Overview

| Concept | Purpose | Storage | User-facing | Mutable |
|---------|---------|---------|-------------|---------|
| **Business Events** | Trigger workflows, notifications, AI context | Planned: `@investhome/events` + n8n | Indirect | N/A (ephemeral) |
| **Activity Log** | Immutable business audit trail | `activity_logs` table | Yes — Activity workspace | Append-only |
| **Audit Log (security)** | Auth and permission changes | Same `activity_logs` table | Yes — filtered | Append-only |
| **Application Logs** | Debugging, ops, errors | stdout / log aggregator | No | Rotating |

---

## 1. Business Events (Domain Events)

### Definition

A **business event** is a domain-significant occurrence intended to trigger downstream reactions: notifications, automations, AI context updates, or external integrations.

Examples (conceptual — **not all wired today**):

- `lead.status_changed` → notify assigned sales user
- `document.processing_completed` → update project document panel
- `drawing.unit_proposal_approved` → create inventory unit (placeholder today)
- `payment_obligation.overdue` → executive alert

### Current implementation status

| Component | Status |
|-----------|--------|
| `@investhome/events` package | **Stub** — types only |
| n8n in Docker Compose | Running; **not integrated** with API events (TD-12) |
| `notification_generator` | **Partial** — sync generation from DB state, not event bus |
| ARQ jobs | Internal async commands, not published domain events |

### Ownership

- **Publisher:** Domain services after successful commit
- **Consumer:** Notification service, automation engine (n8n), future AI brain
- **Schema owner:** `@investhome/events` (when wired)

### Retention

Ephemeral on bus; durable effects captured in Activity Log and entity state.

### Future AI usage

Business events will feed the AI Brain context graph: "what happened, to what entity, when" without re-parsing activity descriptions. Events carry structured payloads; activity log carries human-auditable diffs.

---

## 2. Activity Log (Business Audit Trail)

### Definition

The **Activity Log** records **who did what, to which entity, when** — with optional field-level change tracking. It is the authoritative user-facing audit trail.

### Implementation

| Field | Purpose |
|-------|---------|
| `entity_type` / `entity_id` | What was affected |
| `action` | `ActivityAction` enum (created, updated, status_changed, …) |
| `actor_type` | `user`, `system`, `ai`, `integration` |
| `actor_user_id` / `actor_name` | Who (nullable for system) |
| `source` | `web`, `api`, `background_job`, `automation`, `ai_service`, … |
| `description_key` | i18n key for UI rendering |
| `changed_fields`, `previous_values`, `new_values` | Field-level audit |
| `request_id` | Correlation with API request |
| `metadata_json` | Extension payload (sanitized) |

### Write path

```
Route/Service → activity_recorder → activity_service → activity_logs
Auth events  → audit_service     → activity_recorder → activity_logs
AI pipeline  → document/drawing activity helpers → activity_logs
```

### Read path

- Entity timelines (per lead, project, document, …)
- Global Activity workspace (`/dashboard/activity`)
- Search entity type `activity` (permission: `activity.view`)
- Permission filtering via `ENTITY_RESOURCE_MAP`

### Sensitive data policy

`activity_config.py` defines `SENSITIVE_FIELD_NAMES` and partial matches. Values redacted to `[REDACTED]` in stored payloads.

### Retention

`RETENTION_POLICY_DAYS = None` — indefinite retention. Future policy per [DOCUMENT_STANDARDS.md](./DOCUMENT_STANDARDS.md) alignment.

### Distinction from application logs

| Activity Log | Application Log |
|--------------|-----------------|
| Queryable per entity | grep/aggregator only |
| Permission-gated | Ops access only |
| Structured business semantics | Stack traces, debug |
| `activity_logs` table | `core/logging_config.py` stdout |

---

## 3. Security Audit (subset of Activity Log)

### Definition

**Security audit events** are auth and permission mutations recorded through `audit_service.py` into the same `activity_logs` table.

### Event types (examples)

| Event type | Activity action |
|------------|-----------------|
| `auth.login` | `LOGIN` |
| `auth.logout` | `LOGOUT` |
| `auth.password_changed` | `PASSWORD_CHANGED` |
| `users.roles_assigned` | `ROLE_ASSIGNED` |
| `roles.permissions_assigned` | `PERMISSION_CHANGED` |

### Entity types

`SECURITY_ENTITY_TYPES`: `user`, `role` — may have stricter visibility rules.

### Future

Dedicated security SIEM export is **not implemented**. Activity log is the interim authoritative store.

---

## 4. Notifications (derived, not a log type)

Notifications are **actionable user messages**, not audit records. They may be generated from:

- Explicit API calls
- `notification_generator` sync scans
- Future business event subscribers

Notifications have their own lifecycle (read, dismiss) and table (`notifications`). They do **not** replace activity log entries.

---

## Relationships

```
                    ┌──────────────────┐
                    │  Domain Service  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌─────────────┐  ┌──────────────┐
     │ Activity   │  │ Notification│  │ Business     │
     │ Log        │  │ (optional)  │  │ Event (future)│
     │ (durable)  │  │             │  │ (ephemeral)  │
     └────────────┘  └─────────────┘  └──────────────┘
              │                              │
              └──────────┬───────────────────┘
                         ▼
                  ┌─────────────┐
                  │  AI Brain   │
                  │  (future)   │
                  └─────────────┘
```

**Rule:** Every mutating operation **must** write Activity Log. Business events and notifications are **additive**.

---

## Actor Types and AI

| `ActivityActorType` | When used |
|---------------------|-----------|
| `USER` | Interactive dashboard/API |
| `SYSTEM` | Seed, migrations, scheduled jobs |
| `AI` | Document/drawing intelligence pipelines |
| `INTEGRATION` | Future n8n/external webhooks |

AI-initiated actions must still respect [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) approval requirements before mutating authoritative entity state.

---

## Future: Unified Event Taxonomy

When `@investhome/events` is wired (IAD-021 placeholder):

1. Business events carry `event_type`, `entity_ref`, `payload`, `correlation_id`
2. Activity recorder subscribes to persist audit entries
3. Notification generator subscribes for user alerts
4. n8n webhooks subscribe for external automation

Until then, **Activity Log is the only durable event history.**

---

*See [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) for wiring status per module.*
