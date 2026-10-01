"""Phase 14.0 — AI Quick Creative live project workflow. No GPT Image. No artwork."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from investhome_api.models.creative_studio_media import CreativeStudioMediaAsset
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.services.creative_director.phase5_workflow import (
    APPROVED_TEMPLE_PHOTO_IDS,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    TEMPLE_PROJECT_ID,
    _lock_temple_assets,
)
from investhome_api.services.creative_director.quick_studio import (
    TEMPLE_LIVING_ID,
    _needs_missing_fact,
    get_quick_project,
    list_quick_projects,
    resolved_photos,
)


def test_temple_lock_keeps_approved_catalog_photos() -> None:
    living = UUID(TEMPLE_LIVING_ID)
    hero, logo = _lock_temple_assets(
        UUID(TEMPLE_PROJECT_ID),
        living,
        UUID("00000000-0000-0000-0000-000000000001"),
    )
    assert str(hero) == TEMPLE_LIVING_ID
    assert str(logo) == LOCKED_LOGO_ASSET_ID
    day004, logo2 = _lock_temple_assets(
        UUID(TEMPLE_PROJECT_ID),
        UUID(LOCKED_HERO_ASSET_ID),
        UUID("11111111-1111-1111-1111-111111111111"),
    )
    assert str(day004) == LOCKED_HERO_ASSET_ID
    assert str(logo2) == LOCKED_LOGO_ASSET_ID


def test_temple_lock_unknown_photo_falls_back_to_day004() -> None:
    hero, logo = _lock_temple_assets(
        UUID(TEMPLE_PROJECT_ID),
        uuid4(),
        uuid4(),
    )
    assert str(hero) == LOCKED_HERO_ASSET_ID
    assert str(logo) == LOCKED_LOGO_ASSET_ID


def test_quick_studio_does_not_import_premium_family_path() -> None:
    import investhome_api.services.creative_director.quick_studio as qs

    source = inspect.getsource(qs)
    assert "premium_studio" not in source
    assert "phase12_3_family_ingest" not in source
    assert "families_in" not in source
    assert "generate_ad_phase5" in source
    assert "revise_ad_phase5" in source


def _add_project(db, *, project_id: UUID, name: str, code: str) -> Project:
    row = Project(
        id=project_id,
        project_code=code,
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(row)
    db.flush()
    return row


def _add_asset(db, *, asset_id: UUID, project_id: UUID, filename: str, content_type: str = "image/jpeg") -> None:
    db.add(
        CreativeStudioMediaAsset(
            id=asset_id,
            filename=filename,
            content_type=content_type,
            file_size=2048,
            width=1600,
            height=1200,
            storage_provider="local",
            storage_key=f"local:{asset_id}",
            linked_project_id=project_id,
        )
    )
    db.flush()


def test_quick_projects_put_temple_first(db) -> None:
    uni = UUID("139a19cd-91a6-4d09-bc95-82bf0284154c")
    _add_project(db, project_id=UUID(TEMPLE_PROJECT_ID), name="The Temple", code="PRJ-TEMP-001")
    _add_project(db, project_id=uni, name="UniLoft", code="PRJ-UNIL-002")
    payload = list_quick_projects(db)
    assert payload["items"][0]["id"] == TEMPLE_PROJECT_ID
    assert payload["items"][0]["name"] == "The Temple"
    assert payload["items"][0]["live"] is True
    names = [item["name"] for item in payload["items"]]
    assert "UniLoft" in names
    blob = str(payload)
    assert "acquisition_price" not in blob
    assert "675.000" not in blob


def test_temple_real_assets_resolve_with_human_labels(db) -> None:
    _add_project(db, project_id=UUID(TEMPLE_PROJECT_ID), name="The Temple", code="PRJ-TEMP-001")
    _add_asset(
        db,
        asset_id=UUID(LOCKED_LOGO_ASSET_ID),
        project_id=UUID(TEMPLE_PROJECT_ID),
        filename="temple-logo.svg",
        content_type="image/svg+xml",
    )
    _add_asset(
        db,
        asset_id=UUID("7346e259-f999-4fbb-a8d5-63708d4e0c81"),
        project_id=UUID(TEMPLE_PROJECT_ID),
        filename="IH_DC_TMP_001_Render_Exterior_Day_003.jpg",
    )
    _add_asset(
        db,
        asset_id=UUID(TEMPLE_LIVING_ID),
        project_id=UUID(TEMPLE_PROJECT_ID),
        filename="IH_DC_TMP_001_Render_Living_Room_001.jpg",
    )
    detail = get_quick_project(db, UUID(TEMPLE_PROJECT_ID))
    assert detail["logo_resolved"] is True
    assert detail["ready"] is True
    assert detail["project_reality_firewall"] == "ACTIVE"
    labels = [photo["label"] for photo in detail["photos"]]
    assert "Dış cephe — gündüz 003" in labels
    assert "İç mekan — oturma odası" in labels
    for photo in detail["photos"]:
        assert photo["id"] in APPROVED_TEMPLE_PHOTO_IDS
        assert photo["id"] not in photo["label"]
        assert "drive" not in photo["label"].lower()
    photos = resolved_photos(db, UUID(TEMPLE_PROJECT_ID))
    assert all(item["id"] != LOCKED_LOGO_ASSET_ID for item in photos)


def test_quick_get_does_not_generate(db, monkeypatch) -> None:
    calls: list[str] = []

    def boom(*_args, **_kwargs):
        calls.append("generate")
        raise RuntimeError("no generate")

    monkeypatch.setattr(
        "investhome_api.services.creative_director.quick_studio.generate_ad_phase5",
        boom,
    )
    _add_project(db, project_id=UUID(TEMPLE_PROJECT_ID), name="The Temple", code="PRJ-TEMP-001")
    get_quick_project(db, UUID(TEMPLE_PROJECT_ID))
    list_quick_projects(db)
    assert calls == []


def test_quick_routes_registered() -> None:
    from investhome_api.main import app

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/ai/creative-studio/quick/projects" in paths
    assert "/ai/creative-studio/quick/generate" in paths
    assert "/ai/creative-studio/premium-campaigns" in paths


def test_quick_does_not_invent_commercial_numbers() -> None:
    assert _needs_missing_fact("Fiyatı da yaz") is True
    assert _needs_missing_fact("Lansman avantajını anlatan şık bir Instagram reklamı hazırla.") is False
    assert _needs_missing_fact("Washington D.C. vurgusu güçlü olsun.") is False
    assert _needs_missing_fact("Fiyatı 450.000 USD olarak yaz.") is False
    assert _needs_missing_fact(
        "The Temple için modern, prestijli ve yatırım odaklı bir Instagram reklamı hazırla. "
        "Gerçek proje görsellerini ve The Temple logosunu kullan. "
        "Tasarım sade ve premium görünsün. "
        "Herhangi bir fiyat veya finansal veri uydurma."
    ) is False
    assert _needs_missing_fact("Herhangi bir fiyat uydurma.") is False
    assert _needs_missing_fact("Finansal veri kullanma.") is False
    assert _needs_missing_fact("Getiri oranı yazma.") is False
    assert _needs_missing_fact("Yatırım odaklı reklam hazırla.") is False
    assert _needs_missing_fact("Lansman avantajını anlat.") is False
    assert _needs_missing_fact("Fiyatı 675.000 USD yaz.") is False
    assert _needs_missing_fact("%35 lansman avantajını yaz.") is False
