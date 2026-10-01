"""Backup readiness provider contract.

Production does not ship a live cloud backup adapter. Env flags cannot
mark backups as verified. A future adapter implements BackupStatusProvider
and returns observed snapshot metadata only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


class BackupProbeError(Exception):
    """Raised when a connected backup provider cannot be queried."""


class BackupNotConfiguredError(BackupProbeError):
    """Raised when no live backup adapter is connected."""


@dataclass(frozen=True)
class BackupSnapshot:
    last_success_at: datetime | None = None
    last_failure_at: datetime | None = None
    last_error: str | None = None
    restore_verified: bool = False


@dataclass(frozen=True)
class BackupProbeResult:
    provider_id: str
    snapshot: BackupSnapshot


class BackupStatusProvider(ABC):
    """Live backup health adapter.

    Implementations must probe the real provider. They must not invent
    successful backups from configuration flags.
    """

    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def probe(self) -> BackupProbeResult:
        raise NotImplementedError


class UnconfiguredBackupProvider(BackupStatusProvider):
    """Default production adapter: no live backup provider is connected."""

    @property
    def provider_id(self) -> str:
        return "none"

    def is_configured(self) -> bool:
        return False

    def probe(self) -> BackupProbeResult:
        raise BackupNotConfiguredError("No live backup provider is connected.")


def get_backup_provider() -> BackupStatusProvider:
    """Return the connected backup adapter.

    No production cloud provider is registered. BACKUP_PROVIDER / BACKUP_HEALTH
    env values cannot select a live adapter.
    """
    return UnconfiguredBackupProvider()
