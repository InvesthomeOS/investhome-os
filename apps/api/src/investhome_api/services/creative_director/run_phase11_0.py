"""Phase 11.0 live. Lock Creative Quality Engine foundation. No artwork."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.idea_first_pipeline import STEPS
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase11_0_foundation import (
    NEXT_PHASE,
    WORKFLOW_ID_11_0,
    generate_phase11_0_creative_quality_foundation,
)
from investhome_api.services.creative_director.stage3_canonical_pipeline import CANONICAL_PREMIUM_PATH, LEGACY_PREMIUM_PATHS
from investhome_api.services.creative_director.typography_quality_engine import HARD_REJECTS, RULES

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-0-creative-quality-engine")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _md(name: str, body: str) -> None:
    (OUT / name).write_text(body.strip() + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase11_0_creative_quality_foundation(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))

    audit = result.get("reference_library_audit") or {}
    lines = [
        "# 01 Reference library audit",
        "",
        f"Path: {audit.get('path')}",
        f"Live folder name: {audit.get('folder_name_live')}",
        f"Total visuals: {audit.get('total_visuals')}",
        f"Grade-A analyzed: {audit.get('grade_a_analyzed')}",
        "",
        "DESIGN_REFERENCES provide DESIGN DNA only.",
        "They are not project photography, architecture, logo, or facts.",
        "",
    ]
    for item in audit.get("inventory") or []:
        lines.append(f"- `{item['filename']}` — {item['status']} — {item['note']}")
    _md("01-reference-library-audit.md", "\n".join(lines))
    _dump("02-reference-design-dna.json", result.get("dna") or {})
    _dump("03-temple-photo-creative-profiles.json", result.get("photos") or {})
    _dump("04-creative-strategy-schema.json", result.get("strategy_schema") or {})

    pipe_lines = ["# 05 Idea-first pipeline", "", "Locked generation order:", ""]
    for i, step in enumerate(STEPS, 1):
        pipe_lines.append(f"{i}. {step.replace('_', ' ')}")
    pipe_lines.extend(
        [
            "",
            "Do not start with a template, text boxes, headline coordinates, or renderer primitives.",
            "Render is step 11. Human approval is step 13 and remains final.",
            "This pipeline is NOT executed in Phase 11.0.",
        ]
    )
    _md("05-idea-first-pipeline.md", "\n".join(pipe_lines))

    type_lines = ["# 06 Typography quality rules", "", "Hard rejects:"]
    for item in HARD_REJECTS:
        type_lines.append(f"- {item}")
    type_lines.append("")
    type_lines.append("Rules:")
    for key, text in RULES.items():
        type_lines.append(f"- **{key}**: {text}")
    _md("06-typography-quality-rules.md", "\n".join(type_lines))

    commercial = result.get("commercial") or {}
    comm_lines = [
        "# 07 Commercial art direction rules",
        "",
        commercial.get("principle") or "",
        "",
        "Hierarchy: " + " → ".join(commercial.get("hierarchy") or []),
        "",
        "Forbidden devices:",
    ]
    for item in commercial.get("forbidden_devices") or []:
        comm_lines.append(f"- {item}")
    _md("07-commercial-art-direction-rules.md", "\n".join(comm_lines))
    _dump("08-anti-template-rules.json", result.get("anti_template") or {})
    _dump("09-creative-critic-v2.json", result.get("critic") or {})

    audit_lines = [
        "# 10 Generation path audit",
        "",
        f"Active premium generation paths before: {result.get('active_premium_generation_paths_before')}",
        f"Canonical path: `{CANONICAL_PREMIUM_PATH}`",
        "",
        "Legacy premium paths (archived for new premium generation):",
        "",
    ]
    for item in LEGACY_PREMIUM_PATHS:
        audit_lines.append(f"- `{item['id']}` — {item['status']} — kept for: {item['kept_for']}")
    audit_lines.extend(
        [
            "",
            "AI Quick Creative remains a separate explicit product mode.",
            "Stage 2 natural-language revision remains locked and is not a generation path.",
        ]
    )
    _md("10-generation-path-audit.md", "\n".join(audit_lines))
    _md(
        "11-canonical-stage3-pipeline.md",
        "\n".join(
            [
                "# 11 Canonical Stage 3 pipeline",
                "",
                f"Canonical premium generation path: `{CANONICAL_PREMIUM_PATH}`",
                "",
                "There is one premium creative generation path.",
                "No silent fallback to template renderer, structured reconstruction,",
                "AI Quick Creative, GPT Image project-mode, or locked-master imitation",
                "for PREMIUM requests.",
                "",
                "Phase 11.0 registers the path. Phase 11.1 will prove it with a new creative.",
                "Executed: NO.",
            ]
        ),
    )
    _md(
        "12-stage3-readiness-report.md",
        "\n".join(
            [
                "# 12 Stage 3 readiness report",
                "",
                f"STATUS: {result.get('status')}",
                f"DESIGN REFERENCES ANALYZED: {result.get('design_references_analyzed')}",
                f"CANONICAL PATH: {result.get('canonical_premium_generation_path')}",
                "NEW CREATIVE GENERATED: NO",
                "STAGE 3 EXECUTED: NO",
                f"NEXT: {NEXT_PHASE}",
            ]
        ),
    )

    report = {
        "PHASE": "11.0 CREATIVE QUALITY ENGINE FOUNDATION",
        "STATUS": result.get("status"),
        "DESIGN REFERENCES ANALYZED": result.get("design_references_analyzed"),
        "DESIGN DNA V2": result.get("design_dna_v2"),
        "PROJECT PHOTO CREATIVE PROFILES": result.get("project_photo_creative_profiles"),
        "CREATIVE STRATEGY V1": result.get("creative_strategy_v1"),
        "IDEA-FIRST PIPELINE": result.get("idea_first_pipeline"),
        "NO-COPY GATE": result.get("no_copy_gate"),
        "TWO-SECOND GATE": result.get("two_second_gate"),
        "TYPOGRAPHIC QUALITY ENGINE": result.get("typographic_quality_engine"),
        "COMMERCIAL ART DIRECTION": result.get("commercial_art_direction"),
        "REFERENCE MATCHING": result.get("reference_matching"),
        "ANTI-TEMPLATE DETECTOR": result.get("anti_template_detector"),
        "CREATIVE CRITIC V2": result.get("creative_critic_v2"),
        "HUMAN PUBLISHABILITY GATE": result.get("human_publishability_gate"),
        "STAGE 2 REVISION COMPATIBILITY": result.get("stage_2_revision_compatibility"),
        "PROJECT REALITY POLICY": result.get("project_reality_policy"),
        "ACTIVE PREMIUM GENERATION PATHS BEFORE": result.get("active_premium_generation_paths_before"),
        "CANONICAL PREMIUM GENERATION PATH": result.get("canonical_premium_generation_path"),
        "LEGACY PREMIUM PATHS": result.get("legacy_premium_paths"),
        "NEW CREATIVE GENERATED": "NO",
        "MASTER 01": "UNCHANGED",
        "MASTER 02": "UNCHANGED",
        "MASTER 03": "UNCHANGED",
        "FORMAT WORK": "NOT EXECUTED",
        "PRODUCTION COVER": "UNCHANGED",
        "STAGE 1": "COMPLETE",
        "STAGE 2": "COMPLETE",
        "STAGE 3 FOUNDATION": result.get("stage_3_foundation"),
        "NEXT": NEXT_PHASE,
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_0,
        "IDENTITY": {"before": before, "after": after},
        "LIBRARY": result.get("library_state"),
    }
    _dump("phase11-0-report.json", report)
    print(json.dumps(
        {k: report[k] for k in ("PHASE", "STATUS", "DESIGN REFERENCES ANALYZED", "CANONICAL PREMIUM GENERATION PATH", "STAGE 3 FOUNDATION")},
        indent=2,
        default=str,
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
