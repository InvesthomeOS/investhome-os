"""Marketing form service — CRUD, fields, logic, publishing."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import (
    FormFieldRegistry,
    FormFieldType,
    FormLogicGroup,
    FormStatus,
    FormVersion,
    MarketingForm,
    MarketingFormField,
)
from investhome_api.models.user_auth import User

DEFAULT_FIELD_REGISTRY = [
    ("text", "Text"),
    ("email", "Email"),
    ("phone", "Phone"),
    ("textarea", "Textarea"),
    ("select", "Select"),
    ("checkbox", "Checkbox"),
    ("radio", "Radio"),
    ("consent", "Consent"),
    ("hidden", "Hidden"),
    ("number", "Number"),
    ("date", "Date"),
]


def compute_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total else 1


def ensure_field_registry(db: Session) -> None:
    for field_type, label in DEFAULT_FIELD_REGISTRY:
        existing = db.scalar(select(FormFieldRegistry).where(FormFieldRegistry.field_type == field_type))
        if not existing:
            db.add(FormFieldRegistry(field_type=field_type, label=label, config_schema_json={"type": "object"}))
    db.flush()


def _get_form_or_404(db: Session, form_id: UUID) -> MarketingForm:
    form = db.get(MarketingForm, form_id)
    if form is None:
        raise HTTPException(status_code=404, detail="Form not found")
    return form


def list_forms(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
    search: str | None = None,
) -> tuple[list[MarketingForm], int]:
    query = select(MarketingForm)
    if status_filter:
        query = query.where(MarketingForm.status == FormStatus(status_filter))
    if search:
        query = query.where(MarketingForm.name.ilike(f"%{search}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingForm.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def create_form(db: Session, payload: dict, user: User) -> MarketingForm:
    ensure_field_registry(db)
    existing = db.scalar(select(MarketingForm).where(MarketingForm.slug == payload["slug"]))
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    form = MarketingForm(
        name=payload["name"],
        slug=payload["slug"],
        campaign_id=payload.get("campaign_id"),
        source_id=payload.get("source_id"),
        created_by_user_id=user.id,
        updated_by_user_id=user.id,
    )
    db.add(form)
    db.flush()
    return form


def update_form(db: Session, form_id: UUID, payload: dict, user: User) -> MarketingForm:
    form = _get_form_or_404(db, form_id)
    if "slug" in payload and payload["slug"] != form.slug:
        existing = db.scalar(select(MarketingForm).where(MarketingForm.slug == payload["slug"]))
        if existing:
            raise HTTPException(status_code=409, detail="Slug already exists")
    for key, value in payload.items():
        setattr(form, key, value)
    form.updated_by_user_id = user.id
    db.flush()
    return form


def list_fields(db: Session, form_id: UUID) -> list[MarketingFormField]:
    _get_form_or_404(db, form_id)
    return list(
        db.scalars(
            select(MarketingFormField)
            .where(MarketingFormField.form_id == form_id)
            .order_by(MarketingFormField.sort_order)
        ).all()
    )


def add_field(db: Session, form_id: UUID, payload: dict) -> MarketingFormField:
    _get_form_or_404(db, form_id)
    ensure_field_registry(db)
    registry = db.scalar(select(FormFieldRegistry).where(FormFieldRegistry.field_type == payload["field_type"]))
    if not registry:
        raise HTTPException(status_code=400, detail="Invalid field type")
    existing = db.scalar(
        select(MarketingFormField).where(
            MarketingFormField.form_id == form_id,
            MarketingFormField.field_key == payload["field_key"],
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Field key already exists")
    field = MarketingFormField(
        form_id=form_id,
        field_key=payload["field_key"],
        field_type=FormFieldType(payload["field_type"]),
        label=payload["label"],
        sort_order=payload.get("sort_order", 0),
        required=payload.get("required", False),
        config_json=payload.get("config_json"),
        validation_json=payload.get("validation_json"),
        is_visible=payload.get("is_visible", True),
    )
    db.add(field)
    db.flush()
    return field


def update_field(db: Session, field_id: UUID, payload: dict) -> MarketingFormField:
    field = db.get(MarketingFormField, field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    for key, value in payload.items():
        if value is not None:
            setattr(field, key, value)
    db.flush()
    return field


def add_logic_group(db: Session, form_id: UUID, payload: dict) -> FormLogicGroup:
    _get_form_or_404(db, form_id)
    conditions = payload.get("conditions_json") or []
    _validate_logic_no_circular(db, form_id, payload["target_field_id"], conditions)
    group = FormLogicGroup(
        form_id=form_id,
        target_field_id=payload["target_field_id"],
        operator=payload.get("operator", "and"),
        action=payload.get("action", "show"),
        conditions_json=conditions,
        sort_order=payload.get("sort_order", 0),
    )
    db.add(group)
    db.flush()
    return group


def _validate_logic_no_circular(
    db: Session, form_id: UUID, target_field_id: UUID, conditions: list[dict]
) -> None:
    """Ensure logic conditions do not reference the target field (no circular dependency)."""
    for cond in conditions:
        source_field_id = cond.get("field_id")
        if source_field_id and str(source_field_id) == str(target_field_id):
            raise HTTPException(status_code=400, detail="Circular logic: target field cannot depend on itself")


def list_logic_groups(db: Session, form_id: UUID) -> list[FormLogicGroup]:
    _get_form_or_404(db, form_id)
    return list(
        db.scalars(
            select(FormLogicGroup).where(FormLogicGroup.form_id == form_id).order_by(FormLogicGroup.sort_order)
        ).all()
    )


def compute_form_readiness(db: Session, form_id: UUID) -> dict:
    form = _get_form_or_404(db, form_id)
    blockers: list[str] = []
    fields = list_fields(db, form_id)
    if not fields:
        blockers.append("no_fields")
    has_email = any(
        (f.field_type.value if hasattr(f.field_type, "value") else f.field_type) == "email" for f in fields
    )
    if not has_email:
        blockers.append("missing_email_field")
    if not form.consent_config_json:
        blockers.append("consent_not_configured")
    return {"form_id": str(form_id), "ready": len(blockers) == 0, "blockers": blockers}


def publish_form(db: Session, form_id: UUID, user: User) -> MarketingForm:
    form = _get_form_or_404(db, form_id)
    readiness = compute_form_readiness(db, form_id)
    if not readiness["ready"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Publishing blocked", "blockers": readiness["blockers"]},
        )
    fields = list_fields(db, form_id)
    logic = list_logic_groups(db, form_id)
    last_version = db.scalar(select(func.max(FormVersion.version_number)).where(FormVersion.form_id == form_id))
    version_number = (last_version or 0) + 1
    snapshot = {
        "form": {"name": form.name, "slug": form.slug, "consent_config_json": form.consent_config_json},
        "fields": [
            {
                "field_key": f.field_key,
                "field_type": f.field_type.value if hasattr(f.field_type, "value") else f.field_type,
                "label": f.label,
                "required": f.required,
                "config_json": f.config_json,
            }
            for f in fields
        ],
        "logic_groups": [{"target_field_id": str(g.target_field_id), "conditions_json": g.conditions_json} for g in logic],
    }
    version = FormVersion(
        form_id=form_id,
        version_number=version_number,
        snapshot_json=snapshot,
        created_by_user_id=user.id,
    )
    db.add(version)
    db.flush()
    form.status = FormStatus.PUBLISHED
    form.published_version_id = version.id
    form.published_at = datetime.now(tz=UTC)
    form.updated_by_user_id = user.id
    db.flush()
    return form


def list_form_versions(db: Session, form_id: UUID) -> list[FormVersion]:
    _get_form_or_404(db, form_id)
    return list(
        db.scalars(
            select(FormVersion).where(FormVersion.form_id == form_id).order_by(FormVersion.version_number.desc())
        ).all()
    )


def list_field_registry(db: Session) -> list[FormFieldRegistry]:
    ensure_field_registry(db)
    return list(db.scalars(select(FormFieldRegistry).where(FormFieldRegistry.is_active.is_(True))).all())
