import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from investhome_api.db.base import Base


class NotificationType(str, enum.Enum):
    REMINDER = "reminder"
    WARNING = "warning"
    APPROVAL = "approval"
    PAYMENT = "payment"
    INVESTOR = "investor"
    PROJECT = "project"
    FINANCE = "finance"
    SYSTEM = "system"
    AI = "ai"
    DOCUMENT = "document"
    CONSTRUCTION = "construction"


class NotificationPriority(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


class NotificationSource(str, enum.Enum):
    USER = "user"
    AUTOMATION = "automation"
    ACTIVITY = "activity"
    AI = "ai"
    INTEGRATION = "integration"
    SCHEDULED_JOB = "scheduled_job"


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=50),
        nullable=False,
    )
    priority: Mapped[NotificationPriority] = mapped_column(
        Enum(NotificationPriority, native_enum=False, length=20),
        nullable=False,
    )
    title_key: Mapped[str] = mapped_column(String(120), nullable=False)
    message_key: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    related_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    related_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source: Mapped[NotificationSource] = mapped_column(
        Enum(NotificationSource, native_enum=False, length=50),
        nullable=False,
        default=NotificationSource.AUTOMATION,
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, native_enum=False, length=20),
        nullable=False,
        default=NotificationStatus.UNREAD,
    )
    dedupe_key: Mapped[str] = mapped_column(String(180), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_notifications_recipient_user_id", "recipient_user_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_priority", "priority"),
        Index(
            "ix_notifications_recipient_dedupe",
            "recipient_user_id",
            "dedupe_key",
            unique=True,
        ),
    )
