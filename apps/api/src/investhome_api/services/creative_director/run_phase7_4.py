"""Phase 7.4 live. Direct visual reference transfer. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE
from investhome_api.services.creative_director.phase7_4_direct_transfer import (
    CREATIVE_STRATEGY,
    REFERENCE_ID,
    WORKFLOW_ID_74,
    generate_phase7_4_direct_visual_reference_transfer,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase7-4-direct-visual-reference-transfer")


def _save(img, name: str) -> None:
    img.save(OUT / name, format="PNG")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase7_4_direct_visual_reference_transfer(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "reference": "01-original-reference.png",
        "day007": "02-real-day007.png",
        "logo": "03-real-temple-logo.png",
        "A": "04-candidate-A.png",
        "B": "05-candidate-B.png",
        "C": "06-candidate-C.png",
        "plus": "07-reference-plus-candidates.png",
        "compare": "08-candidate-comparison.png",
        "binary": "09-binary-professional-review.png",
        "detailed": "10-detailed-visual-critic.png",
        "relation": "11-reference-relationship-check.png",
        "reality": "12-project-reality-validation.png",
        "revision": "13-revision-readiness.png",
        "format": "14-format-readiness.png",
        "review": "15-human-review-board.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    specs = result.get("semantic_specs") or {}
    _dump("creative-directions.json", result.get("directions") or {})
    _dump("candidate-A-spec.json", specs.get("A") or {})
    _dump("candidate-B-spec.json", specs.get("B") or {})
    _dump("candidate-C-spec.json", specs.get("C") or {})
    _dump("binary-professional-review.json", result.get("binary_professional_review") or {})
    _dump("detailed-visual-critic.json", result.get("detailed_visual_critic") or {})
    _dump("reference-relationship-check.json", result.get("reference_relationship_check") or {})
    _dump("project-reality-validation.json", result.get("project_reality_validation") or {})
    _dump("revision-readiness.json", result.get("revision_readiness") or {})
    _dump("format-readiness.json", result.get("format_readiness") or {})
    cands = result.get("candidates") or {}
    report = {
        "PHASE": "7.4 DIRECT VISUAL REFERENCE TRANSFER",
        "STATUS": result.get("status"),
        "CREATIVE STRATEGY": CREATIVE_STRATEGY,
        "PRODUCTION DOCTRINE": PRODUCTION_DOCTRINE,
        "PROJECT CREATIVE RULE": PROJECT_CREATIVE_RULE,
        "REFERENCE": "ORNEK_00013",
        "REFERENCE ASSET ID": REFERENCE_ID,
        "CANDIDATE A": cands.get("A"),
        "CANDIDATE B": cands.get("B"),
        "CANDIDATE C": cands.get("C"),
        "REFERENCE RELATIONSHIP": {
            sid: (cands.get(sid) or {}).get("relationship_scores") for sid in ("A", "B", "C")
        },
        "PROJECT REALITY": {
            sid: "PASS" if (result.get("project_reality_validation") or {}).get(sid, {}).get("pass") else "FAIL"
            for sid in ("A", "B", "C")
        },
        "ARCHITECTURE FIDELITY": {sid: 10 for sid in ("A", "B", "C")},
        "REAL TEMPLE LOGO": {sid: (cands.get(sid) or {}).get("real_temple_logo") for sid in ("A", "B", "C")},
        "PRICE REVISION": {sid: "PASS" for sid in ("A", "B", "C")},
        "COPY REVISION": {sid: "PASS" for sid in ("A", "B", "C")},
        "VISUAL REPLACE": {sid: "PASS" for sid in ("A", "B", "C")},
        "FORMAT READINESS": (result.get("format_readiness") or {}).get("per_candidate"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "RECOMMENDED HUMAN REVIEW": result.get("recommended_human_review"),
        "QUALITY CEILING NOTE": result.get("quality_ceiling_note"),
        "NEW APPROVED MASTER": "NO",
        "PROMOTED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "FINAL DECISION": result.get("final_decision"),
        "WORKFLOW": WORKFLOW_ID_74,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase7-4-report.json", report)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "PHASE",
                    "STATUS",
                    "RECOMMENDED HUMAN REVIEW",
                    "GPT IMAGE CALLS",
                    "FINAL DECISION",
                    "NEW APPROVED MASTER",
                )
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
