"""Semantic media candidate ranking for SMB Design Engine (Asset IDs only)."""

from __future__ import annotations

import re
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset, CreativeStudioMediaFolder
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate

IMAGE_MIME_PREFIXES = ("image/",)
HERO_IMAGE_MIMES = ("image/jpeg", "image/jpg", "image/png", "image/webp")
PREFERRED_CATEGORIES = (
    "02_RENDER",
    "06_MEDIA",
    "05_LOCATION",
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

VisualSubject = Literal[
    "EXTERIOR",
    "INTERIOR",
    "AERIAL",
    "ARCHITECTURAL_RENDER",
    "FLOOR_PLAN",
    "NEIGHBORHOOD",
    "LOCATION",
    "AMENITY",
    "BRANDING",
    "UNKNOWN",
]

GENERATIVE_MARKERS = (
    "ideogram",
    "ideogram-poc",
    "provider:ideogram",
    "generated-image",
    "unsplash",
    "stock-photo",
    "placeholder",
)

CAMPAIGN_SUBJECT_PREF: dict[str, tuple[str, ...]] = {
    "LOCATION": ("AERIAL", "EXTERIOR", "NEIGHBORHOOD", "LOCATION", "ARCHITECTURAL_RENDER"),
    "INVESTMENT": ("ARCHITECTURAL_RENDER", "EXTERIOR", "AERIAL"),
    "ARCHITECTURE": ("EXTERIOR", "ARCHITECTURAL_RENDER"),
    "LIFESTYLE": ("INTERIOR", "AMENITY"),
    "LAUNCH": ("ARCHITECTURAL_RENDER", "EXTERIOR", "AERIAL"),
    "PROJECT_OVERVIEW": ("ARCHITECTURAL_RENDER", "EXTERIOR", "AERIAL", "NEIGHBORHOOD"),
}

TOKEN_RE = re.compile(r"[a-z0-9ğüşıöçàâäéèêëïîôùûüç]{2,}", re.I)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text or "")}


def _haystack(asset: CreativeStudioMediaAsset, folder_path: str = "") -> str:
    tags = asset.tags if isinstance(asset.tags, list) else []
    return " ".join(
        [
            asset.filename or "",
            asset.folder_category or "",
            folder_path,
            " ".join(str(t) for t in tags),
        ]
    ).lower()


def is_generative_or_synthetic_asset(asset: CreativeStudioMediaAsset) -> bool:
    """Never use Ideogram/Unsplash/placeholder output as a real project photograph."""
    hay = _haystack(asset)
    if any(marker in hay for marker in GENERATIVE_MARKERS):
        return True
    name = (asset.filename or "").lower()
    if name.startswith("ideogram-") or name.startswith("unsplash-"):
        return True
    return False


def is_hero_image(asset: CreativeStudioMediaAsset) -> bool:
    ctype = (asset.content_type or "").lower()
    if not any(ctype.startswith(p) or ctype == p for p in IMAGE_MIME_PREFIXES):
        return False
    if ctype == "image/svg+xml":
        return False
    if ctype.startswith("image/") and ctype not in HERO_IMAGE_MIMES and "jpeg" not in ctype and "png" not in ctype and "webp" not in ctype:
        return False
    name = (asset.filename or "").lower()
    if name in {".ds_store", "thumbs.db"} or name.endswith(".ds_store"):
        return False
    return True


