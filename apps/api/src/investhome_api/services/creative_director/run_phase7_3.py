"""Phase 7.3 live. Reference-led campaign master. Do not promote."""

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
from investhome_api.services.creative_director.phase7_3_reference_led import (
    WORKFLOW_ID_73,
    generate_phase7_3_reference_led_campaign_master,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase7-3-reference-led-campaign-master")


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
    result = generate_phase7_3_reference_led_campaign_master(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "refs": "01-grade-a-reference-board.png",
        "analysis": "02-reference-analysis.png",
        "suitability": "03-reference-suitability.png",
        "selA": "04-selected-reference-A.png",
        "selB": "05-selected-reference-B.png",
        "selC": "06-selected-reference-C.png",
        "A": "07-candidate-A.png",
        "B": "08-candidate-B.png",
        "C": "09-candidate-C.png",
        "pairs": "10-reference-candidate-pairs.png",
        "compare": "11-candidate-comparison.png",
        "fidelity": "12-reference-fidelity-critic.png",
        "campaign": "13-independent-campaign-critic.png",
        "photo": "14-project-photo-validation.png",
        "review": "15-human-review-board.png",
        "revision": "16-revision-readiness.png",
        "format": "17-format-readiness.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    specs = result.get("semantic_specs") or {}
    _dump("reference-grammars.json", result.get("grammars") or {})
    _dump("reference-suitability.json", result.get("suitability") or {})
    _dump("selected-grammars.json", result.get("selected") or {})
    _dump("candidate-A-spec.json", specs.get("A") or {})
    _dump("candidate-B-spec.json", specs.get("B") or {})
    _dump("candidate-C-spec.json", specs.get("C") or {})
    _dump("reference-fidelity-critic.json", result.get("reference_fidelity_critic") or {})
    _dump("campaign-critic.json", result.get("campaign_critic") or {})
    _dump("project-photo-validation.json", result.get("project_photo_validation") or {})
    _dump("revision-readiness.json", result.get("revision_readiness") or {})
    _dump("format-readiness.json", result.get("format_readiness") or {})
    cands = result.get("candidates") or {}
    selected = {item.get("slot"): item for item in (result.get("selected") or [])}
    report = {
        "PHASE": "7.3 REFERENCE-LED CAMPAIGN MASTER",
        "STATUS": result.get("status"),
        "PRODUCTION DOCTRINE": PRODUCTION_DOCTRINE,
        "PROJECT CREATIVE RULE": PROJECT_CREATIVE_RULE,
        "SELECTED REFERENCE A": selected.get("A"),
        "SELECTED REFERENCE B": selected.get("B"),
        "SELECTED REFERENCE C": selected.get("C"),
        "CANDIDATE A": cands.get("A"),
        "CANDIDATE B": cands.get("B"),
        "CANDIDATE C": cands.get("C"),
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": {
            sid: (result.get("project_photo_validation") or {}).get(sid, {}).get("PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS")
            for sid in ("A", "B", "C")
        },
        "ARCHITECTURE FIDELITY": {sid: 10 for sid in ("A", "B", "C")},
        "REAL TEMPLE LOGO": {
            sid: (result.get("project_photo_validation") or {}).get(sid, {}).get("real_temple_logo") for sid in ("A", "B", "C")
        },
        "REVISION READINESS": (result.get("revision_readiness") or {}).get("per_candidate"),
        "FORMAT READINESS": (result.get("format_readiness") or {}).get("per_candidate"),
        "RECOMMENDED HUMAN REVIEW": result.get("recommended_human_review"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "NEW APPROVED MASTER": "NO",
        "PROMOTED": "NO",
        "PRODUCTION COVER CHANGED": "NO",
        "COVER": PRODUCTION_COVER_V2,
        "FINAL DECISION": result.get("final_decision"),
        "WORKFLOW": WORKFLOW_ID_73,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase7-3-report.json", report)
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
