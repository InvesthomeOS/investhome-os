"""Inventory API routes — buildings, floors, inventory assets."""

from datetime import UTC, datetime
from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.inventory import (
    AvailabilityStatus,
    Building,
    ClosingStatus,
    ConstructionStatus,
    Floor,
    InventoryAsset,
    InventoryAssetType,
    InventorySalesStatus,
    LeasingStatus,
    ReservationStatus,
    StatusCategory,
    StructureStatus,
    UsageType,
)
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.inventory import (
    BuildingCreate,
    BuildingListResponse,
    BuildingResponse,
    BuildingUpdate,
    FloorCreate,
    FloorListResponse,
    FloorResponse,
    FloorUpdate,
    InventoryAssetCreate,
    InventoryAssetListResponse,
    InventoryAssetResponse,
    InventoryAssetStatusHistoryResponse,
    InventoryAssetStatusUpdate,
    InventoryAssetUpdate,
)
from investhome_api.services.activity_recorder import (
    activity_context_from_request,
    log_entity_archived,
    log_entity_created,
    log_entity_restored,
    log_entity_updated,
)
from investhome_api.services.activity_service import log_activity, snapshot_entity
from investhome_api.services.inventory.status_service import (
    StatusTransitionError,
    list_status_history,
    update_asset_status,
)
from investhome_api.services.inventory.system_code_service import generate_system_code
from investhome_api.services.inventory.validation_service import (
    InventoryValidationError,
    validate_asset_create,
    validate_asset_update,
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

BUILDING_ACTIVITY_FIELDS = ["name", "code", "building_type", "status", "address", "total_floors"]
FLOOR_ACTIVITY_FIELDS = ["floor_number", "display_name", "level_code", "status", "sort_order"]
ASSET_ACTIVITY_FIELDS = [
    "display_id",
    "system_code",
    "legal_identifier",
    "asset_type",
    "usage_type",
    "building_id",
    "floor_id",
    "availability_status",
    "sales_status",
    "construction_status",
]


def _validation_http_error(exc: InventoryValidationError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.error_key)


def _get_building_or_404(building_id: UUID, db: Session, *, include_archived: bool = False) -> Building:
    building = db.get(Building, building_id)
    if building is None or (building.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    return building


def _get_floor_or_404(floor_id: UUID, db: Session, *, include_archived: bool = False) -> Floor:
    floor = db.get(Floor, floor_id)
    if floor is None or (floor.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor not found")
    return floor


def _get_asset_or_404(asset_id: UUID, db: Session, *, include_archived: bool = False) -> InventoryAsset:
    asset = db.get(InventoryAsset, asset_id)
    if asset is None or (asset.archived_at is not None and not include_archived):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory asset not found")
    return asset


# --- Buildings ---


@router.get("/buildings", response_model=BuildingListResponse)
def list_buildings(
    project_id: UUID | None = None,
    building_type: str | None = None,
    status_filter: StructureStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> BuildingListResponse:
    sort_columns = {
        "name": Building.name,
        "code": Building.code,
        "updated_at": Building.updated_at,
        "created_at": Building.created_at,
    }
    sort_column = sort_columns.get(sort_by, Building.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(Building)
    if not include_archived:
        query = query.where(Building.archived_at.is_(None))
    if project_id is not None:
        query = query.where(Building.project_id == project_id)
    if building_type is not None:
        query = query.where(Building.building_type == building_type)
    if status_filter is not None:
        query = query.where(Building.status == status_filter)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Building.name.ilike(pattern),
                Building.code.ilike(pattern),
                Building.address.ilike(pattern),
                Building.description.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    buildings = db.scalars(
        query.order_by(order_fn(sort_column)).offset((page - 1) * page_size).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0
    return BuildingListResponse(
        items=[BuildingResponse.model_validate(b) for b in buildings],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/buildings/{building_id}", response_model=BuildingResponse)
def get_building(
    building_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> BuildingResponse:
    return BuildingResponse.model_validate(_get_building_or_404(building_id, db))


@router.post("/buildings", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
def create_building(
    payload: BuildingCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "create")),
) -> BuildingResponse:
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    building = Building(**payload.model_dump())
    db.add(building)
    try:
        db.flush()
        log_entity_created(
            db,
            entity_type=ActivityEntityType.BUILDING,
            entity_id=building.id,
            description_key="activity.inventory.building.created",
            actor=actor,
            metadata={"name": building.name, "code": building.code},
            request=request,
            is_demo=building.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inventory.errors.building_code_duplicate",
        ) from exc
    db.refresh(building)
    return BuildingResponse.model_validate(building)


@router.patch("/buildings/{building_id}", response_model=BuildingResponse)
def update_building(
    building_id: UUID,
    payload: BuildingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "update")),
) -> BuildingResponse:
    building = _get_building_or_404(building_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    before = snapshot_entity(building, BUILDING_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(building, field, value)
    building.updated_at = datetime.now(UTC)

    try:
        db.flush()
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.BUILDING,
            entity_id=building.id,
            description_key="activity.inventory.building.updated",
            actor=actor,
            before=before,
            after=snapshot_entity(building, BUILDING_ACTIVITY_FIELDS),
            metadata={"name": building.name, "code": building.code},
            request=request,
            is_demo=building.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inventory.errors.building_code_duplicate",
        ) from exc
    db.refresh(building)
    return BuildingResponse.model_validate(building)


@router.post("/buildings/{building_id}/archive", response_model=BuildingResponse)
def archive_building(
    building_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "archive")),
) -> BuildingResponse:
    building = _get_building_or_404(building_id, db)
    if building.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Building is already archived")
    building.archived_at = datetime.now(UTC)
    building.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.BUILDING,
        entity_id=building.id,
        description_key="activity.inventory.building.archived",
        actor=actor,
        metadata={"name": building.name, "code": building.code},
        request=request,
        is_demo=building.is_demo,
    )
    db.commit()
    db.refresh(building)
    return BuildingResponse.model_validate(building)


@router.post("/buildings/{building_id}/restore", response_model=BuildingResponse)
def restore_building(
    building_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "restore")),
) -> BuildingResponse:
    building = _get_building_or_404(building_id, db, include_archived=True)
    if building.archived_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Building is not archived")
    building.archived_at = None
    building.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.BUILDING,
        entity_id=building.id,
        description_key="activity.inventory.building.restored",
        actor=actor,
        metadata={"name": building.name, "code": building.code},
        request=request,
        is_demo=building.is_demo,
    )
    db.commit()
    db.refresh(building)
    return BuildingResponse.model_validate(building)


