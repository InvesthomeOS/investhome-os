"""Marketing lead capture API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_landing_conversion import (
    HandoffSLAResponse,
    LeadCaptureDashboard,
    LeadRoutingRuleCreate,
    LeadRoutingRuleResponse,
    SalesHandoffResponse,
    SubmissionSummary,
)
from investhome_api.services.marketing.lead_capture_service import (
    create_handoff_record,
    create_routing_rule,
    get_lead_capture_dashboard,
    list_duplicates,
    list_handoffs,
    list_routing_rules,
    list_slas,
    list_verification_queue,
)
from investhome_api.services.marketing.submission_service import compute_pages

router = APIRouter(prefix="/marketing/lead-capture", tags=["marketing-lead-capture"])


@router.get("/dashboard", response_model=LeadCaptureDashboard)
def lead_capture_dashboard_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_lead_capture")),
):
    return get_lead_capture_dashboard(db)


@router.get("/routing", response_model=list[LeadRoutingRuleResponse])
def list_routing_rules_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_lead_routing")),
):
    rules = list_routing_rules(db)
    return [
        LeadRoutingRuleResponse(
            id=r.id,
            name=r.name,
            priority=r.priority,
            is_active=r.is_active,
            is_fallback=r.is_fallback,
            conditions_json=r.conditions_json,
            action_json=r.action_json,
            form_id=r.form_id,
            source_id=r.source_id,
        )
        for r in rules
    ]


@router.post("/routing", response_model=LeadRoutingRuleResponse, status_code=201)
def create_routing_rule_route(
    payload: LeadRoutingRuleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_lead_routing")),
):
    rule = create_routing_rule(db, payload.model_dump())
    db.commit()
    return LeadRoutingRuleResponse(
        id=rule.id,
        name=rule.name,
        priority=rule.priority,
        is_active=rule.is_active,
        is_fallback=rule.is_fallback,
        conditions_json=rule.conditions_json,
        action_json=rule.action_json,
        form_id=rule.form_id,
        source_id=rule.source_id,
    )


@router.get("/handoff", response_model=list[SalesHandoffResponse])
def list_handoffs_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_lead_capture")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    items, _ = list_handoffs(db, page=page, page_size=page_size)
    return [
        SalesHandoffResponse(
            id=h.id,
            lead_context_id=h.lead_context_id,
            submission_id=h.submission_id,
            sales_lead_id=h.sales_lead_id,
            status=h.status,
            due_at=h.due_at,
            blockers_json=h.blockers_json,
        )
        for h in items
    ]


@router.post("/handoff/{context_id}", response_model=SalesHandoffResponse, status_code=201)
def create_handoff_route(
    context_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "hand_to_sales")),
):
    handoff = create_handoff_record(db, context_id)
    db.commit()
    return SalesHandoffResponse(
        id=handoff.id,
        lead_context_id=handoff.lead_context_id,
        submission_id=handoff.submission_id,
        sales_lead_id=handoff.sales_lead_id,
        status=handoff.status,
        due_at=handoff.due_at,
        blockers_json=handoff.blockers_json,
    )


@router.get("/slas", response_model=list[HandoffSLAResponse])
def list_slas_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_lead_capture")),
):
    return list_slas(db)


@router.get("/duplicates")
def list_duplicates_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_lead_capture")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    items, total = list_duplicates(db, page=page, page_size=page_size)
    return {
        "items": [
            SubmissionSummary(
                id=s.id,
                form_id=s.form_id,
                landing_page_id=s.landing_page_id,
                status=s.status.value if hasattr(s.status, "value") else s.status,
                contact_id=s.contact_id,
                lead_context_id=s.lead_context_id,
                created_at=s.created_at,
            )
            for s in items
        ],
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.get("/verification")
def verification_queue_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "verify")),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    items, total = list_verification_queue(db, page=page, page_size=page_size)
    return {
        "items": [{"id": str(i.id), "contact_id": str(i.contact_id) if i.contact_id else None} for i in items],
        "total": total,
        "pages": compute_pages(total, page_size),
    }
