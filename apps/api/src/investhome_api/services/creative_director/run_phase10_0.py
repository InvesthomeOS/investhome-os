"""Phase 10.0 live. PRICE_ONLY child of locked Master 03. Do not regenerate. Do not start formats."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase10_0_master import (
    WORKFLOW_ID_10,
    generate_phase10_0_natural_language_price_revision,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase10-0-natural-language-price-revision")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _write(name: str, image) -> None:
    (OUT / name).write_bytes(_png(image))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase10_0_natural_language_price_revision(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-locked-master-03.png": images.get("parent"),
        "02-natural-language-parse.png": images.get("parse"),
        "03-price-territory.png": images.get("territory"),
        "04-price-revision-child.png": images.get("child"),
        "05-parent-vs-child.png": images.get("pair"),
        "06-pixel-diff.png": images.get("diff"),
        "07-revision-validation.png": images.get("validation"),
        "08-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    _dump("natural-language-parse.json", result.get("parse") or {})
    _dump("revision-contract.json", result.get("contract") or {})
    _dump("pixel-diff.json", (result.get("compose") or {}).get("pixel_delta") or {})
    _dump("revision-validation.json", result.get("validation") or {})
    validation = result.get("validation") or {}
    report = {
        "PHASE": "10.0 NATURAL-LANGUAGE PRICE REVISION",
        "STATUS": result.get("status"),
        "USER COMMAND": result.get("user_command"),
        "PARENT MASTER": result.get("parent_master_name"),
        "PARENT MASTER ID": result.get("parent_master_id"),
        "PARENT ASSET ID": result.get("parent_asset_id"),
        "CHILD REVISION ID": result.get("child_revision_id"),
        "CHILD ASSET ID": result.get("child_asset_id"),
        "REVISION TYPE": result.get("revision_type"),
        "OLD PRICE": result.get("old_price"),
        "NEW PRICE": result.get("new_price"),
        "NATURAL LANGUAGE PARSE": validation.get("NATURAL_LANGUAGE_PARSE"),
        "PRICE TERRITORY ONLY": validation.get("PRICE_TERRITORY_ONLY"),
        "PIXEL DELTA OUTSIDE PRICE TERRITORY": validation.get("PIXEL_DELTA_OUTSIDE_PRICE_TERRITORY"),
        "ARCHITECTURE FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": validation.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "LOGO PRESERVED": validation.get("LOGO_PRESERVED"),
        "HEADLINE PRESERVED": validation.get("HEADLINE_PRESERVED"),
        "OFFER PRESERVED": validation.get("OFFER_PRESERVED"),
        "UNIT PRESERVED": validation.get("UNIT_PRESERVED"),
        "CTA PRESERVED": validation.get("CTA_PRESERVED"),
        "CLOSURE PRESERVED": validation.get("CLOSURE_PRESERVED"),
        "LOOKING CHAMBER PRESERVED": validation.get("LOOKING_CHAMBER_PRESERVED"),
        "GPT IMAGE CALLS": validation.get("GPT_IMAGE_CALLS"),
        "PARENT MASTER CHANGED": "NO",
        "CHILD APPROVAL STATUS": "DRAFT",
        "ROUTER ELIGIBLE": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_10,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase10-0-report.json", report)
    print(json.dumps(
        {
            k: report[k]
            for k in (
                "PHASE",
                "STATUS",
                "CHILD REVISION ID",
                "CHILD ASSET ID",
                "PIXEL DELTA OUTSIDE PRICE TERRITORY",
            )
        },
        indent=2,
        default=str,
    ))


if __name__ == "__main__":
    main()
