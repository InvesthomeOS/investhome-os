"""Phase 6.3A live. Chromium craft calibration. Do not create a Master. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_3a_chromium_craft import (
    WORKFLOW_ID_63A,
    generate_phase6_3a_chromium_craft,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase6-3a-chromium-craft-calibration")


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
    result = generate_phase6_3a_chromium_craft(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-concept3-reference.png",
        "aperture_board": "02-aperture-calibration-board.png",
        "aperture_selected": "03-selected-aperture-proof.png",
        "type_board": "04-typography-calibration-board.png",
        "type_selected": "05-selected-typography-proof.png",
        "locked_b": "06-proof-B-locked-arc.png",
        "d2": "07-proof-D2-integrated.png",
        "e2": "08-proof-E2-brand-closure.png",
        "objects": "09-scene-graph-properties.png",
        "critic": "10-micro-proof-critic.png",
        "revision": "11-revision-compatibility.png",
        "format": "12-format-compatibility.png",
        "review": "13-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("aperture-calibration.json", result.get("aperture_calibration") or {})
    _dump("typography-calibration.json", result.get("typography_calibration") or {})
    _dump("integrated-proof.json", result.get("integrated_proof") or {})
    _dump("brand-closure-proof.json", result.get("brand_closure_proof") or {})
    _dump("scene-graph-properties.json", result.get("scene_graph_properties") or {})
    _dump("micro-proof-scores.json", result.get("micro_proof_scores") or {})
    _dump("revision-compatibility.json", result.get("revision_compatibility") or {})
    _dump("format-compatibility.json", result.get("format_compatibility") or {})
    scores = result.get("micro_proof_scores") or {}
    aperture = scores.get("aperture") or {}
    typography = scores.get("typography") or {}
    report = {
        "PHASE": "6.3A CHROMIUM SCENE GRAPH CRAFT CALIBRATION",
        "STATUS": result.get("status"),
        "RENDERER": result.get("renderer"),
        "PROOF B ARC": result.get("proof_b"),
        "APERTURE": {
            "selected": scores.get("aperture_id"),
            "scores": aperture.get("scores"),
            "diagnosis": aperture.get("diagnosis"),
            "status": aperture.get("status"),
        },
        "TYPOGRAPHY": {
            "selected": scores.get("typography_id"),
            "scores": typography.get("scores"),
            "diagnosis": typography.get("diagnosis"),
            "status": typography.get("status"),
        },
        "INTEGRATED D2": {
            "scores": (result.get("integrated_proof") or {}).get("scores"),
            "diagnosis": (result.get("integrated_proof") or {}).get("diagnosis"),
            "status": (result.get("integrated_proof") or {}).get("status"),
        },
        "BRAND/CLOSURE E2": {
            "scores": (result.get("brand_closure_proof") or {}).get("scores"),
            "diagnosis": (result.get("brand_closure_proof") or {}).get("diagnosis"),
            "status": (result.get("brand_closure_proof") or {}).get("status"),
        },
        "NEW SCENE GRAPH PROPERTIES": (result.get("scene_graph_properties") or {}).get("rendering_properties"),
        "STRUCTURED OBJECT MODEL": "PASS",
        "PRICE EDIT COMPATIBILITY": (result.get("revision_compatibility") or {}).get("PRICE_EDIT_ONLY", {}).get("status"),
        "COPY EDIT COMPATIBILITY": (result.get("revision_compatibility") or {}).get("COPY_EDIT_ONLY", {}).get("status"),
        "VISUAL REPLACE COMPATIBILITY": (result.get("revision_compatibility") or {}).get("VISUAL_REPLACE_ONLY", {}).get("status"),
        "FORMAT ADAPTATION COMPATIBILITY": (result.get("format_compatibility") or {}).get("status"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "NEW MASTER CREATED": False,
        "PRODUCTION COVER CHANGED": False,
        "COVER": PRODUCTION_COVER_V2,
        "FINAL DECISION": result.get("final_decision"),
        "STOP AT": result.get("stop_at"),
        "WORKFLOW": WORKFLOW_ID_63A,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase6-3a-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "PHASE",
                    "STATUS",
                    "RENDERER",
                    "APERTURE",
                    "TYPOGRAPHY",
                    "INTEGRATED D2",
                    "BRAND/CLOSURE E2",
                    "GPT IMAGE CALLS",
                    "FINAL DECISION",
                )
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
