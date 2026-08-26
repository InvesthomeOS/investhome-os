"""Revision Engine v2 — editable commercial layers, no PRICE_BLOCK pixel fallback."""

from __future__ import annotations

from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    build_design_spec,
    design_spec_to_smb_elements,
    route_revision,
)
from investhome_api.services.creative_director.price_block_revision import (
    is_baked_price_ad,
    parse_price_block,
)
from investhome_api.services.creative_director.generate_ad import (
    adapt_final_turkish_texts,
    extract_labeled_brief_copy,
    is_lifestyle_campaign,
)
from investhome_api.services.creative_director.pricing import (
    build_pricing_claims,
    extract_unit_codes,
)
from investhome_api.services.creative_director.revision_intelligence import interpret_revision_plan

BRIEF = (
    "The Temple için premium bir lansman reklamı hazırla. "
    "2+1 dairenin liste fiyatı 675.000 USD. "
    "Lansmana özel %35 avantajı ve alırken kazanma fırsatını vurgula."
)

INSTRUCTION = (
    "675.000 USD liste fiyatının üzerini çiz.\n"
    "Lansman fiyatını 438.750 USD yap.\n"
    "Altına Kazancınız 236.250 USD yaz.\n"
    "Tasarımın geri kalan hiçbir şeyini değiştirme."
)


def _v2_spec():
    return build_design_spec(
        production_brief={
            "campaign_intent": "price_campaign",
            "hero": "The Temple Lansmanı",
            "cta": "Detayları İncele",
            "supporting": ["Alırken kazanma fırsatı.", "Lansmana özel avantaj."],
            "final_copy": {
                "headline": "The Temple Lansmanı",
                "list_price": "675.000 USD",
                "value_badge": "%35",
                "cta": "Detayları İncele",
                "unit": "2+1",
            },
        },
        texts={
            "headline": "The Temple Lansmanı",
            "hero": "Lansmana özel avantaj",
            "unit": "2+1",
            "list_price": "675.000 USD",
            "offer_price": "",
            "value_badge": "%35",
            "cta": "Detayları İncele",
            "supporting": "Alırken kazanma fırsatı",
            "campaign_mode": "launch_price",
        },
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        finished_ad_raster_asset_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        campaign_intent="price_campaign",
        revision_engine_v2=True,
    )


GOLDEN_MASTER_BRIEF = """THE TEMPLE — LAUNCH OFFER
The Temple için premium bir lansman reklamı hazırla.
Ana fikir:
ALIRKEN KAZAN
2+1 daire liste fiyatı:
675.000 USD
Lansman avantajı:
%35
Mesaj:
The Temple'da yerinizi lansman döneminde alın.
CTA:
PROJEYİ KEŞFET
Use the real approved The Temple visual and real The Temple logo."""


def test_pricing_extracts_tr_list_and_percent() -> None:
    claims = build_pricing_claims(brief=BRIEF)
    assert claims["list_price"] == 675000.0
    assert claims["launch_price"] is None
    assert claims["discount"]["display"] == "%35"
    assert claims["price_presentation"]["list"]
    assert extract_unit_codes(BRIEF) == ["2+1"]
    assert extract_unit_codes("2+1 dairenin liste fiyatı 675.000 USD") == ["2+1"]
    assert "204" in extract_unit_codes("The Temple Unit 204 lansman")


def test_golden_master_brief_copy_is_literal() -> None:
    labeled = extract_labeled_brief_copy(GOLDEN_MASTER_BRIEF)
    assert labeled["headline"] == "ALIRKEN KAZAN"
    assert labeled["cta"] == "PROJEYİ KEŞFET"
    assert labeled["unit"] == "2+1"
    assert "lansman döneminde" in labeled["supporting"]
    claims = build_pricing_claims(brief=GOLDEN_MASTER_BRIEF)
    assert claims["list_price"] == 675000.0
    assert claims["launch_price"] is None
    assert claims["discount"]["display"] == "%35"
    assert claims["claims"][0]["display"] == "2+1"
    assert is_lifestyle_campaign(
        ctx={"campaign_intent": "general_awareness"},
        pricing=claims,
        original_brief=GOLDEN_MASTER_BRIEF,
    ) is False
    texts = adapt_final_turkish_texts(
        language="tr",
        strategy={},
        campaign_copy={"cta": "Explore Details"},
        pricing=claims,
        approved_claims=claims["claims"],
        original_brief=GOLDEN_MASTER_BRIEF,
        lifestyle=False,
    )
    assert texts["headline"] == "ALIRKEN KAZAN"
    assert texts["cta"] == "PROJEYİ KEŞFET"
    assert texts["unit"] == "2+1"
    assert "675" in texts["list_price"]
    assert texts["offer_price"] == ""
    assert "%35" in texts["value_badge"]


def test_v2_initial_layers_list_price_unstruck_hidden_offer() -> None:
    spec = _v2_spec()
    by_id = {el["id"]: el for el in spec["elements"]}
    assert spec.get("revision_engine_v2") is True
    assert by_id["old-price"]["content"] == "675.000 USD"
    assert by_id["old-price"].get("visible") is not False
    assert (by_id["old-price"].get("typography") or {}).get("text_decoration") != "line-through"
    assert by_id["new-price"].get("visible") is False
    assert by_id["savings-price"].get("visible") is False
    assert by_id["discount-badge"]["content"] == "%35"
    assert "logo" in by_id
    assert "cta" in by_id
    smb = design_spec_to_smb_elements(spec)
    smb_ids = {el["id"] for el in smb}
    assert "old-price" in smb_ids
    assert "new-price" not in smb_ids
    assert "savings-price" not in smb_ids
    assert "discount-badge" in smb_ids
    assert "logo" in smb_ids
    assert "cta" in smb_ids


def test_v2_price_revision_is_layer_only() -> None:
    spec = _v2_spec()
    intent = parse_price_block(INSTRUCTION)
    assert intent is not None
    after = apply_layer_operations(spec, intent.operations())
    by_id = {el["id"]: el for el in after["elements"]}
    assert by_id["old-price"]["content"] == "675.000 USD"
    assert (by_id["old-price"].get("typography") or {}).get("text_decoration") == "line-through"
    assert by_id["new-price"]["visible"] is True
    assert by_id["new-price"]["content"] == "438.750 USD"
    assert by_id["savings-price"]["visible"] is True
    assert "236.250" in by_id["savings-price"]["content"]
    assert "old-price-strikethrough" in by_id
    smb = design_spec_to_smb_elements(after)
    contents = " ".join(str(el.get("content") or el.get("label") or "") for el in smb)
    assert "675.000 USD" in contents
    assert "438.750 USD" in contents
    assert "236.250" in contents


def test_v2_not_baked_and_price_stays_micro_edit() -> None:
    spec = _v2_spec()
    ctx = {
        "revision_engine_v2": True,
        "visual_foundation_asset_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "production_mode": "editable_finished_ad",
        "editable_finished_ad": True,
        "design_spec": spec,
        "structured_design_data": {"elements": spec["elements"]},
    }
    assert is_baked_price_ad(ctx) is False
    plan = interpret_revision_plan(instruction=INSTRUCTION, design_spec=spec)
    route = route_revision(
        instruction=INSTRUCTION,
        revision_diff=plan,
        has_structured_design=True,
    )
    assert route == "MICRO_EDIT"
    assert "headline" in plan.preserve
