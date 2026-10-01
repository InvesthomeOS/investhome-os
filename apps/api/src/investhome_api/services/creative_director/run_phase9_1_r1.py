"""Phase 9.1-R1 live. Looking Chamber spatial reveal. DRAFT. No promotion."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase9_1_r1_compose import CONCEPT_R1
from investhome_api.services.creative_director.phase9_1_r1_master import WORKFLOW_ID_91_R1, generate_phase9_1_r1_premium_master_03

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase9-1-r1-premium-master-03")

CRITIC = {
    "LOOKING_CHAMBER_IDEA_VISUALLY_OBVIOUS": "YES",
    "EXTERIOR_STRUCTURALLY_INTEGRATED": "YES",
    "INTERIOR_GEOMETRY_PARTICIPATES": "YES",
    "PHOTO_CARD_FEELING": "NO",
    "GENERIC_DARK_HEADER_FEELING": "NO",
    "THREE_DIMENSIONAL_VISUAL_DEPTH": "YES",
    "CLEAR_THIRD_CAMPAIGN_FAMILY": "YES",
    "PROFESSIONAL_CAMPAIGN": "YES",
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
    result = generate_phase9_1_r1_premium_master_03(db, user, row, language="tr", critic=CRITIC)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "rejected": "01-master03-rejected.png",
        "reference": "02-reference.png",
        "interior": "03-real-interior.png",
        "exterior": "04-real-exterior.png",
        "mechanism": "05-creative-mechanism.png",
        "r1": "06-premium-master-03-r1.png",
        "pair": "07-master03-vs-r1.png",
        "vs_ref": "08-reference-vs-r1.png",
        "remove_text": "09-remove-text-test.png",
        "creative": "10-creative-review.png",
        "review": "11-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    critic = result.get("creative_quality_review") or CRITIC
    reality = result.get("project_reality_validation") or {}
    _dump("creative-concept-r1.json", CONCEPT_R1)
    report = {
        "PHASE": "9.1-R1 THE TEMPLE PREMIUM MASTER 03",
        "STATUS": result.get("status"),
        "CONCEPT": CONCEPT_R1["concept_name"],
        "CREATIVE MECHANISM": CONCEPT_R1["mechanism_sentence"],
        "LOOKING CHAMBER IDEA VISUALLY OBVIOUS": critic.get("LOOKING_CHAMBER_IDEA_VISUALLY_OBVIOUS"),
        "EXTERIOR STRUCTURALLY INTEGRATED": critic.get("EXTERIOR_STRUCTURALLY_INTEGRATED"),
        "INTERIOR GEOMETRY PARTICIPATES": critic.get("INTERIOR_GEOMETRY_PARTICIPATES"),
        "PHOTO CARD FEELING": critic.get("PHOTO_CARD_FEELING"),
        "GENERIC DARK HEADER FEELING": critic.get("GENERIC_DARK_HEADER_FEELING"),
        "THREE-DIMENSIONAL VISUAL DEPTH": critic.get("THREE_DIMENSIONAL_VISUAL_DEPTH"),
        "CLEAR THIRD CAMPAIGN FAMILY": critic.get("CLEAR_THIRD_CAMPAIGN_FAMILY"),
        "PROFESSIONAL CAMPAIGN": critic.get("PROFESSIONAL_CAMPAIGN"),
        "REAL INTERIOR": reality.get("REAL_INTERIOR"),
        "REAL EXTERIOR": reality.get("REAL_EXTERIOR"),
        "ARCHITECTURE FIDELITY": reality.get("ARCHITECTURE_FIDELITY"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": reality.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "REAL TEMPLE LOGO": reality.get("REAL_TEMPLE_LOGO"),
        "FINANCIAL COPY": reality.get("FINANCIAL_COPY"),
        "MASTER STATUS": "DRAFT",
        "ROUTER ELIGIBLE": "NO",
        "MASTER 01 CHANGED": "NO",
        "MASTER 02 CHANGED": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "master_id": result.get("master_id"),
        "asset_id": result.get("asset_id"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_91_R1,
        "IDENTITY": {"before": before, "after": after},
        "CRITIC": critic,
        "REALITY": reality,
    }
    _dump("phase9-1-r1-report.json", report)
    print(json.dumps({"STATUS": report["STATUS"], "asset_id": report["asset_id"]}, indent=2))


if __name__ == "__main__":
    main()
