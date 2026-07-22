"""G15A Platform Core models — module registry, entitlements, webhooks, external access."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class ModuleLifecycleStatus(str, enum.Enum):
    """Honest module lifecycle — never claim Available until working."""

    AVAILABLE = "available"
    PILOT = "pilot"
    PLANNED = "planned"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    DISABLED = "disabled"


class EntitlementEffect(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD = "dead"


class IntegrationStatus(str, enum.Enum):
    AVAILABLE = "available"
    CONFIGURED = "configured"
    PLANNED = "planned"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    NOT_CONNECTED = "not_connected"
    DISABLED = "disabled"


class ExternalUserTypeCode(str, enum.Enum):
    CONTRACTOR = "contractor"
    INVESTOR = "investor"
    PARTNER = "partner"
    VENDOR = "vendor"
    AGENT = "agent"


class PlatformModule(Base):
    """Runtime module registry — distinct from static modules/* manifests."""

    __tablename__ = "platform_modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    name_tr: Mapped[str] = mapped_column(String(160), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ModuleLifecycleStatus.PLANNED.value
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    env_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    depends_on_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    feature_flag_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    route_prefix: Mapped[str | None] = mapped_column(String(255), nullable=True)
    admin_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pilot_phase: Mapped[str | None] = mapped_column(String(32), nullable=True)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    # Once activated, module key (code) is immutable
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    key_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformEntitlement(Base):
    """Access entitlements (NOT billing). Grants/denies module or capability access."""

    __tablename__ = "platform_entitlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    name_tr: Mapped[str] = mapped_column(String(160), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_code: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    capability: Mapped[str] = mapped_column(String(120), nullable=False)
    effect: Mapped[str] = mapped_column(String(16), nullable=False, default=EntitlementEffect.ALLOW.value)
    target_roles_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    target_company_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    target_user_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    target_external_types_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformExternalUserType(Base):
    """External user type definitions for isolation & scoping."""

    __tablename__ = "platform_external_user_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_tr: Mapped[str] = mapped_column(String(120), nullable=False)
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    isolation_rules_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    default_scopes_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    can_see_budgets: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformWebhookSubscription(Base):
    """Outbound webhook subscriptions with signed payloads."""

    __tablename__ = "platform_webhook_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    target_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    secret_prefix: Mapped[str] = mapped_column(String(16), nullable=False)
    event_types_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformWebhookDelivery(Base):
    """Webhook delivery attempts with status tracking."""

    __tablename__ = "platform_webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    signature_header: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=WebhookDeliveryStatus.PENDING.value
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PlatformIntegration(Base):
    """Integration marketplace registry — honest statuses only."""

    __tablename__ = "platform_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name_en: Mapped[str] = mapped_column(String(160), nullable=False)
    name_tr: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=IntegrationStatus.PLANNED.value
    )
    description_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    description_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    env_keys_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    docs_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformBrandingConfig(Base):
    """Shared branding tokens only — no arbitrary CSS injection."""

    __tablename__ = "platform_branding_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, default="default")
    display_name_en: Mapped[str] = mapped_column(String(160), nullable=False, default="InvestHome")
    display_name_tr: Mapped[str] = mapped_column(String(160), nullable=False, default="InvestHome")
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    secondary_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    support_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    footer_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    footer_tr: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Deliberately NO custom_css column — arbitrary CSS injection forbidden
    allowed_token_keys_json: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: [
            "primary_color",
            "accent_color",
            "secondary_color",
            "logo_url",
            "favicon_url",
            "display_name",
            "footer",
        ],
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class PlatformExternalAccessAudit(Base):
    """Audit trail for external-user access attempts and denials."""

    __tablename__ = "platform_external_access_audits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    external_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False, default="allowed")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
