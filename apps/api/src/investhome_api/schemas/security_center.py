"""Pydantic schemas for Security Center (P11)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class SecurityKpiItem(BaseModel):
    key: str
    label: str
    value: int | float | str | None
    available: bool
    note: str | None = None


class SecuritySignalItem(BaseModel):
    id: str
    signal_type: str
    severity: str
    event_count: int
    first_seen: datetime
    last_seen: datetime
    correlation_key: str
    summary: str
    metadata: dict = Field(default_factory=dict)


class SecuritySignalListResponse(BaseModel):
    items: list[SecuritySignalItem]
    total: int


class SecurityDashboardResponse(BaseModel):
    kpis: list[SecurityKpiItem]
    alerts: list[dict]
    signals: list[SecuritySignalItem] = Field(default_factory=list)
    generated_at: datetime


class AuthSessionItem(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str | None = None
    user_name: str | None = None
    ip_address: str | None
    user_agent: str | None
    device_label: str | None
    created_at: datetime
    last_seen_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    is_current: bool = False


class AuthSessionListResponse(BaseModel):
    items: list[AuthSessionItem]
    total: int


class ProviderStatusItem(BaseModel):
    provider_id: str
    category: str
    label: str
    status: str  # configured | missing | invalid | disabled | not_connected
    configured: bool
    message: str | None = None
    env_keys: list[str] = Field(default_factory=list)


class ProviderStatusListResponse(BaseModel):
    items: list[ProviderStatusItem]


class MfaPolicyResponse(BaseModel):
    enforcement: str  # optional | required | disabled
    methods: list[ProviderStatusItem]
    recovery_codes_available: bool
    adoption: SecurityKpiItem


class ApiKeyItem(BaseModel):
    id: UUID
    name: str
    key_prefix: str
    scopes: list[str]
    status: str
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
    created_by_user_id: UUID | None


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyItem]
    total: int


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None


class ApiKeyCreateResponse(BaseModel):
    key: ApiKeyItem
    secret: str  # shown once only


class ApiKeyRotateResponse(BaseModel):
    key: ApiKeyItem
    secret: str


class TemporaryGrantItem(BaseModel):
    id: UUID
    user_id: UUID
    resource: str
    action: str
    reason: str | None
    starts_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    granted_by_user_id: UUID | None


class TemporaryGrantListResponse(BaseModel):
    items: list[TemporaryGrantItem]
    total: int


class TemporaryGrantCreateRequest(BaseModel):
    user_id: UUID
    resource: str
    action: str
    reason: str | None = None
    expires_at: datetime


class FeatureFlagItem(BaseModel):
    key: str
    enabled: bool
    source: str  # env | override
    rollout_percent: int
    target_roles: list[str] = Field(default_factory=list)
    notes: str | None = None
    env_default: bool | None = None


class FeatureFlagListResponse(BaseModel):
    items: list[FeatureFlagItem]


class FeatureFlagUpdateRequest(BaseModel):
    enabled: bool
    rollout_percent: int = Field(default=100, ge=0, le=100)
    target_roles: list[str] = Field(default_factory=list)
    notes: str | None = None


class ComplianceOverviewResponse(BaseModel):
    policies: list[dict]
    retention: list[dict]
    consent: list[dict]
    legal_holds: list[dict]
    privacy: list[dict]
    knowledge_retention_link: str
    notes: list[str]


class DataGovernanceResponse(BaseModel):
    classifications: list[dict]
    sensitive_fields: list[dict]
    masking: list[dict]
    notes: list[str]


class BackupStatusResponse(BaseModel):
    status: str  # not_configured | configured | verified | stale | failed
    last_backup_at: datetime | None
    backup_age_seconds: int | None = None
    freshness_hours: int = 24
    health: str
    provider: str
    declared_provider: str = "none"
    message: str
    restore_verified: bool = False
    warning: bool = True
    env_keys: list[str]


class SystemConfigResponse(BaseModel):
    currencies: list[str]
    languages: list[str]
    timezones: list[str]
    feature_flags: list[FeatureFlagItem]
    brand_settings_path: str
    organization_path: str


class SystemHealthComponent(BaseModel):
    id: str
    label: str
    status: str  # healthy | degraded | unavailable | not_configured
    detail: str | None = None
    link: str | None = None


class SystemHealthResponse(BaseModel):
    components: list[SystemHealthComponent]
    overall: str


class SecurityIncidentItem(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str
    category: str
    summary: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class SecurityIncidentListResponse(BaseModel):
    items: list[SecurityIncidentItem]
    total: int


class SecurityIncidentCreateRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    severity: str = "medium"
    category: str = "security"
    summary: str | None = None


class AuditExportRequest(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None
    actions: list[str] = Field(default_factory=list)


class AuditExportResponse(BaseModel):
    exported_at: datetime
    total: int
    items: list[dict]
    note: str


class MessageResponse(BaseModel):
    message: str


class UserSecurityActionsResponse(BaseModel):
    message: str
    sessions_revoked: int = 0
