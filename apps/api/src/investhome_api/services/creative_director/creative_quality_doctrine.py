"""CreativeQualityDoctrineV1 — references + craft + prior Investhome OS failure lessons."""

from __future__ import annotations

from typing import Any

DOCTRINE_ID = "creative-quality-doctrine-v1"

CORE_RULES = {
    "A_image_design_integration": "Image and design must feel integrated. Do not place text on a photograph as a sticker sheet.",
    "B_protect_architecture": "Protect silhouette, tower/spire, entrance, primary façade, perspective lines, and key details.",
    "C_real_negative_space": "Use real photographic quiet. Do not invent giant rectangles so type has a box to live in.",
    "D_reading_hierarchy": "First and second reads must be immediate. The ad is understandable in one glance.",
    "E_designed_commerce": "Price, discount, and unit form one composition, not a stack of facts.",
    "F_typography_is_art_direction": "Type is not UI labels. Display and support faces must be decided per concept.",
    "G_gold_is_accent": "Premium is not more gold. Gold is a thin accent only.",
    "H_no_dashboard_language": "No KPI cards, metric tiles, pills, floating UI blocks, web buttons, or cards around every fact.",
    "I_logo_intentional": "Logo placement is composed, not pasted into a leftover corner.",
    "J_cta_composed": "CTA belongs to the visual composition, not a website button.",
    "K_restraint": "Empty space is not an invitation to decorate.",
    "L_family_is_not_template": "A design family is a philosophy, not a coordinate template.",
}

FAILURE_LESSONS = [
    "GPT Image as project architect invents buildings — never again as architecture source.",
    "Autonomous SVG overlay and 5.2B ornamental chrome produced jewelry/dashboard language.",
    "Giant discount medallions, ribbons, gold swooshes, and opaque panels fail premium real-estate.",
    "Listing-card layouts and lower-third strips read as portals, not campaigns.",
    "Filename-only or metadata-only 'analysis' does not produce art direction.",
    "Cloning a previous OS candidate is not original creative quality.",
    "Human visual PASS is authoritative over automated critic on a locked master; critic must not reopen approved art direction.",
]

FORBIDDEN_COPY = [
    "exact coordinates from a reference",
    "unique artwork from a reference",
    "copywriting from another project",
    "another project's building pixels",
    "another project's logo",
]


def build_quality_doctrine(retrieved: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    principles: list[str] = []
    for item in retrieved or []:
        dna = dict(item.get("dna") or {})
        principles.extend(list(dna.get("REUSABLE_PRINCIPLES") or [])[:4])
    return {
        "schema": "CreativeQualityDoctrineV1",
        "doctrine_id": DOCTRINE_ID,
        "core_rules": dict(CORE_RULES),
        "failure_lessons": list(FAILURE_LESSONS),
        "reference_principles": principles[:24],
        "do_not_copy": list(FORBIDDEN_COPY),
        "status": "READY",
    }
