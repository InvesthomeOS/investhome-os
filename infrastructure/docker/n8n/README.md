# n8n Infrastructure

Docker-side configuration notes for the Investhome OS n8n automation service.

## Database

n8n persists workflow state to the `n8n` PostgreSQL schema created by `infrastructure/docker/postgres/init/01-schemas.sql`.

## Security

- Enable basic auth in production (`N8N_BASIC_AUTH_*`)
- Replace `N8N_ENCRYPTION_KEY` with a cryptographically secure 32+ character value
- Disable diagnostics in production (`N8N_DIAGNOSTICS_ENABLED=false`)

## Workflow imports

Place exportable workflow JSON files in `automations/n8n/workflows/` for version control.
