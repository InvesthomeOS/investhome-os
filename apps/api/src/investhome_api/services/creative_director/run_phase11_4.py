"""Phase 11.4 live. Integrated commercial campaign proof. Does not create format children. Does not revise Proof 01/02."""

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
from investhome_api.services.creative_director.phase11_4_master import WORKFLOW_ID_11_4, generate_phase11_4_creative_quality_proof
from investhome_api.services.creative_director.phase11_4_strategy import HEADLINE, HIERARCHY, TWO_SECOND

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-4-creative-quality-proof-03")


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
    result = generate_phase11_4_creative_quality_proof(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-project-asset-opportunity-board.png": images.get("opportunity"),
        "06-visual-idea-proof.png": images.get("no_copy"),
        "07-commercial-system-proof.png": images.get("commercial_system"),
        "08-art-direction-board.png": images.get("art_direction"),
        "09-stage3-creative-proof-03.png": images.get("proof"),
        "10-thumbnail-proof.png": images.get("thumbnail"),
        "13-semantic-revision-map.png": images.get("semantic"),
        "14-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    _dump("02-concept-evaluation.json", result.get("concept_evaluation") or {})
    _dump("03-integrated-creative-strategy.json", result.get("strategy") or {})
    _dump("04-campaign-skeleton.json", result.get("campaign_skeleton") or {})
    _dump("05-reading-path.json", result.get("reading_path") or {})
    _dump("11-creative-critic-v3.json", result.get("critic") or {})
    _dump("12-fresh-blind-critic-v3.json", result.get("fresh_critic") or {})
    critic = result.get("critic") or {}
    scores = dict(critic.get("scores") or {})
    fresh = result.get("fresh_critic") or {}
    answers = dict(fresh.get("answers") or {})
    report = {
        "PHASE": "11.4 CREATIVE QUALITY PROOF 03",
        "STATUS": result.get("status"),
        "CANONICAL PIPELINE": result.get("pipeline_id"),
        "CREATIVE NAME": result.get("creative_name"),
        "CREATIVE CONCEPT": result.get("creative_concept"),
        "WHY SPECIFIC TO THE TEMPLE": (result.get("strategy") or {}).get("why_this_idea_fits_this_project"),
        "SELECTED REAL TEMPLE ASSET(S)": result.get("selected_asset"),
        "CAMPAIGN HIERARCHY": HIERARCHY,
        "COMMERCIAL MECHANISM": ((result.get("integrated_concept") or {}).get("answers") or {}).get(
            "HOW DOES THE SALES MESSAGE PARTICIPATE IN THE VISUAL IDEA?"
        ),
        "READING PATH": " → ".join((result.get("reading_path") or {}).get("abstract_flow") or []),
        "HEADLINE": HEADLINE,
        "TWO_SECOND": TWO_SECOND,
        "VISUAL IDEA GATE": "PASS" if (result.get("visual_idea_gate") or {}).get("pass") else "FAIL",
        "COMMERCIAL SYSTEM GATE": "PASS" if (result.get("commercial_system_gate") or {}).get("pass") else "FAIL",
        "DETACHED COMMERCIAL LOCKUP": "CLEAR" if (result.get("detached_lockup") or {}).get("pass") else "DETECTED",
        "THUMBNAIL TEST": "PASS" if (result.get("thumbnail_test") or {}).get("pass") else "FAIL",
        "ADVERTISEMENT VS POSTER": (result.get("advertisement_vs_poster") or {}).get("answer"),
        "VISUAL IDEA": scores.get("VISUAL_IDEA"),
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL INTEGRATION": scores.get("COMMERCIAL_INTEGRATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "READING PATH SCORE": scores.get("READING_PATH"),
        "BRAND CHARACTER": scores.get("BRAND_CHARACTER"),
        "DEPTH": scores.get("DEPTH"),
        "NEGATIVE SPACE": scores.get("NEGATIVE_SPACE"),
        "DISTINCTIVENESS": scores.get("DISTINCTIVENESS"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "TWO-SECOND IMPACT": scores.get("TWO_SECOND_IMPACT"),
        "PERSUASIVE POWER": scores.get("PERSUASIVE_POWER"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "FRESH CRITIC — PROFESSIONAL AGENCY": answers.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH CRITIC — CLEAR VISUAL IDEA": answers.get("CLEAR_VISUAL_IDEA"),
        "FRESH CRITIC — PROJECT SPECIFIC": answers.get("PROJECT_SPECIFIC"),
        "FRESH CRITIC — COMMERCIAL MESSAGE PART OF IDEA": answers.get("COMMERCIAL_MESSAGE_PART_OF_IDEA"),
        "FRESH CRITIC — COMMERCIAL INFORMATION FEELS ATTACHED": answers.get("COMMERCIAL_INFORMATION_FEELS_ATTACHED"),
        "FRESH CRITIC — CLEAR READING PATH": answers.get("CLEAR_READING_PATH"),
        "FRESH CRITIC — PERSUASIVE": answers.get("PERSUASIVE"),
        "FRESH CRITIC — MEMORABLE": answers.get("MEMORABLE_AFTER_TWO_SECONDS"),
        "FRESH CRITIC — TEMPLATE": answers.get("LOOKS_LIKE_TEMPLATE"),
        "FRESH CRITIC — WOULD PUBLISH": answers.get("WOULD_PUBLISH"),
        "REAL PROJECT PHOTOGRAPHY": result.get("real_project_photography"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": result.get("project_photo_internal_generated_pixels"),
        "ARCHITECTURE FIDELITY": result.get("architecture_fidelity"),
        "REAL TEMPLE LOGO": result.get("real_temple_logo"),
        "STAGE 2 REVISION COMPATIBILITY": result.get("stage_2_revision_compatibility"),
        "APPROVAL": result.get("approval"),
        "EXACT FAILURE": result.get("exact_failure"),
        "MASTER 01": "UNCHANGED",
        "MASTER 02": "UNCHANGED",
        "MASTER 03": "UNCHANGED",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER": "UNCHANGED",
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_4,
        "SUBMITTED_AS_DRAFT_MASTER": result.get("submitted_as_draft_master"),
        "ROUTER_ELIGIBLE": False,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("15-phase11-4-report.json", report)
    print(
        json.dumps(
            {
                "PHASE": report["PHASE"],
                "STATUS": report["STATUS"],
                "PUBLISHABILITY": report["PUBLISHABILITY"],
                "FRESH CRITIC — WOULD PUBLISH": report["FRESH CRITIC — WOULD PUBLISH"],
                "SUBMITTED": result.get("submitted_as_draft_master"),
            },
            indent=2,
            default=str,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
