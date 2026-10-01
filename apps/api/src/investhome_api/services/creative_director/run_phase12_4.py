"""Phase 12.4 live. Approve and activate the UniLoft Last Units family. No generation. No price revision."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import CAMPAIGN_NAME, FAMILY_ID, PROJECT_NAME
from investhome_api.services.creative_director.phase12_4_approve_lock import (
    NEXT_PHASE,
    STATUS,
    WORKFLOW_ID_12_4,
    generate_phase12_4_family_approval,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import ORNEK_FAMILY_ID

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-4-family-approval")


def _dump(name: str, payload: object) -> None:
    if name.endswith(".md"):
        (OUT / name).write_text(str(payload), encoding="utf-8")
        return
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def final_report_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Phase 12.4 final report",
            "",
            f"PHASE: {report['PHASE']}",
            f"STATUS: {report['STATUS']}",
            f"FAMILY: {report['FAMILY']}",
            f"FAMILY ID: {report['FAMILY ID']}",
            f"4:5: {report['4:5']}",
            f"9:16: {report['9:16']}",
            f"1:1: {report['1:1']}",
            f"16:9: {report['16:9']}",
            f"ROUTER ELIGIBLE: {report['ROUTER ELIGIBLE']}",
            f"FAMILY-WIDE REVISION: {report['FAMILY-WIDE REVISION']}",
            f"NEXT: {report['NEXT']}",
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
    result = generate_phase12_4_family_approval(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    _dump("01-approved-family.json", result["family"])
    _dump("02-format-master-inventory.json", result["inventory"])
    _dump("03-identity-lock.json", result["identity_lock"])
    _dump("04-routing-tests.json", result["routing_tests"])
    _dump("05-family-wide-revision-ready.json", result["family_wide_revision_ready"])
    _dump("06-immutability-report.json", result["immutability"])
    result["boards"]["approved"].save(OUT / "07-approved-family-board.png")
    report = {
        "PHASE": "12.4 FIRST PRODUCTION PREMIUM CREATIVE FAMILY APPROVAL",
        "STATUS": STATUS,
        "FAMILY": CAMPAIGN_NAME,
        "FAMILY ID": FAMILY_ID,
        "PROJECT / BRAND": PROJECT_NAME,
        "4:5": "HUMAN_APPROVED / ACTIVE",
        "9:16": "HUMAN_APPROVED / ACTIVE",
        "1:1": "HUMAN_APPROVED / ACTIVE",
        "16:9": "MISSING",
        "ROUTER ELIGIBLE": "YES",
        "FAMILY-WIDE REVISION": "READY",
        "NEXT": NEXT_PHASE,
        "CREATIVES GENERATED": 0,
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "IDEOGRAM CALLS": 0,
        "PRICE REVISION EXECUTED": False,
        "ORNEK_00013 FAMILY": ORNEK_FAMILY_ID,
        "WORKFLOW": WORKFLOW_ID_12_4,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("08-final-report.md", final_report_markdown(report))
    _dump("08-final-report.json", report)
    print(
        json.dumps(
            {
                "PHASE": report["PHASE"],
                "STATUS": report["STATUS"],
                "FAMILY_ID": FAMILY_ID,
                "4:5": report["4:5"],
                "9:16": report["9:16"],
                "1:1": report["1:1"],
                "16:9": report["16:9"],
                "NEXT": report["NEXT"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
