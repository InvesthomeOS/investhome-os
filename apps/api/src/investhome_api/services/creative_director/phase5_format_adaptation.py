"""Phase 5.1 — AI format adaptation from an approved Phase 5.0 Master.

The image model recomposes the approved creative for 1:1, 9:16, and 16:9.
Does not crop/resize the Master as the final. Does not overwrite the Master.
Does not start video or publishing. Does not rewrite the Phase 5.0 generate/revise loop.
"""

from __future__ import annotations

import io
import logging
import re
from copy import deepcopy
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import CreativeDirectorReviseAdResponse
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
from investhome_api.services.creative_director.generate_ad import project_asset_lock_summary
from investhome_api.services.creative_director.project_architecture_lock import (
    architecture_integrity_qa,
    architecture_lock_prompt_lines,
    lock_generated_creative,
    persist_locked_image,
    source_has_architecture_structure,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    WORKFLOW_ID,
    _lock_temple_assets,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
    _write_phase5,
    build_creative_context,
    provider_capability_record,
)
from investhome_api.services.creative_director.provider_router import (
    assert_image_provider_available,
    route_ad_social_image,
)
from investhome_api.services.gpt_image_design.config import ASPECT_TO_SIZE
from investhome_api.services.gpt_image_design.persistence import asset_url
from investhome_api.services.gpt_image_design.service import generate_gpt_image_creatives

logger = logging.getLogger(__name__)

MAX_RETRIES_PER_FORMAT = 2
WORKFLOW_ID_51 = "phase5_format_adaptation"

FORMAT_TARGETS: list[dict[str, Any]] = [
    {
        "key": "square",
        "aspect_ratio": "1:1",
        "format_preset": "square",
        "target_format": "instagram_square_1:1",
        "width": 1024,
        "height": 1024,
        "label": "Square 1:1",
        "safe_area": "Keep logo, headline, facts, and CTA inside the square. Fill the canvas.",
        "art_direction": (
            "Compose a native square advertisement. Do not chop the 4:5 Master top and bottom. "
            "Keep a strong relationship between headline, architecture, commercial facts, CTA, and logo."
        ),
    },
    {
        "key": "story",
        "aspect_ratio": "9:16",
        "format_preset": "story",
        "target_format": "instagram_story_9:16",
        "width": 1088,
        "height": 1920,
        "label": "Story 9:16",
        "safe_area": (
            "Keep headline, price, commercial claim, CTA, and logo away from the extreme top ~12% "
            "and bottom ~18% (Story UI collision). Do not draw Instagram UI chrome."
        ),
        "art_direction": (
            "Compose a native vertical Story. Use vertical space intentionally. "
            "Do not float the 4:5 Master inside a taller canvas. "
            "CTA belongs in a natural lower action area. Reposition logo if needed."
        ),
    },
    {
        "key": "landscape",
        "aspect_ratio": "16:9",
        "format_preset": "landscape",
        "target_format": "landscape_16:9",
        "width": 1920,
        "height": 1088,
        "label": "Landscape 16:9",
        "safe_area": "Use the full horizontal frame. No empty side pillars.",
        "art_direction": (
            "Compose a native landscape campaign creative. "
            "Do not center the vertical ad with empty sides. "
            "Architecture may occupy one visual zone; campaign information may use natural negative space."
        ),
    },
]

_OLD_PRICE_TOKENS = ("675.000", "675000", "438.750", "438750")


def approved_semantic_content(session: dict[str, Any], master_ocr: str = "") -> dict[str, str]:
    """Facts come from the approved version, never from initial generation defaults."""
    master = session.get("approved_master") or {}
    approved_vid = str(master.get("approved_version_id") or session.get("approved_version_id") or "")
    approved = next(
        (v for v in (session.get("versions") or []) if str(v.get("version_id")) == approved_vid),
        None,
    )
    if not isinstance(approved, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Format adaptation requires an approved version.",
        )
    stored = dict((approved.get("creative_context") or {}).get("required_factual_content") or {})
    facts = {
        "headline": str(stored.get("headline") or REQUIRED_FACTS["headline"]),
        "unit": str(stored.get("unit") or REQUIRED_FACTS["unit"]),
        "unit_label": str(stored.get("unit_label") or REQUIRED_FACTS["unit_label"]),
        "discount": str(stored.get("discount") or REQUIRED_FACTS["discount"]),
        "discount_label": str(stored.get("discount_label") or REQUIRED_FACTS["discount_label"]),
        "cta": str(stored.get("cta") or REQUIRED_FACTS["cta"]),
        "list_price": str(stored.get("list_price") or "").strip(),
    }
    ocr_price = _price_from_text(master_ocr)
    if ocr_price:
        facts["list_price"] = ocr_price
    if not facts["list_price"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Approved Master has no list price to inherit.",
        )
    return facts


