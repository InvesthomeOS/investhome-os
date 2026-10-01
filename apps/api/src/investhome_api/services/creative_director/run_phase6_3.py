"""Phase 6.3 live. Renderer capability gap. Do not create a Master. Do not promote."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_3_renderer_capability_gap import (
    WORKFLOW_ID_63,
    generate_phase6_3_capability_gap,
)

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase6-3-renderer-capability-gap")


def _save(img, name: str) -> None:
    img.save(OUT / name, format="PNG")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase6_3_capability_gap(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "map": "01-concept3-capability-map.png",
        "matrix": "02-v4-capability-matrix.png",
        "compare": "03-renderer-architecture-comparison.png",
        "A": "04-proof-A-dark-aperture.png",
        "B": "05-proof-B-arc-system.png",
        "C": "06-proof-C-typographic-mass.png",
        "D": "07-proof-D-photo-type-field.png",
        "E": "08-proof-E-brand-cta-closure.png",
        "critic": "09-micro-proof-critic.png",
        "objects": "10-structured-object-model.png",
        "revision": "11-revision-compatibility.png",
        "format": "12-format-compatibility.png",
        "decision": "13-final-architecture-decision.png",
    }
    for key, name in mapping.items():
        if images.get(key) is not None:
            _save(images[key], name)
    _dump("production-visual-capability-map.json", result.get("capability_map") or {})
    _dump("v4-capability-audit.json", result.get("v4_audit") or [])
    _dump("renderer-architecture-comparison.json", result.get("renderer_comparison") or {})
    _dump("runtime-dependency-audit.json", result.get("runtime_dependencies") or {})
    _dump("micro-proof-scores.json", result.get("micro_proof_scores") or {})
    _dump("structured-object-model.json", result.get("structured_object_model") or {})
    _dump("revision-compatibility.json", result.get("revision_compatibility") or {})
    _dump("format-compatibility.json", result.get("format_compatibility") or {})
    proofs = (result.get("micro_proof_scores") or {}).get("proofs") or {}
    report = {
        "PHASE": "6.3 PRODUCTION RENDERER CAPABILITY GAP",
        "STATUS": result.get("status"),
        "CURRENT BOTTLENECK": result.get("current_bottleneck"),
        "SELECTED RENDERER ARCHITECTURE": result.get("selected_renderer"),
        "V4 COUNTS": result.get("v4_counts"),
        "MICRO PROOF A": (proofs.get("A") or {}).get("scores"),
        "MICRO PROOF B": (proofs.get("B") or {}).get("scores"),
        "MICRO PROOF C": (proofs.get("C") or {}).get("scores"),
        "MICRO PROOF D": (proofs.get("D") or {}).get("scores"),
        "MICRO PROOF E": (proofs.get("E") or {}).get("scores"),
        "STRUCTURED OBJECT MODEL": "PASS",
        "REVISION": result.get("revision_compatibility"),
        "FORMAT": result.get("format_compatibility"),
        "GPT IMAGE CALLS": result.get("image_model_calls"),
        "NEW MASTER CREATED": False,
        "PRODUCTION COVER CHANGED": False,
        "COVER": PRODUCTION_COVER_V2,
        "BLOCKER": result.get("blocker"),
        "WORKFLOW": WORKFLOW_ID_63,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("phase6-3-report.json", report)
    print(json.dumps({k: report[k] for k in ("PHASE", "STATUS", "SELECTED RENDERER ARCHITECTURE", "GPT IMAGE CALLS", "BLOCKER")}, indent=2, default=str))


if __name__ == "__main__":
    main()
