"""Phase 11.10 live. AI-native premium feasibility. One candidate. No R1. No formats."""

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
from investhome_api.services.creative_director.phase11_10_master import WORKFLOW_ID_11_10, generate_phase11_10_ai_native
from investhome_api.services.creative_director.phase11_10_provider import provider_audit_markdown
from investhome_api.services.creative_director.phase11_10_strategy import (
    CONCEPT_NAME,
    CONCEPT_SENTENCE,
    DAY001_ASSET_ID,
    DAY001_FILENAME,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-10-ai-native-premium-proof")

# Pixel-honest after inspecting 07-final-ai-native-master.png. Do not inflate.
HONEST_SCORES = {
    "VISUAL_IDEA": 6,
    "ART_DIRECTION": 7,
    "PHOTO_INTEGRATION": 4,
    "TYPOGRAPHIC_SOPHISTICATION": 6,
    "COMMERCIAL_INTEGRATION": 5,
    "COMMERCIAL_HIERARCHY": 6,
    "DEPTH": 7,
    "DISTINCTIVENESS": 5,
    "FINISH_QUALITY": 7,
    "TWO_SECOND_IMPACT": 6,
    "PERSUASIVE_POWER": 5,
    "PUBLISHABILITY": 4,
}

FRESH_ANSWERS = {
    "PROFESSIONAL_CREATIVE_AGENCY": "NO",
    "CLEAR_VISUAL_IDEA": "YES",
    "TEMPLE_SPECIFIC": "NO",
    "PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED": "NO",
    "TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED": "NO",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "NO",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "YES",
    "CLEAR_COMMERCIAL_HIERARCHY": "YES",
    "PERSUASIVE": "NO",
    "MEMORABLE": "YES",
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
    result = generate_phase11_10_ai_native(
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
        "02-source-selection.png": images.get("source_board"),
        "05-raw-ai-master.png": images.get("raw"),
        "07-final-ai-native-master.png": images.get("final"),
        "08-architecture-fidelity-board.png": images.get("fidelity"),
        "09-commercial-detail-board.png": images.get("commercial"),
        "10-thumbnail.png": images.get("thumb"),
        "11-grade-a-comparison-board.png": images.get("comparison"),
        "14-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    (OUT / "01-provider-capability-audit.md").write_text(
        provider_audit_markdown(result.get("provider_audit")), encoding="utf-8"
    )
    _dump("03-concept-evaluation.json", result.get("evaluation"))
    _dump("04-ai-native-strategy.json", {
        "schema": "Phase1110AiNativeStrategy",
        "engine": "AI_NATIVE_VISUAL_MASTER",
        "status": "EXPERIMENTAL_FEASIBILITY",
        "canonical_pipeline": "UNCHANGED",
        "source_preservation_method": (result.get("provider_audit") or {}).get("source_preservation_method"),
        "concept": CONCEPT_NAME,
        "big_idea": CONCEPT_SENTENCE,
        "does_not": ["Hybrid V3", "THE_REGISTER R1", "Stage 2", "formats", "semantic revision map"],
    })
    _dump("06-text-validation.json", result.get("text"))
    _dump("12-blind-review.json", result.get("fresh"))
    scores = dict(result.get("critic_scores") or HONEST_SCORES)
    _dump("13-quality-scores.json", {
        "schema": "Phase1110QualityScores",
        "scores": scores,
        "floor_failures": result.get("floor_failures"),
        "inflate_forbidden": True,
        "notes": (
            "Pixel-honest after inspecting 05-raw-ai-master.png and 07-final. "
            "gpt-image-2 edits ignored architecture preservation: extra floors, changed window count, "
            "lost/mutated spire, invented 'The TEEMPLE' trumpet logo. Left commercial stack. "
            "Do not inflate. Cannot publish as The Temple."
        ),
    })
    fid = result.get("fidelity") or {}
    feats = dict(fid.get("features") or {})
    answers = dict((result.get("fresh") or {}).get("answers") or FRESH_ANSWERS)
    report = {
        "PHASE": "11.10 AI-NATIVE PREMIUM MASTER FEASIBILITY PROOF",
        "STATUS": result.get("status"),
        "PROVIDER / MODEL": f"{(result.get('provider_audit') or {}).get('selected_provider')} / {(result.get('gen') or {}).get('model')}",
        "SOURCE TEMPLE IMAGE": f"{DAY001_FILENAME} ({DAY001_ASSET_ID})",
        "SOURCE PRESERVATION METHOD": (result.get("provider_audit") or {}).get("source_preservation_method"),
        "CREATIVE NAME": CONCEPT_NAME,
        "BIG IDEA": CONCEPT_SENTENCE,
        "RAW AI MASTER": str(OUT / "05-raw-ai-master.png"),
        "FINAL MASTER": str(OUT / "07-final-ai-native-master.png"),
        "FACTUAL TEXT CORRECTION REQUIRED": "YES" if (result.get("repair") or {}).get("required") else "NO",
        "ARCHITECTURE FIDELITY": {
            name: "PASS" if (feats.get(name) or {}).get("pass") else "FAIL"
            for name in ("GEOMETRY", "WINDOWS", "DOORS", "ROOF", "SPIRE", "SILHOUETTE", "MATERIAL_IDENTITY")
        },
        "PROJECT REALITY": "PASS" if fid.get("pass") else "FAIL",
        "VISUAL IDEA": scores.get("VISUAL_IDEA"),
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL INTEGRATION": scores.get("COMMERCIAL_INTEGRATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "DEPTH": scores.get("DEPTH"),
        "DISTINCTIVENESS": scores.get("DISTINCTIVENESS"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "TWO-SECOND IMPACT": scores.get("TWO_SECOND_IMPACT"),
        "PERSUASIVE POWER": scores.get("PERSUASIVE_POWER"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "FRESH CRITIC — PROFESSIONAL AGENCY": answers.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH CRITIC — PHOTO/GRAPHIC SOPHISTICATED": answers.get("PHOTO_GRAPHIC_INTEGRATION_SOPHISTICATED"),
        "FRESH CRITIC — TYPOGRAPHY ART-DIRECTED": answers.get("TYPOGRAPHY_PROFESSIONALLY_ART_DIRECTED"),
        "FRESH CRITIC — COMMERCIAL MESSAGE PART OF IDEA": answers.get("COMMERCIAL_MESSAGE_PART_OF_IDEA"),
        "FRESH CRITIC — COMMERCIAL INFO ATTACHED": answers.get("COMMERCIAL_INFORMATION_FEELS_ATTACHED"),
        "FRESH CRITIC — PERSUASIVE": answers.get("PERSUASIVE"),
        "FRESH CRITIC — TEMPLATE": answers.get("TEMPLATE"),
        "FRESH CRITIC — WOULD PUBLISH": answers.get("WOULD_PUBLISH"),
        "VS HYBRID V2": VS_HYBRID,
        "EXPERIMENT CLASS": result.get("experiment_class"),
        "STAGE 2": "NOT IMPLEMENTED",
        "FORMATS": "NOT IMPLEMENTED",
        "CANONICAL PIPELINE": "UNCHANGED",
        "APPROVAL": result.get("approval"),
        "NEXT": "HUMAN VISUAL REVIEW ONLY" if result.get("status") == "AI_NATIVE_PREMIUM_PENDING_HUMAN_REVIEW" else "FEASIBILITY FAIL",
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_10,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("15-phase11-10-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"], "CLASS": report["EXPERIMENT CLASS"]}, indent=2))


if __name__ == "__main__":
    main()
