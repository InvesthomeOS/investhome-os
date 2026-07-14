# PostgreSQL

Initialization scripts and configuration for the Investhome OS PostgreSQL instance.

## Schemas

| Schema       | Owner Service | Purpose                          |
|--------------|---------------|----------------------------------|
| `investhome` | API           | Application data and migrations  |
| `n8n`        | n8n           | Workflow automation persistence  |

## Init scripts

Scripts in `init/` run once on first container startup via `docker-entrypoint-initdb.d`.
