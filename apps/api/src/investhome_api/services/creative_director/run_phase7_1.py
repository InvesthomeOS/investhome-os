"""Phase 7.1 live. Candidate C project-reality lock. Do not promote."""

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
from investhome_api.services.creative_director.phase7_1_candidate_c_r1 import (
    WORKFLOW_ID_71,
    generate_phase7_1_candidate_c_r1,
)
from investhome_api.services.creative_director.phase7_1_reality_lock import PARENT_C_ASSET_ID

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase7-1-candidate-c-project-reality-lock")


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
    result = generate_phase7_1_candidate_c_r1(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "day007": "01-real-day007.png",
        "parent": "02-candidate-c-parent.png",
        "difference": "03-architecture-difference-map.png",
        "mask": "04-immutable-architecture-mask.png",
        "cr1": "05-candidate-c-r1.png",
        "c_vs_cr1": "06-c-vs-c-r1.png",
        "day007_vs_cr1": "07-day007-vs-c-r1.png",
        "provenance": "08-project-pixel-provenance.png",
        "architecture": "09-architecture-validation.png",
        "preservation": "10-creative-preservation.png",
        "critic": "11-final-visual-critic.png",
        "spec": "12-semantic-master-spec.png",
        "review": "13-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("project-reality-difference-map.json", result.get("difference_map") or {})
    _dump("immutable-project-architecture-mask.json", result.get("immutable_mask") or {})
    _dump("project-pixel-provenance.json", result.get("project_pixel_provenance") or {})
    _dump("architecture-validation.json", result.get("architecture_validation") or {})
    _dump("creative-preservation.json", result.get("creative_preservation") or {})
    _dump("final-visual-critic.json", result.get("final_visual_critic") or {})
    _dump("semantic-creative-spec.json", result.get("semantic_creative_spec") or {})
    _dump("revision-readiness.json", result.get("revision_readiness") or {})
    arch = result.get("architecture_validation") or {}
    preserve = result.get("creative_preservation") or {}
    critic = result.get("final_visual_critic") or {}
    report = {
        "PHASE": "7.1 CANDIDATE C PROJECT-REALITY LOCK",
        "STATUS": result.get("status"),
        "PRODUCTION DOCTRINE": PRODUCTION_DOCTRINE,
        "PARENT": "Candidate C",
        "PARENT ASSET ID": PARENT_C_ASSET_ID,
        "C-R1 ASSET ID": result.get("c_r1_asset_id"),
        "REAL PROJECT PHOTO": "Day_007",
        "REAL PROJECT PHOTO ASSET ID": result.get("day007_asset_id"),
        "REAL TEMPLE LOGO": result.get("logo_asset_id"),
        "PROJECT PIXEL PROVENANCE": (result.get("project_pixel_provenance") or {}).get("status"),
        "GENERATED PROJECT ARCHITECTURE PIXELS": result.get("generated_project_architecture_pixels"),
        "ARCHITECTURE VALIDATION": arch.get("scores"),
        "ARCHITECTURE FIDELITY": arch.get("architecture_fidelity"),
        "CREATIVE PRESERVATION": preserve.get("scores"),
        "FINAL VISUAL CRITIC": critic.get("scores"),
        "SEMANTIC SPEC": result.get("semantic_spec_status"),
        "PRICE REVISION": result.get("price_revision"),
        "COPY REVISION": result.get("copy_revision"),
        "VISUAL REPLACE": result.get("visual_replace"),
        "PROVIDER CALLS": result.get("image_model_calls"),
        "VISION CALLS": result.get("vision_calls"),
        "NEW APPROVED MASTER": "NO",
        "PROMOTED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_71,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase7-1-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "PHASE",
                    "STATUS",
                    "C-R1 ASSET ID",
                    "PROJECT PIXEL PROVENANCE",
                    "ARCHITECTURE FIDELITY",
                    "PROVIDER CALLS",
                    "NEW APPROVED MASTER",
                )
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
