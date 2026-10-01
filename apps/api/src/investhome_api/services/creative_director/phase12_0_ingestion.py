"""Phase 12.0 — ingest one existing Investhome finished creative as a pending Production Premium Master.

Does not redesign, reconstruct, or generate pixels. Original asset remains byte-for-byte.
Does not activate the master. Does not run Stage 4.0.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from PIL import Image, ImageDraw
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset, CreativeStudioMediaFolder
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
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
from investhome_api.services.creative_director.project_creative_master_library import (
    add_master,
    count_approved_premium,
    empty_master,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_12_0 = "phase12_0_first_production_premium_master_ingestion"
STATUS_PENDING = "PRODUCTION_PREMIUM_MASTER_PENDING_HUMAN_REVIEW"
STATUS_NONE = "NO_ELIGIBLE_PRODUCTION_CREATIVE_FOUND"
STATUS_FAIL = "PRODUCTION_PREMIUM_MASTER_INGESTION_FAIL"
GOLD = (201, 168, 92)
IVORY = (236, 230, 218)

SELECTED_FILENAME = "ORNEK_00013.jpg"
SELECTED_ASSET_ID = GRADE_A_MEDIA[SELECTED_FILENAME]
PRODUCTION_MASTER_ID = str(uuid5(NAMESPACE_URL, "investhome:production-premium-master:ornek-00013:phase12-0"))
SOURCE_PROJECT_NAME = "Investhome brand / Washington D.C. (not The Temple)"
SOURCE_CATEGORY = "INVESTHOME_APPROVED"
CANONICAL_SIZE = (1080, 1350)

FORBIDDEN_NAME_MARKERS = (
    "gpt-image-project-",
    "hybrid-v1",
    "hybrid-v2",
    "ai-native",
    "reference-guided",
    "premium-master-01",
    "premium-master-02",
    "premium-master-03",
)

CANDIDATE_NOTES = {
    "ORNEK_00013.jpg": {
        "project": SOURCE_PROJECT_NAME,
        "approval_evidence": "Investhome-branded finished 4:5 campaign in Media Library DESIGN_REFERENCE; human-curated Grade-A set",
        "production_quality": "PASS",
        "master_suitability": "STRONGEST — brand thesis campaign; architecture is not The Temple",
        "commercial": "Brand proposition without numeric price / unit / web CTA",
    },
    "ORNEK_00001.jpg": {
        "project": "UniLoft / Investhome — Washington D.C.",
        "approval_evidence": "Investhome-branded finished 4:5 UniLoft campaign in DESIGN_REFERENCE",
        "production_quality": "PASS",
        "master_suitability": "STRONG — named UniLoft offer; not The Temple",
        "commercial": "Early-access offer present; no numeric price",
    },
    "ORNEK_00008.jpg": {
        "project": "UniLoft / Investhome — Washington D.C.",
        "approval_evidence": "Investhome-branded finished 4:5 UniLoft dusk campaign in DESIGN_REFERENCE",
        "production_quality": "PASS",
        "master_suitability": "STRONG — delivery badges; UniLoft architecture, not The Temple",
        "commercial": "Early-delivery offer; no numeric price",
    },
    "ORNEK_00006.jpg": {
        "project": "UniLoft / Investhome — Washington D.C.",
        "approval_evidence": "Investhome-branded finished 4:5 UniLoft interior campaign in DESIGN_REFERENCE",
        "production_quality": "PASS",
        "master_suitability": "STRONG — market-scarcity thesis; UniLoft interior, not The Temple",
        "commercial": "Verbal investment argument; no price",
    },
    "ORNEK_00011.jpg": {
        "project": "300 I St. NE / Investhome — Washington D.C.",
        "approval_evidence": "Investhome-branded finished 4:5 proximity campaign in DESIGN_REFERENCE",
        "production_quality": "PASS",
        "master_suitability": "STRONG — different building; not The Temple",
        "commercial": "Location walking times; no price",
    },
    "ORNEK_00015.jpg": {
        "project": "Investhome / Washington D.C. interior campaign",
        "approval_evidence": "Investhome-branded finished 4:5 interior campaign in DESIGN_REFERENCE",
        "production_quality": "PASS",
        "master_suitability": "GRADE_A interior; not The Temple",
        "commercial": "Lifestyle proof; no price",
    },
}


def _bbox(x: float, y: float, w: float, h: float) -> dict[str, float]:
    return {"x": round(x, 4), "y": round(y, 4), "w": round(w, 4), "h": round(h, 4)}


def _territory(
    *,
    territory_id: str,
    present: bool,
    role: str,
    bbox: dict[str, float] | None,
    importance: str,
    relationships: list[str],
    editability: str,
    immutability: str,
    format_priority: str,
    copy: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": territory_id,
        "present": present,
        "BOUNDARY": bbox,
        "SEMANTIC_ROLE": role,
        "VISUAL_IMPORTANCE": importance,
        "RELATIONSHIPS": relationships,
        "EDITABILITY": editability,
        "IMMUTABILITY": immutability,
        "FORMAT_PRIORITY": format_priority,
    }
    if copy:
        row["copy"] = copy
    if note:
        row["note"] = note
    return row


def ornek_00013_semantic_map() -> dict[str, Any]:
    """Territories follow ORNEK_00013. Absent commercial slots are recorded as absent."""
    photo = _bbox(0.0, 0.36, 0.50, 0.64)
    headline = _bbox(0.48, 0.08, 0.46, 0.30)
    subhead = _bbox(0.46, 0.40, 0.48, 0.22)
    highlight = _bbox(0.50, 0.54, 0.42, 0.07)
    logo = _bbox(0.58, 0.86, 0.36, 0.10)
    background = _bbox(0.0, 0.0, 1.0, 1.0)
    return {
        "schema": "PremiumSemanticMapV1",
        "status": "READY",
        "extracted": "AFTER the design exists",
        "source_filename": SELECTED_FILENAME,
        "source_asset_id": SELECTED_ASSET_ID,
        "doctrine": ["DESIGN FIRST", "SEMANTICS SECOND", "EDITABILITY THIRD"],
        "never_originate_design_from_map": True,
        "design_observation": (
            "Asymmetric two-mass 4:5: lower-left neoclassical colonnade as structural photographic mass; "
            "navy field as the message page; stacked headline in the void; quiet Investhome footer."
        ),
        "territories": [
            _territory(
                territory_id="PROJECT_IDENTITY",
                present=True,
                role="Investhome brand campaign for Washington D.C. investment — not The Temple",
                bbox=logo,
                importance="high",
                relationships=["LOGO ↔ BRAND_IDENTITY"],
                editability="SEMANTICALLY_EDITABLE",
                immutability="IMMUTABLE_IDENTITY",
                format_priority="must remain brand identification",
            ),
            _territory(
                territory_id="PROJECT_PHOTO",
                present=True,
                role="VISUAL_HERO — cropped neoclassical colonnade as structural mass",
                bbox=photo,
                importance="primary",
                relationships=["PHOTO ↔ VISUAL_HERO", "PHOTO ↔ HEADLINE"],
                editability="FORMAT_FLEXIBLE",
                immutability="IMMUTABLE_IDENTITY",
                format_priority="architecture immutable; crop/position flexible",
                note="This photograph is not The Temple. Do not treat it as Temple project reality.",
            ),
            _territory(
                territory_id="LOGO",
                present=True,
                role="Investhome wordmark + house mark + tagline YATIRIMA AÇILAN KAPI",
                bbox=logo,
                importance="high",
                relationships=["LOGO ↔ BRAND_IDENTITY"],
                editability="FORMAT_FLEXIBLE",
                immutability="IMMUTABLE_IDENTITY",
                format_priority="brand identification, not visual hero",
            ),
            _territory(
                territory_id="HEADLINE",
                present=True,
                role="primary verbal chant",
                bbox=headline,
                importance="primary",
                relationships=["OFFER ↔ HEADLINE", "HEADLINE ↔ SUBHEAD", "PHOTO ↔ HEADLINE"],
                editability="SEMANTICALLY_EDITABLE",
                immutability="copy locked until a revision asks to change it",
                format_priority="line-break and scale flexible",
                copy="DÜZENLİ. / GÜVENLİ. / PRESTİJLİ.",
            ),
            _territory(
                territory_id="SUBHEAD",
                present=True,
                role="supporting investment argument",
                bbox=subhead,
                importance="medium",
                relationships=["HEADLINE ↔ SUBHEAD"],
                editability="SEMANTICALLY_EDITABLE",
                immutability="",
                format_priority="OPTIONAL_BY_FORMAT if the frame cannot hold the paragraph",
                copy=(
                    "Planlı şehir dokusu, yüksek yaşam standartları ve güçlü kira piyasası... "
                    "Tüm bunlar Washington DC’yi sadece popüler değil, istikrarlı bir yatırım lokasyonu yapıyor."
                ),
            ),
            _territory(
                territory_id="OFFER",
                present=False,
                role="no numeric / % offer in this design",
                bbox=None,
                importance="absent",
                relationships=["OFFER ↔ HEADLINE"],
                editability="OPTIONAL_BY_FORMAT",
                immutability="",
                format_priority="do not invent an offer badge",
                note="The gold PRESTİJLİ line is verbal prestige, not a commercial offer device.",
            ),
            _territory(
                territory_id="PRICE",
                present=False,
                role="no price territory in this design",
                bbox=None,
                importance="absent",
                relationships=["PRICE ↔ UNIT"],
                editability="OPTIONAL_BY_FORMAT",
                immutability="",
                format_priority="do not invent a price",
            ),
            _territory(
                territory_id="UNIT",
                present=False,
                role="no unit territory in this design",
                bbox=None,
                importance="absent",
                relationships=["PRICE ↔ UNIT"],
                editability="OPTIONAL_BY_FORMAT",
                immutability="",
                format_priority="do not invent a unit",
            ),
            _territory(
                territory_id="CTA",
                present=False,
                role="no web-button CTA; brand footer is identification not action",
                bbox=None,
                importance="absent",
                relationships=["CTA ↔ COMMERCIAL_SEQUENCE"],
                editability="OPTIONAL_BY_FORMAT",
                immutability="",
                format_priority="do not invent a button",
            ),
            _territory(
                territory_id="CLOSURE",
                present=True,
                role="gold land inside the headline stack (PRESTİJLİ) plus highlighted location phrase",
                bbox=highlight,
                importance="medium",
                relationships=["HEADLINE ↔ SUBHEAD"],
                editability="SEMANTICALLY_EDITABLE",
                immutability="",
                format_priority="keep as the verbal land, not a badge",
                copy="PRESTİJLİ. / istikrarlı bir yatırım lokasyonu",
            ),
            _territory(
                territory_id="BACKGROUND",
                present=True,
                role="designed navy field — the page, not leftover sky",
                bbox=background,
                importance="structural",
                relationships=["PHOTO ↔ VISUAL_HERO"],
                editability="FORMAT_FLEXIBLE",
                immutability="",
                format_priority="field may redistributing; do not replace with generated architecture",
            ),
            _territory(
                territory_id="GRAPHIC_ELEMENTS",
                present=True,
                role="translucent highlight over the closing location phrase",
                bbox=highlight,
                importance="low",
                relationships=["HEADLINE ↔ SUBHEAD"],
                editability="DECORATIVE",
                immutability="",
                format_priority="OPTIONAL_BY_FORMAT",
            ),
            _territory(
                territory_id="DECORATIVE_ELEMENTS",
                present=False,
                role="no separate ornament beyond the highlight",
                bbox=None,
                importance="absent",
                relationships=[],
                editability="DECORATIVE",
                immutability="",
                format_priority="OPTIONAL_BY_FORMAT",
            ),
        ],
    }


def relationship_map() -> dict[str, Any]:
    return {
        "schema": "PremiumMasterRelationshipMapV1",
        "status": "READY",
        "pairs": [
            {"left": "PRICE", "right": "UNIT", "status": "ABSENT", "rule": "must remain a clear commercial pair when both exist"},
            {"left": "OFFER", "right": "HEADLINE", "status": "HEADLINE_ONLY", "rule": "headline carries the proposition; no separate offer device"},
            {"left": "CTA", "right": "COMMERCIAL_SEQUENCE", "status": "ABSENT", "rule": "do not invent a final action button"},
            {"left": "LOGO", "right": "BRAND_IDENTITY", "status": "LOCKED", "rule": "brand identification, not visual hero"},
            {"left": "PHOTO", "right": "VISUAL_HERO", "status": "LOCKED", "rule": "colonnade is structural mass, not decoration"},
            {"left": "HEADLINE", "right": "SUBHEAD", "status": "LOCKED", "rule": "chant then argument in the navy void"},
            {"left": "PHOTO", "right": "HEADLINE", "status": "LOCKED", "rule": "prestige architecture proves PRESTİJLİ; type stays off the stone"},
        ],
    }


def master_lock_map() -> dict[str, Any]:
    return {
        "schema": "PremiumMasterLockMapV1",
        "status": "READY",
        "IMMUTABLE_IDENTITY": ["LOGO", "PROJECT_PHOTO architecture", "Investhome brand mark", "navy/gold personality"],
        "SEMANTICALLY_EDITABLE": ["HEADLINE", "SUBHEAD", "CLOSURE"],
        "FORMAT_FLEXIBLE": ["PROJECT_PHOTO crop/position", "type line-breaks", "logo position", "navy field redistribution"],
        "DECORATIVE": ["GRAPHIC_ELEMENTS highlight"],
        "OPTIONAL_BY_FORMAT": ["SUBHEAD paragraph", "GRAPHIC_ELEMENTS", "absent PRICE/UNIT/CTA/OFFER — do not invent them"],
        "do_not_make_every_element_editable": True,
    }


def inspect_candidates(db: Session) -> dict[str, Any]:
    folders = {str(item.id): item for item in db.scalars(select(CreativeStudioMediaFolder))}

    def folder_path(folder_id: Any) -> str:
        names: list[str] = []
        current = folders.get(str(folder_id)) if folder_id else None
        seen: set[str] = set()
        while current is not None and str(current.id) not in seen:
            seen.add(str(current.id))
            names.append(current.name)
            current = folders.get(str(current.parent_id)) if current.parent_id else None
        return " / ".join(reversed(names))

    rejected: list[dict[str, Any]] = []
    marketing_empty = True
    for folder in folders.values():
        path = folder_path(folder.id)
        if "09_MARKETING_CONTENT" in path or path.endswith("05_SOCIAL"):
            count = db.scalar(
                select(CreativeStudioMediaAsset.id).where(
                    CreativeStudioMediaAsset.folder_id == folder.id,
                    CreativeStudioMediaAsset.archived_at.is_(None),
                )
            )
            if count is not None:
                marketing_empty = False
    if marketing_empty:
        rejected.append(
            {
                "filename": None,
                "reason": "Temple 09_MARKETING_CONTENT and 05_SOCIAL contain no finished campaign creatives",
            }
        )
    assets = list(db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.archived_at.is_(None))))
    research_rejected = 0
    for asset in assets:
        name = asset.filename or ""
        if any(marker in name.lower() for marker in FORBIDDEN_NAME_MARKERS):
            research_rejected += 1
    rejected.append(
        {
            "filename": "gpt-image-project-* / Hybrid / AI-native / Masters 01–03",
            "count": research_rejected,
            "reason": "Research artifacts. Forbidden as production Premium Masters.",
        }
    )
    rejected.append(
        {
            "filename": "08_CATALOG artwork / Links / PDFs",
            "reason": "Print catalog source photography and multi-page PDFs, not a 4:5 campaign advertisement",
        }
    )

    records: list[dict[str, Any]] = []
    for filename in (
        "ORNEK_00013.jpg",
        "ORNEK_00001.jpg",
        "ORNEK_00008.jpg",
        "ORNEK_00006.jpg",
        "ORNEK_00011.jpg",
        "ORNEK_00015.jpg",
    ):
        asset_id = GRADE_A_MEDIA[filename]
        asset = db.get(CreativeStudioMediaAsset, UUID(asset_id))
        note = CANDIDATE_NOTES[filename]
        image = Image.open(io.BytesIO(_read_bytes(db, UUID(asset_id)))).convert("RGB")
        records.append(
            {
                "ASSET_ID": asset_id,
                "FILENAME": filename,
                "PROJECT": note["project"],
                "SOURCE_CATEGORY": SOURCE_CATEGORY,
                "FORMAT": "4:5",
                "RESOLUTION": f"{image.size[0]}×{image.size[1]}",
                "APPROVAL_EVIDENCE": note["approval_evidence"],
                "PRODUCTION_QUALITY": note["production_quality"],
                "MASTER_SUITABILITY": note["master_suitability"],
                "folder": folder_path(asset.folder_id) if asset else None,
                "design_references_are_not_automatically_masters": True,
                "evidence_it_is_an_investhome_creative": True,
                "temple_architecture": False,
                "selected": filename == SELECTED_FILENAME,
                "image": image,
            }
        )
    return {
        "schema": "ProductionMasterCandidateAuditV1",
        "selected_filename": SELECTED_FILENAME,
        "selected_asset_id": SELECTED_ASSET_ID,
        "records": records,
        "rejected_pools": rejected,
        "note": (
            "DESIGN_REFERENCES are not automatically production masters. "
            "These six are ingested as candidates because they are finished Investhome-branded "
            "4:5 campaign advertisements, not inspiration-only moodboards. "
            "None depict The Temple. Human review must confirm Production Premium Master status."
        ),
    }


def quality_check() -> dict[str, str]:
    return {
        "PROFESSIONAL QUALITY": "PASS",
        "COMMERCIAL COMPLETENESS": "PASS",
        "BRAND QUALITY": "PASS",
        "TYPOGRAPHIC QUALITY": "PASS",
        "IMAGE QUALITY": "PASS",
        "FORMAT ADAPTATION POTENTIAL": "PASS",
        "commercial_completeness_note": (
            "Complete brand/investment advertisement. PRICE, UNIT, and web CTA are absent in the design "
            "and must not be invented. Offer is verbal prestige, not a % device."
        ),
        "temple_project_reality_note": "FAIL for The Temple — colonnade is not Temple architecture.",
    }


def source_record() -> dict[str, Any]:
    return {
        "ORIGINAL_ASSET_ID": SELECTED_ASSET_ID,
        "MASTER_ID": PRODUCTION_MASTER_ID,
        "SOURCE_CATEGORY": SOURCE_CATEGORY,
        "SOURCE_PROJECT": SOURCE_PROJECT_NAME,
        "CANONICAL_FORMAT": "4:5",
        "CANONICAL_DIMENSIONS": f"{CANONICAL_SIZE[0]}×{CANONICAL_SIZE[1]}",
        "APPROVAL_STATUS": "PENDING HUMAN REVIEW",
        "ORIGINAL_ASSET_MODIFIED": False,
        "byte_for_byte": True,
        "rendered_replacement": False,
    }


def build_pending_master() -> dict[str, Any]:
    master = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="Investhome — DÜZENLİ. GÜVENLİ. PRESTİJLİ. (ORNEK_00013)",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        visual_asset=SELECTED_ASSET_ID,
        master_id=PRODUCTION_MASTER_ID,
    )
    master["source"] = SOURCE_CATEGORY
    master["source_project"] = SOURCE_PROJECT_NAME
    master["canonical_format"] = "4:5"
    master["canonical_dimensions"] = list(CANONICAL_SIZE)
    master["production_quality"] = False
    master["router_eligible"] = False
    master["pending_human_review"] = True
    master["human_review"] = "PENDING"
    master["temple_architecture"] = False
    master["original_asset_id"] = SELECTED_ASSET_ID
    master["logo_asset_id"] = None
    master["photo_object_source"] = None
    master["semantic_map"] = ornek_00013_semantic_map()
    master["relationship_map"] = relationship_map()
    master["lock_map"] = master_lock_map()
    master["creative_tags"] = ["PRODUCTION_CANDIDATE", "INVESTHOME_APPROVED", "ORNEK_00013", "NOT_TEMPLE"]
    master["note"] = (
        "Pending human review. Original DESIGN_REFERENCE asset referenced byte-for-byte. "
        "Not router eligible. Not The Temple. Stage 4 remains paused."
    )
    return master


def render_candidate_board(records: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1280), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "01  PRODUCTION MASTER CANDIDATES  —  existing Investhome creatives, not generated", font=_font(18), fill=GOLD)
    draw.text((36, 48), "Max 6. DESIGN_REFERENCES are not automatic masters. None is The Temple.", font=_font(14), fill=(180, 176, 168))
    x = 36
    y = 88
    for index, rec in enumerate(records[:6]):
        tile = rec["image"].copy()
        tile.thumbnail((280, 350), Image.Resampling.LANCZOS)
        col = index % 6
        px = 36 + col * 314
        canvas.paste(tile.convert("RGB"), (px, y))
        label = "SELECTED" if rec.get("selected") else "CANDIDATE"
        draw.text((px, y + 360), f"{label}  {rec['FILENAME']}", font=_font(13), fill=GOLD if rec.get("selected") else IVORY)
        draw.text((px, y + 382), rec["RESOLUTION"], font=_font(12), fill=(160, 156, 148))
        draw.text((px, y + 404), rec["PRODUCTION_QUALITY"], font=_font(12), fill=(160, 156, 148))
        _ = x
    draw.text((36, 520), "Each file is a finished Investhome 4:5 campaign. Architecture / project is not The Temple.", font=_font(14), fill=IVORY)
    y = 560
    for rec in records[:6]:
        line = f"{rec['FILENAME']}  {rec['ASSET_ID']}  {rec['PROJECT']}"
        draw.text((36, y), line[:140], font=_font(13), fill=(200, 196, 188))
        y += 28
        draw.text((56, y), rec["MASTER_SUITABILITY"][:120], font=_font(13), fill=(160, 156, 148))
        y += 32
    return canvas


def render_semantic_overlay(original: Image.Image, semantic: dict[str, Any]) -> Image.Image:
    image = original.copy().convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = image.size
    colors = {
        "PROJECT_PHOTO": (220, 80, 80, 70),
        "HEADLINE": (201, 168, 92, 80),
        "SUBHEAD": (120, 170, 210, 70),
        "LOGO": (180, 220, 160, 80),
        "CLOSURE": (220, 180, 90, 70),
        "GRAPHIC_ELEMENTS": (180, 140, 220, 50),
    }
    for item in semantic.get("territories") or []:
        bbox = item.get("BOUNDARY")
        if not item.get("present") or not isinstance(bbox, dict):
            continue
        if item["id"] in {"BACKGROUND", "PROJECT_IDENTITY"}:
            continue
        color = colors.get(item["id"], (200, 200, 200, 50))
        x0 = int(bbox["x"] * w)
        y0 = int(bbox["y"] * h)
        x1 = int((bbox["x"] + bbox["w"]) * w)
        y1 = int((bbox["y"] + bbox["h"]) * h)
        draw.rectangle((x0, y0, x1, y1), outline=color[:3] + (220,), width=4, fill=color)
        draw.text((x0 + 8, y0 + 8), item["id"], font=_font(18), fill=(255, 255, 255, 240))
    return Image.alpha_composite(image, overlay).convert("RGB")


def render_human_review_board(*, original: Image.Image, overlay: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 18), "10  HUMAN REVIEW  —  IS THIS AN ACCEPTABLE PRODUCTION PREMIUM MASTER?", font=_font(18), fill=GOLD)
    draw.text((36, 48), "Left: original, no overlay.  Right: semantic territories.  Not The Temple.  Not auto-activated.", font=_font(14), fill=(180, 176, 168))
    left = original.copy()
    right = overlay.copy()
    left.thumbnail((820, 980), Image.Resampling.LANCZOS)
    right.thumbnail((820, 980), Image.Resampling.LANCZOS)
    canvas.paste(left.convert("RGB"), (40, 88))
    canvas.paste(right.convert("RGB"), (980, 88))
    draw.text((40, 1058), f"ORIGINAL  {SELECTED_FILENAME}  {SELECTED_ASSET_ID}", font=_font(13), fill=IVORY)
    draw.text((980, 1058), "SEMANTIC OVERLAY  —  analysis only, original unchanged", font=_font(13), fill=IVORY)
    return canvas


def generate_phase12_0_ingestion(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = user
    original_ctx = dict(row.context_json or {})
    before = snapshot_identity(original_ctx)
    before["current_master_design_spec_id"] = original_ctx.get("current_master_design_spec_id")
    blob = _phase5(dict(original_ctx))
    preserved = preserve_stage2(blob)
    preserved["quality1112"] = list(blob.get("phase11_12_product_lock_tests") or [])
    preserved["quality40"] = list(blob.get("stage4_0_format_proof_tests") or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()

    library = blob.get("project_creative_master_library")
    if not isinstance(library, dict):
        raise RuntimeError("Phase 12.0 requires ProjectCreativeMasterLibraryV1")
    if blob.get("premium_creative_product_model_locked") is not True:
        raise RuntimeError("Phase 12.0 requires Phase 11.12 product-model lock")

    master_01 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == APPROVED_MASTER_ID), None)
    master_02 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID), None)
    master_03 = next((item for item in library.get("masters") or [] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID), None)
    if master_01 is None or master_02 is None or master_03 is None:
        raise RuntimeError("Phase 12.0 requires Masters 01–03 records to remain")
    m1 = json.loads(json.dumps(_jsonable(master_01), default=str))
    m2 = json.loads(json.dumps(_jsonable(master_02), default=str))
    m3 = _identity_slice(master_03)
    kids = {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03.get("derived_revisions") or [])}
    lock_before = blob.get("premium_creative_product_model_locked")
    product_before = blob.get("premium_creative_product_model")
    auto_before = library.get("autonomous_premium_generation")
    quick_before = library.get("ai_quick_creative_status")
    role_before = library.get("masters_01_03_role")
    cover_before = blob.get("current_cover_asset_id") or original_ctx.get("current_cover_asset_id")

    audit = inspect_candidates(db)
    selected_image = next(item["image"] for item in audit["records"] if item["selected"])
    if selected_image.size != CANONICAL_SIZE:
        raise RuntimeError("Selected original is not the expected 4:5 asset")
    semantic = ornek_00013_semantic_map()
    overlay = render_semantic_overlay(selected_image, semantic)
    pending = build_pending_master()
    if any(str(item.get("master_id")) == PRODUCTION_MASTER_ID for item in library.get("masters") or []):
        library["masters"] = [item for item in library["masters"] if str(item.get("master_id")) != PRODUCTION_MASTER_ID]
    add_master(library, pending)
    library["stage4_0_status"] = "PAUSED"
    library["next_production_phase"] = "HUMAN MASTER APPROVAL"
    library["phase12_0_status"] = STATUS_PENDING
    library["pending_production_master_id"] = PRODUCTION_MASTER_ID

    master_01_after = next(item for item in library["masters"] if str(item.get("master_id")) == APPROVED_MASTER_ID)
    master_02_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_02_ID)
    master_03_after = next(item for item in library["masters"] if str(item.get("master_id")) == TEMPLE_PREMIUM_MASTER_03_ID)
    if json.dumps(_jsonable(master_01_after), default=str) != json.dumps(m1, default=str):
        raise RuntimeError("Phase 12.0 refused to change Master 01")
    if json.dumps(_jsonable(master_02_after), default=str) != json.dumps(m2, default=str):
        raise RuntimeError("Phase 12.0 refused to change Master 02")
    if _identity_slice(master_03_after) != m3:
        raise RuntimeError("Phase 12.0 refused to mutate Master 03")
    if {str(item.get("revision_id")): str(item.get("visual_asset")) for item in (master_03_after.get("derived_revisions") or [])} != kids:
        raise RuntimeError("Phase 12.0 refused to mutate Stage 2 children")
    if str(master_01_after.get("visual_asset")) != APPROVED_ASSET_ID:
        raise RuntimeError("Phase 12.0 refused to change Master 01 visual")
    if str(master_02_after.get("visual_asset")) != APPROVED_ASSET_02:
        raise RuntimeError("Phase 12.0 refused to change Master 02 visual")
    if str(master_03_after.get("visual_asset")) != APPROVED_ASSET_03:
        raise RuntimeError("Phase 12.0 refused to change Master 03 visual")
    if count_approved_premium(library) != 3:
        raise RuntimeError("Phase 12.0 must not promote the pending master")
    if library.get("autonomous_premium_generation") != auto_before:
        raise RuntimeError("Phase 12.0 refused to change autonomous premium status")
    if library.get("ai_quick_creative_status") != quick_before:
        raise RuntimeError("Phase 12.0 refused to change AI Quick Creative")
    if library.get("masters_01_03_role") != role_before:
        raise RuntimeError("Phase 12.0 refused to reclassify Masters 01–03")
    if blob.get("premium_creative_product_model_locked") != lock_before:
        raise RuntimeError("Phase 12.0 refused to unlock the product model")
    if blob.get("premium_creative_product_model") != product_before:
        raise RuntimeError("Phase 12.0 refused to rewrite the Phase 11.12 product model")
    if pending.get("router_eligible") is not False or pending.get("approval_status") != "DRAFT":
        raise RuntimeError("Phase 12.0 must not auto-activate the pending master")
    if pending.get("visual_asset") != SELECTED_ASSET_ID:
        raise RuntimeError("Phase 12.0 must reference the original asset")
    if provider_call_count() != 0:
        raise RuntimeError("Phase 12.0 must not call image generation")

    blob["project_creative_master_library"] = json.loads(json.dumps(_jsonable(library), default=str))
    blob["stage4_0_status"] = "PAUSED"
    restore_stage2(blob, preserved)
    blob["phase11_12_product_lock_tests"] = preserved.get("quality1112")
    blob["stage4_0_format_proof_tests"] = preserved.get("quality40")
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_12_0,
        "created_at": _now(),
        "status": STATUS_PENDING,
        "selected_filename": SELECTED_FILENAME,
        "asset_id": SELECTED_ASSET_ID,
        "master_id": PRODUCTION_MASTER_ID,
        "source_category": SOURCE_CATEGORY,
        "source_project": SOURCE_PROJECT_NAME,
        "router_eligible": False,
        "approval": "PENDING HUMAN REVIEW",
        "original_asset_modified": False,
        "gpt_image_calls": provider_call_count(),
        "ideogram_calls": 0,
        "stage_4": "PAUSED",
        "cover": PRODUCTION_COVER_V2,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "language": language,
        "quality": quality_check(),
        "audit": {k: v for k, v in audit.items() if k != "records"} | {
            "records": [{k: val for k, val in rec.items() if k != "image"} for rec in audit["records"]]
        },
        "semantic_map": semantic,
        "relationship_map": relationship_map(),
        "lock_map": master_lock_map(),
        "source_record": source_record(),
        "ingestion": {
            "schema": "PremiumMasterIngestionV1",
            "status": "READY",
            "executed": True,
            "rendered_new_version": False,
            "master": {k: pending[k] for k in pending if k not in {"semantic_map", "relationship_map", "lock_map"}},
        },
        "boards": {
            "candidate": render_candidate_board(audit["records"]),
            "original": selected_image.copy(),
            "overlay": overlay,
            "review": render_human_review_board(original=selected_image, overlay=overlay),
        },
        "cover_before": cover_before,
    }
    tests = list(blob.get("phase12_0_ingestion_tests") or [])
    slim = {k: v for k, v in record.items() if k != "boards"}
    tests.append(json.loads(json.dumps(_jsonable(slim), default=str)))
    blob["phase12_0_ingestion_tests"] = tests
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
    return record
