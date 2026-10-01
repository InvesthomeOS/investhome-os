"""Phase 12.5 live. Family-wide PRICE_ONLY children. Do not activate. Do not generate."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import FAMILY_ID
from investhome_api.services.creative_director.phase12_5_lock import (
    WORKFLOW_ID_12_5,
    generate_phase12_5_family_wide_revision,
)
from investhome_api.services.creative_director.phase12_5_price_revise import NEW_VALUE, OLD_VALUE

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-5-family-wide-revision")


def _dump(name: str, payload: object) -> None:
    if name.endswith(".md"):
        (OUT / name).write_text(str(payload), encoding="utf-8")
        return
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _write(name: str, image) -> None:
    (OUT / name).write_bytes(_png(image))


def final_report_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Phase 12.5 final report",
            "",
            f"PHASE: {report['PHASE']}",
            f"STATUS: {report['STATUS']}",
            f"COMMAND: {report['COMMAND']}",
            "PRICE_ONLY",
            f"4:5: {report['4:5']}",
            f"9:16: {report['9:16']}",
            f"1:1: {report['1:1']}",
            f"16:9: {report['16:9']}",
            f"ORIGINAL MASTERS MODIFIED: {report['ORIGINAL MASTERS MODIFIED']}",
            f"REVISION CHILDREN: {report['REVISION CHILDREN']}",
            f"UNRELATED VISUAL DELTA: {report['UNRELATED VISUAL DELTA']}",
            f"GPT IMAGE CALLS: {report['GPT IMAGE CALLS']}",
            f"IDEOGRAM CALLS: {report['IDEOGRAM CALLS']}",
            f"APPROVAL: {report['APPROVAL']}",
            "",
            "Human review board:",
            "[07-family-before-after-board.png](artifacts/phase12-5-family-wide-revision/07-family-before-after-board.png)",
            "",
        ]
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase12_5_family_wide_revision(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    _write("01-feed-4x5-price-375.png", images["feed_after"])
    _write("02-story-9x16-price-375.png", images["story_after"])
    _write("03-square-1x1-price-375.png", images["square_after"])
    _write("04-feed-before-after.png", images["feed_pair"])
    _write("05-story-before-after.png", images["story_pair"])
    _write("06-square-before-after.png", images["square_pair"])
    _write("07-family-before-after-board.png", images["family_board"])
    _write("08-mobile-preview.png", images["mobile"])
    _dump("09-revision-lineage.json", result["lineage"])
    _dump("10-delta-report.json", result["delta"])
    report = {
        "PHASE": result["PHASE"],
        "STATUS": result["status"],
        "COMMAND": f"{OLD_VALUE} USD → {NEW_VALUE} USD",
        "PRICE_ONLY": True,
        "4:5": result["4:5"],
        "9:16": result["9:16"],
        "1:1": result["1:1"],
        "16:9": result["16:9"],
        "ORIGINAL MASTERS MODIFIED": result["ORIGINAL MASTERS MODIFIED"],
        "REVISION CHILDREN": result["REVISION CHILDREN"],
        "UNRELATED VISUAL DELTA": result["UNRELATED VISUAL DELTA"],
        "GPT IMAGE CALLS": result["GPT IMAGE CALLS"],
        "IDEOGRAM CALLS": result["IDEOGRAM CALLS"],
        "APPROVAL": result["APPROVAL"],
        "FAMILY_ID": FAMILY_ID,
        "WORKFLOW": WORKFLOW_ID_12_5,
        "IDENTITY": {"before": before, "after": after},
        "child_9x16_asset": result.get("child_9x16_asset"),
        "child_1x1_asset": result.get("child_1x1_asset"),
    }
    _dump("11-final-report.md", final_report_markdown(report))
    _dump("11-final-report.json", report)
    print(
        json.dumps(
            {
                "PHASE": report["PHASE"],
                "STATUS": report["STATUS"],
                "4:5": report["4:5"],
                "9:16": report["9:16"],
                "1:1": report["1:1"],
                "16:9": report["16:9"],
                "REVISION CHILDREN": report["REVISION CHILDREN"],
                "GPT IMAGE CALLS": report["GPT IMAGE CALLS"],
                "FAMILY_ID": FAMILY_ID,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
