"""Phase 5.2 — AI Reels video from an approved Phase 5.0 Master.

Provider-independent workflow: context, plan, versioning, revision, approval, QA.
Does not overwrite the Approved Master or Phase 5.1 format family.
Does not fake video with slideshows, CSS, or FFmpeg ken-burns.
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset, MediaAssetSourceType
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import CreativeDirectorReviseAdResponse
from investhome_api.services.creative_director.generate_ad import project_asset_lock_summary
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.orchestrator import assign_capabilities
from investhome_api.services.creative_director.phase5_format_adaptation import approved_semantic_content
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    TEMPLE_PROJECT_ID,
    WORKFLOW_ID,
    _lock_temple_assets,
    _now,
    _phase5,
    _production_guard,
    _write_phase5,
)
from investhome_api.services.creative_director.project_architecture_lock import architecture_lock_policy
from investhome_api.services.creative_studio_media_service import asset_content_url
from investhome_api.services.document_validation import content_stream
from investhome_api.services.gpt_image_design.persistence import asset_url
from investhome_api.services.storage.factory import get_storage_provider, provider_enum

logger = logging.getLogger(__name__)

WORKFLOW_ID_52 = "phase5_reels_video"
LOCKED_MASTER_ID = "5765e350-06f5-45d6-9e70-a63cd4dd2072"
LOCKED_FORMAT_FAMILY_ID = "2f29711d-285c-4e6d-a1b8-5b058eeb58b4"
TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920
TARGET_DURATION = 12.0


def video_architecture_lock_interface() -> dict[str, Any]:
    """Reusable 5.1A policy for a future stricter video lock. Does not generate video."""
    policy = architecture_lock_policy(
        source_asset_id=LOCKED_HERO_ASSET_ID,
        source_filename=HERO_FILENAME,
    )
    return {
        "architecture_lock_policy": policy["policy_name"],
        "source_architecture_asset": policy["source_architecture_asset_id"],
        "protected_architecture_reference": policy["video"]["protected_architecture_reference"],
        "qa_method": policy["video"]["qa_method"],
        "stricter_for_video": True,
        "video_started": False,
    }

VIDEO_GENERATE_MARKERS = (
    "reel",
    "reels",
    "video üret",
    "video uret",
    "video yap",
    "video hazırla",
    "video hazirla",
)
VIDEO_REVISE_MARKERS = (
    "videoyu",
    "video daha",
    "sahneyi",
    "ilk sahne",
    "müzik",
    "muzik",
    "geçiş",
    "gecis",
    "yavaş",
    "yavas",
    "ekranda",
)


def discover_video_capability() -> dict[str, Any]:
    plan = assign_capabilities(["video_generate", "video_edit", "music"])
    by_cap = {a.capability: a for a in plan.assignments}
    gen = by_cap.get("video_generate")
    edit = by_cap.get("video_edit")
    music = by_cap.get("music")
    usable = bool(gen and gen.available and not gen.missing)
    return {
        "provider": (gen.provider_id if gen else None) or "video_stub",
        "model": None,
        "video_generate": bool(usable),
        "video_edit": bool(edit and edit.available and not edit.missing),
        "image_to_video": False,
        "reference_image_video": False,
        "aspect_9_16": False,
        "duration_control": False,
        "project_image_conditioning": False,
        "video_revision": bool(edit and edit.available and not edit.missing),
        "first_frame_or_keyframe": False,
        "audio": bool(music and music.available and not music.missing),
        "usable": usable,
        "reason": (gen.reason if gen else "No video provider registered"),
        "missing_capabilities": list(plan.missing_capabilities),
        "assignments": [a.__dict__ for a in plan.assignments],
    }


def select_approved_project_visuals(db: Session, project_id: UUID) -> list[dict[str, str]]:
    """Traceable approved project images only. Hero is always first."""
    chosen: list[dict[str, str]] = [
        {"asset_id": LOCKED_HERO_ASSET_ID, "filename": HERO_FILENAME, "role": "approved_hero"}
    ]
    seen = {LOCKED_HERO_ASSET_ID, LOCKED_LOGO_ASSET_ID}
    rows = list(
        db.scalars(
            select(CreativeStudioMediaAsset)
            .where(
                CreativeStudioMediaAsset.linked_project_id == project_id,
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
            .limit(80)
        ).all()
    )
    for row in rows:
        aid = str(row.id)
        if aid in seen:
            continue
        ctype = (row.content_type or "").lower()
        name = (row.filename or "").lower()
        cat = (row.folder_category or "").upper()
        if not ctype.startswith("image"):
            continue
        if "logo" in name or cat == "01_BRAND":
            continue
        exterior = "exterior" in name or "cephe" in name or "render" in name or cat.startswith("02_RENDER")
        if not exterior and "temple" not in name:
            continue
        chosen.append(
            {
                "asset_id": aid,
                "filename": str(row.filename or ""),
                "role": "approved_project_visual",
            }
        )
        seen.add(aid)
        if len(chosen) >= 4:
            break
    return chosen


def build_video_creative_context(
    *,
    session: dict[str, Any],
    facts: dict[str, str],
    project_visuals: list[dict[str, str]],
    user_request: str,
    previous_video_version: dict[str, Any] | None = None,
    revision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    master = session.get("approved_master") or {}
    return {
        "approved_master_id": master.get("master_id"),
        "approved_version_id": master.get("approved_version_id"),
        "approved_master_asset_id": master.get("master_asset_id"),
        "format_family_id": session.get("format_family_id") or master.get("format_family_id"),
        "campaign_identity": (master.get("creative_identity") or {}).get("concept") or facts.get("headline"),
        "project_identity": {"project_id": session.get("project_id"), "name": "The Temple"},
        "project_asset_policy": "PROJECT_LOCKED",
        "approved_campaign_content": dict(facts),
        "approved_project_assets": list(project_visuals),
        "logo_asset_id": master.get("logo_asset") or LOCKED_LOGO_ASSET_ID,
        "target_platform": "instagram_reels",
        "target_aspect_ratio": "9:16",
        "target_width": TARGET_WIDTH,
        "target_height": TARGET_HEIGHT,
        "target_duration_seconds": TARGET_DURATION,
        "user_request": user_request,
        "video_generation_constraints": [
            "Motion version of the approved campaign, not a new concept.",
            "Do not invent architecture, façades, interiors, or logos.",
            "Restrained cinematic motion only.",
            "Facts must match the approved Master exactly.",
            "No copyrighted commercial music.",
        ],
        "previous_video_version_id": (previous_video_version or {}).get("version_id"),
        "revision_instructions": revision,
    }


def build_video_creative_plan(context: dict[str, Any]) -> dict[str, Any]:
    """Campaign-specific plan from this Master's facts and selected assets — not a stock template."""
    facts = context["approved_campaign_content"]
    visuals = list(context.get("approved_project_assets") or [])
    master_id = str(context.get("approved_master_asset_id") or "")
    hero = visuals[0]["asset_id"] if visuals else LOCKED_HERO_ASSET_ID
    extra = visuals[1]["asset_id"] if len(visuals) > 1 else hero
    duration = float(context.get("target_duration_seconds") or TARGET_DURATION)
    beats = [
        {
            "beat": "attention",
            "purpose": f"Open on the approved {facts['headline']} campaign identity.",
            "source_asset_id": master_id or hero,
            "approx_seconds": 2.5,
            "motion": "slow cinematic push, no aggressive reconstruction",
            "on_screen_text": facts["headline"],
        },
        {
            "beat": "project",
            "purpose": "Reveal The Temple architecture from an approved project photograph.",
            "source_asset_id": hero,
            "approx_seconds": 3.0,
            "motion": "gentle camera drift / subtle parallax",
            "on_screen_text": None,
        },
        {
            "beat": "opportunity",
            "purpose": "Hold the launch-advantage idea without new financial claims.",
            "source_asset_id": extra,
            "approx_seconds": 2.5,
            "motion": "controlled reveal",
            "on_screen_text": f"{facts['discount']} {facts['discount_label']}",
        },
        {
            "beat": "commercial",
            "purpose": "State approved unit and price.",
            "source_asset_id": master_id or hero,
            "approx_seconds": 2.5,
            "motion": "hold; prefer factual text overlay if generative text is unreliable",
            "on_screen_text": f"{facts['unit']} {facts['unit_label']} · {facts['list_price']}",
        },
        {
            "beat": "cta_brand",
            "purpose": "Close on CTA and real project logo.",
            "source_asset_id": str(context.get("logo_asset_id") or LOCKED_LOGO_ASSET_ID),
            "approx_seconds": 1.5,
            "motion": "settle",
            "on_screen_text": facts["cta"],
        },
    ]
    return {
        "plan_id": str(uuid4()),
        "created_at": _now(),
        "target_format": "instagram_reels_9:16",
        "approx_duration_seconds": duration,
        "opening_hook": facts["headline"],
        "scene_progression": [b["beat"] for b in beats],
        "beats": beats,
        "source_asset_ids": [str(v["asset_id"]) for v in visuals] + [master_id],
        "logo_asset_id": context.get("logo_asset_id"),
        "motion_strategy": "restrained cinematic push, subtle parallax, no architectural hallucination",
        "text_reveal_strategy": "controlled title compositing if the video model cannot paint accurate text",
        "commercial_timing": "price and unit visible in the commercial beat; hold longer if revision asks",
        "cta_ending": facts["cta"],
        "logo_ending": True,
        "transition_logic": "simple cuts / dissolves only; no hyperactive or meme transitions",
        "audio": "silent unless a licensed/generated music capability is connected",
        "locked_facts": dict(facts),
        "not_a_fixed_template": True,
    }


