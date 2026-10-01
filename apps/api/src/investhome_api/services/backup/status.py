"""Derive truthful backup readiness from a live provider probe."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta

from investhome_api.services.backup.provider import (
    BackupNotConfiguredError,
    BackupProbeError,
    BackupStatusProvider,
    get_backup_provider,
)

STATUS_NOT_CONFIGURED = "not_configured"
STATUS_CONFIGURED = "configured"
STATUS_VERIFIED = "verified"
STATUS_STALE = "stale"
STATUS_FAILED = "failed"

STATUS_VALUES = (
    STATUS_NOT_CONFIGURED,
    STATUS_CONFIGURED,
    STATUS_VERIFIED,
    STATUS_STALE,
    STATUS_FAILED,
)

HEALTH_BY_STATUS = {
    STATUS_NOT_CONFIGURED: "unavailable",
    STATUS_CONFIGURED: "warning",
    STATUS_VERIFIED: "ok",
    STATUS_STALE: "warning",
    STATUS_FAILED: "failed",
}

WARNING_STATUSES = frozenset(
    {
        STATUS_NOT_CONFIGURED,
        STATUS_CONFIGURED,
        STATUS_STALE,
        STATUS_FAILED,
    }
)

ENV_KEYS = ("BACKUP_PROVIDER", "BACKUP_FRESHNESS_HOURS")


def _payload(
    *,
    status: str,
    provider: str,
    message: str,
    last_backup_at: datetime | None = None,
    backup_age_seconds: int | None = None,
    freshness_hours: int,
    restore_verified: bool = False,
    declared_provider: str = "none",
) -> dict:
    return {
        "status": status,
        "last_backup_at": last_backup_at,
        "backup_age_seconds": backup_age_seconds,
        "freshness_hours": freshness_hours,
        "health": HEALTH_BY_STATUS[status],
        "provider": provider,
        "declared_provider": declared_provider,
        "message": message,
        "restore_verified": restore_verified,
        "warning": status in WARNING_STATUSES,
        "env_keys": list(ENV_KEYS),
    }


def evaluate_backup_status(
    provider: BackupStatusProvider,
    *,
    now: datetime | None = None,
    freshness_hours: int = 24,
    declared_provider: str = "none",
) -> dict:
    clock = now or datetime.now(UTC)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=UTC)
    hours = max(1, int(freshness_hours))
    declared = (declared_provider or "none").strip() or "none"

    if not provider.is_configured():
        extra = ""
        if declared.lower() not in {"", "none", "disabled"}:
            extra = (
                f" BACKUP_PROVIDER={declared} is set but no live adapter is connected;"
                " env flags cannot mark backups verified."
            )
        return _payload(
            status=STATUS_NOT_CONFIGURED,
            provider=provider.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            message=(
                "No live backup provider is connected. Backup protection is not verified."
                + extra
            ),
        )

    try:
        probe = provider.probe()
    except BackupNotConfiguredError:
        return _payload(
            status=STATUS_NOT_CONFIGURED,
            provider=provider.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            message="No live backup provider is connected. Backup protection is not verified.",
        )
    except BackupProbeError as exc:
        return _payload(
            status=STATUS_FAILED,
            provider=provider.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            message=f"Backup provider probe failed: {exc}",
        )
    except Exception:
        return _payload(
            status=STATUS_FAILED,
            provider=provider.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            message="Backup provider probe failed.",
        )

    snap = probe.snapshot
    restore_verified = bool(snap.restore_verified)
    last_success = snap.last_success_at
    if last_success is not None and last_success.tzinfo is None:
        last_success = last_success.replace(tzinfo=UTC)

    if snap.last_error and last_success is None:
        return _payload(
            status=STATUS_FAILED,
            provider=probe.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            last_backup_at=snap.last_failure_at,
            restore_verified=False,
            message=f"Backup failed: {snap.last_error}",
        )

    if last_success is None:
        return _payload(
            status=STATUS_CONFIGURED,
            provider=probe.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            restore_verified=False,
            message="Backup adapter is connected but no successful backup has been verified yet.",
        )

    age = clock - last_success
    age_seconds = int(age.total_seconds())
    if age > timedelta(hours=hours):
        return _payload(
            status=STATUS_STALE,
            provider=probe.provider_id,
            declared_provider=declared,
            freshness_hours=hours,
            last_backup_at=last_success,
            backup_age_seconds=age_seconds,
            restore_verified=restore_verified,
            message=(
                f"Last successful backup is older than {hours} hour(s). "
                "Backup protection is stale."
            ),
        )

    verified_message = f"Last successful backup is within the {hours} hour freshness window."
    if not restore_verified:
        verified_message += " Restore rehearsal has not been verified."
    return _payload(
        status=STATUS_VERIFIED,
        provider=probe.provider_id,
        declared_provider=declared,
        freshness_hours=hours,
        last_backup_at=last_success,
        backup_age_seconds=age_seconds,
        restore_verified=restore_verified,
        message=verified_message,
    )


def _freshness_hours() -> int:
    raw = os.getenv("BACKUP_FRESHNESS_HOURS", "24")
    try:
        return max(1, int(raw))
    except ValueError:
        return 24


def _declared_provider() -> str:
    return (os.getenv("BACKUP_PROVIDER") or "none").strip() or "none"


def backup_status(
    provider: BackupStatusProvider | None = None,
    *,
    now: datetime | None = None,
) -> dict:
    return evaluate_backup_status(
        provider if provider is not None else get_backup_provider(),
        now=now,
        freshness_hours=_freshness_hours(),
        declared_provider=_declared_provider(),
    )
