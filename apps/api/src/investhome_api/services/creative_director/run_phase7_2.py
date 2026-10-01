"""Phase 7.2 live. Immutable project photo object. Do not promote."""

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
from investhome_api.services.creative_director.phase7_2_immutable_photo import (
    WORKFLOW_ID_72,
    generate_phase7_2_immutable_photo_object,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase7-2-immutable-project-photo-object")


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
    result = generate_phase7_2_immutable_photo_object(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "concept3": "01-concept3-reference.png",
        "day007": "02-real-day007.png",
        "logo": "03-real-temple-logo.png",
        "A": "04-candidate-A.png",
        "B": "05-candidate-B.png",
        "C": "06-candidate-C.png",
        "compare": "07-candidate-comparison.png",
        "photo_validation": "08-project-photo-object-validation.png",
        "critic": "09-visual-critic.png",
        "review": "10-human-review-board.png",
        "specA": "11-semantic-spec-A.png",
        "specB": "12-semantic-spec-B.png",
        "specC": "13-semantic-spec-C.png",
        "revision": "14-revision-readiness.png",
        "format": "15-format-readiness.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    specs = result.get("semantic_specs") or {}
    _dump("candidate-A-spec.json", specs.get("A") or {})
    _dump("candidate-B-spec.json", specs.get("B") or {})
    _dump("candidate-C-spec.json", specs.get("C") or {})
    _dump("project-photo-object-validation.json", result.get("project_photo_object_validation") or {})
    _dump("visual-critic.json", result.get("visual_critic") or {})
    _dump("revision-readiness.json", result.get("revision_readiness") or {})
    _dump("format-readiness.json", result.get("format_readiness") or {})
    cands = result.get("candidates") or {}
    report = {
        "PHASE": "7.2 PROJECT IMAGE AS IMMUTABLE CREATIVE OBJECT",
        "STATUS": result.get("status"),
        "PRODUCTION DOCTRINE": PRODUCTION_DOCTRINE,
        "NEW PROJECT CREATIVE RULE": PROJECT_CREATIVE_RULE,
        "REAL PROJECT PHOTO": "Day_007",
        "REAL PROJECT PHOTO ASSET ID": result.get("day007_asset_id"),
        "REAL TEMPLE LOGO": result.get("logo_asset_id"),
        "CANDIDATE A": cands.get("A"),
        "CANDIDATE B": cands.get("B"),
        "CANDIDATE C": cands.get("C"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": {
            sid: (result.get("project_photo_object_validation") or {}).get(sid, {}).get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS")
            for sid in ("A", "B", "C")
        },
        "DUPLICATE / GENERATED TEMPLE LOGO": {sid: (cands.get(sid) or {}).get("generated_or_duplicate_logo") for sid in ("A", "B", "C")},
        "REVISION READINESS": (result.get("revision_readiness") or {}).get("per_candidate"),
        "FORMAT READINESS": (result.get("format_readiness") or {}).get("per_candidate"),
        "RECOMMENDED HUMAN REVIEW CANDIDATE": result.get("recommended_human_review_candidate"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "NEW APPROVED MASTER": "NO",
        "PROMOTED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_72,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase7-2-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "PHASE",
                    "STATUS",
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
