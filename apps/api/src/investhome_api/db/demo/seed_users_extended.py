"""Idempotent extended demo users — fill missing role accounts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.auth_seed import DEMO_PASSWORD
from investhome_api.db.session import SessionLocal
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password

EXTENDED_DEMO_USERS: list[dict[str, object]] = [
    {
        "full_name": "Elif Demir",
        "email": "marketing@investhome.demo",
        "job_title": "Marketing Director",
        "department": "Marketing",
        "role_code": "marketing",
    },
    {
        "full_name": "Marcus Webb",
        "email": "operations@investhome.demo",
        "job_title": "Head of Operations",
        "department": "Operations",
        "role_code": "operations",
    },
    {
        "full_name": "Ayşe Yılmaz",
        "email": "partner@investhome.demo",
        "job_title": "Managing Partner",
        "department": "Partnerships",
        "role_code": "partner",
    },
    {
        "full_name": "Jordan Hale",
        "email": "assistant@investhome.demo",
        "job_title": "Executive Assistant",
        "department": "Administration",
        "role_code": "assistant",
    },
]


def _ensure_user(session: Session, payload: dict[str, object], roles: dict[str, Role], hashed: str) -> bool:
    email = str(payload["email"]).lower()
    existing = session.scalar(select(User).where(User.email == email))
    if existing is not None:
        if not existing.is_demo:
            existing.is_demo = True
        role_code = str(payload["role_code"])
        role = roles.get(role_code)
        if role is not None:
            has_role = session.scalar(
                select(UserRole.id).where(
                    UserRole.user_id == existing.id,
                    UserRole.role_id == role.id,
                )
            )
            if has_role is None:
                session.add(UserRole(user_id=existing.id, role_id=role.id))
        return False

    role_code = str(payload["role_code"])
    role = roles.get(role_code)
    if role is None:
        return False

    user = User(
        full_name=str(payload["full_name"]),
        email=email,
        phone="+90 555 100 2000",
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
    session.add(UserRole(user_id=user.id, role_id=role.id))
    return True


def seed_users_extended(session: Session | None = None) -> int:
    """Add missing marketing/operations/partner/assistant demo users. Returns inserted count."""
    own_session = session is None
    session = session or SessionLocal()
    try:
        roles = {
            role.code: role
            for role in session.scalars(select(Role).where(Role.is_system_role.is_(True))).all()
        }
        hashed = hash_password(DEMO_PASSWORD)
        inserted = 0
        for payload in EXTENDED_DEMO_USERS:
            if _ensure_user(session, payload, roles, hashed):
                inserted += 1
        if own_session:
            session.commit()
        else:
            session.flush()
        return inserted
    finally:
        if own_session:
            session.close()
