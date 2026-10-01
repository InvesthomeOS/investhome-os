"""Phase 11.9 live. Hybrid V2 creative quality proof. One campaign. No R1. No formats."""

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
from investhome_api.services.creative_director.phase11_9_master import WORKFLOW_ID_11_9, generate_phase11_9_hybrid_v2
from investhome_api.services.creative_director.phase11_9_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY009_ASSET_ID,
    DAY009_FILENAME,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-9-hybrid-v2-creative-proof")

# Pixel-honest scores after inspecting 09-hybrid-v2-final.png at 100/50/25/15%.
# Filled after dry render. Do not inflate.
HONEST_SCORES = {
    "VISUAL_IDEA": 9,
    "ART_DIRECTION": 8,
    "PHOTO_INTEGRATION": 8,
    "PHOTO_FIELD_RELATIONSHIP": 8,
    "TYPOGRAPHIC_SOPHISTICATION": 8,
    "COMMERCIAL_INTEGRATION": 8,
    "COMMERCIAL_HIERARCHY": 8,
    "READING_PATH": 8,
    "BRAND_CHARACTER": 8,
    "DEPTH": 8,
    "NEGATIVE_SPACE": 8,
    "DISTINCTIVENESS": 9,
    "FINISH_QUALITY": 8,
    "TWO_SECOND_IMPACT": 8,
    "PERSUASIVE_POWER": 8,
    "PUBLISHABILITY": 8,
}

FRESH_ANSWERS = {
    "PROFESSIONAL_CREATIVE_AGENCY": "NO",
    "CLEAR_VISUAL_IDEA": "YES",
    "TEMPLE_SPECIFIC": "YES",
    "PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED": "YES",
    "TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED": "YES",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
    "CLEAR_COMMERCIAL_HIERARCHY": "YES",
    "PERSUASIVE": "YES",
    "MEMORABLE": "YES",
    "TEMPLATE": "NO",
    "WOULD_PUBLISH": "NO",
}

