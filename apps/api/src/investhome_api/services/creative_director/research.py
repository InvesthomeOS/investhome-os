"""Drive / RAG research + real asset lock for Creative Director."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select

from investhome_api.models.project import Project
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.gpt_image_design.source import TEMPLE_PRIMARY_LOGO_ID, prefer_project_logo
from investhome_api.services.creative_director.quality_lock.architecture_truth import (
    annotate_asset_truth,
    classify_candidate,
    creative_freedom_level_for,
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

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        return annotate_asset_truth(raw)


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
) -> SelectedAsset:
    classification = classify_candidate(cand, role=role)
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
        }
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
        project_relation=str(annotated.get("project_relation") or "project_primary"),
        approved=bool(annotated.get("approved")),
        approved_status=str(annotated.get("approved_status") or "unapproved"),
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
    interiors = [c for c in candidates if _is_interior(c) and not _is_exterior_primary(c)]
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
) -> DriveResearchPackage:
    """Research Drive/RAG + lock real hero visual + logo. No image generation."""
    warnings: list[str] = []
    linked_project_id = project.id
    intent = (campaign_intent or "").strip().lower() or None
    search_queries = [
        brief,
        f"{project.project_name} interior living lobby",
        f"{project.project_name} exterior facade neighborhood",
        f"{project.project_name} logo brand",
        f"{project.project_name} unit price list inventory",
    ]
    if intent == "location":
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

    pref = intent_to_asset_preference(intent or "lifestyle")
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
    if mode == "project":
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
                "summary": "Selected real project hero asset",
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
                "summary": "Selected real project logo",
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