def interpret_video_revision(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    folded = raw.casefold()
    changes: list[str] = []
    if any(k in folded for k in ("yavaş", "yavas", "premium", "sakin")):
        changes.append("pace_slower")
    if any(k in folded for k in ("kısalt", "kisalt")):
        changes.append("timing_shorten_opening")
    if "fiyat" in folded or "675" in folded or "ekranda" in folded:
        changes.append("text_timing_price_longer")
    if "logo" in folded:
        changes.append("logo")
    if any(k in folded for k in ("görsel", "gorsel", "dış cephe", "dis cephe")):
        changes.append("scene_replace_exterior")
    if any(k in folded for k in ("müzik", "muzik")):
        changes.append("audio")
    if any(k in folded for k in ("geçiş", "gecis")):
        changes.append("transition_simplify")
    if not changes:
        changes.append("pace_or_tone")
    return {
        "requested_changes": changes,
        "pace": "slower" if "pace_slower" in changes else None,
        "price_hold": "longer" if "text_timing_price_longer" in changes else None,
        "preserve_campaign_identity": True,
        "locked_facts": True,
        "user_instruction": raw,
        "scope": "local",
    }


def apply_revision_to_plan(plan: dict[str, Any], revision: dict[str, Any]) -> dict[str, Any]:
    next_plan = deepcopy(plan)
    next_plan["plan_id"] = str(uuid4())
    next_plan["parent_plan_id"] = plan.get("plan_id")
    next_plan["revision"] = revision
    if revision.get("pace") == "slower":
        next_plan["approx_duration_seconds"] = min(15.0, float(next_plan.get("approx_duration_seconds") or 12) + 2.0)
        next_plan["motion_strategy"] = "slower, more premium, still restrained"
        for beat in next_plan.get("beats") or []:
            beat["approx_seconds"] = round(float(beat.get("approx_seconds") or 2) * 1.15, 2)
    if revision.get("price_hold") == "longer":
        for beat in next_plan.get("beats") or []:
            if beat.get("beat") == "commercial":
                beat["approx_seconds"] = round(float(beat.get("approx_seconds") or 2.5) + 1.2, 2)
                beat["motion"] = "hold the approved price on screen longer"
        next_plan["commercial_timing"] = "price remains on screen longer than v1"
    next_plan["created_at"] = _now()
    return next_plan


def generate_video(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Provider adapter. No connected video backend exists in this OS today."""
    cap = discover_video_capability()
    if not cap["usable"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "message": "No usable video generation provider is connected.",
                "missing_capabilities": cap["missing_capabilities"],
                "reason": cap["reason"],
                "workflow": WORKFLOW_ID_52,
            },
        )
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Video provider listed as available but no adapter is implemented.",
    )


def persist_video_asset(
    db: Session,
    *,
    actor: User,
    linked_project_id: UUID | None,
    content: bytes,
    session_id: str,
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
) -> CreativeStudioMediaAsset:
    now = datetime.now(UTC)
    storage_key = f"creative-studio/{now.year:04d}/{now.month:02d}/{uuid4().hex}.mp4"
    storage = get_storage_provider()
    storage.save(storage_key, content_stream(content), content_length=len(content))
    asset = CreativeStudioMediaAsset(
        filename=f"phase5-reel-{session_id[:8]}.mp4",
        content_type="video/mp4",
        file_size=len(content),
        width=width,
        height=height,
        storage_provider=provider_enum().value,
        storage_key=storage_key,
        linked_project_id=linked_project_id,
        uploaded_by_user_id=actor.id,
        source_type=MediaAssetSourceType.UPLOAD.value,
        tags=["phase5", "reels", f"session:{session_id}"],
    )
    db.add(asset)
    db.flush()
    return asset


def video_qa(
    *,
    content: bytes | None,
    declared: dict[str, Any],
    facts: dict[str, str],
    source_asset_ids: list[str],
) -> dict[str, Any]:
    playable = bool(content) and (b"ftyp" in (content[:64] if content else b""))
    ratio_ok = int(declared.get("width") or 0) > 0 and abs(
        (int(declared.get("width") or 1) / max(int(declared.get("height") or 1), 1)) - (9 / 16)
    ) < 0.08
    duration = float(declared.get("duration") or 0)
    duration_ok = 8.0 <= duration <= 16.0 if duration else False
    hero_ok = LOCKED_HERO_ASSET_ID in source_asset_ids
    logo_ok = LOCKED_LOGO_ASSET_ID in source_asset_ids or str(declared.get("logo_asset_id")) == LOCKED_LOGO_ASSET_ID
    price_ok = facts.get("list_price") == "675.000 USD"
    old_price = facts.get("list_price") == "438.750 USD"
    return {
        "playable_video": playable,
        "aspect_ratio_ok": ratio_ok,
        "duration_ok": duration_ok,
        "duration": duration,
        "project_asset_integrity": "pass" if hero_ok else "fail",
        "logo_presence": "pass" if logo_ok else "unverified",
        "content_integrity": "fail" if old_price or not price_ok else "pass",
        "campaign_identity": "pass" if facts.get("headline") == "ALIRKEN KAZAN" else "fail",
        "architecture_integrity": "unverified" if not playable else "review",
        "cta_presence": "pass" if facts.get("cta") else "fail",
        "unexpected_redesign": False,
        "failed": (not playable) or old_price or not hero_ok,
    }


def _current_video(blob: dict[str, Any], session: dict[str, Any]) -> dict[str, Any] | None:
    vid = session.get("current_video_id") or blob.get("current_video_id")
    videos = dict(blob.get("videos") or {})
    row = videos.get(str(vid)) if vid else None
    return dict(row) if isinstance(row, dict) else None


def _persist_video(ctx: dict[str, Any], session: dict[str, Any], video: dict[str, Any]) -> None:
    blob = _phase5(ctx)
    videos = dict(blob.get("videos") or {})
    videos[str(video["video_id"])] = video
    blob["videos"] = videos
    blob["current_video_id"] = video["video_id"]
    ctx[CTX_KEY] = blob
    session["current_video_id"] = video["video_id"]
    session["video_started"] = True
    session["publishing_started"] = False
    hooks = dict(session.get("next_hooks") or {})
    hooks["video"] = video.get("status") or "started"
    hooks["reel"] = video.get("status") or "started"
    hooks["publishing"] = "unstarted"
    session["next_hooks"] = hooks
    if video.get("status") == "APPROVED":
        session["status"] = "VIDEO_READY"
    elif session.get("status") in {"APPROVED", "FORMAT_ADAPTATION_READY"}:
        session["status"] = session.get("status")
    _write_phase5(ctx, session)


def _blocked_response(
    *,
    row: CreativeDirectorCampaign,
    session: dict[str, Any],
    video: dict[str, Any],
    facts: dict[str, str],
    cap: dict[str, Any],
    interior_id: UUID,
    logo_id: UUID,
    language: str,
    intent: str,
) -> CreativeDirectorReviseAdResponse:
    master = session.get("approved_master") or {}
    master_asset = UUID(str(master.get("master_asset_id")))
    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio="9:16",
        format_preset="reelsCover",
        production_mode="finished_ad",
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=master_asset,
        final_asset_url=asset_url(master_asset),
        master_asset_id=master_asset,
        master_finished_ad_asset_id=master_asset,
        finished_ad_raster_asset_id=master_asset,
        final_turkish_texts=facts,
        provider_call_count=0,
        gpt_image_call_count=0,
        user_feedback="Reels şu anda üretilemiyor.",
        revision_intents=[intent],
        quality_guard={
            "status": "blocked",
            "workflow": WORKFLOW_ID_52,
            "phase5_session_workflow": WORKFLOW_ID,
            "session_id": session["session_id"],
            "session_status": session.get("status"),
            "video_id": video.get("video_id"),
            "video_status": video.get("status"),
            "video_provider_missing": True,
            "video_provider": cap.get("provider"),
            "missing_capabilities": cap.get("missing_capabilities"),
            "approved_master_changed": False,
            "format_family_changed": False,
            "phase4_renderer_used": False,
            "publishing_started": False,
            "note": "Provider-independent Reels workflow persisted. No video file generated. Visual PASS not claimed.",
        },
        campaign_context={
            "phase5_session_id": session["session_id"],
            "video": {
                "video_id": video.get("video_id"),
                "status": video.get("status"),
                "plan_id": ((video.get("versions") or [{}])[-1].get("video_plan") or {}).get("plan_id")
                if video.get("versions")
                else None,
            },
            "approved_master_id": master.get("master_id"),
            "format_family_id": session.get("format_family_id"),
        },
        interpreted_plan={"intent": intent, "provider_missing": True},
    )


def generate_or_revise_reel(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    ctx: dict[str, Any],
    session: dict[str, Any],
    *,
    language: str,
    interior_id: UUID,
    logo_id: UUID,
    interior_meta: dict[str, Any],
    logo_meta: dict[str, Any],
    instruction: str,
    intent: str,
) -> CreativeDirectorReviseAdResponse:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    interior_id, logo_id = _lock_temple_assets(row.linked_project_id, interior_id, logo_id)
    master = session.get("approved_master")
    if not isinstance(master, dict) or not master.get("master_asset_id"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Reels requires an approved Phase 5.0 Master.",
        )
    if session.get("status") not in {"APPROVED", "FORMAT_ADAPTATION_READY", "VIDEO_READY"} and intent == "VIDEO_GENERATE":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Approve the Master before Reels generation.",
        )
    master_asset_before = str(master["master_asset_id"])
    family_before = session.get("format_family_id")
    facts = approved_semantic_content(session)
    if facts.get("list_price") != "675.000 USD" and "438.750" in str(facts.get("list_price")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Refusing old non-approved price on Reels.",
        )
    cap = discover_video_capability()
    visuals = select_approved_project_visuals(db, UUID(str(session.get("project_id") or TEMPLE_PROJECT_ID)))
    blob = _phase5(ctx)
    video = _current_video(blob, session)
    revision = interpret_video_revision(instruction) if intent == "VIDEO_REVISE" else None

    if intent == "VIDEO_APPROVE":
        if not video or not video.get("current_version_id"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No Reels version to approve.",
            )
        if video.get("status") == "PROVIDER_MISSING":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot approve a Reels that was not generated.",
            )
        current = next(
            (v for v in video.get("versions") or [] if v.get("version_id") == video.get("current_version_id")),
            None,
        )
        if not isinstance(current, dict):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing current video version.")
        current["approval_state"] = "approved"
        approved = {
            "approved_video_id": str(uuid4()),
            "video_id": video["video_id"],
            "approved_version_id": current["version_id"],
            "approved_asset_id": current.get("asset_id"),
            "master_id": master["master_id"],
            "format_family_id": session.get("format_family_id"),
            "project_id": session.get("project_id"),
            "approval_timestamp": _now(),
            "publishing_started": False,
        }
        video["approved_version_id"] = current["version_id"]
        video["status"] = "APPROVED"
        video["approved_video"] = approved
        video["updated_at"] = _now()
        _persist_video(ctx, session, video)
        after = snapshot_identity(ctx)
        after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
        _production_guard(before, after)
        persisted = ((ctx.get(CTX_KEY) or {}).get("sessions") or {}).get(session["session_id"], {})
        if str((persisted.get("approved_master") or {}).get("master_asset_id")) != master_asset_before:
            raise RuntimeError("Phase 5.2 refused to change the approved Master")
        if family_before and persisted.get("format_family_id") != family_before:
            raise RuntimeError("Phase 5.2 refused to change the format family")
        row.context_json = ctx
        flag_modified(row, "context_json")
        db.flush()
        asset = UUID(str(current["asset_id"])) if current.get("asset_id") else UUID(master_asset_before)
        return CreativeDirectorReviseAdResponse(
            campaign_id=row.id,
            project_id=row.linked_project_id,
            language=language,
            aspect_ratio="9:16",
            format_preset="reelsCover",
            production_mode="finished_ad",
            interior_asset_id=interior_id,
            logo_asset_id=logo_id,
            final_asset_id=asset,
            final_asset_url=asset_content_url(asset) if current.get("asset_id") else asset_url(asset),
            master_asset_id=UUID(master_asset_before),
            provider_call_count=0,
            user_feedback="Video onaylandı.",
            revision_intents=["VIDEO_APPROVE"],
            quality_guard={
                "status": "review",
                "workflow": WORKFLOW_ID_52,
                "video_id": video["video_id"],
                "approved_version_id": current["version_id"],
                "approved_video_id": approved["approved_video_id"],
                "session_status": "VIDEO_READY",
                "approved_master_changed": False,
                "format_family_changed": False,
                "publishing_started": False,
                "phase4_renderer_used": False,
            },
            campaign_context={
                "phase5_session_id": session["session_id"],
                "status": "VIDEO_READY",
                "video": {"video_id": video["video_id"], "status": "APPROVED"},
            },
        )

    context = build_video_creative_context(
        session=session,
        facts=facts,
        project_visuals=visuals,
        user_request=instruction,
        previous_video_version=(video.get("versions") or [None])[-1] if video else None,
        revision=revision,
    )
    if intent == "VIDEO_REVISE":
        if not video:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No Reels to revise.",
            )
        parent = next(
            (v for v in video.get("versions") or [] if v.get("version_id") == video.get("current_version_id")),
            (video.get("versions") or [None])[-1],
        )
        plan = apply_revision_to_plan(dict((parent or {}).get("video_plan") or {}), revision or {})
        version_number = int((parent or {}).get("version_number") or 1) + 1
        parent_id = (parent or {}).get("version_id")
        generation_type = "REVISION"
        revision_method = "plan_plus_reference_regenerate" if not cap.get("video_edit") else "provider_video_edit"
    else:
        plan = build_video_creative_plan(context)
        version_number = 1
        parent_id = None
        generation_type = "INITIAL_GENERATION"
        revision_method = "provider_image_to_video"
        video = {
            "video_id": str(uuid4()),
            "session_id": session["session_id"],
            "master_id": master["master_id"],
            "format_family_id": session.get("format_family_id") or master.get("format_family_id"),
            "project_id": session.get("project_id"),
            "video_type": "REELS",
            "target_format": "instagram_reels_9:16",
            "status": "DRAFT",
            "current_version_id": None,
            "approved_version_id": None,
            "created_at": _now(),
            "updated_at": _now(),
            "versions": [],
        }

    source_ids = [v["asset_id"] for v in visuals] + [LOCKED_LOGO_ASSET_ID, str(master["master_asset_id"])]
    try:
        remote = generate_video(
            context=context,
            plan=plan,
            revision=revision,
            current_video=video,
        )
    except HTTPException as exc:
        if exc.status_code != status.HTTP_503_SERVICE_UNAVAILABLE:
            raise
        version = {
            "version_id": str(uuid4()),
            "video_id": video["video_id"],
            "version_number": version_number,
            "parent_version_id": parent_id,
            "asset_id": None,
            "user_instruction": instruction,
            "resolved_instruction": "Blocked: no connected video provider.",
            "video_plan": plan,
            "source_asset_ids": source_ids,
            "logo_asset_id": LOCKED_LOGO_ASSET_ID,
            "provider": cap.get("provider"),
            "provider_model": cap.get("model"),
            "generation_type": generation_type,
            "revision_method": None,
            "duration": TARGET_DURATION,
            "width": TARGET_WIDTH,
            "height": TARGET_HEIGHT,
            "created_at": _now(),
            "approval_state": "blocked",
            "qa": video_qa(content=None, declared={"width": TARGET_WIDTH, "height": TARGET_HEIGHT, "duration": 0, "logo_asset_id": LOCKED_LOGO_ASSET_ID}, facts=facts, source_asset_ids=source_ids),
        }
        versions = list(video.get("versions") or [])
        versions.append(version)
        video["versions"] = versions
        video["current_version_id"] = version["version_id"]
        video["status"] = "PROVIDER_MISSING"
        video["provider_capability"] = cap
        video["updated_at"] = _now()
        video["creative_context"] = context
        _persist_video(ctx, session, video)
        after = snapshot_identity(ctx)
        after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
        _production_guard(before, after)
        persisted = ((ctx.get(CTX_KEY) or {}).get("sessions") or {}).get(session["session_id"], {})
        if str((persisted.get("approved_master") or {}).get("master_asset_id")) != master_asset_before:
            raise RuntimeError("Phase 5.2 refused to change the approved Master")
        if family_before and persisted.get("format_family_id") != family_before:
            raise RuntimeError("Phase 5.2 refused to change the format family")
        row.context_json = ctx
        flag_modified(row, "context_json")
        db.flush()
        return _blocked_response(
            row=row,
            session=session,
            video=video,
            facts=facts,
            cap=cap,
            interior_id=interior_id,
            logo_id=logo_id,
            language=language,
            intent=intent,
        )

    content = remote.get("content")
    if not content:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Video provider returned no bytes.")
    asset = persist_video_asset(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=content,
        session_id=session["session_id"],
        width=int(remote.get("width") or TARGET_WIDTH),
        height=int(remote.get("height") or TARGET_HEIGHT),
    )
    qa = video_qa(
        content=content,
        declared={
            "width": remote.get("width") or TARGET_WIDTH,
            "height": remote.get("height") or TARGET_HEIGHT,
            "duration": remote.get("duration") or plan.get("approx_duration_seconds"),
            "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        },
        facts=facts,
        source_asset_ids=source_ids,
    )
    version = {
        "version_id": str(uuid4()),
        "video_id": video["video_id"],
        "version_number": version_number,
        "parent_version_id": parent_id,
        "asset_id": str(asset.id),
        "user_instruction": instruction,
        "resolved_instruction": remote.get("resolved_instruction") or plan.get("opening_hook"),
        "video_plan": plan,
        "source_asset_ids": source_ids,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "provider": remote.get("provider") or cap.get("provider"),
        "provider_model": remote.get("model"),
        "generation_type": generation_type,
        "revision_method": revision_method if intent == "VIDEO_REVISE" else "provider_image_to_video",
        "duration": remote.get("duration") or plan.get("approx_duration_seconds"),
        "width": remote.get("width") or TARGET_WIDTH,
        "height": remote.get("height") or TARGET_HEIGHT,
        "created_at": _now(),
        "approval_state": "qa_flagged" if qa.get("failed") else "draft",
        "qa": qa,
    }
    versions = list(video.get("versions") or [])
    versions.append(version)
    video["versions"] = versions
    video["current_version_id"] = version["version_id"]
    video["status"] = "DRAFT" if intent == "VIDEO_GENERATE" else "REVISING"
    video["updated_at"] = _now()
    video["creative_context"] = context
    _persist_video(ctx, session, video)
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    _production_guard(before, after)
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio="9:16",
        format_preset="reelsCover",
        production_mode="finished_ad",
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=asset.id,
        final_asset_url=asset_content_url(asset.id),
        master_asset_id=UUID(master_asset_before),
        project_asset_lock=project_asset_lock_summary(
            interior_id=interior_id,
            logo_id=logo_id,
            interior_meta={**dict(interior_meta), "filename": HERO_FILENAME},
            logo_meta=dict(logo_meta),
            source_asset_id=interior_id,
        ),
        final_turkish_texts=facts,
        provider_call_count=int(remote.get("provider_call_count") or 1),
        user_feedback=None,
        revision_intents=[intent],
        previous_asset_id=None,
        quality_guard={
            "status": "review",
            "workflow": WORKFLOW_ID_52,
            "video_id": video["video_id"],
            "version_id": version["version_id"],
            "version_number": version_number,
            "video_status": video["status"],
            "qa": qa,
            "approved_master_changed": False,
            "format_family_changed": False,
            "phase4_renderer_used": False,
            "publishing_started": False,
            "note": "User visual approval required — do not declare Visual Quality PASS.",
        },
        campaign_context={
            "phase5_session_id": session["session_id"],
            "video": {
                "video_id": video["video_id"],
                "version_id": version["version_id"],
                "asset_id": str(asset.id),
                "asset_url": asset_content_url(asset.id),
                "status": video["status"],
                "aspect_ratio": "9:16",
                "format_preset": "reelsCover",
            },
        },
        interpreted_plan=revision or {"intent": intent},
        change_diff_validation=qa,
    )
