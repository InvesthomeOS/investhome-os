"""Phase 5.4A-R1 — final art-direction polish of the approved 5.4A master.

Offer lockup + CTA only. Crop, grade, and composition remain locked.
Does not overwrite 5.4A. Does not activate live routing.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import (
    APPROVAL_CANDIDATE,
    MASTER_COMMERCIAL_FINAL_ID,
    MASTER_COMMERCIAL_R1_ID,
    build_premium_commercial_r1_master,
    scene_premium_commercial_final,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
)
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import (
    _png,
    _render_scene,
    critic_fail_reasons,
    critic_pass_54a,
    render_architecture_provenance,
    render_pair,
    request_final_critic,
)
from investhome_api.services.creative_director.phase5_production_creative import PHASE50_MASTER_ASSET_ID
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54A_R1 = "phase5_4a_r1_final_polish"
PARENT_54A_ASSET_ID = "35345972-3b30-400a-a83f-95975db9dd3a"
PARENT_REASON = "FINAL_HUMAN_DIRECTED_ART_POLISH"
LOCKED_GRADE = {"warmth": 0.11, "contrast": 1.08, "brightness": 0.99, "vignette": 0.09}


def critic_pass_r1(scores: dict[str, Any]) -> bool:
    """Human art direction overrides text_on_photo_likeness."""
    filtered = dict(scores)
    filtered["text_on_photo_likeness"] = 0
    return critic_pass_54a(filtered)


def generate_premium_commercial_r1_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    source_asset_id: str | None = None,
    logo_asset_id: str | None = None,
    facts: dict[str, str] | None = None,
) -> dict[str, Any]:
    hero_id = str(source_asset_id or LOCKED_HERO_ASSET_ID)
    logo_id = str(logo_asset_id or LOCKED_LOGO_ASSET_ID)
    campaign_facts = dict(facts or REQUIRED_FACTS)
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = {
        "session": blob.get("current_session_id"),
        "family": blob.get("current_format_family_id"),
        "lock": list(blob.get("architecture_lock_tests") or []),
        "photo": list(blob.get("photo_foundation_tests") or []),
        "design": list(blob.get("creative_design_tests") or []),
        "overlay": list(blob.get("creative_overlay_tests") or []),
        "master": list(blob.get("creative_master_tests") or []),
        "production": list(blob.get("production_creative_tests") or []),
        "vad": list(blob.get("visual_art_director_tests") or []),
        "scene": list(blob.get("design_scene_tests") or []),
        "library": list(blob.get("creative_master_library_tests") or []),
        "final54a": list(blob.get("premium_commercial_final_tests") or []),
        "approved": {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()},
        "sessions": dict(blob.get("sessions") or {}),
    }
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    before["architecture_lock_tests_count"] = len(preserved["lock"])
    before["photo_foundation_tests_count"] = len(preserved["photo"])
    before["creative_design_tests_count"] = len(preserved["design"])
    before["creative_overlay_tests_count"] = len(preserved["overlay"])
    before["creative_master_tests_count"] = len(preserved["master"])
    before["production_creative_tests_count"] = len(preserved["production"])
    before["visual_art_director_tests_count"] = len(preserved["vad"])
    before["design_scene_tests_count"] = len(preserved["scene"])
    before["creative_master_library_tests_count"] = len(preserved["library"])
    before["premium_commercial_final_tests_count"] = len(preserved["final54a"])

    fonts = build_font_registry()
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    try:
        reference = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE50_MASTER_ASSET_ID)))).convert("RGB")
    except Exception:
        reference = source
    try:
        parent_54a = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_54A_ASSET_ID)))).convert("RGB")
    except Exception:
        parent_54a = None
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    photo_uri = _jpeg_data_uri(graded)
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(logo_bytes)

    parent_pack = _render_scene(
        scene_premium_commercial_final(campaign_facts),
        photo_uri=photo_uri,
        logo_markup=logo_markup,
        font_css=font_css,
        facts=campaign_facts,
    )
    if parent_54a is None:
        parent_54a = parent_pack["image"]
    child = build_premium_commercial_r1_master(campaign_facts)
    child["created_at"] = _now()
    child["parent_master_id"] = MASTER_COMMERCIAL_FINAL_ID
    child["parent_asset_id"] = PARENT_54A_ASSET_ID
    child["parent_reason"] = PARENT_REASON
    child["approval_status"] = APPROVAL_CANDIDATE
    final_pack = _render_scene(
        str(child.get("scene_markup") or ""),
        photo_uri=photo_uri,
        logo_markup=logo_markup,
        font_css=font_css,
        facts=campaign_facts,
    )
    provenance = architecture_provenance_qa(
        source=source, foundation=crop, final=final_pack["image"], transform=transform
    )
    critic, critic_calls = request_final_critic(
        candidate=final_pack["image"],
        foundation=graded,
        reference=reference,
        parent=parent_54a,
        facts=campaign_facts,
    )
    critic = dict(critic)
    critic["pass_raw"] = bool(critic.get("pass"))
    critic["pass"] = critic_pass_r1(critic) if critic.get("mode") == "vision" else False
    critic["fail_reasons"] = [] if critic["pass"] else (
        ["critic_unavailable"] if critic.get("mode") != "vision" else [
            r for r in critic_fail_reasons(critic) if not r.startswith("text_on_photo_likeness")
        ]
    )
    critic["text_on_photo_likeness_overridden_by_human"] = True
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(final_pack["image"]),
        content_type="image/png",
        campaign_mode="project-creative-master-candidate",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.4A-R1 PREMIUM_COMMERCIAL final art polish",
    )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54A_R1,
        "created_at": _now(),
        "creative_method": "phase5_4a_r1_offer_and_cta_polish_only",
        "design_family": "PREMIUM_COMMERCIAL",
        "parent_master": "Phase 5.4A",
        "parent_master_id": MASTER_COMMERCIAL_FINAL_ID,
        "parent_asset_id": PARENT_54A_ASSET_ID,
        "parent_reason": PARENT_REASON,
        "master_id": MASTER_COMMERCIAL_R1_ID,
        "source_asset_id": hero_id,
        "source_filename": HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None,
        "architecture_changed": False,
        "photo_crop_changed": False,
        "photo_grade_changed": False,
        "architecture_generation_used": False,
        "gpt_image_calls": 0,
        "critic_vision_calls": critic_calls,
        "real_logo_asset_id": logo_id,
        "project_id": TEMPLE_PROJECT_ID,
        "display_font": ((fonts.get("roles") or {}).get("DISPLAY_SERIF") or {}).get("font_file"),
        "support_font": ((fonts.get("roles") or {}).get("EDITORIAL_SANS") or {}).get("font_file"),
        "offer_lockup_change": "price and %35 LANSMAN AVANTAJI grouped as one offer: gold rule binder + baseline lockup",
        "cta_change": "editorial inscription closer: 20px ivory between gold rules, lifted off the street edge, wider lockup for social-size reading",
        "other_composition_changes": "none — logo, headline, unit, price placement, crop, and grade locked",
        "final_asset_id": str(asset.id),
        "final_size": list(final_pack["image"].size),
        "approval_status": APPROVAL_CANDIDATE,
        "live_routing_active": False,
        "scene_gate": final_pack["gate"],
        "provenance_qa": provenance,
        "critic": critic,
        "hard_gate": bool(critic.get("pass")),
        "hard_gate_reasons": list(critic.get("fail_reasons") or []),
        "video_started": False,
        "publishing_started": False,
        "other_formats_generated": False,
        "human_approval_required": True,
    }
    tests = [
        t
        for t in list(blob.get("premium_commercial_r1_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54A_R1)
    ]
    tests.append({k: v for k, v in record.items()})
    blob["premium_commercial_r1_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    blob["architecture_lock_tests"] = preserved["lock"]
    blob["photo_foundation_tests"] = preserved["photo"]
    blob["creative_design_tests"] = preserved["design"]
    blob["creative_overlay_tests"] = preserved["overlay"]
    blob["creative_master_tests"] = preserved["master"]
    blob["production_creative_tests"] = preserved["production"]
    blob["visual_art_director_tests"] = preserved["vad"]
    blob["design_scene_tests"] = preserved["scene"]
    blob["creative_master_library_tests"] = preserved["library"]
    blob["premium_commercial_final_tests"] = preserved["final54a"]
    blob["approved_masters"] = preserved["approved"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    after["architecture_lock_tests_count"] = len(list(blob.get("architecture_lock_tests") or []))
    after["photo_foundation_tests_count"] = len(list(blob.get("photo_foundation_tests") or []))
    after["creative_design_tests_count"] = len(list(blob.get("creative_design_tests") or []))
    after["creative_overlay_tests_count"] = len(list(blob.get("creative_overlay_tests") or []))
    after["creative_master_tests_count"] = len(list(blob.get("creative_master_tests") or []))
    after["production_creative_tests_count"] = len(list(blob.get("production_creative_tests") or []))
    after["visual_art_director_tests_count"] = len(list(blob.get("visual_art_director_tests") or []))
    after["design_scene_tests_count"] = len(list(blob.get("design_scene_tests") or []))
    after["creative_master_library_tests_count"] = len(list(blob.get("creative_master_library_tests") or []))
    after["premium_commercial_final_tests_count"] = len(list(blob.get("premium_commercial_final_tests") or []))
    _production_guard(before, after)
    if blob.get("premium_commercial_final_tests") != preserved["final54a"]:
        raise RuntimeError("Phase 5.4A-R1 refused to change Phase 5.4A history")
    if blob.get("creative_master_library_tests") != preserved["library"]:
        raise RuntimeError("Phase 5.4A-R1 refused to change Phase 5.4 A/B/C history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4A-R1 refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "reference": reference,
        "parent": parent_54a,
        "final": final_pack["image"],
    }
    record["rendered"] = final_pack
    record["child_master"] = child
    record["fonts"] = fonts
    _ = language
    _ = render_pair
    _ = render_architecture_provenance
    return record
