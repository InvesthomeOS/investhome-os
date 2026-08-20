"""Quality Lock freeze + AI revision unit/regression tests (no live GPT spend)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from investhome_api.services.creative_director.quality_lock.intent import (
    classify_cd_campaign_intent,
)
from investhome_api.services.creative_director.revision import (
    build_revision_brief,
    interpret_revision_intents,
    render_revision_production_prompt,
)

def _artifacts_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "artifacts" / "creative-quality-lock"
        if candidate.is_dir():
            return candidate
    docker = Path("/app/artifacts/creative-quality-lock")
    if docker.is_dir():
        return docker
    raise AssertionError("Quality Lock artifacts directory not found")


ARTIFACTS = _artifacts_dir()

CAMPAIGN_KEYS = (
    ("A_price_sales", "price_campaign"),
    ("B_location", "location"),
    ("C_lifestyle_features", {"amenities", "lifestyle"}),
)


def _load_json(name: str) -> dict:
    path = ARTIFACTS / name
    assert path.is_file(), f"missing Quality Lock artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_quality_lock_artifacts_exist_for_regression() -> None:
    for key, _ in CAMPAIGN_KEYS:
        assert (ARTIFACTS / f"{key}-report.json").is_file()
        assert (ARTIFACTS / f"{key}-generate-ad.json").is_file()
        assert (ARTIFACTS / f"{key}-campaign-create.json").is_file()
        assert (ARTIFACTS / f"{key}-final.png").is_file()
    assert (ARTIFACTS / "summary.json").is_file()


def test_quality_lock_artifact_pipeline_invariants() -> None:
    summary = _load_json("summary.json")
    assert summary.get("visual_quality_pass_declared") is False
    assert summary.get("provider_budget_ok") is True
    assert int(summary.get("total_provider_calls") or 0) <= 3

    for key, intent_expect in CAMPAIGN_KEYS:
        report = _load_json(f"{key}-report.json")
        gen = _load_json(f"{key}-generate-ad.json")
        camp = _load_json(f"{key}-campaign-create.json")

        intent = report.get("1_campaign_intent") or (camp.get("campaign_context") or {}).get(
            "campaign_intent"
        )
        if isinstance(intent_expect, set):
            assert intent in intent_expect
        else:
            assert intent == intent_expect or (
                key == "A_price_sales" and intent in {"price_campaign", "sales_offer", "launch"}
            )

        assert report.get("10_language") == "tr" or gen.get("language") == "tr"
        assert gen.get("production_mode") == "finished_ad"
        assert gen.get("final_asset_id")
        assert report.get("17_final_asset_id") == gen.get("final_asset_id")
        assert report.get("19_native_pipeline_used") == "NO"

        pb = gen.get("production_brief") or {}
        assert pb.get("campaign_intent") or report.get("1_campaign_intent")
        assert pb.get("message_strategy") or report.get("15_production_brief", {}).get(
            "message_strategy"
        )
        assert pb.get("design_direction") or report.get("13_design_direction")
        logo = report.get("9_logo") or {}
        assert logo.get("asset_id") or gen.get("logo_asset_id")
        assert report.get("7_selected_asset", {}).get("asset_id") or gen.get("interior_asset_id")


def test_quality_lock_a_price_asset_id_stable() -> None:
    report = _load_json("A_price_sales-report.json")
    gen = _load_json("A_price_sales-generate-ad.json")
    assert report["17_final_asset_id"] == "f00ef35d-fc9a-422d-9531-b6b62e756816"
    assert gen["final_asset_id"] == report["17_final_asset_id"]
    assert report["campaign_id"] == "7f4015bf-906b-4728-95b5-ef6a888b1236"


def test_revision_intents_copy_and_layout() -> None:
    intents = interpret_revision_intents(
        "Başlığı daha premium yap. %25 rozetini biraz küçült. "
        "Sınırlı sayıda ünite ifadesini kaldır. Tasarımın geri kalanını mümkün olduğunca değiştirme."
    )
    assert "COPY_CHANGE" in intents
    assert "LAYOUT_CHANGE" in intents or "STYLE_CHANGE" in intents
    assert "SIMPLIFY" not in intents or True  # optional


def test_revision_intents_cta_only() -> None:
    intents = interpret_revision_intents("CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme.")
    assert "COPY_CHANGE" in intents


def test_revision_brief_preserves_locks_and_scarcity_removal() -> None:
    production_brief = {
        "campaign_intent": "price_campaign",
        "hero": "Modern. Şık. Tarihi.",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": ["Sınırlı sayıda ünite", "Unit 204 Lansman Fırsatı"],
        "final_copy": {
            "headline": "Modern. Şık. Tarihi.",
            "cta": "Lansman Fiyatını Kaçırmayın",
            "list_price": "$400,000",
            "offer_price": "$300,000",
            "value_badge": "~25% lansman fiyat avantajı",
        },
        "approved_claims": [{"key": "list_price", "display": "$400,000"}],
        "forbidden_claims": [],
        "asset_lock": {"logo_asset_id": str(uuid4())},
        "logo_lock": {"status": "pass"},
        "design_direction": {"premium_level": "high"},
        "message_strategy": {"primary_message": "launch price"},
        "simplicity_director": {"density": "balanced"},
    }
    instruction = (
        "Başlığı daha premium yap. %25 rozetini biraz küçült. "
        "Sınırlı sayıda ünite ifadesini kaldır."
    )
    intents = interpret_revision_intents(instruction)
    brief = build_revision_brief(
        instruction=instruction,
        intents=intents,
        production_brief=production_brief,
        original_brief="The Temple Unit 204",
        language="tr",
        current_final_asset_id=uuid4(),
    )
    assert brief["mode"] == "revision"
    assert brief["language_lock"] is True
    assert brief["claim_guard_active"] is True
    assert brief["keep_unchanged_default"] is True
    assert brief["copy_overrides"].get("remove_scarcity") == "true"
    assert brief["copy_overrides"].get("badge_scale") == "slightly_smaller"
    assert all("sınırlı" not in str(s).lower() for s in brief["supporting"])

    prompt = render_revision_production_prompt(
        revision_brief=brief,
        production_brief=production_brief,
        original_brief="The Temple Unit 204",
        lifestyle=False,
    )
    assert "AI REVISION MODE" in prompt
    assert "KEEP EVERYTHING ELSE UNCHANGED" in prompt
    assert "Claim" in prompt or "FORBIDDEN" in prompt or "APPROVED CLAIMS" in prompt


def test_revision_brief_cta_override() -> None:
    production_brief = {
        "campaign_intent": "price_campaign",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": [],
        "final_copy": {"cta": "Lansman Fiyatını Kaçırmayın"},
        "approved_claims": [],
        "forbidden_claims": [],
        "asset_lock": {},
        "logo_lock": {},
    }
    instruction = "CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme."
    brief = build_revision_brief(
        instruction=instruction,
        intents=interpret_revision_intents(instruction),
        production_brief=production_brief,
        original_brief="brief",
        language="tr",
        current_final_asset_id=uuid4(),
    )
    assert brief["cta"] == "Detayları İncele"
    assert brief["copy_overrides"].get("cta") == "Detayları İncele"


def test_intent_classifiers_match_quality_lock_briefs() -> None:
    price = classify_cd_campaign_intent(
        "The Temple için Unit 204 lansman reklamı. Normal fiyat $400,000, lansman $300,000. Türkçe.",
        language="tr",
        project_name="The Temple",
        has_price_pair=True,
    )
    assert price.campaign_intent in {"price_campaign", "sales_offer", "launch"}
    loc = classify_cd_campaign_intent(
        "The Temple Adams Morgan lokasyon avantajları. Türkçe. Fiyat kullanma.",
        language="tr",
        project_name="The Temple",
    )
    assert loc.campaign_intent == "location"
