"""Creative orchestration cleanup — language lock, logo lock, simplicity, claim-guard."""

from __future__ import annotations

from uuid import uuid4

from investhome_api.services.creative_director.pricing import build_pricing_claims

BRIEF = (
    "The Temple projesinin gerçek interior görsellerini kullan. Unit 204 lansman kampanyası. "
    "Normal fiyat $400,000, lansman fiyatı $300,000. "
    "Modern, şık ve tarihi karakterini ön plana çıkar. "
)


def test_language_lock_tr_strips_english_from_production_brief() -> None:
    from investhome_api.services.creative_director.generate_ad import adapt_final_turkish_texts
    from investhome_api.services.creative_director.production_brief import (
        build_production_brief,
        looks_english_ad_copy,
        render_finished_ad_production_prompt,
    )

    pricing = build_pricing_claims(brief=BRIEF)
    strategy = {
        "big_idea": "History Meets Modernity",
        "hero_message": "Own a Piece of History with a Modern Twist",
        "sales_hook": "Unit 204 Launch Opportunity",
        "offer": "Exclusive launch pricing",
        "cta": "Explore Details",
        "supporting_messages": [
            "Historic character + modern living",
            "Discover the elegance of DC",
            "Schedule a viewing today",
            "Fourth leak should be dropped",
        ],
        "objective": "Unit launch",
    }
    campaign_copy = dict(strategy)
    texts = adapt_final_turkish_texts(
        language="tr",
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        approved_claims=pricing["claims"],
        original_brief=BRIEF,
    )
    for key in ("headline", "hero", "sales_hook", "cta", "supporting", "eyebrow"):
        assert not looks_english_ad_copy(texts.get(key)), f"{key} leaked English: {texts.get(key)}"
    assert texts["cta"] == "Detayları İncele"

    brief = build_production_brief(
        ctx={},
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        texts=texts,
        approved_claims=pricing["claims"],
        blocked_claims=[],
        interior_meta={"asset_id": str(uuid4()), "filename": "interior.jpg"},
        logo_meta={
            "asset_id": str(uuid4()),
            "filename": "logo.svg",
            "role": "project_logo",
        },
        language="tr",
        aspect_ratio="4:5",
        format_preset="portrait",
    )
    for key in ("big_idea", "hero", "sales_hook", "cta", "offer"):
        assert not looks_english_ad_copy(str(brief.get(key) or "")), f"brief.{key} leaked English"
    assert len(brief["supporting"]) <= 3
    assert all(not looks_english_ad_copy(m) for m in brief["supporting"])
    assert brief["final_copy"]["cta"] == "Detayları İncele"
    prompt = render_finished_ad_production_prompt(
        production_brief=brief,
        art_direction={},
        original_brief=BRIEF,
    )
    assert "LANGUAGE LOCK" in prompt
    assert "Explore Details" not in prompt
    assert "History Meets Modernity" not in prompt


def test_logo_lock_requires_verified_asset_id() -> None:
    from investhome_api.services.creative_director.production_brief import (
        build_production_brief,
        verify_logo_lock,
    )

    missing = verify_logo_lock({})
    assert missing["status"] == "fail"
    assert missing["ai_must_not_draw_logo"] is True
    assert missing["no_duplicate_logos"] is True

    logo_id = str(uuid4())
    ok = verify_logo_lock(
        {"asset_id": logo_id, "filename": "IH_DC_TMP_001_Logo_Primary.svg", "role": "project_logo"}
    )
    assert ok["status"] == "pass"
    assert ok["logo_locked"] is True
    assert ok["verified_project_logo"] is True
    assert ok["logo_asset_id"] == logo_id

    pricing = build_pricing_claims(brief=BRIEF)
    texts = {
        "headline": "Modern. Şık. Tarihi.",
        "hero": "Tarihi karakterle modern yaşam bir arada.",
        "sales_hook": "Unit 204 Lansman Fırsatı",
        "cta": "Detayları İncele",
        "offer": "$400,000 → $300,000",
        "eyebrow": "Unit 204 Lansman Fırsatı",
        "supporting": "Unit 204 Lansman Fırsatı",
        "campaign_mode": "launch_price",
    }
    brief = build_production_brief(
        ctx={},
        strategy={},
        campaign_copy={},
        pricing=pricing,
        texts=texts,
        approved_claims=[],
        blocked_claims=[],
        interior_meta={"asset_id": str(uuid4()), "filename": "interior.jpg"},
        logo_meta={
            "asset_id": logo_id,
            "filename": "IH_DC_TMP_001_Logo_Primary.svg",
            "role": "project_logo",
        },
        language="tr",
        aspect_ratio="4:5",
        format_preset="portrait",
    )
    assert brief["asset_lock"]["logo_asset_id"] == logo_id
    assert brief["asset_lock"]["logo_locked"] is True
    assert brief["asset_lock"]["ai_must_not_draw_logo"] is True
    assert brief["logo_lock"]["status"] == "pass"