# --- Floors ---


@router.get("/floors", response_model=FloorListResponse)
def list_floors(
    building_id: UUID | None = None,
    project_id: UUID | None = None,
    status_filter: StructureStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="sort_order"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> FloorListResponse:
    sort_columns = {
        "floor_number": Floor.floor_number,
        "sort_order": Floor.sort_order,
        "updated_at": Floor.updated_at,
    }
    sort_column = sort_columns.get(sort_by, Floor.sort_order)
    order_fn = asc if sort_order == "asc" else desc

    query = select(Floor)
    if not include_archived:
        query = query.where(Floor.archived_at.is_(None))
    if building_id is not None:
        query = query.where(Floor.building_id == building_id)
    if project_id is not None:
        query = query.join(Building, Floor.building_id == Building.id).where(Building.project_id == project_id)
    if status_filter is not None:
        query = query.where(Floor.status == status_filter)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Floor.display_name.ilike(pattern),
                Floor.level_code.ilike(pattern),
                Floor.description.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    floors = db.scalars(
        query.order_by(order_fn(sort_column)).offset((page - 1) * page_size).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0
    return FloorListResponse(
        items=[FloorResponse.model_validate(f) for f in floors],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/floors/{floor_id}", response_model=FloorResponse)
def get_floor(
    floor_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> FloorResponse:
    return FloorResponse.model_validate(_get_floor_or_404(floor_id, db))


@router.post("/floors", response_model=FloorResponse, status_code=status.HTTP_201_CREATED)
def create_floor(
    payload: FloorCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "create")),
) -> FloorResponse:
    if db.get(Building, payload.building_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")

    floor = Floor(**payload.model_dump())
    db.add(floor)
    try:
        db.flush()
        log_entity_created(
            db,
            entity_type=ActivityEntityType.FLOOR,
            entity_id=floor.id,
            description_key="activity.inventory.floor.created",
            actor=actor,
            metadata={"floor_number": floor.floor_number, "level_code": floor.level_code},
            request=request,
            is_demo=floor.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inventory.errors.floor_identifier_duplicate",
        ) from exc
    db.refresh(floor)
    return FloorResponse.model_validate(floor)


@router.patch("/floors/{floor_id}", response_model=FloorResponse)
def update_floor(
    floor_id: UUID,
    payload: FloorUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "update")),
) -> FloorResponse:
    floor = _get_floor_or_404(floor_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    before = snapshot_entity(floor, FLOOR_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(floor, field, value)
    floor.updated_at = datetime.now(UTC)

    try:
        db.flush()
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.FLOOR,
            entity_id=floor.id,
            description_key="activity.inventory.floor.updated",
            actor=actor,
            before=before,
            after=snapshot_entity(floor, FLOOR_ACTIVITY_FIELDS),
            metadata={"floor_number": floor.floor_number},
            request=request,
            is_demo=floor.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inventory.errors.floor_identifier_duplicate",
        ) from exc
    db.refresh(floor)
    return FloorResponse.model_validate(floor)


@router.post("/floors/{floor_id}/archive", response_model=FloorResponse)
def archive_floor(
    floor_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "archive")),
) -> FloorResponse:
    floor = _get_floor_or_404(floor_id, db)
    if floor.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Floor is already archived")
    floor.archived_at = datetime.now(UTC)
    floor.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.FLOOR,
        entity_id=floor.id,
        description_key="activity.inventory.floor.archived",
        actor=actor,
        metadata={"floor_number": floor.floor_number},
        request=request,
        is_demo=floor.is_demo,
    )
    db.commit()
    db.refresh(floor)
    return FloorResponse.model_validate(floor)


