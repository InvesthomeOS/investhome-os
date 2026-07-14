# Redis

Redis instance for caching, pub/sub, and session backing (when enabled).

## Usage

- Port: `6379` (configurable via `REDIS_PORT`)
- Persistence: AOF enabled in `docker-compose.yml`

## Integration points

- `@investhome/events` — future event bus transport
- API — session/cache layer (not yet wired)
