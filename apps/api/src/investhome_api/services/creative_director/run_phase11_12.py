"""Phase 11.12 live. Product-model lock only. No artwork."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase11_12_lock import WORKFLOW_ID_11_12, generate_phase11_12_product_lock
from investhome_api.services.creative_director.premium_creative_product_model import (
    NEXT_STAGE,
    STATUS,
    ai_quick_creative_contract,
    next_stage_roadmap,
    premium_master_contract,
    premium_master_ingestion_v1,
    premium_revision_contract,
    premium_semantic_map_v1,
    project_reality_contract,
    research_archive_map,
    research_conclusion,
    reusable_capabilities,
    routing_model,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-12-premium-product-lock")


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
    result = generate_phase11_12_product_lock(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))

    conclusion = research_conclusion()
    _md(
        "01-research-conclusion.md",
        f"""# 01 Research conclusion

Autonomous premium creative generation cannot currently satisfy all three requirements simultaneously:

1. PUBLISHABILITY / AGENCY-LEVEL QUALITY
2. PROJECT REALITY / ARCHITECTURE FIDELITY
3. RELIABLE AUTOMATED PRODUCTION

Evidence:

- OLD PROGRAMMATIC COMPILER = {conclusion['evidence']['OLD_PROGRAMMATIC_COMPILER']}
- HYBRID V1 = {conclusion['evidence']['HYBRID_V1']}
- HYBRID V1 FINISH = {conclusion['evidence']['HYBRID_V1_FINISH']}
- HYBRID V2 = {conclusion['evidence']['HYBRID_V2']}
- AI-NATIVE = {conclusion['evidence']['AI_NATIVE']}
- REFERENCE-GUIDED = {conclusion['evidence']['REFERENCE_GUIDED']}

Decision: STOP autonomous premium creative quality experimentation.

Do not create Hybrid V3, another reference reconstruction, another AI-native experiment, another Temple creative proof, or another renderer architecture.

AI role shifts from AUTONOMOUS PREMIUM DESIGNER to PREMIUM CREATIVE OPERATOR.

Masters 01–03 remain research/system proofs. They are not the desired quality benchmark. Records and artifacts are preserved.
""",
    )
    _md(
        "02-final-creative-product-model.md",
        """# 02 Final creative product model

Creative Studio has two distinct modes.

## Mode A — AI Quick Creative

Fast, automatic, convenient, good-enough everyday creative.

The system may generate a creative automatically.

It is NOT represented as a Premium Master, an agency-level campaign, or a human-approved creative.

## Mode B — Premium Master

High-quality, brand-critical, campaign-critical, launch-quality creative.

A Premium Master begins from a HUMAN-APPROVED DESIGN.

The system does not invent the initial Premium Master.

AI intelligence is a Premium Creative Operator: understand the approved design, revise by natural language, preserve unrelated design, adapt formats later, keep project reality and brand consistency.

Doctrine: DESIGN FIRST. SEMANTICS SECOND. EDITABILITY THIRD.
""",
    )
    _dump("03-ai-quick-creative-contract.json", ai_quick_creative_contract())
    _dump("04-premium-master-contract.json", premium_master_contract())
    _dump("05-premium-master-ingestion-v1.json", premium_master_ingestion_v1())
    _dump("06-premium-semantic-map-v1.json", premium_semantic_map_v1())
    _dump("07-premium-revision-contract.json", premium_revision_contract())
    _dump("08-project-reality-contract.json", project_reality_contract())
    _dump("09-routing-model.json", routing_model())
    _dump("10-research-archive-map.json", research_archive_map())
    _dump("11-reusable-capabilities.json", reusable_capabilities())
    roadmap = next_stage_roadmap()
    then = "\n".join(f"- {item}" for item in roadmap["then"])
    _md(
        "12-next-stage-roadmap.md",
        f"""# 12 Next stage roadmap

Next: {roadmap['next']}

Then:

{then}

Not executed in this phase: formats, Story, Reel, video, live Creative Studio, publishing.

No new Temple creative was generated.
""",
    )
    report = {
        "PHASE": "11.12 PREMIUM CREATIVE PRODUCT MODEL LOCK",
        "STATUS": STATUS,
        "AI QUICK CREATIVE": "ACTIVE",
        "AUTONOMOUS PREMIUM GENERATION": "DISABLED",
        "PREMIUM MASTER SOURCE": "HUMAN-APPROVED DESIGN",
        "PREMIUM MASTER INGESTION": "READY",
        "PREMIUM SEMANTIC MAP": "READY",
        "NATURAL-LANGUAGE REVISION": "READY / PRESERVED",
        "PRICE REVISION": "READY / PRESERVED",
        "COPY REVISION": "READY / PRESERVED",
        "PROJECT PHOTO REPLACEMENT": "READY / PRESERVED",
        "PROJECT REALITY": "LOCKED",
        "PREMIUM MASTER LIBRARY": "READY / PRESERVED",
        "HUMAN APPROVAL REQUIRED": "YES",
        "RESEARCH PATHS": "ARCHIVED",
        "REUSABLE CAPABILITIES": "PRESERVED",
        "NEW CREATIVE GENERATED": "NO",
        "FORMAT WORK": "NOT EXECUTED",
        "STORY / REEL / VIDEO": "NOT EXECUTED",
        "LIVE CREATIVE STUDIO": "NOT EXECUTED",
        "NEXT": NEXT_STAGE,
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_12,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("13-phase11-12-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"]}, indent=2))


if __name__ == "__main__":
    main()
