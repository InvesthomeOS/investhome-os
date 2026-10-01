"""Phase 11.11 live. Reference-guided reconstruction. One candidate. No R1. No formats."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase11_11_master import WORKFLOW_ID_11_11, generate_phase11_11_reference_guided
from investhome_api.services.creative_director.phase11_11_match import DAY008_ASSET_ID, DAY008_FILENAME
from investhome_api.services.creative_director.phase11_11_select import SELECTED_FILENAME, SELECTED_MEDIA_ID, SELECTED_REFERENCE_ID, WHY_SELECTED
from investhome_api.services.creative_director.phase11_11_structure import commercial_role_map, transferable_dna

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-11-reference-guided-proof")

# Filled after inspecting 08-reference-guided-final.png. Do not inflate.
HONEST_SCORES = {
    "ART_DIRECTION": 6,
    "PHOTO_INTEGRATION": 5,
    "TYPOGRAPHIC_SOPHISTICATION": 6,
    "COMMERCIAL_INTEGRATION": 6,
    "COMMERCIAL_HIERARCHY": 7,
    "READING_PATH": 6,
    "BRAND_CHARACTER": 6,
    "DEPTH": 5,
    "NEGATIVE_SPACE": 7,
    "DISTINCTIVENESS": 5,
    "FINISH_QUALITY": 5,
    "TWO_SECOND_IMPACT": 6,
    "PERSUASIVE_POWER": 5,
    "PUBLISHABILITY": 5,
}

FRESH_ANSWERS = {
    "PROFESSIONAL_CREATIVE_AGENCY": "NO",
    "PROJECT_SPECIFIC": "YES",
    "PHOTO_TYPE_RELATIONSHIP_SOPHISTICATED": "NO",
    "COMMERCIAL_HIERARCHY_DESIGNED": "YES",
    "PERSUASIVE": "NO",
    "MEMORABLE": "NO",
    "TEMPLATE": "YES",
    "WOULD_PUBLISH": "NO",
}

VS_HYBRID = "WORSE"


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _write(name: str, image) -> None:
    (OUT / name).write_bytes(_png(image))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase11_11_reference_guided(
        db,
        user,
        row,
        honest_scores=HONEST_SCORES,
        fresh_answers=FRESH_ANSWERS,
        vs_hybrid=VS_HYBRID,
    )
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-reference-selection-board.png": images.get("selection"),
        "05-temple-asset-match-board.png": images.get("match"),
        "07-reconstruction-development.png": images.get("development"),
        "08-reference-guided-final.png": images.get("final"),
        "09-thumbnail-15.png": images.get("thumb15"),
        "10-thumbnail-25.png": images.get("thumb25"),
        "12-grade-a-comparison-board.png": images.get("comparison"),
        "15-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    field = images.get("field")
    if field is not None:
        _write("field.png", field)
    _dump("02-reference-score.json", result.get("scores_table"))
    _dump("03-reference-design-structure.json", result.get("structure"))
    _dump("04-transferable-dna.json", result.get("dna"))
    _dump("06-commercial-role-map.json", result.get("roles"))
    _dump("11-reference-similarity-audit.json", result.get("similarity"))
    scores = dict(result.get("critic_scores") or HONEST_SCORES)
    answers = dict((result.get("fresh") or {}).get("answers") or FRESH_ANSWERS)
    _dump(
        "13-creative-critic.json",
        {
            "schema": "Phase1111CreativeCritic",
            "scores": scores,
            "floor_failures": result.get("floor_failures"),
            "inflate_forbidden": True,
            "notes": (
            "Pixel-honest after inspecting 08-reference-guided-final.png. "
            "Two-mass DNA transferred, but the Temple fragment sits as a daylight cutout on a dark void "
            "with leftover sky halo — not 00013's stone-as-foundation collision. "
            "Right-column facts are role-mapped, still a commercial stack. Do not inflate. Did not beat Hybrid V2's 8."
        ),
        },
    )
    _dump("14-fresh-blind-review.json", result.get("fresh"))
    dna = result.get("dna") or transferable_dna()
    roles = result.get("roles") or commercial_role_map()
    report = {
        "PHASE": "11.11 REFERENCE-GUIDED PREMIUM RECONSTRUCTION PROOF",
        "STATUS": result.get("status"),
        "SELECTED REFERENCE": f"{SELECTED_FILENAME} ({SELECTED_REFERENCE_ID} / media {SELECTED_MEDIA_ID})",
        "WHY SELECTED": WHY_SELECTED,
        "TRANSFERABLE DESIGN DNA": "; ".join(list(dna.get("TRANSFERABLE_DESIGN_DNA") or [])[:4]),
        "REFERENCE SIGNATURE EXCLUDED": "; ".join(list(dna.get("REFERENCE_SIGNATURE_EXCLUDED") or [])[:4]),
        "REAL TEMPLE ASSET": f"{DAY008_FILENAME} ({DAY008_ASSET_ID})",
        "PROJECT REALITY": result.get("project_reality"),
        "ARCHITECTURE FIDELITY": result.get("architecture_fidelity"),
        "PROJECT INTERNAL GENERATED PIXELS": result.get("project_internal_generated_pixels"),
        "REAL TEMPLE LOGO": result.get("real_temple_logo"),
        "COMMERCIAL ROLE MAPPING": roles.get("short"),
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL INTEGRATION": scores.get("COMMERCIAL_INTEGRATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "READING PATH": scores.get("READING_PATH"),
        "DEPTH": scores.get("DEPTH"),
        "DISTINCTIVENESS": scores.get("DISTINCTIVENESS"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "PERSUASIVE POWER": scores.get("PERSUASIVE_POWER"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "15% TEST": result.get("test_15"),
        "25% TEST": result.get("test_25"),
        "REFERENCE DNA TRANSFER": "PASS" if (result.get("similarity") or {}).get("TRANSFERABLE_DNA") == "CLEAR" else "FAIL",
        "SIGNATURE COPYING": (result.get("similarity") or {}).get("SIGNATURE_ELEMENT_COPYING"),
        "FRESH CRITIC — PROFESSIONAL AGENCY": answers.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH CRITIC — PHOTO/TYPE SOPHISTICATED": answers.get("PHOTO_TYPE_RELATIONSHIP_SOPHISTICATED"),
        "FRESH CRITIC — COMMERCIAL HIERARCHY DESIGNED": answers.get("COMMERCIAL_HIERARCHY_DESIGNED"),
        "FRESH CRITIC — PERSUASIVE": answers.get("PERSUASIVE"),
        "FRESH CRITIC — TEMPLATE": answers.get("TEMPLATE"),
        "FRESH CRITIC — WOULD PUBLISH": answers.get("WOULD_PUBLISH"),
        "VS HYBRID V2": VS_HYBRID,
        "APPROVAL": result.get("approval"),
        "NEXT": "HUMAN VISUAL REVIEW ONLY" if result.get("status") == "REFERENCE_GUIDED_PREMIUM_PENDING_HUMAN_REVIEW" else "CREATIVE QUALITY FAIL",
        "STAGE 2": "NOT IMPLEMENTED",
        "FORMATS": "NOT IMPLEMENTED",
        "CANONICAL PIPELINE": "UNCHANGED",
        "ROUTER_ELIGIBLE": False,
        "MASTER": False,
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_11,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("16-phase11-11-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"]}, indent=2))


if __name__ == "__main__":
    main()
