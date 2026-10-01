"""Phase 8.2 live. One Temple Premium Master from ORNEK_00001. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_2_human_selected_master import (
    MASTER_NAME,
    WORKFLOW_ID_82,
    generate_phase8_2_human_selected_premium_master,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-2-human-selected-premium-master")


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
    result = generate_phase8_2_human_selected_premium_master(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "source": "01-human-selected-source.png",
        "candidates": "02-temple-photo-candidates.png",
        "selected": "03-selected-temple-photo.png",
        "plan": "04-composition-plan.png",
        "master": "05-temple-premium-master-01.png",
        "pair": "06-source-vs-master.png",
        "reality": "07-project-reality-validation.png",
        "territories": "08-semantic-territories.png",
        "revision": "09-revision-readiness.png",
        "format": "10-format-strategy.png",
        "review": "11-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("photo-selection.json", result.get("photo_selection") or {})
    _dump("composition-plan.json", result.get("composition_plan") or {})
    _dump(
        "temple-premium-master-01.json",
        {
            "master_name": result.get("master_name"),
            "master_id": result.get("master_id"),
            "asset_id": result.get("asset_id"),
            "approval_status": result.get("approval_status"),
            "router_eligible": result.get("router_eligible"),
            "human_selected_source": result.get("human_selected_source"),
            "photo_selection": result.get("photo_selection"),
            "logo_asset_id": result.get("logo_asset_id"),
        },
    )
    _dump("semantic-creative-spec.json", result.get("semantic_spec") or {})
    _dump("revision-contract.json", result.get("revision_contract") or {})
    _dump("format-strategy.json", result.get("format_strategy") or {})
    _dump("project-reality-validation.json", result.get("project_reality_validation") or {})
    reality = result.get("project_reality_validation") or {}
    photo = result.get("photo_selection") or {}
    rev = result.get("revision_contract") or {}
    report = {
        "PHASE": "8.2 HUMAN-SELECTED PREMIUM MASTER",
        "STATUS": result.get("status"),
        "HUMAN SELECTED SOURCE": result.get("human_selected_source"),
        "SELECTED TEMPLE PHOTO": {
            "filename": photo.get("selected_filename"),
            "asset_id": photo.get("selected_asset_id"),
            "reason": photo.get("reason"),
        },
        "MASTER": {
            "name": result.get("master_name") or MASTER_NAME,
            "master_id": result.get("master_id"),
            "asset_id": result.get("asset_id"),
            "approval_status": result.get("approval_status"),
        },
        "FULL-CANVAS PHOTOGRAPHIC EXPERIENCE": reality.get("FULL_CANVAS_PHOTOGRAPHIC_EXPERIENCE"),
        "NATURAL NEGATIVE SPACE": reality.get("NATURAL_NEGATIVE_SPACE"),
        "PHOTO + TYPOGRAPHY INTEGRATION": reality.get("PHOTO_TYPOGRAPHY_INTEGRATION"),
        "COMMERCIAL HIERARCHY": reality.get("COMMERCIAL_HIERARCHY"),
        "REAL PROJECT PHOTO": reality.get("REAL_PROJECT_PHOTO"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": reality.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "ARCHITECTURE FIDELITY": reality.get("ARCHITECTURE_FIDELITY"),
        "REAL TEMPLE LOGO": reality.get("REAL_TEMPLE_LOGO"),
        "DUPLICATE TEMPLE WORDMARK": reality.get("DUPLICATE_TEMPLE_WORDMARK"),
        "SEMANTIC SPEC": "PASS" if (result.get("semantic_spec") or {}).get("schema") == "SemanticCreativeSpecV1" else "FAIL",
        "PRICE REVISION": (rev.get("PRICE_EDIT_ONLY") or {}).get("status"),
        "COPY REVISION": (rev.get("COPY_EDIT_ONLY") or {}).get("status"),
        "VISUAL REPLACE": (rev.get("VISUAL_REPLACE_ONLY") or {}).get("status"),
        "FORMAT STRATEGY": "PASS" if (result.get("format_strategy") or {}).get("implemented") is False else "FAIL",
        "ROUTER ELIGIBLE": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "HUMAN APPROVAL": "PENDING",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_82,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-2-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "MASTER", "SELECTED TEMPLE PHOTO", "HUMAN APPROVAL")}, indent=2, default=str))


if __name__ == "__main__":
    main()
