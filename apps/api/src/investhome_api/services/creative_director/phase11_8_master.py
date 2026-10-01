"""Phase 11.8 — Hybrid Premium Engine V2 capability tests.

Does not generate a campaign. Does not create THE_LEDGER R2.
Does not modify Proofs 01–03, 11.6, 11.7 R1, Masters, cover, or Stage 2.
Canonical Stage 3 router remains unchanged.
"""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID, hybrid_engine_v2_contract
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    PRODUCTION_COVER_V2,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r3_approve_lock import APPROVED_ASSET_02
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r2_approve_lock import APPROVED_ASSET_03
from investhome_api.services.creative_director.phase10_0_master import _identity_slice
from investhome_api.services.creative_director.phase10_3_finalize import preserve_stage2, restore_stage2
from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID, DAY003_FILENAME
from investhome_api.services.creative_director.phase11_8_boards import (
    contact_test_board,
    edge_test_board,
    hierarchy_scale_board,
    material_test_board,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.creative_director.project_object_extraction_v2 import (
    EDGE_BACKGROUNDS,
    extract_project_object_v2,
    inspect_fringe,
    spire_preserved,
)
from investhome_api.services.creative_director.project_reality_firewall_v1 import run_project_reality_firewall
from investhome_api.services.creative_director.responsive_commercial_hierarchy_v2 import render_hierarchy_proof
from investhome_api.services.creative_director.scene_material_integration_v2 import (
    analyze_field,
    contact_occlusion_model,
    integrate_object_into_field,
    match_object_to_field,
    object_layout,
    paper_luminance_mask,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_11_8 = "phase11_8_hybrid_premium_engine_v2"
ORIGINAL_FIELD = Path("/tmp/phase11-6-hybrid-premium-engine/06-generated-field.png")
LOCKED_PATHS = (
    Path("/tmp/phase11-6-hybrid-premium-engine/09-hybrid-premium-proof.png"),
    Path("/tmp/phase11-7-hybrid-finish/07-hybrid-premium-proof-r1.png"),
)


def _assert_untouched_masters(library: dict[str, Any], m1, m2, m3, kids, p1s, p2s, p3s) -> None:
    m1a = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    m2a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    m3a = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(m1a), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 11.8 refused to change Master 01")
    if json.dumps(_jsonable(m2a), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 11.8 refused to change Master 02")
    if _identity_slice(m3a) != m3:
        raise RuntimeError("Phase 11.8 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (m3a.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 11.8 refused to mutate Stage 2 children")
    if str(m1a.get("visual_asset")) != APPROVED_ASSET_ID or str(m2a.get("visual_asset")) != APPROVED_ASSET_02 or str(m3a.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 11.8 refused to change master visuals")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 11.8 refused to change approved premium count")
    if p1s is not None and library.get("stage_3_creative_quality_proof") != p1s:
        raise RuntimeError("Phase 11.8 refused to rewrite Proof 01")
    if p2s is not None and library.get("stage_3_creative_quality_proof_02") != p2s:
        raise RuntimeError("Phase 11.8 refused to rewrite Proof 02")
    if p3s is not None and library.get("stage_3_creative_quality_proof_03") != p3s:
        raise RuntimeError("Phase 11.8 refused to rewrite Proof 03")


def generate_phase11_8_engine_v2(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
) -> dict[str, Any]:
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    for src, alias in (
        ("phase11_0_foundation_tests", "quality110"),
        ("phase11_1_creative_quality_proof_tests", "quality111"),
        ("phase11_2_creative_quality_proof_tests", "quality112"),
        ("phase11_3_commercial_creative_system_tests", "quality113"),
        ("phase11_4_creative_quality_proof_tests", "quality114"),
        ("phase11_6_hybrid_premium_engine_tests", "quality116"),
        ("phase11_7_hybrid_finish_tests", "quality117"),
    ):
        preserved[alias] = list(blob.get(src) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 11.8 requires ProjectCreativeMasterLibraryV1")
    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 11.8 requires locked Masters 01–03")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    p1s, p2s, p3s = library.get("stage_3_creative_quality_proof"), library.get("stage_3_creative_quality_proof_02"), library.get("stage_3_creative_quality_proof_03")
    locked_bytes = {str(path): path.read_bytes() if path.is_file() else None for path in LOCKED_PATHS}

    if not ORIGINAL_FIELD.is_file():
        raise RuntimeError("Phase 11.8 requires the retained Phase 11.6 non-project field")
    field = Image.open(ORIGINAL_FIELD).convert("RGB")
    firewall = run_project_reality_firewall(field)
    if firewall.get("status") != "PASS":
        raise RuntimeError("Retained field failed ProjectRealityFirewallV1")
    source = Image.open(BytesIO(_read_bytes(db, UUID(DAY003_ASSET_ID)))).convert("RGB")
    obj, extract_meta = extract_project_object_v2(source)
    if int(extract_meta.get("generated_architecture_pixels") or 0) != 0:
        raise RuntimeError("Extraction V2 invented architecture pixels")

    edge_reports = {}
    edge_images = {}
    for name, color in EDGE_BACKGROUNDS.items():
        edge_reports[name] = inspect_fringe(obj, color)
        edge_images[name] = edge_test_board(obj, color, name.upper())
    spire = spire_preserved(obj)
    extraction_pass = all(item.get("pass") for item in edge_reports.values()) and bool(spire.get("preserved"))

    fused, integrate_meta = integrate_object_into_field(field, obj)
    paper = paper_luminance_mask(field)
    layout = object_layout(obj, paper, field.size)
    matched, _match = match_object_to_field(obj, analyze_field(field))
    layers = contact_occlusion_model(
        field=field,
        obj=matched,
        layout=layout,
        field_stats=analyze_field(field),
    )
    material_board = material_test_board(field, obj, matched, fused)
    contact_board = contact_test_board(field, fused, layers["overlay"], layers["ambient"])

    hier_full, hier_report, thumbs = render_hierarchy_proof()
    if provider_call_count() != 0:
        raise RuntimeError("Phase 11.8 must not generate images")

    _assert_untouched_masters(library, m1, m2, m3, kids, p1s, p2s, p3s)
    for path, payload in locked_bytes.items():
        p = Path(path)
        if payload is not None and p.is_file() and p.read_bytes() != payload:
            raise RuntimeError(f"Phase 11.8 refused to modify locked proof {p.name}")

    extraction_ok = extraction_pass
    lighting_ok = not bool((integrate_meta.get("match") or {}).get("generative_relight"))
    contact_ok = (integrate_meta.get("contact") or {}).get("full_silhouette_drop_shadow") is False
    hierarchy_ok = bool(hier_report.get("pass"))
    all_ok = extraction_ok and lighting_ok and contact_ok and hierarchy_ok and firewall.get("status") == "PASS"
    status = "HYBRID_PREMIUM_ENGINE_V2_READY" if all_ok else "HYBRID_PREMIUM_ENGINE_V2_FAIL"

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    restore_stage2(blob, preserved)
    blob["phase11_0_foundation_tests"] = preserved.get("quality110")
    blob["phase11_1_creative_quality_proof_tests"] = preserved.get("quality111")
    blob["phase11_2_creative_quality_proof_tests"] = preserved.get("quality112")
    blob["phase11_3_commercial_creative_system_tests"] = preserved.get("quality113")
    blob["phase11_4_creative_quality_proof_tests"] = preserved.get("quality114")
    blob["phase11_6_hybrid_premium_engine_tests"] = preserved.get("quality116")
    blob["phase11_7_hybrid_finish_tests"] = preserved.get("quality117")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_11_8,
        "created_at": _now(),
        "status": status,
        "engine": ENGINE_ID,
        "engine_contract": hybrid_engine_v2_contract(),
        "source": {"filename": DAY003_FILENAME, "asset_id": DAY003_ASSET_ID},
        "firewall": firewall,
        "extract_meta": extract_meta,
        "edge_reports": edge_reports,
        "spire": spire,
        "extraction_pass": extraction_ok,
        "integrate_meta": integrate_meta,
        "hierarchy": hier_report,
        "new_campaign_generated": False,
        "ledger_r2": False,
        "gpt_image_calls": provider_call_count(),
        "cover": PRODUCTION_COVER_V2,
        "canonical_pipeline": "UNCHANGED",
    }
    tests = list(blob.get("phase11_8_engine_v2_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["phase11_8_engine_v2_tests"] = tests
    ctx = dict(original_ctx)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["identity"] = {"before": before, "after": after}
    record["images"] = {
        "object": obj,
        "fused": fused,
        "edges": edge_images,
        "material": material_board,
        "contact": contact_board,
        "hierarchy": hier_full,
        "thumbs": thumbs,
        "scale_board": hierarchy_scale_board(thumbs),
    }
    return record
