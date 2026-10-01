"""Phase 10.1 live. HEADLINE_ONLY child. Do not overwrite parent or price children."""

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
from investhome_api.services.creative_director.phase10_1_master import WORKFLOW_ID_10_1, generate_phase10_1_copy_revision

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase10-1-natural-language-copy-revision")


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
    critic_path = Path("/tmp/phase10-1-critic.json")
    critic = json.loads(critic_path.read_text(encoding="utf-8-sig")) if critic_path.is_file() else None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase10_1_copy_revision(db, user, row, language="tr", critic=critic)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "01-locked-master-03.png": images.get("parent"),
        "02-original-headline-territory.png": images.get("original_territory"),
        "03-clean-headline-background.png": images.get("clean_bg"),
        "04-new-headline-render.png": images.get("new_headline"),
        "05-copy-revision-child.png": images.get("child"),
        "06-parent-vs-child.png": images.get("pair"),
        "07-pixel-diff.png": images.get("diff"),
        "08-25-percent-legibility.png": images.get("preview25"),
        "09-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    validation = result.get("validation") or {}
    compose = result.get("compose") or {}
    _dump("natural-language-parse.json", result.get("parse"))
    _dump("copy-revision-contract.json", result.get("contract"))
    _dump("headline-layout.json", compose.get("layout"))
    _dump("pixel-diff.json", compose.get("pixel_delta"))
    _dump("revision-validation.json", validation)
    report = {
        "PHASE": "10.1 NATURAL-LANGUAGE COPY REVISION",
        "STATUS": result.get("status"),
        "USER COMMAND": result.get("user_command"),
        "PARENT MASTER": result.get("parent_master_name"),
        "PARENT MASTER ID": result.get("parent_master_id"),
        "PARENT ASSET ID": result.get("parent_asset_id"),
        "CHILD REVISION ID": result.get("child_revision_id"),
        "CHILD ASSET ID": result.get("child_asset_id"),
        "REVISION TYPE": result.get("revision_type"),
        "OLD COPY": result.get("old_copy"),
        "NEW COPY": result.get("new_copy"),
        "NATURAL LANGUAGE PARSE": validation.get("NATURAL_LANGUAGE_PARSE"),
        "OLD HEADLINE COMPLETELY REMOVED": validation.get("OLD_HEADLINE_COMPLETELY_REMOVED"),
        "CLEAN BACKGROUND": validation.get("CLEAN_BACKGROUND"),
        "NEW HEADLINE FULLY LEGIBLE": validation.get("NEW_HEADLINE_FULLY_LEGIBLE"),
        "TURKISH GLYPHS": validation.get("TURKISH_GLYPHS"),
        "TYPOGRAPHY NATIVE TO MASTER": validation.get("TYPOGRAPHY_NATIVE_TO_MASTER"),
        "HEADLINE HIERARCHY": validation.get("HEADLINE_HIERARCHY"),
        "VISIBLE PATCH": validation.get("VISIBLE_PATCH"),
        "TEXT COLLISIONS": validation.get("TEXT_COLLISIONS"),
        "PIXEL DELTA OUTSIDE HEADLINE TERRITORY": validation.get("PIXEL_DELTA_OUTSIDE_HEADLINE_TERRITORY"),
        "LOOKING CHAMBER PRESERVED": validation.get("LOOKING_CHAMBER_PRESERVED"),
        "ARCHITECTURE FIDELITY": validation.get("ARCHITECTURE_FIDELITY"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": validation.get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS"),
        "LOGO PRESERVED": validation.get("LOGO_PRESERVED"),
        "OFFER PRESERVED": validation.get("OFFER_PRESERVED"),
        "PRICE PRESERVED": validation.get("PRICE_PRESERVED"),
        "CTA PRESERVED": validation.get("CTA_PRESERVED"),
        "GPT IMAGE CALLS": validation.get("GPT_IMAGE_CALLS"),
        "PARENT MASTER CHANGED": "NO",
        "CHILD APPROVAL": "DRAFT",
        "ROUTER ELIGIBLE": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER CHANGED": "NO",
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_10_1,
        "CRITIC": result.get("critic"),
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase10-1-report.json", report)
    print(json.dumps(
        {k: report[k] for k in ("PHASE", "STATUS", "CHILD REVISION ID", "CHILD ASSET ID", "PIXEL DELTA OUTSIDE HEADLINE TERRITORY")},
        indent=2,
        default=str,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
