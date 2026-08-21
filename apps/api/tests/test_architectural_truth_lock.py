"""Architectural Truth Lock — unit tests."""

from __future__ import annotations

from uuid import uuid4

from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_director.production_brief import (
    build_production_brief,
    render_finished_ad_production_prompt,
)
from investhome_api.services.creative_director.quality_lock.architecture_truth import (
    annotate_asset_truth,
    architecture_truth_guard,
    classify_architecture_asset,
    pick_truthful_hero_for_intent,
)
from investhome_api.services.creative_director.quality_lock.design_direction import (
    build_design_direction,
)


def _cand(
    *,
    filename: str,
    subject: str,
    tags: list[str] | None = None,
    score: float = 5.0,
) -> SocialDesignMediaCandidate:
    return SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename=filename,
        content_type="image/jpeg",
        folder_id=None,
        folder_category="02_RENDER",
        tags=tags or [],
        score=score,
        linked_project_id=uuid4(),
        visual_subject=subject,
        source_type="google_drive",
        provenance_source="google_drive",
    )


def test_classify_exterior_historic_plus_addition() -> None:
    cl = classify_architecture_asset(
        filename="IH_TMP_Historic_Plus_Addition_Street_01.jpeg",
        visual_subject="EXTERIOR",
        folder_category="02_RENDER",
        tags=["historic", "addition"],
    )
    assert cl == "EXTERIOR_HISTORIC_PLUS_ADDITION"


def test_classify_interior_approved() -> None:
    cl = classify_architecture_asset(
        filename="IH_TMP_Living_Room_01.jpeg",
        visual_subject="INTERIOR",
        folder_category="06_MEDIA",
    )
    assert cl == "INTERIOR_APPROVED"


def test_annotate_sets_freedom_levels() -> None:
    exterior = annotate_asset_truth(
        {
            "asset_id": str(uuid4()),
            "filename": "facade.jpeg",
            "visual_subject": "EXTERIOR",
            "provenance_source": "google_drive",
        }
    )
    assert exterior["architecture_locked"] is True
    assert exterior["creative_freedom_level"] == 0
    assert exterior["classification"] == "EXTERIOR_APPROVED"

    interior = annotate_asset_truth(
        {
            "asset_id": str(uuid4()),
            "filename": "living.jpeg",
            "visual_subject": "INTERIOR",
            "provenance_source": "google_drive",
        }
    )
    assert interior["creative_freedom_level"] == 1


def test_location_prefers_approved_exterior_not_invented() -> None:
    exterior = _cand(filename="project_exterior.jpeg", subject="EXTERIOR", score=8.0)
    interior = _cand(filename="living.jpeg", subject="INTERIOR", score=9.0)
    picked, reason, report = pick_truthful_hero_for_intent(
        [interior, exterior],
        campaign_intent="location",
    )
    assert picked is not None
    assert picked.asset_id == exterior.asset_id
    assert report["status"] == "pass"
    assert "approved_exterior" in (reason or "")


def test_historic_plus_addition_fail_closed_when_missing() -> None:
    interior = _cand(filename="living.jpeg", subject="INTERIOR")
    exterior = _cand(filename="generic_street.jpeg", subject="EXTERIOR")
    picked, _reason, report = pick_truthful_hero_for_intent(
        [interior, exterior],
        campaign_intent="architecture",
        require_historic_plus_addition=True,
    )
    assert picked is None
    assert report["fail_closed"] is True
    assert "Historic+Addition" in (report.get("message") or "")


def test_architecture_truth_guard_pass_for_locked_interior() -> None:
    aid = str(uuid4())
    meta = {
        "asset_id": aid,
        "filename": "living.jpeg",
        "visual_subject": "INTERIOR",
        "provenance_source": "google_drive",
    }
    guard = architecture_truth_guard(
        hero_meta=meta,
        source_asset_id=aid,
        campaign_intent="lifestyle",
    )
    assert guard["fail_closed"] is False
    assert guard["status"] == "pass"
    assert guard["classification"] == "INTERIOR_APPROVED"
    assert guard["architecture_locked"] is True
    assert guard["creative_freedom_level"] == 1


def test_architecture_truth_guard_fail_closed_historic_missing() -> None:
    aid = str(uuid4())
    meta = {
        "asset_id": aid,
        "filename": "living.jpeg",
        "visual_subject": "INTERIOR",
        "provenance_source": "google_drive",
    }
    guard = architecture_truth_guard(
        hero_meta=meta,
        source_asset_id=aid,
        campaign_intent="architecture",
        require_historic_plus_addition=True,
    )
    assert guard["fail_closed"] is True
    assert "historic_addition_missing_or_invented" in guard["failures"]


def test_production_brief_includes_architecture_truth() -> None:
    aid = str(uuid4())
    interior = {
        "asset_id": aid,
        "filename": "living.jpeg",
        "visual_subject": "INTERIOR",
        "role": "hero_interior",
        "provenance_source": "google_drive",
    }
    logo = {
        "asset_id": str(uuid4()),
        "filename": "logo.svg",
        "role": "project_logo",
    }
    brief = build_production_brief(
        ctx={"selected_assets": [interior], "campaign_intent": "lifestyle"},
        strategy={"objective": "awareness", "tone": "premium"},
        campaign_copy={"hero_message": "Zamansız Yaşam", "cta": "Detayları İncele"},
        pricing={},
        texts={
            "headline": "Zamansız Yaşam",
            "cta": "Detayları İncele",
            "eyebrow": "",
            "supporting": "",
        },
        approved_claims=[],
        blocked_claims=[],
        interior_meta=interior,
        logo_meta=logo,
        language="tr",
        aspect_ratio="4:5",
        format_preset="portrait",
        campaign_intent="lifestyle",
    )
    lock = brief["asset_lock"]
    assert lock["classification"] == "INTERIOR_APPROVED"
    assert lock["architecture_locked"] is True
    assert lock["creative_freedom_level"] == 1
    assert brief["architecture_truth"]["asset_id"] == aid

    prompt = render_finished_ad_production_prompt(
        production_brief=brief,
        art_direction={},
        original_brief="lifestyle interior",
        lifestyle=True,
    )
    assert "ARCHITECTURAL TRUTH LOCK" in prompt
    assert "LEVEL 1 CONTROLLED" in prompt


def test_design_direction_level_0_strict() -> None:
    d = build_design_direction(
        campaign_intent="architecture",
        language="tr",
        creative_freedom_level=0,
    )
    assert "LEVEL 0 STRICT" in d.creative_freedom
    assert "NEVER regenerate" in d.creative_freedom
