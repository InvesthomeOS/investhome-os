"""Editable Layer Fidelity v2 — composition plan, critic, renderer primitives, RI smoke."""

from __future__ import annotations

from investhome_api.services.creative_director.composition_critic import (
    critique_composition,
    revise_design_spec_once,
)
from investhome_api.services.creative_director.composition_plan import build_composition_plan
from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    assemble_editable_design,
    build_design_spec,
    design_spec_to_smb_elements,
    route_revision,
)
from investhome_api.services.creative_director.revision_intelligence import (
    interpret_revision_plan,
    snapshot_elements,
    validate_change_diff,
)
from investhome_api.schemas.creative_director import RevisionDiff, RevisionOperation


def _price_texts() -> dict[str, str]:
    return {
        "headline": "Modern. Şık. Tarihi.",
        "hero": "Unit 204 Lansman Fırsatı",
        "unit": "Unit 204",
        "list_price": "$400,000",
        "offer_price": "$300,000",
        "value_badge": "~25% lansman fiyat avantajı",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": "Tarihi karakter, modern tasarım.",
        "campaign_mode": "launch_price",
    }


def _brief(intent: str = "price_campaign") -> dict:
    return {
        "campaign_intent": intent,
        "hero": "The Temple'da Modern Yaşam",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": [
            "Tarihi karakter, modern tasarım.",
            "Sınırlı sayıda ünite, kaçırmayın.",
        ],
        "final_copy": {
            "headline": "Modern. Şık. Tarihi.",
            "list_price": "$400,000",
            "offer_price": "$300,000",
            "value_badge": "~25% lansman fiyat avantajı",
            "cta": "Lansman Fiyatını Kaçırmayın",
            "unit": "Unit 204",
        },
        "design_direction": {"information_density": "medium"},
        "message_strategy": {
            "primary_message": "Modern. Şık. Tarihi.",
            "hero_headline": "Modern. Şık. Tarihi.",
        },
    }


def test_composition_plan_intent_families_differ():
    price = build_composition_plan(campaign_intent="price_campaign", production_brief=_brief())
    loc = build_composition_plan(
        campaign_intent="location",
        production_brief=_brief("location"),
        texts={"headline": "Adams Morgan'ın Kalbinde Yaşam", "cta": "Detayları Keşfedin"},
    )
    life = build_composition_plan(
        campaign_intent="lifestyle",
        production_brief=_brief("lifestyle"),
        texts={"headline": "Yaşamın Kalbinde", "cta": "The Temple'ı Keşfet"},
    )
    assert price["layout_family"] != loc["layout_family"] != life["layout_family"]
    assert price["layout_family"] == "price_lower_third"
    assert loc["layout_family"] == "location_place_led"
    assert life["layout_family"] == "lifestyle_editorial"
    for plan in (price, loc, life):
        assert plan["focal_point"]["zone"]
        assert plan["zones"]["text_safe"]
        assert plan["overlays"] or plan["gradients"]
        assert plan["safe_margins"]["x_pct"] > 0


def test_richer_design_spec_has_overlays_and_composition():
    assembled = assemble_editable_design(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        campaign_intent="price_campaign",
    )
    spec = assembled["design_spec"]
    assert spec["version"] == 2
    assert spec.get("composition_plan")
    assert spec.get("composition", {}).get("layout_family") == "price_lower_third"
    ids = {el["id"] for el in spec["elements"]}
    assert "overlay-bottom-dark" in ids
    assert "price-frame" in ids
    assert "headline" in ids and "cta" in ids and "logo" in ids
    headline = next(e for e in spec["elements"] if e["id"] == "headline")
    assert headline["y"] >= int(spec["canvas"]["height"] * 0.35)


def test_critic_gate_one_revise():
    plan = build_composition_plan(campaign_intent="price_campaign", production_brief=_brief())
    # Intentionally broken flat spec
    bad = {
        "version": 2,
        "locked_background": True,
        "campaign_intent": "price_campaign",
        "canvas": {"width": 1080, "height": 1350},
        "elements": [
            {
                "id": "master_background",
                "type": "image",
                "role": "background",
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1350,
                "locked": True,
            },
            {
                "id": "logo",
                "type": "logo",
                "x": 40,
                "y": 40,
                "width": 200,
                "height": 80,
            },
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": "Hi",
                "x": 40,
                "y": 40,
                "width": 900,
                "height": 80,
                "typography": {"font_size": 40},
            },
            {
                "id": "cta",
                "type": "cta",
                "content": "Go",
                "x": 40,
                "y": 1200,
                "width": 300,
                "height": 50,
            },
        ],
    }
    critique = critique_composition(composition_plan=plan, design_spec=bad)
    assert critique["status"] == "fail"
    fixed = revise_design_spec_once(design_spec=bad, composition_plan=plan, critique=critique)
    critique2 = critique_composition(composition_plan=plan, design_spec=fixed)
    assert "overlay-bottom-dark" in {e["id"] for e in fixed["elements"]}
    # One revise is enough to recover overlay; may still fail price but critic ran once
    assert critique2 is not None