def classify_visual_subject(
    asset: CreativeStudioMediaAsset,
    *,
    folder_path: str = "",
) -> VisualSubject:
    """Classify from existing metadata first. Do not invent a category without evidence."""
    category = (asset.folder_category or "").upper()
    hay = _haystack(asset, folder_path)
    filename = (asset.filename or "").lower()

    if category == "01_BRAND" or any(k in hay for k in ("logo", "wordmark", "brandmark")):
        return "BRANDING"
    if category in {"03_FLOOR_PLANS", "04_UNIT_PLANS"} or any(
        k in hay for k in ("floorplan", "floor plan", "floor_plan", "unit plan", "unit_plan")
    ):
        return "FLOOR_PLAN"
    if any(k in hay for k in ("aerial", "drone", "birdseye", "bird's eye", "overhead")):
        return "AERIAL"
    if any(k in hay for k in ("amenity", "amenities", "spa", "pool", "rooftop", "gym", "lobby")):
        if any(k in hay for k in ("interior", "living", "bedroom", "kitchen", "bathroom", "suite")):
            return "INTERIOR"
        return "AMENITY"
    if any(k in hay for k in ("interior", "living", "bedroom", "kitchen", "bathroom", "suite", "residence")):
        return "INTERIOR"
    if category == "02_RENDER" or "render" in filename:
        if any(k in hay for k in ("exterior", "facade", "façade", "street", "sunset", "twilight", "day")):
            return "ARCHITECTURAL_RENDER"
        if any(k in hay for k in ("interior", "living", "bedroom", "kitchen", "bathroom")):
            return "INTERIOR"
        return "ARCHITECTURAL_RENDER" if "render" in hay else "UNKNOWN"
    if any(k in hay for k in ("exterior", "facade", "façade", "street elevation", "building")):
        return "EXTERIOR"
    if category == "05_LOCATION":
        return "LOCATION"
    if any(k in hay for k in ("neighborhood", "streetscape", "context", "chapel", "campus")):
        return "NEIGHBORHOOD"
    if category == "06_MEDIA":
        return "EXTERIOR" if any(k in hay for k in ("chapel", "building", "street")) else "UNKNOWN"
    return "UNKNOWN"


def provenance_source_for_asset(asset: CreativeStudioMediaAsset) -> str:
    source = (asset.source_type or "").strip().lower()
    if source == "google_drive" or (asset.storage_provider or "") == "google_drive":
        return "google_drive"
    if source == "upload" or (asset.storage_provider or "") == "local":
        return "upload"
    return source or (asset.storage_provider or "unknown")


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
    visual_subject: str | None = None,
    campaign_type: str | None = None,
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

    subject = (visual_subject or "").upper()
    campaign = (campaign_type or "").upper()
    preferred = CAMPAIGN_SUBJECT_PREF.get(campaign) or ()
    if subject and preferred:
        if subject in preferred:
            score += 6.0 - preferred.index(subject) * 0.75
        elif subject in {"FLOOR_PLAN", "BRANDING"}:
            score -= 8.0
        elif subject == "UNKNOWN":
            score -= 1.5
    if is_generative_or_synthetic_asset(asset):
        score -= 50.0
    if not is_hero_image(asset):
        score -= 20.0

    return score


def list_media_candidates(
    db: Session,
    *,
    linked_project_id: UUID,
    instruction: str,
    limit: int = 24,
    preference_tokens: set[str] | None = None,
    campaign_type: str | None = None,
    exclude_asset_ids: set[UUID] | None = None,
) -> list[SocialDesignMediaCandidate]:
    """List project-scoped image assets ranked for the instruction. No Unsplash/mock."""
    query = (
        select(CreativeStudioMediaAsset)
        .where(CreativeStudioMediaAsset.archived_at.is_(None))
        .where(CreativeStudioMediaAsset.linked_project_id == linked_project_id)
        .order_by(CreativeStudioMediaAsset.created_at.desc())
        .limit(400)
    )
    assets = list(db.scalars(query).all())
    query_tokens = _tokens(instruction)
    scored: list[SocialDesignMediaCandidate] = []
    skip_ids = exclude_asset_ids or set()

    for asset in assets:
        # Strict isolation — defensive
        if asset.linked_project_id != linked_project_id:
            continue
        if asset.id in skip_ids:
            continue
        if is_generative_or_synthetic_asset(asset):
            continue
        folder_path = _folder_path_hint(db, asset.folder_id)
        subject = classify_visual_subject(asset, folder_path=folder_path)
        s = score_asset(
            asset,
            query_tokens=query_tokens,
            folder_path=folder_path,
            preference_tokens=preference_tokens,
            visual_subject=subject,
            campaign_type=campaign_type,
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
                visual_subject=subject,
                source_type=asset.source_type,
                provenance_source=provenance_source_for_asset(asset),
            )
        )

    scored.sort(key=lambda c: (-c.score, c.filename.lower()))
    cap = max(1, min(limit, 48))
    heroes = [c for c in scored if (c.visual_subject or "") != "BRANDING"][:cap]
    brands = [c for c in scored if (c.visual_subject or "") == "BRANDING"][:8]
    merged = heroes + [b for b in brands if b.asset_id not in {h.asset_id for h in heroes}]
    return merged


