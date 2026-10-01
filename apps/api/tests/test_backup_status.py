"""Backup readiness status — truthful reporting without a live provider."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from investhome_api.services.backup.provider import (
    BackupProbeError,
    BackupProbeResult,
    BackupSnapshot,
    BackupStatusProvider,
    UnconfiguredBackupProvider,
)
from investhome_api.services.backup.status import evaluate_backup_status
from investhome_api.services.security_center_service import backup_status


def _login_admin(client: TestClient) -> None:
    res = client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
    assert res.status_code == 200, res.text


class _FakeProvider(BackupStatusProvider):
    def __init__(
        self,
        *,
        configured: bool = True,
        provider_id: str = "test-provider",
        snapshot: BackupSnapshot | None = None,
        error: Exception | None = None,
    ) -> None:
        self._configured = configured
        self._provider_id = provider_id
        self._snapshot = snapshot or BackupSnapshot()
        self._error = error

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def is_configured(self) -> bool:
        return self._configured

    def probe(self) -> BackupProbeResult:
        if self._error:
            raise self._error
        return BackupProbeResult(provider_id=self._provider_id, snapshot=self._snapshot)


NOW = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)


def test_no_provider_is_not_configured() -> None:
    result = evaluate_backup_status(UnconfiguredBackupProvider(), now=NOW, freshness_hours=24)
    assert result["status"] == "not_configured"
    assert result["health"] == "unavailable"
    assert result["warning"] is True
    assert result["restore_verified"] is False
    assert result["last_backup_at"] is None


def test_configured_without_success_is_not_verified() -> None:
    result = evaluate_backup_status(_FakeProvider(snapshot=BackupSnapshot()), now=NOW)
    assert result["status"] == "configured"
    assert result["health"] == "warning"
    assert result["warning"] is True
    assert result["restore_verified"] is False


def test_recent_verified_backup() -> None:
    snap = BackupSnapshot(last_success_at=NOW - timedelta(hours=2), restore_verified=False)
    result = evaluate_backup_status(_FakeProvider(snapshot=snap), now=NOW, freshness_hours=24)
    assert result["status"] == "verified"
    assert result["health"] == "ok"
    assert result["warning"] is False
    assert result["restore_verified"] is False
    assert result["last_backup_at"] is not None
    assert result["backup_age_seconds"] == 2 * 3600


def test_old_backup_is_stale() -> None:
    snap = BackupSnapshot(last_success_at=NOW - timedelta(hours=25))
    result = evaluate_backup_status(_FakeProvider(snapshot=snap), now=NOW, freshness_hours=24)
    assert result["status"] == "stale"
    assert result["health"] == "warning"
    assert result["warning"] is True
    assert result["freshness_hours"] == 24


def test_provider_error_is_failed() -> None:
    result = evaluate_backup_status(
        _FakeProvider(error=BackupProbeError("timeout")),
        now=NOW,
        freshness_hours=24,
    )
    assert result["status"] == "failed"
    assert result["health"] == "failed"
    assert result["warning"] is True
    assert "timeout" in result["message"]


def test_failed_snapshot_without_success() -> None:
    snap = BackupSnapshot(last_error="upload denied", last_failure_at=NOW)
    result = evaluate_backup_status(_FakeProvider(snapshot=snap), now=NOW)
    assert result["status"] == "failed"


def test_env_flag_alone_cannot_produce_verified(monkeypatch) -> None:
    monkeypatch.setenv("BACKUP_PROVIDER", "aws_s3")
    monkeypatch.setenv("BACKUP_HEALTH", "healthy")
    monkeypatch.setenv("BACKUP_LAST_SUCCESS_AT", NOW.isoformat())
    result = backup_status()
    assert result["status"] == "not_configured"
    assert result["health"] != "ok"
    assert result["restore_verified"] is False
    assert "env flags cannot mark backups verified" in result["message"]


def test_security_center_backup_endpoint_truthful(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/backup")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "not_configured"
    assert body["health"] == "unavailable"
    assert body["warning"] is True
    assert body["last_backup_at"] is None
    assert body["restore_verified"] is False
    assert body["freshness_hours"] == 24


def test_security_center_dashboard_backup_kpi(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/dashboard")
    assert res.status_code == 200
    body = res.json()
    backup = next(k for k in body["kpis"] if k["key"] == "backup_health")
    assert backup["available"] is True
    assert backup["value"] == "not_configured"
    assert any(a["title"] == "Backup protection is not verified" for a in body["alerts"])
