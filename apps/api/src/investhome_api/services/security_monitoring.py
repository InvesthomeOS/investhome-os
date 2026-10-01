"""Security event monitoring and alert-readiness.

Aggregates existing auth/security events into unresolved signals. Does not
block users, change authentication, or store secrets, codes, or raw IPs.
"""

from __future__ import annotations

import hashlib
import hmac
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from investhome_api.config.settings import get_settings
from investhome_api.core.logging_config import get_logger

logger = get_logger("investhome.security.monitor")

_SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "code",
    "otp",
    "recovery",
    "cookie",
    "authorization",
    "session",
    "webhook",
    "body",
    "content",
    "document_bytes",
    "raw",
)


class SecurityEventKind(StrEnum):
    FAILED_LOGIN = "failed_login"
    MFA_FAILURE = "mfa_failure"
    CSRF_REJECTED = "csrf_rejected"
    WEBHOOK_SIGNATURE_FAILURE = "webhook_signature_failure"
    DOCUMENT_ACCESS_DENIED = "document_access_denied"
    ADMIN_MFA_RESET = "admin_mfa_reset"
    SESSION_REVOKED = "session_revoked"


class SignalType(StrEnum):
    FAILED_LOGIN_IP = "failed_login_ip"
    FAILED_LOGIN_ACCOUNT = "failed_login_account"
    FAILED_LOGIN_MULTI_ACCOUNT = "failed_login_multi_account"
    MFA_FAILURE_BURST = "mfa_failure_burst"
    CSRF_FAILURE_BURST = "csrf_failure_burst"
    WEBHOOK_SIGNATURE_BURST = "webhook_signature_burst"
    DOCUMENT_ACCESS_DENIED_BURST = "document_access_denied_burst"
    ADMIN_MFA_RESET = "admin_mfa_reset"
    SESSION_REVOKED = "session_revoked"


class SignalSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class SecurityAlertDispatcher(Protocol):
    """Future email/Slack/other delivery. Production has no connected provider."""

    def dispatch(self, signal: SecuritySignal) -> None: ...


class NoopAlertDispatcher:
    def dispatch(self, signal: SecuritySignal) -> None:
        logger.info(
            "security_signal_ready type=%s severity=%s count=%s",
            signal.signal_type,
            signal.severity,
            signal.event_count,
        )


@dataclass
class SecurityMonitorThresholds:
    window_seconds: int = 900
    failed_login_burst: int = 5
    failed_login_critical: int = 15
    multi_account: int = 3
    multi_account_critical: int = 8
    mfa_burst: int = 5
    csrf_burst: int = 8
    webhook_burst: int = 5
    document_denied_burst: int = 8


@dataclass
class SecuritySignal:
    id: str
    signal_type: str
    severity: str
    event_count: int
    first_seen: float
    last_seen: float
    correlation_key: str
    summary: str
    metadata: dict[str, object] = field(default_factory=dict)

    def as_public_dict(self) -> dict:
        return {
            "id": self.id,
            "signal_type": self.signal_type,
            "severity": self.severity,
            "event_count": self.event_count,
            "first_seen": datetime.fromtimestamp(self.first_seen, tz=UTC),
            "last_seen": datetime.fromtimestamp(self.last_seen, tz=UTC),
            "correlation_key": self.correlation_key,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }


@dataclass
class _Bucket:
    times: list[float] = field(default_factory=list)
    members: dict[str, float] = field(default_factory=dict)


class InMemorySignalStore:
    def __init__(self, *, now: Callable[[], float] | None = None) -> None:
        self._lock = threading.Lock()
        self._buckets: dict[str, _Bucket] = {}
        self._signals: dict[str, SecuritySignal] = {}
        self._now = now or time.time

    def add_event(self, key: str, window: int, member: str | None = None) -> tuple[int, int]:
        now = self._now()
        cutoff = now - window
        with self._lock:
            bucket = self._buckets.setdefault(key, _Bucket())
            bucket.times = [t for t in bucket.times if t > cutoff]
            bucket.members = {k: ts for k, ts in bucket.members.items() if ts > cutoff}
            bucket.times.append(now)
            if member:
                bucket.members[member] = now
            return len(bucket.times), len(bucket.members)

    def upsert_signal(self, signal: SecuritySignal) -> tuple[SecuritySignal, bool, bool]:
        with self._lock:
            existing = self._signals.get(signal.id)
            if existing is None:
                self._signals[signal.id] = signal
                return signal, True, False
            existing.event_count = signal.event_count
            existing.last_seen = signal.last_seen
            existing.summary = signal.summary
            existing.metadata = signal.metadata
            upgraded = _severity_rank(signal.severity) > _severity_rank(existing.severity)
            if upgraded:
                existing.severity = signal.severity
            return existing, False, upgraded

    def list_signals(self) -> list[SecuritySignal]:
        with self._lock:
            return list(self._signals.values())


