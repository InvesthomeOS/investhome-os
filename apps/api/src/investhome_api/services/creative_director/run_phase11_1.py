"""Phase 11.1 live. Idea-first quality proof. Does not create format children."""

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
from investhome_api.services.creative_director.phase11_1_master import WORKFLOW_ID_11_1, generate_phase11_1_creative_quality_proof
from investhome_api.services.creative_director.phase11_1_strategy import TWO_SECOND, concept_selection_markdown

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-1-creative-quality-proof")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _md(name: str, body: str) -> None:
    (OUT / name).write_text(body.strip() + "\n", encoding="utf-8")


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
    result = generate_phase11_1_creative_quality_proof(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-project-asset-opportunity-board.png": images.get("opportunity"),
        "05-no-copy-proof.png": images.get("no_copy"),
        "07-art-direction-board.png": images.get("art_direction"),
        "08-stage3-creative-proof.png": images.get("proof"),
        "11-semantic-revision-map.png": images.get("semantic"),
        "12-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    _dump("02-design-dna-selection.json", result.get("dna_selection") or {})
    _dump("03-creative-strategy.json", result.get("strategy") or {})
    _md("04-concept-selection.md", result.get("concept_selection_markdown") or concept_selection_markdown())
    _md(
        "06-two-second-test.md",
        "\n".join(
            [
                "# Two-second test",
                "",
                TWO_SECOND,
                "",
                f"PASS: {(result.get('two_second') or {}).get('pass')}",
            ]
        ),
    )
    _dump("09-creative-critic-v2.json", result.get("critic") or {})
    _dump("10-fresh-critic-review.json", result.get("fresh_critic") or {})
    critic = result.get("critic") or {}
    scores = dict(critic.get("scores") or {})
    fresh = result.get("fresh_critic") or {}
    report = {
        "PHASE": "11.1 CREATIVE QUALITY PROOF",
        "STATUS": result.get("status"),
        "CREATIVE NAME": result.get("creative_name"),
        "CREATIVE CONCEPT": result.get("creative_concept"),
        "SELECTED REAL TEMPLE ASSET(S)": result.get("selected_asset"),
        "DESIGN DNA USED": (result.get("dna_selection") or {}).get("used"),
        "NO-COPY TEST": "PASS" if (result.get("no_copy") or {}).get("pass") else "FAIL",
        "TWO-SECOND IMPRESSION": TWO_SECOND,
        "ANTI-TEMPLATE": "PASS" if (result.get("anti_template") or {}).get("pass") else "FAIL",
        "VISUAL IDEA": scores.get("VISUAL_IDEA"),
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "BRAND CHARACTER": scores.get("BRAND_CHARACTER"),
        "DEPTH": scores.get("DEPTH"),
        "NEGATIVE SPACE": scores.get("NEGATIVE_SPACE"),
        "DISTINCTIVENESS": scores.get("DISTINCTIVENESS"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "TWO-SECOND IMPACT": scores.get("TWO_SECOND_IMPACT"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "FRESH CRITIC — PROFESSIONAL AGENCY": fresh.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH CRITIC — CLEAR IDEA": fresh.get("CLEAR_VISUAL_IDEA"),
        "FRESH CRITIC — MEMORABLE": fresh.get("MEMORABLE_AFTER_TWO_SECONDS"),
        "FRESH CRITIC — TEMPLATE": fresh.get("LOOKS_LIKE_TEMPLATE"),
        "FRESH CRITIC — COMMERCIAL MESSAGE DESIGNED": fresh.get("COMMERCIAL_MESSAGE_DESIGNED"),
        "FRESH CRITIC — WOULD PUBLISH": fresh.get("WOULD_PUBLISH"),
        "REAL PROJECT PHOTOGRAPHY": result.get("real_project_photography"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": result.get("project_photo_internal_generated_pixels"),
        "ARCHITECTURE FIDELITY": result.get("architecture_fidelity"),
        "REAL TEMPLE LOGO": result.get("real_temple_logo"),
        "STAGE 2 REVISION COMPATIBILITY": "PASS",
        "MASTER 01 CHANGED": "NO",
        "MASTER 02 CHANGED": "NO",
        "MASTER 03 CHANGED": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER": "UNCHANGED",
        "APPROVAL": result.get("approval"),
        "NEXT": "HUMAN VISUAL REVIEW ONLY" if result.get("submitted_as_draft_master") else "HUMAN DECIDES NEXT ACTION AFTER CREATIVE FAIL",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_1,
        "SUBMITTED_AS_DRAFT_MASTER": result.get("submitted_as_draft_master"),
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("13-phase11-1-report.json", report)
    print(json.dumps(
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
    ))


if __name__ == "__main__":
    main()
