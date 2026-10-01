"""Phase 6.3B live. Integrated Chromium craft proof. Do not create a Master."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_3b_integrated_craft import (
    WORKFLOW_ID_63B,
    generate_phase6_3b_integrated_craft,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase6-3b-integrated-craft-proof")


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
    result = generate_phase6_3b_integrated_craft(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-concept3-reference.png",
        "T1": "02-typography-study-T1.png",
        "T2": "03-typography-study-T2.png",
        "T3": "04-typography-study-T3.png",
        "T4": "05-typography-study-T4.png",
        "type_compare": "06-typography-comparison.png",
        "type_selected": "07-selected-typography.png",
        "d2": "08-D2-integrated.png",
        "d2_critic": "09-D2-critic.png",
        "e2": "10-E2-complete-scene.png",
        "e2_critic": "11-E2-critic.png",
        "compare": "12-concept3-vs-D2-vs-E2.png",
        "scene": "13-structured-scene-validation.png",
        "revision": "14-revision-compatibility.png",
        "format": "15-format-compatibility.png",
        "review": "16-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("typography-calibration.json", result.get("typography_calibration") or {})
    _dump("D2-integrated-proof.json", result.get("d2") or {})
    _dump("D2-critic.json", result.get("d2") or {})
    _dump("E2-complete-proof.json", result.get("e2") or {})
    _dump("E2-critic.json", result.get("e2") or {})
    _dump("structured-scene-validation.json", result.get("structured_scene_validation") or {})
    _dump("revision-compatibility.json", result.get("revision_compatibility") or {})
    _dump("format-compatibility.json", result.get("format_compatibility") or {})
    aperture = result.get("aperture") or {}
    report = {
        "PHASE": "6.3B CHROMIUM INTEGRATED CRAFT PROOF",
        "STATUS": result.get("status"),
        "RENDERER": result.get("renderer"),
        "APERTURE": aperture,
        "ARC": result.get("proof_b"),
        "SELECTED TYPOGRAPHY": {
            "id": result.get("selected_typography"),
            "scores": ((result.get("typography_calibration") or {}).get("treatments") or {}).get(result.get("selected_typography") or "", {}).get("scores"),
            "status": ((result.get("typography_calibration") or {}).get("treatments") or {}).get(result.get("selected_typography") or "", {}).get("status"),
        },
        "D2": result.get("d2"),
        "E2": result.get("e2"),
        "REAL TEMPLE LOGO": result.get("real_temple_logo"),
        "STRUCTURED SCENE": (result.get("structured_scene_validation") or {}).get("status"),
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
        "WORKFLOW": WORKFLOW_ID_63B,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase6-3b-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "PHASE",
                    "STATUS",
                    "RENDERER",
                    "APERTURE",
                    "SELECTED TYPOGRAPHY",
                    "D2",
                    "E2",
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
