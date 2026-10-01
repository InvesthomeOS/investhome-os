"""Phase 8.0 live. Production model + Temple library bootstrap. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase8_0_production_model import (
    WORKFLOW_ID_80,
    generate_phase8_0_production_model,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-0-creative-studio-production-model")


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
    result = generate_phase8_0_production_model(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "model": "01-production-model.png",
        "library": "02-project-master-library.png",
        "routing": "03-master-routing-flow.png",
        "revision": "04-revision-routing-flow.png",
        "format": "05-format-readiness-model.png",
        "refs": "06-design-references-role.png",
        "bootstrap": "07-temple-library-bootstrap.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("project-creative-master-library-v1.json", result.get("library") or {})
    _dump("creative-master-router-v2.json", result.get("router_examples") or {})
    _dump("revision-router.json", result.get("revision_router") or {})
    _dump("format-strategy-schema.json", result.get("format_strategy") or {})
    _dump("design-references-policy.json", result.get("design_references_policy") or {})
    _dump("temple-master-library.json", result.get("library") or {})
    report = {
        "PHASE": "8.0 CREATIVE STUDIO PRODUCTION MODEL",
        "STATUS": result.get("status"),
        "PRODUCTION MODEL": result.get("production_model"),
        "PRODUCTION DOCTRINE": PRODUCTION_DOCTRINE,
        "PROJECT CREATIVE RULE": PROJECT_CREATIVE_RULE,
        "PROJECT MASTER LIBRARY": "PASS" if result.get("library_pass") else "FAIL",
        "MASTER ROUTER": "PASS" if result.get("router_pass") else "FAIL",
        "REVISION ROUTER": "PASS" if result.get("revision_pass") else "FAIL",
        "PRICE EDIT": result.get("price_edit"),
        "COPY EDIT": result.get("copy_edit"),
        "VISUAL REPLACE": result.get("visual_replace"),
        "FORMAT STRATEGY": "PASS" if result.get("format_strategy_pass") else "FAIL",
        "DESIGN_REFERENCES POLICY": "PASS" if result.get("design_references_pass") else "FAIL",
        "THE TEMPLE": {
            "HUMAN_APPROVED PREMIUM MASTERS": result.get("human_approved_premium_count"),
            "ARCHIVED RESEARCH MASTERS": result.get("archived_research_count"),
        },
        "AI QUICK CREATIVE": result.get("ai_quick_creative"),
        "PRODUCTION COVER CHANGED": "NO",
        "PHASE 7 CANDIDATES PROMOTED": result.get("phase7_candidates_promoted"),
        "NEW APPROVED MASTER": "NO",
        "PROMOTED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "NEXT PRODUCTION PHASE": result.get("next_production_phase"),
        "WORKFLOW": WORKFLOW_ID_80,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-0-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "NEXT PRODUCTION PHASE", "AI QUICK CREATIVE")}, indent=2, default=str))


if __name__ == "__main__":
    main()