def pick_best_asset(
    candidates: list[SocialDesignMediaCandidate],
    *,
    require_image: bool = True,
    campaign_type: str | None = None,
) -> UUID | None:
    """Deterministic top pick — Asset ID only. Never a generated substitute."""
    preferred = CAMPAIGN_SUBJECT_PREF.get((campaign_type or "").upper()) or ()
    ranked = list(candidates)
    if preferred:
        ranked = sorted(
            ranked,
            key=lambda c: (
                0 if (c.visual_subject or "") in preferred else 1,
                preferred.index(c.visual_subject) if (c.visual_subject or "") in preferred else 99,
                -c.score,
                (c.filename or "").lower(),
            ),
        )
    for cand in ranked:
        ctype = (cand.content_type or "").lower()
        if require_image and not ctype.startswith("image/"):
            continue
        if ctype == "image/svg+xml":
            continue
        if (cand.visual_subject or "") in {"FLOOR_PLAN", "BRANDING"} and preferred:
            continue
        if cand.score < 0:
            continue
        return cand.asset_id
    # Fallback: first real photograph/render even if low score — never SVG/generative.
    for cand in ranked:
        ctype = (cand.content_type or "").lower()
        if ctype.startswith("image/") and ctype != "image/svg+xml" and (cand.visual_subject or "") not in {
            "FLOOR_PLAN",
            "BRANDING",
        }:
            return cand.asset_id
    return None


def pick_logo_asset(
    candidates: list[SocialDesignMediaCandidate],
    *,
    project_name: str | None = None,
    project_code: str | None = None,
) -> SocialDesignMediaCandidate | None:
    """Real brand asset only. Never generate a logo.

    Project identity (name/code in filename) outranks a generic corporate lockup.
    """
    name_tokens = {t.lower() for t in TOKEN_RE.findall(project_name or "") if len(t) >= 4}
    code_hay = (project_code or "").strip().lower()
    scored: list[tuple[float, SocialDesignMediaCandidate]] = []
    for cand in candidates:
        hay = " ".join(
            [
                cand.filename or "",
                cand.folder_category or "",
                " ".join(cand.tags or []),
            ]
        ).lower()
        if (cand.visual_subject or "") != "BRANDING" and "logo" not in hay and (cand.folder_category or "") != "01_BRAND":
            continue
        ctype = (cand.content_type or "").lower()
        if not ctype.startswith("image/"):
            continue
        score = 0.0
        if "logo" in hay:
            score += 4.0
        if "primary" in hay:
            score += 2.0
        if "white" in hay:
            score += 1.5
        if ctype == "image/svg+xml":
            score += 0.5
        if "historic" in hay:
            score -= 1.8
        if "addition" in hay:
            score -= 1.8
        if re.search(r"(^|_|-)logo(_|-)primary", hay) and "addition" not in hay and "historic" not in hay:
            score += 2.0
        if any(tok in hay for tok in name_tokens):
            score += 2.5
        if code_hay and code_hay in hay:
            score += 2.5
        elif code_hay:
            for part in re.split(r"[-_\s]+", code_hay):
                if len(part) >= 3 and part in hay:
                    score += 1.2
                    break
        # Corporate lockup is supporting, not the primary project mark.
        if "investhome" in hay and not any(tok in hay for tok in name_tokens) and (
            not code_hay or code_hay not in hay
        ):
            score -= 1.2
        scored.append((score, cand))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], row[1].filename.lower()))
    return scored[0][1]


