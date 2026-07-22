# Release Candidate — G11

| Field | Value |
|-------|-------|
| Intended tag | `v1.0.0-rc.1` |
| Tag applied | **NO** (deferred) |
| Reason | Working tree dirty (~695 paths); tagging would misrepresent release contents |
| HEAD commit | `b5a79c6efba889978e90023cc153d2487d8b65c2` |
| Branch | `main` |
| API version (runtime) | `0.1.0` |
| Alembic | `0059_merge_p10_p11` |
| Owner | TBD |
| Approval | **NO-GO / PENDING** |

## Notes

- Prefer creating a clean release branch from audited files before tagging.
- Do not force-push or reset production history.
- Rollback reference = image digest / git SHA recorded at deploy time.
