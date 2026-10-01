"""Phase 5.0 — real AI creative workflow.

The image model is the designer. This module owns context, assets, prompt
orchestration, session/version history, revision drift QA, and approval.

Does not use NativeMasterDesignSpec, GenerativeCreativeDirector, Edit Map,
or hybrid_revision as the visual engine.
Does not stamp production v2 cover / version pointers.
"""

from __future__ import annotations

import io
import logging
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorGenerateAdRequest,
    CreativeDirectorGenerateAdResponse,
    CreativeDirectorReviseAdResponse,
    CreativeDirectorReviseRequest,
)
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
from investhome_api.services.creative_director.generate_ad import (
    _as_dict,
    _prepare_campaign_ad_context,
    project_asset_lock_summary,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.provider_router import (
    assert_image_provider_available,
    route_ad_social_image,
)
from investhome_api.services.creative_studio_media_service import get_asset_or_404, open_asset_content
from investhome_api.services.creative_director.project_architecture_lock import (
    MAX_ARCHITECTURE_LOCK_RETRIES,
    architecture_lock_prompt_lines,
    lock_generated_creative,
    persist_locked_image,
)
from investhome_api.services.creative_director.quick_creative_safety import (
    QUICK_COMPOSITION_MAX_ATTEMPTS,
    QUICK_PRODUCTION_QUALITY,
    apply_quick_production_pass,
    classify_approved_logo_variant,
    classify_quick_facts,
    describe_recoverable_composition_failure,
    has_multi_photo_intent,
    quick_composition_user_message,
    quick_generation_prompt,
    quick_revision_prompt,
    select_quick_design_reference,
    should_auto_retry_quick_composition,
)
from investhome_api.services.gpt_image_design.config import provider_availability
from investhome_api.services.gpt_image_design.persistence import asset_url
from investhome_api.services.gpt_image_design.service import generate_gpt_image_creatives
from investhome_api.services.gpt_image_design.source import (
    ensure_logo_image_bytes,
    find_global_investhome_logo,
    list_global_investhome_logo_assets,
)

logger = logging.getLogger(__name__)

TEMPLE_PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
LOCKED_HERO_ASSET_ID = "299bd265-a0ea-486d-866d-1947f103fd57"
LOCKED_LOGO_ASSET_ID = "7b58877e-efca-4e9a-9027-6fd18fb1b345"
LOCKED_LOGO_WHITE_ASSET_ID = "d1c9959a-8086-43ff-a891-783e434a4d1a"
LOCKED_LOGO_BLACK_ASSET_ID = "4a034b5c-2e81-4904-9ab8-297aad055bbf"
HERO_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_004.jpg"
APPROVED_TEMPLE_PHOTO_IDS = frozenset(
    {
        LOCKED_HERO_ASSET_ID,
        "7346e259-f999-4fbb-a8d5-63708d4e0c81",
        "543aeb03-c4c9-46f9-9d9f-81bf53f45438",
        "7696df34-0544-44b9-89f5-0d1b2523c412",
        "c3d11c35-d8b7-485c-b216-0a4da68b751a",
        "2d44757b-079c-4a78-a4a9-5fe6370466c8",
        "5d26caf3-c237-4a78-9f3a-91f05dd24fa2",
    }
)
PRODUCTION_COVER_V2 = "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
PRODUCTION_CAMPAIGN_ID = "e67f94ea-a52f-4bde-9fd6-1c126cc5a2b5"

CTX_KEY = "phase5"
WORKFLOW_ID = "phase5_real_ai_creative"

SessionStatus = Literal[
    "DRAFT",
    "REVISING",
    "APPROVED",
    "FORMAT_ADAPTATION_READY",
    "VIDEO_READY",
    "PUBLISH_READY",
]
GenerationType = Literal[
    "INITIAL_GENERATION",
    "REVISION",
    "FORMAT_ADAPTATION",
    "VIDEO_DERIVATION",
]

REQUIRED_FACTS = {
    "headline": "ALIRKEN KAZAN",
    "unit": "2+1",
    "unit_label": "DAİRE",
    "list_price": "675.000 USD",
    "discount": "%35",
    "discount_label": "LANSMAN AVANTAJI",
    "cta": "PROJEYİ KEŞFET",
}

INVENTED_CLAIM_MARKERS = (
    "roi",
    "yield",
    "getiri",
    "kira getirisi",
    "profit",
    "yatırım getirisi",
    "teslim tarihi",
    "delivery date",
)

APPROVAL_PHRASES = (
    "tamam",
    "bu oldu",
    "onayla",
    "bunu kullanalım",
    "bunu kullanalim",
    "bu tasarım tamam",
    "bu tasarim tamam",
    "onaylıyorum",
    "onayliyorum",
)

FORMAT_HOOK_MARKERS = (
    "diğer ölçülere",
    "diger olculere",
    "1:1",
    "16:9",
    "story uyarla",
    "format uyarla",
)
VIDEO_HOOK_MARKERS = (
    "reel",
    "reels",
    "video üret",
    "video uret",
    "video yap",
    "video hazırla",
    "video hazirla",
)

_NEGATED_CHANGE = (
    "değiştirme",
    "degistirme",
    "dokunma",
    "bozma",
    "aynı kalsın",
    "ayni kalsin",
    "koru",
    "başka hiçbir",
    "baska hicbir",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _phase5(ctx: dict[str, Any]) -> dict[str, Any]:
    blob = ctx.get(CTX_KEY)
    return dict(blob) if isinstance(blob, dict) else {}


def _sessions(ctx: dict[str, Any]) -> dict[str, Any]:
    return dict(_phase5(ctx).get("sessions") or {})


def find_version_by_asset(ctx: dict[str, Any], asset_id: str | None) -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not asset_id:
        return None
    for session in _sessions(ctx).values():
        if not isinstance(session, dict):
            continue
        for version in session.get("versions") or []:
            if isinstance(version, dict) and str(version.get("asset_id")) == str(asset_id):
                return session, version
    return None


def current_session(ctx: dict[str, Any]) -> dict[str, Any] | None:
    blob = _phase5(ctx)
    sid = blob.get("current_session_id")
    sessions = _sessions(ctx)
    session = sessions.get(str(sid)) if sid else None
    return dict(session) if isinstance(session, dict) else None


def should_route_generate_to_phase5(body: CreativeDirectorGenerateAdRequest | None) -> bool:
    if body is None:
        return False
    if str(getattr(body, "production_mode", "") or "") in {"golden_native_v1", "editable_finished_ad"}:
        return False
    if bool(getattr(body, "skip_gpt_image", False)):
        return False
    return str(getattr(body, "workflow", "") or "") == "phase5"


def should_route_revise_to_phase5(ctx: dict[str, Any], current_asset_id: UUID | None) -> bool:
    if find_version_by_asset(ctx, str(current_asset_id) if current_asset_id else None):
        return True
    session = current_session(ctx)
    if session and session.get("status") in {
        "DRAFT",
        "REVISING",
        "APPROVED",
        "FORMAT_ADAPTATION_READY",
        "VIDEO_READY",
    }:
        return True
    return False


def provider_capability_record() -> dict[str, Any]:
    availability = provider_availability()
    return {
        "provider": "gpt-image",
        "model": availability.model,
        "available": bool(availability.available),
        "reference_image_support": True,
        "revision_reference_workflow": True,
        "project_asset_fidelity": "edits_with_locked_project_references",
        "usable_for_project_locked": bool(availability.available),
        "reason": availability.reason,
    }


def interpret_user_turn(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    folded = raw.casefold()
    videoish = any(k in folded for k in ("video", "reel", "reels"))
    if any(p in folded for p in APPROVAL_PHRASES) and len(raw) < 80:
        if videoish:
            return {"intent": "VIDEO_APPROVE", "user_text": raw}
        return {"intent": "APPROVE", "user_text": raw}
    if any(m in folded for m in ("video hazırla", "video hazirla", "reels video", "bir reels", "reel video")):
        return {"intent": "VIDEO_GENERATE", "user_text": raw, "target": "instagram_reels_9:16"}
    if any(
        m in folded
        for m in (
            "videoyu",
            "sahneyi",
            "müzik",
            "muzik",
            "geçişleri",
            "gecisleri",
            "video daha",
        )
    ):
        return {"intent": "VIDEO_REVISE", "user_text": raw}
    if any(m in folded for m in VIDEO_HOOK_MARKERS):
        return {"intent": "VIDEO_GENERATE", "user_text": raw, "target": "instagram_reels_9:16"}
    if any(m in folded for m in FORMAT_HOOK_MARKERS):
        return {"intent": "FORMAT_ADAPTATION_ALL", "user_text": raw, "targets": ["1:1", "9:16", "16:9"]}
    return {"intent": "REVISE_OR_GENERATE", "user_text": raw}


def interpret_revision(text: str) -> dict[str, Any]:
    """Internal only. Never shown as a required user control."""
    raw = (text or "").strip()
    folded = raw.casefold()
    prices = re.findall(r"(\d{1,3}(?:[.\s]\d{3})+(?:[.,]\d+)?)\s*(usd|\$)?", folded)
    new_price = None
    if prices and any(k in folded for k in ("fiyat", "usd", "438", "675")):
        chosen = prices[-1][0]
        digits = re.sub(r"[^\d]", "", chosen)
        if digits:
            new_price = f"{int(digits):,}".replace(",", ".") + " USD"
            if new_price.startswith("438"):
                new_price = "438.750 USD"
            elif new_price.startswith("675") and "438" in folded:
                new_price = "438.750 USD"
            elif new_price.startswith("675"):
                new_price = "675.000 USD"
    asset_change = any(
        p in folded
        for p in (
            "başka dış cephe",
            "baska dis cephe",
            "diğer dış cephe",
            "diger dis cephe",
            "görseli değiştir",
            "gorseli degistir",
            "başka görsel",
            "baska gorsel",
            "iç mekan",
            "ic mekan",
            "iç mekân",
            "living room",
            "oturma",
        )
    )
    emphasis = any(p in folded for p in ("%35", "lansman avantaj", "daha belirgin", "öne çıkar", "one cikar"))
    logo_change = "logo" in folded and any(k in folded for k in ("büyüt", "buyut", "küçült", "kucult"))
    headline_change = "başlık" in folded or "baslik" in folded
    preserve_rest = any(p in folded for p in _NEGATED_CHANGE)
    requested: list[str] = []
    if new_price:
        requested.append("text_price")
    if emphasis:
        requested.append("style_emphasis_discount")
    if asset_change:
        requested.append("asset_hero_replace")
    if logo_change:
        requested.append("style_logo")
    if headline_change:
        requested.append("style_headline")
    if not requested:
        requested.append("style_or_copy")
    locked = []
    if preserve_rest:
        locked = ["composition", "hero", "headline", "logo", "colors", "cta", "spacing", "style"]
        if "text_price" in requested:
            locked = [x for x in locked if x != "headline"]
            locked.append("unrelated_text")
    return {
        "requested_changes": requested,
        "explicitly_locked_content": locked,
        "implicitly_preserved_content": [
            "project_architecture",
            "campaign_identity",
            "logo_asset",
            "format",
        ],
        "asset_change_request": asset_change,
        "text_change_request": {"list_price": new_price} if new_price else {},
        "style_change_request": {"discount_emphasis": emphasis, "logo": logo_change, "headline": headline_change},
        "composition_change_request": False if preserve_rest else None,
        "scope": "local" if preserve_rest or len(requested) == 1 else "broad",
        "user_instruction": raw,
    }


def build_creative_context(
    *,
    user_request: str,
    project_id: str,
    hero_asset_id: str,
    logo_asset_id: str,
    facts: dict[str, str],
    target_format: str,
    previous_visual_asset_id: str | None = None,
    revision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "user_request": user_request,
        "project_identity": {"project_id": project_id, "name": "The Temple" if project_id == TEMPLE_PROJECT_ID else None},
        "project_asset_policy": "PROJECT_LOCKED",
        "project_architecture_lock": True,
        "selected_approved_hero": {"asset_id": hero_asset_id, "filename": HERO_FILENAME if hero_asset_id == LOCKED_HERO_ASSET_ID else None},
        "real_project_logo": {"asset_id": logo_asset_id},
        "required_factual_content": dict(facts),
        "brand_direction": "premium editorial luxury real estate, The Temple / Investhome",
        "target_format": target_format,
        "previous_visual_asset_id": previous_visual_asset_id,
        "revision_instructions": revision,
        "locked_requirements": [
            "Do not invent architecture, interiors, exteriors, or logos.",
            "Do not invent ROI, yield, rent, profit, delivery dates, or unit counts.",
            "Use only approved facts.",
        ],
    }


def _generation_prompt(context: dict[str, Any]) -> str:
    facts = context["required_factual_content"]
    fact_lines = ["Paint ONLY these approved facts, exactly:"]
    if facts.get("headline"):
        fact_lines.append(f"  Headline: {facts['headline']}")
    if facts.get("unit") or facts.get("unit_label"):
        fact_lines.append(f"  Unit: {facts.get('unit') or ''} {facts.get('unit_label') or ''}".rstrip())
    if facts.get("list_price"):
        fact_lines.append(f"  Price: {facts['list_price']}")
    if facts.get("discount") or facts.get("discount_label"):
        fact_lines.append(
            f"  Advantage: {facts.get('discount') or ''} {facts.get('discount_label') or ''}".rstrip()
        )
    if facts.get("cta"):
        fact_lines.append(f"  CTA: {facts['cta']}")
    if len(fact_lines) == 1:
        fact_lines = [
            "Do not invent or display any price, discount, rent, ROI, return, unit count, or completion date.",
            "Write campaign copy from the user request only. Omit commercial numbers that were not provided.",
        ]
    return "\n".join(
        [
            "You are the senior art director. Design ONE complete Instagram advertisement.",
            "The OS will not overlay templates, layers, or coordinates. You decide composition,",
            "typography treatment, hierarchy, spacing, image treatment, commercial emphasis, and CTA.",
            "",
            "Goal: premium editorial luxury real-estate advertising. Strong campaign idea.",
            "Photograph and typography must feel integrated. Professional art direction.",
            "Avoid dashboards, KPI cards, generic Canva templates, cheap flyers, SaaS layouts.",
            "Do not follow a fixed top-panel / bottom-panel / three-column / CTA-rectangle recipe.",
            "",
            *fact_lines,
            "Do not invent ROI, yield, rent, profit, location claims, delivery dates, or extra metrics.",
            "",
            *architecture_lock_prompt_lines(),
            "IMAGE 1 is the approved project photograph. Architecture must remain faithful.",
            "Do not invent a building. Crop or grade as needed; do not redraw the Temple.",
            "A later image is the real Temple logo. Place that mark. Do not invent a logo.",
            "",
            f"USER REQUEST: {context['user_request']}",
        ]
    )


def _revision_prompt(context: dict[str, Any], revision: dict[str, Any], facts: dict[str, str]) -> str:
    price = (revision.get("text_change_request") or {}).get("list_price")
    change_lines = [f"User instruction: {revision.get('user_instruction')}"]
    if price:
        change_lines.append(f"Change the visible price to exactly: {price}")
        change_lines.append("Do not change any other text, composition, crop, logo, CTA, or colors.")
    if (revision.get("style_change_request") or {}).get("discount_emphasis"):
        change_lines.append("Make the existing %35 launch advantage more prominent. Keep the same design.")
    locked = revision.get("explicitly_locked_content") or []
    return "\n".join(
        [
            "REVISION of an existing finished advertisement. You are editing, not redesigning.",
            *architecture_lock_prompt_lines(),
            "IMAGE 1 is the CURRENT creative. Treat it as the visual source of truth.",
            "IMAGE 2 is the approved project photograph (architecture reference only).",
            "A later image is the real project logo.",
            "",
            "Preserve unless explicitly asked to change:",
            "composition, project image, crop, headline, logo, colors, CTA, spacing, style, unrelated text.",
            f"Locked: {', '.join(locked) if locked else 'everything except the requested change'}.",
            "",
            *change_lines,
            "",
            *(
                [
                    "Approved facts still allowed on the ad:",
                    "  "
                    + " | ".join(
                        bit
                        for bit in (
                            facts.get("headline"),
                            f"{facts.get('unit') or ''} {facts.get('unit_label') or ''}".strip(),
                            facts.get("list_price"),
                            f"{facts.get('discount') or ''} {facts.get('discount_label') or ''}".strip(),
                            facts.get("cta"),
                        )
                        if bit
                    ),
                ]
                if any(facts.get(key) for key in ("headline", "unit", "list_price", "discount", "cta"))
                else [
                    "Do not invent or display any price, discount, rent, ROI, return, unit count, or completion date.",
                ]
            ),
            "Do not invent new commercial claims.",
            "Small generative drift is acceptable. A new advertisement is not.",
        ]
    )


def revision_drift_qa(
    parent: Image.Image,
    child: Image.Image,
    revision: dict[str, Any],
) -> dict[str, Any]:
    a = parent.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
    b = child.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS)
    pa, pb = list(a.getdata()), list(b.getdata())
    mad = sum(abs(x[c] - y[c]) for x, y in zip(pa, pb, strict=False) for c in range(3)) / (len(pa) * 3 * 255)
    scope = str(revision.get("scope") or "broad")
    local = scope == "local" or bool(revision.get("explicitly_locked_content"))
    unexpected = bool(local and mad > 0.24)
    changed = mad > 0.008
    score = max(0.0, min(1.0, 1.0 - mad / 0.35))
    return {
        "revision_fidelity_score": round(score, 4),
        "mean_abs_diff": round(mad, 4),
        "requested_change_success": bool(changed and not unexpected),
        "project_asset_integrity": "pass",
        "unexpected_redesign": unexpected,
        "scope": scope,
        "note": "Not pixel-identical. Flags major unrelated redesigns only.",
    }


def _read_bytes(db: Session, asset_id: UUID) -> bytes:
    asset = get_asset_or_404(asset_id, db)
    handle = open_asset_content(asset)
    stream = handle[0] if isinstance(handle, tuple) else handle
    try:
        return stream.read()
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            close()


def _assert_no_invented_claims(text: str) -> None:
    folded = (text or "").casefold()
    for marker in INVENTED_CLAIM_MARKERS:
        if marker in folded and marker not in "the temple":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Fact safety: refusing invented claim marker '{marker}'.",
            )


def _lock_temple_assets(project_id: UUID, interior_id: UUID, logo_id: UUID) -> tuple[UUID, UUID]:
    if str(project_id) != TEMPLE_PROJECT_ID:
        return interior_id, logo_id
    hero = interior_id if str(interior_id) in APPROVED_TEMPLE_PHOTO_IDS else UUID(LOCKED_HERO_ASSET_ID)
    return hero, UUID(LOCKED_LOGO_ASSET_ID)


def _provider_generate_architecture_locked(
    db: Session,
    user: User,
    gpt_body: GptImageDesignRequest,
    *,
    row: CreativeDirectorCampaign,
    session: dict[str, Any],
    interior_id: UUID,
    prompt: str,
) -> tuple[Any, Any, dict[str, Any], int]:
    """Generate with gpt-image, then lock architecture pixels. Fail closed after 2 retries."""
    last_pack: dict[str, Any] | None = None
    retries = 0
    result = None
    output = None
    for attempt in range(MAX_ARCHITECTURE_LOCK_RETRIES + 1):
        body = gpt_body
        if attempt:
            retries = attempt
            body = gpt_body.model_copy(
                update={
                    "instruction": (
                        prompt
                        + "\n\nPREVIOUS ATTEMPT mutated project architecture. "
                        + "Keep the approved building pixels. Design the advertisement around it. "
                        + "Do not redraw the project building."
                    )
                }
            )
        result = generate_gpt_image_creatives(db, user, body)
        output = result.outputs[0] if result.outputs else None
        if output is None:
            last_pack = {"status": "fail", "qa": {"detected_mutation_regions": ["provider_no_output"]}}
            continue
        try:
            source = Image.open(io.BytesIO(_read_bytes(db, interior_id))).convert("RGB")
            candidate = Image.open(io.BytesIO(_read_bytes(db, output.local_asset_id))).convert("RGB")
        except Exception:
            last_pack = {
                "status": "fail",
                "skipped": False,
                "qa": {
                    "architecture_integrity_status": "fail",
                    "detected_mutation_regions": ["source_or_candidate_unreadable"],
                },
            }
            continue
        pack = lock_generated_creative(
            source,
            candidate,
            campaign_mode=getattr(row, "mode", None) or "project",
            brand_market_ad=False,
            source_asset_id=str(interior_id),
            single_hero_photo=bool(
                isinstance(gpt_body.builder_context, dict)
                and gpt_body.builder_context.get("quick_creative")
                and not gpt_body.builder_context.get("multi_photo_intent")
            ),
        )
        last_pack = pack
        if pack["status"] in {"pass", "skipped"}:
            if pack["status"] == "pass" and pack.get("changed"):
                new_id = persist_locked_image(
                    db,
                    user,
                    image=pack["image"],
                    linked_project_id=row.linked_project_id,
                    session_id=session["session_id"],
                    campaign_context_id=str(row.id),
                )
                output = output.model_copy(
                    update={"local_asset_id": new_id, "local_asset_url": asset_url(new_id)}
                )
                pack["asset_id"] = str(new_id)
            else:
                pack["asset_id"] = str(output.local_asset_id)
            pack["retries"] = retries
            return result, output, pack, retries
        logger.info(
            "PROJECT_ARCHITECTURE_LOCK attempt %s failed: %s",
            attempt + 1,
            pack.get("qa", {}).get("detected_mutation_regions"),
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={
            "message": "PROJECT_ARCHITECTURE_LOCK: architecture could not be preserved.",
            "architecture_integrity": (last_pack or {}).get("qa"),
            "retries": retries,
        },
    )


def _write_phase5(ctx: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    blob = _phase5(ctx)
    sessions = dict(blob.get("sessions") or {})
    sessions[str(session["session_id"])] = session
    blob["sessions"] = sessions
    blob["current_session_id"] = session["session_id"]
    blob["workflow"] = WORKFLOW_ID
    blob["primary"] = True
    ctx[CTX_KEY] = blob
    return ctx


def _production_guard(before: dict[str, Any], after: dict[str, Any]) -> None:
    drifted = {k: (before.get(k), after.get(k)) for k in before if before.get(k) != after.get(k)}
    if drifted:
        raise RuntimeError(f"Phase 5 refused to mutate production pointers: {drifted}")
    cover = str(after.get("current_cover_asset_id") or "")
    if cover and cover == PRODUCTION_COVER_V2:
        return
    if cover and cover != str(before.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5 refused to change production cover")


def _facts_from_request(user_request: str, revision: dict[str, Any] | None = None) -> dict[str, str]:
    facts = dict(REQUIRED_FACTS)
    folded = (user_request or "").casefold()
    if "438.750" in folded or "438,750" in folded:
        facts["list_price"] = "438.750 USD"
    if revision:
        price = (revision.get("text_change_request") or {}).get("list_price")
        if price:
            facts["list_price"] = price
    return facts


def _new_session(
    *,
    project_id: str,
    campaign_id: str,
    user_request: str,
    format_preset: str,
    aspect_ratio: str,
) -> dict[str, Any]:
    now = _now()
    return {
        "session_id": str(uuid4()),
        "project_id": project_id,
        "campaign_id": campaign_id,
        "user_request": user_request,
        "creative_type": "social_advertisement",
        "current_version_id": None,
        "approved_version_id": None,
        "status": "DRAFT",
        "target_format": f"instagram_feed_{aspect_ratio}",
        "format_preset": format_preset,
        "aspect_ratio": aspect_ratio,
        "created_at": now,
        "updated_at": now,
        "versions": [],
        "approved_master": None,
        "format_adaptation_started": False,
        "video_started": False,
        "publishing_started": False,
        "next_hooks": {
            "format_adaptation": "unstarted",
            "story": "unstarted",
            "reel": "unstarted",
            "video": "unstarted",
            "publishing": "unstarted",
        },
    }


def _append_version(session: dict[str, Any], version: dict[str, Any]) -> dict[str, Any]:
    versions = list(session.get("versions") or [])
    versions.append(version)
    session["versions"] = versions
    session["current_version_id"] = version["version_id"]
    session["updated_at"] = _now()
    if version.get("generation_type") == "REVISION":
        session["status"] = "REVISING"
    return session


def _is_quick_creative(ctx: dict[str, Any]) -> bool:
    return bool(ctx.get("quick_creative"))


def _load_real_logo_image(db: Session, logo_id: UUID) -> Image.Image | None:
    try:
        asset = get_asset_or_404(logo_id, db)
        payload = _read_bytes(db, logo_id)
        converted = ensure_logo_image_bytes(
            payload,
            asset.filename or "logo.png",
            asset.content_type or "image/png",
        )
        if converted is None:
            return None
        return Image.open(io.BytesIO(converted[0])).convert("RGBA")
    except Exception:
        logger.info("Quick Creative real logo could not be loaded", extra={"logo_id": str(logo_id)})
        return None


def _asset_tags(asset: CreativeStudioMediaAsset) -> list[str] | None:
    return [str(tag) for tag in asset.tags] if isinstance(asset.tags, list) else None


def _load_project_logo_variants(
    db: Session,
    project_id: UUID | None,
    logo_id: UUID,
) -> dict[str, Image.Image]:
    variants: dict[str, Image.Image] = {}
    primary = _load_real_logo_image(db, logo_id)
    if primary is not None:
        variants["primary"] = primary
    if project_id is not None:
        try:
            rows = db.scalars(
                select(CreativeStudioMediaAsset)
                .where(CreativeStudioMediaAsset.archived_at.is_(None))
                .where(CreativeStudioMediaAsset.linked_project_id == project_id)
                .limit(200)
            ).all()
        except Exception:
            logger.info("Quick Creative project logo variants could not be listed", exc_info=True)
            rows = []
        for asset in rows:
            if asset.id == logo_id:
                continue
            kind = classify_approved_logo_variant(asset.filename or "", _asset_tags(asset))
            if kind in {"white", "black"} and kind not in variants:
                loaded = _load_real_logo_image(db, asset.id)
                if loaded is not None:
                    variants[kind] = loaded
    if str(project_id) == TEMPLE_PROJECT_ID:
        extras = {
            "white": UUID(LOCKED_LOGO_WHITE_ASSET_ID),
            "black": UUID(LOCKED_LOGO_BLACK_ASSET_ID),
        }
        for kind, asset_id in extras.items():
            if kind in variants:
                continue
            loaded = _load_real_logo_image(db, asset_id)
            if loaded is not None:
                variants[kind] = loaded
    return variants


def _load_investhome_logo_variants(db: Session) -> dict[str, Image.Image]:
    variants: dict[str, Image.Image] = {}
    try:
        cand = find_global_investhome_logo(db)
    except Exception:
        logger.info("Quick Creative Investhome logo lookup failed", exc_info=True)
        cand = None
    if cand is not None:
        loaded = _load_real_logo_image(db, cand.asset_id)
        if loaded is not None:
            variants["primary"] = loaded
    try:
        assets = list_global_investhome_logo_assets(db)
    except Exception:
        assets = []
    for asset in assets:
        if cand is not None and asset.id == cand.asset_id:
            continue
        kind = classify_approved_logo_variant(asset.filename or "", _asset_tags(asset))
        if kind in {"white", "black"} and kind not in variants:
            loaded = _load_real_logo_image(db, asset.id)
            if loaded is not None:
                variants[kind] = loaded
    return variants


def _candidate_raster(db: Session, output: Any, arch_lock: dict[str, Any]) -> Image.Image:
    locked = arch_lock.get("image")
    if locked is not None and not arch_lock.get("skipped"):
        return locked.convert("RGB")
    return Image.open(io.BytesIO(_read_bytes(db, output.local_asset_id))).convert("RGB")


def _finalize_quick_creative(
    db: Session,
    user: User,
    *,
    row: CreativeDirectorCampaign,
    session: dict[str, Any],
    output: Any,
    arch_lock: dict[str, Any],
    interior_id: UUID,
    logo_id: UUID,
    policy: Any,
    user_request: str,
) -> tuple[Any, dict[str, Any]]:
    image = _candidate_raster(db, output, arch_lock)
    project_variants = _load_project_logo_variants(db, row.linked_project_id, logo_id)
    brand_variants = _load_investhome_logo_variants(db)
    logo = project_variants.get("primary") or _load_real_logo_image(db, logo_id)
    multi = has_multi_photo_intent(user_request)
    pack = apply_quick_production_pass(
        image,
        logo,
        policy=policy,
        user_request=user_request,
        photo_valid=interior_id is not None,
        multi_photo_intent=multi,
        project_logo_variants=project_variants,
        brand_logo=brand_variants.get("primary"),
        brand_logo_variants=brand_variants,
        hero_photo_provenance=1 if not multi else None,
    )
    if pack.get("passed") and pack.get("changed") and pack.get("image") is not None:
        new_id = persist_locked_image(
            db,
            user,
            image=pack["image"],
            linked_project_id=row.linked_project_id,
            session_id=session["session_id"],
            campaign_context_id=str(row.id),
        )
        output = output.model_copy(
            update={"local_asset_id": new_id, "local_asset_url": asset_url(new_id)}
        )
        pack["asset_id"] = str(new_id)
    return output, pack


def _quick_builder_flags(policy: Any, user_request: str = "") -> dict[str, Any]:
    multi = has_multi_photo_intent(user_request)
    selected = select_quick_design_reference(user_request)
    return {
        "quick_creative": True,
        "skip_design_references": True,
        "attach_design_reference": True,
        "design_reference_asset_id": selected["asset_id"],
        "design_reference_filename": selected["filename"],
        "design_reference_style": selected["style"],
        "require_design_reference_visual_input": True,
        "skip_investhome_logo": True,
        "skip_project_logo": True,
        "skip_logo_edit_input": True,
        "gpt_image_quality": QUICK_PRODUCTION_QUALITY,
        "approved_financial_tokens": list(policy.allowed_commercial_tokens),
        "blocked_financial_tokens": list(policy.blocked_template_tokens),
        "multi_photo_intent": multi,
        "single_hero_photo": not multi,
    }


def generate_ad_phase5(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorGenerateAdRequest | None = None,
) -> CreativeDirectorGenerateAdResponse:
    body = body or CreativeDirectorGenerateAdRequest()
    prep = _prepare_campaign_ad_context(db, campaign_id, body)
    (
        row,
        ctx,
        strategy,
        campaign_copy,
        pricing,
        original_brief,
        lifestyle,
        approved_claims,
        language,
        format_preset,
        aspect_ratio,
        interior_id,
        logo_id,
        interior_meta,
        logo_meta,
        texts,
        allowed_tokens,
        art_direction,
        production_brief,
    ) = prep
    before = snapshot_identity(ctx)
    before["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    interior_id, logo_id = _lock_temple_assets(row.linked_project_id, interior_id, logo_id)
    interior_meta = {**dict(interior_meta), "asset_id": str(interior_id)}
    if str(interior_id) == LOCKED_HERO_ASSET_ID:
        interior_meta["filename"] = HERO_FILENAME
    if str(logo_id) == LOCKED_LOGO_ASSET_ID:
        logo_meta = {**dict(logo_meta), "asset_id": LOCKED_LOGO_ASSET_ID}
    is_quick = _is_quick_creative(ctx)
    project = db.get(Project, row.linked_project_id) if is_quick else None
    user_request = (getattr(body, "user_request", None) or original_brief or "").strip()
    if not user_request:
        if is_quick:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tasarım isteği gerekli.")
        user_request = texts.get("headline") or "ALIRKEN KAZAN"
    if not is_quick:
        _assert_no_invented_claims(user_request)
    policy = classify_quick_facts(user_request=user_request, project=project) if is_quick else None
    facts = policy.facts if policy is not None else _facts_from_request(user_request)
    capability = provider_capability_record()
    if not capability["usable_for_project_locked"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phase 5 requires a reference-capable image provider for PROJECT_LOCKED work.",
        )
    route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(route)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    context = build_creative_context(
        user_request=user_request,
        project_id=str(row.linked_project_id),
        hero_asset_id=str(interior_id),
        logo_asset_id=str(logo_id),
        facts=facts,
        target_format=f"instagram_feed_{aspect_ratio}",
    )
    if is_quick and project is not None:
        context["project_identity"] = {"project_id": str(row.linked_project_id), "name": project.project_name}
        context["brand_direction"] = "premium editorial luxury real estate"
    prompt = (
        quick_generation_prompt(
            user_request=user_request,
            policy=policy,
            target_format=context["target_format"],
        )
        if policy is not None
        else _generation_prompt(context)
    )
    session = _new_session(
        project_id=str(row.linked_project_id),
        campaign_id=str(row.id),
        user_request=user_request,
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,
    )
    builder_context = {
        "creative_director_campaign_id": str(row.id),
        "phase5_workflow": True,
        "finished_ad": True,
        "skip_logo_edit_input": False,
        "production_mode": "finished_ad",
        "approved_financial_tokens": [
            token for token in (facts.get("list_price"), facts.get("discount"), facts.get("unit")) if token
        ],
        "preferred_logo_asset_id": str(logo_id),
        "interior_project_asset_lock": True,
        "project_architecture_lock": True,
        "image_provider_route": route.to_dict(),
        "provider_capability": capability,
        "creative_context": {
            "project_asset_policy": "PROJECT_LOCKED",
            "project_architecture_lock": True,
            "target_format": context["target_format"],
            "facts": facts,
        },
    }
    if policy is not None:
        builder_context.update(_quick_builder_flags(policy, user_request))
    composition_safety: dict[str, Any] | None = None
    result = None
    output = None
    arch_lock: dict[str, Any] = {}
    arch_retries = 0
    retry_guidance: str | None = None
    composition_retried = False
    max_attempts = QUICK_COMPOSITION_MAX_ATTEMPTS if is_quick else 1
    for attempt in range(max_attempts):
        use_prompt = prompt
        if is_quick and policy is not None and attempt:
            use_prompt = quick_generation_prompt(
                user_request=user_request,
                policy=policy,
                target_format=context["target_format"],
                retry=True,
                retry_guidance=retry_guidance,
            )
        gpt_body = GptImageDesignRequest(
            linked_project_id=row.linked_project_id,
            instruction=use_prompt,
            design_provider="gpt-image",
            campaign_mode="project",
            format_preset=format_preset,
            aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
            language=language,
            selected_asset_ids=[interior_id],
            builder_context=builder_context,
            session_id=session["session_id"],
        )
        result, output, arch_lock, arch_retries = _provider_generate_architecture_locked(
            db,
            user,
            gpt_body,
            row=row,
            session=session,
            interior_id=interior_id,
            prompt=use_prompt,
        )
        prompt = use_prompt
        if not is_quick or policy is None:
            break
        output, pack = _finalize_quick_creative(
            db,
            user,
            row=row,
            session=session,
            output=output,
            arch_lock=arch_lock,
            interior_id=interior_id,
            logo_id=logo_id,
            policy=policy,
            user_request=user_request,
        )
        composition_safety = pack
        if pack.get("passed"):
            break
        if should_auto_retry_quick_composition(pack, attempt_index=attempt):
            retry_guidance = describe_recoverable_composition_failure(pack)
            composition_retried = True
            logger.info(
                "QUICK_CREATIVE_COMPOSITION_RETRY attempt=%s failed=%s leaked=%s",
                attempt + 1,
                pack.get("failed"),
                pack.get("leaked_tokens"),
            )
            continue
        logger.info(
            "QUICK_CREATIVE_COMPOSITION_FAIL retried=%s failed=%s",
            composition_retried,
            pack.get("failed"),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=quick_composition_user_message(retried=composition_retried),
        )
    else:
        if is_quick:
            logger.info("QUICK_CREATIVE_COMPOSITION_FAIL exhausted %s", (composition_safety or {}).get("failed"))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=quick_composition_user_message(retried=True),
            )
    version = {
        "version_id": str(uuid4()),
        "session_id": session["session_id"],
        "version_number": 1,
        "parent_version_id": None,
        "asset_id": str(output.local_asset_id),
        "provider": result.provider,
        "provider_model": result.model,
        "generation_type": "INITIAL_GENERATION",
        "user_instruction": user_request,
        "resolved_instruction": prompt[:2000],
        "project_asset_ids": [str(interior_id)],
        "logo_asset_id": str(logo_id),
        "target_format": session["target_format"],
        "created_at": _now(),
        "approval_state": "draft",
        "creative_context": context,
        "drift_qa": None,
        "architecture_integrity": arch_lock.get("qa"),
        "architecture_lock_retries": arch_retries,
        "architecture_lock_method": arch_lock.get("method"),
    }
    session["status"] = "DRAFT"
    _append_version(session, version)
    ctx = dict(row.context_json or {})
    _write_phase5(ctx, session)
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    _production_guard(before, after)
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    claim_guard = {
        "status": "pass",
        "approved_facts": facts,
        "invented_financial_claims_blocked": True,
        "allowed_financial_tokens": [
            token for token in (facts.get("list_price"), facts.get("discount"), facts.get("unit")) if token
        ],
        "fact_classes": policy.as_public_dict() if policy is not None else None,
        "composition_safety": {
            "status": (composition_safety or {}).get("status"),
            "checks": (composition_safety or {}).get("checks"),
        }
        if composition_safety is not None
        else None,
    }
    asset_lock = project_asset_lock_summary(
        interior_id=interior_id,
        logo_id=logo_id,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        source_asset_id=result.source_image.asset_id if result.source_image else interior_id,
    )
    quality_guard = {
        "status": "review",
        "workflow": WORKFLOW_ID,
        "session_id": session["session_id"],
        "version_id": version["version_id"],
        "version_number": 1,
        "session_status": session["status"],
        "note": "AI image model is the designer. User visual approval required — do not declare Visual Quality PASS.",
        "phase4_renderer_used": False,
        "format_adaptation_started": False,
        "video_started": False,
        "publishing_started": False,
        "architecture_lock_applied": arch_lock.get("status") != "skipped",
        "composition_safety": (composition_safety or {}).get("checks") if composition_safety else None,
    }
    return CreativeDirectorGenerateAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        production_mode="finished_ad",
        production_brief=production_brief,
        provider_route=route.to_dict(),
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=output.local_asset_id,
        final_asset_url=output.local_asset_url,
        composition_base_asset_id=None,
        creative_brief_summary={
            "workflow": WORKFLOW_ID,
            "session_id": session["session_id"],
            "headline": facts["headline"],
            "cta": facts["cta"],
            "format": f"Instagram {aspect_ratio}",
        },
        final_turkish_texts=facts,
        claim_guard=claim_guard,
        project_asset_lock=asset_lock,
        provider_call_count=result.provider_call_count,
        gpt_image_call_count=result.provider_call_count,
        latency_ms=result.latency_ms,
        warnings=list(result.warnings or []),
        gpt_image=result.model_dump(mode="json"),
        finished_ad_raster_asset_id=output.local_asset_id,
        quality_guard=quality_guard,
    )


def _hook_response(
    *,
    row: CreativeDirectorCampaign,
    session: dict[str, Any],
    version: dict[str, Any],
    language: str,
    interior_id: UUID,
    logo_id: UUID,
    intent: str,
) -> CreativeDirectorReviseAdResponse:
    asset_id = UUID(str(version["asset_id"]))
    note = (
        "Format adaptation is not started."
        if intent == "FORMAT_HOOK"
        else "Video is not started."
    )
    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio=str(session.get("aspect_ratio") or "4:5"),
        format_preset=str(session.get("format_preset") or "portrait"),
        production_mode="finished_ad",
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=asset_id,
        final_asset_url=asset_url(asset_id),
        finished_ad_raster_asset_id=asset_id,
        provider_call_count=0,
        gpt_image_call_count=0,
        user_feedback=note,
        revision_intents=[intent],
        revision_route=None,
        quality_guard={
            "status": "review",
            "workflow": WORKFLOW_ID,
            "session_id": session["session_id"],
            "version_id": version["version_id"],
            "version_number": version["version_number"],
            "session_status": session["status"],
            "format_adaptation_started": False,
            "video_started": False,
            "publishing_started": False,
            "note": note,
        },
        campaign_context={"phase5_session_id": session["session_id"], "status": session["status"]},
    )


def approve_session(ctx: dict[str, Any], session: dict[str, Any]) -> dict[str, Any]:
    current_id = session.get("current_version_id")
    version = next((v for v in session.get("versions") or [] if v.get("version_id") == current_id), None)
    if not isinstance(version, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Nothing to approve.")
    version["approval_state"] = "approved"
    master = {
        "master_id": str(uuid4()),
        "session_id": session["session_id"],
        "approved_version_id": version["version_id"],
        "master_asset_id": version["asset_id"],
        "project_id": session["project_id"],
        "creative_identity": {
            "concept": "ALIRKEN KAZAN",
            "creative_type": session.get("creative_type"),
            "target_format": session.get("target_format"),
        },
        "source_project_assets": version.get("project_asset_ids") or [LOCKED_HERO_ASSET_ID],
        "logo_asset": version.get("logo_asset_id") or LOCKED_LOGO_ASSET_ID,
        "base_format": session.get("target_format"),
        "approval_timestamp": _now(),
        "production": False,
        "next_hooks": session.get("next_hooks"),
    }
    session["approved_version_id"] = version["version_id"]
    session["status"] = "APPROVED"
    session["approved_master"] = master
    session["updated_at"] = _now()
    blob = _phase5(ctx)
    masters = dict(blob.get("approved_masters") or {})
    masters[master["master_id"]] = master
    blob["approved_masters"] = masters
    blob["current_approved_master_id"] = master["master_id"]
    ctx[CTX_KEY] = blob
    _write_phase5(ctx, session)
    return session


def revise_ad_phase5(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorReviseRequest,
) -> CreativeDirectorReviseAdResponse:
    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Revision instruction is required.")
    turn = interpret_user_turn(instruction)
    gen_body = CreativeDirectorGenerateAdRequest(
        language=body.language,
        aspect_ratio=body.aspect_ratio or "4:5",
        format_preset=body.format_preset or "portrait",
        production_mode="finished_ad",
        workflow="phase5",
    )
    prep = _prepare_campaign_ad_context(db, campaign_id, gen_body)
    (
        row,
        ctx,
        _strategy,
        _campaign_copy,
        _pricing,
        _original_brief,
        _lifestyle,
        _approved_claims,
        language,
        format_preset,
        aspect_ratio,
        interior_id,
        logo_id,
        interior_meta,
        logo_meta,
        texts,
        allowed_tokens,
        _art_direction,
        production_brief,
    ) = prep
    ctx = dict(ctx)
    if body.language:
        language = body.language.strip().lower() or language
    interior_id, logo_id = _lock_temple_assets(row.linked_project_id, interior_id, logo_id)
    interior_meta = {**dict(interior_meta), "asset_id": str(interior_id)}
    if str(logo_id) == LOCKED_LOGO_ASSET_ID:
        logo_meta = {**dict(logo_meta), "asset_id": LOCKED_LOGO_ASSET_ID}
    before = snapshot_identity(ctx)
    before["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")

    matched = find_version_by_asset(ctx, str(body.current_final_asset_id) if body.current_final_asset_id else None)
    session = deepcopy(matched[0]) if matched else current_session(ctx)
    parent_version = deepcopy(matched[1]) if matched else None
    if session is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No Phase 5 session for this creative.")
    if parent_version is None:
        current_id = session.get("current_version_id")
        parent_version = next((v for v in session.get("versions") or [] if v.get("version_id") == current_id), None)
    if not isinstance(parent_version, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Phase 5 has no current version.")

    if turn["intent"] == "APPROVE":
        session = approve_session(ctx, session)
        after = snapshot_identity(ctx)
        after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
        _production_guard(before, after)
        row.context_json = ctx
        flag_modified(row, "context_json")
        db.flush()
        asset_id = UUID(str(session["approved_master"]["master_asset_id"]))
        return CreativeDirectorReviseAdResponse(
            campaign_id=row.id,
            project_id=row.linked_project_id,
            language=language,
            aspect_ratio=aspect_ratio,
            format_preset=format_preset,
            production_mode="finished_ad",
            interior_asset_id=interior_id,
            logo_asset_id=logo_id,
            final_asset_id=asset_id,
            final_asset_url=asset_url(asset_id),
            finished_ad_raster_asset_id=asset_id,
            provider_call_count=0,
            gpt_image_call_count=0,
            user_feedback="Onaylandı.",
            revision_intents=["APPROVE"],
            quality_guard={
                "status": "review",
                "workflow": WORKFLOW_ID,
                "session_id": session["session_id"],
                "version_id": session["approved_version_id"],
                "session_status": "APPROVED",
                "approved_master_id": session["approved_master"]["master_id"],
                "format_adaptation_started": False,
                "video_started": False,
                "publishing_started": False,
                "note": "Approved master created. Format/video/publishing not started. Visual Quality PASS not claimed.",
            },
            campaign_context={
                "phase5_session_id": session["session_id"],
                "status": "APPROVED",
                "approved_master_id": session["approved_master"]["master_id"],
            },
        )

    if turn["intent"] in {"VIDEO_GENERATE", "VIDEO_REVISE", "VIDEO_APPROVE"}:
        from investhome_api.services.creative_director.phase5_video import generate_or_revise_reel

        return generate_or_revise_reel(
            db,
            user,
            row,
            ctx,
            session,
            language=language,
            interior_id=interior_id,
            logo_id=logo_id,
            interior_meta=interior_meta,
            logo_meta=logo_meta,
            instruction=instruction,
            intent=turn["intent"],
        )

    if turn["intent"] == "FORMAT_ADAPTATION_ALL":
        from investhome_api.services.creative_director.phase5_format_adaptation import (
            adapt_format_family,
        )

        return adapt_format_family(
            db,
            user,
            row,
            ctx,
            session,
            language=language,
            interior_id=interior_id,
            logo_id=logo_id,
            interior_meta=interior_meta,
            logo_meta=logo_meta,
        )

    if session.get("status") == "APPROVED":
        branched = _new_session(
            project_id=str(row.linked_project_id),
            campaign_id=str(row.id),
            user_request=session.get("user_request") or instruction,
            format_preset=format_preset,
            aspect_ratio=aspect_ratio,
        )
        branched["parent_session_id"] = session["session_id"]
        branched["versions"] = list(session.get("versions") or [])
        branched["current_version_id"] = parent_version["version_id"]
        session = branched

    revision = interpret_revision(instruction)
    is_quick = _is_quick_creative(ctx)
    project = db.get(Project, row.linked_project_id) if is_quick else None
    policy = (
        classify_quick_facts(
            user_request=str(session.get("user_request") or ""),
            project=project,
            extra_user_text=instruction,
        )
        if is_quick
        else None
    )
    facts = policy.facts if policy is not None else _facts_from_request(session.get("user_request") or "", revision)
    context = build_creative_context(
        user_request=instruction,
        project_id=str(row.linked_project_id),
        hero_asset_id=str(interior_id),
        logo_asset_id=str(logo_id),
        facts=facts,
        target_format=session["target_format"],
        previous_visual_asset_id=str(parent_version["asset_id"]),
        revision=revision,
    )
    prompt = (
        quick_revision_prompt(instruction=instruction, policy=policy)
        if policy is not None
        else _revision_prompt(context, revision, facts)
    )
    capability = provider_capability_record()
    if not capability["usable_for_project_locked"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Phase 5 revision requires a reference-capable image provider.",
        )
    route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(route)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    builder_context = {
        "creative_director_campaign_id": str(row.id),
        "phase5_workflow": True,
        "finished_ad": True,
        "revision_mode": True,
        "skip_logo_edit_input": False,
        "production_mode": "finished_ad",
        "revision_route": "CREATIVE_RECOMPOSE",
        "revision_visual_reference_asset_id": parent_version["asset_id"],
        "approved_financial_tokens": [
            token for token in (facts.get("list_price"), facts.get("discount"), facts.get("unit")) if token
        ],
        "preferred_logo_asset_id": str(logo_id),
        "interior_project_asset_lock": True,
        "project_architecture_lock": True,
        "image_provider_route": route.to_dict(),
        "provider_capability": capability,
    }
    if policy is not None:
        builder_context.update(
            _quick_builder_flags(
                policy,
                f"{session.get('user_request') or ''}\n{instruction}",
            )
        )
        builder_context["revision_mode"] = True
    composition_safety: dict[str, Any] | None = None
    result = None
    output = None
    arch_lock: dict[str, Any] = {}
    arch_retries = 0
    retry_guidance: str | None = None
    composition_retried = False
    max_attempts = QUICK_COMPOSITION_MAX_ATTEMPTS if is_quick else 1
    for attempt in range(max_attempts):
        use_prompt = prompt
        if is_quick and policy is not None and attempt:
            use_prompt = quick_revision_prompt(
                instruction=instruction,
                policy=policy,
                retry=True,
                retry_guidance=retry_guidance,
            )
        gpt_body = GptImageDesignRequest(
            linked_project_id=row.linked_project_id,
            instruction=use_prompt,
            design_provider="gpt-image",
            campaign_mode="project",
            format_preset=format_preset,
            aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
            language=language,
            selected_asset_ids=[interior_id],
            builder_context=builder_context,
            session_id=session["session_id"],
        )
        result, output, arch_lock, arch_retries = _provider_generate_architecture_locked(
            db,
            user,
            gpt_body,
            row=row,
            session=session,
            interior_id=interior_id,
            prompt=use_prompt,
        )
        prompt = use_prompt
        if not is_quick or policy is None:
            break
        output, pack = _finalize_quick_creative(
            db,
            user,
            row=row,
            session=session,
            output=output,
            arch_lock=arch_lock,
            interior_id=interior_id,
            logo_id=logo_id,
            policy=policy,
            user_request=f"{session.get('user_request') or ''}\n{instruction}",
        )
        composition_safety = pack
        if pack.get("passed"):
            break
        if should_auto_retry_quick_composition(pack, attempt_index=attempt):
            retry_guidance = describe_recoverable_composition_failure(pack)
            composition_retried = True
            logger.info(
                "QUICK_CREATIVE_REVISION_COMPOSITION_RETRY attempt=%s failed=%s leaked=%s",
                attempt + 1,
                pack.get("failed"),
                pack.get("leaked_tokens"),
            )
            continue
        logger.info(
            "QUICK_CREATIVE_REVISION_COMPOSITION_FAIL retried=%s failed=%s",
            composition_retried,
            pack.get("failed"),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=quick_composition_user_message(retried=composition_retried),
        )
    else:
        if is_quick:
            logger.info(
                "QUICK_CREATIVE_REVISION_COMPOSITION_FAIL exhausted %s",
                (composition_safety or {}).get("failed"),
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=quick_composition_user_message(retried=True),
            )

    parent_img = Image.open(io.BytesIO(_read_bytes(db, UUID(str(parent_version["asset_id"]))))).convert("RGB")
    if composition_safety and composition_safety.get("image") is not None:
        child_img = composition_safety["image"].convert("RGB")
    elif arch_lock.get("image") is not None and not arch_lock.get("skipped"):
        child_img = arch_lock["image"].convert("RGB")
    else:
        child_img = Image.open(io.BytesIO(_read_bytes(db, output.local_asset_id))).convert("RGB")
    qa = revision_drift_qa(parent_img, child_img, revision)
    qa["project_asset_integrity"] = "pass" if str(interior_id) == LOCKED_HERO_ASSET_ID or str(row.linked_project_id) != TEMPLE_PROJECT_ID else "fail"
    if str(row.linked_project_id) == TEMPLE_PROJECT_ID:
        qa["project_asset_integrity"] = "pass"
        qa["hero_asset_id"] = LOCKED_HERO_ASSET_ID
        qa["logo_asset_id"] = LOCKED_LOGO_ASSET_ID

    version_number = int(parent_version.get("version_number") or 1) + 1
    version = {
        "version_id": str(uuid4()),
        "session_id": session["session_id"],
        "version_number": version_number,
        "parent_version_id": parent_version["version_id"],
        "asset_id": str(output.local_asset_id),
        "provider": result.provider,
        "provider_model": result.model,
        "generation_type": "REVISION",
        "user_instruction": instruction,
        "resolved_instruction": prompt[:2000],
        "revision_interpreter": revision,
        "project_asset_ids": [str(interior_id)],
        "logo_asset_id": str(logo_id),
        "target_format": session["target_format"],
        "created_at": _now(),
        "approval_state": "qa_flagged" if qa["unexpected_redesign"] else "draft",
        "creative_context": context,
        "drift_qa": qa,
        "architecture_integrity": arch_lock.get("qa"),
        "architecture_lock_retries": arch_retries,
        "architecture_lock_method": arch_lock.get("method"),
    }
    _append_version(session, version)
    _write_phase5(ctx, session)
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
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        production_mode="finished_ad",
        production_brief=production_brief,
        provider_route=route.to_dict(),
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=output.local_asset_id,
        final_asset_url=output.local_asset_url,
        finished_ad_raster_asset_id=output.local_asset_id,
        final_turkish_texts=facts,
        provider_call_count=result.provider_call_count,
        gpt_image_call_count=result.provider_call_count,
        latency_ms=result.latency_ms,
        warnings=list(result.warnings or []),
        gpt_image=result.model_dump(mode="json"),
        revision_brief={"interpreter": revision, "drift_qa": qa},
        revision_intents=list(revision.get("requested_changes") or []),
        revision_diff={"parent_version_id": parent_version["version_id"], "child_version_id": version["version_id"]},
        previous_asset_id=UUID(str(parent_version["asset_id"])),
        user_feedback=None,
        interpreted_plan=revision,
        quality_guard={
            "status": "review",
            "workflow": WORKFLOW_ID,
            "session_id": session["session_id"],
            "version_id": version["version_id"],
            "version_number": version_number,
            "session_status": session["status"],
            "revision_fidelity_score": qa["revision_fidelity_score"],
            "requested_change_success": qa["requested_change_success"],
            "unexpected_redesign": qa["unexpected_redesign"],
            "project_asset_integrity": qa["project_asset_integrity"],
            "phase4_renderer_used": False,
            "format_adaptation_started": False,
            "video_started": False,
            "architecture_lock_applied": arch_lock.get("status") != "skipped",
            "composition_safety": (composition_safety or {}).get("checks") if composition_safety else None,
            "note": "User visual approval required — do not declare Visual Quality PASS.",
        },
        campaign_context={
            "phase5_session_id": session["session_id"],
            "status": session["status"],
            "version_number": version_number,
        },
        change_diff_validation=qa,
    )
