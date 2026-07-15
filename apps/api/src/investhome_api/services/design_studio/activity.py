"""Visual Design Studio domain activity hooks."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivityEntityType, ActivitySource
from investhome_api.models.user_auth import User
from investhome_api.services.activity_recorder import activity_context_from_request
from investhome_api.services.activity_service import log_activity


def record_design_project_created(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.project_created",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title},
        request_context=activity_context_from_request(request),
    )


def record_source_plan_selected(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    document_title: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.source_plan_selected",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "document_title": document_title},
        request_context=activity_context_from_request(request),
    )


def record_color_overlay_updated(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    mode: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.color_overlay_updated",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "mode": mode},
        request_context=activity_context_from_request(request),
    )


def record_version_saved(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    version_number: int,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.version_saved",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "version_number": str(version_number)},
        request_context=activity_context_from_request(request),
    )


def record_design_approved(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.APPROVED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.approved",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title},
        request_context=activity_context_from_request(request),
    )


def record_design_rejected(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
    comment: str | None = None,
) -> None:
    metadata: dict[str, str] = {"title": title}
    if comment:
        metadata["comment"] = comment
    log_activity(
        db,
        action=ActivityAction.REJECTED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.rejected",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata=metadata,
        request_context=activity_context_from_request(request),
    )


def record_design_archived(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.ARCHIVED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.archived",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title},
        request_context=activity_context_from_request(request),
    )


def record_style_preset_created(
    db: Session,
    *,
    preset_id: UUID,
    name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=preset_id,
        description_key="activity.design.style_preset_created",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"name": name},
        request_context=activity_context_from_request(request),
    )


def record_style_preset_updated(
    db: Session,
    *,
    preset_id: UUID,
    name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=preset_id,
        description_key="activity.design.style_preset_updated",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"name": name},
        request_context=activity_context_from_request(request),
    )


def record_material_package_created(
    db: Session,
    *,
    package_id: UUID,
    name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=package_id,
        description_key="activity.design.material_package_created",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"name": name},
        request_context=activity_context_from_request(request),
    )


def record_material_package_applied(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    package_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.material_package_applied",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "package_name": package_name},
        request_context=activity_context_from_request(request),
    )


def record_furniture_layout_updated(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    item_count: int,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.furniture_layout_updated",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "item_count": str(item_count)},
        request_context=activity_context_from_request(request),
    )


def record_submitted_for_review(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.submitted_for_review",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title},
        request_context=activity_context_from_request(request),
    )


def record_revision_requested(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
    comment: str | None = None,
) -> None:
    metadata: dict[str, str] = {"title": title}
    if comment:
        metadata["comment"] = comment
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.revision_requested",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata=metadata,
        request_context=activity_context_from_request(request),
    )


def record_style_preset_created(
    db: Session,
    *,
    preset_id: UUID,
    name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=preset_id,
        description_key="activity.design.style_preset_created",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"name": name},
        request_context=activity_context_from_request(request),
    )


def record_style_preset_updated(
    db: Session,
    *,
    preset_id: UUID,
    name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=preset_id,
        description_key="activity.design.style_preset_updated",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"name": name},
        request_context=activity_context_from_request(request),
    )


def record_material_package_created(
    db: Session,
    *,
    package_id: UUID,
    name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.CREATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=package_id,
        description_key="activity.design.material_package_created",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"name": name},
        request_context=activity_context_from_request(request),
    )


def record_material_package_applied(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    package_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.material_package_applied",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "package_name": package_name},
        request_context=activity_context_from_request(request),
    )


def record_furniture_layout_updated(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    item_count: int,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.furniture_layout_updated",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "item_count": str(item_count)},
        request_context=activity_context_from_request(request),
    )


def record_furniture_added(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    item_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.furniture_added",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "item_name": item_name},
        request_context=activity_context_from_request(request),
    )


def record_furniture_removed(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    item_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.furniture_removed",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "item_name": item_name},
        request_context=activity_context_from_request(request),
    )


def record_furniture_moved(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    item_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.furniture_moved",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "item_name": item_name},
        request_context=activity_context_from_request(request),
    )


def record_style_changed(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    preset_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.style_changed",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "preset_name": preset_name},
        request_context=activity_context_from_request(request),
    )


def record_material_changed(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    package_name: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.material_changed",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title, "package_name": package_name},
        request_context=activity_context_from_request(request),
    )


def record_submitted_for_review(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.submitted_for_review",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata={"title": title},
        request_context=activity_context_from_request(request),
    )


def record_revision_requested(
    db: Session,
    *,
    design_project_id: UUID,
    title: str,
    actor: User | None,
    request: Request | None = None,
    comment: str | None = None,
) -> None:
    metadata: dict[str, str] = {"title": title}
    if comment:
        metadata["comment"] = comment
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=ActivityEntityType.DESIGN_PROJECT,
        entity_id=design_project_id,
        description_key="activity.design.revision_requested",
        actor_user=actor,
        actor_type=ActivityActorType.USER if actor else ActivityActorType.SYSTEM,
        source=ActivitySource.WEB if request else ActivitySource.API,
        metadata=metadata,
        request_context=activity_context_from_request(request),
    )
