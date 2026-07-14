"""User serialization helpers."""

from investhome_api.models.user_auth import User
from investhome_api.schemas.auth import CurrentUserResponse, RoleSummary, UserResponse
from investhome_api.services.permission_service import get_user_permission_keys


def serialize_user(user: User) -> UserResponse:
    return UserResponse.model_validate(
        {
            **UserResponse.model_validate(user).model_dump(),
            "roles": [RoleSummary.model_validate(role) for role in user.roles],
        }
    )


def serialize_current_user(user: User) -> CurrentUserResponse:
    base = serialize_user(user)
    permissions = sorted(get_user_permission_keys(user))
    if "*:*" in permissions:
        permissions = ["*:*"]
    return CurrentUserResponse(**base.model_dump(), permissions=permissions)