@router.post("/floors/{floor_id}/restore", response_model=FloorResponse)
def restore_floor(
    floor_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "restore")),
) -> FloorResponse:
    floor = _get_floor_or_404(floor_id, db, include_archived=True)
    if floor.archived_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Floor is not archived")
    floor.archived_at = None
    floor.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.FLOOR,
        entity_id=floor.id,
        description_key="activity.inventory.floor.restored",
        actor=actor,
        metadata={"floor_number": floor.floor_number},
        request=request,
        is_demo=floor.is_demo,
    )
    db.commit()
    db.refresh(floor)
    return FloorResponse.model_validate(floor)


# --- Inventory Assets ---


def _apply_asset_filters(
    query,
    *,
    project_id: UUID | None,
    building_id: UUID | None,
    floor_id: UUID | None,
    asset_type: InventoryAssetType | None,
    usage_type: UsageType | None,
    availability_status: AvailabilityStatus | None,
    reservation_status: ReservationStatus | None,
    sales_status: InventorySalesStatus | None,
    construction_status: ConstructionStatus | None,
    closing_status: ClosingStatus | None,
    leasing_status: LeasingStatus | None,
    search: str | None,
    include_archived: bool,
):
    if not include_archived:
        query = query.where(InventoryAsset.archived_at.is_(None))
    if project_id is not None:
        query = query.where(InventoryAsset.project_id == project_id)
    if building_id is not None:
        query = query.where(InventoryAsset.building_id == building_id)
    if floor_id is not None:
        query = query.where(InventoryAsset.floor_id == floor_id)
    if asset_type is not None:
        query = query.where(InventoryAsset.asset_type == asset_type)
    if usage_type is not None:
        query = query.where(InventoryAsset.usage_type == usage_type)
    if availability_status is not None:
        query = query.where(InventoryAsset.availability_status == availability_status)
    if reservation_status is not None:
        query = query.where(InventoryAsset.reservation_status == reservation_status)
    if sales_status is not None:
        query = query.where(InventoryAsset.sales_status == sales_status)
    if construction_status is not None:
        query = query.where(InventoryAsset.construction_status == construction_status)
    if closing_status is not None:
        query = query.where(InventoryAsset.closing_status == closing_status)
    if leasing_status is not None:
        query = query.where(InventoryAsset.leasing_status == leasing_status)
    if search:
        pattern = f"%{search.strip()}%"
        project_subq = select(Project.id).where(
            or_(Project.project_code.ilike(pattern), Project.project_name.ilike(pattern))
        )
        building_subq = select(Building.id).where(Building.code.ilike(pattern))
        floor_subq = select(Floor.id).where(
            or_(Floor.display_name.ilike(pattern), Floor.level_code.ilike(pattern))
        )
        query = query.where(
            or_(
                InventoryAsset.display_id.ilike(pattern),
                InventoryAsset.system_code.ilike(pattern),
                InventoryAsset.legal_identifier.ilike(pattern),
                InventoryAsset.description.ilike(pattern),
                InventoryAsset.project_id.in_(project_subq),
                InventoryAsset.building_id.in_(building_subq),
                InventoryAsset.floor_id.in_(floor_subq),
            )
        )
    return query


