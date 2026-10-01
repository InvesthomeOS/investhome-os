"""Phase 12.5-R1 live. Approve PRICE children. Lock PARTIAL_SUCCESS. Do not start 12.6."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import FAMILY_ID
from investhome_api.services.creative_director.phase12_5_r1_lock import (
    NEXT_PHASE,
    WORKFLOW_ID_12_5_R1,
    generate_phase12_5_r1_revision_lock,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-5-r1-revision-lock")


def _dump(name: str, payload: object) -> None:
    if name.endswith(".md"):
        (OUT / name).write_text(str(payload), encoding="utf-8")
        return
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def final_report_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Phase 12.5-R1 lock proof",
            "",
            f"PHASE: {report['PHASE']}",
            f"FINAL STATUS: {report['FINAL STATUS']}",
            f"HUMAN REVIEW: {report['HUMAN REVIEW']}",
            f"9:16 REVISION: {report['9:16 REVISION']}",
            f"1:1 REVISION: {report['1:1 REVISION']}",
            f"4:5: {report['4:5']}",
            f"16:9: {report['16:9']}",
            f"UNRELATED VISUAL DELTA: {report['UNRELATED VISUAL DELTA']}",
            f"ORIGINAL MASTERS MODIFIED: {report['ORIGINAL MASTERS MODIFIED']}",
            f"FAMILY-WIDE REVISION ENGINE: {report['FAMILY-WIDE REVISION ENGINE']}",
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
    result = generate_phase12_5_r1_revision_lock(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    _dump("01-result-model.json", result["result_model"])
    _dump("02-approved-children.json", result["approved_children"])
    _dump("03-format-results.json", result["members"])
    _dump("04-immutability-report.json", result["immutability"])
    report = {
        "PHASE": result["PHASE"],
        "FINAL STATUS": result["status"],
        "HUMAN REVIEW": result["HUMAN REVIEW"],
        "9:16 REVISION": result["9:16 REVISION"],
        "1:1 REVISION": result["1:1 REVISION"],
        "4:5": result["4:5"],
        "16:9": result["16:9"],
        "UNRELATED VISUAL DELTA": result["UNRELATED VISUAL DELTA"],
        "ORIGINAL MASTERS MODIFIED": result["ORIGINAL MASTERS MODIFIED"],
        "FAMILY-WIDE REVISION ENGINE": result["FAMILY-WIDE REVISION ENGINE"],
        "USER FACING": result["user_facing"],
        "NEXT": result["NEXT"],
        "PHASE_12_6_EXECUTED": result["PHASE_12_6_EXECUTED"],
        "FAMILY_ID": FAMILY_ID,
        "WORKFLOW": WORKFLOW_ID_12_5_R1,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("05-final-report.md", final_report_markdown(report))
    _dump("05-final-report.json", report)
    print(
        json.dumps(
            {
                "PHASE": report["PHASE"],
                "FINAL STATUS": report["FINAL STATUS"],
                "HUMAN REVIEW": report["HUMAN REVIEW"],
                "9:16": report["9:16 REVISION"],
                "1:1": report["1:1 REVISION"],
                "4:5": report["4:5"],
                "16:9": report["16:9"],
                "ENGINE": report["FAMILY-WIDE REVISION ENGINE"],
                "NEXT": NEXT_PHASE,
                "PHASE_12_6_EXECUTED": False,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
