"""Live Creative Studio — Premium Campaigns surface.

PRODUCTION LOCK (Phase 13.0 FINAL): UI HUMAN_APPROVED, workflow PRODUCTION_READY, routing ACTIVE.
Wires HUMAN_APPROVED Creative Families into the product UI.
Does not generate new Premium formats. Does not call GPT Image / Ideogram.
Does not overwrite immutable format masters.
Rejected Story adaptation engines are not on this route.
"""

from __future__ import annotations

import io
import re
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
    FAMILY_WIDE_REVISION,
    FORMAT_ADAPTATION,
    PRICE_EDIT_ONLY,
    VISUAL_REPLACE_ONLY,
    classify_production_intent,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    PRODUCTION_CAMPAIGN_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase10_0_master import attach_derived_revision
from investhome_api.services.creative_director.phase10_3_finalize import approve_child_revision
from investhome_api.services.creative_director.phase12_3_family_ingest import FAMILY_ID as UNILOFT_FAMILY_ID
from investhome_api.services.creative_director.phase12_5_price_revise import (
    apply_feed_price_revision,
    apply_square_price_revision,
    apply_story_price_revision,
)
from investhome_api.services.creative_director.phase12_6_copy_revise import (
    OLD_COPY,
    apply_feed_copy_revision,
    apply_square_copy_revision,
    apply_story_copy_revision,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    SKIP_FORMAT_MASTER_MISSING,
    SKIP_TARGET_NOT_PRESENT,
    SQUARE,
    STORY_REEL,
    REVISE_INDEPENDENTLY,
    families_in,
    family_wide_user_confirmation,
    format_copy_phrase_present,
    format_semantic_present,
    lookup_format_master,
    resolve_family,
    route_family_wide_revision,
    route_format_request,
)
from investhome_api.services.creative_studio_media_service import get_asset_or_404, open_asset_content
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

MSG_TARGET_NOT_PRESENT = "Bu bilgi seçili tasarımda bulunmuyor."
MSG_FORMAT_MASTER_MISSING = "Bu kampanyanın bu formatta onaylı tasarımı bulunmuyor."
MSG_REVISION_FAIL = "Değişiklik uygulanamadı. Tasarım korunarak işlem durduruldu."

DISPLAY_FORMATS = (FEED_PORTRAIT, STORY_REEL, SQUARE)
FORMAT_LABELS = {
    FEED_PORTRAIT: "Gönderi 4:5",
    STORY_REEL: "Story 9:16",
    SQUARE: "Kare 1:1",
    LANDSCAPE: "16:9",
}
USER_FORMAT_MISSING = {
    LANDSCAPE: "Bu kampanyanın onaylı 16:9 tasarımı henüz bulunmuyor.",
}

Scope = Literal["selected", "campaign"]

_PRICE_375 = re.compile(r"\b375(?:[.,]000)?\b")


def _fold_copy(text: str) -> str:
    table = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s"})
    return (text or "").translate(table).casefold()


def format_missing_message(fmt: str) -> str:
    return USER_FORMAT_MISSING.get(fmt) or MSG_FORMAT_MASTER_MISSING


def is_proven_price_command(instruction: str) -> bool:
    compact = (instruction or "").replace(" ", "").replace(",", ".")
    return "375.000" in compact or "375000" in compact or bool(_PRICE_375.search(instruction or ""))


def is_proven_copy_command(instruction: str) -> bool:
    folded = _fold_copy(instruction)
    return "son daireler" in folded and "son firsatlar" in folded


def _campaign_row(db: Session) -> CreativeDirectorCampaign:
    row = db.get(CreativeDirectorCampaign, UUID(PRODUCTION_CAMPAIGN_ID))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Premium campaigns are not available.")
    return row


def _library(row: CreativeDirectorCampaign) -> dict[str, Any]:
    blob = _phase5(dict(row.context_json or {}))
    library = blob.get("project_creative_master_library")
    return dict(library) if isinstance(library, dict) else {}


def _save_library(row: CreativeDirectorCampaign, library: dict[str, Any]) -> None:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    blob = _phase5(original)
    blob["project_creative_master_library"] = library
    original[CTX_KEY] = blob
    _production_guard(before, snapshot_identity(original))
    row.context_json = original
    flag_modified(row, "context_json")


