"""Resolve real project photos and logos for GPT Image edits. No generated marks."""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_studio_media_service import (
    get_asset_or_404,
    open_asset_content,
)
from investhome_api.services.gpt_image_design.svg_raster import svg_bytes_to_png
from investhome_api.services.social_design_engine.generation import asset_preference_tokens
from investhome_api.services.social_design_engine.media import (
    classify_visual_subject,
    list_media_candidates,
    pick_best_asset,
    pick_logo_asset,
)

logger = logging.getLogger(__name__)

AERIAL_EXTERIOR_TOKENS = (
    asset_preference_tokens("premium_hero")
    | asset_preference_tokens("aerial")
    | asset_preference_tokens("exterior")
)

_EDIT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}

# Preferred Temple Primary lockup (01_BRAND). Must remain a real file — never AI-redrawn.
TEMPLE_PRIMARY_LOGO_ID = UUID("7b58877e-efca-4e9a-9027-6fd18fb1b345")

INVESHOME_GLOBAL_LOGO_MISSING = "Investhome global logo asset bulunamadı"


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
    original_content_type: str | None = None


@dataclass(frozen=True)
class LogoResolveResult:
    logos: list[ResolvedSourceImage]
    notes: list[str]
    warnings: list[str]
    investhome_found: bool


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


def ensure_logo_image_bytes(
    payload: bytes,
    filename: str,
    content_type: str,
) -> tuple[bytes, str, str, str] | None:
    """Rasterize real logo bytes for OS composition. SVG is converted; never AI-redrawn.

    Returns (bytes, filename, content_type_for_pil, original_content_type).
    """
    ctype = (content_type or "").split(";")[0].strip().lower()
    lower_name = (filename or "logo").lower()
    original = ctype or "application/octet-stream"
    if ctype == "image/svg+xml" or lower_name.endswith(".svg"):
        png = svg_bytes_to_png(payload)
        if png is None:
            return None
        stem = Path(filename or "logo").stem or "logo"
        return png, f"{stem}.png", "image/png", "image/svg+xml"
    converted = ensure_edit_image_bytes(payload, filename, content_type)
    if converted is None:
        return None
    image_bytes, out_name, out_type = converted
    return image_bytes, out_name, out_type, original


def _candidate_for(
    candidates: list[SocialDesignMediaCandidate],
    asset_id: UUID,
) -> SocialDesignMediaCandidate | None:
    return next((c for c in candidates if c.asset_id == asset_id), None)


def _candidate_from_asset(
    db: Session,
    asset: CreativeStudioMediaAsset,
) -> SocialDesignMediaCandidate:
    tags = [str(t) for t in (asset.tags or [])] if isinstance(asset.tags, list) else []
    folder_path = ""
    if asset.folder_id is not None:
        from investhome_api.services.social_design_engine.media import _folder_path_hint

        folder_path = _folder_path_hint(db, asset.folder_id)
    subject = classify_visual_subject(asset, folder_path=folder_path)
    return SocialDesignMediaCandidate(
        asset_id=asset.id,
        filename=asset.filename,
        content_type=asset.content_type,
        folder_id=asset.folder_id,
        folder_category=asset.folder_category,
        tags=tags,
        score=1.0,
        linked_project_id=asset.linked_project_id or UUID(int=0),
        visual_subject=subject,
        source_type=asset.source_type,
        provenance_source="media_library",
    )


def prefer_project_logo(
    candidates: list[SocialDesignMediaCandidate],
    *,
    project_name: str | None,
    project_code: str | None,
    preferred_asset_id: UUID | None = TEMPLE_PRIMARY_LOGO_ID,
) -> SocialDesignMediaCandidate | None:
    """Prefer a known Primary SVG when present; else existing logo picker."""
    if preferred_asset_id is not None:
        preferred = _candidate_for(candidates, preferred_asset_id)
        if preferred is not None:
            return preferred
        # Prefered ID may exist in DB but not in ranked candidates — still allow.
        # Caller may resolve by ID separately.
    return pick_logo_asset(
        candidates,
        project_name=project_name,
        project_code=project_code,
    )


