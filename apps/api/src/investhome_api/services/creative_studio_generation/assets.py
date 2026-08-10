"""Validate selected Media Library assets against the linked project."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.schemas.creative_studio_generation import CreativeStudioSelectedAsset


def validate_selected_assets(
    db: Session,
    *,
    linked_project_id: UUID,
    selected_asset_ids: list[UUID],
) -> list[CreativeStudioSelectedAsset]:
    """
    Ensure every selected asset exists, is not archived, and belongs to linked_project_id.

    Cross-project asset ids are rejected (403). Missing assets → 404.
    """
    if not selected_asset_ids:
        return []

    # Preserve caller order; dedupe while validating
    seen: set[UUID] = set()
    ordered_ids: list[UUID] = []
    for aid in selected_asset_ids:
        if aid in seen:
            continue
        seen.add(aid)
        ordered_ids.append(aid)

    out: list[CreativeStudioSelectedAsset] = []
    for aid in ordered_ids:
        asset = db.get(CreativeStudioMediaAsset, aid)
        if asset is None or asset.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Asset not found: {aid}",
            )
        if asset.linked_project_id is None or asset.linked_project_id != linked_project_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Asset does not belong to linked_project_id "
                    f"(asset_id={aid}, expected_project={linked_project_id})"
                ),
            )
        out.append(
            CreativeStudioSelectedAsset(
                asset_id=asset.id,
                filename=asset.filename,
                project_id=linked_project_id,
                folder_category=asset.folder_category,
                content_type=asset.content_type,
            )
        )
    return out
