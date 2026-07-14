# n8n Automations

Workflow automation layer for Investhome OS.

## Directory structure

```
automations/n8n/
├── workflows/     # Version-controlled workflow exports (JSON)
└── README.md
```

## Local access

When running via Docker Compose:

- URL: http://localhost:5678
- Credentials: configured via `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` in `.env`

## Conventions

- Prefix workflow names with module identifier (e.g. `leads/`, `finance/`)
- Export workflows to `workflows/` after changes for auditability
- Do not store credentials in workflow JSON — use n8n credential vault
