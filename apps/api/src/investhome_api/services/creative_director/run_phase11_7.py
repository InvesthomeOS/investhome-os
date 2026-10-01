"""Phase 11.7 live. Hybrid finish quality pass. Same concept. No new field. No formats."""

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
from investhome_api.services.creative_director.phase11_6_strategy import CONCEPT_NAME, DAY003_ASSET_ID, DAY003_FILENAME
from investhome_api.services.creative_director.phase11_7_master import WORKFLOW_ID_11_7, generate_phase11_7_hybrid_finish

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-7-hybrid-finish")

# Pixel-honest scores after inspecting 07-hybrid-premium-proof-r1.png at 100/50/25/15%.
# Do not inflate. Halo, lighting mismatch, and 15% CTA still block the 9 floors.
HONEST_SCORES = {
    "VISUAL_IDEA": 8,
    "ART_DIRECTION": 8,
    "PHOTO_INTEGRATION": 8,
    "TYPOGRAPHIC_SOPHISTICATION": 8,
    "COMMERCIAL_INTEGRATION": 8,
    "COMMERCIAL_HIERARCHY": 8,
    "READING_PATH": 8,
    "BRAND_CHARACTER": 8,
    "DEPTH": 8,
    "NEGATIVE_SPACE": 8,
    "DISTINCTIVENESS": 8,
    "FINISH_QUALITY": 8,
    "TWO_SECOND_IMPACT": 8,
    "PERSUASIVE_POWER": 8,
    "PUBLISHABILITY": 8,
}

FRESH_ANSWERS = {
    "PROFESSIONAL_CREATIVE_AGENCY": "NO",
    "CLEAR_VISUAL_IDEA": "YES",
    "PROJECT_SPECIFIC": "YES",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
    "CLEAR_READING_PATH": "YES",
    "PERSUASIVE": "YES",
    "MEMORABLE_AFTER_TWO_SECONDS": "YES",
    "LOOKS_LIKE_TEMPLATE": "NO",
    "WOULD_PUBLISH": "NO",
}

BLIND = {
    "MORE_PROFESSIONALLY_ART_DIRECTED": "B",
    "BETTER_PHOTO_GRAPHIC_INTEGRATION": "B",
    "BETTER_TYPOGRAPHY": "B",
    "STRONGER_COMMERCIAL_HIERARCHY": "B",
    "MORE_PERSUASIVE": "B",
    "WOULD_PUBLISH": "NEITHER",
}

FRESH_PHOTO_GRAPHIC_SOPHISTICATED = "NO"
FRESH_TYPOGRAPHY_ART_DIRECTED = "YES"


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
    result = generate_phase11_7_hybrid_finish(
        db,
        user,
        row,
        honest_scores=HONEST_SCORES,
        fresh_answers=FRESH_ANSWERS,
        blind=BLIND,
    )
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-original-proof.png": images.get("original"),
        "04-material-integration-study.png": images.get("material"),
        "05-typography-finish-study.png": images.get("type"),
        "06-commercial-hierarchy-study.png": images.get("hierarchy"),
        "07-hybrid-premium-proof-r1.png": images.get("r1"),
        "08-thumbnail-r1.png": images.get("thumb"),
        "09-side-by-side-review.png": images.get("side"),
        "13-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    critic = result.get("critic") or {}
    scores = dict(critic.get("scores") or HONEST_SCORES)
    critic["notes"] = (
        "Pixel-honest after inspecting hybrid-premium-proof-r1.png at 100/50/25/15%. "
        "R1 fixes the vertical spine, inverted logo, CTA-before-value, and some foot occlusion. "
        "A pale fringe still reads on the spire at 100%. Daylight object vs museum field is unreconciled. "
        "PROJEYİ KEŞFET still collapses at 15%. Do not inflate to the 9 floors. Concept unchanged."
    )
    fresh = result.get("fresh") or {}
    answers = dict(fresh.get("answers") or FRESH_ANSWERS)
    _dump("10-creative-critic-v3.json", critic)
    _dump("11-blind-comparison.json", {
        "schema": "Phase117BlindComparison",
        "shown": "A = original Phase 11.6 Hybrid Proof; B = Phase 11.7 R1. Labels A/B only. No phase numbers explained.",
        "answers": BLIND,
        "quality_b": result.get("quality_b"),
        "publish_b": result.get("publish_b"),
        "b_wins": result.get("b_wins"),
        "required": "B wins all quality categories and WOULD PUBLISH = B",
        "notes": (
            "B wins art direction, photo/graphic integration, typography, commercial hierarchy, and persuasion versus A. "
            "Neither is publishable at agency finish: R1 still shows a spire fringe and unresolved light."
        ),
    })
    _dump("12-fresh-final-review.json", fresh)
    report = {
        "PHASE": "11.7 HYBRID PREMIUM FINISH QUALITY PASS",
        "STATUS": result.get("status"),
        "CONCEPT": CONCEPT_NAME,
        "CONCEPT_UNCHANGED": True,
        "REAL TEMPLE SOURCE": f"{DAY003_FILENAME} ({DAY003_ASSET_ID})",
        "PROJECT REALITY FIREWALL": (result.get("firewall") or {}).get("status"),
        "PRIMARY FINISH DEFECTS": [
            "White halo on spire/roof from dilated sky-punch mask",
            "Hard foot crop; paper never occluded the object",
            "Full-silhouette fake drop shadow",
            "Vertical price spine unread at 15%",
            "CTA under headline — gone at 15%, arrived before value",
        ],
        "CORRECTIONS": [
            "Erode + defringe isolation, no post-sky dilation",
            "Museum grade on the same Day_003 pixels",
            "Paper recomposited over object feet; contact only on paper",
            "%35 printed behind the monument; 675.000 USD + 2+1 on one plate line",
            "PROJEYİ KEŞFET as last tracked beat on the paper",
        ],
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL INTEGRATION": scores.get("COMMERCIAL_INTEGRATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "READING PATH": scores.get("READING_PATH"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "PERSUASIVE POWER": scores.get("PERSUASIVE_POWER"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "SIDE-BY-SIDE": "R1 BETTER" if result.get("quality_b") else "NOT BETTER",
        "FRESH REVIEW — PROFESSIONAL AGENCY": answers.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH REVIEW — PHOTO/GRAPHIC SOPHISTICATED": FRESH_PHOTO_GRAPHIC_SOPHISTICATED,
        "FRESH REVIEW — TYPOGRAPHY ART-DIRECTED": FRESH_TYPOGRAPHY_ART_DIRECTED,
        "FRESH REVIEW — PERSUASIVE": answers.get("PERSUASIVE"),
        "FRESH REVIEW — TEMPLATE": answers.get("LOOKS_LIKE_TEMPLATE"),
        "FRESH REVIEW — WOULD PUBLISH": answers.get("WOULD_PUBLISH"),
        "STAGE 2": "NOT IMPLEMENTED",
        "FORMATS": "NOT IMPLEMENTED",
        "MASTER ROUTING": "NOT IMPLEMENTED",
        "APPROVAL": result.get("approval"),
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "ENGINE": result.get("engine"),
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_7,
        "IDENTITY": {"before": before, "after": after},
        "FINISH_FLOOR_FAIL": result.get("finish_floor_fail"),
    }
    _dump("14-phase11-7-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"], "PUBLISHABILITY": report["PUBLISHABILITY"]}, indent=2))


if __name__ == "__main__":
    main()
