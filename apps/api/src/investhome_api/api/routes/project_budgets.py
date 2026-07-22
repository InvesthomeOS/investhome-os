"""Project budget foundation routes (Sprint 10A4A)."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_budget_foundation import (
    BudgetCategoryCreate,
    BudgetCategoryResponse,
    BudgetCategoryUpdate,
    BudgetImportConfirmRequest,
    BudgetImportPreviewResponse,
    BudgetImportResultResponse,
    BudgetLineBulkCreateRequest,
    BudgetLineCreate,
    BudgetLineListResponse,
    BudgetLineReorderRequest,
    BudgetLineResponse,
    BudgetLineUpdate,
    BudgetRevisionCreate,
    BudgetRevisionListResponse,
    BudgetRevisionResponse,
    BudgetRevisionUpdate,
    BudgetSummaryResponse,
    BudgetVersionCreate,
    BudgetVersionListResponse,
    BudgetVersionResponse,
    BudgetVersionUpdate,
    CostCodeCreate,
    CostCodeResponse,
    CostCodeUpdate,
)
from investhome_api.services import project_budget_service as svc

router = APIRouter(tags=["project-budgets"])


# ---------------------------------------------------------------------------
# Taxonomy
# ---------------------------------------------------------------------------


@router.get("/budget-categories", response_model=list[BudgetCategoryResponse])
def list_budget_categories(
    search: str | None = Query(default=None, max_length=255),
    active_only: bool = Query(default=True),
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view_financial")),
) -> list[BudgetCategoryResponse]:
    return svc.list_categories(db, search=search, active_only=active_only, company_id=company_id)


@router.post(
    "/budget-categories",
    response_model=BudgetCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_budget_category(
    payload: BudgetCategoryCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> BudgetCategoryResponse:
    return svc.create_category(db, payload, actor=actor)


@router.patch("/budget-categories/{category_id}", response_model=BudgetCategoryResponse)
def update_budget_category(
    category_id: UUID,
    payload: BudgetCategoryUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> BudgetCategoryResponse:
    return svc.update_category(db, category_id, payload, actor=actor)


@router.delete("/budget-categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_category(db, category_id, actor=actor)


@router.get("/cost-codes", response_model=list[CostCodeResponse])
def list_cost_codes(
    search: str | None = Query(default=None, max_length=255),
    category_id: UUID | None = None,
    active_only: bool = Query(default=True),
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("projects", "view_financial")),
) -> list[CostCodeResponse]:
    return svc.list_cost_codes(
        db,
        search=search,
        category_id=category_id,
        active_only=active_only,
        company_id=company_id,
    )


@router.post("/cost-codes", response_model=CostCodeResponse, status_code=status.HTTP_201_CREATED)
def create_cost_code(
    payload: CostCodeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CostCodeResponse:
    return svc.create_cost_code(db, payload, actor=actor)


@router.patch("/cost-codes/{cost_code_id}", response_model=CostCodeResponse)
def update_cost_code(
    cost_code_id: UUID,
    payload: CostCodeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> CostCodeResponse:
    return svc.update_cost_code(db, cost_code_id, payload, actor=actor)


@router.delete("/cost-codes/{cost_code_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost_code(
    cost_code_id: UUID,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_cost_code(db, cost_code_id, actor=actor)


# ---------------------------------------------------------------------------
# Project budgets
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/budget-summary", response_model=BudgetSummaryResponse)
def get_budget_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetSummaryResponse:
    return svc.get_budget_summary(db, user, project_id)


@router.get("/projects/{project_id}/budgets", response_model=BudgetVersionListResponse)
def list_project_budgets(
    project_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionListResponse:
    return svc.list_versions(db, user, project_id)


@router.post(
    "/projects/{project_id}/budgets",
    response_model=BudgetVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_budget(
    project_id: UUID,
    payload: BudgetVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.create_version(db, user, project_id, payload, request=request)


@router.get("/projects/{project_id}/budgets/{budget_id}", response_model=BudgetVersionResponse)
def get_project_budget(
    project_id: UUID,
    budget_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.get_version(db, user, project_id, budget_id)


@router.patch("/projects/{project_id}/budgets/{budget_id}", response_model=BudgetVersionResponse)
def update_project_budget(
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetVersionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.update_version(db, user, project_id, budget_id, payload, request=request)


@router.post("/projects/{project_id}/budgets/{budget_id}/submit", response_model=BudgetVersionResponse)
def submit_project_budget(
    project_id: UUID,
    budget_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.submit_version(db, user, project_id, budget_id, request=request)


@router.post("/projects/{project_id}/budgets/{budget_id}/approve", response_model=BudgetVersionResponse)
def approve_project_budget(
    project_id: UUID,
    budget_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.approve_version(db, user, project_id, budget_id, request=request)


@router.post("/projects/{project_id}/budgets/{budget_id}/reject", response_model=BudgetVersionResponse)
def reject_project_budget(
    project_id: UUID,
    budget_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.reject_version(db, user, project_id, budget_id, request=request)


@router.post("/projects/{project_id}/budgets/{budget_id}/archive", response_model=BudgetVersionResponse)
def archive_project_budget(
    project_id: UUID,
    budget_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.archive_version(db, user, project_id, budget_id, request=request)


@router.post("/projects/{project_id}/budgets/{budget_id}/clone", response_model=BudgetVersionResponse)
def clone_project_budget(
    project_id: UUID,
    budget_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.clone_version(db, user, project_id, budget_id, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/set-current",
    response_model=BudgetVersionResponse,
)
def set_current_project_budget(
    project_id: UUID,
    budget_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetVersionResponse:
    return svc.set_current_version(db, user, project_id, budget_id, request=request)


@router.get("/projects/{project_id}/budgets/{budget_id}/lines", response_model=BudgetLineListResponse)
def list_budget_lines(
    project_id: UUID,
    budget_id: UUID,
    search: str | None = Query(default=None, max_length=255),
    category_id: UUID | None = None,
    cost_code_id: UUID | None = None,
    active_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetLineListResponse:
    return svc.list_lines(
        db,
        user,
        project_id,
        budget_id,
        search=search,
        category_id=category_id,
        cost_code_id=cost_code_id,
        active_only=active_only,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/lines",
    response_model=BudgetLineResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_budget_line(
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetLineCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetLineResponse:
    return svc.create_line(db, user, project_id, budget_id, payload, request=request)


@router.patch(
    "/projects/{project_id}/budgets/{budget_id}/lines/{line_id}",
    response_model=BudgetLineResponse,
)
def update_budget_line(
    project_id: UUID,
    budget_id: UUID,
    line_id: UUID,
    payload: BudgetLineUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetLineResponse:
    return svc.update_line(db, user, project_id, budget_id, line_id, payload, request=request)


@router.delete(
    "/projects/{project_id}/budgets/{budget_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_budget_line(
    project_id: UUID,
    budget_id: UUID,
    line_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> None:
    svc.delete_line(db, user, project_id, budget_id, line_id, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/lines/reorder",
    response_model=BudgetLineListResponse,
)
def reorder_budget_lines(
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetLineReorderRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetLineListResponse:
    return svc.reorder_lines(db, user, project_id, budget_id, payload, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/lines/bulk",
    response_model=BudgetLineListResponse,
)
def bulk_create_budget_lines(
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetLineBulkCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetLineListResponse:
    return svc.bulk_create_lines(db, user, project_id, budget_id, payload, request=request)


@router.get(
    "/projects/{project_id}/budgets/{budget_id}/revisions",
    response_model=BudgetRevisionListResponse,
)
def list_budget_revisions(
    project_id: UUID,
    budget_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionListResponse:
    return svc.list_revisions(db, user, project_id, budget_id)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/revisions",
    response_model=BudgetRevisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetRevisionCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.create_revision(db, user, project_id, budget_id, payload, request=request)


@router.get(
    "/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}",
    response_model=BudgetRevisionResponse,
)
def get_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.get_revision(db, user, project_id, budget_id, revision_id)


@router.patch(
    "/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}",
    response_model=BudgetRevisionResponse,
)
def update_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    payload: BudgetRevisionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.update_revision(
        db, user, project_id, budget_id, revision_id, payload, request=request
    )


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}/submit",
    response_model=BudgetRevisionResponse,
)
def submit_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.submit_revision(db, user, project_id, budget_id, revision_id, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}/approve",
    response_model=BudgetRevisionResponse,
)
def approve_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.approve_revision(db, user, project_id, budget_id, revision_id, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}/reject",
    response_model=BudgetRevisionResponse,
)
def reject_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.reject_revision(db, user, project_id, budget_id, revision_id, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/revisions/{revision_id}/cancel",
    response_model=BudgetRevisionResponse,
)
def cancel_budget_revision(
    project_id: UUID,
    budget_id: UUID,
    revision_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetRevisionResponse:
    return svc.cancel_revision(db, user, project_id, budget_id, revision_id, request=request)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/import/preview",
    response_model=BudgetImportPreviewResponse,
)
async def preview_budget_import(
    project_id: UUID,
    budget_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetImportPreviewResponse:
    content = (await file.read()).decode("utf-8-sig")
    return svc.preview_import_csv(db, user, project_id, budget_id, content)


@router.post(
    "/projects/{project_id}/budgets/{budget_id}/import/confirm",
    response_model=BudgetImportResultResponse,
)
def confirm_budget_import(
    project_id: UUID,
    budget_id: UUID,
    payload: BudgetImportConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> BudgetImportResultResponse:
    return svc.confirm_import_csv(db, user, project_id, budget_id, payload, request=request)


@router.get("/projects/{project_id}/budgets/{budget_id}/export")
def export_budget_lines(
    project_id: UUID,
    budget_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("projects", "view")),
) -> Response:
    csv_text = svc.export_lines_csv(db, user, project_id, budget_id)
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="project-{project_id}-budget-{budget_id}.csv"'
        },
    )
