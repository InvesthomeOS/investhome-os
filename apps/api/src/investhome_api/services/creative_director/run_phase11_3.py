"""Phase 11.3 live. Lock commercial creative system. No artwork. No Proof 03."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.campaign_reading_path_v1 import campaign_reading_path_schema
from investhome_api.services.creative_director.commercial_typography_system_v1 import commercial_typography_system_markdown
from investhome_api.services.creative_director.integrated_campaign_pipeline import integrated_pipeline_markdown
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.numeric_art_direction import numeric_art_direction_markdown
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase11_3_foundation import (
    NEXT_PHASE,
    WORKFLOW_ID_11_3,
    generate_phase11_3_commercial_creative_system,
)
from investhome_api.services.creative_director.stage3_failure_learning_v2 import stage3_failure_learning_v2

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-3-commercial-creative-system")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _md(name: str, body: str) -> None:
    (OUT / name).write_text(body.strip() + "\n", encoding="utf-8")


def _learning_markdown() -> str:
    learning = stage3_failure_learning_v2()
    p1 = learning["proof_01"]
    p2 = learning["proof_02"]
    return "\n".join(
        [
            "# 01 Proof 01 + Proof 02 systemic learning",
            "",
            "## Systemic conclusion",
            "",
            learning["systemic_conclusion"],
            "",
            f"**Root cause:** {learning['root_cause']}",
            "",
            "Do not broaden the diagnosis. Do not revise either proof.",
            "",
            "## Proof 01",
            "",
            f"- Status: `{p1['status']}` preserved",
            f"- Visual idea {p1['visual_idea']} / commercial hierarchy {p1['commercial_hierarchy']} / publishability {p1['publishability']}",
            f"- Fresh: idea YES, memorable YES, commercial designed NO, would publish NO",
            f"- Mode: {p1['failure_mode']}",
            "",
            "## Proof 02",
            "",
            f"- Status: `{p2['status']}` preserved",
            f"- Visual idea {p2['visual_idea']} / commercial hierarchy {p2['commercial_hierarchy']} / publishability {p2['publishability']}",
            f"- Fresh: idea YES, Temple-specific YES, memorable YES, commercial designed NO, would publish NO",
            f"- Mode: {p2['failure_mode']}",
            "",
            f"Repeated failure: **{learning['repeated_failure']}**",
            "",
            "Correction: integrated campaign concept pipeline. Not R1. Not Proof 03 in this phase.",
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
    result = generate_phase11_3_commercial_creative_system(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    subsystems = dict(result.get("subsystems") or {})

    _md("01-proof01-proof02-systemic-learning.md", _learning_markdown())
    _dump("02-commercial-design-dna.json", result.get("commercial_design_dna") or {})
    _dump("03-integrated-campaign-concept-schema.json", result.get("integrated_campaign_concept") or {})
    _dump("04-campaign-reading-path-schema.json", result.get("campaign_reading_path") or campaign_reading_path_schema())
    _md("05-commercial-typography-system.md", commercial_typography_system_markdown())
    _md("06-numeric-art-direction.md", numeric_art_direction_markdown())
    _dump("07-detached-commercial-lockup-detector.json", result.get("detached_lockup") or {})
    _dump("08-commercial-system-gate.json", result.get("commercial_system_gate") or {})
    _dump("09-creative-critic-v3.json", result.get("critic_v3") or {})
    _dump("10-fresh-critic-v3.json", result.get("fresh_critic_v3") or {})
    _md("11-stage3-integrated-pipeline.md", integrated_pipeline_markdown())
    _md(
        "12-phase11-3-readiness-report.md",
        "\n".join(
            [
                "# 12 Phase 11.3 readiness report",
                "",
                "PHASE: 11.3 COMMERCIAL CREATIVE SYSTEM CORRECTION",
                f"STATUS: {result.get('status')}",
                "PROOF 01 LEARNING: INTEGRATED",
                "PROOF 02 LEARNING: INTEGRATED",
                "SYSTEMIC FAILURE IDENTIFIED: YES",
                f"ROOT CAUSE: {(result.get('learning') or {}).get('root_cause')}",
                f"COMMERCIAL DESIGN DNA: {subsystems.get('COMMERCIAL_DESIGN_DNA')}",
                f"INTEGRATED CAMPAIGN CONCEPT: {subsystems.get('INTEGRATED_CAMPAIGN_CONCEPT')}",
                f"CAMPAIGN READING PATH: {subsystems.get('CAMPAIGN_READING_PATH')}",
                f"COMMERCIAL TYPOGRAPHY SYSTEM: {subsystems.get('COMMERCIAL_TYPOGRAPHY_SYSTEM')}",
                f"NUMERIC ART DIRECTION: {subsystems.get('NUMERIC_ART_DIRECTION')}",
                f"DETACHED COMMERCIAL LOCKUP DETECTOR: {subsystems.get('DETACHED_COMMERCIAL_LOCKUP_DETECTOR')}",
                f"COMMERCIAL SYSTEM GATE: {subsystems.get('COMMERCIAL_SYSTEM_GATE')}",
                f"THUMBNAIL TEST: {subsystems.get('THUMBNAIL_TEST')}",
                f"ADVERTISEMENT VS POSTER TEST: {subsystems.get('ADVERTISEMENT_VS_POSTER_TEST')}",
                f"CREATIVE CRITIC V3: {subsystems.get('CREATIVE_CRITIC_V3')}",
                f"FRESH CRITIC V3: {subsystems.get('FRESH_CRITIC_V3')}",
                "STAGE 2 COMPATIBILITY: PRESERVED",
                "OLD STAGE 3 PIPELINE: SUPERSEDED",
                f"CANONICAL PREMIUM PIPELINE: {result.get('canonical_premium_generation_path')}",
                "NEW CREATIVE GENERATED: NO",
                "PROOF 01: PRESERVED / REJECTED",
                "PROOF 02: PRESERVED / REJECTED",
                "MASTER 01: UNCHANGED",
                "MASTER 02: UNCHANGED",
                "MASTER 03: UNCHANGED",
                "FORMAT WORK: NOT EXECUTED",
                f"TEMPLE HIERARCHY SELECTED: {(result.get('temple_hierarchy_evaluation') or {}).get('selected')} (not rendered)",
                f"NEXT: {NEXT_PHASE}",
                "",
                "Do not execute Phase 11.4 in this phase.",
            ]
        ),
    )
    report = {
        "PHASE": "11.3 COMMERCIAL CREATIVE SYSTEM CORRECTION",
        "STATUS": result.get("status"),
        "PROOF 01 LEARNING": "INTEGRATED",
        "PROOF 02 LEARNING": "INTEGRATED",
        "SYSTEMIC FAILURE IDENTIFIED": "YES",
        "ROOT CAUSE": (result.get("learning") or {}).get("root_cause"),
        "COMMERCIAL DESIGN DNA": subsystems.get("COMMERCIAL_DESIGN_DNA"),
        "INTEGRATED CAMPAIGN CONCEPT": subsystems.get("INTEGRATED_CAMPAIGN_CONCEPT"),
        "CAMPAIGN READING PATH": subsystems.get("CAMPAIGN_READING_PATH"),
        "COMMERCIAL TYPOGRAPHY SYSTEM": subsystems.get("COMMERCIAL_TYPOGRAPHY_SYSTEM"),
        "NUMERIC ART DIRECTION": subsystems.get("NUMERIC_ART_DIRECTION"),
        "DETACHED COMMERCIAL LOCKUP DETECTOR": subsystems.get("DETACHED_COMMERCIAL_LOCKUP_DETECTOR"),
        "COMMERCIAL SYSTEM GATE": subsystems.get("COMMERCIAL_SYSTEM_GATE"),
        "THUMBNAIL TEST": subsystems.get("THUMBNAIL_TEST"),
        "ADVERTISEMENT VS POSTER TEST": subsystems.get("ADVERTISEMENT_VS_POSTER_TEST"),
        "CREATIVE CRITIC V3": subsystems.get("CREATIVE_CRITIC_V3"),
        "FRESH CRITIC V3": subsystems.get("FRESH_CRITIC_V3"),
        "STAGE 2 COMPATIBILITY": "PRESERVED",
        "OLD STAGE 3 PIPELINE": "SUPERSEDED",
        "CANONICAL PREMIUM PIPELINE": result.get("canonical_premium_generation_path"),
        "NEW CREATIVE GENERATED": "NO",
        "PROOF 01": "PRESERVED / REJECTED",
        "PROOF 02": "PRESERVED / REJECTED",
        "MASTER 01": "UNCHANGED",
        "MASTER 02": "UNCHANGED",
        "MASTER 03": "UNCHANGED",
        "FORMAT WORK": "NOT EXECUTED",
        "NEXT": NEXT_PHASE,
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_3,
        "IDENTITY": {"before": before, "after": after},
        "LIBRARY": result.get("library_state"),
        "TEMPLE_HIERARCHY": (result.get("temple_hierarchy_evaluation") or {}).get("selected"),
    }
    _dump("phase11-3-report.json", report)
    print(
        json.dumps(
            {
                "PHASE": report["PHASE"],
                "STATUS": report["STATUS"],
                "CANONICAL PREMIUM PIPELINE": report["CANONICAL PREMIUM PIPELINE"],
                "NEW CREATIVE GENERATED": report["NEW CREATIVE GENERATED"],
            },
            indent=2,
            default=str,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
