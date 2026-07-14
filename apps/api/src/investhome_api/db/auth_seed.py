"""Seed roles, permissions, and demo users."""

from sqlalchemy import select

from investhome_api.config.permissions_config import (
    ACTIONS,
    DEFAULT_ROLE_PERMISSIONS,
    RESOURCES,
    SYSTEM_ROLE_CODES,
)
from investhome_api.db.session import SessionLocal
from investhome_api.models.user_auth import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
    UserStatus,
)
from investhome_api.services.auth_service import hash_password

DEMO_PASSWORD = "Demo123!"

ROLE_LABELS: dict[str, tuple[str, str]] = {
    "super_admin": ("Super Admin", "Full platform access"),
    "executive": ("Executive", "Executive dashboard and broad read access"),
    "partner": ("Partner", "Partner-level portfolio visibility"),
    "sales": ("Sales", "Leads and investor acquisition"),
    "investor_relations": ("Investor Relations", "Investor lifecycle management"),
    "finance": ("Finance", "Financial operations and reporting"),
    "construction": ("Construction", "Project delivery and construction"),
    "marketing": ("Marketing", "Marketing and lead visibility"),
    "operations": ("Operations", "Cross-functional operations"),
    "assistant": ("Assistant", "Limited create/update support"),
    "read_only": ("Read Only", "View-only access"),
}

DEMO_USERS: list[dict[str, object]] = [
    {
        "full_name": "Super Admin (Demo)",
        "email": "superadmin@investhome.demo",
        "job_title": "Platform Administrator",
        "department": "Administration",
        "role_code": "super_admin",
    },
    {
        "full_name": "Executive (Demo)",
        "email": "executive@investhome.demo",
        "job_title": "Chief Executive Officer",
        "department": "Executive",
        "role_code": "executive",
    },
    {
        "full_name": "Sales (Demo)",
        "email": "sales@investhome.demo",
        "job_title": "Sales Manager",
        "department": "Sales",
        "role_code": "sales",
    },
    {
        "full_name": "Investor Relations (Demo)",
        "email": "ir@investhome.demo",
        "job_title": "Investor Relations Lead",
        "department": "Investor Relations",
        "role_code": "investor_relations",
    },
    {
        "full_name": "Finance (Demo)",
        "email": "finance@investhome.demo",
        "job_title": "Finance Director",
        "department": "Finance",
        "role_code": "finance",
    },
    {
        "full_name": "Construction (Demo)",
        "email": "construction@investhome.demo",
        "job_title": "Construction Manager",
        "department": "Construction",
        "role_code": "construction",
    },
    {
        "full_name": "Read Only (Demo)",
        "email": "readonly@investhome.demo",
        "job_title": "Analyst",
        "department": "Operations",
        "role_code": "read_only",
    },
]


def _permission_key(resource: str, action: str) -> str:
    return f"{resource}:{action}"


def seed_permissions_and_roles() -> tuple[int, int]:
    with SessionLocal() as session:
        existing = session.scalar(select(Permission.id).limit(1))
        if existing is not None:
            return 0, 0

        permission_map: dict[str, Permission] = {}
        for resource in sorted(RESOURCES):
            for action in sorted(ACTIONS):
                permission = Permission(
                    resource=resource,
                    action=action,
                    description=f"{action.title()} {resource.replace('_', ' ')}",
                )
                session.add(permission)
                permission_map[_permission_key(resource, action)] = permission

        session.flush()

        role_map: dict[str, Role] = {}
        for code in sorted(SYSTEM_ROLE_CODES):
            name, description = ROLE_LABELS[code]
            role = Role(
                name=name,
                code=code,
                description=description,
                is_system_role=True,
            )
            session.add(role)
            role_map[code] = role

        session.flush()

        for role_code, grants in DEFAULT_ROLE_PERMISSIONS.items():
            role = role_map[role_code]
            for resource, action in grants:
                permission = permission_map[_permission_key(resource, action)]
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))

        session.commit()
        return len(permission_map), len(role_map)


def sync_system_permissions() -> int:
    """Ensure new resources/actions and default role grants exist on upgraded databases."""
    with SessionLocal() as session:
        permission_map: dict[str, Permission] = {
            _permission_key(permission.resource, permission.action): permission
            for permission in session.scalars(select(Permission)).all()
        }
        added = 0

        for resource in sorted(RESOURCES):
            for action in sorted(ACTIONS):
                key = _permission_key(resource, action)
                if key in permission_map:
                    continue
                permission = Permission(
                    resource=resource,
                    action=action,
                    description=f"{action.title()} {resource.replace('_', ' ')}",
                )
                session.add(permission)
                permission_map[key] = permission
                added += 1

        session.flush()

        roles = {
            role.code: role
            for role in session.scalars(select(Role).where(Role.is_system_role.is_(True))).all()
        }
        existing_grants = {
            (grant.role_id, grant.permission_id)
            for grant in session.scalars(select(RolePermission)).all()
        }

        for role_code, grants in DEFAULT_ROLE_PERMISSIONS.items():
            role = roles.get(role_code)
            if role is None:
                continue
            for resource, action in grants:
                permission = permission_map.get(_permission_key(resource, action))
                if permission is None:
                    continue
                key = (role.id, permission.id)
                if key in existing_grants:
                    continue
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                existing_grants.add(key)
                added += 1

        if added:
            session.commit()
        return added


def seed_demo_users() -> int:
    with SessionLocal() as session:
        existing = session.scalar(select(User.id).limit(1))
        if existing is not None:
            return 0

        roles = {
            role.code: role
            for role in session.scalars(select(Role).where(Role.is_system_role.is_(True))).all()
        }
        hashed = hash_password(DEMO_PASSWORD)

        for payload in DEMO_USERS:
            role_code = str(payload["role_code"])
            user = User(
                full_name=str(payload["full_name"]),
                email=str(payload["email"]),
                phone="+90 555 000 0000",
                job_title=str(payload["job_title"]),
                department=str(payload["department"]),
                status=UserStatus.ACTIVE,
                preferred_language="tr",
                timezone="Europe/Istanbul",
                hashed_password=hashed,
                is_demo=True,
            )
            session.add(user)
            session.flush()
            session.add(UserRole(user_id=user.id, role_id=roles[role_code].id))

        session.commit()
        return len(DEMO_USERS)
