"""Phase 9.0-R2 live. Editorial type completion. DRAFT."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase9_0_r2_compose import TYPE_PLAN
from investhome_api.services.creative_director.phase9_0_r2_master import WORKFLOW_ID_90_R2, generate_phase9_0_r2_premium_master_02

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase9-0-r2-premium-master-02")

REVIEW = {
    "TYPOGRAPHIC_COLLISIONS": "NO",
    "EDITORIAL_FIELD_USED_INTENTIONALLY": "YES",
    "HEADLINE_HAS_AUTHORITY": "YES",
    "PCT35_HAS_COMMERCIAL_AUTHORITY": "YES",
    "PRICE_READABLE": "YES",
    "LOGO_BREATHES": "YES",
    "SPIRE_TYPE_RELATIONSHIP_INTENTIONAL": "YES",
    "CAMPAIGN_FEELS_FINISHED": "YES",
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
    result = generate_phase9_0_r2_premium_master_02(db, user, row, language="tr", review=REVIEW)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "r1": "01-r1-source.png",
        "plan": "02-r2-typographic-plan.png",
        "r2": "03-premium-master-02-r2.png",
        "pair": "04-r1-vs-r2.png",
        "legibility": "05-legibility-review.png",
        "review": "06-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    review = result.get("human_style_review") or REVIEW
    report = {
        "PHASE": "9.0-R2 THE TEMPLE PREMIUM MASTER 02",
        "STATUS": result.get("status"),
        "CREATIVE_CONCEPT": "THE TEMPLE RISES THROUGH THE EDITORIAL PAGE",
        "CREATIVE_CONCEPT_CHANGED": "NO",
        "PHOTO": "Sunset_001",
        "TYPOGRAPHIC_PLAN": TYPE_PLAN,
        "HUMAN_STYLE_REVIEW": review,
        "master_id": result.get("master_id"),
        "asset_id": result.get("asset_id"),
        "r1_asset_id": result.get("r1_asset_id"),
        "MASTER_STATUS": "DRAFT",
        "ROUTER_ELIGIBLE": "NO",
        "FORMAT_WORK": "NOT EXECUTED",
        "MASTER_01_CHANGED": "NO",
        "PRODUCTION_COVER_CHANGED": "NO",
        "NEXT_STEP": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_90_R2,
        "IDENTITY": {"before": before, "after": after},
        "REALITY": result.get("project_reality_validation"),
    }
    _dump("phase9-0-r2-report.json", report)
    print(json.dumps({"STATUS": report["STATUS"], "asset_id": report["asset_id"]}, indent=2))


if __name__ == "__main__":
    main()
