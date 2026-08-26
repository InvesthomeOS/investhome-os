"""Drive / RAG research + real asset lock for Creative Director."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import or_, select

from investhome_api.models.project import Project
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.gpt_image_design.source import (
    TEMPLE_PRIMARY_LOGO_ID,
    find_global_investhome_logo,
    prefer_project_logo,
)
from investhome_api.services.creative_director.quality_lock.architecture_truth import (
    APPROVED_EXTERIOR_OPTIONS,
    annotate_asset_truth,
    classify_candidate,
    creative_freedom_level_for,
    is_workspace_screenshot,
    pick_truthful_hero_for_intent,
)
from investhome_api.services.creative_director.quality_lock.asset_scoring import (
    pick_hero_asset_for_intent,
    selection_role_for_intent,
)
from investhome_api.services.creative_director.quality_lock.intent import intent_to_asset_preference
from investhome_api.services.social_design_engine.generation import asset_preference_tokens
from investhome_api.services.social_design_engine.media import (
    list_media_candidates,
    pick_best_asset,
    pick_logo_asset,
)


@dataclass
class ResearchHit:
    asset_id: str | None
    document_id: str | None
    file: str | None
    category: str | None
    source: str | None
    summary: str | None
    excerpt: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SelectedAsset:
    asset_id: str
    filename: str
    content_type: str | None
    folder_category: str | None
    visual_subject: str | None
    tags: list[str] = field(default_factory=list)
    role: str = "hero"
    provenance_source: str | None = None
    selection_score: float | None = None
    selection_reason: str | None = None
    classification: str | None = None
    architecture_locked: bool | None = None
    creative_freedom_level: int | None = None
    project_relation: str = "project_primary"
    approved: bool | None = None
    approved_status: str | None = None
    selection_trace: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        relation = self.project_relation or "project_primary"
        annotated = annotate_asset_truth(raw, project_relation=relation)
        if str(self.role or "") in {"city_visual", "investhome_logo", "brand_logo"}:
            annotated["project_relation"] = "brand_independent"
        if self.selection_trace:
            annotated["selection_trace"] = dict(self.selection_trace)
        return annotated


@dataclass
class DriveResearchPackage:
    project_id: str
    project_name: str
    mode: str
    hits: list[ResearchHit]
    media_candidates: list[SocialDesignMediaCandidate]
    selected_interior: SelectedAsset | None
    selected_logo: SelectedAsset | None
    drive_sources: list[dict[str, Any]]
    unit_mentions: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    architecture_truth: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "mode": self.mode,
            "hits": [h.to_dict() for h in self.hits],
            "selected_interior": self.selected_interior.to_dict() if self.selected_interior else None,
            "selected_logo": self.selected_logo.to_dict() if self.selected_logo else None,
            "drive_sources": list(self.drive_sources),
            "unit_mentions": list(self.unit_mentions),
            "warnings": list(self.warnings),
            "media_candidate_count": len(self.media_candidates),
            "architecture_truth": self.architecture_truth,
        }


def _candidate_map(
    candidates: list[SocialDesignMediaCandidate],
) -> dict[UUID, SocialDesignMediaCandidate]:
    return {c.asset_id: c for c in candidates}


def _to_selected(
    cand: SocialDesignMediaCandidate,
    *,
    role: str,
    selection_score: float | None = None,
    selection_reason: str | None = None,
    project_relation: str | None = None,
    selection_trace: dict[str, Any] | None = None,
) -> SelectedAsset:
    classification = classify_candidate(cand, role=role)
    relation = project_relation or "project_primary"
    annotated = annotate_asset_truth(
        {
            "asset_id": str(cand.asset_id),
            "filename": cand.filename,
            "folder_category": cand.folder_category,
            "visual_subject": cand.visual_subject,
            "tags": list(cand.tags or []),
            "role": role,
            "provenance_source": cand.provenance_source,
            "classification": classification,
        },
        project_relation=relation,
    )
    return SelectedAsset(
        asset_id=str(cand.asset_id),
        filename=cand.filename,
        content_type=cand.content_type,
        folder_category=cand.folder_category,
        visual_subject=cand.visual_subject,
        tags=list(cand.tags or []),
        role=role,
        provenance_source=cand.provenance_source,
        selection_score=selection_score,
        selection_reason=selection_reason,
        classification=str(annotated.get("classification") or classification),
        architecture_locked=bool(annotated.get("architecture_locked")),
        creative_freedom_level=int(
            annotated.get("creative_freedom_level")
            if annotated.get("creative_freedom_level") is not None
            else creative_freedom_level_for(classification)
        ),
        project_relation=str(annotated.get("project_relation") or relation),
        approved=bool(annotated.get("approved")),
        approved_status=str(annotated.get("approved_status") or "unapproved"),
        selection_trace=selection_trace,
    )


def _is_interior(cand: SocialDesignMediaCandidate) -> bool:
    subject = (cand.visual_subject or "").upper()
    if subject == "INTERIOR":
        return True
    hay = " ".join(
        [cand.filename or "", cand.folder_category or "", " ".join(cand.tags or [])]
    ).lower()
    return any(k in hay for k in ("interior", "living", "bedroom", "kitchen", "bathroom", "lobby", "suite"))


def _is_exterior_primary(cand: SocialDesignMediaCandidate) -> bool:
    subject = (cand.visual_subject or "").upper()
    return subject in {"EXTERIOR", "AERIAL", "NEIGHBORHOOD", "LOCATION"}


_CITY_VISUAL_TOKENS = (
    "washington",
    " dc",
    "d.c",
    "skyline",
    "capitol",
    "adams",
    "morgan",
    "neighborhood",
    "location",
    "streetscape",
    "street",
    "city",
    "sehir",
    "şehir",
    "district",
    "veiw",
)
_CITY_EXCLUDE_TOKENS = (
    "chapel",
    "temple",
    "tmp_001",
    "ideogram",
    "gpt-image",
    "provider:ideogram",
    "living",
    "bedroom",
    "kitchen",
    "bathroom",
    "interior",
    "addition",
)


def _city_visual_trust(
    cand: SocialDesignMediaCandidate,
    *,
    classification: str,
) -> tuple[int, str]:
    """Lower tier number = higher trust. Unclassified is last fallback, never treated as approved."""
    hay = _haystack(cand)
    provenance = f"{cand.provenance_source or ''} {cand.source_type or ''}".lower()
    drive_or_ml = any(tok in provenance for tok in ("drive", "media_library", "upload", "google"))
    subject = (cand.visual_subject or "").upper()
    folder = (cand.folder_category or "").upper()
    classified_place = classification in {"LOCATION", "NEIGHBORHOOD"} or subject in {
        "LOCATION",
        "NEIGHBORHOOD",
    }
    folder_loc = "05_LOCATION" in folder or folder in {"LOCATION", "NEIGHBORHOOD"}
    generative = any(tok in hay for tok in ("ideogram", "gpt-image", "provider:ideogram", "provider:gpt-image"))
    if classification == "UNCLASSIFIED":
        return 4, "unclassified_fallback"
    if classified_place and folder_loc and drive_or_ml and not generative:
        return 1, "approved_company_or_location"
    if classified_place and drive_or_ml and not generative:
        return 2, "verified_media_library_location"
    if classified_place and not generative:
        return 3, "approved_external_or_provider_city"
    return 4, "unclassified_fallback"


def pick_city_visual(
    candidates: list[SocialDesignMediaCandidate],
    *,
    brief: str = "",
) -> tuple[SocialDesignMediaCandidate | None, float | None, str | None, dict[str, Any] | None]:
    """Brand/market hero: place imagery, never project interior or locked architecture."""
    brief_l = (brief or "").lower()
    scored: list[tuple[int, float, str, dict[str, Any], SocialDesignMediaCandidate]] = []
    for cand in candidates:
        ctype = (cand.content_type or "").lower()
        if not ctype.startswith("image/") or ctype == "image/svg+xml":
            continue
        if _is_interior(cand):
            continue
        classification = classify_candidate(cand)
        if classification in APPROVED_EXTERIOR_OPTIONS:
            continue
        if classification == "INTERIOR_APPROVED" or classification == "FLOORPLAN":
            continue
        if classification.startswith("LOGO"):
            continue
        hay = _haystack(cand)
        if any(tok in hay for tok in _CITY_EXCLUDE_TOKENS):
            continue
        if any(tok in hay for tok in ("screencapture", "localhost", "ai-chat")):
            continue
        subject = (cand.visual_subject or "").upper()
        folder = (cand.folder_category or "").upper()
        place_subject = subject in {"LOCATION", "NEIGHBORHOOD"} or classification in {
            "LOCATION",
            "NEIGHBORHOOD",
        }
        token_hit = any(tok in hay for tok in _CITY_VISUAL_TOKENS)
        folder_hit = "05_LOCATION" in folder or folder in {"LOCATION", "NEIGHBORHOOD"}
        if not (place_subject or token_hit or folder_hit):
            continue
        score = float(cand.score or 0.0)
        reasons: list[str] = ["city_place_visual"]
        if subject in {"LOCATION", "NEIGHBORHOOD"} or classification in {"LOCATION", "NEIGHBORHOOD"}:
            score += 8.0
            reasons.append("place_subject")
        if any(tok in hay for tok in ("washington", "skyline", "capitol")):
            score += 10.0
            reasons.append("washington_dc")
        if "adams" in hay or "morgan" in hay:
            score += 4.0
            reasons.append("neighborhood")
        if folder_hit:
            score += 3.0
            reasons.append("location_folder")
        if "washington" in brief_l and any(tok in hay for tok in ("washington", "dc", "adams")):
            score += 3.0
            reasons.append("brief_place_fit")
        tier, trust_label = _city_visual_trust(cand, classification=classification)
        if tier == 4:
            score -= 20.0
            reasons.append("unclassified_last_fallback")
        else:
            reasons.append(trust_label)
        approved = classification not in {"UNCLASSIFIED", "FLOORPLAN"} and tier < 4
        trace = {
            "asset_id": str(cand.asset_id),
            "source": cand.provenance_source or cand.source_type,
            "approval_status": "approved" if approved else "unapproved",
            "visual_role": "city_visual",
            "trust_tier": tier,
            "trust_label": trust_label,
            "classification": classification,
            "filename": cand.filename,
        }
        scored.append((tier, score, "+".join(reasons), trace, cand))
    if not scored:
        return None, None, None, None
    scored.sort(key=lambda row: (row[0], -row[1]))
    best = scored[0]
    return best[4], best[1], best[2], best[3]


# Room / subject weights for campaign hero interiors (filename alone is not enough).
_ROOM_WEIGHTS: tuple[tuple[tuple[str, ...], float], ...] = (
    (("living", "lounge", "great.?room", "oturma", "salon"), 8.0),
    (("lobby", "lobby.?lounge", "reception", "atrium"), 7.0),
    (("kitchen", "mutfak", "dining"), 6.0),
    (("suite", "master", "bedroom", "yatak"), 3.5),
    (("bathroom", "bath", "banyo"), 1.0),
    (("corridor", "hallway", "closet", "detail"), 0.5),
)


def _haystack(cand: SocialDesignMediaCandidate) -> str:
    return " ".join(
        [
            cand.filename or "",
            cand.folder_category or "",
            cand.visual_subject or "",
            " ".join(cand.tags or []),
        ]
    ).lower()


def score_interior_candidate(
    cand: SocialDesignMediaCandidate,
    *,
    brief: str = "",
    width: int | None = None,
    height: int | None = None,
) -> tuple[float, str]:
    """Score real interiors for ad hero use — not first-match / not filename-only.

    Signals: quality proxies, resolution, composition/negative-space potential,
    text-placement potential, character fit, brief fit. Base media score is a
    component, never the sole criterion.
    """
    reasons: list[str] = []
    score = 0.0
    hay = _haystack(cand)
    brief_l = (brief or "").lower()

    # Base retrieval score (includes some preference overlap) — capped influence.
    base = float(cand.score or 0.0)
    score += min(base, 12.0) * 0.35
    reasons.append(f"base_media={base:.2f}")

    # Quality / mime
    ctype = (cand.content_type or "").lower()
    if ctype in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
        score += 3.0
        reasons.append("photo_render")
    elif ctype == "image/svg+xml":
        score -= 20.0
        reasons.append("svg_penalty")

    # Resolution
    w = width
    h = height
    if w and h and w > 0 and h > 0:
        area = int(w) * int(h)
        if area >= 2_000_000:
            score += 5.0
            reasons.append("hi_res")
        elif area >= 1_000_000:
            score += 3.5
            reasons.append("good_res")
        elif area >= 400_000:
            score += 2.0
            reasons.append("ok_res")
        else:
            score -= 1.5
            reasons.append("low_res")
        # Composition / text-placement: prefer landscape or near-square with width room.
        aspect = w / h
        if 1.15 <= aspect <= 1.9:
            score += 3.0
            reasons.append("landscape_text_space")
        elif 0.85 <= aspect <= 1.15:
            score += 2.0
            reasons.append("square_editorial")
        elif aspect < 0.7:
            score -= 1.0
            reasons.append("tall_tight")
        # Negative-space proxy: wider frames leave more copy room.
        if w >= 1600:
            score += 1.0

    # Room / subject character (not filename-only — tags + subject + category too)
    room_bonus = 0.0
    room_label = "interior"
    for keys, weight in _ROOM_WEIGHTS:
        if any(re.search(k, hay) for k in keys):
            room_bonus = weight
            room_label = keys[0]
            break
    else:
        if (cand.visual_subject or "").upper() == "INTERIOR":
            room_bonus = 4.0
            room_label = "interior_generic"
    score += room_bonus
    reasons.append(f"room={room_label}:{room_bonus}")

    # Brief fit — living/character campaigns prefer living/lobby over bedroom detail.
    wants_character = any(
        k in brief_l for k in ("tarihi", "historic", "modern", "şık", "sik", "karakter", "character", "elegant")
    )
    wants_interior = any(k in brief_l for k in ("interior", "iç", "ic mekan", "görsel", "gorsel"))
    if wants_character or wants_interior:
        if room_label in {"living", "lobby", "kitchen"}:
            score += 4.0
            reasons.append("brief_character_fit")
        elif room_label in {"suite", "bedroom"}:
            score -= 1.5
            reasons.append("bedroom_secondary_for_character")

    # Prefer living-space tokens in brief explicitly.
    for token in ("living", "lobby", "salon", "oturma", "kitchen", "mutfak"):
        if token in brief_l and token in hay:
            score += 2.0
            reasons.append(f"brief_token:{token}")
            break

    # Provenance: real Drive/media preferred.
    prov = (cand.provenance_source or cand.source_type or "").lower()
    if "drive" in prov or "google" in prov:
        score += 1.5
        reasons.append("drive_provenance")

    # Mild filename sequence preference only as tie-breaker component (not sole criterion).
    seq = re.search(r"_(\d{2,3})\.", cand.filename or "")
    if seq:
        # Mid-sequence often better lit hero frames than 001 thumbnails.
        n = int(seq.group(1))
        if 3 <= n <= 20:
            score += 0.4
            reasons.append("mid_sequence")

    reason = "; ".join(reasons)
    return score, reason


def pick_real_interior(
    candidates: list[SocialDesignMediaCandidate],
    *,
    brief: str = "",
    dimensions: dict[UUID, tuple[int | None, int | None]] | None = None,
) -> tuple[SocialDesignMediaCandidate | None, float | None, str | None]:
    """PROJECT MODE: real project interior only — never AI-invented substitute.

    Scores among interiors; does not return the first match or filename sort alone.
    """
    interiors = [
        c
        for c in candidates
        if _is_interior(c)
        and not _is_exterior_primary(c)
        and not is_workspace_screenshot(_haystack(c))
    ]
    if not interiors:
        return None, None, None

    dims = dimensions or {}
    ranked: list[tuple[float, str, SocialDesignMediaCandidate]] = []
    for cand in interiors:
        ctype = (cand.content_type or "").lower()
        if ctype == "image/svg+xml":
            continue
        if not ctype.startswith("image/"):
            continue
        w, h = dims.get(cand.asset_id, (None, None))
        s, reason = score_interior_candidate(cand, brief=brief, width=w, height=h)
        ranked.append((s, reason, cand))

    if not ranked:
        # Last resort: still never exterior; use prior pick_best among interiors.
        picked_id = pick_best_asset(interiors, require_image=True, campaign_type="LIFESTYLE")
        by_id = _candidate_map(interiors)
        if picked_id and picked_id in by_id:
            return by_id[picked_id], None, "fallback_pick_best_asset"
        return None, None, None

    ranked.sort(key=lambda row: (-row[0], (row[2].filename or "").lower()))
    best_score, best_reason, best = ranked[0]
    return best, best_score, best_reason


def pick_real_logo(
    candidates: list[SocialDesignMediaCandidate],
    *,
    project_name: str | None,
    project_code: str | None,
    db: Session | None = None,
) -> SocialDesignMediaCandidate | None:
    logo = prefer_project_logo(
        candidates,
        project_name=project_name,
        project_code=project_code,
        preferred_asset_id=TEMPLE_PRIMARY_LOGO_ID,
    )
    if logo is not None:
        return logo
    # Preferred Temple Primary may exist in DB but not ranked candidates.
    if db is not None:
        from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset

        preferred = db.get(CreativeStudioMediaAsset, TEMPLE_PRIMARY_LOGO_ID)
        if preferred is not None and preferred.archived_at is None:
            linked = preferred.linked_project_id
            if linked is None and candidates:
                linked = candidates[0].linked_project_id
            if linked is None:
                return None
            return SocialDesignMediaCandidate(
                asset_id=preferred.id,
                filename=preferred.filename,
                content_type=preferred.content_type,
                folder_id=preferred.folder_id,
                folder_category=preferred.folder_category,
                tags=[str(t) for t in (preferred.tags or [])] if isinstance(preferred.tags, list) else [],
                score=99.0,
                linked_project_id=linked,
                visual_subject="BRANDING",
                source_type=preferred.source_type,
                provenance_source="google_drive"
                if (preferred.source_type or "") == "google_drive"
                else (preferred.storage_provider or "unknown"),
            )
    return pick_logo_asset(candidates, project_name=project_name, project_code=project_code)


def _unit_mentions_from_hits(hits: list[ResearchHit], unit_codes: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for code in unit_codes:
        pattern = re.compile(rf"\bunit\s*{re.escape(code)}\b", re.I)
        matched = [h for h in hits if pattern.search(h.excerpt or "") or pattern.search(h.summary or "")]
        out.append(
            {
                "unit_code": code,
                "found_in_drive": bool(matched),
                "hit_count": len(matched),
                "excerpts": [
                    {"file": h.file, "excerpt": (h.excerpt or "")[:240], "score": h.score}
                    for h in matched[:3]
                ],
            }
        )
    return out


def research_project_drive(
    db: Session,
    *,
    project: Project,
    brief: str,
    mode: str = "project",
    unit_codes: list[str] | None = None,
    retrieval_limit: int = 12,
    campaign_intent: str | None = None,
    recent_asset_ids: list[str] | None = None,
    ad_scope: str = "project",
    visual_kind: str | None = None,
) -> DriveResearchPackage:
    """Research Drive/RAG + lock real hero visual + logo. No image generation."""
    warnings: list[str] = []
    linked_project_id = project.id
    intent = (campaign_intent or "").strip().lower() or None
    scope = (ad_scope or "project").strip().lower() or "project"
    kind = (visual_kind or "unspecified").strip().lower() or "unspecified"
    search_queries = [
        brief,
        f"{project.project_name} interior living lobby",
        f"{project.project_name} exterior facade neighborhood",
        f"{project.project_name} logo brand",
        f"{project.project_name} unit price list inventory",
    ]
    if scope == "brand":
        search_queries = [
            brief,
            "Washington DC skyline neighborhood street location",
            "Adams Morgan location neighborhood street",
            "Investhome brand logo",
        ]
    elif intent == "location":
        search_queries.insert(1, f"{project.project_name} Adams Morgan location neighborhood street")
    for code in unit_codes or []:
        search_queries.append(f"{project.project_name} Unit {code} price")

    hits: list[ResearchHit] = []
    seen_keys: set[str] = set()
    for query in search_queries:
        try:
            rows = hybrid_search(
                db,
                query=query,
                project_scope="single",
                project_id=linked_project_id,
                project_ids=None,
                limit=retrieval_limit,
                builder=None,
            )
        except ProjectScopeError as exc:
            warnings.append(str(exc))
            continue
        for h in rows:
            key = f"{getattr(h, 'document_id', None)}:{getattr(h, 'chunk_id', None)}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            if getattr(h, "project_id", None) and h.project_id != linked_project_id:
                continue
            hits.append(
                ResearchHit(
                    asset_id=str(h.asset_id) if getattr(h, "asset_id", None) else None,
                    document_id=str(h.document_id) if getattr(h, "document_id", None) else None,
                    file=getattr(h, "file", None),
                    category=getattr(h, "category", None),
                    source=getattr(h, "source", None),
                    summary=getattr(h, "summary", None),
                    excerpt=(getattr(h, "chunk_text", None) or "")[:500],
                    score=float(getattr(h, "score", 0) or 0),
                )
            )

    pref = "neighborhood" if scope == "brand" else intent_to_asset_preference(intent or "lifestyle")
    if scope == "brand":
        from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
        from investhome_api.services.gpt_image_design.source import _candidate_from_asset

        brand_rows = list(
            db.scalars(
                select(CreativeStudioMediaAsset).where(
                    CreativeStudioMediaAsset.archived_at.is_(None),
                    CreativeStudioMediaAsset.content_type.ilike("image/%"),
                    or_(
                        CreativeStudioMediaAsset.linked_project_id == linked_project_id,
                        CreativeStudioMediaAsset.linked_project_id.is_(None),
                    ),
                ).limit(500)
            ).all()
        )
        candidates = []
        for row in brand_rows:
            if (row.content_type or "").lower() == "image/svg+xml":
                continue
            candidates.append(_candidate_from_asset(db, row))
    else:
        candidates = list_media_candidates(
            db,
            linked_project_id=linked_project_id,
            instruction=brief,
            limit=32,
            preference_tokens=asset_preference_tokens(pref),
            campaign_type="LIFESTYLE",
        )

    selected_interior = None
    selected_logo = None
    truth_report: dict[str, Any] | None = None
    if scope == "brand":
        city_cand, city_score, city_reason, city_trace = pick_city_visual(candidates, brief=brief)
        if city_cand is None:
            warnings.append(
                "No Washington DC / city place visual found in Drive/Media Library. "
                "Brand/market ads will not substitute a project interior or architecture render."
            )
        else:
            if city_trace and city_trace.get("trust_tier") == 4:
                warnings.append(
                    "City visual is UNCLASSIFIED/unapproved last fallback — not treated as an approved asset."
                )
            selected_interior = _to_selected(
                city_cand,
                role="city_visual",
                selection_score=city_score,
                selection_reason=city_reason,
                project_relation="brand_independent",
                selection_trace=city_trace,
            )
            truth_report = {
                "intent": intent or "investment",
                "status": "brand_place_visual",
                "fail_closed": False,
                "message": "Brand/market ad — locked place imagery, not project architecture.",
                "project_relation": "brand_independent",
                "asset_trace": city_trace,
                "selected": {
                    "asset_id": str(city_cand.asset_id),
                    "filename": city_cand.filename,
                    "pool": "city_visual",
                    "approval_status": (city_trace or {}).get("approval_status"),
                    "visual_role": "city_visual",
                    "source": (city_trace or {}).get("source"),
                },
            }
        logo_cand = find_global_investhome_logo(db)
        if logo_cand is None:
            warnings.append(
                "Approved Investhome logo not found. Will not invent a logo or fake brand mark."
            )
        else:
            selected_logo = _to_selected(
                logo_cand,
                role="investhome_logo",
                project_relation="brand_independent",
            )
    elif mode == "project":
        dims: dict[UUID, tuple[int | None, int | None]] = {}
        dim_ids = [c.asset_id for c in candidates]
        if dim_ids:
            from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset

            for row in db.scalars(
                select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.id.in_(dim_ids))
            ).all():
                dims[row.id] = (row.width, row.height)

        recent_set = {str(x) for x in (recent_asset_ids or []) if str(x).strip()}
        brief_l = (brief or "").lower()
        require_hpa = any(
            k in brief_l
            for k in (
                "historic+addition",
                "historic + addition",
                "historic and addition",
                "tarihi+addition",
                "historic plus addition",
                "historic_plus_addition",
            )
        )
        hero_cand = None
        hero_score: float | None = None
        hero_reason: str | None = None
        role = "hero"
        if intent in {"location", "architecture", "project_brand", "investment"} or require_hpa:
            truth_cand, truth_reason, truth_report = pick_truthful_hero_for_intent(
                candidates,
                campaign_intent=intent or "location",
                require_historic_plus_addition=require_hpa,
            )
            if truth_report.get("fail_closed"):
                warnings.append(str(truth_report.get("message") or truth_reason))
                warnings.append("architectural_truth_fail_closed")
                hero_cand = None
                hero_reason = truth_reason
                role = selection_role_for_intent(intent or "architecture")
                # Brand-language briefs ("logo", "reklam") classify as project_brand
                # and the exterior pool fail-closes even when approved interiors exist.
                # Historic+Addition stays fail-closed. Social ads may use a real interior.
                if not require_hpa and intent == "project_brand":
                    hero_cand, hero_score, hero_reason = pick_real_interior(
                        candidates,
                        brief=brief,
                        dimensions=dims,
                    )
                    if hero_cand is not None:
                        role = "hero_interior"
                        warnings.append("project_brand_interior_fallback")
                        truth_report = {
                            **truth_report,
                            "fail_closed": False,
                            "status": "pass_interior_fallback",
                            "message": (
                                "project_brand exterior pool miss; locked approved interior"
                            ),
                            "selected": {
                                "asset_id": str(hero_cand.asset_id),
                                "filename": hero_cand.filename,
                                "pool": "interior_fallback",
                            },
                        }
            elif truth_cand is not None:
                hero_cand = truth_cand
                hero_score = float(truth_cand.score or 0.0)
                hero_reason = truth_reason
                role = selection_role_for_intent(intent or "location")
            elif intent:
                # Soft miss only — never after Historic+Addition fail-closed
                hero_cand, hero_score, hero_reason = pick_hero_asset_for_intent(
                    candidates,
                    campaign_intent=intent,
                    brief=brief,
                    dimensions=dims,
                    recent_asset_ids=recent_set,
                )
                role = selection_role_for_intent(intent)
            else:
                hero_cand, hero_score, hero_reason = pick_real_interior(
                    candidates,
                    brief=brief,
                    dimensions=dims,
                )
                role = "hero_interior"
        elif intent:
            hero_cand, hero_score, hero_reason = pick_hero_asset_for_intent(
                candidates,
                campaign_intent=intent,
                brief=brief,
                dimensions=dims,
                recent_asset_ids=recent_set,
            )
            role = selection_role_for_intent(intent)
        else:
            hero_cand, hero_score, hero_reason = pick_real_interior(
                candidates,
                brief=brief,
                dimensions=dims,
            )
            role = "hero_interior"

        if kind == "exterior" and hero_cand is not None and _is_interior(hero_cand):
            ext_cand, ext_reason, ext_report = pick_truthful_hero_for_intent(
                candidates,
                campaign_intent="architecture",
                require_historic_plus_addition=require_hpa,
            )
            if ext_cand is not None:
                hero_cand = ext_cand
                hero_score = float(ext_cand.score or 0.0)
                hero_reason = ext_reason or "user_requested_exterior"
                role = "hero_exterior"
                truth_report = ext_report
            else:
                warnings.append(
                    "User requested exterior (dış cephe); no approved exterior found. "
                    "Will not substitute an interior."
                )
                hero_cand = None
                truth_report = ext_report
        elif kind == "interior" and hero_cand is not None and not _is_interior(hero_cand):
            int_cand, int_score, int_reason = pick_real_interior(
                candidates,
                brief=brief,
                dimensions=dims,
            )
            if int_cand is not None:
                hero_cand = int_cand
                hero_score = int_score
                hero_reason = int_reason or "user_requested_interior"
                role = "hero_interior"
            else:
                warnings.append(
                    "User requested interior; no real interior found. "
                    "Will not substitute an exterior."
                )
                hero_cand = None

        if hero_cand is None:
            warnings.append(
                "No real project hero asset found in Drive/Media Library. "
                "PROJECT MODE will not invent or substitute an AI image. "
                "Fake architecture fallback FORBIDDEN."
            )
        else:
            selected_interior = _to_selected(
                hero_cand,
                role=role,
                selection_score=hero_score,
                selection_reason=hero_reason,
            )
        logo_cand = pick_real_logo(
            candidates,
            project_name=project.project_name,
            project_code=project.project_code,
            db=db,
        )
        if logo_cand is None:
            warnings.append("No real project logo asset found. Will not AI-draw a logo.")
        else:
            selected_logo = _to_selected(logo_cand, role="project_logo")

    drive_sources: list[dict[str, Any]] = []
    for h in hits[:24]:
        drive_sources.append(
            {
                "file": h.file,
                "category": h.category,
                "source": h.source,
                "asset_id": h.asset_id,
                "summary": h.summary,
                "excerpt": h.excerpt[:200],
                "score": h.score,
            }
        )
    # Also surface selected media as sources.
    if selected_interior:
        drive_sources.insert(
            0,
            {
                "file": selected_interior.filename,
                "category": selected_interior.folder_category,
                "source": selected_interior.provenance_source or "media_library",
                "asset_id": selected_interior.asset_id,
                "summary": (
                    "Selected city/place visual"
                    if selected_interior.role == "city_visual"
                    else "Selected real project hero asset"
                ),
                "excerpt": "",
                "score": 1.0,
                "role": selected_interior.role or "selected_hero",
                "selection_score": selected_interior.selection_score,
                "selection_reason": selected_interior.selection_reason,
                "classification": selected_interior.classification,
                "architecture_locked": selected_interior.architecture_locked,
                "creative_freedom_level": selected_interior.creative_freedom_level,
            },
        )
    if selected_logo:
        drive_sources.insert(
            0 if not selected_interior else 1,
            {
                "file": selected_logo.filename,
                "category": selected_logo.folder_category,
                "source": selected_logo.provenance_source or "media_library",
                "asset_id": selected_logo.asset_id,
                "summary": (
                    "Selected approved Investhome logo"
                    if selected_logo.role == "investhome_logo"
                    else "Selected real project logo"
                ),
                "excerpt": "",
                "score": 1.0,
                "role": "selected_logo",
                "classification": selected_logo.classification,
            },
        )

    return DriveResearchPackage(
        project_id=str(project.id),
        project_name=project.project_name,
        mode=mode,
        hits=hits,
        media_candidates=candidates,
        selected_interior=selected_interior,
        selected_logo=selected_logo,
        drive_sources=drive_sources,
        unit_mentions=_unit_mentions_from_hits(hits, unit_codes or []),
        warnings=warnings,
        architecture_truth=truth_report,
    )


def select_visual_replace_source(
    db: Session,
    *,
    project: Project,
    instruction: str,
    exclude_asset_ids: set[str] | None = None,
    logo_asset_id: str | None = None,
) -> tuple[SelectedAsset | None, dict[str, Any]]:
    """Pick an approved project exterior via existing Drive research. No second asset system."""
    skip = {str(x).strip() for x in (exclude_asset_ids or set()) if str(x).strip()}
    if logo_asset_id:
        skip.add(str(logo_asset_id))
    pkg = research_project_drive(
        db,
        project=project,
        brief=instruction,
        mode="project",
        campaign_intent="architecture",
        visual_kind="exterior",
        recent_asset_ids=list(skip),
        ad_scope="project",
    )
    skip_uuids: set[UUID] = set()
    for raw_id in skip:
        try:
            skip_uuids.add(UUID(raw_id))
        except (TypeError, ValueError):
            continue
    pool = list(pkg.media_candidates or [])
    seen = {str(c.asset_id) for c in pool}
    extra = list_media_candidates(
        db,
        linked_project_id=project.id,
        instruction=instruction,
        limit=80,
        exclude_asset_ids=skip_uuids,
    )
    for cand in extra:
        aid = str(cand.asset_id)
        if aid not in seen:
            seen.add(aid)
            pool.append(cand)
    candidates: list[Any] = []
    candidate_trace: list[dict[str, Any]] = []
    for cand in pool:
        aid = str(cand.asset_id)
        if aid in skip:
            continue
        classification = classify_candidate(cand)
        if classification.startswith("LOGO") or classification == "FLOORPLAN":
            continue
        hay = " ".join(
            [
                str(cand.filename or ""),
                str(cand.folder_category or ""),
                str(cand.visual_subject or ""),
                " ".join(cand.tags or []),
            ]
        ).lower()
        if any(tok in hay for tok in ("gpt-image", "ideogram", "provider:gpt-image")):
            continue
        exterior = classification in APPROVED_EXTERIOR_OPTIONS or (
            "exterior" in hay and not _is_interior(cand)
        )
        if not exterior:
            continue
        candidates.append(cand)
        candidate_trace.append(
            {
                "asset_id": aid,
                "filename": cand.filename,
                "folder": cand.folder_category,
                "role": cand.visual_subject or classification,
                "approval_status": "approved" if classification in APPROVED_EXTERIOR_OPTIONS else "unapproved",
                "source": cand.provenance_source,
                "score": float(cand.score or 0.0),
                "classification": classification,
            }
        )

    selected = pkg.selected_interior
    if selected is not None and str(selected.asset_id) in skip:
        selected = None
    if selected is not None and selected.classification not in APPROVED_EXTERIOR_OPTIONS:
        selected = None
    truth: dict[str, Any] | None = pkg.architecture_truth
    if selected is None and candidates:
        ext_cand, ext_reason, ext_report = pick_truthful_hero_for_intent(
            candidates,
            campaign_intent="architecture",
        )
        truth = ext_report
        if ext_cand is not None and str(ext_cand.asset_id) not in skip:
            selected = _to_selected(
                ext_cand,
                role="hero_exterior",
                selection_score=float(ext_cand.score or 0.0),
                selection_reason=ext_reason or "user_requested_exterior",
                selection_trace=ext_report,
            )

    if selected is not None and (
        str(selected.asset_id) in skip
        or (selected.classification or "") not in APPROVED_EXTERIOR_OPTIONS
    ):
        selected = None

    report = {
        "project_id": str(project.id),
        "candidates": candidate_trace,
        "selected": selected.to_dict() if selected else None,
        "warnings": list(pkg.warnings or []),
        "architecture_truth": truth,
        "excluded_asset_ids": sorted(skip),
    }
    return selected, report
