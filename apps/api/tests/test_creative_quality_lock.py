"""Creative Director Quality Lock v1 — unit tests."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_director.quality_lock.asset_scoring import (
    pick_hero_asset_for_intent,
    score_candidate_for_intent,
)
from investhome_api.services.creative_director.quality_lock.intent import (
    classify_cd_campaign_intent,
)
from investhome_api.services.creative_director.quality_lock.self_critique import (
    critique_and_fix_production_brief,
    critique_production_brief,
)
from investhome_api.services.creative_director.quality_lock.simplicity import (
    apply_simplicity_caps,
    simplicity_caps_for_intent,
)


PRICE_BRIEF = (
    "The Temple için Unit 204 lansman reklamı hazırla. "
    "Normal fiyat $400,000, lansman fiyatı $300,000. "
    "Türkçe hazırla."
)

LOCATION_BRIEF = (
    "The Temple projesinin Adams Morgan lokasyon avantajlarını anlatan "
    "premium Instagram reklamı hazırla. Türkçe."
)

FEATURES_BRIEF = (
    "The Temple için sosyal medya reklamı hazırla. "
    "Projenin kataloğunu ve Drive'daki bilgileri incele. "
    "Projenin en güçlü özelliklerinden birkaçını seç ve bunları ön plana çıkar. "
    "Türkçe hazırla."
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


def test_classify_price_sales_intent() -> None:
    result = classify_cd_campaign_intent(
        PRICE_BRIEF,
        language="tr",
        project_name="The Temple",
        has_price_pair=True,
    )
    assert result.campaign_intent in {"price_campaign", "sales_offer", "launch"}
    assert result.language == "tr"


def test_classify_location_intent() -> None:
    result = classify_cd_campaign_intent(
        LOCATION_BRIEF,
        language="tr",
        project_name="The Temple",
    )
    assert result.campaign_intent == "location"
    assert result.asset_preference in {"neighborhood", "aerial", "exterior"}


def test_classify_amenities_lifestyle_intent() -> None:
    result = classify_cd_campaign_intent(
        FEATURES_BRIEF,
        language="tr",
        project_name="The Temple",
    )
    assert result.campaign_intent in {"amenities", "lifestyle"}


def test_asset_scoring_prefers_exterior_for_location() -> None:
    exterior = _cand(
        filename="IH_DC_TMP_001_Exterior_Street_01.jpeg",
        subject="EXTERIOR",
        tags=["exterior", "street", "neighborhood"],
        score=4.0,
    )
    interior = _cand(
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        subject="INTERIOR",
        tags=["interior", "living"],
        score=9.0,
    )
    ext_score, _ = score_candidate_for_intent(
        exterior, campaign_intent="location", brief=LOCATION_BRIEF, width=2000, height=1400
    )
    int_score, _ = score_candidate_for_intent(
        interior, campaign_intent="location", brief=LOCATION_BRIEF, width=2000, height=1400
    )
    assert ext_score > int_score
    picked, _, reason = pick_hero_asset_for_intent(
        [interior, exterior],
        campaign_intent="location",
        brief=LOCATION_BRIEF,
        dimensions={exterior.asset_id: (2000, 1400), interior.asset_id: (2000, 1400)},
    )
    assert picked is not None
    assert picked.asset_id == exterior.asset_id
    assert reason and "location" in reason


def test_asset_scoring_prefers_interior_for_lifestyle() -> None:
    exterior = _cand(
        filename="IH_DC_TMP_001_Exterior_01.jpeg",
        subject="EXTERIOR",
        tags=["exterior"],
        score=8.0,
    )
    living = _cand(
        filename="IH_DC_TMP_001_Render_Living_Room_003.jpeg",
        subject="INTERIOR",
        tags=["interior", "living"],
        score=5.0,
    )
    picked, _, _ = pick_hero_asset_for_intent(
        [exterior, living],
        campaign_intent="lifestyle",
        brief=FEATURES_BRIEF,
        dimensions={exterior.asset_id: (1800, 1200), living.asset_id: (1800, 1200)},
    )
    assert picked is not None
    assert picked.asset_id == living.asset_id


def test_simplicity_caps_by_intent() -> None:
    price_caps = simplicity_caps_for_intent("price_campaign")
    assert price_caps.max_headlines == 1
    assert price_caps.max_cta == 1
    assert price_caps.max_logos == 1
    assert price_caps.max_supporting <= 3
    assert price_caps.allow_price_block is True

    sparse = simplicity_caps_for_intent("location")
    applied = apply_simplicity_caps(
        supporting_messages=["a", "b", "c", "d"],
        caps=sparse,
    )
    assert len(applied["supporting_messages"]) <= sparse.max_supporting
    assert applied["element_budget"]["headline"] == 1
    assert applied["element_budget"]["cta"] == 1
    assert applied["element_budget"]["logo"] == 1


def test_self_critique_fixes_excess_supporting_and_english_leak() -> None:
    logo_id = str(uuid4())
    asset_id = str(uuid4())
    brief = {
        "campaign_intent": "lifestyle",
        "language": "tr",
        "big_idea": "History Meets Modernity",
        "hero": "Own a Piece of History with a Modern Twist",
        "sales_hook": "Explore Details Now",
        "cta": "",
        "supporting": ["one", "two", "three", "four", "five"],
        "final_copy": {"headline": "History Meets Modernity", "cta": "", "supporting": "x"},
        "asset_lock": {
            "interior_asset_id": asset_id,
            "logo_asset_id": logo_id,
        },
        "logo_lock": {"logo_asset_id": logo_id, "status": "pass"},
        "approved_claims": [],
        "forbidden_claims": [],
        "design_direction": {"premium_level": "high", "visual_mood": "quiet luxury"},
        "visual_direction": "premium",
    }
    critique = critique_production_brief(brief, campaign_intent="lifestyle")
    assert critique["status"] == "needs_fix"
    fixed, after = critique_and_fix_production_brief(brief, campaign_intent="lifestyle")
    assert after.get("fixed_once") is True
    caps = simplicity_caps_for_intent("lifestyle")
    assert len(fixed.get("supporting") or []) <= caps.max_supporting
    assert fixed.get("cta")
    assert fixed.get("self_critique")


def test_no_native_fallback_in_finished_ad_path() -> None:
    """Quality lock must not introduce silent native /social/design fallback."""
    import investhome_api.services.creative_director.generate_ad as gen_mod

    text = Path(gen_mod.__file__).read_text(encoding="utf-8")
    assert "createDefaultElements" not in text
    assert "PLACEHOLDER_HEADLINE" not in text
    assert "/social/design" not in text
    assert "critique_and_fix_production_brief" in text
    assert "finished_ad" in text
