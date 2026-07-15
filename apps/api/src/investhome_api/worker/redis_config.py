"""Parse Redis URL for ARQ worker settings."""

from __future__ import annotations

from urllib.parse import urlparse

from arq.connections import RedisSettings


def redis_settings_from_url(url: str) -> RedisSettings:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    password = parsed.password
    db = 0
    if parsed.path and parsed.path.strip("/"):
        try:
            db = int(parsed.path.strip("/"))
        except ValueError:
            db = 0
    return RedisSettings(host=host, port=port, password=password, database=db)
