"""Environment guards for demo seed / reset operations."""

from __future__ import annotations

import os

from investhome_api.config.settings import get_settings

PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


class DemoSeedSafetyError(RuntimeError):
    """Raised when demo seed/reset is blocked for the current environment."""


def assert_demo_seed_allowed() -> None:
    """Refuse production unless ``ALLOW_DEMO_SEED_IN_PRODUCTION=true`` is set."""
    settings = get_settings()
    environment = (settings.environment or "").strip().lower()
    if environment not in PRODUCTION_ENVIRONMENTS:
        return

    override = os.environ.get("ALLOW_DEMO_SEED_IN_PRODUCTION", "").strip().lower()
    if override in {"1", "true", "yes"}:
        return

    raise DemoSeedSafetyError(
        "Refusing demo seed/reset in production. "
        "Set ALLOW_DEMO_SEED_IN_PRODUCTION=true to override explicitly."
    )
