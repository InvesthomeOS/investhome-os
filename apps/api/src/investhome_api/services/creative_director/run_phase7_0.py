"""Phase 7.0 live. Visual master candidates. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase7_0_doctrine import (
    MASTER_TYPE,
    PRIMARY_CREATIVE_ENGINE,
    PRODUCTION_DOCTRINE,
)
from investhome_api.services.creative_director.phase7_0_production_reset import (
    WORKFLOW_ID_70,
    generate_phase7_0_production_reset,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase7-0-production-architecture-reset")


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
    result = generate_phase7_0_production_reset(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "doctrine": "01-production-doctrine.png",
        "flow": "02-architecture-flow.png",
        "spec": "03-semantic-creative-spec.png",
        "revision": "04-revision-contract.png",
        "format": "05-format-adaptation-spec.png",
        "A": "06-final-candidate-A.png",
        "B": "07-final-candidate-B.png",
        "C": "08-final-candidate-C.png",
        "compare": "09-final-candidate-comparison.png",
        "review": "10-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("semantic-creative-spec-v1.json", result.get("semantic_creative_spec") or {})
    _dump("semantic-revision-contract-v1.json", result.get("semantic_revision_contract") or {})
    _dump("format-adaptation-spec-v1.json", result.get("format_adaptation_spec_payload") or {})
    _dump("production-doctrine.json", result.get("production_doctrine_payload") or {})
    cands = result.get("candidates") or {}
    report = {
        "PHASE": "7.0 PRODUCTION CREATIVE ARCHITECTURE RESET",
        "STATUS": result.get("status"),
        "PRODUCTION DOCTRINE": PRODUCTION_DOCTRINE,
        "PRIMARY CREATIVE ENGINE": PRIMARY_CREATIVE_ENGINE,
        "MASTER TYPE": MASTER_TYPE,
        "SEMANTIC SPEC": result.get("semantic_spec_status"),
        "PRICE REVISION CONTRACT": result.get("price_revision_contract"),
        "COPY REVISION CONTRACT": result.get("copy_revision_contract"),
        "VISUAL REPLACE CONTRACT": result.get("visual_replace_contract"),
        "FORMAT ADAPTATION SPEC": result.get("format_adaptation_spec"),
        "CANDIDATE A": cands.get("A"),
        "CANDIDATE B": cands.get("B"),
        "CANDIDATE C": cands.get("C"),
        "RECOMMENDED HUMAN REVIEW CANDIDATE": result.get("recommended_human_review_candidate"),
        "NEW APPROVED MASTER": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "RESEARCH BRANCHES RETIRED": "YES",
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "WORKFLOW": WORKFLOW_ID_70,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase7-0-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "PHASE",
                    "STATUS",
                    "PRODUCTION DOCTRINE",
                    "RECOMMENDED HUMAN REVIEW CANDIDATE",
                    "GPT IMAGE CALLS",
                    "NEW APPROVED MASTER",
                )
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
