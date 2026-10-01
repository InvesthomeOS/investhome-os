"""Phase 5.1A locked test family.

Generates a SEPARATE architecture-locked 4:5 + 1:1 / 9:16 / 16:9 family.
Does not overwrite the approved Phase 5.0 Master or the existing 5.1 family.
Does not start video or publishing.
"""

from __future__ import annotations

import io
import logging
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_format_adaptation import (
    FORMAT_TARGETS,
    _adaptation_prompt,
)
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _generation_prompt,
    _lock_temple_assets,
    _now,
    _phase5,
    _production_guard,
    _provider_generate_architecture_locked,
    _read_bytes,
    build_creative_context,
    provider_capability_record,
)
from investhome_api.services.creative_director.project_architecture_lock import (
    LOCK_METHOD,
    POLICY_NAME,
    architecture_lock_policy,
)
from investhome_api.services.creative_director.provider_router import (
    assert_image_provider_available,
    route_ad_social_image,
)
from investhome_api.services.gpt_image_design.persistence import asset_url

logger = logging.getLogger(__name__)

LOCKED_FAMILY_WORKFLOW = "phase5_1a_architecture_lock"


def generate_architecture_locked_test_family(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved_session = blob.get("current_session_id")
    preserved_family = blob.get("current_format_family_id")
    preserved_master_ids = {
        mid: dict(rec)
        for mid, rec in dict(blob.get("approved_masters") or {}).items()
    }

    interior_id, logo_id = _lock_temple_assets(
        row.linked_project_id, UUID(LOCKED_HERO_ASSET_ID), UUID(LOCKED_LOGO_ASSET_ID)
    )
    facts = dict(REQUIRED_FACTS)
    capability = provider_capability_record()
    if not capability["usable_for_project_locked"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Architecture-locked family requires a reference-capable image provider.",
        )
    route = route_ad_social_image(prefer_edit=True)
    assert_image_provider_available(route)

    test_session_id = str(uuid4())
    session = {"session_id": test_session_id}
    context = build_creative_context(
        user_request="The Temple architecture-locked ALIRKEN KAZAN test family",
        project_id=str(row.linked_project_id or TEMPLE_PROJECT_ID),
        hero_asset_id=str(interior_id),
        logo_asset_id=str(logo_id),
        facts=facts,
        target_format="instagram_feed_4:5",
    )
    prompt = _generation_prompt(context)
    master_pack = _one_locked(
        db,
        user,
        row,
        session,
        interior_id=interior_id,
        logo_id=logo_id,
        language=language,
        format_preset="portrait",
        aspect_ratio="4:5",
        prompt=prompt,
        extra_context={"finished_ad": True, "phase5_architecture_lock_test": True},
    )
    members = {
        "4:5": {
            "role": "architecture_locked_master",
            "asset_id": master_pack["asset_id"],
            "asset_url": master_pack["asset_url"],
            "qa": master_pack["qa"],
            "retries": master_pack["retries"],
            "provider": master_pack["provider"],
            "provider_model": master_pack["provider_model"],
        }
    }
    for target in FORMAT_TARGETS:
        adapt_prompt = _adaptation_prompt(facts=facts, target=target)
        pack = _one_locked(
            db,
            user,
            row,
            session,
            interior_id=interior_id,
            logo_id=logo_id,
            language=language,
            format_preset=str(target["format_preset"]),
            aspect_ratio=str(target["aspect_ratio"]),
            prompt=adapt_prompt,
            extra_context={
                "finished_ad": True,
                "phase5_format_adaptation": True,
                "phase5_architecture_lock_test": True,
                "revision_route": "CREATIVE_RECOMPOSE",
                "revision_visual_reference_asset_id": master_pack["asset_id"],
            },
        )
        members[str(target["aspect_ratio"])] = {
            "role": "architecture_locked_adaptation",
            "asset_id": pack["asset_id"],
            "asset_url": pack["asset_url"],
            "qa": pack["qa"],
            "retries": pack["retries"],
            "provider": pack["provider"],
            "provider_model": pack["provider_model"],
            "target_format": target["target_format"],
        }

    family_id = str(uuid4())
    record = {
        "family_id": family_id,
        "workflow": LOCKED_FAMILY_WORKFLOW,
        "policy": POLICY_NAME,
        "created_at": _now(),
        "test_session_id": test_session_id,
        "source_asset_id": str(interior_id),
        "source_filename": HERO_FILENAME,
        "logo_asset_id": str(logo_id),
        "architecture_lock_method": LOCK_METHOD,
        "members": members,
        "facts": facts,
        "video_started": False,
        "publishing_started": False,
        "existing_master_changed": False,
        "existing_format_family_changed": False,
        "policy_record": architecture_lock_policy(
            source_asset_id=str(interior_id),
            source_filename=HERO_FILENAME,
        ),
    }
    tests = list(blob.get("architecture_lock_tests") or [])
    tests.append(record)
    blob["architecture_lock_tests"] = tests
    blob["current_session_id"] = preserved_session
    blob["current_format_family_id"] = preserved_family
    blob["approved_masters"] = preserved_master_ids
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    _production_guard(before, after)
    if blob.get("current_session_id") != preserved_session:
        raise RuntimeError("Architecture lock test refused to change current_session_id")
    if blob.get("current_format_family_id") != preserved_family:
        raise RuntimeError("Architecture lock test refused to change current_format_family_id")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    return record


def _one_locked(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    session: dict[str, Any],
    *,
    interior_id: UUID,
    logo_id: UUID,
    language: str,
    format_preset: str,
    aspect_ratio: str,
    prompt: str,
    extra_context: dict[str, Any],
) -> dict[str, Any]:
    capability = provider_capability_record()
    route = route_ad_social_image(prefer_edit=True)
    builder_context = {
        "creative_director_campaign_id": str(row.id),
        "phase5_workflow": True,
        "skip_logo_edit_input": False,
        "production_mode": "finished_ad",
        "approved_financial_tokens": [REQUIRED_FACTS["list_price"], REQUIRED_FACTS["discount"], REQUIRED_FACTS["unit"]],
        "preferred_logo_asset_id": str(logo_id),
        "interior_project_asset_lock": True,
        "project_architecture_lock": True,
        "image_provider_route": route.to_dict(),
        "provider_capability": capability,
        **extra_context,
    }
    gpt_body = GptImageDesignRequest(
        linked_project_id=row.linked_project_id,
        instruction=prompt,
        design_provider="gpt-image",
        campaign_mode="project",
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        language=language,
        selected_asset_ids=[interior_id],
        builder_context=builder_context,
        session_id=session["session_id"],
    )
    logger.info("architecture-locked generate %s", aspect_ratio)
    result, output, pack, retries = _provider_generate_architecture_locked(
        db,
        user,
        gpt_body,
        row=row,
        session=session,
        interior_id=interior_id,
        prompt=prompt,
    )
    return {
        "asset_id": str(output.local_asset_id),
        "asset_url": output.local_asset_url or asset_url(output.local_asset_id),
        "qa": pack.get("qa"),
        "retries": retries,
        "status": pack.get("status"),
        "method": pack.get("method"),
        "provider": result.provider,
        "provider_model": result.model,
        "image": pack.get("image") or Image.open(io.BytesIO(_read_bytes(db, output.local_asset_id))).convert("RGB"),
    }
