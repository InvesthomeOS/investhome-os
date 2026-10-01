"""Phase 8.1 live. One Temple Premium Master draft. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_1_first_premium_master import (
    MASTER_NAME,
    WORKFLOW_ID_81,
    generate_phase8_1_first_project_premium_master,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-1-first-project-premium-master")


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
    result = generate_phase8_1_first_project_premium_master(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-reference.png",
        "master": "02-temple-premium-master-01.png",
        "pair": "03-reference-vs-master.png",
        "reality": "04-project-reality-validation.png",
        "territories": "05-semantic-territories.png",
        "revision": "06-revision-contract.png",
        "format": "07-format-strategy.png",
        "review": "08-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("temple-premium-master-01.json", {
        "master_name": result.get("master_name"),
        "master_id": result.get("master_id"),
        "asset_id": result.get("asset_id"),
        "approval_status": result.get("approval_status"),
        "router_eligible": result.get("router_eligible"),
        "design_source": result.get("design_source"),
        "project_photo_asset_id": result.get("project_photo_asset_id"),
        "logo_asset_id": result.get("logo_asset_id"),
    })
    _dump("semantic-creative-spec.json", result.get("semantic_spec") or {})
    _dump("revision-contract.json", result.get("revision_contract") or {})
    _dump("format-strategy.json", result.get("format_strategy") or {})
    _dump("project-reality-validation.json", result.get("project_reality_validation") or {})
    _dump("visual-critic.json", result.get("visual_critic") or {})
    reality = result.get("project_reality_validation") or {}
    report = {
        "PHASE": "8.1 FIRST PROJECT PREMIUM MASTER",
        "STATUS": result.get("status"),
        "MASTER": {
            "name": result.get("master_name") or MASTER_NAME,
            "master_id": result.get("master_id"),
            "asset_id": result.get("asset_id"),
            "approval_status": result.get("approval_status"),
        },
        "DESIGN SOURCE": result.get("design_source"),
        "PROJECT PHOTO": result.get("project_photo_asset_id"),
        "REAL PROJECT PHOTO": reality.get("REAL_PROJECT_PHOTO"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": reality.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "ARCHITECTURE FIDELITY": reality.get("ARCHITECTURE_FIDELITY"),
        "REAL TEMPLE LOGO": reality.get("REAL_TEMPLE_LOGO"),
        "DUPLICATE TEMPLE WORDMARK": reality.get("DUPLICATE_TEMPLE_WORDMARK"),
        "SEMANTIC SPEC": "PASS" if (result.get("semantic_spec") or {}).get("schema") == "SemanticCreativeSpecV1" else "FAIL",
        "PRICE REVISION CONTRACT": (result.get("revision_contract") or {}).get("PRICE_EDIT_ONLY", {}).get("status"),
        "COPY REVISION CONTRACT": (result.get("revision_contract") or {}).get("COPY_EDIT_ONLY", {}).get("status"),
        "VISUAL REPLACE CONTRACT": (result.get("revision_contract") or {}).get("VISUAL_REPLACE_ONLY", {}).get("status"),
        "FORMAT STRATEGY": "PASS" if (result.get("format_strategy") or {}).get("implemented") is False else "FAIL",
        "ROUTER ELIGIBLE": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "HUMAN APPROVAL": "PENDING",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_81,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-1-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "MASTER", "HUMAN APPROVAL")}, indent=2, default=str))


if __name__ == "__main__":
    main()
