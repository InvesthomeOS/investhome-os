"""Authorization: permission checks and role management helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.user_auth import Permission, Role, User


def is_super_admin(user: User) -> bool:
    return any(role.code == "super_admin" for role in user.roles)


def user_can_manage_users(user: User) -> bool:
    if is_super_admin(user):
        return True
    return _has_permission_direct(user, "users", "manage")


def user_can_manage_roles(user: User) -> bool:
    if is_super_admin(user):
        return True
    return _has_permission_direct(user, "roles", "manage")


def _has_permission_direct(user: User, resource: str, action: str) -> bool:
    for role in user.roles:
        for permission in role.permissions:
            if permission.resource == resource and permission.action == action:
                return True
    return False


def user_has_permission(user: User, resource: str, action: str) -> bool:
    if is_super_admin(user):
        return True
    return _has_permission_direct(user, resource, action)


def load_user_with_roles(db: Session, user_id) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id, User.archived_at.is_(None))
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
        )
    )


def get_user_permission_keys(user: User) -> set[str]:
    if is_super_admin(user):
        return {"*:*"}
    keys: set[str] = set()
    for role in user.roles:
        for permission in role.permissions:
            keys.add(f"{permission.resource}:{permission.action}")
    return keys


def ensure_not_privilege_escalation(
    actor: User,
    target_role_codes: list[str],
    *,
    assigning_permissions: list[tuple[str, str]] | None = None,
) -> None:
    """Prevent non-super-admins from granting roles or permissions they do not hold."""
    if is_super_admin(actor):
        return

    actor_codes = {role.code for role in actor.roles}
    for code in target_role_codes:
        if code == "super_admin" or code not in actor_codes:
            from fastapi import HTTPException, status

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign roles beyond your own privileges",
            )

    if assigning_permissions:
        for resource, action in assigning_permissions:
            if not user_has_permission(actor, resource, action):
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot grant permissions you do not possess",
                )


def get_all_permissions(db: Session) -> list[Permission]:
    return list(db.scalars(select(Permission).order_by(Permission.resource, Permission.action)).all())