def test_production_brief_includes_creative_simplicity_max_three_supporting() -> None:
    from investhome_api.services.creative_director.brief import _SYSTEM
    from investhome_api.services.creative_director.production_brief import (
        CREATIVE_SIMPLICITY_PRINCIPLES,
        build_production_brief,
        render_finished_ad_production_prompt,
    )

    assert "CREATIVE SIMPLICITY" in _SYSTEM

    pricing = build_pricing_claims(brief=BRIEF)
    texts = {
        "headline": "Modern. Şık. Tarihi.",
        "hero": "Tarihi karakterle modern yaşam bir arada.",
        "sales_hook": "Unit 204 Lansman Fırsatı",
        "cta": "Detayları İncele",
        "offer": "$400,000 → $300,000",
        "eyebrow": "Unit 204 Lansman Fırsatı",
        "supporting": "Unit 204 Lansman Fırsatı",
        "campaign_mode": "launch_price",
    }
    brief = build_production_brief(
        ctx={},
        strategy={
            "supporting_messages": [
                "Zarif tasarım detayları",
                "Şehir merkezinde sakin yaşam",
                "Gerçek proje interior görselleri",
                "Fazla dördüncü satır",
                "Beşinci satır da fazla",
            ]
        },
        campaign_copy={},
        pricing=pricing,
        texts=texts,
        approved_claims=[],
        blocked_claims=[],
        interior_meta={"asset_id": str(uuid4()), "filename": "interior.jpg"},
        logo_meta={"asset_id": str(uuid4()), "filename": "logo.svg", "role": "project_logo"},
        language="tr",
        aspect_ratio="4:5",
        format_preset="portrait",
    )
    assert brief["max_supporting_messages"] == 3
    assert len(brief["supporting"]) <= 3
    assert brief["creative_simplicity"] == list(CREATIVE_SIMPLICITY_PRINCIPLES)
    prompt = render_finished_ad_production_prompt(
        production_brief=brief,
        art_direction={},
        original_brief=BRIEF,
    )
    assert "CREATIVE SIMPLICITY" in prompt


def test_claim_guard_one_cikar_does_not_require_profit() -> None:
    from investhome_api.services.social_design_engine.campaign_intent import (
        classify_campaign_intent,
        detect_explicit_financial_requests,
    )
    from investhome_api.services.social_design_engine.verified_facts import (
        _infer_extracted_key,
        resolve_missing_facts,
    )

    for prompt in (
        "öne çıkar",
        "öne çıkarmak",
        "lokasyonu öne çıkaran premium Instagram postu",
        "Modern, şık ve tarihi karakterini ön plana çıkar.",
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium Instagram postu.",
    ):
        reqs = detect_explicit_financial_requests(prompt)
        assert not any(r.key == "profit" for r in reqs), f"false profit on: {prompt!r} -> {reqs}"
        intent = classify_campaign_intent(prompt, project_name="The Temple")
        assert not any(r.key == "profit" and r.required for r in intent.explicit_fact_requests)
        missing, ok, reason = resolve_missing_facts(
            intent=intent,
            knowledge=None,  # type: ignore[arg-type]
            selected=[],
            campaign_facts=[],
        )
        assert ok is True or not any(m.key == "profit" and m.required for m in missing)
        if reason:
            assert "Profit" not in reason

    assert _infer_extracted_key("öne çıkaran lokasyon notu") != "profit"
    assert _infer_extracted_key("projected profit $1.2M") == "profit"
    profit_reqs = detect_explicit_financial_requests("Projenin net kârını öne çıkar")
    assert any(r.key == "profit" and r.required for r in profit_reqs)