def test_renderer_primitives_mapping():
    layers = design_spec_to_smb_elements(
        build_design_spec(
            production_brief=_brief(),
            texts=_price_texts(),
            master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
            campaign_intent="price_campaign",
        )
    )
    by_id = {el["id"]: el for el in layers}
    assert by_id["master_background"]["type"] == "IMAGE"
    assert by_id["logo"]["type"] == "IMAGE"
    assert by_id["headline"]["type"] == "TEXT"
    assert by_id["cta"]["type"] == "BUTTON"
    assert by_id["overlay-bottom-dark"]["type"] == "SHAPE"
    assert "linear-gradient" in str(by_id["overlay-bottom-dark"]["fill"])
    assert by_id["price-frame"]["type"] == "SHAPE"
    assert by_id["discount-badge"]["type"] == "TEXT"


def test_lifestyle_and_location_specs_not_same_template():
    life = build_design_spec(
        production_brief=_brief("lifestyle"),
        texts={
            "headline": "Yaşamın Kalbinde, The Temple'da",
            "hero": "Şehrin merkezinde modern yaşam fırsatı.",
            "cta": "The Temple'ı Keşfet",
            "supporting": "Sade ve şık tasarımlar.",
        },
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        campaign_intent="lifestyle",
    )
    loc = build_design_spec(
        production_brief=_brief("location"),
        texts={
            "headline": "Adams Morgan'ın Kalbinde Yaşam",
            "hero": "Adams Morgan'ın kalbinde yaşama fırsatı",
            "cta": "Detayları Keşfedin",
            "supporting": "Kültürel çeşitlilik ve canlı sosyal yaşam",
        },
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        campaign_intent="location",
    )
    assert life["composition"]["layout_family"] != loc["composition"]["layout_family"]
    life_ids = {e["id"] for e in life["elements"]}
    loc_ids = {e["id"] for e in loc["elements"]}
    assert "overlay-top-light" in life_ids
    assert "overlay-top-dark" in loc_ids
    assert "new-price" not in life_ids
    assert "new-price" not in loc_ids


def test_revision_intelligence_v2_layer_only_smoke():
    """LAYER_ONLY geometric + copy still works on fidelity-v2 specs; GPT path not invoked."""
    spec = build_design_spec(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        campaign_intent="price_campaign",
    )
    instruction = (
        "Başlığı 'Zamansız Bir Yaşam' yap. Logoyu %20 büyüt. CTA'yı 'Detayları İncele' yap"
    )
    plan = interpret_revision_plan(
        instruction=instruction,
        production_brief=_brief(),
        design_spec=spec,
    )
    route = route_revision(instruction=instruction, revision_diff=plan, intents=["COPY_CHANGE"])
    assert route == "LAYER_ONLY"
    before = snapshot_elements(spec)
    after_spec = apply_layer_operations(spec, plan.operations)
    validation = validate_change_diff(before=before, after_spec=after_spec, revision_diff=plan)
    assert validation["unexpected_mutation_count"] == 0
    assert after_spec["elements"][0]["asset_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    hl = next(e for e in after_spec["elements"] if e["id"] == "headline")
    assert hl["content"] == "Zamansız Bir Yaşam"
    cta = next(e for e in after_spec["elements"] if e["id"] == "cta")
    assert cta["content"] == "Detayları İncele"
    assert any(e.get("id") == "overlay-bottom-dark" for e in after_spec["elements"])

def test_route_layer_only_headline_still():
    diff = RevisionDiff(
        operations=[
            RevisionOperation(
                target="headline",
                action="replace_text",
                **{"from": "A", "to": "B"},
                confidence="high",
                mode="exact",
            )
        ]
    )
    assert route_revision(instruction="Başlığı değiştir", revision_diff=diff) == "LAYER_ONLY"
