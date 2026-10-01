"""Phase 12.3 — discover and ingest an existing multi-format Premium Creative Family.

Does not generate creatives. Does not derive missing formats. Does not redesign.
Does not alter the ORNEK_00013 family. Does not activate routing.
"""

from __future__ import annotations

import hashlib
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
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import _font
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
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
from investhome_api.services.creative_director.phase12_0_ingestion import (
    PRODUCTION_MASTER_ID,
    SELECTED_ASSET_ID,
    _bbox,
    _territory,
)
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FAMILY_LOCKED_PROPERTIES,
    FAMILY_SCHEMA,
    FEED_PORTRAIT,
    FORMAT_MASTER_SCHEMA,
    LANDSCAPE,
    ORNEK_FAMILY_ID,
    SQUARE,
    STORY_REEL,
    empty_format_slot,
    format_lock_map,
    format_relationship_map,
)
from investhome_api.services.creative_director.project_creative_master_library import count_approved_premium
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count

WORKFLOW_ID_12_3 = "phase12_3_first_multiformat_production_creative_family"
STATUS_PENDING = "MULTI_FORMAT_FAMILY_PENDING_HUMAN_REVIEW"
STATUS_NONE = "NO_EXISTING_MULTI_FORMAT_PRODUCTION_FAMILY_FOUND"
STATUS_FAIL = "MULTI_FORMAT_FAMILY_INGESTION_FAIL"
GOLD = (201, 168, 92)
IVORY = (236, 230, 218)
NAVY = (12, 14, 20)
MUTED = (160, 156, 148)
FOLDER = "Media Library / Investhome OS / DESIGN_REFERENCE"
SOURCE_CATEGORY = "INVESTHOME_APPROVED"
PROJECT_NAME = "UniLoft / Investhome — Washington D.C."
CAMPAIGN_NAME = "UniLoft Washington D.C. — Last Units / $357.000"

ASSET_4X5 = "f73556b5-e8a7-4c20-b874-0a6aef2a5570"
ASSET_9X16 = "c83ba58e-063f-4118-8df1-b8787082187b"
ASSET_1X1 = "4de0deeb-49f0-4936-9db4-9e6deb0d6cb7"
ASSET_1X1_VARIANT = "5ce5e26d-d1fd-4802-a6e6-7c0eecfb3279"
FILE_4X5 = "ORNEK_00012.jpg"
FILE_9X16 = "ORNEK_00005.jpg"
FILE_1X1 = "ORNEK_00003.jpg"
FILE_1X1_VARIANT = "ORNEK_00004.jpg"

FAMILY_ID = str(uuid5(NAMESPACE_URL, "investhome:premium-creative-family:uniloft-last-units-357k"))
MASTER_4X5_ID = str(uuid5(NAMESPACE_URL, "investhome:premium-format-master:uniloft-last-units-357k:4x5"))
MASTER_9X16_ID = str(uuid5(NAMESPACE_URL, "investhome:premium-format-master:uniloft-last-units-357k:9x16"))
MASTER_1X1_ID = str(uuid5(NAMESPACE_URL, "investhome:premium-format-master:uniloft-last-units-357k:1x1"))

FORBIDDEN_NAME_MARKERS = (
    "gpt-image-project-",
    "hybrid-v1",
    "hybrid-v2",
    "ai-native",
    "reference-guided",
    "premium-master-01",
    "premium-master-02",
    "premium-master-03",
    "premium-story-9x16",
    "stage4",
    "recomposition",
)

