# Phase 6 — Document Import Plan

**Execution status:** NOT EXECUTED — no Drive/SharePoint/export package provided.

## Plan

1. Export documents from source store preserving:
   - original filename
   - created/modified timestamps
   - folder path (as tags or metadata)
   - MIME type
2. Generate `documents_manifest.csv` with `checksum_sha256` per file
3. Dry-run manifest via `investhome-migrate dry-run`
4. Stage files under `DOCUMENT_STORAGE_ROOT` (never commit binaries to git)
5. Create `Document` rows + `DocumentLink` to projects/leads/investors/etc.
6. Reconcile: file count, checksum mismatches, orphan links

## Reject rules

- Missing file on disk
- Checksum mismatch
- Unknown `entity_type` / unresolved `entity_key`
- Paths escaping storage root

## Demo today

~7 documents in local DB (mostly demo placeholders). **Not** production document corpus.

## Reconciliation (blocked)

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Files in export | source count | — | SKIP |
| Manifest rows | = files | — | SKIP |
| Checksum match | 100% | — | SKIP |
| Linked entities resolve | 100% critical | — | SKIP |
