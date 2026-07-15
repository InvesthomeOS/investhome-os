"""Visual Design Studio API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.design_studio import DesignStatus, DesignType
from investhome_api.models.document import Document
from investhome_api.models.user_auth import User
from investhome_api.schemas.design_studio import (
    ApplyMaterialPackageRequest,
    CompatibleSourceDocumentsResponse,
    DesignProjectCreate,
    DesignProjectListResponse,
    DesignProjectResponse,
    DesignProjectUpdate,
    DesignSourceRegionsResponse,
    DesignStatusAction,
    DesignVersionCreate,
    DesignVersionListResponse,
    DesignVersionResponse,
    FurnitureItemCreate,
    FurnitureItemListResponse,
    FurnitureItemResponse,
    FurnitureItemUpdate,
    MaterialPackageCreate,
    MaterialPackageListResponse,
    MaterialPackageResponse,
    MaterialPackageUpdate,
    StylePresetCreate,
    StylePresetListResponse,
    StylePresetResponse,
    StylePresetUpdate,
    VersionCompareRequest,
    VersionCompareResponse,
)
from investhome_api.services.design_studio import activity as design_activity
from investhome_api.services.design_studio_service import (
    build_design_project_response,
    create_design_project,
    get_design_project_or_404,
    get_source_regions,
    list_compatible_source_documents,
    list_design_projects,
    save_design_version,
)
from investhome_api.services.design_studio_sprint2_service import (
    apply_material_package,
    approve_design,
    archive_furniture_item,
    archive_material_package,
    archive_style_preset,
    build_design_version_response,
    compare_design_versions,
    create_furniture_item,
    create_material_package,
    create_style_preset,
    list_furniture_items,
    list_material_packages,
    list_style_presets,
    log_design_parameter_changes,
    merge_design_parameters,
    reject_design,
    request_revision,
    submit_for_review,
    update_furniture_item,
    update_material_package,
    update_style_preset,
)
from investhome_api.services.design_studio_sprint2_service import (
    _furniture_to_response as furniture_to_response,
)
from investhome_api.models.design_studio import MaterialPackage

router = APIRouter(prefix="/design", tags=["design"])

_design_view = Depends(require_permission("design", "view"))
_design_create = Depends(require_permission("design", "create"))
_design_update = Depends(require_permission("design", "update"))
_design_save_version = Depends(require_permission("design", "save_version"))
_design_approve = Depends(require_permission("design", "approve"))
_design_archive = Depends(require_permission("design", "archive"))
_design_manage_styles = Depends(require_permission("design", "manage_styles"))
_design_manage_materials = Depends(require_permission("design", "manage_materials"))
_design_manage_furniture = Depends(require_permission("design", "manage_furniture"))
_design_submit_review = Depends(require_permission("design", "submit_review"))


# --- Design Projects (Sprint 1 + extensions) ---


@router.get("/projects", response_model=DesignProjectListResponse)
def list_projects(
    search: str | None = Query(default=None, max_length=255),
    project_id: UUID | None = Query(default=None),
    design_type: DesignType | None = Query(default=None),
    status_filter: DesignStatus | None = Query(default=None, alias="status"),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> DesignProjectListResponse:
    items = list_design_projects(
        db,
        search=search,
        project_id=project_id,
        design_type=design_type,
        status_filter=status_filter,
        include_archived=include_archived,
    )
    return DesignProjectListResponse(items=items, total=len(items))


@router.get("/projects/{design_project_id}", response_model=DesignProjectResponse)
def get_project(
    design_project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db, include_archived=True)
    return build_design_project_response(design_project, db)


@router.post("/projects", response_model=DesignProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: DesignProjectCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_create,
) -> DesignProjectResponse:
    design_project = create_design_project(
        db,
        project_id=payload.project_id,
        document_id=payload.document_id,
        document_version_id=payload.document_version_id,
        drawing_analysis_id=payload.drawing_analysis_id,
        title=payload.title,
        description=payload.description,
        design_type=payload.design_type,
        actor=actor,
    )
    document = db.get(Document, payload.document_id)
    design_activity.record_design_project_created(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        actor=actor,
        request=request,
    )
    if document is not None:
        design_activity.record_source_plan_selected(
            db,
            design_project_id=design_project.id,
            title=design_project.title,
            document_title=document.title,
            actor=actor,
            request=request,
        )
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.patch("/projects/{design_project_id}", response_model=DesignProjectResponse)
def update_project(
    design_project_id: UUID,
    payload: DesignProjectUpdate,
    db: Session = Depends(get_db),
    actor: User = _design_update,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    for field, value in updates.items():
        setattr(design_project, field, value)

    design_project.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.post("/projects/{design_project_id}/archive", response_model=DesignProjectResponse)
def archive_project(
    design_project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_archive,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db)

    if design_project.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Design project is already archived")

    design_project.archived_at = datetime.now(UTC)
    design_project.status = DesignStatus.ARCHIVED
    design_project.updated_at = datetime.now(UTC)
    design_activity.record_design_archived(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.post("/projects/{design_project_id}/submit-review", response_model=DesignProjectResponse)
def submit_review(
    design_project_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_submit_review,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    submit_for_review(db, design_project, actor)
    design_activity.record_submitted_for_review(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.post("/projects/{design_project_id}/request-revision", response_model=DesignProjectResponse)
def request_revision_endpoint(
    design_project_id: UUID,
    payload: DesignStatusAction,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_approve,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    request_revision(db, design_project, actor, payload.comment)
    design_activity.record_revision_requested(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        actor=actor,
        request=request,
        comment=payload.comment,
    )
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.post("/projects/{design_project_id}/approve", response_model=DesignProjectResponse)
def approve_project(
    design_project_id: UUID,
    request: Request,
    payload: DesignStatusAction = DesignStatusAction(),
    db: Session = Depends(get_db),
    actor: User = _design_approve,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    approve_design(db, design_project, actor, payload.comment)
    design_activity.record_design_approved(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.post("/projects/{design_project_id}/reject", response_model=DesignProjectResponse)
def reject_project(
    design_project_id: UUID,
    payload: DesignStatusAction,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_approve,
) -> DesignProjectResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    reject_design(db, design_project, actor, payload.comment)
    design_activity.record_design_rejected(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        actor=actor,
        request=request,
        comment=payload.comment,
    )
    db.commit()
    db.refresh(design_project)
    return build_design_project_response(design_project, db)


@router.get("/projects/{design_project_id}/versions", response_model=DesignVersionListResponse)
def list_versions(
    design_project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> DesignVersionListResponse:
    design_project = get_design_project_or_404(design_project_id, db, include_archived=True)
    versions = sorted(design_project.versions, key=lambda v: v.version_number, reverse=True)
    return DesignVersionListResponse(
        items=[build_design_version_response(v, db) for v in versions],
        total=len(versions),
    )


@router.post(
    "/projects/{design_project_id}/versions",
    response_model=DesignVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    design_project_id: UUID,
    payload: DesignVersionCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_save_version,
) -> DesignVersionResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    if design_project.status == DesignStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Approved versions are historical — create a new draft project to continue editing",
        )

    latest_params = None
    if design_project.versions:
        latest = max(design_project.versions, key=lambda v: v.version_number)
        latest_params = latest.design_parameters

    params = merge_design_parameters(latest_params, payload.design_parameters)

    log_design_parameter_changes(
        db,
        design_project=design_project,
        previous_params=latest_params,
        new_params=params,
        actor=actor,
        request=request,
    )

    if params.get("furniture_items") or params.get("furniture_placements"):
        item_count = len(params.get("furniture_placements") or params.get("furniture_items") or [])
        design_activity.record_furniture_layout_updated(
            db,
            design_project_id=design_project.id,
            title=design_project.title,
            item_count=item_count,
            actor=actor,
            request=request,
        )
    elif not (params.get("selected_style_preset_id") or params.get("selected_material_package_id")):
        design_activity.record_color_overlay_updated(
            db,
            design_project_id=design_project.id,
            title=design_project.title,
            mode=params.get("mode", "basic_overlay"),
            actor=actor,
            request=request,
        )

    version = save_design_version(
        db,
        design_project,
        design_parameters=params,
        source_geometry_version=payload.source_geometry_version,
        actor=actor,
    )
    design_activity.record_version_saved(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        version_number=version.version_number,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(version)
    return build_design_version_response(version, db)


@router.post(
    "/projects/{design_project_id}/compare-versions",
    response_model=VersionCompareResponse,
)
def compare_versions(
    design_project_id: UUID,
    payload: VersionCompareRequest,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> VersionCompareResponse:
    return compare_design_versions(db, design_project_id, payload.version_a_id, payload.version_b_id)


@router.post(
    "/projects/{design_project_id}/apply-material-package",
    response_model=DesignVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_material_package_endpoint(
    design_project_id: UUID,
    payload: ApplyMaterialPackageRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_save_version,
) -> DesignVersionResponse:
    design_project = get_design_project_or_404(design_project_id, db)
    package = db.get(MaterialPackage, payload.material_package_id)
    version = apply_material_package(db, design_project, payload, actor)
    design_activity.record_material_package_applied(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        package_name=package.name if package else "Unknown",
        actor=actor,
        request=request,
    )
    design_activity.record_version_saved(
        db,
        design_project_id=design_project.id,
        title=design_project.title,
        version_number=version.version_number,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(version)
    return DesignVersionResponse.model_validate(version)


@router.get("/projects/{design_project_id}/source-regions", response_model=DesignSourceRegionsResponse)
def get_project_source_regions(
    design_project_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> DesignSourceRegionsResponse:
    design_project = get_design_project_or_404(design_project_id, db, include_archived=True)
    return get_source_regions(db, design_project)


@router.get("/compatible-documents", response_model=CompatibleSourceDocumentsResponse)
def list_compatible_documents(
    project_id: UUID = Query(...),
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> CompatibleSourceDocumentsResponse:
    items = list_compatible_source_documents(db, project_id)
    return CompatibleSourceDocumentsResponse(items=items, total=len(items))


# --- Style Presets ---


@router.get("/style-presets", response_model=StylePresetListResponse)
def list_style_presets_endpoint(
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> StylePresetListResponse:
    items = list_style_presets(db, search=search, include_archived=include_archived)
    return StylePresetListResponse(items=items, total=len(items))


@router.get("/style-presets/{preset_id}", response_model=StylePresetResponse)
def get_style_preset(
    preset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> StylePresetResponse:
    from investhome_api.services.design_studio_sprint2_service import _get_style_preset_or_404

    preset = _get_style_preset_or_404(preset_id, db, include_archived=True)
    return StylePresetResponse.model_validate(preset)


@router.post("/style-presets", response_model=StylePresetResponse, status_code=status.HTTP_201_CREATED)
def create_style_preset_endpoint(
    payload: StylePresetCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_manage_styles,
) -> StylePresetResponse:
    preset = create_style_preset(db, payload, actor)
    design_activity.record_style_preset_created(
        db,
        preset_id=preset.id,
        name=preset.name,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(preset)
    return StylePresetResponse.model_validate(preset)


@router.patch("/style-presets/{preset_id}", response_model=StylePresetResponse)
def update_style_preset_endpoint(
    preset_id: UUID,
    payload: StylePresetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_manage_styles,
) -> StylePresetResponse:
    preset = update_style_preset(db, preset_id, payload)
    design_activity.record_style_preset_updated(
        db,
        preset_id=preset.id,
        name=preset.name,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(preset)
    return StylePresetResponse.model_validate(preset)


@router.post("/style-presets/{preset_id}/archive", response_model=StylePresetResponse)
def archive_style_preset_endpoint(
    preset_id: UUID,
    db: Session = Depends(get_db),
    actor: User = _design_manage_styles,
) -> StylePresetResponse:
    preset = archive_style_preset(db, preset_id)
    db.commit()
    db.refresh(preset)
    return StylePresetResponse.model_validate(preset)


# --- Material Packages ---


@router.get("/material-packages", response_model=MaterialPackageListResponse)
def list_material_packages_endpoint(
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> MaterialPackageListResponse:
    items = list_material_packages(db, search=search, include_archived=include_archived)
    return MaterialPackageListResponse(items=items, total=len(items))


@router.get("/material-packages/{package_id}", response_model=MaterialPackageResponse)
def get_material_package(
    package_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> MaterialPackageResponse:
    from investhome_api.services.design_studio_sprint2_service import _get_material_package_or_404

    package = _get_material_package_or_404(package_id, db, include_archived=True)
    return MaterialPackageResponse.model_validate(package)


@router.post("/material-packages", response_model=MaterialPackageResponse, status_code=status.HTTP_201_CREATED)
def create_material_package_endpoint(
    payload: MaterialPackageCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = _design_manage_materials,
) -> MaterialPackageResponse:
    package = create_material_package(db, payload, actor)
    design_activity.record_material_package_created(
        db,
        package_id=package.id,
        name=package.name,
        actor=actor,
        request=request,
    )
    db.commit()
    db.refresh(package)
    return MaterialPackageResponse.model_validate(package)


@router.patch("/material-packages/{package_id}", response_model=MaterialPackageResponse)
def update_material_package_endpoint(
    package_id: UUID,
    payload: MaterialPackageUpdate,
    db: Session = Depends(get_db),
    actor: User = _design_manage_materials,
) -> MaterialPackageResponse:
    package = update_material_package(db, package_id, payload)
    db.commit()
    db.refresh(package)
    return MaterialPackageResponse.model_validate(package)


@router.post("/material-packages/{package_id}/archive", response_model=MaterialPackageResponse)
def archive_material_package_endpoint(
    package_id: UUID,
    db: Session = Depends(get_db),
    actor: User = _design_manage_materials,
) -> MaterialPackageResponse:
    package = archive_material_package(db, package_id)
    db.commit()
    db.refresh(package)
    return MaterialPackageResponse.model_validate(package)


# --- Furniture Catalog ---


@router.get("/furniture", response_model=FurnitureItemListResponse)
def list_furniture_endpoint(
    search: str | None = Query(default=None, max_length=255),
    room_type: str | None = Query(default=None),
    furniture_type: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> FurnitureItemListResponse:
    items = list_furniture_items(
        db,
        search=search,
        room_type=room_type,
        furniture_type=furniture_type,
        include_archived=include_archived,
    )
    return FurnitureItemListResponse(items=items, total=len(items))


@router.get("/furniture/{item_id}", response_model=FurnitureItemResponse)
def get_furniture_item(
    item_id: UUID,
    db: Session = Depends(get_db),
    _user: User = _design_view,
) -> FurnitureItemResponse:
    from investhome_api.services.design_studio_sprint2_service import _get_furniture_item_or_404

    item = _get_furniture_item_or_404(item_id, db, include_archived=True)
    return furniture_to_response(item)


@router.post("/furniture", response_model=FurnitureItemResponse, status_code=status.HTTP_201_CREATED)
def create_furniture_endpoint(
    payload: FurnitureItemCreate,
    db: Session = Depends(get_db),
    actor: User = _design_manage_furniture,
) -> FurnitureItemResponse:
    item = create_furniture_item(db, payload)
    db.commit()
    db.refresh(item)
    return furniture_to_response(item)


@router.patch("/furniture/{item_id}", response_model=FurnitureItemResponse)
def update_furniture_endpoint(
    item_id: UUID,
    payload: FurnitureItemUpdate,
    db: Session = Depends(get_db),
    actor: User = _design_manage_furniture,
) -> FurnitureItemResponse:
    item = update_furniture_item(db, item_id, payload)
    db.commit()
    db.refresh(item)
    return furniture_to_response(item)


@router.post("/furniture/{item_id}/archive", response_model=FurnitureItemResponse)
def archive_furniture_endpoint(
    item_id: UUID,
    db: Session = Depends(get_db),
    actor: User = _design_manage_furniture,
) -> FurnitureItemResponse:
    item = archive_furniture_item(db, item_id)
    db.commit()
    db.refresh(item)
    return furniture_to_response(item)
