"""Sales contract readiness API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.inventory import InventoryAsset
from investhome_api.models.lead import Lead
from investhome_api.models.investor import Investor
from investhome_api.models.sales import OpportunityPartyType, SalesOpportunity
from investhome_api.models.sales_readiness import (
    BLOCKING_REQUIREMENT_STATUSES,
    ReadinessCaseStatus,
    SalesReadinessCase,
    SalesReadinessRequirement,
)
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import WorkItemType
from investhome_api.schemas.sales_readiness import (
    AddRequirementRequest,
    CancelCasePayload,
    ContractSignedPayload,
    CreateFollowUpFromReadinessRequest,
    CreateReadinessCaseRequest,
    DepositSummaryResponse,
    HandoffApprovePayload,
    HandoffRequestPayload,
    HandoffReturnPayload,
    LinkSourceRequest,
    ReadinessCaseListResponse,
    ReadinessCaseResponse,
    ReadinessDashboardKpisResponse,
    ReadinessRequirementResponse,
    ReadinessStatusHistoryResponse,
    RejectRequirementRequest,
    ReopenRequirementRequest,
    UpdateReadinessCaseRequest,
    VerifyRequirementRequest,
    WaiveRequirementRequest,
)
from investhome_api.services.sales import readiness_requirement_service as req_svc
from investhome_api.services.sales import readiness_service as svc
from investhome_api.services.work import work_item_service as work_svc

router = APIRouter(prefix="/sales/readiness", tags=["sales-readiness"])


def _handle_error(exc: svc.ReadinessError | req_svc.ReadinessRequirementError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.error_key)


def _enrich_case(
    db: Session,
    case: SalesReadinessCase,
    *,
    user: User,
    include_requirements: bool = False,
    include_deposit: bool = False,
) -> ReadinessCaseResponse:
    response = ReadinessCaseResponse.model_validate(case)
    opportunity = db.get(SalesOpportunity, case.opportunity_id)
    if opportunity:
        response.opportunity_code = opportunity.opportunity_code
    if case.party_id and opportunity:
        if opportunity.party_type == OpportunityPartyType.LEAD:
            lead = db.get(Lead, case.party_id)
            response.party_name = lead.full_name if lead else None
        else:
            investor = db.get(Investor, case.party_id)
            response.party_name = investor.full_name if investor else None
    if case.inventory_asset_id:
        asset = db.get(InventoryAsset, case.inventory_asset_id)
        response.inventory_display_id = asset.display_id if asset else None
    if include_requirements:
        requirements = req_svc.list_requirements(db, case.id)
        response.requirements = [ReadinessRequirementResponse.model_validate(r) for r in requirements]
        response.missing_mandatory_count = sum(
            1 for r in requirements if r.is_mandatory and r.status in BLOCKING_REQUIREMENT_STATUSES
        )
    if include_deposit:
        try:
            summary = svc.get_deposit_summary(db, case, user=user)
            response.deposit_summary = DepositSummaryResponse(**summary)
        except svc.ReadinessError:
            pass
    return response


@router.get("/dashboard/kpis", response_model=ReadinessDashboardKpisResponse)
def get_dashboard_kpis(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_readiness")),
) -> ReadinessDashboardKpisResponse:
    try:
        return ReadinessDashboardKpisResponse(**svc.build_dashboard_kpis(db, user))
    except svc.ReadinessError as exc:
        raise _handle_error(exc) from exc


@router.get("/cases", response_model=ReadinessCaseListResponse)
def list_cases(
    view: str | None = Query(default=None),
    opportunity_id: UUID | None = Query(default=None),
    project_id: UUID | None = Query(default=None),
    inventory_asset_id: UUID | None = Query(default=None),
    party_id: UUID | None = Query(default=None),
    assigned_sales_user_id: UUID | None = Query(default=None),
    assigned_legal_user_id: UUID | None = Query(default=None),
    assigned_finance_user_id: UUID | None = Query(default=None),
    status: ReadinessCaseStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    sort_by: str = Query(default="updated_at"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_readiness")),
) -> ReadinessCaseListResponse:
    try:
        items, total = svc.list_cases(
            db,
            user,
            view=view,
            opportunity_id=opportunity_id,
            project_id=project_id,
            inventory_asset_id=inventory_asset_id,
            party_id=party_id,
            assigned_sales_user_id=assigned_sales_user_id,
            assigned_legal_user_id=assigned_legal_user_id,
            assigned_finance_user_id=assigned_finance_user_id,
            status=status,
            search=search,
            include_archived=include_archived,
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_dir=sort_dir,
        )
    except svc.ReadinessError as exc:
        raise _handle_error(exc) from exc
    return ReadinessCaseListResponse(
        items=[_enrich_case(db, item, user=user) for item in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/cases/{case_id}", response_model=ReadinessCaseResponse)
def get_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
    except svc.ReadinessError as exc:
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True, include_deposit=True)


@router.post("/opportunities/{opportunity_id}/cases", response_model=ReadinessCaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    opportunity_id: UUID,
    payload: CreateReadinessCaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "create_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.create_from_opportunity(
            db,
            opportunity_id,
            payload.model_dump(exclude_unset=True),
            actor=user,
            request=request,
        )
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True, include_deposit=True)


@router.patch("/cases/{case_id}", response_model=ReadinessCaseResponse)
def update_case(
    case_id: UUID,
    payload: UpdateReadinessCaseRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.update_assignments(
            db,
            case,
            payload.model_dump(exclude_unset=True),
            actor=user,
            request=request,
        )
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True, include_deposit=True)


@router.post("/cases/{case_id}/recalculate", response_model=ReadinessCaseResponse)
def recalculate_case(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True, include_deposit=True)


@router.delete("/cases/{case_id}", response_model=ReadinessCaseResponse)
def archive_case(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.archive_case(db, case, actor=user, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user)


@router.post("/cases/{case_id}/restore", response_model=ReadinessCaseResponse)
def restore_case(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id, include_archived=True)
        case = svc.restore_case(db, case, actor=user, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/cancel", response_model=ReadinessCaseResponse)
def cancel_case(
    case_id: UUID,
    payload: CancelCasePayload,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.cancel_case(db, case, actor=user, reason=payload.reason, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user)


@router.post("/cases/{case_id}/ready-for-contract", response_model=ReadinessCaseResponse)
def mark_ready_for_contract(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.mark_ready_for_contract(db, case, actor=user, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/contract-preparation", response_model=ReadinessCaseResponse)
def mark_contract_preparation(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.mark_contract_preparation(db, case, actor=user, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/signature-pending", response_model=ReadinessCaseResponse)
def mark_signature_pending(
    case_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.mark_signature_pending(db, case, actor=user, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/contract-signed", response_model=ReadinessCaseResponse)
def mark_contract_signed(
    case_id: UUID,
    payload: ContractSignedPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.mark_contract_signed(
            db,
            case,
            actor=user,
            signed_document_id=payload.signed_document_id,
            request=request,
        )
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/handoff/request", response_model=ReadinessCaseResponse)
def request_handoff(
    case_id: UUID,
    payload: HandoffRequestPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "request_handoff")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.request_handoff(db, case, actor=user, notes=payload.notes, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/handoff/approve", response_model=ReadinessCaseResponse)
def approve_handoff(
    case_id: UUID,
    payload: HandoffApprovePayload,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "approve_handoff")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.approve_handoff(db, case, actor=user, notes=payload.notes, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.post("/cases/{case_id}/handoff/return", response_model=ReadinessCaseResponse)
def return_handoff(
    case_id: UUID,
    payload: HandoffReturnPayload,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "return_handoff")),
) -> ReadinessCaseResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        case = svc.return_handoff(db, case, actor=user, reason=payload.reason, request=request)
        db.commit()
        db.refresh(case)
    except svc.ReadinessError as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return _enrich_case(db, case, user=user, include_requirements=True)


@router.get("/cases/{case_id}/status-history", response_model=list[ReadinessStatusHistoryResponse])
def get_status_history(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_readiness")),
) -> list[ReadinessStatusHistoryResponse]:
    try:
        svc.get_case_or_raise(db, case_id)
    except svc.ReadinessError as exc:
        raise _handle_error(exc) from exc
    history = svc.get_status_history(db, case_id)
    return [ReadinessStatusHistoryResponse.model_validate(h) for h in history]


@router.get("/cases/{case_id}/requirements", response_model=list[ReadinessRequirementResponse])
def list_requirements(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_readiness")),
) -> list[ReadinessRequirementResponse]:
    try:
        svc.get_case_or_raise(db, case_id)
    except svc.ReadinessError as exc:
        raise _handle_error(exc) from exc
    requirements = req_svc.list_requirements(db, case_id)
    return [ReadinessRequirementResponse.model_validate(r) for r in requirements]


@router.post("/cases/{case_id}/requirements", response_model=ReadinessRequirementResponse, status_code=status.HTTP_201_CREATED)
def add_requirement(
    case_id: UUID,
    payload: AddRequirementRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessRequirementResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        req = req_svc.add_manual_requirement(db, case, payload.model_dump(), actor=user)
        svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(req)
    except (svc.ReadinessError, req_svc.ReadinessRequirementError) as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return ReadinessRequirementResponse.model_validate(req)


@router.post("/requirements/{requirement_id}/verify", response_model=ReadinessRequirementResponse)
def verify_requirement(
    requirement_id: UUID,
    payload: VerifyRequirementRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "verify_readiness")),
) -> ReadinessRequirementResponse:
    try:
        req = req_svc.get_requirement_or_raise(db, requirement_id)
        req = req_svc.verify_requirement(db, req, actor=user, notes=payload.notes, request=request)
        case = svc.get_case_or_raise(db, req.readiness_case_id)
        svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(req)
    except (svc.ReadinessError, req_svc.ReadinessRequirementError) as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return ReadinessRequirementResponse.model_validate(req)


@router.post("/requirements/{requirement_id}/reject", response_model=ReadinessRequirementResponse)
def reject_requirement(
    requirement_id: UUID,
    payload: RejectRequirementRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "verify_readiness")),
) -> ReadinessRequirementResponse:
    try:
        req = req_svc.get_requirement_or_raise(db, requirement_id)
        req = req_svc.reject_requirement(db, req, actor=user, reason=payload.reason, request=request)
        case = svc.get_case_or_raise(db, req.readiness_case_id)
        svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(req)
    except (svc.ReadinessError, req_svc.ReadinessRequirementError) as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return ReadinessRequirementResponse.model_validate(req)


@router.post("/requirements/{requirement_id}/waive", response_model=ReadinessRequirementResponse)
def waive_requirement(
    requirement_id: UUID,
    payload: WaiveRequirementRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "waive_requirement")),
) -> ReadinessRequirementResponse:
    try:
        req = req_svc.get_requirement_or_raise(db, requirement_id)
        req = req_svc.waive_requirement(db, req, actor=user, reason=payload.reason, request=request)
        case = svc.get_case_or_raise(db, req.readiness_case_id)
        svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(req)
    except (svc.ReadinessError, req_svc.ReadinessRequirementError) as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return ReadinessRequirementResponse.model_validate(req)


@router.post("/requirements/{requirement_id}/reopen", response_model=ReadinessRequirementResponse)
def reopen_requirement(
    requirement_id: UUID,
    payload: ReopenRequirementRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessRequirementResponse:
    try:
        req = req_svc.get_requirement_or_raise(db, requirement_id)
        req = req_svc.reopen_requirement(db, req, actor=user, reason=payload.reason, request=request)
        case = svc.get_case_or_raise(db, req.readiness_case_id)
        svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(req)
    except (svc.ReadinessError, req_svc.ReadinessRequirementError) as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return ReadinessRequirementResponse.model_validate(req)


@router.post("/requirements/{requirement_id}/link", response_model=ReadinessRequirementResponse)
def link_source(
    requirement_id: UUID,
    payload: LinkSourceRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "update_readiness")),
) -> ReadinessRequirementResponse:
    try:
        req = req_svc.get_requirement_or_raise(db, requirement_id)
        req = req_svc.link_source(
            db,
            req,
            source_entity_type=payload.source_entity_type,
            source_entity_id=payload.source_entity_id,
            actor=user,
            request=request,
        )
        case = svc.get_case_or_raise(db, req.readiness_case_id)
        svc.recalculate_case(db, case, actor=user)
        db.commit()
        db.refresh(req)
    except (svc.ReadinessError, req_svc.ReadinessRequirementError) as exc:
        db.rollback()
        raise _handle_error(exc) from exc
    return ReadinessRequirementResponse.model_validate(req)


@router.get("/opportunities/{opportunity_id}/summary", response_model=ReadinessCaseResponse | None)
def get_opportunity_readiness(
    opportunity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_readiness")),
) -> ReadinessCaseResponse | None:
    from sqlalchemy import select

    case = db.scalar(
        select(SalesReadinessCase)
        .where(
            SalesReadinessCase.opportunity_id == opportunity_id,
            SalesReadinessCase.archived_at.is_(None),
            SalesReadinessCase.status.not_in(
                [ReadinessCaseStatus.CANCELLED, ReadinessCaseStatus.ARCHIVED]
            ),
        )
        .order_by(SalesReadinessCase.updated_at.desc())
        .limit(1)
    )
    if case is None:
        return None
    return _enrich_case(db, case, user=user, include_requirements=True, include_deposit=True)


@router.get("/cases/{case_id}/deposit", response_model=DepositSummaryResponse)
def get_deposit_summary(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "view_deposit_status")),
) -> DepositSummaryResponse:
    try:
        case = svc.get_case_or_raise(db, case_id)
        summary = svc.get_deposit_summary(db, case, user=user)
    except svc.ReadinessError as exc:
        raise _handle_error(exc) from exc
    return DepositSummaryResponse(**summary)


@router.post("/cases/{case_id}/follow-ups", status_code=status.HTTP_201_CREATED)
def create_follow_up_from_readiness(
    case_id: UUID,
    payload: CreateFollowUpFromReadinessRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("sales", "manage_followups")),
):
    try:
        case = svc.get_case_or_raise(db, case_id)
        wi_type = WorkItemType(payload.follow_up_type)
        item, _ = work_svc.create_follow_up(
            db,
            {
                "title": payload.title or f"Readiness follow-up: {case.case_code}",
                "work_item_type": wi_type,
                "due_at": payload.due_at,
                "notes": payload.notes,
                "opportunity_id": case.opportunity_id,
                "lead_id": case.lead_id,
                "inventory_asset_id": case.inventory_asset_id,
                "related_entity_type": "opportunity",
                "related_entity_id": case.opportunity_id,
            },
            actor=user,
            request=request,
        )
        db.commit()
    except (svc.ReadinessError, work_svc.WorkItemError, ValueError) as exc:
        db.rollback()
        if isinstance(exc, svc.ReadinessError):
            raise _handle_error(exc) from exc
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    from investhome_api.schemas.work_item import WorkItemResponse

    return WorkItemResponse.model_validate(item)
