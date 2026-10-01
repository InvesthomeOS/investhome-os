"""Phase 6.2 live. Native Day_007 composition. Do not promote. Do not create R1."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_2_real_photo_native import (
    WORKFLOW_ID_62,
    generate_phase6_2_native_composition,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase6-2-real-photo-native-composition")


def _save(img, name: str) -> None:
    img.save(OUT / name, format="PNG")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase6_2_native_composition(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "concept": "01-approved-concept3.png",
        "photo": "02-real-day007.png",
        "map": "03-real-photo-composition-map.png",
        "plan": "04-creative-direction-transfer-plan.png",
        "sketch_a": "05-sketch-A.png",
        "sketch_b": "06-sketch-B.png",
        "sketch_c": "07-sketch-C.png",
        "compare": "08-sketch-comparison.png",
        "sketch_critic": "09-sketch-critic.png",
        "master": "10-selected-structured-master.png",
        "vs_concept": "11-concept3-vs-final.png",
        "vs_photo": "12-real-photo-vs-final.png",
        "final_critic": "13-final-visual-critic.png",
        "revision": "14-revision-readiness.png",
        "assets": "15-real-asset-validation.png",
        "review": "16-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("real-photo-composition-map.json", result.get("real_photo_composition_map") or {})
    _dump("creative-direction-transfer-plan.json", result.get("creative_direction_transfer_plan") or {})
    _dump("sketches.json", result.get("sketch_scores") or {})
    _dump("sketch-critic.json", result.get("sketch_critic") or {})
    _dump("selected-master-spec.json", result.get("selected_master_spec") or {})
    _dump("final-visual-critic.json", result.get("final_visual_critic") or {})
    _dump("revision-readiness.json", result.get("revision_readiness") or {})
    _dump("real-asset-validation.json", result.get("real_asset_validation") or {})
    scores = (result.get("final_visual_critic") or {}).get("scores") or {}
    report = {
        "PHASE": "6.2 REAL PHOTO NATIVE COMPOSITION",
        "STATUS": result.get("status"),
        "APPROVED CAMPAIGN DIRECTION": result.get("approved_campaign_direction"),
        "REAL PHOTO": result.get("real_photo"),
        "REAL TEMPLE LOGO": result.get("logo_asset_id"),
        "SKETCH A": ((result.get("sketch_scores") or {}).get("A") or {}).get("scores"),
        "SKETCH B": ((result.get("sketch_scores") or {}).get("B") or {}).get("scores"),
        "SKETCH C": ((result.get("sketch_scores") or {}).get("C") or {}).get("scores"),
        "SELECTED SKETCH": result.get("selected_sketch"),
        "FINAL CANDIDATE": {"asset_id": result.get("candidate_asset_id"), "master_spec_id": result.get("master_spec_id")},
        "FINAL VISUAL SCORES": scores,
        "REAL PHOTO INTEGRATION": scores.get("real_photo_integration"),
        "CAMPAIGN FAMILY FIDELITY": scores.get("campaign_family_fidelity"),
        "ARCHITECTURE FIDELITY": scores.get("architecture_fidelity"),
        "REVISION READINESS": (result.get("revision_readiness") or {}).get("checks"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "PROMOTED": False,
        "PRODUCTION COVER CHANGED": False,
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_62,
        "MISSED GATES": result.get("missed_gates"),
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase6-2-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "SELECTED SKETCH", "FINAL CANDIDATE", "GPT IMAGE CALLS", "MISSED GATES")}, indent=2, default=str))


if __name__ == "__main__":
    main()
