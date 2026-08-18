"""Resolve real project photos and logos for GPT Image edits. No generated marks."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_studio_media_service import (
    get_asset_or_404,
    open_asset_content,
)
from investhome_api.services.social_design_engine.generation import asset_preference_tokens
from investhome_api.services.social_design_engine.media import (
    list_media_candidates,
    pick_best_asset,
    pick_logo_asset,
    pick_supporting_logo_asset,
)

logger = logging.getLogger(__name__)

AERIAL_EXTERIOR_TOKENS = (
    asset_preference_tokens("premium_hero")
    | asset_preference_tokens("aerial")
    | asset_preference_tokens("exterior")
)

_EDIT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


@dataclass(frozen=True)
class ResolvedSourceImage:
    asset_id: UUID
    filename: str
    content_type: str
    folder_category: str | None
    tags: list[str]
    image_bytes: bytes
    width: int | None = None
    height: int | None = None
    role: str = "source"


def _image_dimensions(payload: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None, None


def ensure_edit_image_bytes(
    payload: bytes,
    filename: str,
    content_type: str,
) -> tuple[bytes, str, str] | None:
    """PNG/JPEG/WEBP for Images edits. SVG cannot be uploaded — caller instructs in brief."""
    ctype = (content_type or "").split(";")[0].strip().lower()
    lower_name = (filename or "source").lower()
    if ctype == "image/svg+xml" or lower_name.endswith(".svg"):
        return None
    if ctype in _EDIT_TYPES and lower_name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        if ctype in {"image/jpeg", "image/jpg"}:
            return payload, filename, "image/jpeg"
        if "webp" in ctype:
            try:
                with Image.open(io.BytesIO(payload)) as image:
                    converted = image.convert("RGBA") if "A" in (image.mode or "") else image.convert("RGB")
                    buf = io.BytesIO()
                    converted.save(buf, format="PNG")
                    stem = Path(filename or "source").stem or "source"
                    return buf.getvalue(), f"{stem}.png", "image/png"
            except Exception:
                return payload, filename, "image/webp"
        return payload, filename, "image/png"
    try:
        with Image.open(io.BytesIO(payload)) as image:
            has_alpha = "A" in (image.mode or "")
            converted = image.convert("RGBA") if has_alpha else image.convert("RGB")
            buf = io.BytesIO()
            converted.save(buf, format="PNG")
            stem = Path(filename or "source").stem or "source"
            return buf.getvalue(), f"{stem}.png", "image/png"
    except Exception:
        return None


def _candidate_for(
    candidates: list[SocialDesignMediaCandidate],
    asset_id: UUID,
) -> SocialDesignMediaCandidate | None:
    return next((c for c in candidates if c.asset_id == asset_id), None)


def pick_source_asset(
    db: Session,
    *,
    linked_project_id: UUID,
    instruction: str,
    selected_asset_ids: list[UUID] | None = None,
) -> tuple[SocialDesignMediaCandidate, list[SocialDesignMediaCandidate]]:
    selected = [aid for aid in (selected_asset_ids or []) if aid]
    candidates = list_media_candidates(
        db,
        linked_project_id=linked_project_id,
        instruction=instruction,
        limit=24,
        preference_tokens=AERIAL_EXTERIOR_TOKENS,
    )
    picked: UUID | None = None
    if selected:
        allowed = {c.asset_id for c in candidates}
        for aid in selected:
            if aid in allowed:
                picked = aid
                break
        if picked is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected source image is not a valid project media asset.",
            )
    if picked is None:
        picked = pick_best_asset(candidates, require_image=True)
    if picked is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No real project image is available for GPT Image project mode.",
        )
    candidate = _candidate_for(candidates, picked)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No real project image is available for GPT Image project mode.",
        )
    ctype = (candidate.content_type or "").lower()
    if not ctype.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GPT Image project mode requires a real project image, not a document.",
        )
    if (candidate.visual_subject or "") == "BRANDING":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="GPT Image source must be a project render/photo, not a logo.",
        )
    return candidate, candidates


def resolve_image_bytes(
    db: Session,
    *,
    linked_project_id: UUID,
    candidate: SocialDesignMediaCandidate,
    role: str,
) -> ResolvedSourceImage | None:
    asset: CreativeStudioMediaAsset = get_asset_or_404(candidate.asset_id, db)
    if asset.linked_project_id != linked_project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media asset not found",
        )
    stream, media_type = open_asset_content(asset, linked_project_id=linked_project_id)
    try:
        payload = stream.read()
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()
    if not payload:
        if role == "source":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Project source image could not be read for GPT Image edits.",
            )
        return None
    filename = candidate.filename or asset.filename or f"{role}.png"
    content_type = media_type or candidate.content_type or asset.content_type or "image/png"
    converted = ensure_edit_image_bytes(payload, filename, content_type)
    if converted is None:
        logger.info(
            "gpt_image_skip_non_raster",
            extra={"role": role, "source_filename": filename, "content_type": content_type},
        )
        if role == "source":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Project source image could not be converted for GPT Image edits.",
            )
        return None
    image_bytes, filename, content_type = converted
    width, height = _image_dimensions(image_bytes)
    return ResolvedSourceImage(
        asset_id=asset.id,
        filename=filename,
        content_type=content_type,
        folder_category=candidate.folder_category,
        tags=list(candidate.tags or []),
        image_bytes=image_bytes,
        width=width,
        height=height,
        role=role,
    )


def pick_design_references(
    candidates: list[SocialDesignMediaCandidate],
    *,
    skip_ids: set[UUID],
    limit: int = 2,
) -> list[SocialDesignMediaCandidate]:
    out: list[SocialDesignMediaCandidate] = []
    for cand in candidates:
        if cand.asset_id in skip_ids:
            continue
        if (cand.visual_subject or "") == "BRANDING":
            continue
        hay = f"{cand.filename or ''} {cand.folder_category or ''} {' '.join(cand.tags or [])}".lower()
        if "logo" in hay:
            continue
        out.append(cand)
        if len(out) >= limit:
            break
    return out


def resolve_project_inputs(
    db: Session,
    *,
    linked_project_id: UUID,
    instruction: str,
    selected_asset_ids: list[UUID] | None,
    project_name: str | None,
    project_code: str | None,
) -> tuple[ResolvedSourceImage, list[ResolvedSourceImage], list[SocialDesignMediaCandidate], list[str]]:
    source_candidate, candidates = pick_source_asset(
        db,
        linked_project_id=linked_project_id,
        instruction=instruction,
        selected_asset_ids=selected_asset_ids,
    )
    source = resolve_image_bytes(
        db,
        linked_project_id=linked_project_id,
        candidate=source_candidate,
        role="source",
    )
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project source image could not be read for GPT Image edits.",
        )

    extras: list[ResolvedSourceImage] = []
    notes: list[str] = []
    project_logo = pick_logo_asset(
        candidates,
        project_name=project_name,
        project_code=project_code,
    )
    supporting = pick_supporting_logo_asset(
        candidates,
        project_logo=project_logo,
        project_name=project_name,
    )
    for role, cand in (("project_logo", project_logo), ("investhome_logo", supporting)):
        if cand is None:
            notes.append(f"{role}: no real file found — do not invent a logo.")
            continue
        resolved = resolve_image_bytes(
            db,
            linked_project_id=linked_project_id,
            candidate=cand,
            role=role,
        )
        if resolved is None:
            notes.append(
                f"{role}: file {cand.filename} is not a raster image (likely SVG). "
                "Do not generate a fake logo; the OS will omit this mark rather than invent one."
            )
            continue
        extras.append(resolved)
        notes.append(
            f"{role}: real file {resolved.filename} (asset {resolved.asset_id}) "
            "will be composited after generation — do not redraw it."
        )

    skip = {source.asset_id, *(row.asset_id for row in extras)}
    references = pick_design_references(candidates, skip_ids=skip, limit=2)
    return source, extras, references, notes
