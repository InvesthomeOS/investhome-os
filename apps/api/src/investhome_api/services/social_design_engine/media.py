"""Semantic media candidate ranking for SMB Design Engine (Asset IDs only)."""

from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset, CreativeStudioMediaFolder
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate

IMAGE_MIME_PREFIXES = ("image/",)
PREFERRED_CATEGORIES = (
    "02_MEDIA",
    "03_MARKETING",
    "04_PHOTOS",
    "05_RENDERINGS",
    "MEDIA",
    "MARKETING",
    "PHOTOS",
    "RENDER",
    "VISUAL",
)

TOKEN_RE = re.compile(r"[a-z0-9ğüşıöçàâäéèêëïîôùûüç]{2,}", re.I)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text or "")}


def _folder_path_hint(db: Session, folder_id: UUID | None) -> str:
    if folder_id is None:
        return ""
    parts: list[str] = []
    current = db.get(CreativeStudioMediaFolder, folder_id)
    depth = 0
    while current is not None and depth < 8:
        parts.append(current.name or "")
        if current.parent_id is None:
            break
        current = db.get(CreativeStudioMediaFolder, current.parent_id)
        depth += 1
    return " / ".join(reversed(parts))


def score_asset(
    asset: CreativeStudioMediaAsset,
    *,
    query_tokens: set[str],
    folder_path: str = "",
    preference_tokens: set[str] | None = None,
) -> float:
    score = 0.0
    ctype = (asset.content_type or "").lower()
    if any(ctype.startswith(p) for p in IMAGE_MIME_PREFIXES):
        score += 4.0
    elif ctype.startswith("video/"):
        score += 0.5
    else:
        score -= 2.0

    filename = (asset.filename or "").lower()
    fname_tokens = _tokens(filename)
    if query_tokens:
        overlap = len(query_tokens & fname_tokens)
        score += overlap * 1.5
        for tok in query_tokens:
            if tok in filename:
                score += 0.75

    category = (asset.folder_category or "").upper()
    for preferred in PREFERRED_CATEGORIES:
        if preferred in category:
            score += 2.0
            break

    path_l = folder_path.lower()
    path_tokens = _tokens(folder_path)
    if query_tokens:
        score += len(query_tokens & path_tokens) * 1.0
        for tok in query_tokens:
            if tok in path_l:
                score += 0.5

    tags = asset.tags if isinstance(asset.tags, list) else []
    tag_tokens: set[str] = set()
    for tag in tags:
        tag_tokens |= _tokens(str(tag))
    if query_tokens:
        score += len(query_tokens & tag_tokens) * 1.25

    # Prefer larger images slightly when dimensions known
    if asset.width and asset.height:
        area = int(asset.width) * int(asset.height)
        if area >= 1_000_000:
            score += 0.5
        elif area >= 300_000:
            score += 0.25

    pref = preference_tokens or set()
    if pref:
        hay = " ".join([filename, path_l, " ".join(str(t).lower() for t in tags)])
        hay_tokens = fname_tokens | path_tokens | tag_tokens
        overlap = len(pref & hay_tokens)
        score += overlap * 2.0
        for tok in pref:
            if tok in hay:
                score += 1.25

    return score


def list_media_candidates(
    db: Session,
    *,
    linked_project_id: UUID,
    instruction: str,
    limit: int = 24,
    preference_tokens: set[str] | None = None,
) -> list[SocialDesignMediaCandidate]:
    """List project-scoped image assets ranked for the instruction. No Unsplash/mock."""
    query = (
        select(CreativeStudioMediaAsset)
        .where(CreativeStudioMediaAsset.archived_at.is_(None))
        .where(CreativeStudioMediaAsset.linked_project_id == linked_project_id)
        .order_by(CreativeStudioMediaAsset.created_at.desc())
        .limit(200)
    )
    assets = list(db.scalars(query).all())
    query_tokens = _tokens(instruction)
    scored: list[SocialDesignMediaCandidate] = []

    for asset in assets:
        # Strict isolation — defensive
        if asset.linked_project_id != linked_project_id:
            continue
        folder_path = _folder_path_hint(db, asset.folder_id)
        s = score_asset(
            asset,
            query_tokens=query_tokens,
            folder_path=folder_path,
            preference_tokens=preference_tokens,
        )
        tags = [str(t) for t in (asset.tags or [])] if isinstance(asset.tags, list) else []
        scored.append(
            SocialDesignMediaCandidate(
                asset_id=asset.id,
                filename=asset.filename,
                content_type=asset.content_type,
                folder_id=asset.folder_id,
                folder_category=asset.folder_category,
                tags=tags,
                score=round(s, 4),
                linked_project_id=linked_project_id,
            )
        )

    scored.sort(key=lambda c: (-c.score, c.filename.lower()))
    return scored[: max(1, min(limit, 48))]


def pick_best_asset(
    candidates: list[SocialDesignMediaCandidate],
    *,
    require_image: bool = True,
) -> UUID | None:
    """Deterministic top pick — Asset ID only."""
    for cand in candidates:
        ctype = (cand.content_type or "").lower()
        if require_image and not ctype.startswith("image/"):
            continue
        if cand.score < 0:
            continue
        return cand.asset_id
    # Fallback: first image even if low score
    for cand in candidates:
        ctype = (cand.content_type or "").lower()
        if ctype.startswith("image/"):
            return cand.asset_id
    return None


def search_project_assets_by_filename(
    db: Session,
    *,
    linked_project_id: UUID,
    q: str,
    limit: int = 12,
) -> list[CreativeStudioMediaAsset]:
    pattern = f"%{(q or '').strip()}%"
    stmt = (
        select(CreativeStudioMediaAsset)
        .where(CreativeStudioMediaAsset.archived_at.is_(None))
        .where(CreativeStudioMediaAsset.linked_project_id == linked_project_id)
        .where(
            CreativeStudioMediaAsset.filename.ilike(pattern)
            | cast(CreativeStudioMediaAsset.tags, String).ilike(pattern)
        )
        .order_by(CreativeStudioMediaAsset.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