def _severity_rank(severity: str) -> int:
    order = {
        SignalSeverity.INFO.value: 1,
        SignalSeverity.WARNING.value: 2,
        SignalSeverity.HIGH.value: 3,
        SignalSeverity.CRITICAL.value: 4,
    }
    return order.get(severity, 0)


def _thresholds() -> SecurityMonitorThresholds:
    try:
        settings = get_settings()
    except Exception:
        return SecurityMonitorThresholds()
    return SecurityMonitorThresholds(
        window_seconds=max(60, int(settings.security_monitor_window_seconds)),
        failed_login_burst=max(2, int(settings.security_monitor_failed_login_burst)),
        failed_login_critical=max(3, int(settings.security_monitor_failed_login_critical)),
        multi_account=max(2, int(settings.security_monitor_multi_account)),
        multi_account_critical=max(3, int(settings.security_monitor_multi_account_critical)),
        mfa_burst=max(2, int(settings.security_monitor_mfa_burst)),
        csrf_burst=max(2, int(settings.security_monitor_csrf_burst)),
        webhook_burst=max(2, int(settings.security_monitor_webhook_burst)),
        document_denied_burst=max(2, int(settings.security_monitor_document_denied_burst)),
    )


def _pepper() -> bytes:
    try:
        settings = get_settings()
    except Exception:
        return hashlib.sha256(b"ih-secmon-v1|unavailable").digest()
    custom = (settings.security_monitor_pepper or "").strip()
    if custom:
        return hashlib.sha256(custom.encode("utf-8")).digest()
    return hashlib.sha256(b"ih-secmon-v1|" + settings.jwt_secret.encode("utf-8")).digest()


