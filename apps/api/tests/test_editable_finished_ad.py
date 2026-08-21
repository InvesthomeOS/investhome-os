"""Unit tests for editable finished-ad Design Spec + revision router (GPT=0 layer path)."""

from __future__ import annotations

from investhome_api.schemas.creative_director import RevisionDiff, RevisionOperation
from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    build_design_spec,
    design_spec_to_smb_elements,
    route_revision,
)


def _price_texts() -> dict[str, str]:
    return {
        "headline": "Modern. Şık. Tarihi.",
        "hero": "The Temple'da Modern Yaşam, Tarihi Doku ile Buluşuyor!",
        "unit": "Unit 204",
        "list_price": "$400,000",
        "offer_price": "$300,000",
        "value_badge": "~25% lansman fiyat avantajı",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": "Unit 204 Lansman Fırsatı",
        "campaign_mode": "launch_price",
    }


def _brief() -> dict:
    return {
        "campaign_intent": "price_campaign",
        "hero": "The Temple'da Modern Yaşam, Tarihi Doku ile Buluşuyor!",
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
    }


REQUIRED_LAYER_IDS = {
    "master_background",
    "logo",
    "headline",
    "subheadline",
    "unit-label",
    "old-price",
    "new-price",
    "discount-badge",
    "support-message-1",
    "support-message-2",
    "cta",
}


def test_build_design_spec_has_required_price_layers():
    spec = build_design_spec(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        finished_ad_raster_asset_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="price_campaign",
    )
    ids = {el["id"] for el in spec["elements"]}
    assert REQUIRED_LAYER_IDS <= ids
    assert spec["master_background_asset_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert spec["mode"] == "editable_finished_ad"
    bg = next(el for el in spec["elements"] if el["id"] == "master_background")
    assert bg["locked"] is True
    assert bg["editable"] is False
    logo = next(el for el in spec["elements"] if el["id"] == "logo")
    assert logo["lock_aspect_ratio"] is True
    assert logo["asset_id"] == "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def test_design_spec_to_smb_elements_maps_types():
    spec = build_design_spec(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    layers = design_spec_to_smb_elements(spec)
    types = {el["id"]: el["type"] for el in layers}
    assert types["master_background"] == "IMAGE"
    assert types["logo"] == "IMAGE"
    assert types["headline"] == "TEXT"
    assert types["cta"] == "BUTTON"
    assert types["discount-badge"] == "TEXT"
    assert types["overlay-bottom-dark"] == "SHAPE"


def test_route_layer_only_for_headline_cta_badge_logo():
    cases = [
        (
            "Başlığı 'Zamansız Bir Yaşam' yap",
            RevisionDiff(
                operations=[
                    RevisionOperation(
                        target="headline",
                        action="replace_text",
                        **{"from": "Modern. Şık. Tarihi.", "to": "Zamansız Bir Yaşam"},
                        confidence="high",
                        mode="exact",
                    )
                ]
            ),
        ),
        (
            "%25 rozetini %30 küçült",
            RevisionDiff(
                operations=[
                    RevisionOperation(
                        target="badge",
                        action="scale",
                        scale_factor=0.7,
                        confidence="high",
                        mode="exact",
                    )
                ]
            ),
        ),
        (
            "CTA'yı 'Detayları İncele' yap",
            RevisionDiff(
                operations=[
                    RevisionOperation(
                        target="cta",
                        action="replace_text",
                        **{"to": "Detayları İncele"},
                        confidence="high",
                        mode="exact",
                    )
                ]
            ),
        ),
        (
            "Logoyu %20 küçült",
            RevisionDiff(
                operations=[
                    RevisionOperation(
                        target="logo",
                        action="scale",
                        scale_factor=0.8,
                        confidence="high",
                        mode="exact",
                    )
                ]
            ),
        ),
    ]
    for instruction, diff in cases:
        assert (
            route_revision(instruction=instruction, revision_diff=diff, intents=["COPY_CHANGE"])
            == "LAYER_ONLY"
        ), instruction


def test_route_image_required_for_interior_change():
    assert (
        route_revision(
            instruction="başka interior kullan, koltuğu değiştir",
            revision_diff=RevisionDiff(operations=[]),
            intents=["ASSET_CHANGE", "VISUAL_CHANGE"],
        )
        == "IMAGE_REQUIRED"
    )


def test_apply_layer_ops_abcd_gpt_zero():
    """Acceptance A–D: layer mutations without inventing new creative."""
    spec = build_design_spec(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    badge_before = next(el for el in spec["elements"] if el["id"] == "discount-badge")
    logo_before = next(el for el in spec["elements"] if el["id"] == "logo")
    bw, bh = badge_before["width"], badge_before["height"]
    lw, lh = logo_before["width"], logo_before["height"]

    ops = [
        RevisionOperation(
            target="headline",
            action="replace_text",
            **{"to": "Zamansız Bir Yaşam"},
            confidence="high",
            mode="exact",
        ),
        RevisionOperation(
            target="badge",
            action="scale",
            scale_factor=0.7,
            confidence="high",
            mode="exact",
        ),
        RevisionOperation(
            target="cta",
            action="replace_text",
            **{"to": "Detayları İncele"},
            confidence="high",
            mode="exact",
        ),
        RevisionOperation(
            target="logo",
            action="scale",
            scale_factor=0.8,
            confidence="high",
            mode="exact",
        ),
    ]
    next_spec = apply_layer_operations(spec, ops)
    by_id = {el["id"]: el for el in next_spec["elements"]}
    assert by_id["headline"]["content"] == "Zamansız Bir Yaşam"
    assert by_id["cta"]["content"] == "Detayları İncele"
    assert abs(by_id["discount-badge"]["width"] - bw * 0.7) <= 1
    assert abs(by_id["discount-badge"]["height"] - bh * 0.7) <= 1
    assert abs(by_id["logo"]["width"] - lw * 0.8) <= 1
    assert abs(by_id["logo"]["height"] - lh * 0.8) <= 1
    # Background immutable
    assert by_id["master_background"]["asset_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert by_id["master_background"]["locked"] is True


def test_layer_edit_preserves_spec_roundtrip_ids():
    spec = build_design_spec(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    )
    edited = apply_layer_operations(
        spec,
        [
            RevisionOperation(
                target="headline",
                action="replace_text",
                **{"to": "Zamansız Bir Yaşam"},
                confidence="high",
                mode="exact",
            )
        ],
    )
    layers = design_spec_to_smb_elements(edited)
    assert any(el["id"] == "headline" and el.get("content") == "Zamansız Bir Yaşam" for el in layers)
    assert any(el["id"] == "master_background" for el in layers)
