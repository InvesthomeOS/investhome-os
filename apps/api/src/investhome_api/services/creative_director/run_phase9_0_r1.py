"""Phase 9.0-R1 live. Composition rebuild of Premium Campaign 02. DRAFT."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase9_0_r1_compose import CONCEPT
from investhome_api.services.creative_director.phase9_0_r1_master import WORKFLOW_ID_90_R1, generate_phase9_0_r1_premium_master_02

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase9-0-r1-premium-master-02")


def _save(img, name: str) -> None:
    img.save(OUT / name, format="PNG")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _dump("creative-concept-r1.json", CONCEPT)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase9_0_r1_premium_master_02(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-reference-source.png",
        "sunset": "02-sunset-001-source.png",
        "logo": "03-real-temple-logo.png",
        "concept": "04-creative-concept-r1.png",
        "r1": "05-premium-master-02-r1.png",
        "vs_parent": "06-master02-vs-r1.png",
        "vs_ref": "07-reference-vs-r1.png",
        "test": "08-creative-test.png",
        "reality": "09-project-reality-validation.png",
        "review": "10-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    if images.get("canvas") is not None:
        _save(images["canvas"], "00-designed-canvas-without-type.png")
    test = result.get("creative_test") or {}
    reality = result.get("project_reality_validation") or {}
    _dump("creative-test-r1.json", test)
    _dump("project-reality-validation-r1.json", reality)
    report = {
        "PHASE": "9.0-R1 THE TEMPLE PREMIUM MASTER 02",
        "STATUS": result.get("status"),
        "CREATIVE_CONCEPT": CONCEPT["concept_sentence"],
        "PHOTO": "Sunset_001",
        "REFERENCE": "ORNEK_00012",
        "CREATIVE_TEST": {
            "CLEAR_IDEA_BEYOND_PHOTO_PLUS_TEXT": test.get("CLEAR_IDEA_BEYOND_PHOTO_PLUS_TEXT"),
            "PHOTO_PARTICIPATES_IN_GRAPHIC_COMPOSITION": test.get("PHOTO_PARTICIPATES_IN_GRAPHIC_COMPOSITION"),
            "DESIGNED_CANVAS_WITHOUT_COPY": test.get("DESIGNED_CANVAS_WITHOUT_COPY"),
            "ARCHITECTURE_PARTICIPATES_IN_IDEA": test.get("ARCHITECTURE_PARTICIPATES_IN_IDEA"),
            "COMMERCIAL_INFORMATION_DESIGNED": test.get("COMMERCIAL_INFORMATION_DESIGNED"),
            "PROFESSIONAL_CAMPAIGN": test.get("PROFESSIONAL_CAMPAIGN"),
        },
        "PROJECT_REALITY": reality,
        "master_id": result.get("master_id"),
        "asset_id": result.get("asset_id"),
        "rejected_asset_id": result.get("rejected_asset_id"),
        "MASTER_STATUS": "DRAFT",
        "ROUTER_ELIGIBLE": "NO",
        "FORMAT_WORK": "NOT EXECUTED",
        "MASTER_01_CHANGED": "NO",
        "PRODUCTION_COVER_CHANGED": "NO",
        "NEXT_STEP": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "WORKFLOW": WORKFLOW_ID_90_R1,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase9-0-r1-report.json", report)
    print(json.dumps({"STATUS": report["STATUS"], "asset_id": report["asset_id"], "master_id": report["master_id"]}, indent=2))


if __name__ == "__main__":
    main()
