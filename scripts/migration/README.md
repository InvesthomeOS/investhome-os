# Migration scripts (G12)

Canonical implementation lives in the API package:

`apps/api/src/investhome_api/migration/`

```bash
# Preferred (repo mounted into one-off container)
docker compose run --rm --entrypoint python \
  -v "${PWD}:/workspace" \
  -e PYTHONPATH=/workspace/apps/api/src \
  -w /workspace \
  api -m investhome_api.migration.cli templates

docker compose run --rm --entrypoint python \
  -v "${PWD}:/workspace" \
  -e PYTHONPATH=/workspace/apps/api/src \
  -e DATABASE_URL=... \
  -w /workspace \
  api -m investhome_api.migration.cli inventory --with-db

# After editable install: investhome-migrate <command>
```

Place real extracts in `data/migration-sources/` (do not commit PII), then:

```bash
... cli dry-run --sources data/migration-sources
... cli duplicates
... cli reconcile
```

See `docs/ops/migration/RUNBOOK.md` and `artifacts/g12-migration/REPORT.md`.
