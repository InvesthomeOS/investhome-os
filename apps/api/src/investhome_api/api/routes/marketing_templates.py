"""Marketing template API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_content_studio import TemplateCreate, TemplatePreviewRequest, TemplateUpdate
from investhome_api.services.marketing.template_service import (
    _template_detail,
    create_template,
    get_template,
    list_placeholders,
    list_templates,
    paginate,
    preview_template,
    update_template,
    validate_template_placeholders,
)

router = APIRouter(prefix="/marketing/templates", tags=["marketing-templates"])


@router.get("")
def list_templates_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    template_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
) -> dict:
    items, total = list_templates(db, page=page, page_size=page_size, template_type=template_type, status_filter=status_filter)
    return paginate(items, total, page, page_size)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_template_route(
    body: TemplateCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    template = create_template(db, payload=body.model_dump(), actor=user)
    db.commit()
    db.refresh(template)
    return {"template": _template_detail(template)}


@router.get("/{template_id}")
def get_template_route(
    template_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    return _template_detail(get_template(db, template_id))


@router.put("/{template_id}")
def update_template_route(
    template_id: UUID,
    body: TemplateUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    template = get_template(db, template_id)
    update_template(db, template, payload=body.model_dump(exclude_unset=True), actor=user)
    db.commit()
    db.refresh(template)
    return {"template": _template_detail(template)}


@router.get("/{template_id}/placeholders")
def template_placeholders(
    template_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    get_template(db, template_id)
    return {"items": list_placeholders(db, template_id)}


@router.post("/{template_id}/validate")
def validate_placeholders(
    template_id: UUID,
    body: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    template = get_template(db, template_id)
    return validate_template_placeholders(db, template, body.values)


@router.post("/{template_id}/preview")
def preview_template_route(
    template_id: UUID,
    body: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_content")),
) -> dict:
    template = get_template(db, template_id)
    return preview_template(db, template, body.values)