def correlation_hash(kind: str, value: str) -> str:
    digest = hmac.new(_pepper(), f"{kind}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:32]


def sanitize_metadata(metadata: dict | None) -> dict[str, object]:
    safe: dict[str, object] = {}
    for key, value in (metadata or {}).items():
        lowered = str(key).lower()
        if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
            continue
        if lowered in {"ip", "ip_address", "email", "password"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str) and len(value) > 120:
                continue
            safe[str(key)] = value
    return safe


_store: InMemorySignalStore | None = None
_dispatcher: SecurityAlertDispatcher | None = None


def reset_security_monitor_for_tests(
    store: InMemorySignalStore | None = None,
    dispatcher: SecurityAlertDispatcher | None = None,
) -> None:
    global _store, _dispatcher
    _store = store or InMemorySignalStore()
    _dispatcher = dispatcher or NoopAlertDispatcher()


def get_signal_store() -> InMemorySignalStore:
    global _store
    if _store is None:
        _store = InMemorySignalStore()
    return _store


def get_alert_dispatcher() -> SecurityAlertDispatcher:
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = NoopAlertDispatcher()
    return _dispatcher


def set_alert_dispatcher(dispatcher: SecurityAlertDispatcher) -> None:
    global _dispatcher
    _dispatcher = dispatcher


def list_active_signals() -> list[dict]:
    items = [item.as_public_dict() for item in get_signal_store().list_signals()]
    items.sort(key=lambda row: str(row.get("last_seen")), reverse=True)
    return items


def _emit(
    signal_type: SignalType,
    correlation_key: str,
    count: int,
    severity: SignalSeverity,
    summary: str,
    metadata: dict,
) -> None:
    now = time.time()
    signal = SecuritySignal(
        id=f"{signal_type.value}:{correlation_key}",
        signal_type=signal_type.value,
        severity=severity.value,
        event_count=count,
        first_seen=now,
        last_seen=now,
        correlation_key=correlation_key,
        summary=summary,
        metadata=sanitize_metadata(metadata),
    )
    existing, created, upgraded = get_signal_store().upsert_signal(signal)
    if created:
        get_alert_dispatcher().dispatch(existing)
    elif upgraded:
        get_alert_dispatcher().dispatch(existing)


def observe_security_event(
    kind: SecurityEventKind | str,
    *,
    ip: str | None = None,
    identity: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Record a security event. Never raises into the request path."""
    try:
        _observe(kind, ip=ip, identity=identity, metadata=metadata)
    except Exception:
        logger.exception("security_monitor_observe_failed kind=%s", kind)


def _observe(
    kind: SecurityEventKind | str,
    *,
    ip: str | None,
    identity: str | None,
    metadata: dict | None,
) -> None:
    event = SecurityEventKind(kind)
    thresholds = _thresholds()
    window = thresholds.window_seconds
    store = get_signal_store()
    ip_key = correlation_hash("ip", (ip or "").strip()) if ip else None
    id_key = correlation_hash("id", (identity or "").strip().lower()) if identity else None
    meta = sanitize_metadata(metadata)

    if event == SecurityEventKind.FAILED_LOGIN:
        if ip_key:
            count, unique = store.add_event(f"fail-ip:{ip_key}", window, member=id_key)
            if count >= thresholds.failed_login_burst:
                severity = (
                    SignalSeverity.HIGH
                    if count >= thresholds.failed_login_critical
                    else SignalSeverity.WARNING
                )
                _emit(
                    SignalType.FAILED_LOGIN_IP,
                    ip_key,
                    count,
                    severity,
                    "Repeated failed logins from the same network identity",
                    {"event_count": count, **meta},
                )
            if unique >= thresholds.multi_account:
                sev = (
                    SignalSeverity.CRITICAL
                    if unique >= thresholds.multi_account_critical
                    else SignalSeverity.HIGH
                )
                _emit(
                    SignalType.FAILED_LOGIN_MULTI_ACCOUNT,
                    ip_key,
                    unique,
                    sev,
                    "Multiple accounts targeted from the same network identity",
                    {"distinct_accounts": unique, **meta},
                )
        if id_key:
            count, _unique = store.add_event(f"fail-id:{id_key}", window)
            if count >= thresholds.failed_login_burst:
                _emit(
                    SignalType.FAILED_LOGIN_ACCOUNT,
                    id_key,
                    count,
                    SignalSeverity.HIGH
                    if count >= thresholds.failed_login_critical
                    else SignalSeverity.WARNING,
                    "Repeated failed logins against the same account",
                    {"event_count": count, **meta},
                )
        return

    if event == SecurityEventKind.MFA_FAILURE:
        key = ip_key or id_key or correlation_hash("mfa", "unknown")
        count, _ = store.add_event(f"mfa:{key}", window)
        if count >= thresholds.mfa_burst:
            _emit(
                SignalType.MFA_FAILURE_BURST,
                key,
                count,
                SignalSeverity.HIGH if count >= thresholds.mfa_burst * 2 else SignalSeverity.WARNING,
                "Repeated MFA or challenge failures",
                {"event_count": count, **meta},
            )
        return

    if event == SecurityEventKind.CSRF_REJECTED:
        key = ip_key or correlation_hash("csrf", "unknown")
        count, _ = store.add_event(f"csrf:{key}", window)
        if count >= thresholds.csrf_burst:
            _emit(
                SignalType.CSRF_FAILURE_BURST,
                key,
                count,
                SignalSeverity.WARNING,
                "Repeated CSRF rejections",
                {"event_count": count, **meta},
            )
        return

    if event == SecurityEventKind.WEBHOOK_SIGNATURE_FAILURE:
        key = ip_key or correlation_hash("hook", "unknown")
        count, _ = store.add_event(f"hook:{key}", window)
        if count >= thresholds.webhook_burst:
            _emit(
                SignalType.WEBHOOK_SIGNATURE_BURST,
                key,
                count,
                SignalSeverity.HIGH,
                "Repeated webhook signature failures",
                {"event_count": count, **meta},
            )
        return

    if event == SecurityEventKind.DOCUMENT_ACCESS_DENIED:
        key = id_key or ip_key or correlation_hash("doc", "unknown")
        count, _ = store.add_event(f"doc:{key}", window)
        if count >= thresholds.document_denied_burst:
            _emit(
                SignalType.DOCUMENT_ACCESS_DENIED_BURST,
                key,
                count,
                SignalSeverity.HIGH
                if count >= thresholds.document_denied_burst * 2
                else SignalSeverity.WARNING,
                "Unusual denied sensitive document access",
                {"event_count": count, **meta},
            )
        return

    if event == SecurityEventKind.ADMIN_MFA_RESET:
        key = id_key or correlation_hash("mfa-reset", "admin")
        count, _ = store.add_event(f"mfa-reset:{key}", window)
        _emit(
            SignalType.ADMIN_MFA_RESET,
            key,
            count,
            SignalSeverity.INFO,
            "Admin MFA reset recorded",
            {"event_count": count, **meta},
        )
        return

    if event == SecurityEventKind.SESSION_REVOKED:
        key = id_key or correlation_hash("session", "admin")
        count, _ = store.add_event(f"session:{key}", window)
        _emit(
            SignalType.SESSION_REVOKED,
            key,
            count,
            SignalSeverity.INFO,
            "Session revocation recorded",
            {"event_count": count, **meta},
        )
