import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class ActivityActorType(str, enum.Enum):
    USER = "user"
    SYSTEM = "system"
    AI = "ai"
    INTEGRATION = "integration"


class ActivitySource(str, enum.Enum):
    WEB = "web"
    API = "api"
    BACKGROUND_JOB = "background_job"
    AUTOMATION = "automation"
    IMPORT = "import"
    INTEGRATION = "integration"
    AI_SERVICE = "ai_service"


class ActivityAction(str, enum.Enum):
    CREATED = "created"
    VIEWED = "viewed"
    UPDATED = "updated"
    STATUS_CHANGED = "status_changed"
    ARCHIVED = "archived"
    RESTORED = "restored"
    DELETED = "deleted"
    EXPORTED = "exported"
    APPROVED = "approved"
    REJECTED = "rejected"
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    PERMISSION_CHANGED = "permission_changed"
    PASSWORD_CHANGED = "password_changed"
    INVITED = "invited"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    PAYMENT_COMPLETED = "payment_completed"
    FUNDING_ADDED = "funding_added"
    FILE_UPLOADED = "file_uploaded"
    NOTE_ADDED = "note_added"
    OTHER = "other"


class ActivityEntityType(str, enum.Enum):
    USER = "user"
    ROLE = "role"
    LEAD = "lead"
    INVESTOR = "investor"
    PROJECT = "project"
    FINANCIAL_ACCOUNT = "financial_account"
    TRANSACTION = "transaction"
    PROJECT_BUDGET = "project_budget"
    FUNDING_COMMITMENT = "funding_commitment"
    PAYMENT_OBLIGATION = "payment_obligation"
    DOCUMENT = "document"
    COMPANY = "company"
    OFFICE = "office"
    DEPARTMENT = "department"
    TEAM = "team"
    BRAND = "brand"
    DESIGN_PROJECT = "design_project"
    BUILDING = "building"
    FLOOR = "floor"
    INVENTORY_ASSET = "inventory_asset"
    INVENTORY_RESERVATION = "inventory_reservation"
    INVENTORY_PRICE = "inventory_price"
    INVENTORY_OWNERSHIP = "inventory_ownership"
    INVENTORY_ASSIGNMENT = "inventory_assignment"
    PRICE_CHANGE_REQUEST = "price_change_request"
    SALES_OPPORTUNITY = "sales_opportunity"
    LEAD_QUALIFICATION = "lead_qualification"
    SALES_PROPOSAL = "sales_proposal"
    WORK_ITEM = "work_item"


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, native_enum=False, length=50),
        nullable=False,
    )
    entity_type: Mapped[ActivityEntityType] = mapped_column(
        Enum(ActivityEntityType, native_enum=False, length=50),
        nullable=False,
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    actor_type: Mapped[ActivityActorType] = mapped_column(
        Enum(ActivityActorType, native_enum=False, length=50),
        nullable=False,
        default=ActivityActorType.SYSTEM,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[ActivitySource] = mapped_column(
        Enum(ActivitySource, native_enum=False, length=50),
        nullable=False,
        default=ActivitySource.API,
    )
    description_key: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    changed_fields: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    previous_values: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    new_values: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
