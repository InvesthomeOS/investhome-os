"""Phase 8.4 live. 1:1 format child. Canonical 4:5 unchanged."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase8_4_adapt import (
    WORKFLOW_ID_84,
    generate_phase8_4_format_adaptation_1x1,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase8-4-format-adaptation-1x1")


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
    result = generate_phase8_4_format_adaptation_1x1(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "canonical": "01-canonical-4x5.png",
        "square": "02-square-1x1.png",
        "pair": "03-side-by-side.png",
        "crop": "04-photo-crop-analysis.png",
        "recomposition": "05-semantic-recomposition.png",
        "identity": "06-identity-validation.png",
        "revision": "07-revision-readiness.png",
        "review": "08-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    identity = result.get("identity") or {}
    scores = identity.get("scores") or {}
    revision = result.get("revision_readiness") or {}
    _dump("format-adaptation-v1.json", result.get("format_adaptation") or {})
    _dump("identity-validation.json", identity)
    _dump("revision-readiness.json", revision)
    report = {
        "PHASE": "8.4 INTELLIGENT FORMAT ADAPTATION — 1:1",
        "STATUS": result.get("status"),
        "PARENT MASTER ID": result.get("parent_master_id"),
        "PARENT ASSET ID": result.get("parent_asset_id"),
        "1:1 CHILD ID": result.get("child_id"),
        "1:1 ASSET ID": result.get("child_asset_id"),
        "SOURCE PHOTO": result.get("source_photo"),
        "SOURCE PHOTO ASSET ID": result.get("source_photo_asset_id"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": result.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "ARCHITECTURE FIDELITY": result.get("ARCHITECTURE_FIDELITY"),
        "CAMPAIGN IDENTITY": scores.get("CAMPAIGN_IDENTITY"),
        "PHOTO IDENTITY": scores.get("PHOTO_IDENTITY"),
        "HEADLINE IDENTITY": scores.get("HEADLINE_IDENTITY"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "TYPOGRAPHIC CHARACTER": scores.get("TYPOGRAPHIC_CHARACTER"),
        "BRAND RELATIONSHIP": scores.get("BRAND_RELATIONSHIP"),
        "COLOR ATMOSPHERE": scores.get("COLOR_ATMOSPHERE"),
        "NEGATIVE SPACE LOGIC": scores.get("NEGATIVE_SPACE_LOGIC"),
        "WHOLE CANVAS FAMILY RESEMBLANCE": scores.get("WHOLE_CANVAS_FAMILY_RESEMBLANCE"),
        "SAME CAMPAIGN FAMILY": identity.get("SAME_CAMPAIGN_FAMILY"),
        "INDEPENDENTLY PUBLISHABLE 1:1": identity.get("INDEPENDENTLY_PUBLISHABLE_1X1"),
        "PRICE REVISION": revision.get("PRICE_EDIT_ONLY"),
        "COPY REVISION": revision.get("COPY_EDIT_ONLY"),
        "VISUAL REPLACE": revision.get("VISUAL_REPLACE_ONLY"),
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "CANONICAL MASTER CHANGED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "HUMAN APPROVAL": "PENDING",
        "NEXT AFTER HUMAN APPROVAL": result.get("next_phase"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_84,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase8-4-report.json", report)
    print(
        json.dumps(
            {k: report[k] for k in ("PHASE", "STATUS", "PARENT MASTER ID", "1:1 CHILD ID", "1:1 ASSET ID", "SAME CAMPAIGN FAMILY")},
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
