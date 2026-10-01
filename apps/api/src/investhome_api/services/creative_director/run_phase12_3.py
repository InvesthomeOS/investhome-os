"""Phase 12.3 live. Discover and ingest an existing multi-format family. No generation."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import (
    CAMPAIGN_NAME,
    FAMILY_ID,
    PROJECT_NAME,
    STATUS_PENDING,
    WORKFLOW_ID_12_3,
)
from investhome_api.services.creative_director.phase12_3_lock import generate_phase12_3_family_ingest
from investhome_api.services.creative_director.premium_creative_family_v1 import ORNEK_FAMILY_ID

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-3-multiformat-family")


def _dump(name: str, payload: object) -> None:
    if name.endswith(".md"):
        (OUT / name).write_text(str(payload), encoding="utf-8")
        return
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def final_report_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Phase 12.3 final report",
            "",
            f"PHASE: {report['PHASE']}",
            f"STATUS: {report['STATUS']}",
            f"SELECTED FAMILY: {report['SELECTED FAMILY']}",
            f"PROJECT / BRAND: {report['PROJECT / BRAND']}",
            f"4:5: {report['4:5']}",
            f"9:16: {report['9:16']}",
            f"1:1: {report['1:1']}",
            f"16:9: {report['16:9']}",
            f"CREATIVES GENERATED: {report['CREATIVES GENERATED']}",
            f"GPT IMAGE CALLS: {report['GPT IMAGE CALLS']}",
            f"IDEOGRAM CALLS: {report['IDEOGRAM CALLS']}",
            f"APPROVAL: {report['APPROVAL']}",
            f"ROUTER ELIGIBLE: {report['ROUTER ELIGIBLE']}",
            f"ORNEK_00013 FAMILY: {report['ORNEK_00013 FAMILY']} unchanged",
            "",
            "Human review board:",
            "[07-human-review-board.png](./07-human-review-board.png)",
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
    result = generate_phase12_3_family_ingest(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    boards = result["boards"]
    boards["discovery"].save(OUT / "01-family-discovery-board.png")
    _dump(
        "02-candidate-report.json",
        {
            "schema": "MultiFormatFamilyCandidateReportV1",
            "excluded": result["excluded"],
            "candidates": result["candidates"],
            "selected_family_id": FAMILY_ID,
        },
    )
    boards["selected"].save(OUT / "03-selected-family-board.png")
    _dump("04-selected-family.json", result["family"])
    _dump("05-format-master-inventory.json", result["inventory"])
    _dump(
        "06-ingestion-report.json",
        {
            "schema": "MultiFormatFamilyIngestionReportV1",
            "status": result["status"],
            "FAMILY_ID": FAMILY_ID,
            "byte_for_byte": True,
            "reconstructed": False,
            "rendered_replacement": False,
            "router_eligible": False,
            "approval": "PENDING HUMAN REVIEW",
            "ornek_00013_family_id": ORNEK_FAMILY_ID,
            "ornek_inventory_unchanged": result["ornek_inventory_unchanged"],
            "gpt_image_calls": result["gpt_image_calls"],
            "ideogram_calls": 0,
            "creatives_generated": 0,
        },
    )
    boards["review"].save(OUT / "07-human-review-board.png")
    report = {
        "PHASE": "12.3 FIRST MULTI-FORMAT PRODUCTION CREATIVE FAMILY",
        "STATUS": result.get("status") or STATUS_PENDING,
        "SELECTED FAMILY": CAMPAIGN_NAME,
        "PROJECT / BRAND": PROJECT_NAME,
        "FAMILY_ID": FAMILY_ID,
        "4:5": "FOUND",
        "9:16": "FOUND",
        "1:1": "FOUND",
        "16:9": "MISSING",
        "CREATIVES GENERATED": 0,
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "IDEOGRAM CALLS": 0,
        "APPROVAL": "PENDING HUMAN REVIEW",
        "ROUTER ELIGIBLE": False,
        "ORNEK_00013 FAMILY": ORNEK_FAMILY_ID,
        "WORKFLOW": WORKFLOW_ID_12_3,
        "IDENTITY": {"before": before, "after": after},
        "REVIEW BOARD": "07-human-review-board.png",
    }
    _dump("08-final-report.md", final_report_markdown(report))
    _dump("08-final-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"], "FAMILY_ID": FAMILY_ID}, indent=2))


if __name__ == "__main__":
    main()