def find_global_investhome_logo(db: Session) -> SocialDesignMediaCandidate | None:
    """Company/global brand lockup — not project Media Library only.

    Looks for assets with no project scope (or company-level) whose filename/tags
    clearly identify the corporate Investhome mark. Never invents a substitute.
    """
    query = (
        select(CreativeStudioMediaAsset)
        .where(CreativeStudioMediaAsset.archived_at.is_(None))
        .where(CreativeStudioMediaAsset.linked_project_id.is_(None))
        .order_by(CreativeStudioMediaAsset.created_at.desc())
        .limit(200)
    )
    assets = list(db.scalars(query).all())
    scored: list[tuple[float, CreativeStudioMediaAsset]] = []
    for asset in assets:
        hay = " ".join(
            [
                asset.filename or "",
                asset.folder_category or "",
                " ".join(str(t) for t in (asset.tags or []) if isinstance(asset.tags, list)),
            ]
        ).lower()
        if "investhome" not in hay and "invest home" not in hay:
            continue
        if "logo" not in hay and (asset.folder_category or "") != "01_BRAND":
            continue
        ctype = (asset.content_type or "").lower()
        if not ctype.startswith("image/"):
            continue
        # Reject project-specific Temple / addition / historic marks.
        if any(tok in hay for tok in ("temple", "tmp_001", "addition", "historic")):
            continue
        score = 3.0
        if "logo" in hay:
            score += 2.0
        if "primary" in hay:
            score += 1.5
        if ctype == "image/svg+xml":
            score += 0.5
        scored.append((score, asset))
    if not scored:
        # Broader corporate search: any non-project asset tagged as Investhome brand logo
        # across company folders (still linked_project_id NULL only).
        broader = (
            select(CreativeStudioMediaAsset)
            .where(CreativeStudioMediaAsset.archived_at.is_(None))
            .where(CreativeStudioMediaAsset.linked_project_id.is_(None))
            .where(
                or_(
                    CreativeStudioMediaAsset.filename.ilike("%investhome%logo%"),
                    CreativeStudioMediaAsset.filename.ilike("%logo%investhome%"),
                    cast(CreativeStudioMediaAsset.tags, String).ilike("%investhome%"),
                )
            )
            .limit(50)
        )
        for asset in db.scalars(broader).all():
            hay = (asset.filename or "").lower()
            if any(tok in hay for tok in ("temple", "tmp_001", "addition", "historic")):
                continue
            ctype = (asset.content_type or "").lower()
            if ctype.startswith("image/"):
                scored.append((1.0, asset))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], (row[1].filename or "").lower()))
    return _candidate_from_asset(db, scored[0][1])


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
    linked_project_id: UUID | None,
    candidate: SocialDesignMediaCandidate,
    role: str,
    allow_svg: bool = False,
) -> ResolvedSourceImage | None:
    asset: CreativeStudioMediaAsset = get_asset_or_404(candidate.asset_id, db)
    if linked_project_id is not None and asset.linked_project_id is not None:
        if asset.linked_project_id != linked_project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media asset not found",
            )
    # Global/company logos (linked_project_id NULL) skip project isolation on open.
    open_scope = None if asset.linked_project_id is None else linked_project_id
    stream, media_type = open_asset_content(asset, linked_project_id=open_scope)
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
    original_ctype = content_type
    if allow_svg or role in {"project_logo", "investhome_logo"}:
        converted_logo = ensure_logo_image_bytes(payload, filename, content_type)
        if converted_logo is None:
            logger.info(
                "gpt_image_logo_unreadable",
                extra={"role": role, "source_filename": filename, "content_type": content_type},
            )
            return None
        image_bytes, filename, content_type, original_ctype = converted_logo
    else:
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
        original_content_type=original_ctype,
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
) -> tuple[ResolvedSourceImage, list[ResolvedSourceImage], list[SocialDesignMediaCandidate], list[str], list[str]]:
    """Returns source, logos, design refs, logo_notes, composition_warnings."""
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
    warnings: list[str] = []

    # Prefer Temple Primary SVG when present in this project library.
    project_logo = prefer_project_logo(
        candidates,
        project_name=project_name,
        project_code=project_code,
        preferred_asset_id=TEMPLE_PRIMARY_LOGO_ID,
    )
    if project_logo is None and any(c.asset_id == TEMPLE_PRIMARY_LOGO_ID for c in candidates):
        project_logo = _candidate_for(candidates, TEMPLE_PRIMARY_LOGO_ID)
    if project_logo is None:
        # Direct fetch of preferred Primary when it belongs to this project.
        preferred_asset = db.get(CreativeStudioMediaAsset, TEMPLE_PRIMARY_LOGO_ID)
        if (
            preferred_asset is not None
            and preferred_asset.archived_at is None
            and preferred_asset.linked_project_id == linked_project_id
        ):
            project_logo = _candidate_from_asset(db, preferred_asset)

    # Investhome: search global/company brand assets first — never silent fallback.
    supporting = find_global_investhome_logo(db)
    investhome_found = supporting is not None
    if not investhome_found:
        warnings.append(INVESHOME_GLOBAL_LOGO_MISSING)
        notes.append(f"investhome_logo: {INVESHOME_GLOBAL_LOGO_MISSING}")
        # Do not silently use a project-local substitute as "global".
        supporting = None

    for role, cand in (("project_logo", project_logo), ("investhome_logo", supporting)):
        if cand is None:
            if role == "project_logo":
                notes.append(f"{role}: no real file found — do not invent a logo.")
            continue
        resolved = resolve_image_bytes(
            db,
            linked_project_id=linked_project_id if role == "project_logo" else None,
            candidate=cand,
            role=role,
            allow_svg=True,
        )
        if resolved is None:
            notes.append(
                f"{role}: file {cand.filename} could not be prepared for OS composition. "
                "Do not generate a fake logo."
            )
            if role == "investhome_logo":
                warnings.append(INVESHOME_GLOBAL_LOGO_MISSING)
                investhome_found = False
            continue
        extras.append(resolved)
        src_kind = "SVG" if (resolved.original_content_type or "").endswith("svg+xml") else "raster"
        notes.append(
            f"{role}: real {src_kind} file {cand.filename} (asset {resolved.asset_id}) "
            "will be composited by OS Final Composition Layer — do not redraw it."
        )

    skip = {source.asset_id, *(row.asset_id for row in extras)}
    references = pick_design_references(candidates, skip_ids=skip, limit=2)
    if not investhome_found and INVESHOME_GLOBAL_LOGO_MISSING not in warnings:
        warnings.append(INVESHOME_GLOBAL_LOGO_MISSING)
    return source, extras, references, notes, warnings