@router.get("/assets", response_model=InventoryAssetListResponse)
def list_assets(
    project_id: UUID | None = None,
    building_id: UUID | None = None,
    floor_id: UUID | None = None,
    asset_type: InventoryAssetType | None = None,
    usage_type: UsageType | None = None,
    availability_status: AvailabilityStatus | None = None,
    reservation_status: ReservationStatus | None = None,
    sales_status: InventorySalesStatus | None = None,
    construction_status: ConstructionStatus | None = None,
    closing_status: ClosingStatus | None = None,
    leasing_status: LeasingStatus | None = None,
    search: str | None = Query(default=None, max_length=255),
    include_archived: bool = Query(default=False),
    sort_by: str = Query(default="updated_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> InventoryAssetListResponse:
    sort_columns = {
        "display_id": InventoryAsset.display_id,
        "system_code": InventoryAsset.system_code,
        "updated_at": InventoryAsset.updated_at,
        "created_at": InventoryAsset.created_at,
    }
    sort_column = sort_columns.get(sort_by, InventoryAsset.updated_at)
    order_fn = asc if sort_order == "asc" else desc

    query = select(InventoryAsset)
    query = _apply_asset_filters(
        query,
        project_id=project_id,
        building_id=building_id,
        floor_id=floor_id,
        asset_type=asset_type,
        usage_type=usage_type,
        availability_status=availability_status,
        reservation_status=reservation_status,
        sales_status=sales_status,
        construction_status=construction_status,
        closing_status=closing_status,
        leasing_status=leasing_status,
        search=search,
        include_archived=include_archived,
    )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    assets = db.scalars(
        query.order_by(order_fn(sort_column)).offset((page - 1) * page_size).limit(page_size)
    ).all()
    pages = ceil(total / page_size) if total else 0
    return InventoryAssetListResponse(
        items=[InventoryAssetResponse.model_validate(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/assets/{asset_id}", response_model=InventoryAssetResponse)
def get_asset(
    asset_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> InventoryAssetResponse:
    return InventoryAssetResponse.model_validate(_get_asset_or_404(asset_id, db))


@router.post("/assets", response_model=InventoryAssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: InventoryAssetCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "create")),
) -> InventoryAssetResponse:
    if db.get(Project, payload.project_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    try:
        validate_asset_create(
            db,
            project_id=payload.project_id,
            asset_type=payload.asset_type,
            usage_type=payload.usage_type,
            building_id=payload.building_id,
            floor_id=payload.floor_id,
        )
    except InventoryValidationError as exc:
        raise _validation_http_error(exc) from exc

    system_code = generate_system_code(
        db,
        project_id=payload.project_id,
        building_id=payload.building_id,
        floor_id=payload.floor_id,
        display_id=payload.display_id,
    )

    asset = InventoryAsset(**payload.model_dump(), system_code=system_code)
    db.add(asset)
    try:
        db.flush()
        log_entity_created(
            db,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=asset.id,
            description_key="activity.inventory.asset.created",
            actor=actor,
            metadata={"display_id": asset.display_id, "system_code": asset.system_code},
            request=request,
            is_demo=asset.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inventory.errors.display_id_duplicate",
        ) from exc
    db.refresh(asset)
    return InventoryAssetResponse.model_validate(asset)


@router.patch("/assets/{asset_id}", response_model=InventoryAssetResponse)
def update_asset(
    asset_id: UUID,
    payload: InventoryAssetUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "update")),
) -> InventoryAssetResponse:
    asset = _get_asset_or_404(asset_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")

    if "system_code" in updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="inventory.errors.system_code_immutable",
        )

    building_id = updates.get("building_id", asset.building_id)
    floor_id = updates.get("floor_id", asset.floor_id)
    asset_type = updates.get("asset_type", asset.asset_type)
    usage_type = updates.get("usage_type", asset.usage_type)

    try:
        validate_asset_update(
            db,
            asset,
            building_id=building_id,
            floor_id=floor_id,
            asset_type=asset_type if "asset_type" in updates else None,
            usage_type=usage_type if "usage_type" in updates else None,
        )
    except InventoryValidationError as exc:
        raise _validation_http_error(exc) from exc

    before = snapshot_entity(asset, ASSET_ACTIVITY_FIELDS)
    for field, value in updates.items():
        setattr(asset, field, value)
    asset.updated_at = datetime.now(UTC)

    try:
        db.flush()
        log_entity_updated(
            db,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=asset.id,
            description_key="activity.inventory.asset.updated",
            actor=actor,
            before=before,
            after=snapshot_entity(asset, ASSET_ACTIVITY_FIELDS),
            metadata={"display_id": asset.display_id, "system_code": asset.system_code},
            request=request,
            is_demo=asset.is_demo,
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="inventory.errors.display_id_duplicate",
        ) from exc
    db.refresh(asset)
    return InventoryAssetResponse.model_validate(asset)


@router.post("/assets/{asset_id}/archive", response_model=InventoryAssetResponse)
def archive_asset(
    asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "archive")),
) -> InventoryAssetResponse:
    asset = _get_asset_or_404(asset_id, db)
    if asset.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is already archived")
    asset.archived_at = datetime.now(UTC)
    asset.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_archived(
        db,
        entity_type=ActivityEntityType.INVENTORY_ASSET,
        entity_id=asset.id,
        description_key="activity.inventory.asset.archived",
        actor=actor,
        metadata={"display_id": asset.display_id, "system_code": asset.system_code},
        request=request,
        is_demo=asset.is_demo,
    )
    db.commit()
    db.refresh(asset)
    return InventoryAssetResponse.model_validate(asset)


@router.post("/assets/{asset_id}/restore", response_model=InventoryAssetResponse)
def restore_asset(
    asset_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "restore")),
) -> InventoryAssetResponse:
    asset = _get_asset_or_404(asset_id, db, include_archived=True)
    if asset.archived_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is not archived")
    asset.archived_at = None
    asset.updated_at = datetime.now(UTC)
    db.flush()
    log_entity_restored(
        db,
        entity_type=ActivityEntityType.INVENTORY_ASSET,
        entity_id=asset.id,
        description_key="activity.inventory.asset.restored",
        actor=actor,
        metadata={"display_id": asset.display_id, "system_code": asset.system_code},
        request=request,
        is_demo=asset.is_demo,
    )
    db.commit()
    db.refresh(asset)
    return InventoryAssetResponse.model_validate(asset)


