"""Authentication and authorization schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from investhome_api.models.user_auth import UserStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    code: str
    description: str | None
    is_system_role: bool


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource: str
    action: str
    description: str | None
    created_at: datetime


class RoleDetail(RoleSummary):
    permissions: list[PermissionResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class RoleListResponse(BaseModel):
    items: list[RoleSummary]
    total: int


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class RolePermissionsUpdate(BaseModel):
    permission_ids: list[UUID]


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: EmailStr
    phone: str | None
    job_title: str | None
    department: str | None
    status: UserStatus
    preferred_language: str
    timezone: str
    avatar_url: str | None
    is_demo: bool
    last_login_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    roles: list[RoleSummary] = Field(default_factory=list)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class UserCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    status: UserStatus = UserStatus.INVITED
    preferred_language: str = Field(default="tr", pattern=r"^(tr|en)$")
    timezone: str = Field(default="UTC", max_length=64)
    avatar_url: str | None = Field(default=None, max_length=500)
    role_ids: list[UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    job_title: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=100)
    status: UserStatus | None = None
    preferred_language: str | None = Field(default=None, pattern=r"^(tr|en)$")
    timezone: str | None = Field(default=None, max_length=64)
    avatar_url: str | None = Field(default=None, max_length=500)


class UserRolesUpdate(BaseModel):
    role_ids: list[UUID]


class CurrentUserResponse(UserResponse):
    permissions: list[str] = Field(default_factory=list)


class PermissionListResponse(BaseModel):
    items: list[PermissionResponse]
    total: int


class MessageResponse(BaseModel):
    message: str
