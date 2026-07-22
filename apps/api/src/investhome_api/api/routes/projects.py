from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.project import (
    DevelopmentStage,
    DevelopmentType,
    ProjectPriority,
    ProjectStatus,
    ProjectType,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
    ProjectStatusChangeRequest,
    ProjectStatusTransitionResponse,
    ProjectTeamListResponse,
    ProjectTeamMemberCreate,
    ProjectTeamMemberResponse,
    ProjectTeamMemberUpdate,
    ProjectUpdate,
)
from investhome_api.schemas.project_dashboard import (
    ProjectActivityListResponse,
    ProjectAlertListResponse,
    ProjectDashboardResponse,
    ProjectMilestoneListResponse,
)
from investhome_api.schemas.project_detail import (
    ProjectConstructionResponse,
    ProjectDetailShell,
    ProjectDirectoryUserListResponse,
    ProjectDocumentsResponse,
    ProjectFinancialsResponse,
    ProjectInvestorsResponse,
    ProjectLeasingResponse,
    ProjectOverviewResponse,
    ProjectSalesResponse,
    ProjectScheduleResponse,
    ProjectUnitsResponse,
)
from investhome_api.schemas.project_executive_finance import (
    ProjectCashFlowSummaryResponse,
    ProjectExecutiveFinanceResponse,
)
from investhome_api.services import project_dashboard_service as dashboard_svc
from investhome_api.services import project_detail_service as detail_svc
from investhome_api.services import project_executive_finance_service as executive_finance_svc
from investhome_api.services import project_service as svc

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/stats", response_model=ProjectStatsResponse)
def get_project_stats(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectStatsResponse:
    return svc.get_project_stats(db, user=user)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    search: str | None = Query(default=None, max_length=255),
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    project_type: ProjectType | None = None,
    development_type: DevelopmentType | None = None,
    priority: ProjectPriority | None = None,
    development_stage: DevelopmentStage | None = None,
    city: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
    assigned_project_manager: str | None = Query(default=None, max_length=255),
    project_manager_user_id: UUID | None = None,
    completion_year: int | None = Query(default=None, ge=1900, le=2100),
    start_date_from: date | None = None,
    start_date_to: date | None = None,
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectListResponse:
    return svc.list_projects(
        db,
        user=user,
        search=search,
        status_filter=status_filter,
        project_type=project_type,
        development_type=development_type,
        priority=priority,
        development_stage=development_stage,
        city=city,
        state=state,
        country=country,
        assigned_project_manager=assigned_project_manager,
        project_manager_user_id=project_manager_user_id,
        completion_year=completion_year,
        start_date_from=start_date_from,
        start_date_to=start_date_to,
        include_archived=include_archived,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )


@router.get("/dashboard", response_model=ProjectDashboardResponse)
def get_projects_dashboard(
    search: str | None = Query(default=None, max_length=255),
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    project_type: ProjectType | None = None,
    priority: ProjectPriority | None = None,
    development_stage: DevelopmentStage | None = None,
    city: str | None = Query(default=None, max_length=100),
    state: str | None = Query(default=None, max_length=100),
    country: str | None = Query(default=None, max_length=100),
    project_manager_user_id: UUID | None = None,
    completion_year: int | None = Query(default=None, ge=1900, le=2100),
    include_archived: bool = Query(default=False),
    milestone_days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectDashboardResponse:
    return dashboard_svc.build_dashboard(
        db,
        user,
        search=search,
        status=status_filter,
        project_type=project_type,
        priority=priority,
        development_stage=development_stage,
        project_manager_user_id=project_manager_user_id,
        city=city,
        state=state,
        country=country,
        completion_year=completion_year,
        include_archived=include_archived,
        milestone_days=milestone_days,
    )


@router.get("/upcoming-milestones", response_model=ProjectMilestoneListResponse)
def get_upcoming_milestones(
    days: int = Query(default=30, ge=1, le=365),
    project_id: UUID | None = None,
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view")),
) -> ProjectMilestoneListResponse:
    return dashboard_svc.list_milestones(
        db,
        days=days,
        project_id=project_id,
        include_archived=include_archived,
    )


@router.get("/critical-items", response_model=ProjectAlertListResponse)
def get_critical_items(
    include_archived: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectAlertListResponse:
    return dashboard_svc.list_critical_items(
        db,
        user,
        include_archived=include_archived,
        limit=limit,
    )


@router.get("/recent-activity", response_model=ProjectActivityListResponse)
def get_recent_project_activity(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectActivityListResponse:
    return dashboard_svc.list_recent_activity(db, user, limit=limit)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectResponse:
    project = svc.get_project_or_404(db, project_id)
    return svc.to_project_response(db, project, user=user, include_team=True)


@router.get("/{project_id}/detail", response_model=ProjectDetailShell)
def get_project_detail(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectDetailShell:
    return detail_svc.build_shell(db, user, project_id)


@router.get("/{project_id}/overview", response_model=ProjectOverviewResponse)
def get_project_overview(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectOverviewResponse:
    return detail_svc.get_overview(db, user, project_id)


@router.get("/{project_id}/campaigns")
def get_project_campaigns(
    project_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> dict:
    """Related marketing campaigns for a project (Sprint 8A1)."""
    from investhome_api.services.marketing.campaign_service import (
        compute_pages,
        list_campaigns_for_project,
    )
    from investhome_api.services.permission_service import user_has_permission

    svc.get_project_or_404(db, project_id)
    if not (
        user_has_permission(user, "marketing", "view")
        or user_has_permission(user, "marketing", "manage_campaigns")
        or user_has_permission(user, "marketing", "view_dashboard")
    ):
        return {"items": [], "page": page, "page_size": page_size, "total": 0, "pages": 0}
    items, total = list_campaigns_for_project(db, project_id, page=page, page_size=page_size)
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": compute_pages(total, page_size),
    }


@router.get("/{project_id}/financials", response_model=ProjectFinancialsResponse)
def get_project_financials(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectFinancialsResponse:
    return detail_svc.get_financials(db, user, project_id)


@router.get(
    "/{project_id}/executive-finance",
    response_model=ProjectExecutiveFinanceResponse,
)
def get_project_executive_finance(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectExecutiveFinanceResponse:
    return executive_finance_svc.get_executive_finance(db, user, project_id)


@router.get(
    "/{project_id}/cash-flow-summary",
    response_model=ProjectCashFlowSummaryResponse,
)
def get_project_cash_flow_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectCashFlowSummaryResponse:
    return executive_finance_svc.get_cash_flow_summary(db, user, project_id)


@router.get("/{project_id}/schedule", response_model=ProjectScheduleResponse)
def get_project_schedule(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectScheduleResponse:
    return detail_svc.get_schedule(db, user, project_id)


@router.get("/{project_id}/construction", response_model=ProjectConstructionResponse)
def get_project_construction(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectConstructionResponse:
    return detail_svc.get_construction(db, user, project_id)


@router.get("/{project_id}/units", response_model=ProjectUnitsResponse)
def get_project_units(
    project_id: UUID,
    search: str | None = Query(default=None, max_length=255),
    availability_status: str | None = None,
    sales_status: str | None = None,
    leasing_status: str | None = None,
    asset_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="display_id"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectUnitsResponse:
    return detail_svc.get_units(
        db,
        user,
        project_id,
        search=search,
        availability_status=availability_status,
        sales_status=sales_status,
        leasing_status=leasing_status,
        asset_type=asset_type,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/{project_id}/sales", response_model=ProjectSalesResponse)
def get_project_sales(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectSalesResponse:
    return detail_svc.get_sales(db, user, project_id)


@router.get("/{project_id}/leasing", response_model=ProjectLeasingResponse)
def get_project_leasing(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectLeasingResponse:
    return detail_svc.get_leasing(db, user, project_id)


@router.get("/{project_id}/investors", response_model=ProjectInvestorsResponse)
def get_project_investors(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectInvestorsResponse:
    return detail_svc.get_investors(db, user, project_id)


@router.get("/{project_id}/documents", response_model=ProjectDocumentsResponse)
def get_project_documents(
    project_id: UUID,
    search: str | None = Query(default=None, max_length=255),
    category: str | None = Query(default=None, max_length=100),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectDocumentsResponse:
    return detail_svc.get_documents(
        db,
        user,
        project_id,
        search=search,
        category=category,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/{project_id}/activity", response_model=ProjectActivityListResponse)
def get_project_activity(
    project_id: UUID,
    search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectActivityListResponse:
    return detail_svc.list_recent_activity(
        db, user, project_id, search=search, page=page, page_size=page_size
    )


@router.get("/{project_id}/alerts", response_model=ProjectAlertListResponse)
def get_project_alerts(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectAlertListResponse:
    return detail_svc.list_project_alerts(db, user, project_id)


@router.get("/{project_id}/milestones", response_model=ProjectMilestoneListResponse)
def get_project_milestones(
    project_id: UUID,
    days: int = Query(default=365, ge=1, le=730),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectMilestoneListResponse:
    return detail_svc.list_project_milestones(db, user, project_id, days=days)


@router.get("/{project_id}/directory-users", response_model=ProjectDirectoryUserListResponse)
def search_project_directory_users(
    project_id: UUID,
    search: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> ProjectDirectoryUserListResponse:
    return detail_svc.search_directory_users(
        db, user, project_id, search=search, limit=limit
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "create")),
) -> ProjectResponse:
    project = svc.create_project(db, payload, actor=actor, request=request)
    return svc.to_project_response(db, project, user=actor, include_team=True)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "update")),
) -> ProjectResponse:
    project = svc.update_project(db, project_id, payload, actor=actor, request=request)
    return svc.to_project_response(db, project, user=actor, include_team=True)


@router.delete("/{project_id}", response_model=ProjectResponse)
def archive_project(
    project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "archive")),
) -> ProjectResponse:
    project = svc.archive_project(db, project_id, actor=actor, request=request)
    return svc.to_project_response(db, project, user=actor)


@router.post("/{project_id}/restore", response_model=ProjectResponse)
def restore_project(
    project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "restore")),
) -> ProjectResponse:
    project = svc.restore_project(db, project_id, actor=actor, request=request)
    return svc.to_project_response(db, project, user=actor, include_team=True)


@router.get("/{project_id}/status-transitions", response_model=ProjectStatusTransitionResponse)
def get_status_transitions(
    project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view")),
) -> ProjectStatusTransitionResponse:
    return svc.get_status_transitions(db, project_id)


@router.post("/{project_id}/status", response_model=ProjectResponse)
def change_project_status(
    project_id: UUID,
    payload: ProjectStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "manage_status")),
) -> ProjectResponse:
    project = svc.change_project_status(
        db,
        project_id,
        payload.status,
        actor=actor,
        request=request,
        note=payload.note,
    )
    return svc.to_project_response(db, project, user=actor, include_team=True)


@router.get("/{project_id}/team", response_model=ProjectTeamListResponse)
def list_project_team(
    project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view_team")),
) -> ProjectTeamListResponse:
    return svc.list_team_members(db, project_id)


@router.post(
    "/{project_id}/team",
    response_model=ProjectTeamMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_project_team_member(
    project_id: UUID,
    payload: ProjectTeamMemberCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "manage_team")),
) -> ProjectTeamMemberResponse:
    member = svc.assign_team_member(db, project_id, payload, actor=actor, request=request)
    return svc.to_team_member_response(db, member)


@router.patch("/{project_id}/team/{member_id}", response_model=ProjectTeamMemberResponse)
def update_project_team_member(
    project_id: UUID,
    member_id: UUID,
    payload: ProjectTeamMemberUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "manage_team")),
) -> ProjectTeamMemberResponse:
    member = svc.update_team_member(
        db, project_id, member_id, payload, actor=actor, request=request
    )
    return svc.to_team_member_response(db, member)


@router.delete("/{project_id}/team/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_team_member(
    project_id: UUID,
    member_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "manage_team")),
) -> None:
    svc.remove_team_member(db, project_id, member_id, actor=actor, request=request)
