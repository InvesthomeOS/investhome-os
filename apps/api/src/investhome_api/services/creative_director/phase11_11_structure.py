"""ReferenceDesignStructureV1 — relative DNA only. No pixel imitation."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.phase11_11_select import (
    SELECTED_FILENAME,
    SELECTED_MEDIA_ID,
    SELECTED_REFERENCE_ID,
    WHY_SELECTED,
)

SCHEMA = "ReferenceDesignStructureV1"

# Relative relationships observed from ORNEK_00013, not that file's pixel grid.
RELATIVE = {
    "hero_visual_mass_width": 0.48,
    "hero_visual_mass_height": 0.62,
    "hero_left_inset": 0.00,
    "hero_bottom_inset": 0.02,
    "type_column_width": 0.40,
    "type_right_inset": 0.07,
    "type_top": 0.12,
    "offer_size_vs_canvas_height": 0.109,
    "price_vs_offer": 0.22,
    "unit_vs_offer": 0.12,
    "cta_vs_offer": 0.16,
    "identity_vs_offer": 0.22,
    "logo_inset": 0.055,
    "commercial_group_rhythm": 0.036,
    "void_before_logo": 0.18,
}


def reference_design_structure() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "source_filename": SELECTED_FILENAME,
        "source_reference_id": SELECTED_REFERENCE_ID,
        "source_media_asset_id": SELECTED_MEDIA_ID,
        "measurements": "relative_relationships_not_pixel_coordinates",
        "CANVAS_LOGIC": "Asymmetric two-mass 4:5 page: architecture is a structural foundation; a designed field is the message territory.",
        "PRIMARY_VISUAL_MASS": "Lower architectural fragment occupying roughly half the width and the lower three-fifths, colliding into the field.",
        "SECONDARY_VISUAL_MASS": "Typographic stack living only in the designed void, not on the stone.",
        "NEGATIVE_SPACE_SYSTEM": "The color field is designed emptiness — the page — not leftover sky.",
        "DOMINANT_AXIS": "Vertical type column in the void; architecture rises as the opposing mass.",
        "VISUAL_ENTRY_POINT": "Architectural mass, then the large commercial hook in the void.",
        "READING_PATH": "stone → identity → offer monument → supporting value → gold action → quiet brand footer",
        "TYPOGRAPHIC_SCALE_RELATIONSHIPS": {
            "offer_to_canvas_height": RELATIVE["offer_size_vs_canvas_height"],
            "price_to_offer": RELATIVE["price_vs_offer"],
            "cta_to_offer": RELATIVE["cta_vs_offer"],
            "identity_to_offer": RELATIVE["identity_vs_offer"],
            "one_gold_land": True,
            "one_family_stack": True,
        },
        "TYPE_IMAGE_INTERACTION": "Type never sits on the photograph. Edge tension is stone against field.",
        "COMMERCIAL_HIERARCHY": "Verbal/numeric chant in the void is the proposition; supporting facts are a quieter paragraph; action is one gold close; brand is a footer.",
        "OFFER_MECHANISM": "Largest designed numeral/phrase in the void — not a badge.",
        "PRICE_MECHANISM": "Supporting line in the same column, grouped with the product, much smaller than the offer.",
        "PRODUCT_MECHANISM": "Paired with price on one baseline as inhabited value, not a listing row.",
        "CTA_MECHANISM": "Single gold closing line. Not a website button.",
        "BRAND_PLACEMENT_LOGIC": "Quiet footer in the field, opposite the architectural mass, generous inset.",
        "DEPTH_SYSTEM": "Field as atmosphere; real stone as the only photographic depth; no fake drop shadow around the whole silhouette.",
        "MATERIAL_SYSTEM": "Designed mineral void + real Temple limestone. Not navy. Not paper. Not a light shaft.",
        "EDGE_BEHAVIOR": "Architecture bleeds the bottom and left; type keeps a right inset; logo keeps a corner inset.",
        "ALIGNMENT_SYSTEM": "Type column end-aligned to the void's inner edge. Architecture bottom-left aligned as foundation.",
        "RHYTHM": "Large scale jump from identity to offer, then a quieter group, then empty field, then brand.",
        "TENSION": "Stone/field collision. Type stays off the collision.",
        "BALANCE": "Heavy architectural left-bottom against sparse right void.",
        "relative": dict(RELATIVE),
        "why_this_reference": WHY_SELECTED,
    }


def transferable_dna() -> dict[str, Any]:
    return {
        "schema": "TransferableDesignDNAV1",
        "source": SELECTED_FILENAME,
        "TRANSFERABLE_DESIGN_DNA": [
            "asymmetric two-mass page (architecture vs designed field)",
            "photograph as structural page mass, not a backdrop",
            "designed emptiness as the message actor",
            "type never on the photograph",
            "monumental scale contrast inside one type family",
            "one gold closing land",
            "quiet brand footer in the field",
            "stone/field edge collision",
            "controlled empty field between commercial group and brand",
        ],
        "REFERENCE_SIGNATURE_EXCLUDED": [
            "UniLoft colonnade / fluted columns / curved entablature",
            "this specific navy field",
            "black-and-white conversion of someone else's architecture",
            "DÜZENLİ. GÜVENLİ. PRESTİJLİ.",
            "UniLoft body copy and 'yatırım lokasyonu' highlight box",
            "investhome house-mark and 'YATIRIMA AÇILAN KAPI'",
            "period-stopped three-word civic chant as a cloneable lockup",
        ],
        "TRANSFERABLE_DNA": "CLEAR",
        "do_not_copy": (
            "reference project, reference building, reference logo, reference copy, "
            "reference price, reference factual content, pixel layout"
        ),
    }


def commercial_role_map() -> dict[str, Any]:
    return {
        "schema": "Phase1111CommercialRoleMap",
        "method": "map_by_role_not_coordinates",
        "rows": [
            {
                "reference_role": "PRIMARY OFFER / stacked civic proposition in the void",
                "temple_content": "%35 LANSMAN AVANTAJI",
                "visual_role": "monumental chant in the designed field",
            },
            {
                "reference_role": "PRICE ANCHOR (absent in the reference; mapped to supporting paragraph)",
                "temple_content": "675.000 USD",
                "visual_role": "supporting value line, grouped with product",
            },
            {
                "reference_role": "PRODUCT INFORMATION (absent; mapped to supporting paragraph)",
                "temple_content": "2+1 DAİRE",
                "visual_role": "paired with price on one inhabited baseline",
            },
            {
                "reference_role": "ACTION / gold closing word",
                "temple_content": "PROJEYİ KEŞFET",
                "visual_role": "one gold land, not a button",
            },
            {
                "reference_role": "IDENTITY / implied by architecture + body location",
                "temple_content": "THE TEMPLE / WASHINGTON D.C.",
                "visual_role": "quiet identity above the offer in the same void",
            },
            {
                "reference_role": "BRAND FOOTER",
                "temple_content": "real Temple logo + optional TARİHİN RUHU, GELECEĞİN DEĞERİ.",
                "visual_role": "quiet field footer",
            },
        ],
        "forbidden_devices": ["badge", "fact stack", "price card", "footer dump", "website button"],
        "short": "%35 is the void chant; price/unit are the supporting paragraph; CTA is the gold close.",
    }