STAGE4_STORY_MARKERS = (
    "gpt-image-investhome-brand-premium-story",
    "story-9x16-r1",
    "story-9x16-r2",
    "story-9x16-r3",
    "story-9x16-clean",
    "story-9x16-retry",
    "story-9x16-recomposition",
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _ratio(width: int, height: int) -> str:
    ratio = width / height
    if abs(ratio - 0.8) < 0.04:
        return FEED_PORTRAIT
    if abs(ratio - 9 / 16) < 0.04:
        return STORY_REEL
    if abs(ratio - 1.0) < 0.04:
        return SQUARE
    if abs(ratio - 16 / 9) < 0.04:
        return LANDSCAPE
    return f"{width}x{height}"


def _folder_path(folders: dict[str, CreativeStudioMediaFolder], folder_id: Any) -> str:
    names: list[str] = []
    current = folders.get(str(folder_id)) if folder_id else None
    seen: set[str] = set()
    while current is not None and str(current.id) not in seen:
        seen.add(str(current.id))
        names.append(current.name)
        current = folders.get(str(current.parent_id)) if current.parent_id else None
    return " / ".join(reversed(names))


def _fit(image: Image.Image, box: tuple[int, int], fill: tuple[int, int, int] = (20, 22, 28)) -> Image.Image:
    tile = Image.new("RGB", box, fill)
    preview = image.copy().convert("RGB")
    preview.thumbnail(box, Image.Resampling.LANCZOS)
    tile.paste(preview, ((box[0] - preview.width) // 2, (box[1] - preview.height) // 2))
    return tile


def _missing_tile(box: tuple[int, int]) -> Image.Image:
    tile = Image.new("RGB", box, (28, 30, 36))
    draw = ImageDraw.Draw(tile)
    draw.rectangle((8, 8, box[0] - 9, box[1] - 9), outline=(70, 72, 80), width=2)
    draw.text((box[0] // 2 - 48, box[1] // 2 - 10), "MISSING", font=_font(22), fill=MUTED)
    return tile


def load_ornek_catalog(db: Session) -> dict[str, dict[str, Any]]:
    folders = {str(item.id): item for item in db.scalars(select(CreativeStudioMediaFolder))}
    catalog: dict[str, dict[str, Any]] = {}
    for asset in db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.archived_at.is_(None))):
        name = asset.filename or ""
        if not name.upper().startswith("ORNEK_"):
            continue
        raw = _read_bytes(db, UUID(str(asset.id)))
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        catalog[name] = {
            "filename": name,
            "asset_id": str(asset.id),
            "image": image,
            "raw": raw,
            "sha256": _sha(raw),
            "width": image.size[0],
            "height": image.size[1],
            "format": _ratio(*image.size),
            "folder": _folder_path(folders, asset.folder_id),
            "source_location": FOLDER,
        }
    return catalog


def excluded_pools(db: Session) -> list[dict[str, Any]]:
    assets = list(db.scalars(select(CreativeStudioMediaAsset).where(CreativeStudioMediaAsset.archived_at.is_(None))))
    research = sum(1 for item in assets if any(m in (item.filename or "").lower() for m in FORBIDDEN_NAME_MARKERS))
    stories = sum(1 for item in assets if any(m in (item.filename or "").lower() for m in STAGE4_STORY_MARKERS))
    return [
        {
            "pool": "Temple 05_SOCIAL and 09_MARKETING_CONTENT",
            "reason": "Folders exist but contain no finished campaign creatives",
        },
        {
            "pool": "gpt-image / Hybrid / AI-native / Masters 01–03 / Ideogram experiments",
            "count": research,
            "reason": "Research artifacts. Forbidden as Creative Family members.",
        },
        {
            "pool": "Rejected Stage 4 Stories",
            "count": stories,
            "reason": "Autonomously derived 9:16 proofs. REJECTED. Not family members.",
        },
        {
            "pool": "08_CATALOG photography / PDFs",
            "reason": "Source photography and print catalogs, not finished multi-format campaign ads",
        },
    ]


def candidate_families(catalog: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    def slot(filename: str | None) -> dict[str, Any] | None:
        if not filename:
            return None
        item = catalog[filename]
        return {
            "filename": item["filename"],
            "asset_id": item["asset_id"],
            "dimensions": f"{item['width']}×{item['height']}",
            "width": item["width"],
            "height": item["height"],
            "source_location": item["folder"],
            "approval_evidence": (
                "Finished Investhome campaign creative in Media Library DESIGN_REFERENCE; "
                "historically used Investhome-approved advertising"
            ),
            "production_quality": "PASS",
            "same_campaign_confidence": None,
        }

    families = [
        {
            "campaign_family_name": CAMPAIGN_NAME,
            "project_or_brand": PROJECT_NAME,
            "same_campaign_confidence": "HIGH",
            "selected": True,
            "note": (
                "Independently art-directed 4:5, 9:16, and 1:1. Shared UniLoft identity, "
                "$357.000 / $2.650 kira / 2026 teslim / 6 ay erken / son daireler badges. "
                "Layouts differ by format, which is required."
            ),
            "formats": {
                FEED_PORTRAIT: slot(FILE_4X5),
                STORY_REEL: slot(FILE_9X16),
                SQUARE: slot(FILE_1X1),
                LANDSCAPE: None,
            },
            "additional": {"1:1_variant": slot(FILE_1X1_VARIANT)},
        },
        {
            "campaign_family_name": "UniLoft — Sabah kahvesi / erken erişim",
            "project_or_brand": PROJECT_NAME,
            "same_campaign_confidence": "N/A — single format",
            "selected": False,
            "note": "Finished 4:5 UniLoft lifestyle. No matching Story/Square/Landscape of this copy flight.",
            "formats": {FEED_PORTRAIT: slot("ORNEK_00001.jpg"), STORY_REEL: None, SQUARE: None, LANDSCAPE: None},
        },
        {
            "campaign_family_name": "UniLoft — Şehre açılan yaşam alanı",
            "project_or_brand": PROJECT_NAME,
            "same_campaign_confidence": "N/A — single format",
            "selected": False,
            "note": "Finished 4:5 dusk UniLoft. Related UniLoft language, not the $357k last-units composition.",
            "formats": {FEED_PORTRAIT: slot("ORNEK_00008.jpg"), STORY_REEL: None, SQUARE: None, LANDSCAPE: None},
        },
        {
            "campaign_family_name": "Investhome brand — DÜZENLİ. GÜVENLİ. PRESTİJLİ.",
            "project_or_brand": "INVESTHOME BRAND",
            "same_campaign_confidence": "N/A — current 4:5-only family",
            "selected": False,
            "note": "Existing ORNEK_00013 family. No genuine matching Story/Square/Landscape discovered. Left unchanged.",
            "formats": {FEED_PORTRAIT: slot("ORNEK_00013.jpg"), STORY_REEL: None, SQUARE: None, LANDSCAPE: None},
        },
        {
            "campaign_family_name": "300 J Street — $200.000 kazanç / %40",
            "project_or_brand": "Investhome — Washington D.C. / 300 J Street NE",
            "same_campaign_confidence": "N/A — single format",
            "selected": False,
            "note": "Finished 4:5 commercial. Different offer than the $357k UniLoft last-units flight.",
            "formats": {FEED_PORTRAIT: slot("ORNEK_00009.jpg"), STORY_REEL: None, SQUARE: None, LANDSCAPE: None},
        },
    ]
    for family in families:
        for rec in family["formats"].values():
            if rec:
                rec["same_campaign_confidence"] = family["same_campaign_confidence"]
    return families


def _semantic(*, filename: str, asset_id: str, observation: str, territories: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "PremiumSemanticMapV1",
        "status": "READY",
        "extracted": "AFTER the design exists",
        "source_filename": filename,
        "source_asset_id": asset_id,
        "doctrine": ["DESIGN FIRST", "SEMANTICS SECOND", "EDITABILITY THIRD"],
        "never_originate_design_from_map": True,
        "design_observation": observation,
        "territories": territories,
    }


def _t(**kwargs: Any) -> dict[str, Any]:
    return _territory(**kwargs)


def semantic_map_4x5() -> dict[str, Any]:
    return _semantic(
        filename=FILE_4X5,
        asset_id=ASSET_4X5,
        observation="Print-resolution 4:5 UniLoft street at golden hour with Capitol axis; circular last-units badges; Investhome footer.",
        territories=[
            _t(territory_id="PROJECT_IDENTITY", present=True, role="UniLoft Washington D.C. / Investhome", bbox=_bbox(0.32, 0.86, 0.36, 0.12), importance="high", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="SEMANTICALLY_EDITABLE", immutability="IMMUTABLE_IDENTITY", format_priority="brand + project identification"),
            _t(territory_id="PROJECT_PHOTO", present=True, role="UniLoft street + Capitol as location proof", bbox=_bbox(0.0, 0.28, 1.0, 0.72), importance="primary", relationships=["PHOTO ↔ VISUAL_HERO"], editability="FORMAT_FLEXIBLE", immutability="IMMUTABLE_IDENTITY", format_priority="UniLoft photograph, not The Temple", note="Not The Temple architecture."),
            _t(territory_id="LOGO", present=True, role="Investhome wordmark + YATIRIMA AÇILAN KAPI", bbox=_bbox(0.32, 0.88, 0.36, 0.10), importance="high", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="FORMAT_FLEXIBLE", immutability="IMMUTABLE_IDENTITY", format_priority="brand identification"),
            _t(territory_id="HEADLINE", present=True, role="primary verbal territory", bbox=_bbox(0.08, 0.06, 0.84, 0.14), importance="primary", relationships=["HEADLINE ↔ OFFER"], editability="SEMANTICALLY_EDITABLE", immutability="copy locked until a revision asks to change it", format_priority="line-break flexible", copy="ABD WASHINGTON D.C. / INVESTHOME GÜVENCESİYLE GAYRİMENKUL YATIRIMI"),
            _t(territory_id="SUBHEAD", present=False, role="no separate subhead plate", bbox=None, importance="absent", relationships=["HEADLINE ↔ SUBHEAD"], editability="OPTIONAL_BY_FORMAT", immutability="", format_priority="do not invent"),
            _t(territory_id="OFFER", present=True, role="last-units / early-delivery circular badges", bbox=_bbox(0.18, 0.42, 0.52, 0.18), importance="high", relationships=["OFFER ↔ PRICE"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="circular devices owned by this format", copy="Planlandan 6 Ay Erken Teslim / Sınırlı Sayıda Son Daireler!"),
            _t(territory_id="PRICE", present=False, role="no $357.000 plate on this 4:5; rent figure is present", bbox=None, importance="absent", relationships=["PRICE ↔ UNIT"], editability="OPTIONAL_BY_FORMAT", immutability="", format_priority="do not invent a price box this format does not have"),
            _t(territory_id="UNIT", present=True, role="2026 teslim + $2.650 kira", bbox=_bbox(0.16, 0.20, 0.68, 0.08), importance="high", relationships=["PRICE ↔ UNIT"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="stat pair", copy="2026 Tapu Teslim / 2.650$ Kira Getirisi"),
            _t(territory_id="CTA", present=False, role="no web-button CTA", bbox=None, importance="absent", relationships=["CTA ↔ COMMERCIAL_SEQUENCE"], editability="OPTIONAL_BY_FORMAT", immutability="", format_priority="do not invent a button"),
            _t(territory_id="CLOSURE", present=True, role="Investhome footer identification", bbox=_bbox(0.32, 0.88, 0.36, 0.10), importance="medium", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="brand close"),
            _t(territory_id="BACKGROUND", present=True, role="golden-hour street photograph as the page", bbox=_bbox(0.0, 0.0, 1.0, 1.0), importance="structural", relationships=["PHOTO ↔ VISUAL_HERO"], editability="FORMAT_FLEXIBLE", immutability="", format_priority="do not replace with generated architecture"),
        ],
    )


def semantic_map_9x16() -> dict[str, Any]:
    return _semantic(
        filename=FILE_9X16,
        asset_id=ASSET_9X16,
        observation="Native 9:16 Story: dusk UniLoft corner rendering; price plate and circular last-units badges; UniLoft mark; Investhome footer. Not a Stage 4 derivative.",
        territories=[
            _t(territory_id="PROJECT_IDENTITY", present=True, role="UniLoft Washington D.C. / Investhome", bbox=_bbox(0.08, 0.70, 0.40, 0.10), importance="high", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="SEMANTICALLY_EDITABLE", immutability="IMMUTABLE_IDENTITY", format_priority="project mark"),
            _t(territory_id="PROJECT_PHOTO", present=True, role="dusk UniLoft corner rendering as Story hero", bbox=_bbox(0.0, 0.18, 1.0, 0.82), importance="primary", relationships=["PHOTO ↔ VISUAL_HERO"], editability="FORMAT_FLEXIBLE", immutability="IMMUTABLE_IDENTITY", format_priority="native Story crop, not a 4:5 restack", note="Not The Temple. Not a Stage 4 derivative."),
            _t(territory_id="LOGO", present=True, role="Investhome wordmark + YATIRIMA AÇILAN KAPI", bbox=_bbox(0.28, 0.88, 0.44, 0.10), importance="high", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="FORMAT_FLEXIBLE", immutability="IMMUTABLE_IDENTITY", format_priority="footer identification"),
            _t(territory_id="HEADLINE", present=True, role="primary Story chant", bbox=_bbox(0.08, 0.04, 0.84, 0.12), importance="primary", relationships=["HEADLINE ↔ PRICE"], editability="SEMANTICALLY_EDITABLE", immutability="copy locked until a revision asks to change it", format_priority="owned by this 9:16", copy="ABD WASHINGTON D.C. / DÜNYANIN BAŞKENTİNDE GAYRİMENKUL YATIRIMI"),
            _t(territory_id="SUBHEAD", present=True, role="Sıfır Konutlar tan plate", bbox=_bbox(0.28, 0.22, 0.44, 0.05), importance="medium", relationships=["HEADLINE ↔ SUBHEAD"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="Story-only plate", copy="Sıfır Konutlar!"),
            _t(territory_id="OFFER", present=True, role="early-delivery + last-units circular badges", bbox=_bbox(0.06, 0.48, 0.88, 0.16), importance="high", relationships=["OFFER ↔ PRICE"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="Story composition owns badge placement", copy="Planlandan 6 Ay Erken Teslim / Sınırlı Sayıda Son Daireler!"),
            _t(territory_id="PRICE", present=True, role="starting-price plate", bbox=_bbox(0.14, 0.16, 0.72, 0.06), importance="primary", relationships=["PRICE ↔ UNIT"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="Story-owned price territory", copy="$357.000'dan Başlayan Fiyatlar"),
            _t(territory_id="UNIT", present=True, role="2026 teslim + $2.650 kira", bbox=_bbox(0.10, 0.28, 0.80, 0.06), importance="high", relationships=["PRICE ↔ UNIT"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="stat pair", copy="2026 Tapu Teslim / 2.650$ Kira Getirisi"),
            _t(territory_id="CTA", present=False, role="no web-button CTA", bbox=None, importance="absent", relationships=["CTA ↔ COMMERCIAL_SEQUENCE"], editability="OPTIONAL_BY_FORMAT", immutability="", format_priority="do not invent a button"),
            _t(territory_id="CLOSURE", present=True, role="Investhome footer", bbox=_bbox(0.28, 0.88, 0.44, 0.10), importance="medium", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="brand close"),
            _t(territory_id="BACKGROUND", present=True, role="dusk architectural render as the Story page", bbox=_bbox(0.0, 0.0, 1.0, 1.0), importance="structural", relationships=["PHOTO ↔ VISUAL_HERO"], editability="FORMAT_FLEXIBLE", immutability="", format_priority="do not replace with generated architecture"),
        ],
    )


def semantic_map_1x1() -> dict[str, Any]:
    return _semantic(
        filename=FILE_1X1,
        asset_id=ASSET_1X1,
        observation="Native 1:1 terrace looking toward the Capitol; commercial card left; circular last-units badges and UniLoft mark right.",
        territories=[
            _t(territory_id="PROJECT_IDENTITY", present=True, role="UniLoft Washington D.C. / Investhome", bbox=_bbox(0.58, 0.58, 0.36, 0.12), importance="high", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="SEMANTICALLY_EDITABLE", immutability="IMMUTABLE_IDENTITY", format_priority="project mark"),
            _t(territory_id="PROJECT_PHOTO", present=True, role="terrace lifestyle + Capitol as location proof", bbox=_bbox(0.0, 0.0, 1.0, 1.0), importance="primary", relationships=["PHOTO ↔ VISUAL_HERO"], editability="FORMAT_FLEXIBLE", immutability="IMMUTABLE_IDENTITY", format_priority="native square crop", note="Not The Temple."),
            _t(territory_id="LOGO", present=True, role="Investhome wordmark + YATIRIMA AÇILAN KAPI", bbox=_bbox(0.28, 0.88, 0.44, 0.10), importance="high", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="FORMAT_FLEXIBLE", immutability="IMMUTABLE_IDENTITY", format_priority="footer identification"),
            _t(territory_id="HEADLINE", present=True, role="primary square chant", bbox=_bbox(0.06, 0.06, 0.70, 0.16), importance="primary", relationships=["HEADLINE ↔ PRICE"], editability="SEMANTICALLY_EDITABLE", immutability="copy locked until a revision asks to change it", format_priority="owned by this 1:1", copy="WASHINGTON D.C. / DÜNYANIN MERKEZİNDE YERİNİZ HAZIR!"),
            _t(territory_id="SUBHEAD", present=True, role="2026 teslim / sıfır konutlar card header", bbox=_bbox(0.04, 0.28, 0.38, 0.12), importance="medium", relationships=["HEADLINE ↔ SUBHEAD"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="square-owned card", copy="2026 Tapu Teslim / Sıfır Konutlar"),
            _t(territory_id="OFFER", present=True, role="%40 indirim + last-units / early-delivery circles", bbox=_bbox(0.04, 0.38, 0.70, 0.28), importance="high", relationships=["OFFER ↔ PRICE"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="square composition owns devices", copy="%40 İndirim ile / Planlandan 6 Ay Erken Teslim / Sınırlı Sayıda Son Daireler!"),
            _t(territory_id="PRICE", present=True, role="starting-price on the commercial card", bbox=_bbox(0.04, 0.48, 0.38, 0.14), importance="primary", relationships=["PRICE ↔ UNIT"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="square-owned price territory", copy="$357.000'dan Başlayan Fiyatlarla!"),
            _t(territory_id="UNIT", present=True, role="$2.650 kira on the commercial card", bbox=_bbox(0.04, 0.58, 0.38, 0.08), importance="high", relationships=["PRICE ↔ UNIT"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="rent figure", copy="2.650$ Kira Getirisi"),
            _t(territory_id="CTA", present=False, role="no web-button CTA", bbox=None, importance="absent", relationships=["CTA ↔ COMMERCIAL_SEQUENCE"], editability="OPTIONAL_BY_FORMAT", immutability="", format_priority="do not invent a button"),
            _t(territory_id="CLOSURE", present=True, role="Investhome footer", bbox=_bbox(0.28, 0.88, 0.44, 0.10), importance="medium", relationships=["LOGO ↔ BRAND_IDENTITY"], editability="SEMANTICALLY_EDITABLE", immutability="", format_priority="brand close"),
            _t(territory_id="BACKGROUND", present=True, role="golden-hour terrace photograph as the page", bbox=_bbox(0.0, 0.0, 1.0, 1.0), importance="structural", relationships=["PHOTO ↔ VISUAL_HERO"], editability="FORMAT_FLEXIBLE", immutability="", format_priority="do not replace with generated architecture"),
        ],
    )
