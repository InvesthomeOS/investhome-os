"""Visual Design Studio Sprint 2 business logic."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.models.design_studio import (
    DesignProject,
    DesignStatus,
    DesignVersion,
    FurnitureItem,
    MaterialPackage,
    StylePreset,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.design_studio import (
    ApplyMaterialPackageRequest,
    DesignParameters,
    DesignVersionResponse,
    FurnitureItemCreate,
    FurnitureItemResponse,
    FurnitureItemUpdate,
    MaterialPackageCreate,
    MaterialPackageResponse,
    MaterialPackageUpdate,
    StylePresetCreate,
    StylePresetResponse,
    StylePresetUpdate,
    VersionCompareDiff,
    VersionCompareResponse,
)
from investhome_api.services.design_studio_service import (
    build_design_project_response,
    get_design_project_or_404,
    save_design_version,
)
from investhome_api.services.permission_service import user_has_permission


def _get_style_preset_or_404(preset_id: UUID, db: Session, *, include_archived: bool = False) -> StylePreset:
    preset = db.get(StylePreset, preset_id)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style preset not found")
    if preset.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Style preset not found")
    return preset


def _get_material_package_or_404(package_id: UUID, db: Session, *, include_archived: bool = False) -> MaterialPackage:
    package = db.get(MaterialPackage, package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material package not found")
    if package.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material package not found")
    return package


def _get_furniture_item_or_404(item_id: UUID, db: Session, *, include_archived: bool = False) -> FurnitureItem:
    item = db.get(FurnitureItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture item not found")
    if item.archived_at is not None and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Furniture item not found")
    return item


def _furniture_to_response(item: FurnitureItem) -> FurnitureItemResponse:
    return FurnitureItemResponse(
        id=item.id,
        name=item.name,
        code=item.code,
        room_type=item.room_type,
        furniture_type=item.furniture_type,
        width=item.width,
        depth=item.depth,
        height=item.height,
        measurement_unit=item.measurement_unit,
        default_rotation=item.default_rotation,
        icon_or_preview=item.icon_or_preview,
        metadata=item.metadata_,
        is_system_item=item.is_system_item,
        created_at=item.created_at,
        updated_at=item.updated_at,
        archived_at=item.archived_at,
    )


# --- Style Presets ---


def list_style_presets(
    db: Session,
    *,
    search: str | None = None,
    include_archived: bool = False,
) -> list[StylePresetResponse]:
    query = select(StylePreset).order_by(StylePreset.is_system_preset.desc(), StylePreset.name)
    if not include_archived:
        query = query.where(StylePreset.archived_at.is_(None))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(StylePreset.name.ilike(pattern), StylePreset.code.ilike(pattern)))
    presets = db.scalars(query).all()
    return [StylePresetResponse.model_validate(p) for p in presets]


def create_style_preset(db: Session, payload: StylePresetCreate, actor: User | None) -> StylePreset:
    existing = db.scalar(select(StylePreset).where(StylePreset.code == payload.code))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Style preset code already exists")
    preset = StylePreset(
        name=payload.name,
        code=payload.code,
        description=payload.description,
        color_palette=payload.color_palette,
        material_preferences=payload.material_preferences,
        furniture_preferences=payload.furniture_preferences,
        is_system_preset=False,
        created_by_user_id=actor.id if actor else None,
    )
    db.add(preset)
    db.flush()
    return preset


def update_style_preset(db: Session, preset_id: UUID, payload: StylePresetUpdate) -> StylePreset:
    preset = _get_style_preset_or_404(preset_id, db)
    if preset.is_system_preset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System presets cannot be edited")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(preset, field, value)
    preset.updated_at = datetime.now(UTC)
    db.flush()
    return preset


def archive_style_preset(db: Session, preset_id: UUID) -> StylePreset:
    preset = _get_style_preset_or_404(preset_id, db)
    if preset.is_system_preset:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System presets cannot be archived")
    if preset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Style preset is already archived")
    preset.archived_at = datetime.now(UTC)
    preset.updated_at = datetime.now(UTC)
    db.flush()
    return preset


# --- Material Packages ---


def list_material_packages(
    db: Session,
    *,
    search: str | None = None,
    include_archived: bool = False,
) -> list[MaterialPackageResponse]:
    query = select(MaterialPackage).order_by(MaterialPackage.name)
    if not include_archived:
        query = query.where(MaterialPackage.archived_at.is_(None))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(MaterialPackage.name.ilike(pattern), MaterialPackage.description.ilike(pattern)))
    packages = db.scalars(query).all()
    return [MaterialPackageResponse.model_validate(p) for p in packages]


def create_material_package(db: Session, payload: MaterialPackageCreate, actor: User | None) -> MaterialPackage:
    package = MaterialPackage(
        name=payload.name,
        description=payload.description,
        flooring=payload.flooring,
        wall_finish=payload.wall_finish,
        ceiling_finish=payload.ceiling_finish,
        cabinetry=payload.cabinetry,
        countertop=payload.countertop,
        backsplash=payload.backsplash,
        bathroom_finish=payload.bathroom_finish,
        metal_finish=payload.metal_finish,
        door_finish=payload.door_finish,
        color_palette=payload.color_palette,
        reference_document_ids=payload.reference_document_ids,
        created_by_user_id=actor.id if actor else None,
    )
    db.add(package)
    db.flush()
    return package


def update_material_package(db: Session, package_id: UUID, payload: MaterialPackageUpdate) -> MaterialPackage:
    package = _get_material_package_or_404(package_id, db)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(package, field, value)
    package.updated_at = datetime.now(UTC)
    db.flush()
    return package


def archive_material_package(db: Session, package_id: UUID) -> MaterialPackage:
    package = _get_material_package_or_404(package_id, db)
    if package.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Material package is already archived")
    package.archived_at = datetime.now(UTC)
    package.updated_at = datetime.now(UTC)
    db.flush()
    return package


def apply_material_package(
    db: Session,
    design_project: DesignProject,
    request: ApplyMaterialPackageRequest,
    actor: User | None,
) -> DesignVersion:
    package = _get_material_package_or_404(request.material_package_id, db)
    if design_project.status == DesignStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify approved design — save a new version on a draft project",
        )

    base_params: dict
    if request.design_parameters is not None:
        base_params = request.design_parameters.model_dump(mode="json")
    elif design_project.versions:
        latest = max(design_project.versions, key=lambda v: v.version_number)
        base_params = dict(latest.design_parameters or {})
    else:
        base_params = {"mode": "basic_overlay", "palette": "default", "regions": [], "backgroundColor": "#F5F0E8"}

    base_params["selected_material_package_id"] = str(package.id)
    if package.color_palette:
        base_params["color_overlays"] = [{"source": "material_package", "palette": package.color_palette}]

    return save_design_version(
        db,
        design_project,
        design_parameters=base_params,
        source_geometry_version=design_project.source_geometry_version,
        actor=actor,
    )


# --- Furniture Catalog ---


def list_furniture_items(
    db: Session,
    *,
    search: str | None = None,
    room_type: str | None = None,
    furniture_type: str | None = None,
    include_archived: bool = False,
) -> list[FurnitureItemResponse]:
    query = select(FurnitureItem).order_by(FurnitureItem.name)
    if not include_archived:
        query = query.where(FurnitureItem.archived_at.is_(None))
    if room_type:
        query = query.where(FurnitureItem.room_type == room_type)
    if furniture_type:
        query = query.where(FurnitureItem.furniture_type == furniture_type)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(FurnitureItem.name.ilike(pattern), FurnitureItem.code.ilike(pattern)))
    items = db.scalars(query).all()
    return [_furniture_to_response(item) for item in items]


def create_furniture_item(db: Session, payload: FurnitureItemCreate) -> FurnitureItem:
    existing = db.scalar(select(FurnitureItem).where(FurnitureItem.code == payload.code))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Furniture code already exists")
    item = FurnitureItem(
        name=payload.name,
        code=payload.code,
        room_type=payload.room_type,
        furniture_type=payload.furniture_type,
        width=payload.width,
        depth=payload.depth,
        height=payload.height,
        measurement_unit=payload.measurement_unit,
        default_rotation=payload.default_rotation,
        icon_or_preview=payload.icon_or_preview,
        metadata_=payload.metadata,
        is_system_item=False,
    )
    db.add(item)
    db.flush()
    return item


def update_furniture_item(db: Session, item_id: UUID, payload: FurnitureItemUpdate) -> FurnitureItem:
    item = _get_furniture_item_or_404(item_id, db)
    if item.is_system_item:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System furniture items cannot be edited")
    updates = payload.model_dump(exclude_unset=True)
    if "metadata" in updates:
        item.metadata_ = updates.pop("metadata")
    for field, value in updates.items():
        setattr(item, field, value)
    item.updated_at = datetime.now(UTC)
    db.flush()
    return item


def archive_furniture_item(db: Session, item_id: UUID) -> FurnitureItem:
    item = _get_furniture_item_or_404(item_id, db)
    if item.is_system_item:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="System furniture items cannot be archived")
    if item.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Furniture item is already archived")
    item.archived_at = datetime.now(UTC)
    item.updated_at = datetime.now(UTC)
    db.flush()
    return item


# --- Review Workflow ---


def _check_approve_permission(design_project: DesignProject, actor: User) -> None:
    if design_project.created_by_user_id == actor.id:
        if not user_has_permission(actor, "design", "approve"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot approve own design without approve permission",
            )


def submit_for_review(db: Session, design_project: DesignProject, actor: User) -> DesignProject:
    if not design_project.versions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Save at least one version before submitting")
    if design_project.status == DesignStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Design is already approved")
    design_project.status = DesignStatus.READY_FOR_REVIEW
    design_project.review_submitted_at = datetime.now(UTC)
    design_project.review_comment = None
    design_project.updated_at = datetime.now(UTC)
    db.flush()
    return design_project


def request_revision(
    db: Session,
    design_project: DesignProject,
    actor: User,
    comment: str | None,
) -> DesignProject:
    _check_approve_permission(design_project, actor)
    design_project.status = DesignStatus.REVISION_REQUESTED
    design_project.review_comment = comment
    design_project.reviewed_by_user_id = actor.id
    design_project.reviewed_at = datetime.now(UTC)
    design_project.updated_at = datetime.now(UTC)
    db.flush()
    return design_project


def approve_design(
    db: Session,
    design_project: DesignProject,
    actor: User,
    comment: str | None = None,
) -> DesignProject:
    _check_approve_permission(design_project, actor)
    design_project.status = DesignStatus.APPROVED
    design_project.review_comment = comment
    design_project.reviewed_by_user_id = actor.id
    design_project.reviewed_at = datetime.now(UTC)
    design_project.updated_at = datetime.now(UTC)
    db.flush()
    return design_project


def reject_design(
    db: Session,
    design_project: DesignProject,
    actor: User,
    comment: str | None,
) -> DesignProject:
    _check_approve_permission(design_project, actor)
    design_project.status = DesignStatus.REJECTED
    design_project.review_comment = comment
    design_project.reviewed_by_user_id = actor.id
    design_project.reviewed_at = datetime.now(UTC)
    design_project.updated_at = datetime.now(UTC)
    db.flush()
    return design_project


# --- Version Comparison ---


def _preset_name(db: Session, preset_id: str | None) -> str | None:
    if not preset_id:
        return None
    try:
        preset = db.get(StylePreset, UUID(preset_id))
        return preset.name if preset else None
    except (ValueError, TypeError):
        return None


def _package_name(db: Session, package_id: str | None) -> str | None:
    if not package_id:
        return None
    try:
        package = db.get(MaterialPackage, UUID(package_id))
        return package.name if package else None
    except (ValueError, TypeError):
        return None


def compare_design_versions(
    db: Session,
    design_project_id: UUID,
    version_a_id: UUID,
    version_b_id: UUID,
) -> VersionCompareResponse:
    design_project = get_design_project_or_404(design_project_id, db, include_archived=True)
    version_a = db.get(DesignVersion, version_a_id)
    version_b = db.get(DesignVersion, version_b_id)
    if version_a is None or version_a.design_project_id != design_project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version A not found")
    if version_b is None or version_b.design_project_id != design_project.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version B not found")

    params_a = version_a.design_parameters or {}
    params_b = version_b.design_parameters or {}

    style_a = params_a.get("selected_style_preset_id")
    style_b = params_b.get("selected_style_preset_id")
    mat_a = params_a.get("selected_material_package_id")
    mat_b = params_b.get("selected_material_package_id")

    furniture_a = set(params_a.get("furniture_items") or [])
    furniture_b = set(params_b.get("furniture_items") or [])
    positions_a = params_a.get("furniture_positions") or {}
    positions_b = params_b.get("furniture_positions") or {}

    moved = [
        fid
        for fid in furniture_a & furniture_b
        if positions_a.get(fid) != positions_b.get(fid)
    ]

    regions_a = params_a.get("regions") or params_a.get("color_overlays") or []
    regions_b = params_b.get("regions") or params_b.get("color_overlays") or []
    colors_changed = regions_a != regions_b or params_a.get("backgroundColor") != params_b.get("backgroundColor")

    diff = VersionCompareDiff(
        style_preset_changed=str(style_a) != str(style_b),
        style_preset_a=_preset_name(db, str(style_a) if style_a else None),
        style_preset_b=_preset_name(db, str(style_b) if style_b else None),
        material_package_changed=str(mat_a) != str(mat_b),
        material_package_a=_package_name(db, str(mat_a) if mat_a else None),
        material_package_b=_package_name(db, str(mat_b) if mat_b else None),
        furniture_count_a=len(furniture_a),
        furniture_count_b=len(furniture_b),
        furniture_added=sorted(furniture_b - furniture_a),
        furniture_removed=sorted(furniture_a - furniture_b),
        furniture_moved=moved,
        colors_changed=colors_changed,
        color_diff_summary="Color overlays differ" if colors_changed else None,
    )

    return VersionCompareResponse(
        version_a=DesignVersionResponse.model_validate(version_a),
        version_b=DesignVersionResponse.model_validate(version_b),
        design_status=design_project.status,
        diff=diff,
    )


def merge_design_parameters(existing: dict | None, incoming: DesignParameters) -> dict:
    """Merge Sprint 2 parameters without dropping Sprint 1 fields."""
    base = dict(existing or {})
    incoming_dict = incoming.model_dump(exclude_unset=True, mode="json")
    base.update(incoming_dict)
    return base


def _placement_map(params: dict | None) -> dict[str, dict[str, Any]]:
    """Normalize furniture placements to instance_id -> placement dict."""
    if not params:
        return {}
    if params.get("furniture_placements"):
        return {
            str(p.get("instance_id", p.get("id", idx))): p
            for idx, p in enumerate(params["furniture_placements"])
        }
    result: dict[str, dict[str, Any]] = {}
    for idx, catalog_id in enumerate(params.get("furniture_items") or []):
        instance_id = f"{catalog_id}-{idx}"
        pos = (params.get("furniture_positions") or {}).get(catalog_id, {"x": 0, "y": 0})
        result[instance_id] = {
            "instance_id": instance_id,
            "catalog_id": catalog_id,
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "rotation": (params.get("furniture_rotations") or {}).get(catalog_id, 0),
        }
    return result


def log_design_parameter_changes(
    db: Session,
    *,
    design_project: DesignProject,
    previous_params: dict | None,
    new_params: dict,
    actor: User | None,
    request,
) -> None:
    """Log Sprint 2A activity events when saving a version (not on every drag)."""
    from investhome_api.services.design_studio import activity as design_activity

    title = design_project.title
    project_id = design_project.id

    old_style = (previous_params or {}).get("selected_style_preset_id")
    new_style = new_params.get("selected_style_preset_id")
    if new_style and str(new_style) != str(old_style or ""):
        preset = db.get(StylePreset, UUID(str(new_style))) if new_style else None
        design_activity.record_style_changed(
            db,
            design_project_id=project_id,
            title=title,
            preset_name=preset.name if preset else str(new_style),
            actor=actor,
            request=request,
        )

    old_material = (previous_params or {}).get("selected_material_package_id")
    new_material = new_params.get("selected_material_package_id")
    if new_material and str(new_material) != str(old_material or ""):
        package = db.get(MaterialPackage, UUID(str(new_material))) if new_material else None
        design_activity.record_material_changed(
            db,
            design_project_id=project_id,
            title=title,
            package_name=package.name if package else str(new_material),
            actor=actor,
            request=request,
        )

    old_placements = _placement_map(previous_params)
    new_placements = _placement_map(new_params)
    old_ids = set(old_placements)
    new_ids = set(new_placements)

    for instance_id in new_ids - old_ids:
        catalog_id = new_placements[instance_id].get("catalog_id", instance_id)
        item = db.get(FurnitureItem, UUID(str(catalog_id))) if _is_uuid(str(catalog_id)) else None
        design_activity.record_furniture_added(
            db,
            design_project_id=project_id,
            title=title,
            item_name=item.name if item else str(catalog_id),
            actor=actor,
            request=request,
        )

    for instance_id in old_ids - new_ids:
        catalog_id = old_placements[instance_id].get("catalog_id", instance_id)
        item = db.get(FurnitureItem, UUID(str(catalog_id))) if _is_uuid(str(catalog_id)) else None
        design_activity.record_furniture_removed(
            db,
            design_project_id=project_id,
            title=title,
            item_name=item.name if item else str(catalog_id),
            actor=actor,
            request=request,
        )

    for instance_id in old_ids & new_ids:
        old_p = old_placements[instance_id]
        new_p = new_placements[instance_id]
        moved = (
            old_p.get("x") != new_p.get("x")
            or old_p.get("y") != new_p.get("y")
            or old_p.get("rotation") != new_p.get("rotation")
        )
        if moved:
            catalog_id = new_p.get("catalog_id", instance_id)
            item = db.get(FurnitureItem, UUID(str(catalog_id))) if _is_uuid(str(catalog_id)) else None
            design_activity.record_furniture_moved(
                db,
                design_project_id=project_id,
                title=title,
                item_name=item.name if item else str(catalog_id),
                actor=actor,
                request=request,
            )


def _is_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except ValueError:
        return False


def build_design_version_response(version: DesignVersion, db: Session) -> DesignVersionResponse:
    created_by_name = None
    if version.created_by_user_id:
        user = db.get(User, version.created_by_user_id)
        created_by_name = user.full_name if user else None
    return DesignVersionResponse(
        id=version.id,
        design_project_id=version.design_project_id,
        version_number=version.version_number,
        source_geometry_version=version.source_geometry_version,
        design_parameters=version.design_parameters,
        output_location=version.output_location,
        thumbnail_location=version.thumbnail_location,
        created_by_user_id=version.created_by_user_id,
        created_by_name=created_by_name,
        created_at=version.created_at,
    )
