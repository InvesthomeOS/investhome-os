"""Phase 12.2 live. Lock Premium Creative Family. Close Stage 4.1. No artwork."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID, SELECTED_ASSET_ID, SELECTED_FILENAME
from investhome_api.services.creative_director.phase12_2_family_lock import (
    WORKFLOW_ID_12_2,
    generate_phase12_2_family_lock,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    AUTONOMOUS_PREMIUM_FORMAT_DESIGN,
    NEXT_PHASE,
    ORNEK_FAMILY_ID,
    PREMIUM_MODEL,
    STATUS_MODEL_READY,
    STATUS_STAGE41_FAIL,
    archived_format_research,
    family_schema,
    family_wide_revision_contract,
    format_master_schema,
    live_product_routing_matrix,
    ornek_00013_family,
    preserved_capabilities,
    project_reality_for_families,
    required_regression_tests,
)
from investhome_api.services.creative_director.premium_creative_product_model import ai_quick_creative_contract

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase12-2-premium-creative-family")


def _dump(name: str, payload: object) -> None:
    if name.endswith(".md"):
        (OUT / name).write_text(str(payload), encoding="utf-8")
        return
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def product_model_markdown() -> str:
    family = family_schema()
    return "\n".join(
        [
            "# Premium Creative Family — product model",
            "",
            "## Stage 4.1 close",
            "",
            "STAGE:",
            "4.1 ONE-SHOT 9:16 PREMIUM RECOMPOSITION",
            "",
            "STATUS:",
            STATUS_STAGE41_FAIL,
            "",
            "TECHNICAL INTEGRITY:",
            "PASS",
            "",
            "DESIGN QUALITY:",
            "FAIL",
            "",
            "HUMAN DECISION:",
            "REJECTED",
            "",
            "PremiumFormatRecomposerV1 must NOT be used for autonomous production Premium format creation.",
            "Preserve it only as archived research / reusable layout utilities.",
            "",
            "## Final Premium product model",
            "",
            "A Premium campaign is NOT one master plus automatically designed formats.",
            "A Premium campaign is a family of HUMAN_APPROVED finished creatives.",
            "",
            "```",
            "CAMPAIGN FAMILY",
            "├── 4:5 FEED MASTER",
            "├── 9:16 STORY MASTER",
            "├── 1:1 SQUARE MASTER",
            "└── 16:9 LANDSCAPE MASTER",
            "```",
            "",
            "Each format is independently art-directed and human approved.",
            "They share the same campaign identity but may have different composition.",
            "",
            f"PREMIUM MODEL: {PREMIUM_MODEL}",
            f"AUTONOMOUS PREMIUM FORMAT DESIGN: {AUTONOMOUS_PREMIUM_FORMAT_DESIGN}",
            "",
            "## Family-level locked properties",
            "",
            *[f"- {item}" for item in family["locked_properties"]],
            "",
            "These define SAME CAMPAIGN.",
            "",
            "## Missing format rule",
            "",
            "Do NOT derive missing Premium formats by autonomous design.",
            "If 4:5 is APPROVED and 9:16 is MISSING, “Bunu Story yap.” returns PREMIUM_FORMAT_MASTER_MISSING.",
            "AI Quick Creative remains available separately.",
            "",
        ]
    )


def routing_matrix_markdown() -> str:
    matrix = live_product_routing_matrix()
    return "\n".join(
        [
            "# Live Premium product routing",
            "",
            f"A) {matrix['A']['when']} → {matrix['A']['then']}",
            f"B) {matrix['B']['when']} → {matrix['B']['then']}",
            f"C) {matrix['C']['when']} → {matrix['C']['then']}",
            f"D) {matrix['D']['when']} → {matrix['D']['then']}",
            f"E) {matrix['E']['when']} → {matrix['E']['then']}",
            f"F) {matrix['F']['when']} → {matrix['F']['then']}",
            "",
            f"Autonomous Premium format design: {matrix['autonomous_premium_format_design']}",
            f"AI Quick Creative: {matrix['ai_quick_creative']}",
            f"Stage 2 revision: {matrix['stage_2_revision']}",
            "",
        ]
    )


def family_wide_markdown() -> str:
    contract = family_wide_revision_contract()
    return "\n".join(
        [
            "# Family-wide revision",
            "",
            f"STATUS: {contract['status']}",
            f"EXAMPLE: {contract['example']}",
            "",
            "System:",
            *[f"{index}. {step}" for index, step in enumerate(contract["steps"], start=1)],
            "",
            f"Uses: {contract['uses']}",
            "",
            "Preserve:",
            *[f"- {item}" for item in contract["preserve"]],
            "",
            "Do not rebuild formats from another format.",
            "",
        ]
    )


def archived_research_markdown() -> str:
    archive = archived_format_research()
    lines = [
        "# Archived Premium format research",
        "",
        "Do not use these as production Premium format creators.",
        "Do not treat rejected Stories as Creative Family members.",
        "Do not make them router eligible.",
        "",
        "## Models",
        "",
    ]
    for model in archive["models"]:
        lines.append(f"- {model['id']} — {model['role']} — {model['status']}")
    lines.extend(["", "## Rejected Story proofs", ""])
    for story in archive["stories"]:
        close = f" ({story['close_status']})" if story.get("close_status") else ""
        lines.append(f"- {story['revision']}: {story['status']}{close}")
    lines.extend(["", "## Reusable technical utilities", ""])
    for item in archive["preserve_utilities"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def preserved_capabilities_markdown() -> str:
    kept = preserved_capabilities()
    reality = project_reality_for_families()
    quick = ai_quick_creative_contract()
    return "\n".join(
        [
            "# Preserved capabilities",
            "",
            f"Stage 2 revision: {kept['stage_2_revision']}",
            f"AI Quick Creative: {kept['ai_quick_creative']} ({quick['status']})",
            f"Project reality: {kept['project_reality']}",
            f"Design Reference Library: {kept['design_reference_library']}",
            f"Production cover: {kept['production_cover']}",
            f"Approved master asset bytes: {kept['approved_master_asset_bytes']}",
            "",
            "## Stage 2 revision router",
            "",
            *[f"- {item}" for item in kept["revision_router"]],
            "",
            "## Reusable format utilities",
            "",
            *[f"- {item}" for item in kept["reusable_format_utilities"]],
            "",
            "## Not production paths",
            "",
            *[f"- {item}" for item in kept["not_production_paths"]],
            "",
            "## Project reality for families",
            "",
            f"PROJECT-scoped images: {reality['PROJECT_scoped']['images']}",
            f"PROJECT-scoped logo: {reality['PROJECT_scoped']['logo']}",
            f"Invented architecture: {reality['PROJECT_scoped']['invented_architecture']}",
            f"Cross-project substitution: {reality['PROJECT_scoped']['cross_project_substitution']}",
            f"BRAND-scoped assets: {reality['BRAND_scoped']['assets']}",
            f"BRAND-scoped cross-project reuse: {reality['BRAND_scoped']['cross_project_reuse']}",
            "",
        ]
    )


def final_report(*, result: dict, before: dict, after: dict, tests: dict) -> dict:
    family = ornek_00013_family()
    return {
        "PHASE": "12.2 PREMIUM CREATIVE FAMILY MODEL LOCK",
        "STATUS": STATUS_MODEL_READY,
        "PREMIUM MODEL": PREMIUM_MODEL,
        "AUTONOMOUS PREMIUM FORMAT DESIGN": AUTONOMOUS_PREMIUM_FORMAT_DESIGN,
        "STAGE 4.1": STATUS_STAGE41_FAIL,
        "TECHNICAL INTEGRITY": "PASS",
        "DESIGN QUALITY": "FAIL",
        "HUMAN DECISION": "REJECTED",
        "CURRENT FAMILY": "INVESTHOME BRAND / ORNEK_00013",
        "FAMILY_ID": ORNEK_FAMILY_ID,
        "MASTER ID": PRODUCTION_MASTER_ID,
        "ASSET": SELECTED_FILENAME,
        "ASSET ID": SELECTED_ASSET_ID,
        "4:5": family["inventory"]["4:5"],
        "9:16": family["inventory"]["9:16"],
        "1:1": family["inventory"]["1:1"],
        "16:9": family["inventory"]["16:9"],
        "FAMILY-WIDE REVISION": "READY",
        "STAGE 2 REVISION": "PRESERVED",
        "AI QUICK CREATIVE": "PRESERVED",
        "PROJECT REALITY": "LOCKED",
        "REJECTED STAGE 4 STORIES ARE FAMILY MEMBERS": "NO",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "IDEOGRAM CALLS": 0,
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_12_2,
        "STORY GENERATED": False,
        "IDENTITY": {"before": before, "after": after},
        "REGRESSION": tests,
        "NEXT": NEXT_PHASE,
    }


def final_report_markdown(report: dict) -> str:
    return "\n".join(
        [
            "# Phase 12.2 final report",
            "",
            f"PHASE: {report['PHASE']}",
            f"STATUS: {report['STATUS']}",
            f"PREMIUM MODEL: {report['PREMIUM MODEL']}",
            f"AUTONOMOUS PREMIUM FORMAT DESIGN: {report['AUTONOMOUS PREMIUM FORMAT DESIGN']}",
            f"CURRENT FAMILY: {report['CURRENT FAMILY']}",
            f"4:5: {report['4:5']}",
            f"9:16: {report['9:16']}",
            f"1:1: {report['1:1']}",
            f"16:9: {report['16:9']}",
            f"FAMILY-WIDE REVISION: {report['FAMILY-WIDE REVISION']}",
            f"STAGE 2 REVISION: {report['STAGE 2 REVISION']}",
            f"AI QUICK CREATIVE: {report['AI QUICK CREATIVE']}",
            f"PROJECT REALITY: {report['PROJECT REALITY']}",
            f"GPT IMAGE CALLS: {report['GPT IMAGE CALLS']}",
            f"IDEOGRAM CALLS: {report['IDEOGRAM CALLS']}",
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
    result = generate_phase12_2_family_lock(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    tests = required_regression_tests()
    report = final_report(result=result, before=before, after=after, tests=tests)
    _dump("01-product-model.md", product_model_markdown())
    _dump("02-family-schema.json", family_schema())
    _dump("03-format-master-schema.json", format_master_schema())
    _dump("04-routing-matrix.md", routing_matrix_markdown())
    _dump("05-family-wide-revision.md", family_wide_markdown())
    _dump("06-current-investhome-family.json", ornek_00013_family())
    _dump("07-archived-format-research.md", archived_research_markdown())
    _dump("08-preserved-capabilities.md", preserved_capabilities_markdown())
    _dump("09-regression-tests.json", tests)
    _dump("10-final-report.md", final_report_markdown(report))
    _dump("10-final-report.json", report)
    print(
        json.dumps(
            {
                "PHASE": report["PHASE"],
                "STATUS": report["STATUS"],
                "FAMILY_ID": report["FAMILY_ID"],
                "4:5": report["4:5"],
                "9:16": report["9:16"],
                "NEXT": report["NEXT"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