def _live_families(library: dict[str, Any]) -> list[dict[str, Any]]:
    found = []
    for family in families_in(library):
        inventory = family.get("inventory") or {}
        approved = str(family.get("approval_status") or "") == "HUMAN_APPROVED"
        has_master = any(str(value) == "HUMAN_APPROVED" for value in inventory.values())
        if approved or has_master:
            found.append(family)
    found.sort(key=lambda item: 0 if str(item.get("FAMILY_ID")) == UNILOFT_FAMILY_ID else 1)
    return found


def _available_formats(family: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for fmt in DISPLAY_FORMATS:
        looked = lookup_format_master(family, fmt)
        if looked.get("status") == "HUMAN_APPROVED":
            out.append(fmt)
    return out


def _preview_asset(family: dict[str, Any], fmt: str) -> str | None:
    session = (family.get("studio_preview") or {}).get(fmt) or {}
    current = session.get("visual_asset")
    if current:
        return str(current)
    looked = lookup_format_master(family, fmt)
    master = looked.get("master") or {}
    asset = master.get("SOURCE_ASSET_ID")
    return str(asset) if asset else None


def _parent_asset(family: dict[str, Any], fmt: str) -> str | None:
    looked = lookup_format_master(family, fmt)
    master = looked.get("master") or {}
    asset = master.get("SOURCE_ASSET_ID")
    return str(asset) if asset else None


def _offer_line(family: dict[str, Any]) -> str | None:
    identity = family.get("identity") or {}
    copy = identity.get("CAMPAIGN_COPY") or {}
    offer = str(copy.get("offer") or "")
    if "son daireler" in _fold_copy(offer) or "son daireler" in _fold_copy(str(family.get("campaign_name") or "")):
        return "Son Daireler"
    if offer:
        return offer.split("/")[-1].strip()
    return None


def _title(family: dict[str, Any]) -> str:
    identity = family.get("identity") or {}
    name = str(identity.get("PROJECT_IDENTITY") or family.get("campaign_name") or "Kampanya")
    if " — " in name:
        return name.split(" — ", 1)[0]
    return name


def _card_preview(family: dict[str, Any]) -> str | None:
    for fmt in DISPLAY_FORMATS:
        asset = _parent_asset(family, fmt)
        if asset:
            return asset
    return None


def present_format(family: dict[str, Any], fmt: str) -> dict[str, Any]:
    looked = lookup_format_master(family, fmt)
    available = looked.get("status") == "HUMAN_APPROVED"
    parent = _parent_asset(family, fmt) if available else None
    session = (family.get("studio_preview") or {}).get(fmt) or {}
    current = str(session.get("visual_asset") or parent or "") or None
    status_value = str(session.get("approval_status") or "")
    has_draft = bool(session.get("revision_id") and status_value == "DRAFT")
    compare = None
    if session.get("parent_asset_id") and session.get("visual_asset"):
        compare = {
            "before_asset_id": str(session["parent_asset_id"]),
            "after_asset_id": str(session["visual_asset"]),
        }
    return {
        "format": fmt,
        "available": available,
        "preview_asset_id": current if available else None,
        "parent_asset_id": parent,
        "has_draft": has_draft,
        "can_approve": has_draft,
        "can_revert": bool(session.get("revision_id") and current and current != parent),
        "compare": compare,
    }


def present_family(family: dict[str, Any], *, selected_format: str | None = None) -> dict[str, Any]:
    available = _available_formats(family)
    default = STORY_REEL if STORY_REEL in available else (available[0] if available else FEED_PORTRAIT)
    selected = selected_format if selected_format in available else default
    formats = [present_format(family, fmt) for fmt in DISPLAY_FORMATS]
    return {
        "id": str(family.get("FAMILY_ID") or ""),
        "title": _title(family),
        "subtitle": _offer_line(family),
        "project": str(family.get("project_name") or identity_project(family) or ""),
        "preview_asset_id": _card_preview(family),
        "updated_at": family.get("approved_at") or family.get("updated_at"),
        "formats": formats,
        "available_formats": available,
        "selected_format": selected,
        "selected": present_format(family, selected) if selected in available else None,
        "publishing": {
            "available": False,
            "message": "Yayınlama bu sürümde bağlı değil.",
        },
    }


def identity_project(family: dict[str, Any]) -> str | None:
    identity = family.get("identity") or {}
    value = identity.get("PROJECT_IDENTITY")
    return str(value) if value else None


def present_card(family: dict[str, Any]) -> dict[str, Any]:
    payload = present_family(family)
    return {
        "id": payload["id"],
        "title": payload["title"],
        "subtitle": payload["subtitle"],
        "project": payload["project"],
        "preview_asset_id": payload["preview_asset_id"],
        "updated_at": payload["updated_at"],
        "available_formats": payload["available_formats"],
    }


def list_premium_campaigns(db: Session) -> dict[str, Any]:
    row = _campaign_row(db)
    library = _library(row)
    campaigns = [present_card(family) for family in _live_families(library)]
    return {"campaigns": campaigns}


def get_premium_campaign(db: Session, family_id: str, *, format: str | None = None) -> dict[str, Any]:
    row = _campaign_row(db)
    library = _library(row)
    family = resolve_family(library, family_id=family_id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kampanya bulunamadı.")
    return present_family(family, selected_format=format)


def plan_studio_revision(
    *,
    family: dict[str, Any],
    instruction: str,
    scope: Scope,
    fmt: str,
) -> dict[str, Any]:
    classified = classify_production_intent(instruction)
    intent = str(classified.get("intent") or "")

    if intent == FORMAT_ADAPTATION:
        # Production lock: never call Story/format recomposers. Switch or report missing.
        target = str(classified.get("target_format") or fmt)
        routed = route_format_request(classified=classified, library={"premium_creative_families": [family]}, family_id=str(family.get("FAMILY_ID")))
        if routed.get("status") == "PREMIUM_FORMAT_MASTER_MISSING" or lookup_format_master(family, target).get("status") != "HUMAN_APPROVED":
            return {
                "ok": False,
                "code": "FORMAT_MASTER_MISSING",
                "message": format_missing_message(target),
                "execute": False,
                "switch_format": None,
                "classified": classified,
            }
        return {
            "ok": True,
            "code": "SWITCH_FORMAT",
            "message": None,
            "execute": False,
            "switch_format": target,
            "classified": classified,
        }

    if intent == VISUAL_REPLACE_ONLY:
        return {
            "ok": False,
            "code": "REVISION_FAIL",
            "message": MSG_REVISION_FAIL,
            "execute": False,
            "switch_format": None,
            "classified": classified,
        }

    family_wide = scope == "campaign" or intent == FAMILY_WIDE_REVISION
    if family_wide and intent in {PRICE_EDIT_ONLY, COPY_EDIT_ONLY, FAMILY_WIDE_REVISION}:
        territory = classified.get("family_wide_territory") or intent
        classified = dict(classified)
        classified["intent"] = FAMILY_WIDE_REVISION
        classified["family_wide_territory"] = territory if territory != FAMILY_WIDE_REVISION else classified.get("family_wide_territory")
        if classified.get("family_wide_territory") is None and intent == PRICE_EDIT_ONLY:
            classified["family_wide_territory"] = PRICE_EDIT_ONLY
        if classified.get("family_wide_territory") is None and intent == COPY_EDIT_ONLY:
            classified["family_wide_territory"] = COPY_EDIT_ONLY
        intent = FAMILY_WIDE_REVISION

    if intent == PRICE_EDIT_ONLY or (
        intent == FAMILY_WIDE_REVISION and "PRICE" in str(classified.get("family_wide_territory") or "")
    ):
        if not is_proven_price_command(instruction):
            return _fail(classified)
        members = _routed_members(family, classified, fmt, family_wide=family_wide, kind="PRICE")
        return _plan_from_members(classified, members, family_wide=family_wide, kind="PRICE")

    if intent == COPY_EDIT_ONLY or (
        intent == FAMILY_WIDE_REVISION and "COPY" in str(classified.get("family_wide_territory") or "")
    ):
        if not is_proven_copy_command(instruction):
            return _fail(classified)
        members = _routed_members(family, classified, fmt, family_wide=family_wide, kind="COPY")
        return _plan_from_members(classified, members, family_wide=family_wide, kind="COPY")

    return _fail(classified)


def _fail(classified: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "code": "REVISION_FAIL",
        "message": MSG_REVISION_FAIL,
        "execute": False,
        "switch_format": None,
        "classified": classified,
    }


def _member_action(family: dict[str, Any], fmt: str, *, kind: str) -> str:
    looked = lookup_format_master(family, fmt)
    if looked.get("status") != "HUMAN_APPROVED":
        return SKIP_FORMAT_MASTER_MISSING
    slot = looked.get("master") or {}
    if kind == "PRICE" and not format_semantic_present(slot, "PRICE"):
        return SKIP_TARGET_NOT_PRESENT
    if kind == "COPY" and not format_copy_phrase_present(slot, OLD_COPY.rstrip("!")):
        return SKIP_TARGET_NOT_PRESENT
    return "REVISE"


def _routed_members(
    family: dict[str, Any],
    classified: dict[str, Any],
    fmt: str,
    *,
    family_wide: bool,
    kind: str,
) -> list[dict[str, Any]]:
    if family_wide:
        wide = route_family_wide_revision(
            classified=classified,
            library={"premium_creative_families": [family]},
            family_id=str(family.get("FAMILY_ID")),
            target_phrase=OLD_COPY if kind == "COPY" else None,
        )
        members = []
        for item in wide.get("members") or []:
            action = item.get("action")
            if action == REVISE_INDEPENDENTLY:
                action = "REVISE"
            members.append({"format": item.get("format"), "action": action})
        return members
    return [{"format": fmt, "action": _member_action(family, fmt, kind=kind)}]


def _plan_from_members(
    classified: dict[str, Any],
    members: list[dict[str, Any]],
    *,
    family_wide: bool,
    kind: str,
) -> dict[str, Any]:
    revise = [item for item in members if item["action"] == "REVISE"]
    if not family_wide:
        if not members:
            return _fail(classified)
        action = members[0]["action"]
        if action == SKIP_TARGET_NOT_PRESENT:
            return {
                "ok": False,
                "code": "TARGET_NOT_PRESENT",
                "message": MSG_TARGET_NOT_PRESENT,
                "execute": False,
                "switch_format": None,
                "classified": classified,
                "members": members,
                "kind": kind,
            }
        if action == SKIP_FORMAT_MASTER_MISSING:
            return {
                "ok": False,
                "code": "FORMAT_MASTER_MISSING",
                "message": format_missing_message(members[0]["format"]),
                "execute": False,
                "switch_format": None,
                "classified": classified,
                "members": members,
                "kind": kind,
            }
        return {
            "ok": True,
            "code": "REVISE",
            "message": None,
            "execute": True,
            "switch_format": None,
            "classified": classified,
            "members": members,
            "kind": kind,
            "family_wide": False,
        }
    if not revise:
        skipped = {item["action"] for item in members}
        if SKIP_TARGET_NOT_PRESENT in skipped and SKIP_FORMAT_MASTER_MISSING in skipped or SKIP_TARGET_NOT_PRESENT in skipped:
            return {
                "ok": False,
                "code": "TARGET_NOT_PRESENT",
                "message": MSG_TARGET_NOT_PRESENT,
                "execute": False,
                "switch_format": None,
                "classified": classified,
                "members": members,
                "kind": kind,
            }
        return {
            "ok": False,
            "code": "FORMAT_MASTER_MISSING",
            "message": MSG_FORMAT_MASTER_MISSING,
            "execute": False,
            "switch_format": None,
            "classified": classified,
            "members": members,
            "kind": kind,
        }
    return {
        "ok": True,
        "code": "REVISE",
        "message": None,
        "execute": True,
        "switch_format": None,
        "classified": classified,
        "members": members,
        "kind": kind,
        "family_wide": True,
    }


def _apply_price(image: Image.Image, fmt: str) -> tuple[Image.Image | None, dict[str, Any]]:
    if fmt == FEED_PORTRAIT:
        return apply_feed_price_revision(image)
    if fmt == STORY_REEL:
        return apply_story_price_revision(image)
    if fmt == SQUARE:
        return apply_square_price_revision(image)
    return None, {}


def _apply_copy(image: Image.Image, fmt: str) -> tuple[Image.Image | None, dict[str, Any]]:
    if fmt == FEED_PORTRAIT:
        return apply_feed_copy_revision(image)
    if fmt == STORY_REEL:
        return apply_story_copy_revision(image)
    if fmt == SQUARE:
        return apply_square_copy_revision(image)
    return None, {}


def _persist_child(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    image: Image.Image,
    *,
    family: dict[str, Any],
    fmt: str,
) -> str:
    project_id = family.get("project_id")
    linked = UUID(str(project_id)) if project_id else row.linked_project_id
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=linked,
        content=_png(image),
        content_type="image/png",
        campaign_mode=f"premium-studio-revision-{fmt.replace(':', 'x')}",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PREMIUM STUDIO REVISION CHILD. DO NOT OVERWRITE FORMAT MASTER.",
    )
    return str(asset.id)


def _slot_source_sha(db: Session, slot: dict[str, Any]) -> str:
    import hashlib

    raw = _read_bytes(db, UUID(str(slot["SOURCE_ASSET_ID"])))
    return hashlib.sha256(raw).hexdigest()


def revise_premium_campaign(
    db: Session,
    user: User,
    family_id: str,
    *,
    instruction: str,
    fmt: str,
    scope: Scope,
) -> dict[str, Any]:
    from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

    row = _campaign_row(db)
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    library = _library(row)
    family = resolve_family(library, family_id=family_id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kampanya bulunamadı.")

    plan = plan_studio_revision(family=family, instruction=instruction, scope=scope, fmt=fmt)
    if plan.get("switch_format"):
        payload = present_family(family, selected_format=str(plan["switch_format"]))
        payload["result"] = {"ok": True, "code": "SWITCH_FORMAT", "message": None}
        return payload
    if not plan.get("execute"):
        payload = present_family(family, selected_format=fmt)
        payload["result"] = {
            "ok": False,
            "code": plan.get("code") or "REVISION_FAIL",
            "message": plan.get("message") or MSG_REVISION_FAIL,
        }
        return payload

    reset_provider_call_count()
    kind = str(plan.get("kind") or "")
    revised = 0
    identities = {}
    shas = {}
    for member in plan.get("members") or []:
        item_fmt = member["format"]
        if member["action"] != "REVISE":
            continue
        looked = lookup_format_master(family, item_fmt)
        slot = looked.get("master")
        if not isinstance(slot, dict):
            continue
        identities[item_fmt] = {
            "FORMAT_MASTER_ID": slot.get("FORMAT_MASTER_ID"),
            "SOURCE_ASSET_ID": slot.get("SOURCE_ASSET_ID"),
            "SOURCE_SHA256": slot.get("SOURCE_SHA256"),
            "APPROVAL_STATUS": slot.get("APPROVAL_STATUS"),
        }
        parent_id = str(slot["SOURCE_ASSET_ID"])
        raw = _read_bytes(db, UUID(parent_id))
        shas[item_fmt] = _slot_source_sha(db, slot)
        parent = Image.open(io.BytesIO(raw)).convert("RGB")
        child_image, meta = _apply_price(parent, item_fmt) if kind == "PRICE" else _apply_copy(parent, item_fmt)
        if child_image is None:
            if not plan.get("family_wide"):
                payload = present_family(family, selected_format=fmt)
                payload["result"] = {
                    "ok": False,
                    "code": "TARGET_NOT_PRESENT",
                    "message": MSG_TARGET_NOT_PRESENT,
                }
                return payload
            continue
        child_id = _persist_child(db, user, row, child_image, family=family, fmt=item_fmt)
        if child_id == parent_id:
            raise RuntimeError("Premium Studio refused to overwrite a format master")
        revision_id = str(uuid4())
        attach_derived_revision(
            slot,
            {
                "revision_id": revision_id,
                "FAMILY_ID": family.get("FAMILY_ID"),
                "PARENT_FORMAT_MASTER_ID": slot.get("FORMAT_MASTER_ID"),
                "parent_asset_id": parent_id,
                "visual_asset": child_id,
                "approval_status": "DRAFT",
                "router_eligible": False,
                "master_state": "CHILD_REVISION",
                "format": item_fmt,
                "natural_language_instruction": instruction,
                "created_at": _now(),
                "phase": "13.0",
                "territory": kind,
                "compose": {k: v for k, v in (meta or {}).items() if k != "runs"},
            },
        )
        preview = dict(family.get("studio_preview") or {})
        preview[item_fmt] = {
            "revision_id": revision_id,
            "visual_asset": child_id,
            "parent_asset_id": parent_id,
            "approval_status": "DRAFT",
        }
        family["studio_preview"] = preview
        revised += 1

    if provider_call_count() != 0:
        raise RuntimeError("Premium Studio refused a GPT Image / Ideogram call")

    for item_fmt, ident in identities.items():
        slot = family["formats"][item_fmt]
        if str(slot.get("SOURCE_ASSET_ID")) != str(ident["SOURCE_ASSET_ID"]):
            raise RuntimeError("Premium Studio refused to mutate a format master asset")
        if str(slot.get("FORMAT_MASTER_ID")) != str(ident["FORMAT_MASTER_ID"]):
            raise RuntimeError("Premium Studio refused to mutate a format master id")
        live = _slot_source_sha(db, slot)
        expected = slot.get("SOURCE_SHA256") or shas[item_fmt]
        if live != expected and live != shas[item_fmt]:
            raise RuntimeError("Premium Studio refused to mutate original master bytes")

    landscape = (family.get("formats") or {}).get(LANDSCAPE) or {}
    if landscape.get("FORMAT_MASTER_ID") is not None:
        raise RuntimeError("Premium Studio fabricated 16:9")

    _save_library(row, library)
    _production_guard(before, snapshot_identity(dict(row.context_json or {})))
    db.add(row)
    db.commit()

    message = None
    if plan.get("family_wide") and revised:
        message = family_wide_user_confirmation(territory=kind, revised_count=revised, language="tr")
        if kind == "PRICE":
            message = family_wide_user_confirmation(territory="PRICE", revised_count=revised, language="tr")
        elif kind == "COPY":
            message = family_wide_user_confirmation(territory="COPY", revised_count=revised, language="tr")

    if revised == 0:
        payload = present_family(family, selected_format=fmt)
        payload["result"] = {
            "ok": False,
            "code": "REVISION_FAIL",
            "message": MSG_REVISION_FAIL,
        }
        return payload

    payload = present_family(family, selected_format=fmt)
    payload["result"] = {"ok": True, "code": "REVISED", "message": message}
    return payload


def approve_premium_revision(db: Session, family_id: str, *, fmt: str) -> dict[str, Any]:
    row = _campaign_row(db)
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    library = _library(row)
    family = resolve_family(library, family_id=family_id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kampanya bulunamadı.")
    session = (family.get("studio_preview") or {}).get(fmt) or {}
    revision_id = session.get("revision_id")
    visual = session.get("visual_asset")
    looked = lookup_format_master(family, fmt)
    slot = looked.get("master")
    if not revision_id or not visual or not isinstance(slot, dict):
        payload = present_family(family, selected_format=fmt)
        payload["result"] = {"ok": False, "code": "REVISION_FAIL", "message": MSG_REVISION_FAIL}
        return payload
    parent_asset = str(slot.get("SOURCE_ASSET_ID"))
    approve_child_revision(slot, revision_id=str(revision_id), visual_asset=str(visual))
    if str(slot.get("SOURCE_ASSET_ID")) != parent_asset:
        raise RuntimeError("Premium Studio refused to overwrite the format master on approval")
    preview = dict(family.get("studio_preview") or {})
    preview[fmt] = {**session, "approval_status": "HUMAN_APPROVED"}
    family["studio_preview"] = preview
    _save_library(row, library)
    _production_guard(before, snapshot_identity(dict(row.context_json or {})))
    db.add(row)
    db.commit()
    payload = present_family(family, selected_format=fmt)
    payload["result"] = {"ok": True, "code": "APPROVED", "message": None}
    return payload


def revert_premium_preview(db: Session, family_id: str, *, fmt: str) -> dict[str, Any]:
    row = _campaign_row(db)
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    library = _library(row)
    family = resolve_family(library, family_id=family_id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kampanya bulunamadı.")
    looked = lookup_format_master(family, fmt)
    slot = looked.get("master") or {}
    parent_asset = slot.get("SOURCE_ASSET_ID")
    preview = dict(family.get("studio_preview") or {})
    preview.pop(fmt, None)
    family["studio_preview"] = preview
    if isinstance(slot, dict) and parent_asset and str(slot.get("SOURCE_ASSET_ID")) != str(parent_asset):
        raise RuntimeError("Premium Studio refused to mutate the format master on revert")
    _save_library(row, library)
    _production_guard(before, snapshot_identity(dict(row.context_json or {})))
    db.add(row)
    db.commit()
    payload = present_family(family, selected_format=fmt)
    payload["result"] = {"ok": True, "code": "REVERTED", "message": None}
    return payload


def download_premium_creative(db: Session, family_id: str, *, fmt: str):
    row = _campaign_row(db)
    library = _library(row)
    family = resolve_family(library, family_id=family_id)
    if family is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Kampanya bulunamadı.")
    looked = lookup_format_master(family, fmt)
    if looked.get("status") != "HUMAN_APPROVED":
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=format_missing_message(fmt))
    asset_id = _preview_asset(family, fmt)
    if not asset_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MSG_FORMAT_MASTER_MISSING)
    asset = get_asset_or_404(UUID(asset_id), db, include_archived=True)
    stream, media_type = open_asset_content(asset)
    title = _title(family).replace('"', "")
    ext = "png" if "png" in (media_type or "") else "jpg"
    filename = f"{title}-{fmt.replace(':', 'x')}.{ext}"
    return stream, media_type, filename
