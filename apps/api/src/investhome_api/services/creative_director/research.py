"""Drive / RAG research + real asset lock for Creative Director."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.project import Project
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.gpt_image_design.source import TEMPLE_PRIMARY_LOGO_ID, prefer_project_logo
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
        }


def _candidate_map(
    candidates: list[SocialDesignMediaCandidate],
) -> dict[UUID, SocialDesignMediaCandidate]:
    return {c.asset_id: c for c in candidates}


def _to_selected(cand: SocialDesignMediaCandidate, *, role: str) -> SelectedAsset:
    return SelectedAsset(
        asset_id=str(cand.asset_id),
        filename=cand.filename,
        content_type=cand.content_type,
        folder_category=cand.folder_category,
        visual_subject=cand.visual_subject,
        tags=list(cand.tags or []),
        role=role,
        provenance_source=cand.provenance_source,
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


def pick_real_interior(
    candidates: list[SocialDesignMediaCandidate],
) -> SocialDesignMediaCandidate | None:
    """PROJECT MODE: real Temple interior only — never AI-invented substitute."""
    interiors = [c for c in candidates if _is_interior(c) and not _is_exterior_primary(c)]
    if interiors:
        picked_id = pick_best_asset(interiors, require_image=True, campaign_type="LIFESTYLE")
        by_id = _candidate_map(interiors)
        if picked_id and picked_id in by_id:
            return by_id[picked_id]
        return interiors[0]
    # Explicit: do not fall back to exterior when brief asked for interiors.
    return None


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
) -> DriveResearchPackage:
    """Research Drive/RAG + lock real interior + logo. No image generation."""
    warnings: list[str] = []
    linked_project_id = project.id
    search_queries = [
        brief,
        f"{project.project_name} interior living lobby",
        f"{project.project_name} logo brand",
        f"{project.project_name} unit price list inventory",
    ]
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

    candidates = list_media_candidates(
        db,
        linked_project_id=linked_project_id,
        instruction=brief,
        limit=32,
        preference_tokens=asset_preference_tokens("interior"),
        campaign_type="LIFESTYLE",
    )

    selected_interior = None
    selected_logo = None
    if mode == "project":
        interior_cand = pick_real_interior(candidates)
        if interior_cand is None:
            warnings.append(
                "No real project interior asset found in Drive/Media Library. "
                "PROJECT MODE will not invent or substitute an exterior/AI image."
            )
        else:
            selected_interior = _to_selected(interior_cand, role="hero_interior")
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
                "summary": "Selected real interior asset",
                "excerpt": "",
                "score": 1.0,
                "role": "selected_interior",
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
    )
