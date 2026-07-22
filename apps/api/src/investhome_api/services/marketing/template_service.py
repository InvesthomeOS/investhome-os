"""Marketing template service — placeholders and validation."""

from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_content_studio import (
    MarketingTemplate,
    MarketingTemplateStatus,
    MarketingTemplateType,
    TemplatePlaceholder,
    TemplateVersion,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.campaign_service import compute_pages


PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _template_summary(template: MarketingTemplate) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "template_type": template.template_type.value,
        "content_type": template.content_type,
        "channel_category": template.channel_category,
        "status": template.status.value,
        "current_version_id": template.current_version_id,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def _template_detail(template: MarketingTemplate) -> dict:
    return {**_template_summary(template), "description": template.description, "archived_at": template.archived_at}


def get_template(db: Session, template_id: UUID) -> MarketingTemplate:
    template = db.get(MarketingTemplate, template_id)
    if template is None or template.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return template


def list_templates(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    template_type: str | None = None,
    status_filter: str | None = None,
) -> tuple[list[dict], int]:
    query = select(MarketingTemplate).where(MarketingTemplate.archived_at.is_(None))
    if template_type:
        query = query.where(MarketingTemplate.template_type == template_type)
    if status_filter:
        query = query.where(MarketingTemplate.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingTemplate.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return [_template_summary(row) for row in rows], total


def create_template(db: Session, *, payload: dict, actor: User) -> MarketingTemplate:
    template = MarketingTemplate(
        name=payload["name"],
        description=payload.get("description"),
        template_type=MarketingTemplateType(payload.get("template_type", "other")),
        content_type=payload.get("content_type"),
        channel_category=payload.get("channel_category"),
        status=MarketingTemplateStatus.DRAFT,
        created_by_user_id=actor.id,
        updated_by_user_id=actor.id,
    )
    db.add(template)
    db.flush()
    version = TemplateVersion(
        template_id=template.id,
        version_number=1,
        body_template=payload.get("body_template"),
        body_json=payload.get("body_json"),
        document_id=payload.get("document_id"),
        created_by_user_id=actor.id,
    )
    db.add(version)
    db.flush()
    template.current_version_id = version.id
    for ph in payload.get("placeholders") or []:
        db.add(TemplatePlaceholder(template_id=template.id, version_id=version.id, **ph))
    return template


def update_template(db: Session, template: MarketingTemplate, *, payload: dict, actor: User) -> MarketingTemplate:
    for field in ("name", "description", "content_type", "channel_category", "status"):
        if field in payload:
            if field == "status":
                template.status = MarketingTemplateStatus(payload[field])
            else:
                setattr(template, field, payload[field])
    template.updated_by_user_id = actor.id
    return template


def validate_template_placeholders(db: Session, template: MarketingTemplate, values: dict) -> dict:
    placeholders = list(
        db.scalars(
            select(TemplatePlaceholder).where(TemplatePlaceholder.template_id == template.id)
        ).all()
    )
    errors: list[str] = []
    for ph in placeholders:
        if ph.required and not values.get(ph.placeholder_key):
            errors.append(f"Required placeholder '{ph.placeholder_key}' is missing")
    version = db.get(TemplateVersion, template.current_version_id) if template.current_version_id else None
    if version and version.body_template:
        found_keys = set(PLACEHOLDER_PATTERN.findall(version.body_template))
        defined_keys = {ph.placeholder_key for ph in placeholders}
        for key in found_keys - defined_keys:
            errors.append(f"Undefined placeholder '{{{{{key}}}}}' in template body")
        for key in defined_keys - found_keys:
            if any(p.required and p.placeholder_key == key for p in placeholders):
                errors.append(f"Required placeholder '{key}' not found in template body")
    return {"valid": len(errors) == 0, "errors": errors}


def preview_template(db: Session, template: MarketingTemplate, values: dict) -> dict:
    validation = validate_template_placeholders(db, template, values)
    if not validation["valid"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=validation)
    version = db.get(TemplateVersion, template.current_version_id) if template.current_version_id else None
    body = version.body_template if version else ""
    rendered = body or ""
    for key, value in values.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return {"rendered": rendered, "template_id": str(template.id)}


def list_placeholders(db: Session, template_id: UUID) -> list[TemplatePlaceholder]:
    return list(
        db.scalars(
            select(TemplatePlaceholder)
            .where(TemplatePlaceholder.template_id == template_id)
            .order_by(TemplatePlaceholder.sort_order)
        ).all()
    )


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": compute_pages(total, page_size)}
