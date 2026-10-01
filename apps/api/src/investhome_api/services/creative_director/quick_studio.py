"""Live Creative Studio — AI Quick Creative project workflow.

Wires the existing Phase 5 generate/revise pipeline to Hızlı Tasarım.
Does not create Premium Masters or Creative Families.
Does not invent project architecture, logos, or commercial numbers.
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorCampaignRequest,
    CreativeDirectorGenerateAdRequest,
    CreativeDirectorReviseRequest,
)
from investhome_api.services.creative_director.phase5_workflow import (
    APPROVED_TEMPLE_PHOTO_IDS,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    TEMPLE_PROJECT_ID,
    current_session,
    generate_ad_phase5,
    revise_ad_phase5,
)
from investhome_api.services.creative_director.quick_creative_safety import (
    requests_unsupported_commercial_fact,
)
from investhome_api.services.creative_director.service import create_campaign
from investhome_api.services.creative_studio_media_service import get_asset_or_404, open_asset_content

FormatId = Literal["4:5", "9:16", "1:1", "16:9"]

FORMAT_PRESETS: dict[str, str] = {
    "4:5": "portrait",
    "9:16": "story",
    "1:1": "square",
    "16:9": "landscape",
}

TEMPLE_PHOTO_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("7346e259-f999-4fbb-a8d5-63708d4e0c81", "Dış cephe — gündüz 003", "exterior"),
    ("543aeb03-c4c9-46f9-9d9f-81bf53f45438", "Dış cephe — gündüz 002", "exterior"),
    ("7696df34-0544-44b9-89f5-0d1b2523c412", "Dış cephe — gündüz 009", "exterior"),
    ("c3d11c35-d8b7-485c-b216-0a4da68b751a", "İç mekan — oturma odası", "interior"),
    ("2d44757b-079c-4a78-a4a9-5fe6370466c8", "Dış cephe — gündüz 008", "exterior"),
    ("5d26caf3-c237-4a78-9f3a-91f05dd24fa2", "Dış cephe — gündüz 001", "exterior"),
    (LOCKED_HERO_ASSET_ID, "Dış cephe — gündüz 004", "exterior"),
)

TEMPLE_LIVING_ID = "c3d11c35-d8b7-485c-b216-0a4da68b751a"
TEMPLE_DEFAULT_EXTERIOR_ID = "7346e259-f999-4fbb-a8d5-63708d4e0c81"

_INTERIOR_MARKERS = ("iç mekan", "ic mekan", "iç mekân", "interior", "living", "oturma", "salon")
_EXTERIOR_MARKERS = ("dış cephe", "dis cephe", "exterior", "cephe")
_NEW_DESIGN_MARKERS = ("yeni bir tasarım", "yeni bir tasarim", "yeni tasarım üret", "yeni tasarim uret")

MSG_MISSING_FACT = (
    "Bu iddia için proje kaydında onaylı bir ticari rakam yok. "
    "Lütfen rakamı yazın veya bu iddiayı çıkarın."
)
MSG_NO_PHOTO = "Bu proje için onaylı bir görsel bulunamadı. Yapay görsel üretilmez."
MSG_NO_LOGO = "Bu proje için onaylı logo bulunamadı. Logo uydurulmaz."
MSG_PHOTO_NOT_APPROVED = "Yalnızca bu projenin onaylı görselleri kullanılabilir."
MSG_NO_CREATIVE = "Önce bir tasarım üretin."


def _fold(text: str) -> str:
    table = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s"})
    return (text or "").translate(table).casefold()


def _project_or_404(db: Session, project_id: UUID) -> Project:
    row = db.get(Project, project_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı.")
    return row


def _campaign_or_404(db: Session, campaign_id: UUID) -> CreativeDirectorCampaign:
    row = db.get(CreativeDirectorCampaign, campaign_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tasarım bulunamadı.")
    ctx = row.context_json or {}
    if not ctx.get("quick_creative"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Tasarım bulunamadı.")
    return row


def _asset(db: Session, asset_id: str) -> CreativeStudioMediaAsset | None:
    try:
        uid = UUID(asset_id)
    except (TypeError, ValueError):
        return None
    row = db.get(CreativeStudioMediaAsset, uid)
    if row is None or row.archived_at is not None:
        return None
    return row


def _photo_meta(asset: CreativeStudioMediaAsset) -> dict[str, Any]:
    return {
        "asset_id": str(asset.id),
        "id": str(asset.id),
        "filename": asset.filename,
        "content_type": asset.content_type,
        "folder_category": asset.folder_category,
        "visual_subject": None,
        "tags": list(asset.tags or []),
        "role": "hero",
        "provenance_source": asset.source_type,
        "classification": "INTERIOR_APPROVED"
        if "interior" in _fold(str(asset.filename or ""))
        else "EXTERIOR_APPROVED",
        "architecture_locked": True,
        "approved": True,
        "project_relation": "project_primary",
    }


def _label_from_filename(filename: str) -> str:
    name = _fold(filename)
    if any(tok in name for tok in ("living", "interior", "oturma", "salon")):
        return "İç mekan"
    if any(tok in name for tok in ("exterior", "cephe", "render")):
        return "Dış cephe"
    return "Proje görseli"


def _temple_photos(db: Session) -> list[dict[str, Any]]:
    photos: list[dict[str, Any]] = []
    seen: set[str] = set()
    for asset_id, label, kind in TEMPLE_PHOTO_CATALOG:
        asset = _asset(db, asset_id)
        if asset is None or str(asset.linked_project_id) != TEMPLE_PROJECT_ID:
            continue
        if asset_id in seen:
            continue
        seen.add(asset_id)
        photos.append(
            {
                "id": asset_id,
                "label": label,
                "kind": kind,
                "filename": asset.filename,
            }
        )
    return photos


def _generic_photos(db: Session, project_id: UUID) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == project_id,
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
        ).all()
    )
    photos: list[dict[str, Any]] = []
    for row in rows:
        name = _fold(str(row.filename or ""))
        ctype = (row.content_type or "").lower()
        if "logo" in name or "svg" in ctype:
            continue
        if not ctype.startswith("image/"):
            continue
        photos.append(
            {
                "id": str(row.id),
                "label": _label_from_filename(str(row.filename or "")),
                "kind": "interior" if any(tok in name for tok in ("living", "interior", "oturma")) else "exterior",
                "filename": row.filename,
            }
        )
    return photos


def _logo_asset(db: Session, project_id: UUID) -> CreativeStudioMediaAsset | None:
    if str(project_id) == TEMPLE_PROJECT_ID:
        asset = _asset(db, LOCKED_LOGO_ASSET_ID)
        if asset is not None:
            return asset
    rows = list(
        db.scalars(
            select(CreativeStudioMediaAsset).where(
                CreativeStudioMediaAsset.linked_project_id == project_id,
                CreativeStudioMediaAsset.archived_at.is_(None),
            )
        ).all()
    )
    for row in rows:
        name = _fold(str(row.filename or ""))
        if "logo" in name:
            return row
    return None


def resolved_photos(db: Session, project_id: UUID) -> list[dict[str, Any]]:
    if str(project_id) == TEMPLE_PROJECT_ID:
        return _temple_photos(db)
    return _generic_photos(db, project_id)


def _public_photos(photos: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [{"id": item["id"], "label": item["label"], "kind": item["kind"]} for item in photos]


def _project_card(project: Project) -> dict[str, Any]:
    return {
        "id": str(project.id),
        "name": project.project_name,
        "code": project.project_code,
        "city": project.city,
        "state": project.state,
        "live": str(project.id) == TEMPLE_PROJECT_ID,
    }


def _needs_missing_fact(request: str) -> bool:
    """Block only an affirmative ask for a commercial number that was not supplied."""
    return requests_unsupported_commercial_fact(request)


def _wants_interior(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _INTERIOR_MARKERS)


def _wants_exterior(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _EXTERIOR_MARKERS)


def _wants_new_design(text: str) -> bool:
    folded = _fold(text)
    return any(marker in folded for marker in _NEW_DESIGN_MARKERS)


def _pick_photo(photos: list[dict[str, Any]], request: str, current_id: str | None = None) -> dict[str, Any] | None:
    if not photos:
        return None
    by_id = {item["id"]: item for item in photos}
    if _wants_interior(request):
        interior = next((item for item in photos if item["kind"] == "interior"), None)
        if interior is not None:
            return interior
    if _wants_exterior(request):
        others = [item for item in photos if item["kind"] == "exterior" and item["id"] != current_id]
        if others:
            return others[0]
        exterior = next((item for item in photos if item["kind"] == "exterior"), None)
        if exterior is not None:
            return exterior
    preferred = by_id.get(TEMPLE_DEFAULT_EXTERIOR_ID) or by_id.get(LOCKED_HERO_ASSET_ID)
    return preferred or photos[0]


def _apply_photo(ctx: dict[str, Any], asset: CreativeStudioMediaAsset) -> None:
    meta = _photo_meta(asset)
    ctx["selected_assets"] = [meta]
    drive = dict(ctx.get("drive_research") or {})
    drive["selected_interior"] = {**dict(drive.get("selected_interior") or {}), **meta}
    ctx["drive_research"] = drive


def _current_preview_id(ctx: dict[str, Any]) -> str | None:
    session = current_session(ctx)
    if not isinstance(session, dict):
        return None
    current_id = session.get("current_version_id")
    for version in session.get("versions") or []:
        if isinstance(version, dict) and version.get("version_id") == current_id:
            asset_id = version.get("asset_id")
            return str(asset_id) if asset_id else None
    versions = [v for v in (session.get("versions") or []) if isinstance(v, dict)]
    if versions:
        asset_id = versions[-1].get("asset_id")
        return str(asset_id) if asset_id else None
    return None


def _photo_label(photos: list[dict[str, Any]], asset_id: str | None) -> str | None:
    if not asset_id:
        return None
    for item in photos:
        if item["id"] == str(asset_id):
            return item["label"]
    return None


def _present(
    *,
    campaign_id: UUID,
    project: Project,
    fmt: str,
    format_preset: str,
    preview_asset_id: str | None,
    selected_photo_label: str | None,
    approved: bool,
    photos: list[dict[str, Any]],
    logo_available: bool,
) -> dict[str, Any]:
    return {
        "campaign_id": str(campaign_id),
        "project_id": str(project.id),
        "project_name": project.project_name,
        "format": fmt,
        "format_preset": format_preset,
        "preview_asset_id": preview_asset_id,
        "selected_photo_label": selected_photo_label,
        "approved": approved,
        "premium": False,
        "project_reality_firewall": "ACTIVE",
        "logo_resolved": logo_available,
        "photos": _public_photos(photos),
    }


def list_quick_projects(db: Session) -> dict[str, Any]:
    rows = list(
        db.scalars(select(Project).where(Project.archived_at.is_(None)).order_by(Project.project_name)).all()
    )
    items = [_project_card(row) for row in rows]
    items.sort(key=lambda item: (0 if item["id"] == TEMPLE_PROJECT_ID else 1, item["name"].casefold()))
    return {"items": items, "total": len(items)}


def get_quick_project(db: Session, project_id: UUID) -> dict[str, Any]:
    project = _project_or_404(db, project_id)
    photos = resolved_photos(db, project.id)
    logo = _logo_asset(db, project.id)
    return {
        "project": _project_card(project),
        "photos": _public_photos(photos),
        "photo_count": len(photos),
        "logo_resolved": logo is not None,
        "ready": bool(photos) and logo is not None,
        "project_reality_firewall": "ACTIVE",
    }


def _stamp_quick_context(
    row: CreativeDirectorCampaign,
    *,
    fmt: str,
    photo: CreativeStudioMediaAsset | None,
) -> dict[str, Any]:
    ctx = dict(row.context_json or {})
    ctx["quick_creative"] = True
    ctx["premium"] = False
    ctx["premium_family"] = None
    engine = dict(ctx.get("generation_engine") or {})
    engine["format_specified"] = True
    engine["format_preset"] = FORMAT_PRESETS[fmt]
    engine["aspect_ratio"] = fmt
    ctx["generation_engine"] = engine
    ctx["format_preset"] = FORMAT_PRESETS[fmt]
    ctx["aspect_ratio"] = fmt
    if photo is not None:
        _apply_photo(ctx, photo)
        if str(row.linked_project_id) == TEMPLE_PROJECT_ID:
            logo_meta = dict(ctx.get("selected_logo") or {})
            logo_meta["asset_id"] = LOCKED_LOGO_ASSET_ID
            ctx["selected_logo"] = logo_meta
            drive = dict(ctx.get("drive_research") or {})
            drive_logo = dict(drive.get("selected_logo") or {})
            drive_logo["asset_id"] = LOCKED_LOGO_ASSET_ID
            drive["selected_logo"] = drive_logo
            ctx["drive_research"] = drive
    row.context_json = ctx
    flag_modified(row, "context_json")
    return ctx


def generate_quick_creative(
    db: Session,
    user: User,
    *,
    project_id: UUID,
    request: str,
    fmt: FormatId = "4:5",
    language: str = "tr",
) -> dict[str, Any]:
    brief = (request or "").strip()
    if not brief:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tasarım isteği gerekli.")
    if fmt not in FORMAT_PRESETS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Geçersiz format.")
    if _needs_missing_fact(brief):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_MISSING_FACT)

    project = _project_or_404(db, project_id)
    photos = resolved_photos(db, project.id)
    logo = _logo_asset(db, project.id)
    if logo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_NO_LOGO)
    picked = _pick_photo(photos, brief)
    if picked is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_NO_PHOTO)
    photo = _asset(db, picked["id"])
    if photo is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_NO_PHOTO)

    created = create_campaign(
        db,
        user,
        CreativeDirectorCampaignRequest(
            project_id=project.id,
            brief=brief,
            mode="project",
            language=language,
        ),
    )
    row = db.get(CreativeDirectorCampaign, created.campaign_id)
    if row is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Kampanya oluşturulamadı.")
    _stamp_quick_context(row, fmt=fmt, photo=photo)
    db.flush()

    gen = generate_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorGenerateAdRequest(
            language=language,
            aspect_ratio=fmt,
            format_preset=FORMAT_PRESETS[fmt],
            production_mode="finished_ad",
            workflow="phase5",
            user_request=brief,
        ),
    )
    return _present(
        campaign_id=row.id,
        project=project,
        fmt=str(gen.aspect_ratio or fmt),
        format_preset=str(gen.format_preset or FORMAT_PRESETS[fmt]),
        preview_asset_id=str(gen.final_asset_id),
        selected_photo_label=picked["label"],
        approved=False,
        photos=photos,
        logo_available=True,
    )


def _quick_payload(db: Session, row: CreativeDirectorCampaign, *, preview_asset_id: str | None, approved: bool) -> dict[str, Any]:
    project = _project_or_404(db, row.linked_project_id)
    ctx = row.context_json or {}
    photos = resolved_photos(db, project.id)
    selected = (ctx.get("selected_assets") or [{}])[0] if ctx.get("selected_assets") else {}
    selected_id = str(selected.get("asset_id") or selected.get("id") or "") or None
    return _present(
        campaign_id=row.id,
        project=project,
        fmt=str(ctx.get("aspect_ratio") or "4:5"),
        format_preset=str(ctx.get("format_preset") or "portrait"),
        preview_asset_id=preview_asset_id or _current_preview_id(ctx),
        selected_photo_label=_photo_label(photos, selected_id),
        approved=approved,
        photos=photos,
        logo_available=_logo_asset(db, project.id) is not None,
    )


def revise_quick_creative(
    db: Session,
    user: User,
    campaign_id: UUID,
    *,
    instruction: str,
) -> dict[str, Any]:
    text = (instruction or "").strip()
    if not text:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Revizyon isteği gerekli.")
    row = _campaign_or_404(db, campaign_id)
    ctx = dict(row.context_json or {})
    preview_id = _current_preview_id(ctx)
    if not preview_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_NO_CREATIVE)
    if _needs_missing_fact(text):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_MISSING_FACT)

    fmt = str(ctx.get("aspect_ratio") or "4:5")
    preset = str(ctx.get("format_preset") or FORMAT_PRESETS.get(fmt, "portrait"))
    photos = resolved_photos(db, row.linked_project_id)
    selected = (ctx.get("selected_assets") or [{}])[0] if ctx.get("selected_assets") else {}
    current_photo_id = str(selected.get("asset_id") or selected.get("id") or "") or None

    if _wants_new_design(text):
        gen = generate_ad_phase5(
            db,
            user,
            row.id,
            CreativeDirectorGenerateAdRequest(
                language=str(ctx.get("language") or "tr"),
                aspect_ratio=fmt,  # type: ignore[arg-type]
                format_preset=preset,
                production_mode="finished_ad",
                workflow="phase5",
                user_request=text,
            ),
        )
        return _quick_payload(db, row, preview_asset_id=str(gen.final_asset_id), approved=False)

    if _wants_interior(text) or _wants_exterior(text):
        picked = _pick_photo(photos, text, current_id=current_photo_id)
        if picked is not None:
            photo = _asset(db, picked["id"])
            if photo is None or (
                str(row.linked_project_id) == TEMPLE_PROJECT_ID and picked["id"] not in APPROVED_TEMPLE_PHOTO_IDS
            ):
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_PHOTO_NOT_APPROVED)
            _apply_photo(ctx, photo)
            row.context_json = ctx
            flag_modified(row, "context_json")
            db.flush()

    result = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction=text,
            current_final_asset_id=UUID(preview_id),
            language=str(ctx.get("language") or "tr"),
            aspect_ratio=fmt,  # type: ignore[arg-type]
            format_preset=preset,
        ),
    )
    approved = "APPROVE" in (result.revision_intents or [])
    return _quick_payload(db, row, preview_asset_id=str(result.final_asset_id), approved=approved)


def replace_quick_image(
    db: Session,
    user: User,
    campaign_id: UUID,
    *,
    photo_id: str,
) -> dict[str, Any]:
    row = _campaign_or_404(db, campaign_id)
    ctx = dict(row.context_json or {})
    preview_id = _current_preview_id(ctx)
    if not preview_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_NO_CREATIVE)
    photos = resolved_photos(db, row.linked_project_id)
    allowed = {item["id"] for item in photos}
    if photo_id not in allowed:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_PHOTO_NOT_APPROVED)
    if str(row.linked_project_id) == TEMPLE_PROJECT_ID and photo_id not in APPROVED_TEMPLE_PHOTO_IDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_PHOTO_NOT_APPROVED)
    photo = _asset(db, photo_id)
    if photo is None or str(photo.linked_project_id) != str(row.linked_project_id):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=MSG_PHOTO_NOT_APPROVED)
    _apply_photo(ctx, photo)
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    fmt = str(ctx.get("aspect_ratio") or "4:5")
    result = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction="Bu görsel yerine diğer onaylı proje görselini kullan.",
            current_final_asset_id=UUID(preview_id),
            language=str(ctx.get("language") or "tr"),
            aspect_ratio=fmt,  # type: ignore[arg-type]
            format_preset=str(ctx.get("format_preset") or FORMAT_PRESETS.get(fmt, "portrait")),
        ),
    )
    return _quick_payload(db, row, preview_asset_id=str(result.final_asset_id), approved=False)


def approve_quick_creative(db: Session, user: User, campaign_id: UUID) -> dict[str, Any]:
    return revise_quick_creative(db, user, campaign_id, instruction="Onayla")


def vary_quick_creative(db: Session, user: User, campaign_id: UUID) -> dict[str, Any]:
    row = _campaign_or_404(db, campaign_id)
    ctx = dict(row.context_json or {})
    brief = str(ctx.get("original_user_brief") or row.original_brief or "").strip()
    if not brief:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tasarım isteği gerekli.")
    fmt = str(ctx.get("aspect_ratio") or "4:5")
    gen = generate_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorGenerateAdRequest(
            language=str(ctx.get("language") or "tr"),
            aspect_ratio=fmt,  # type: ignore[arg-type]
            format_preset=str(ctx.get("format_preset") or FORMAT_PRESETS.get(fmt, "portrait")),
            production_mode="finished_ad",
            workflow="phase5",
            user_request=brief,
        ),
    )
    return _quick_payload(db, row, preview_asset_id=str(gen.final_asset_id), approved=False)


def download_quick_creative(db: Session, campaign_id: UUID):
    row = _campaign_or_404(db, campaign_id)
    preview_id = _current_preview_id(row.context_json or {})
    if not preview_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=MSG_NO_CREATIVE)
    asset = get_asset_or_404(UUID(preview_id), db, include_archived=True)
    stream, media_type = open_asset_content(asset)
    project = db.get(Project, row.linked_project_id)
    name = (project.project_name if project else "tasarim").replace('"', "")
    fmt = str((row.context_json or {}).get("aspect_ratio") or "4:5").replace(":", "x")
    ext = "png" if "png" in (media_type or "") else "jpg"
    return stream, media_type, f"{name}-hizli-{fmt}.{ext}"
