"""Phase 6.4 live. AI-native structured authoring. Do not create a Master."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_4_ai_native_authoring import (
    ARCHITECTURE,
    WORKFLOW_ID_64,
    generate_phase6_4_ai_native_authoring,
)
from investhome_api.services.creative_director.phase6_4_scene_v2 import SCENE_SCHEMA

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase6-4-ai-native-structured-authoring")


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
    result = generate_phase6_4_ai_native_authoring(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "concept": "01-concept3-reference.png",
        "day007": "02-real-day007.png",
        "logo": "03-real-temple-logo.png",
        "A": "04-scene-A-render.png",
        "B": "05-scene-B-render.png",
        "C": "06-scene-C-render.png",
        "compare": "07-scene-comparison.png",
        "critic": "08-visual-critic.png",
        "review": "09-human-review-board.png",
        "best_structure": "10-best-scene-structure.png",
        "revision": "11-revision-structure-check.png",
        "format": "12-format-structure-check.png",
        "architecture": "13-architecture-decision.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    payloads = result.get("scene_payloads") or {}
    validations = result.get("validations") or {}
    _dump("ai-creative-scene-v2-schema.json", result.get("schema") or SCENE_SCHEMA)
    _dump("scene-A.json", payloads.get("A") or {})
    _dump("scene-B.json", payloads.get("B") or {})
    _dump("scene-C.json", payloads.get("C") or {})
    _dump("scene-A-validation.json", validations.get("A") or {})
    _dump("scene-B-validation.json", validations.get("B") or {})
    _dump("scene-C-validation.json", validations.get("C") or {})
    _dump("visual-critic.json", result.get("visual_critic") or {})
    _dump(
        "best-scene-structure.json",
        {
            "best": result.get("best_scene"),
            "asset_id": result.get("best_scene_asset_id"),
            "structure_id": result.get("best_scene_structure_id"),
            "scene": payloads.get(result.get("best_scene") or "A") or {},
        },
    )
    _dump("revision-structure-check.json", result.get("revision_structure_check") or {})
    _dump("format-structure-check.json", result.get("format_structure_check") or {})
    scenes = result.get("scenes") or {}
    report = {
        "PHASE": "6.4 AI-NATIVE STRUCTURED DESIGN AUTHORING",
        "STATUS": result.get("status"),
        "ARCHITECTURE": ARCHITECTURE,
        "SCENE A": scenes.get("A"),
        "SCENE B": scenes.get("B"),
        "SCENE C": scenes.get("C"),
        "BEST SCENE": result.get("best_scene"),
        "BEST SCENE ASSET ID": result.get("best_scene_asset_id"),
        "BEST SCENE STRUCTURE ID": result.get("best_scene_structure_id"),
        "REAL DAY_007": result.get("real_day007"),
        "REAL TEMPLE LOGO": result.get("real_temple_logo"),
        "GENERATED ARCHITECTURE": result.get("generated_architecture"),
        "GENERATED LOGO": result.get("generated_logo"),
        "GENERATED TEXT RASTER": result.get("generated_text_raster"),
        "PRICE EDIT STRUCTURE": (result.get("revision_structure_check") or {}).get("PRICE_EDIT_ONLY", {}).get("status"),
        "COPY EDIT STRUCTURE": (result.get("revision_structure_check") or {}).get("COPY_EDIT_ONLY", {}).get("status"),
        "VISUAL REPLACE STRUCTURE": (result.get("revision_structure_check") or {}).get("VISUAL_REPLACE_ONLY", {}).get("status"),
        "FORMAT STRUCTURE": (result.get("format_structure_check") or {}).get("status"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "NEW APPROVED MASTER": "NO",
        "PROMOTED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "FINAL DECISION": result.get("final_decision"),
        "WORKFLOW": WORKFLOW_ID_64,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase6-4-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "ARCHITECTURE", "BEST SCENE", "FINAL DECISION", "GPT IMAGE CALLS")}, indent=2, default=str))


if __name__ == "__main__":
    main()
