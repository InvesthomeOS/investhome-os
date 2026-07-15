# Investhome OS — Document Standards

**Last updated:** 2026-07-15

Governance for business documents managed by the Document Engine.

**Related:** [DATA_OWNERSHIP.md](./DATA_OWNERSHIP.md) · [SECURITY_PRINCIPLES.md](./SECURITY_PRINCIPLES.md) · [VERSIONING_POLICY.md](./VERSIONING_POLICY.md) · [AI_PRINCIPLES.md](./AI_PRINCIPLES.md)

---

## Naming

| Element | Convention |
|---------|------------|
| Display title | User-provided — free text, TR/EN |
| Storage key | System-generated UUID path — **not** user filename |
| Original filename | Preserved in metadata (`original_filename`) |
| Document type | `DocumentType` enum — e.g., `architectural_drawing`, `contract` |
| Code/reference | Optional `reference_number` field where applicable |

**Do not** rely on filename for business logic — use `document_type` and entity links.

---

## Folders

| Layer | Organization |
|-------|--------------|
| Database | Flat `documents` table with metadata filters |
| Filesystem | `{DOCUMENT_STORAGE_ROOT}/{storage_key}` — opaque paths |
| UI | Workspace filters by type, status, entity, confidentiality — no OS folder tree |
| Entity panels | Documents linked via `DocumentLink` polymorphic association |

### DocumentLink pattern

```
DocumentLink:
  document_id → documents.id
  entity_type → project | investor | lead | transaction | (unit future)
  entity_id   → UUID
```

---

## Metadata

Required / standard fields on `documents`:

| Field | Purpose |
|-------|---------|
| `title` | Display name |
| `document_type` | Classification enum |
| `status` | Lifecycle (`draft`, `active`, `archived`, …) |
| `confidentiality_level` | Access control |
| `processing_status` | Intelligence pipeline state |
| `mime_type`, `file_size_bytes` | Technical metadata |
| `uploaded_by_user_id` | Provenance |
| `effective_date`, `expiration_date` | Contract validity (optional) |
| `is_demo` | Demo data flag |

Intelligence metadata in separate tables (`document_analyses`, `drawing_analyses`).

---

## Confidentiality

Four levels per [ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md) IAD-012:

| Level | Default upload | External AI |
|-------|----------------|-------------|
| `public` | Rare | Allowed if configured |
| `internal` | **Default** | Allowed if configured |
| `confidential` | Manual assignment | Blocked by default |
| `highly_confidential` | Manual assignment | Blocked by default |

Upload UI must allow explicit confidentiality selection for sensitive docs.

Access requires mapped permissions (`view_confidential`, `view_highly_confidential`).

---

## Retention

| Data | Retention today |
|------|-----------------|
| Document binaries | Indefinite while not archived |
| Archived documents | Retained — excluded from default views |
| Extracted text | With document — reprocess refreshes |
| Q&A conversations | `DOCUMENT_QA_HISTORY_RETENTION_DAYS=90` |
| Activity log entries | Indefinite (`RETENTION_POLICY_DAYS=None`) |

**Future:** Configurable retention per `document_type` via SystemPreference.

---

## Approval

| Workflow | Mechanism |
|----------|-----------|
| Document publish | `draft` → `active` status transition |
| Drawing unit approval | Separate proposal approval API |
| Supersede | New version marks old as `superseded` |
| Brand assets | `brand.manage_assets` + linked document |

Material status changes must write Activity Log.

---

## Links

| Link type | Implementation |
|-----------|----------------|
| Entity attachment | `DocumentLink` |
| Direct FK | `project_id` on documents where applicable |
| Cross-module UI | Entity document panels in lead/investor/project/finance drawers |
| Download | Authenticated API — no public URLs |
| Preview | API-generated preview where supported |
| Search | Document entity in universal search with confidentiality filter |

### Rules

- One document may link to multiple entities via multiple `DocumentLink` rows
- Deleting entity does not auto-delete documents — archive/orphan review required
- Intelligence reprocess does not break links

---

## Upload Validation

Per `document_validation` service:

- Max size: `DOCUMENT_MAX_UPLOAD_BYTES`
- Allowed extensions and MIME types
- Reject path traversal in filenames

---

## Brand Assets

Brand assets (`BrandAsset`) reference documents via Document Engine — same standards apply. Types: logo, letterhead, templates, etc. (`BrandAssetType` enum).

---

## Demo Documents

Seeded documents have `is_demo: true`. Demo architectural drawing may be `.txt` placeholder — labeled honestly in audits.

---

## Checklist: New Document Type

1. Add to `DocumentType` enum if needed
2. Update upload validation allowlist if new MIME
3. Add TR/EN labels
4. Map search indexing if applicable
5. Define confidentiality default
6. Add intelligence pipeline support or `not_supported` path
7. Update [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)

---

*Storage provider: local operational; cloud stubbed — see [INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md).*