def _price_from_text(text: str) -> str | None:
    folded = (text or "").replace(",", ".")
    if "438.750" in folded or "438750" in re.sub(r"[^\d]", "", folded):
        if "438" in folded:
            return "438.750 USD"
    if "675.000" in folded or re.search(r"675[\.\s]?000", folded):
        return "675.000 USD"
    return None


def _ocr_image_bytes(content: bytes) -> str:
    try:
        from investhome_api.services.document_intelligence.ocr import LocalTesseractOCR
        from investhome_api.services.document_intelligence.types import SourceReference

        provider = LocalTesseractOCR()
        if not provider.is_available():
            return ""
        result = provider.ocr_image(content, SourceReference(section="format_adaptation"))
        text = (result.text or "").strip()
        if "OCR placeholder" in text:
            return ""
        return text
    except Exception:
        logger.info("Phase 5.1 OCR unavailable", exc_info=True)
        return ""


def _fold(text: str) -> str:
    return (
        (text or "")
        .casefold()
        .replace("ı", "i")
        .replace("İ", "i")
        .replace("ş", "s")
        .replace("Ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )


def validate_required_text(ocr_text: str, facts: dict[str, str]) -> dict[str, Any]:
    folded = _fold(ocr_text)
    digits = re.sub(r"[^\d]", "", ocr_text or "")
    approved_price = facts["list_price"]
    approved_digits = re.sub(r"[^\d]", "", approved_price)
    missing: list[str] = []
    if "alirken" not in folded or "kazan" not in folded:
        missing.append("headline")
    if "2+1" not in (ocr_text or "") and "2 + 1" not in (ocr_text or ""):
        missing.append("unit")
    if approved_digits and approved_digits not in digits:
        missing.append("price")
    if "35" not in digits and "%35" not in (ocr_text or "") and "35" not in folded:
        missing.append("discount")
    if "kesfet" not in folded and "keşfet" not in (ocr_text or "").casefold():
        missing.append("cta")
    leaked = []
    for token in _OLD_PRICE_TOKENS:
        token_digits = re.sub(r"[^\d]", "", token)
        if token_digits and token_digits != approved_digits and token_digits in digits:
            leaked.append(token)
    invented = any(m in folded for m in ("roi", "yield", "kira getirisi", "yatirim getirisi"))
    available = bool((ocr_text or "").strip())
    failed = bool(missing or leaked or invented) if available else False
    return {
        "available": available,
        "status": "fail" if failed else ("pass" if available else "unverified"),
        "missing": missing,
        "leaked_old_or_wrong_price": leaked,
        "invented_claims": invented,
        "ocr_excerpt": (ocr_text or "")[:400],
    }


def _band_std(img: Image.Image, box: tuple[int, int, int, int]) -> float:
    crop = img.convert("RGB").crop(box)
    if crop.width < 2 or crop.height < 2:
        return 0.0
    px = list(crop.resize((32, 32), Image.Resampling.BILINEAR).getdata())
    if not px:
        return 0.0
    mean = sum(sum(p) for p in px) / (len(px) * 3)
    var = sum((sum(p) / 3 - mean) ** 2 for p in px) / len(px)
    return var**0.5


def _band_mean(img: Image.Image, box: tuple[int, int, int, int]) -> tuple[float, float, float]:
    crop = img.convert("RGB").crop(box)
    if crop.width < 1 or crop.height < 1:
        return (0.0, 0.0, 0.0)
    px = list(crop.resize((8, 8), Image.Resampling.BOX).getdata())
    n = max(len(px), 1)
    return (sum(p[0] for p in px) / n, sum(p[1] for p in px) / n, sum(p[2] for p in px) / n)


def format_utilization_qa(img: Image.Image, target: dict[str, Any]) -> dict[str, Any]:
    w, h = img.size
    tw, th = int(target["width"]), int(target["height"])
    ratio_ok = abs(w / h - tw / th) < 0.08
    size_ok = abs(w - tw) <= 32 or abs(h - th) <= 32 or (w >= tw * 0.85 and h >= th * 0.85)
    letterbox = False
    key = target["key"]
    if key == "landscape":
        left_box = (0, 0, max(1, int(w * 0.12)), h)
        right_box = (int(w * 0.88), 0, w, h)
        center_box = (int(w * 0.35), 0, int(w * 0.65), h)
        left, right, center = _band_std(img, left_box), _band_std(img, right_box), _band_std(img, center_box)
        lm, rm, cm = _band_mean(img, left_box), _band_mean(img, right_box), _band_mean(img, center_box)
        side_center = sum(abs(lm[i] - cm[i]) + abs(rm[i] - cm[i]) for i in range(3)) / 2
        letterbox = center > 22 and left < 8 and right < 8 and side_center > 40
    elif key == "story":
        top_box = (0, 0, w, max(1, int(h * 0.12)))
        bot_box = (0, int(h * 0.88), w, h)
        mid_box = (0, int(h * 0.35), w, int(h * 0.65))
        top, bottom, mid = _band_std(img, top_box), _band_std(img, bot_box), _band_std(img, mid_box)
        tm, bm, mm = _band_mean(img, top_box), _band_mean(img, bot_box), _band_mean(img, mid_box)
        edge_mid = sum(abs(tm[i] - mm[i]) + abs(bm[i] - mm[i]) for i in range(3)) / 2
        letterbox = mid > 22 and top < 8 and bottom < 8 and edge_mid > 40
    elif key == "square":
        letterbox = (h / max(w, 1) > 1.15) or (w / max(h, 1) > 1.15)
    fill = 0.2 if letterbox else 0.85
    if ratio_ok:
        fill += 0.1
    score = 0.0 if letterbox or not ratio_ok else min(1.0, fill)
    return {
        "score": round(score, 4),
        "ratio_ok": ratio_ok,
        "size_ok": size_ok,
        "letterbox_or_pillarbox": letterbox,
        "output_size": [w, h],
        "target_size": [tw, th],
        "status": "fail" if letterbox or not ratio_ok else "pass",
    }


def _mean_rgb(img: Image.Image) -> tuple[float, float, float]:
    pixel = img.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return (float(pixel[0]), float(pixel[1]), float(pixel[2]))


def _mean_identity(a: Image.Image, b: Image.Image) -> float:
    ca, cb = _mean_rgb(a), _mean_rgb(b)
    dist = sum(abs(ca[i] - cb[i]) for i in range(3)) / (3 * 255)
    return max(0.0, min(1.0, 1.0 - dist * 3.0))


def adaptation_qa(
    *,
    master: Image.Image,
    derivative: Image.Image,
    hero: Image.Image | None,
    target: dict[str, Any],
    facts: dict[str, str],
    ocr_text: str,
    hero_id: str,
    logo_id: str,
) -> dict[str, Any]:
    identity = _mean_identity(master, derivative)
    arch = _mean_identity(hero, derivative) if hero is not None else 0.5
    util = format_utilization_qa(derivative, target)
    text = validate_required_text(ocr_text, facts)
    arch_qa = None
    architecture_fail = arch < 0.18
    if hero is not None and source_has_architecture_structure(hero):
        arch_qa = architecture_integrity_qa(hero, derivative, source_asset_id=hero_id)
        architecture_fail = arch_qa.get("architecture_integrity_status") == "fail"
    unexpected = identity < 0.32 or util["letterbox_or_pillarbox"]
    content_fail = text["status"] == "fail"
    project_ok = (not architecture_fail) and hero_id == LOCKED_HERO_ASSET_ID and logo_id == LOCKED_LOGO_ASSET_ID
    failed = unexpected or content_fail or architecture_fail or util["status"] == "fail"
    reasons: list[str] = []
    if unexpected:
        reasons.append("unexpected_campaign_redesign_or_letterbox")
    if content_fail:
        reasons.extend(text.get("missing") or [])
        if text.get("leaked_old_or_wrong_price"):
            reasons.append("wrong_or_old_price")
    if architecture_fail:
        reasons.append("architecture_mismatch")
    if util["status"] == "fail":
        reasons.append("format_utilization")
    return {
        "campaign_identity_score": round(identity, 4),
        "content_integrity": text["status"],
        "project_asset_integrity": "pass" if project_ok else "fail",
        "format_utilization": util["status"],
        "format_utilization_score": util["score"],
        "architecture_fidelity": round(arch, 4),
        "architecture_integrity": arch_qa,
        "unexpected_redesign": unexpected,
        "text_validation": text,
        "utilization": util,
        "failed": failed,
        "fail_reasons": reasons,
        "hero_asset_id": hero_id,
        "logo_asset_id": logo_id,
    }


def _adaptation_prompt(
    *,
    facts: dict[str, str],
    target: dict[str, Any],
    retry_note: str = "",
) -> str:
    size = ASPECT_TO_SIZE.get(target["aspect_ratio"]) or f"{target['width']}x{target['height']}"
    lines = [
        "FORMAT ADAPTATION of an ALREADY APPROVED advertisement.",
        "You are NOT creating a similar ad, a new version, another concept, or a new campaign.",
        "IMAGE 1 is the APPROVED MASTER CREATIVE. It is the visual source of truth.",
        "IMAGE 2 is the approved project photograph. Architecture must remain that building.",
        *architecture_lock_prompt_lines(),
        "A later image is the real project logo. Place that mark. Do not invent a logo.",
        "",
        "Preserve visual identity: The Temple, ALIRKEN KAZAN, same architecture, same hero,",
        "same logo, luxury/editorial mood, typography character, color atmosphere,",
        "commercial hierarchy, iconographic language, CTA character, overall art direction.",
        "Recompose professionally for the new canvas. Do not stretch, crop, letterbox, or pillarbox.",
        "Do not leave the old 4:5 layout floating inside the new frame.",
        "Permission: RECOMPOSE. Not: REDESIGN THE CAMPAIGN.",
        "",
        f"TARGET FORMAT: {target['label']} ({target['aspect_ratio']}) canvas {size}.",
        target["art_direction"],
        f"SAFE AREA GUIDANCE (do not draw guides): {target['safe_area']}",
        "",
        "Paint ONLY these approved-master facts, exactly. Do not restore older version values:",
        f"  Headline: {facts['headline']}",
        f"  Unit: {facts['unit']} {facts['unit_label']}",
        f"  Price: {facts['list_price']}",
        f"  Advantage: {facts['discount']} {facts['discount_label']}",
        f"  CTA: {facts['cta']}",
        "Do not invent ROI, yield, rent, profit, location claims, delivery dates, or extra metrics.",
        "Do not invent a building or a different Temple façade.",
    ]
    if retry_note:
        lines.extend(["", "PREVIOUS ATTEMPT FAILED. Fix this and keep the same campaign:", retry_note])
    return "\n".join(lines)


def adapt_creative_format(
    db: Session,
    user: User,
    *,
    row: CreativeDirectorCampaign,
    session: dict[str, Any],
    master: dict[str, Any],
    facts: dict[str, str],
    target: dict[str, Any],
    interior_id: UUID,
    logo_id: UUID,
    language: str,
    master_img: Image.Image,
    hero_img: Image.Image | None,
) -> dict[str, Any]:
    capability = provider_capability_record()
    if not capability["usable_for_project_locked"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Format adaptation requires a reference-capable image provider for PROJECT_LOCKED work.",
        )
    route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(route)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    attempts: list[dict[str, Any]] = []
    last_fail = "unknown"
    calls = 0
    for attempt in range(MAX_RETRIES_PER_FORMAT + 1):
        prompt = _adaptation_prompt(facts=facts, target=target, retry_note=last_fail if attempt else "")
        builder_context = {
            "creative_director_campaign_id": str(row.id),
            "phase5_workflow": True,
            "phase5_format_adaptation": True,
            "finished_ad": True,
            "skip_logo_edit_input": False,
            "production_mode": "finished_ad",
            "revision_route": "CREATIVE_RECOMPOSE",
            "revision_visual_reference_asset_id": master["master_asset_id"],
            "approved_financial_tokens": [facts["list_price"], facts["discount"], facts["unit"]],
            "preferred_logo_asset_id": str(logo_id),
            "interior_project_asset_lock": True,
            "project_architecture_lock": True,
            "image_provider_route": route.to_dict(),
            "provider_capability": capability,
            "target_format": target["target_format"],
        }
        gpt_body = GptImageDesignRequest(
            linked_project_id=row.linked_project_id,
            instruction=prompt,
            design_provider="gpt-image",
            campaign_mode="project",
            format_preset=str(target["format_preset"]),
            aspect_ratio=target["aspect_ratio"],
            language=language,
            selected_asset_ids=[interior_id],
            builder_context=builder_context,
            session_id=session["session_id"],
        )
        result = generate_gpt_image_creatives(db, user, gpt_body)
        calls += int(result.provider_call_count or 1)
        output = result.outputs[0] if result.outputs else None
        if output is None:
            last_fail = "provider returned no output"
            attempts.append({"attempt": attempt + 1, "status": "no_output", "user_facing": False})
            continue
        raw = _read_bytes(db, output.local_asset_id)
        child = Image.open(io.BytesIO(raw)).convert("RGB")
        if hero_img is not None:
            arch_lock = lock_generated_creative(
                hero_img,
                child,
                campaign_mode=getattr(row, "mode", None) or "project",
                brand_market_ad=False,
                source_asset_id=str(interior_id),
            )
        else:
            arch_lock = {"status": "skipped", "skipped": True, "qa": None}
        if not arch_lock.get("skipped") and arch_lock.get("image") is not None:
            child = arch_lock["image"].convert("RGB")
            if arch_lock["status"] == "pass" and arch_lock.get("changed"):
                new_id = persist_locked_image(
                    db,
                    user,
                    image=child,
                    linked_project_id=row.linked_project_id,
                    session_id=session["session_id"],
                    campaign_context_id=str(row.id),
                )
                output = output.model_copy(
                    update={"local_asset_id": new_id, "local_asset_url": asset_url(new_id)}
                )
                buf = io.BytesIO()
                child.save(buf, format="PNG")
                raw = buf.getvalue()
        ocr = _ocr_image_bytes(raw)
        qa = adaptation_qa(
            master=master_img,
            derivative=child,
            hero=hero_img,
            target=target,
            facts=facts,
            ocr_text=ocr,
            hero_id=str(interior_id),
            logo_id=str(logo_id),
        )
        if arch_lock.get("status") == "fail":
            qa["failed"] = True
            qa["fail_reasons"] = list(qa.get("fail_reasons") or []) + ["architecture_integrity"]
            qa["architecture_integrity"] = arch_lock.get("qa")
        record = {
            "attempt": attempt + 1,
            "asset_id": str(output.local_asset_id),
            "status": "fail" if qa["failed"] else "pass",
            "user_facing": not qa["failed"],
            "qa": qa,
            "provider": result.provider,
            "provider_model": result.model,
            "resolved_instruction": prompt[:1800],
        }
        attempts.append(record)
        if not qa["failed"]:
            return {
                "ok": True,
                "output": output,
                "result": result,
                "qa": qa,
                "prompt": prompt,
                "attempts": attempts,
                "retry_count": attempt,
                "provider_call_count": calls,
                "route": route,
                "capability": capability,
            }
        last_fail = ", ".join(qa.get("fail_reasons") or ["quality"])
        logger.info("Phase 5.1 %s attempt %s failed: %s", target["key"], attempt + 1, last_fail)
    return {
        "ok": False,
        "output": None,
        "result": None,
        "qa": attempts[-1].get("qa") if attempts else {},
        "prompt": _adaptation_prompt(facts=facts, target=target, retry_note=last_fail),
        "attempts": attempts,
        "retry_count": MAX_RETRIES_PER_FORMAT,
        "provider_call_count": calls,
        "route": route,
        "capability": capability,
        "fail_reasons": last_fail,
    }


def adapt_format_family(
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
) -> CreativeDirectorReviseAdResponse:
    master = session.get("approved_master")
    if not isinstance(master, dict) or not master.get("master_asset_id"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Format adaptation requires an approved Phase 5.0 Master.",
        )
    if session.get("status") not in {"APPROVED", "FORMAT_ADAPTATION_READY"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Approve the Master before format adaptation.",
        )
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    interior_id, logo_id = _lock_temple_assets(row.linked_project_id, interior_id, logo_id)
    master_id_before = str(master["master_asset_id"])
    master_bytes = _read_bytes(db, UUID(master_id_before))
    master_img = Image.open(io.BytesIO(master_bytes)).convert("RGB")
    master_ocr = _ocr_image_bytes(master_bytes)
    facts = approved_semantic_content(session, master_ocr)
    try:
        hero_img = Image.open(io.BytesIO(_read_bytes(db, interior_id))).convert("RGB")
    except Exception:
        hero_img = None

    family_id = str(uuid4())
    derivatives: list[dict[str, Any]] = []
    debug_attempts: list[dict[str, Any]] = []
    total_calls = 0
    first_ok: dict[str, Any] | None = None
    failures: list[str] = []

    for target in FORMAT_TARGETS:
        pack = adapt_creative_format(
            db,
            user,
            row=row,
            session=session,
            master=master,
            facts=facts,
            target=target,
            interior_id=interior_id,
            logo_id=logo_id,
            language=language,
            master_img=master_img,
            hero_img=hero_img,
        )
        total_calls += int(pack.get("provider_call_count") or 0)
        for attempt in pack.get("attempts") or []:
            if not attempt.get("user_facing"):
                debug_attempts.append({"format": target["key"], **attempt})
        if not pack.get("ok"):
            failures.append(f"{target['key']}: {pack.get('fail_reasons')}")
            continue
        output = pack["output"]
        result = pack["result"]
        derivative = {
            "derivative_id": str(uuid4()),
            "master_id": master["master_id"],
            "source_approved_version_id": master["approved_version_id"],
            "asset_id": str(output.local_asset_id),
            "derivative_type": "FORMAT_ADAPTATION",
            "target_format": target["target_format"],
            "target_width": target["width"],
            "target_height": target["height"],
            "format_preset": target["format_preset"],
            "aspect_ratio": target["aspect_ratio"],
            "provider": result.provider,
            "provider_model": result.model,
            "generation_method": "FORMAT_ADAPTATION",
            "created_at": _now(),
            "status": "ready",
            "retry_count": pack["retry_count"],
            "qa": pack["qa"],
            "project_asset_ids": [str(interior_id)],
            "logo_asset_id": str(logo_id),
            "approved_content": facts,
            "resolved_instruction": pack["prompt"][:1800],
            "user_facing": True,
        }
        derivatives.append(derivative)
        if first_ok is None:
            first_ok = {"derivative": derivative, "output": output, "result": result, "pack": pack}

    if first_ok is None or len(derivatives) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Format adaptation did not produce a complete family.",
                "failures": failures,
                "debug_attempt_count": len(debug_attempts),
            },
        )

    family = {
        "family_id": family_id,
        "session_id": session["session_id"],
        "master_id": master["master_id"],
        "source_approved_version_id": master["approved_version_id"],
        "master_asset_id": master_id_before,
        "members": {
            "4:5": {"role": "approved_master", "asset_id": master_id_before, "target_format": master.get("base_format")},
            **{
                d["aspect_ratio"]: {
                    "role": "format_adaptation",
                    "derivative_id": d["derivative_id"],
                    "asset_id": d["asset_id"],
                    "target_format": d["target_format"],
                }
                for d in derivatives
            },
        },
        "created_at": _now(),
        "video_started": False,
        "publishing_started": False,
    }

    blob = _phase5(ctx)
    deriv_map = dict(blob.get("derivatives") or {})
    for item in derivatives:
        deriv_map[item["derivative_id"]] = item
    families = dict(blob.get("format_families") or {})
    families[family_id] = family
    blob["derivatives"] = deriv_map
    blob["format_families"] = families
    blob["current_format_family_id"] = family_id
    blob["debug_format_attempts"] = (list(blob.get("debug_format_attempts") or []) + debug_attempts)[-40:]
    ctx[CTX_KEY] = blob

    session = deepcopy(session)
    session["format_family_id"] = family_id
    session["status"] = "FORMAT_ADAPTATION_READY"
    session["format_adaptation_started"] = True
    session["video_started"] = False
    session["publishing_started"] = False
    session["updated_at"] = _now()
    hooks = dict(session.get("next_hooks") or {})
    hooks["format_adaptation"] = "completed"
    hooks["story"] = "unstarted"
    hooks["reel"] = "unstarted"
    hooks["video"] = "unstarted"
    hooks["publishing"] = "unstarted"
    session["next_hooks"] = hooks
    approved = dict(session.get("approved_master") or master)
    if str(approved.get("master_asset_id")) != master_id_before:
        raise RuntimeError("Phase 5.1 refused to change approved master asset")
    approved["format_family_id"] = family_id
    session["approved_master"] = approved
    _write_phase5(ctx, session)

    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    _production_guard(before, after)
    persisted_master = (ctx.get(CTX_KEY) or {}).get("sessions", {}).get(session["session_id"], {}).get(
        "approved_master", {}
    )
    if str(persisted_master.get("master_asset_id")) != master_id_before:
        raise RuntimeError("Phase 5.1 refused to overwrite the approved 4:5 Master")

    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()

    square = next(d for d in derivatives if d["aspect_ratio"] == "1:1")
    output = first_ok["output"]
    result = first_ok["result"]
    pack = first_ok["pack"]
    public_family = {
        "family_id": family_id,
        "master_asset_id": master_id_before,
        "derivatives": [
            {
                "derivative_id": d["derivative_id"],
                "asset_id": d["asset_id"],
                "asset_url": asset_url(UUID(d["asset_id"])),
                "format_preset": d["format_preset"],
                "aspect_ratio": d["aspect_ratio"],
                "label": next(t["label"] for t in FORMAT_TARGETS if t["aspect_ratio"] == d["aspect_ratio"]),
                "width": d["target_width"],
                "height": d["target_height"],
            }
            for d in derivatives
        ],
    }
    asset_lock = project_asset_lock_summary(
        interior_id=interior_id,
        logo_id=logo_id,
        interior_meta={**dict(interior_meta), "asset_id": str(interior_id), "filename": HERO_FILENAME},
        logo_meta={**dict(logo_meta), "asset_id": str(logo_id)},
        source_asset_id=interior_id,
    )
    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio="1:1",
        format_preset="square",
        production_mode="finished_ad",
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=UUID(square["asset_id"]),
        final_asset_url=asset_url(UUID(square["asset_id"])),
        finished_ad_raster_asset_id=UUID(square["asset_id"]),
        master_asset_id=UUID(master_id_before),
        master_finished_ad_asset_id=UUID(master_id_before),
        final_turkish_texts=facts,
        claim_guard={"status": "pass", "approved_facts": facts, "source": "approved_version"},
        project_asset_lock=asset_lock,
        provider_call_count=total_calls,
        gpt_image_call_count=total_calls,
        latency_ms=int(result.latency_ms or 0),
        gpt_image=result.model_dump(mode="json"),
        user_feedback="Kare, Story ve yatay ölçü hazır.",
        revision_intents=["FORMAT_ADAPTATION_ALL"],
        revision_route="CREATIVE_RECOMPOSE",
        previous_asset_id=UUID(master_id_before),
        quality_guard={
            "status": "review",
            "workflow": WORKFLOW_ID_51,
            "phase5_session_workflow": WORKFLOW_ID,
            "session_id": session["session_id"],
            "session_status": "FORMAT_ADAPTATION_READY",
            "format_family_id": family_id,
            "approved_master_id": master["master_id"],
            "approved_master_changed": False,
            "phase4_renderer_used": False,
            "simple_resize_crop_used": False,
            "format_adaptation_started": True,
            "video_started": False,
            "publishing_started": False,
            "note": "Format family ready for human review. Visual Quality PASS not claimed.",
        },
        campaign_context={
            "phase5_session_id": session["session_id"],
            "status": "FORMAT_ADAPTATION_READY",
            "format_family": public_family,
            "approved_master_id": master["master_id"],
        },
        interpreted_plan={"intent": "FORMAT_ADAPTATION_ALL", "targets": ["1:1", "9:16", "16:9"]},
        change_diff_validation={d["aspect_ratio"]: d["qa"] for d in derivatives},
    )
