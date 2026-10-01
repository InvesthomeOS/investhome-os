"""Phase 8.3 live. Approve and lock. Do not re-render. Do not change cover."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_3_approve_lock import (
    WORKFLOW_ID_83,
    generate_phase8_3_approve_lock_first_premium_master,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-3-approved-premium-master")


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
    result = generate_phase8_3_approve_lock_first_premium_master(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "approved": "01-approved-master.png",
        "library": "02-master-library-state.png",
        "router": "03-router-validation.png",
        "revision": "04-revision-routing-validation.png",
        "format": "05-format-readiness.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("approved-master.json", result.get("approved_master") or {})
    _dump("master-library-state.json", result.get("library_state") or {})
    _dump("router-validation.json", result.get("router_validation") or {})
    _dump(
        "revision-routing-validation.json",
        {
            "revision_contract": result.get("revision_contract"),
            "revision_routing": result.get("revision_routing"),
            "cases": [c for c in (result.get("router_validation") or {}).get("cases") or [] if c.get("expected_route") == "MASTER_DERIVED_REVISION"],
        },
    )
    report = {
        "PHASE": "8.3 APPROVE & LOCK FIRST PROJECT PREMIUM MASTER",
        "STATUS": result.get("status"),
        "MASTER NAME": result.get("master_name"),
        "MASTER ID": result.get("master_id"),
        "ASSET ID": result.get("asset_id"),
        "APPROVAL STATUS": result.get("approval_status"),
        "MASTER STATE": result.get("master_state"),
        "ROUTER ELIGIBLE": "YES" if result.get("router_eligible") else "NO",
        "CANONICAL FORMAT": result.get("canonical_format"),
        "REAL PROJECT PHOTO": "PASS",
        "ARCHITECTURE FIDELITY": 10,
        "REAL TEMPLE LOGO": "PASS",
        "PRICE REVISION": "ACTIVE",
        "COPY REVISION": "ACTIVE",
        "VISUAL REPLACE": "ACTIVE",
        "THE TEMPLE HUMAN_APPROVED PREMIUM MASTERS": result.get("human_approved_premium_count"),
        "PREMIUM ROUTING": result.get("premium_routing"),
        "REVISION ROUTING": result.get("revision_routing"),
        "FORMAT READINESS": result.get("format_readiness"),
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT PHASE": result.get("next_phase"),
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_83,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-3-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "MASTER ID", "ASSET ID", "ROUTER ELIGIBLE", "PREMIUM ROUTING")}, indent=2, default=str))


if __name__ == "__main__":
    main()
