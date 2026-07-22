"""Project team member assignments (foundation for Projects Workspace)."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class ProjectTeamRole(str, enum.Enum):
    PROJECT_MANAGER = "project_manager"
    DEVELOPMENT_MANAGER = "development_manager"
    CONSTRUCTION_MANAGER = "construction_manager"
    ACQUISITIONS = "acquisitions"
    FINANCE = "finance"
    SALES = "sales"
    LEASING = "leasing"
    MARKETING = "marketing"
    LEGAL = "legal"
    OPERATIONS = "operations"
    ADMIN = "admin"
    EXECUTIVE = "executive"
    EXTERNAL_ADVISOR = "external_advisor"


class ProjectTeamMemberStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ENDED = "ended"


class ProjectTeamMember(Base):
    """User assignment on a development project with a workspace role."""

    __tablename__ = "project_team_members"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            "role",
            name="uq_project_team_members_project_user_role",
        ),
        Index("ix_project_team_members_project_id", "project_id"),
        Index("ix_project_team_members_user_id", "user_id"),
        Index("ix_project_team_members_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ProjectTeamRole] = mapped_column(
        Enum(ProjectTeamRole, native_enum=False, length=40),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ProjectTeamMemberStatus] = mapped_column(
        Enum(ProjectTeamMemberStatus, native_enum=False, length=20),
        nullable=False,
        default=ProjectTeamMemberStatus.ACTIVE,
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
