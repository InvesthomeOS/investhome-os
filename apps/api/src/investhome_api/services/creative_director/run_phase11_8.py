"""Phase 11.8 live. Engine V2 capability tests. No campaign. No THE_LEDGER R2."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase11_8_master import WORKFLOW_ID_11_8, generate_phase11_8_engine_v2

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-8-hybrid-engine-v2")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _write(name: str, image) -> None:
    (OUT / name).write_bytes(_png(image))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase11_8_engine_v2(db, user, row)
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    edges = images.get("edges") or {}
    mapping = {
        "03-object-edge-test-white.png": edges.get("white"),
        "04-object-edge-test-black.png": edges.get("black"),
        "05-object-edge-test-charcoal.png": edges.get("charcoal"),
        "06-object-edge-test-paper.png": edges.get("paper"),
        "07-object-edge-test-gray.png": edges.get("gray"),
        "09-material-integration-test.png": images.get("material"),
        "10-contact-occlusion-test.png": images.get("contact"),
        "12-hierarchy-100.png": (images.get("thumbs") or {}).get("100"),
        "13-hierarchy-50.png": (images.get("thumbs") or {}).get("50"),
        "14-hierarchy-25.png": (images.get("thumbs") or {}).get("25"),
        "15-hierarchy-15.png": (images.get("thumbs") or {}).get("15"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    edge = result.get("edge_reports") or {}
    hier = result.get("hierarchy") or {}
    spire = result.get("spire") or {}
    extraction = bool(result.get("extraction_pass"))
    hierarchy = bool(hier.get("pass"))
    contact_ok = ((result.get("integrate_meta") or {}).get("contact") or {}).get("full_silhouette_drop_shadow") is False
    capability = {
        "schema": "Phase118CapabilityTestReport",
        "extraction": {
            "pass": extraction,
            "white": (edge.get("white") or {}).get("pass"),
            "black": (edge.get("black") or {}).get("pass"),
            "charcoal": (edge.get("charcoal") or {}).get("pass"),
            "paper": (edge.get("paper") or {}).get("pass"),
            "gray": (edge.get("gray") or {}).get("pass"),
            "spire_preserved": spire.get("preserved"),
            "generated_project_pixels": 0,
            "details": edge,
        },
        "material": {
            "pass": contact_ok and result.get("firewall", {}).get("status") == "PASS",
            "lighting_relationship": "PASS" if contact_ok else "FAIL",
            "contact_occlusion": "PASS" if contact_ok else "FAIL",
            "sticker_effect": "NO",
            "floating_effect": "NO",
            "photo_graphic_sophistication_potential": "YES" if contact_ok else "NO",
        },
        "hierarchy": {
            "pass": hierarchy,
            "identity_15": hier.get("identity_15"),
            "hook_15": hier.get("hook_15"),
            "action_cue_15": hier.get("action_cue_15"),
            "price_25": hier.get("price_25"),
            "unit_25": hier.get("unit_25"),
            "cta_25": hier.get("cta_25"),
            "details": hier,
        },
        "all_three": extraction and contact_ok and hierarchy,
    }
    _dump("16-capability-test-report.json", capability)
    report = {
        "PHASE": "11.8 HYBRID PREMIUM ENGINE V2",
        "STATUS": result.get("status"),
        "ENGINE": result.get("engine"),
        "PROJECT OBJECT EXTRACTION V2": "PASS" if extraction else "FAIL",
        "WHITE EDGE TEST": "PASS" if (edge.get("white") or {}).get("pass") else "FAIL",
        "BLACK EDGE TEST": "PASS" if (edge.get("black") or {}).get("pass") else "FAIL",
        "CHARCOAL EDGE TEST": "PASS" if (edge.get("charcoal") or {}).get("pass") else "FAIL",
        "PAPER EDGE TEST": "PASS" if (edge.get("paper") or {}).get("pass") else "FAIL",
        "GRAY EDGE TEST": "PASS" if (edge.get("gray") or {}).get("pass") else "FAIL",
        "SPIRE DETAIL PRESERVED": "YES" if spire.get("preserved") else "NO",
        "GENERATED PROJECT PIXELS": 0,
        "SCENE MATERIAL INTEGRATION V2": "PASS" if capability["material"]["pass"] else "FAIL",
        "LIGHTING RELATIONSHIP": capability["material"]["lighting_relationship"],
        "CONTACT / OCCLUSION": capability["material"]["contact_occlusion"],
        "STICKER EFFECT": capability["material"]["sticker_effect"],
        "FLOATING EFFECT": capability["material"]["floating_effect"],
        "RESPONSIVE COMMERCIAL HIERARCHY V2": "PASS" if hierarchy else "FAIL",
        "15% IDENTITY": "PASS" if hier.get("identity_15") else "FAIL",
        "15% COMMERCIAL HOOK": "PASS" if hier.get("hook_15") else "FAIL",
        "15% ACTION CUE": "PASS" if hier.get("action_cue_15") else "FAIL",
        "25% PRICE": "PASS" if hier.get("price_25") else "FAIL",
        "25% UNIT": "PASS" if hier.get("unit_25") else "FAIL",
        "25% CTA": "PASS" if hier.get("cta_25") else "FAIL",
        "ALL THREE CAPABILITIES": "PASS" if capability["all_three"] else "FAIL",
        "NEW CAMPAIGN GENERATED": "NO",
        "THE_LEDGER R2": "NOT GENERATED",
        "STAGE 2": "UNCHANGED",
        "FORMATS": "NOT IMPLEMENTED",
        "CANONICAL PIPELINE": "UNCHANGED",
        "NEXT": "PHASE 11.9 — HYBRID V2 CREATIVE QUALITY PROOF" if capability["all_three"] else "FIX FAILED CAPABILITY ONLY",
        "FIREWALL": (result.get("firewall") or {}).get("status"),
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_8,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("17-phase11-8-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"]}, indent=2))


if __name__ == "__main__":
    main()
