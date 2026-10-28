"""Archive, restore, ownership transfer, and safe permanent deletion."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from investhome_api.db.base import Base
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus

INFRASTRUCTURE_TABLES = frozenset(
    {
        "user_roles",
        "user_mfa",
        "user_mfa_recovery_codes",
        "user_invitations",
        "password_reset_tokens",
        "auth_sessions",
    }
)

TRANSFER_COLUMNS = frozenset(
    {
        ("crm_contacts", "owner_user_id"),
        ("leads", "assigned_manager_id"),
        ("sales_opportunities", "assigned_sales_user_id"),
        ("crm_activities", "assigned_user_id"),
        ("crm_activities", "owner_id"),
        ("crm_user_communication_accounts", "user_id"),
    }
)

OPEN_TASK_COLUMNS = frozenset(
    {
        ("crm_activities", "assigned_user_id"),
        ("crm_activities", "owner_id"),
    }
)

TABLE_LABELS = {
    "crm_contacts": "contacts",
    "leads": "leads",
    "sales_opportunities": "opportunities",
    "crm_activities": "tasks",
    "crm_activity_comments": "notes",
    "documents": "documents",
    "company_workspace_documents": "documents",
    "crm_communications": "communications",
    "crm_user_communication_accounts": "communication_accounts",
    "inventory_assignments": "assignments",
    "crm_communication_audit_logs": "audit",
}


def _label(table_name: str) -> str:
    return TABLE_LABELS.get(table_name, table_name)


def _user_fk_columns() -> list[tuple[object, str]]:
    import investhome_api.models  # noqa: F401

    found: list[tuple[object, str]] = []
    for table in Base.metadata.tables.values():
        if table.name in INFRASTRUCTURE_TABLES:
            continue
        for column in table.columns:
            for fk in column.foreign_keys:
                if fk.column.table.name == "users" and fk.column.name == "id":
                    found.append((table, column.name))
    return found


def deletion_dependencies(db: Session, user_id: UUID) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table, column_name in _user_fk_columns():
        total = db.scalar(
            select(func.count()).select_from(table).where(table.c[column_name] == user_id)
        )
        amount = int(total or 0)
        if amount <= 0:
            continue
        key = _label(table.name)
        counts[key] = counts.get(key, 0) + amount
    return counts


def deletion_report(db: Session, *, actor: User, target: User) -> dict[str, object]:
    if actor.id == target.id:
        return {"cannot_delete": True, "reason": "self", "dependencies": {}}
    if is_last_active_super_admin(db, target):
        return {"cannot_delete": True, "reason": "last_super_admin", "dependencies": {}}
    dependencies = deletion_dependencies(db, target.id)
    return {
        "cannot_delete": bool(dependencies),
        "reason": "dependencies" if dependencies else "safe",
        "dependencies": dependencies,
    }


def is_last_active_super_admin(db: Session, user: User) -> bool:
    if user.archived_at is not None or user.status != UserStatus.ACTIVE:
        return False
    codes = {role.code for role in user.roles}
    if "super_admin" not in codes:
        return False
    others = db.scalars(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            Role.code == "super_admin",
            User.status == UserStatus.ACTIVE,
            User.archived_at.is_(None),
            User.id != user.id,
        )
    ).all()
    return len(list(others)) == 0


def transfer_operational_ownership(
    db: Session,
    *,
    source_user_id: UUID,
    target_user_id: UUID,
) -> dict[str, int]:
    moved: dict[str, int] = {}
    import investhome_api.models  # noqa: F401

    tables_by_name = {table.name: table for table in Base.metadata.tables.values()}
    for table_name, column_name in TRANSFER_COLUMNS:
        table = tables_by_name.get(table_name)
        if table is None or column_name not in table.c:
            continue
        condition = table.c[column_name] == source_user_id
        if (table_name, column_name) in OPEN_TASK_COLUMNS and "completed_at" in table.c:
            condition = condition & table.c.completed_at.is_(None)
        before = db.scalar(select(func.count()).select_from(table).where(condition))
        count = int(before or 0)
        if count:
            db.execute(update(table).where(condition).values({column_name: target_user_id}))
            moved[_label(table_name)] = moved.get(_label(table_name), 0) + count
    db.flush()
    return moved