def pick_supporting_logo_asset(
    candidates: list[SocialDesignMediaCandidate],
    *,
    project_logo: SocialDesignMediaCandidate | None,
    project_name: str | None = None,
) -> SocialDesignMediaCandidate | None:
    """Corporate Investhome lockup only — never a generated mark, never the project logo."""
    skip = project_logo.asset_id if project_logo is not None else None
    name_tokens = {t.lower() for t in TOKEN_RE.findall(project_name or "") if len(t) >= 4}
    scored: list[tuple[float, SocialDesignMediaCandidate]] = []
    for cand in candidates:
        if skip is not None and cand.asset_id == skip:
            continue
        hay = " ".join(
            [
                cand.filename or "",
                cand.folder_category or "",
                " ".join(cand.tags or []),
            ]
        ).lower()
        if (cand.visual_subject or "") != "BRANDING" and "logo" not in hay and (cand.folder_category or "") != "01_BRAND":
            continue
        ctype = (cand.content_type or "").lower()
        if not ctype.startswith("image/"):
            continue
        if any(tok in hay for tok in name_tokens) and "investhome" not in hay:
            continue
        if "investhome" not in hay and "invest home" not in hay:
            continue
        score = 3.0 if "investhome" in hay else 1.0
        if "logo" in hay:
            score += 2.0
        if "white" in hay:
            score += 0.8
        if "addition" in hay or "historic" in hay or "temple" in hay:
            score -= 4.0
        scored.append((score, cand))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], row[1].filename.lower()))
    return scored[0][1]


def pick_map_asset(candidates: list[SocialDesignMediaCandidate]) -> SocialDesignMediaCandidate | None:
    """Real location/map asset only. Floor plans are not maps."""
    scored: list[tuple[float, SocialDesignMediaCandidate]] = []
    for cand in candidates:
        hay = " ".join(
            [
                cand.filename or "",
                cand.folder_category or "",
                " ".join(cand.tags or []),
                cand.visual_subject or "",
            ]
        ).lower()
        subject = (cand.visual_subject or "").upper()
        if subject == "FLOOR_PLAN":
            continue
        ctype = (cand.content_type or "").lower()
        if not ctype.startswith("image/") or ctype == "image/svg+xml":
            continue
        score = 0.0
        if not any(k in hay for k in ("map", "site-plan", "siteplan", "context-plan", "vicinity", "location-map")):
            continue
        score += 6.0
        if subject in {"LOCATION", "AERIAL", "NEIGHBORHOOD"}:
            score += 1.5
        if "floor" in hay or "unit plan" in hay:
            continue
        scored.append((score, cand))
    if not scored:
        return None
    scored.sort(key=lambda row: (-row[0], row[1].filename.lower()))
    return scored[0][1]


def extract_design_reference_language(
    candidates: list[SocialDesignMediaCandidate],
    *,
    project_name: str | None = None,
) -> dict[str, Any]:
    """Read composition language from real marketing/brand references. Never photocopy."""
    name_l = (project_name or "").lower()
    refs: list[dict[str, str]] = []
    for cand in candidates:
        hay = " ".join(
            [
                cand.filename or "",
                cand.folder_category or "",
                " ".join(cand.tags or []),
            ]
        ).lower()
        category = (cand.folder_category or "").upper()
        is_ref = category in {"03_MARKETING", "01_BRAND", "05_LOCATION"} or any(
            k in hay
            for k in (
                "campaign",
                "keyvisual",
                "key-visual",
                "social",
                "instagram",
                "mood",
                "board",
                "lookbook",
                "stationery",
                "brand",
            )
        )
        if not is_ref:
            continue
        if (cand.visual_subject or "") == "FLOOR_PLAN":
            continue
        refs.append(
            {
                "filename": cand.filename or "",
                "category": cand.folder_category or "",
                "subject": cand.visual_subject or "",
            }
        )
        if len(refs) >= 8:
            break
    hay_all = " ".join(r["filename"] + " " + r["category"] for r in refs).lower()
    image_led = any(k in hay_all for k in ("render", "exterior", "architecture", "aerial"))
    return {
        "whitespace": "generous" if "brand" in hay_all or "logo" in hay_all else "balanced",
        "image_text_balance": "image_dominant" if image_led else "editorial",
        "logo_hierarchy": "project_primary",
        "overlay": "localized_readable",
        "composition_language": "architectural_editorial",
        "color": "light_type_on_dark_field",
        "architectural_presentation": "hero_photograph",
        "info_hierarchy": "headline_then_place",
        "project_name": name_l,
        "references": refs[:6],
    }


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
