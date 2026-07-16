"""Apply configurable readiness templates to cases."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.sales_readiness import (
    ReadinessRequirementStatus,
    SalesReadinessCase,
    SalesReadinessRequirement,
    SalesReadinessTemplate,
    SalesReadinessTemplateItem,
)
from investhome_api.services.sales.readiness_config import DEFAULT_TEMPLATE_ITEMS, REQUIREMENT_GROUP_MAP


def get_default_template(db: Session) -> SalesReadinessTemplate | None:
    return db.scalar(
        select(SalesReadinessTemplate).where(
            SalesReadinessTemplate.is_default.is_(True),
            SalesReadinessTemplate.is_active.is_(True),
        )
    )


def resolve_template(
    db: Session,
    *,
    project_id: UUID | None = None,
    asset_type: str | None = None,
    party_type: str | None = None,
) -> SalesReadinessTemplate | None:
    """Pick best matching template — project-specific first, else default."""
    if project_id:
        specific = db.scalar(
            select(SalesReadinessTemplate).where(
                SalesReadinessTemplate.project_id == project_id,
                SalesReadinessTemplate.is_active.is_(True),
            )
        )
        if specific:
            return specific
    return get_default_template(db)


def apply_template_to_case(
    db: Session,
    case: SalesReadinessCase,
    *,
    template: SalesReadinessTemplate | None = None,
) -> list[SalesReadinessRequirement]:
    """Create requirements from template items — idempotent for existing types."""
    existing_types = {
        req.requirement_type
        for req in db.scalars(
            select(SalesReadinessRequirement).where(
                SalesReadinessRequirement.readiness_case_id == case.id
            )
        ).all()
    }

    items: list[SalesReadinessTemplateItem] = []
    if template:
        items = list(
            db.scalars(
                select(SalesReadinessTemplateItem)
                .where(SalesReadinessTemplateItem.template_id == template.id)
                .order_by(SalesReadinessTemplateItem.sort_order)
            ).all()
        )

    created: list[SalesReadinessRequirement] = []
    if not items:
        for entry in DEFAULT_TEMPLATE_ITEMS:
            req_type = entry["type"]
            if req_type in existing_types:
                continue
            req = SalesReadinessRequirement(
                readiness_case_id=case.id,
                requirement_type=req_type,
                template_group=entry["group"],
                title=entry["title"],
                is_mandatory=entry["mandatory"],
                status=ReadinessRequirementStatus.MISSING,
            )
            db.add(req)
            created.append(req)
            existing_types.add(req_type)
        db.flush()
        return created

    for item in items:
        if item.requirement_type in existing_types:
            continue
        req = SalesReadinessRequirement(
            readiness_case_id=case.id,
            requirement_type=item.requirement_type,
            template_group=item.template_group,
            title=item.title,
            description=item.description,
            is_mandatory=item.is_mandatory,
            status=ReadinessRequirementStatus.MISSING,
        )
        db.add(req)
        created.append(req)
        existing_types.add(item.requirement_type)
    db.flush()
    return created


def seed_default_template(db: Session) -> SalesReadinessTemplate:
    """Ensure default template exists — used in migration and tests."""
    existing = get_default_template(db)
    if existing:
        return existing
    template = SalesReadinessTemplate(
        code="default",
        name="Default Contract Readiness",
        description="Standard reservation → deposit → contract → handoff checklist",
        is_default=True,
        is_active=True,
    )
    db.add(template)
    db.flush()
    for entry in DEFAULT_TEMPLATE_ITEMS:
        db.add(
            SalesReadinessTemplateItem(
                template_id=template.id,
                template_group=entry["group"],
                requirement_type=entry["type"],
                title=entry["title"],
                is_mandatory=entry["mandatory"],
                sort_order=entry["order"],
            )
        )
    db.flush()
    return template
