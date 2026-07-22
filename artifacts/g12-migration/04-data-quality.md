# Phase 4 — Data Quality Audit

**Scope:** Local Docker demo DB + absence of real sources.  
**Label:** DRY-RUN / DEMO ONLY — not production quality certification.

## Findings

| Check | Result | Evidence |
|-------|--------|----------|
| Real source completeness | **FAIL** | No extracts in repo |
| Required fields on sources | **SKIP** | No sources |
| Currency codes | **N/A** | Demo finance uses USD; no source mix to audit |
| Date parseability | **N/A** | No source dates |
| FK orphans (txn→account) | **PASS** (demo) | `dry-run/demo-integrity.json` |
| FK orphans (reservation→asset) | **PASS** (demo) | same |
| Status enum validity | **PASS** (demo seed) | seed uses model enums |
| Duplicate emails (CRM) | run `investhome-migrate duplicates` | suggest_merge only |
| Financial near-duplicates | flagged never_auto_merge | same |
| Demo contamination risk | **HIGH for go-live** | Nearly all rows `is_demo=true` |

## Missing / blocked

- Source-vs-target completeness ratios
- Multi-currency normalization plan (need source currencies)
- Historical closed-won pipeline quality
- Bank statement period coverage

## Quality gate for real cutover

1. Every critical source file received + sampled
2. Dry-run rejected = 0 for masters + finance
3. Duplicate report reviewed
4. Zero critical orphans after staging import