@router.post("/assets/{asset_id}/status", response_model=InventoryAssetStatusHistoryResponse)
def update_asset_status_endpoint(
    asset_id: UUID,
    payload: InventoryAssetStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("inventory", "manage_status")),
) -> InventoryAssetStatusHistoryResponse:
    asset = _get_asset_or_404(asset_id, db)
    try:
        history = update_asset_status(
            db,
            asset,
            category=payload.status_category,
            new_status=payload.new_status,
            reason=payload.reason,
            actor=actor,
            effective_at=payload.effective_at,
        )
        log_activity(
            db,
            action=ActivityAction.STATUS_CHANGED,
            entity_type=ActivityEntityType.INVENTORY_ASSET,
            entity_id=asset.id,
            description_key="activity.inventory.asset.status_changed",
            actor_user=actor,
            metadata={
                "display_id": asset.display_id,
                "system_code": asset.system_code,
                "status_category": payload.status_category.value,
                "previous_status": history.previous_status,
                "new_status": history.new_status,
            },
            changed_fields=[payload.status_category.value],
            previous_values={payload.status_category.value: history.previous_status},
            new_values={payload.status_category.value: history.new_status},
            request_context=activity_context_from_request(request),
            is_demo=asset.is_demo,
        )
        db.commit()
    except StatusTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.error_key) from exc
    db.refresh(history)
    return InventoryAssetStatusHistoryResponse.model_validate(history)


@router.get("/assets/{asset_id}/status-history", response_model=list[InventoryAssetStatusHistoryResponse])
def get_asset_status_history(
    asset_id: UUID,
    status_category: StatusCategory | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("inventory", "view")),
) -> list[InventoryAssetStatusHistoryResponse]:
    _get_asset_or_404(asset_id, db, include_archived=True)
    history = list_status_history(db, asset_id, category=status_category)
    return [InventoryAssetStatusHistoryResponse.model_validate(row) for row in history]
