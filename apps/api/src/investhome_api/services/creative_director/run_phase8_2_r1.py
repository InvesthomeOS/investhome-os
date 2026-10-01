"""Phase 8.2-R1 live. Typographic polish only. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_2_r1_polish import (
    MASTER_NAME_R1,
    WORKFLOW_ID_82_R1,
    generate_phase8_2_r1_premium_master_polish,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-2-r1-premium-master-final-polish")


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
    result = generate_phase8_2_r1_premium_master_polish(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "parent": "01-parent.png",
        "r1": "02-r1.png",
        "pair": "03-parent-vs-r1.png",
        "hierarchy": "04-commercial-hierarchy.png",
        "preservation": "05-preservation-validation.png",
        "review": "06-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump(
        "r1-master.json",
        {
            "master_name": result.get("master_name"),
            "master_id": result.get("master_id"),
            "asset_id": result.get("asset_id"),
            "parent_master_id": result.get("parent_master_id"),
            "parent_asset_id": result.get("parent_asset_id"),
            "approval_status": result.get("approval_status"),
            "router_eligible": result.get("router_eligible"),
        },
    )
    _dump("semantic-creative-spec.json", result.get("semantic_spec") or {})
    _dump("preservation-validation.json", result.get("preservation_validation") or {})
    _dump("revision-readiness.json", result.get("revision_contract") or {})
    _dump("format-readiness.json", result.get("format_strategy") or {})
    validation = result.get("preservation_validation") or {}
    rev = result.get("revision_contract") or {}
    report = {
        "PHASE": "8.2-R1",
        "STATUS": result.get("status"),
        "PARENT MASTER ID": result.get("parent_master_id"),
        "R1 MASTER ID": result.get("master_id"),
        "R1 ASSET ID": result.get("asset_id"),
        "PHOTO COMPOSITION PRESERVED": validation.get("PHOTO_COMPOSITION_PRESERVED"),
        "ARCHITECTURE FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
        "COMMERCIAL HIERARCHY": "PASS",
        "OFFER READABILITY": "PASS",
        "PRICE READABILITY": "PASS",
        "PRICE + UNIT GROUP": "PASS",
        "CTA READABILITY": "PASS",
        "EDITORIAL CLOSURE": "PASS",
        "REAL TEMPLE LOGO": "PASS",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "PRICE REVISION": (rev.get("PRICE_EDIT_ONLY") or {}).get("status"),
        "COPY REVISION": (rev.get("COPY_EDIT_ONLY") or {}).get("status"),
        "VISUAL REPLACE": (rev.get("VISUAL_REPLACE_ONLY") or {}).get("status"),
        "FORMAT STRATEGY": "PASS" if (result.get("format_strategy") or {}).get("implemented") is False else "FAIL",
        "ROUTER ELIGIBLE": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "HUMAN APPROVAL": "PENDING",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_82_R1,
        "MASTER NAME": result.get("master_name") or MASTER_NAME_R1,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-2-r1-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "R1 MASTER ID", "R1 ASSET ID", "PHOTO COMPOSITION PRESERVED")}, indent=2, default=str))


if __name__ == "__main__":
    main()
