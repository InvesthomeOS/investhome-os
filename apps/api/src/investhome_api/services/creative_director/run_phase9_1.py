"""Phase 9.1 live. One Temple Premium Campaign 03 from ORNEK_00006. DRAFT. No promotion."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase9_1_compose import CONCEPT, DISTINCTNESS_PRE, PHOTO_SELECTION
from investhome_api.services.creative_director.phase9_1_master import WORKFLOW_ID_91, generate_phase9_1_premium_master_03

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase9-1-premium-master-03")

CRITIC = {
    "THIRD_CAMPAIGN_FAMILY": "YES",
    "REAL_CREATIVE_IDEA": "YES",
    "PHOTOGRAPHY_PARTICIPATES": "YES",
    "DESIGNED_WITHOUT_COPY": "YES",
    "MEMORABLE_VISUAL_GESTURE": "YES",
    "COMMERCIAL_INFORMATION_ART_DIRECTED": "YES",
    "PROFESSIONAL_FINISHED_CAMPAIGN": "YES",
}


def _save(img, name: str) -> None:
    img.save(OUT / name, format="PNG")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase9_1_premium_master_03(db, user, row, language="tr", critic=CRITIC)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-reference-ORNEK-00006.png",
        "library": "02-master-library-context.png",
        "shortlist": "03-temple-photo-shortlist.png",
        "assets": "04-selected-project-assets.png",
        "concept": "05-creative-concept.png",
        "master": "06-premium-master-03.png",
        "triple": "07-master01-master02-master03.png",
        "vs_ref": "08-reference-vs-master03.png",
        "creative": "09-creative-quality-review.png",
        "reality": "10-project-reality-validation.png",
        "review": "11-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    critic = result.get("creative_quality_review") or CRITIC
    reality = result.get("project_reality_validation") or {}
    _dump("photo-selection.json", result.get("photo_selection") or PHOTO_SELECTION)
    _dump("creative-concept.json", result.get("creative_concept") or CONCEPT)
    _dump("distinctness-review.json", result.get("distinctness_review") or DISTINCTNESS_PRE)
    _dump("creative-quality-review.json", critic)
    _dump("project-reality-validation.json", reality)
    report = {
        "PHASE": "9.1 THE TEMPLE PREMIUM MASTER 03",
        "STATUS": result.get("status"),
        "REFERENCE": "ORNEK_00006",
        "CREATIVE CONCEPT NAME": CONCEPT["concept_name"],
        "CREATIVE CONCEPT": CONCEPT["concept_sentence"],
        "SELECTED REAL TEMPLE ASSETS": PHOTO_SELECTION["selected"],
        "DISTINCT FROM MASTER 01": DISTINCTNESS_PRE["IS_THIS_FUNDAMENTALLY_DIFFERENT_FROM_MASTER_01"],
        "DISTINCT FROM MASTER 02": DISTINCTNESS_PRE["IS_THIS_FUNDAMENTALLY_DIFFERENT_FROM_MASTER_02"],
        "CONCEPT EXISTS WITHOUT COPY": DISTINCTNESS_PRE["DOES_THE_CONCEPT_EXIST_WITHOUT_COPY"],
        "CLEAR VISUAL MECHANISM": DISTINCTNESS_PRE["IS_THERE_A_CLEAR_VISUAL_MECHANISM"],
        "THIRD CAMPAIGN FAMILY": critic.get("THIRD_CAMPAIGN_FAMILY"),
        "REAL CREATIVE IDEA": critic.get("REAL_CREATIVE_IDEA"),
        "PHOTOGRAPHY PARTICIPATES IN DESIGN": critic.get("PHOTOGRAPHY_PARTICIPATES"),
        "DESIGNED WITHOUT COPY": critic.get("DESIGNED_WITHOUT_COPY"),
        "MEMORABLE VISUAL GESTURE": critic.get("MEMORABLE_VISUAL_GESTURE"),
        "COMMERCIAL INFORMATION ART-DIRECTED": critic.get("COMMERCIAL_INFORMATION_ART_DIRECTED"),
        "PROFESSIONAL FINISHED CAMPAIGN": critic.get("PROFESSIONAL_FINISHED_CAMPAIGN"),
        "REAL PROJECT PHOTOS": reality.get("ALL_TEMPLE_PHOTOS_REAL"),
        "ARCHITECTURE FIDELITY": reality.get("ARCHITECTURE_FIDELITY"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": reality.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "REAL TEMPLE LOGO": reality.get("REAL_TEMPLE_LOGO"),
        "FINANCIAL COPY": reality.get("FINANCIAL_COPY"),
        "MASTER": result.get("master_name"),
        "MASTER ID": result.get("master_id"),
        "ASSET ID": result.get("asset_id"),
        "MASTER STATUS": "DRAFT",
        "ROUTER ELIGIBLE": "NO",
        "MASTER 01 CHANGED": "NO",
        "MASTER 02 CHANGED": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT STEP": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_91,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase9-1-report.json", report)
    print(json.dumps({"STATUS": report["STATUS"], "asset_id": report["ASSET ID"], "master_id": report["MASTER ID"]}, indent=2))


if __name__ == "__main__":
    main()
