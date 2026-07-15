# Investhome OS — Automation Principles

**Last updated:** 2026-07-15

**Related:** [EVENT_MODEL.md](./EVENT_MODEL.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md) · [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) (IAD-010) · [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)

---

## Automation Engine

Investhome OS uses **two automation layers** today:

| Layer | Technology | Status |
|-------|------------|--------|
| **Internal async jobs** | ARQ + Redis | Implemented — document/drawing pipelines |
| **External workflows** | n8n (Docker sidecar) | Configured — **not wired** to domain events (TD-12) |

Future: `@investhome/events` as internal bus between API and n8n.

```
API Service → (future) Event Bus → n8n webhook
     │
     └── ARQ enqueue → Worker → pipeline steps
```

---

## Allowed Automation

| Automation | Trigger | Side effects | Approval |
|------------|---------|--------------|----------|
| Document text extraction | Upload / reprocess | Updates analysis, activity | None — deterministic |
| Document OCR | Pipeline step | Extracted text | None |
| Heuristic classification | Pipeline step | Analysis metadata | None |
| Drawing detection | Upload / reprocess | Analysis + proposals | None for detection |
| Unit creation from proposal | Manual API approval | Creates placeholder unit ID | **Required** |
| Notification sync generation | API read / scheduled | Creates notifications | None |
| Demo seed | Deploy / migrate | Seeds `is_demo` data | Dev only |

### Forbidden without explicit governance review

- Auto-posting finance transactions from AI extraction
- Auto-approving drawing proposals
- Bulk delete/archive without audit
- Sending external emails without user action
- Modifying permissions/roles

---

## Approval Gates

Automations that **mutate authoritative state** must pass through:

1. **Permission check** — `require_permission(resource, action)`
2. **Human approval** — for consequential business actions (see [AI_PRINCIPLES.md](./AI_PRINCIPLES.md))
3. **Activity log write** — append-only record
4. **Idempotency** — safe to retry without duplicate side effects (where applicable)

| Gate type | Example |
|-----------|---------|
| Permission gate | `finance.approve` before obligation status → completed |
| Explicit approval endpoint | `POST .../drawing-unit-proposals/{id}/approve` |
| Feature flag gate | `FEATURE_N8N_AUTOMATION` before webhook dispatch |
| Confidentiality gate | Block external AI on highly confidential docs |

---

## Retry Policy

### ARQ jobs (document/drawing processing)

| Setting | Value |
|---------|-------|
| Max retries | `DOCUMENT_PROCESSING_MAX_RETRIES=3` (default) |
| Queue | Redis via `REDIS_URL` |
| Sync fallback | `DOCUMENT_PROCESSING_SYNC=true` |
| Dead letter | **Not implemented** — failed jobs remain in failed state |

### Retry rules

- Retry transient failures (network, temporary file lock)
- Do **not** retry validation failures (bad file type, size exceeded)
- Log each attempt with `request_id` in application logs
- Record terminal failure in document `processing_status=failed`

### Worker health

**TD-01:** Worker `entrypoint.sh` must honor ARQ CMD — automation blocked until fixed.

---

## Failure Handling

| Failure mode | User experience | Operator action |
|--------------|-----------------|-----------------|
| Job queued, worker down | Document stuck in `queued` | Start worker; fix entrypoint |
| Extraction failed | `processing_status=failed` | Reprocess with `documents.reprocess` |
| OCR unavailable | Placeholder text in dev | Install Tesseract in image |
| DWG conversion | `dwg_external_required` honest message | External converter integration |
| n8n unreachable | No external workflow | Internal jobs unaffected |

**Manual override:** Users with `documents.reprocess` can trigger pipeline rerun. Super admin can toggle `DOCUMENT_PROCESSING_SYNC` for dev.

---

## Manual Override

| Scenario | Override mechanism |
|----------|-------------------|
| Stuck processing | Reprocess API |
| Wrong AI classification | Manual edit analysis (if exposed) or reprocess |
| Automation disabled | `FEATURE_*` env flags |
| Skip async queue | `DOCUMENT_PROCESSING_SYNC=true` |
| n8n workflow pause | n8n UI (external) |

All overrides must generate Activity Log entries where they change entity state.

---

## n8n Integration (planned)

| Principle | Rule |
|-----------|------|
| Inbound | Webhooks authenticated — no anonymous triggers |
| Outbound | API calls use service account or scoped token |
| Data | Pass entity IDs, not full PII blobs |
| Idempotency | n8n workflows must handle duplicate deliveries |
| Audit | Log `ActivitySource.AUTOMATION` |

`FEATURE_N8N_AUTOMATION=false` by default.

---

## Adding New Automation (checklist)

1. Define trigger (event, schedule, or API)
2. Classify: read-only vs mutating
3. If mutating: define approval gate + permission
4. Implement idempotent handler
5. Write activity log on state change
6. Add retry policy with max attempts
7. Add feature flag if optional
8. Document in [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)
9. Add test (unit or integration)

---

*Worker runtime status: [TECHNICAL_DEBT.md](./TECHNICAL_DEBT.md) TD-01.*