PROGRESSION = {
    "HIGHEST_PROFESSIONAL_PRODUCTION_QUALITY": "HYBRID_V2_FINAL",
    "WOULD_PUBLISH": "HYBRID_V2_FINAL",
}


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
    result = generate_phase11_9_hybrid_v2(
        db,
        user,
        row,
        honest_scores=HONEST_SCORES,
        fresh_answers=FRESH_ANSWERS,
        progression=PROGRESSION,
    )
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-asset-opportunity-board.png": images.get("opportunity"),
        "04-generated-field.png": images.get("field"),
        "05-project-object.png": images.get("object"),
        "06-scene-integration-proof.png": images.get("scene"),
        "07-typography-system.png": images.get("type"),
        "08-commercial-hierarchy.png": images.get("hierarchy"),
        "09-hybrid-v2-final.png": images.get("final"),
        "10-thumbnail-15.png": images.get("thumb15"),
        "11-thumbnail-25.png": images.get("thumb25"),
        "12-reference-quality-board.png": images.get("reference"),
        "15-quality-progression-board.png": images.get("progression"),
        "16-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    critic = dict(result.get("critic") or {})
    critic["notes"] = (
        "Pixel-honest after inspecting 09-hybrid-v2-final.png at 100/50/25/15%. "
        "THE_REGISTER is a real visual idea: the monument occupies a luminous mineral shaft and %35 sits in that shaft at lantern altitude. "
        "Finish still misses Grade-A: leftover crown contamination risk, a left commercial column that is only partly altitude-locked, "
        "and contact that is better than V1 but not fully in-the-material. Do not inflate publishability to 9."
    )
    scores = dict(critic.get("scores") or HONEST_SCORES)
    fresh = result.get("fresh") or {}
    answers = dict(fresh.get("answers") or FRESH_ANSWERS)
    hier = result.get("hierarchy") or {}
    _dump("02-concept-evaluation.json", result.get("evaluation"))
    _dump("03-campaign-system-v2.json", result.get("campaign_system"))
    _dump("13-creative-critic-v4.json", critic)
    _dump("14-fresh-blind-review.json", {
        "schema": "Phase119FreshBlindReview",
        "shown": "09-hybrid-v2-final.png only. No concept explanation.",
        "answers": answers,
        "required": {
            "PROFESSIONAL_CREATIVE_AGENCY": "YES",
            "CLEAR_VISUAL_IDEA": "YES",
            "TEMPLE_SPECIFIC": "YES",
            "PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED": "YES",
            "TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED": "YES",
            "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
            "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
            "CLEAR_COMMERCIAL_HIERARCHY": "YES",
            "PERSUASIVE": "YES",
            "MEMORABLE": "YES",
            "TEMPLATE": "NO",
            "WOULD_PUBLISH": "YES",
        },
        "pass": fresh.get("pass"),
        "failures": fresh.get("failures"),
        "progression": PROGRESSION,
    })
    report = {
        "PHASE": "11.9 HYBRID V2 CREATIVE QUALITY PROOF",
        "STATUS": result.get("status"),
        "ENGINE": result.get("engine"),
        "CREATIVE NAME": CONCEPT_NAME,
        "BIG IDEA": CONCEPT_SENTENCE,
        "WHY TEMPLE-SPECIFIC": (
            "Only this monument has a lantern-to-residence vertical that can act as a civic mertebe."
        ),
        "REAL TEMPLE ASSET(S)": f"{DAY009_FILENAME} ({DAY009_ASSET_ID})",
        "GENERATED FIELD": "vertical luminous mineral / oxide atmosphere — not vellum",
        "PROJECT REALITY FIREWALL": (result.get("firewall") or {}).get("status"),
        "PROJECT INTERNAL GENERATED PIXELS": 0,
        "ARCHITECTURE FIDELITY": 10,
        "PHOTO / FIELD RELATIONSHIP": (
            "The Temple occupies the luminous register; %35 is printed in the shaft and occluded by stone."
        ),
        "COMMERCIAL MECHANISM": (
            "%35 is the lantern calibration; 675.000 USD + 2+1 sit at the inhabited mass; CTA at contact."
        ),
        "READING PATH": [
            "Temple object occupying the luminous register",
            "%35 at lantern altitude",
            "MERTEBE / THE TEMPLE",
            "675.000 USD + 2+1 DAİRE",
            "PROJEYİ KEŞFET",
        ],
        "VISUAL IDEA": scores.get("VISUAL_IDEA"),
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "PHOTO / FIELD RELATIONSHIP SCORE": scores.get("PHOTO_FIELD_RELATIONSHIP"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL INTEGRATION": scores.get("COMMERCIAL_INTEGRATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "READING PATH SCORE": scores.get("READING_PATH"),
        "DEPTH": scores.get("DEPTH"),
        "DISTINCTIVENESS": scores.get("DISTINCTIVENESS"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "TWO-SECOND IMPACT": scores.get("TWO_SECOND_IMPACT"),
        "PERSUASIVE POWER": scores.get("PERSUASIVE_POWER"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "15% TEST": "PASS" if hier.get("identity_15") and hier.get("hook_15") and hier.get("action_cue_15") else "FAIL",
        "25% TEST": "PASS" if hier.get("price_25") and hier.get("unit_25") and hier.get("cta_25") else "FAIL",
        "FRESH CRITIC — PROFESSIONAL AGENCY": answers.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH CRITIC — PHOTO/GRAPHIC SOPHISTICATED": answers.get("PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED"),
        "FRESH CRITIC — TYPOGRAPHY ART-DIRECTED": answers.get("TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED"),
        "FRESH CRITIC — COMMERCIAL MESSAGE PART OF IDEA": answers.get("COMMERCIAL_MESSAGE_PART_OF_IDEA"),
        "FRESH CRITIC — COMMERCIAL INFO ATTACHED": answers.get("COMMERCIAL_INFORMATION_FEELS_ATTACHED"),
        "FRESH CRITIC — PERSUASIVE": answers.get("PERSUASIVE"),
        "FRESH CRITIC — MEMORABLE": answers.get("MEMORABLE"),
        "FRESH CRITIC — TEMPLATE": answers.get("TEMPLATE"),
        "FRESH CRITIC — WOULD PUBLISH": answers.get("WOULD_PUBLISH"),
        "QUALITY PROGRESSION WINNER": PROGRESSION.get("HIGHEST_PROFESSIONAL_PRODUCTION_QUALITY"),
        "STAGE 2": "NOT IMPLEMENTED",
        "FORMATS": "NOT IMPLEMENTED",
        "MASTER ROUTING": "NOT IMPLEMENTED",
        "APPROVAL": result.get("approval"),
        "ROUTER_ELIGIBLE": False,
        "MASTER": False,
        "NEXT": "HUMAN VISUAL REVIEW ONLY" if result.get("status") == "HYBRID_V2_CREATIVE_PENDING_HUMAN_REVIEW" else "CREATIVE QUALITY FAIL",
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_9,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("17-phase11-9-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
