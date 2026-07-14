# Investhome OS

Enterprise real-estate investment operating system — a production-grade monorepo for strategic oversight, lead acquisition, investor relations, project delivery, and financial operations.

## Architecture

```
investhome-os/
├── apps/
│   ├── web/                  # Next.js 15 + TypeScript (App Router)
│   └── api/                  # FastAPI + Python 3.12
├── packages/
│   ├── shared/               # Shared types, constants, utilities
│   ├── ui/                   # Design system and UI primitives
│   ├── auth/                 # Authentication contracts
│   ├── ai-runtime/           # AI orchestration interfaces
│   ├── permissions/          # RBAC and permission contracts
│   └── events/               # Domain event contracts
├── modules/
│   ├── executive/            # Strategic oversight domain
│   ├── leads/                # Acquisition pipeline domain
│   ├── investors/            # Capital partner domain
│   ├── projects/             # Development lifecycle domain
│   └── finance/              # Treasury and compliance domain
├── automations/
│   └── n8n/                  # Workflow automation
└── infrastructure/
    └── docker/               # Container infrastructure configs
```

## Tech stack

| Layer            | Technology                                      |
|------------------|-------------------------------------------------|
| Frontend         | Next.js 15, React 19, TypeScript, App Router    |
| Backend          | FastAPI, Python 3.12, SQLAlchemy 2, Alembic   |
| Configuration    | Pydantic Settings                               |
| Monorepo         | pnpm workspaces, Turborepo                      |
| Data             | PostgreSQL 16, Redis 7                          |
| Automation       | n8n                                             |
| Containers       | Docker, Docker Compose                          |

## Prerequisites

- Node.js >= 20
- pnpm >= 9
- Python >= 3.12
- Docker & Docker Compose

## Quick start

### 1. Clone and configure

```bash
git clone <repository-url> investhome-os
cd investhome-os
cp .env.example .env
```

### 2. Install dependencies

```bash
# JavaScript / TypeScript workspace
pnpm install

# Python API (local development)
cd apps/api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cd ../..
```

### 3. Run with Docker Compose

```bash
docker compose up --build
```

| Service    | URL                          |
|------------|------------------------------|
| Web        | http://localhost:3000        |
| API        | http://localhost:8000      |
| API Docs   | http://localhost:8000/docs   |
| Health     | http://localhost:8000/health |
| n8n        | http://localhost:5678        |

### 4. Run locally (without Docker)

**Terminal 1 — API:**

```bash
cd apps/api
source .venv/bin/activate
uvicorn investhome_api.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Web:**

```bash
pnpm --filter @investhome/web dev
```

## Development commands

```bash
# Run all dev servers (via Turborepo)
pnpm dev

# Build all packages and apps
pnpm build

# Type-check the TypeScript workspace
pnpm typecheck

# Format code
pnpm format

# API tests
cd apps/api && pytest

# Database migrations
cd apps/api && alembic upgrade head
```

## API health endpoint

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "ok",
  "service": "Investhome OS API",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-07-14T09:00:00Z",
  "database": "connected"
}
```

## Package boundaries

### Apps

- **web** — User-facing application shell, routing, and presentation layer
- **api** — HTTP API gateway, persistence, and cross-cutting infrastructure

### Packages

Shared libraries consumed by apps and modules. Packages define **contracts** — not business logic.

### Modules

Domain-bounded contexts aligned to business capabilities. Each module owns its vocabulary, events, and permission scopes. Modules must not import from other modules directly; integrate via events and API contracts.

## Environment variables

See [`.env.example`](.env.example) for the full configuration reference.

## License

Proprietary — Investhome OS. All rights reserved.
