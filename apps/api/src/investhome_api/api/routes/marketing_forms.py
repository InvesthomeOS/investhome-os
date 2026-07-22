"""Marketing forms API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_landing_conversion import (
    FormCreate,
    FormDetail,
    FormFieldCreate,
    FormFieldRegistryItem,
    FormFieldResponse,
    FormFieldUpdate,
    FormListResponse,
    FormLogicGroupCreate,
    FormLogicGroupResponse,
    FormReadinessResponse,
    FormSummary,
    FormUpdate,
)
from investhome_api.services.activity_recorder import log_entity_created, log_entity_updated
from investhome_api.services.marketing.form_service import (
    add_field,
    add_logic_group,
    compute_form_readiness,
    compute_pages,
    create_form,
    list_field_registry,
    list_fields,
    list_form_versions,
    list_forms,
    list_logic_groups,
    publish_form,
    update_field,
    update_form,
)
from investhome_api.models.marketing_landing_conversion import MarketingForm

router = APIRouter(prefix="/marketing/forms", tags=["marketing-forms"])


def _form_summary(form: MarketingForm) -> FormSummary:
    return FormSummary(
        id=form.id,
        name=form.name,
        slug=form.slug,
        status=form.status.value if hasattr(form.status, "value") else form.status,
        campaign_id=form.campaign_id,
        source_id=form.source_id,
        published_at=form.published_at,
        created_at=form.created_at,
        updated_at=form.updated_at,
    )


@router.get("", response_model=FormListResponse)
def list_forms_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
):
    items, total = list_forms(db, page=page, page_size=page_size, status_filter=status, search=search)
    return FormListResponse(
        items=[_form_summary(f) for f in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=compute_pages(total, page_size),
    )


@router.post("", response_model=FormSummary, status_code=201)
def create_form_route(
    payload: FormCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    form = create_form(db, payload.model_dump(), user)
    db.commit()
    log_entity_created(
        db,
        entity_type=ActivityEntityType.MARKETING_FORM,
        entity_id=form.id,
        description_key="marketing.form.created",
        actor=user,
        request=request,
    )
    db.commit()
    return _form_summary(form)


@router.get("/field-registry", response_model=list[FormFieldRegistryItem])
def field_registry_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    return list_field_registry(db)


@router.get("/{form_id}", response_model=FormDetail)
def get_form_route(
    form_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    form = db.get(MarketingForm, form_id)
    if not form:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Form not found")
    fields = list_fields(db, form_id)
    logic = list_logic_groups(db, form_id)
    return FormDetail(
        **_form_summary(form).model_dump(),
        consent_config_json=form.consent_config_json,
        routing_config_json=form.routing_config_json,
        notification_config_json=form.notification_config_json,
        spam_config_json=form.spam_config_json,
        published_version_id=form.published_version_id,
        fields=[
            FormFieldResponse(
                id=f.id,
                form_id=f.form_id,
                field_key=f.field_key,
                field_type=f.field_type.value if hasattr(f.field_type, "value") else f.field_type,
                label=f.label,
                sort_order=f.sort_order,
                required=f.required,
                config_json=f.config_json,
                validation_json=f.validation_json,
                is_visible=f.is_visible,
            )
            for f in fields
        ],
        logic_groups=[
            FormLogicGroupResponse(
                id=g.id,
                form_id=g.form_id,
                target_field_id=g.target_field_id,
                operator=g.operator.value if hasattr(g.operator, "value") else g.operator,
                action=g.action,
                conditions_json=g.conditions_json,
                sort_order=g.sort_order,
            )
            for g in logic
        ],
    )


@router.patch("/{form_id}", response_model=FormSummary)
def update_form_route(
    form_id: UUID,
    payload: FormUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    form = update_form(db, form_id, payload.model_dump(exclude_unset=True), user)
    db.commit()
    log_entity_updated(
        db,
        entity_type=ActivityEntityType.MARKETING_FORM,
        entity_id=form.id,
        description_key="marketing.form.updated",
        actor=user,
        request=request,
    )
    db.commit()
    return _form_summary(form)


@router.get("/{form_id}/readiness", response_model=FormReadinessResponse)
def form_readiness_route(
    form_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    return compute_form_readiness(db, form_id)


@router.post("/{form_id}/publish", response_model=FormSummary)
def publish_form_route(
    form_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "publish_forms")),
):
    form = publish_form(db, form_id, user)
    db.commit()
    return _form_summary(form)


@router.get("/{form_id}/fields", response_model=list[FormFieldResponse])
def list_fields_route(
    form_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    fields = list_fields(db, form_id)
    return [
        FormFieldResponse(
            id=f.id,
            form_id=f.form_id,
            field_key=f.field_key,
            field_type=f.field_type.value if hasattr(f.field_type, "value") else f.field_type,
            label=f.label,
            sort_order=f.sort_order,
            required=f.required,
            config_json=f.config_json,
            validation_json=f.validation_json,
            is_visible=f.is_visible,
        )
        for f in fields
    ]


@router.post("/{form_id}/fields", response_model=FormFieldResponse, status_code=201)
def add_field_route(
    form_id: UUID,
    payload: FormFieldCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    field = add_field(db, form_id, payload.model_dump())
    db.commit()
    return FormFieldResponse(
        id=field.id,
        form_id=field.form_id,
        field_key=field.field_key,
        field_type=field.field_type.value if hasattr(field.field_type, "value") else field.field_type,
        label=field.label,
        sort_order=field.sort_order,
        required=field.required,
        config_json=field.config_json,
        validation_json=field.validation_json,
        is_visible=field.is_visible,
    )


@router.patch("/fields/{field_id}", response_model=FormFieldResponse)
def update_field_route(
    field_id: UUID,
    payload: FormFieldUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    field = update_field(db, field_id, payload.model_dump(exclude_unset=True))
    db.commit()
    return FormFieldResponse(
        id=field.id,
        form_id=field.form_id,
        field_key=field.field_key,
        field_type=field.field_type.value if hasattr(field.field_type, "value") else field.field_type,
        label=field.label,
        sort_order=field.sort_order,
        required=field.required,
        config_json=field.config_json,
        validation_json=field.validation_json,
        is_visible=field.is_visible,
    )


@router.post("/{form_id}/logic", response_model=FormLogicGroupResponse, status_code=201)
def add_logic_route(
    form_id: UUID,
    payload: FormLogicGroupCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    group = add_logic_group(db, form_id, payload.model_dump())
    db.commit()
    return FormLogicGroupResponse(
        id=group.id,
        form_id=group.form_id,
        target_field_id=group.target_field_id,
        operator=group.operator.value if hasattr(group.operator, "value") else group.operator,
        action=group.action,
        conditions_json=group.conditions_json,
        sort_order=group.sort_order,
    )


@router.get("/{form_id}/versions")
def list_form_versions_route(
    form_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_forms")),
):
    return list_form_versions(db, form_id)
