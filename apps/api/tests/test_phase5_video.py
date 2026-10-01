"""Phase 5.2 — Reels workflow. Does not fake video when the provider is missing."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID, uuid4

from investhome_api.schemas.creative_director import CreativeDirectorReviseRequest
from investhome_api.services.creative_director.phase5_video import (
    apply_revision_to_plan,
    build_video_creative_plan,
    discover_video_capability,
    interpret_video_revision,
    video_qa,
)
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    interpret_user_turn,
    revise_ad_phase5,
)


def _approved_session(master_asset: UUID, format_family_id: str) -> tuple[str, dict]:
    session_id = str(uuid4())
    version_id = str(uuid4())
    master_id = "5765e350-06f5-45d6-9e70-a63cd4dd2072"
    return session_id, {
        "session_id": session_id,
        "project_id": TEMPLE_PROJECT_ID,
        "status": "FORMAT_ADAPTATION_READY",
        "current_version_id": version_id,
        "approved_version_id": version_id,
        "format_family_id": format_family_id,
        "user_request": "The Temple için ALIRKEN KAZAN. Fiyat 675.000 USD.",
        "creative_type": "social_advertisement",
        "target_format": "instagram_feed_4:5",
        "versions": [
            {
                "version_id": version_id,
                "asset_id": str(master_asset),
                "version_number": 3,
                "project_asset_ids": [LOCKED_HERO_ASSET_ID],
                "logo_asset_id": LOCKED_LOGO_ASSET_ID,
                "creative_context": {
                    "required_factual_content": {
                        "headline": "ALIRKEN KAZAN",
                        "unit": "2+1",
                        "unit_label": "DAİRE",
                        "list_price": "675.000 USD",
                        "discount": "%35",
                        "discount_label": "LANSMAN AVANTAJI",
                        "cta": "PROJEYİ KEŞFET",
                    }
                },
            }
        ],
        "approved_master": {
            "master_id": master_id,
            "session_id": session_id,
            "approved_version_id": version_id,
            "master_asset_id": str(master_asset),
            "logo_asset": LOCKED_LOGO_ASSET_ID,
            "base_format": "instagram_feed_4:5",
            "format_family_id": format_family_id,
            "creative_identity": {"concept": "ALIRKEN KAZAN"},
        },
        "format_adaptation_started": True,
        "video_started": False,
        "publishing_started": False,
        "next_hooks": {"format_adaptation": "completed", "video": "unstarted", "publishing": "unstarted"},
    }


def test_reels_intents() -> None:
    assert interpret_user_turn("Bundan bir Reels video hazırla.")["intent"] == "VIDEO_GENERATE"
    assert interpret_user_turn(
        "Videoyu biraz daha yavaş ve premium yap. 675.000 USD fiyatı ekranda biraz daha uzun tut."
    )["intent"] == "VIDEO_REVISE"
    assert interpret_user_turn("Tamam, videoyu onayla.")["intent"] == "VIDEO_APPROVE"


def test_video_provider_is_not_connected() -> None:
    cap = discover_video_capability()
    assert cap["usable"] is False
    assert "video_generate" in cap["missing_capabilities"]
    assert cap["provider"] == "video_stub"


def test_plan_inherits_approved_master_price_not_v2() -> None:
    context = {
        "approved_campaign_content": {
            "headline": "ALIRKEN KAZAN",
            "unit": "2+1",
            "unit_label": "DAİRE",
            "list_price": "675.000 USD",
            "discount": "%35",
            "discount_label": "LANSMAN AVANTAJI",
            "cta": "PROJEYİ KEŞFET",
        },
        "approved_project_assets": [{"asset_id": LOCKED_HERO_ASSET_ID}],
        "approved_master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485",
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "target_duration_seconds": 12,
    }
    plan = build_video_creative_plan(context)
    assert plan["locked_facts"]["list_price"] == "675.000 USD"
    assert "438.750" not in str(plan)
    assert plan["not_a_fixed_template"] is True
    assert "attention" in plan["scene_progression"]
    rev = interpret_video_revision(
        "Videoyu biraz daha yavaş ve premium yap. 675.000 USD fiyatı ekranda biraz daha uzun tut. Diğer tasarım kimliğini koru."
    )
    assert "pace_slower" in rev["requested_changes"]
    assert rev["price_hold"] == "longer"
    updated = apply_revision_to_plan(plan, rev)
    assert updated["approx_duration_seconds"] > plan["approx_duration_seconds"]
    commercial = next(b for b in updated["beats"] if b["beat"] == "commercial")
    original = next(b for b in plan["beats"] if b["beat"] == "commercial")
    assert commercial["approx_seconds"] > original["approx_seconds"]


def test_video_qa_rejects_old_price_and_missing_file() -> None:
    facts = {"headline": "ALIRKEN KAZAN", "list_price": "438.750 USD", "cta": "PROJEYİ KEŞFET"}
    qa = video_qa(
        content=None,
        declared={"width": 1080, "height": 1920, "duration": 12, "logo_asset_id": LOCKED_LOGO_ASSET_ID},
        facts=facts,
        source_asset_ids=[LOCKED_HERO_ASSET_ID],
    )
    assert qa["failed"] is True
    assert qa["content_integrity"] == "fail"


def test_phase52_blocks_without_faking_video_and_does_not_touch_master(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_workflow as wf

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"PH52-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    master_asset = uuid4()
    family_id = "2f29711d-285c-4e6d-a1b8-5b058eeb58b4"
    session_id, session = _approved_session(master_asset, family_id)
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {
            "current_version": 2,
            "current_cover_asset_id": PRODUCTION_COVER_V2,
            "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        },
        "phase5": {
            "current_session_id": session_id,
            "sessions": {session_id: session},
            "format_families": {family_id: {"family_id": family_id, "master_asset_id": str(master_asset)}},
            "approved_masters": {session["approved_master"]["master_id"]: session["approved_master"]},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="placeholder",
        context_json=ctx,
        status="ready",
    )
    db.add(row)
    db.flush()

    def fake_prep(db, campaign_id, body):
        return (
            row,
            dict(row.context_json or {}),
            {},
            {},
            {},
            "brief",
            False,
            [],
            "tr",
            "portrait",
            "4:5",
            UUID(LOCKED_HERO_ASSET_ID),
            UUID(LOCKED_LOGO_ASSET_ID),
            {"asset_id": LOCKED_HERO_ASSET_ID},
            {"asset_id": LOCKED_LOGO_ASSET_ID},
            {},
            [],
            {},
            {},
        )

    monkeypatch.setattr(wf, "_prepare_campaign_ad_context", fake_prep)
    out = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction="Bundan bir Reels video hazırla.",
            current_final_asset_id=master_asset,
        ),
    )
    assert out.quality_guard["video_provider_missing"] is True
    assert out.quality_guard["approved_master_changed"] is False
    assert out.quality_guard["publishing_started"] is False
    assert out.provider_call_count == 0
    db.refresh(row)
    final = dict(row.context_json or {})
    assert final["current_cover_asset_id"] == PRODUCTION_COVER_V2
    sess = final["phase5"]["sessions"][session_id]
    assert sess["approved_master"]["master_asset_id"] == str(master_asset)
    assert sess["format_family_id"] == family_id
    video = final["phase5"]["videos"][sess["current_video_id"]]
    assert video["status"] == "PROVIDER_MISSING"
    v1 = video["versions"][0]
    assert v1["asset_id"] is None
    assert v1["video_plan"]["locked_facts"]["list_price"] == "675.000 USD"

    rev = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction="Videoyu biraz daha yavaş ve premium yap. 675.000 USD fiyatı ekranda biraz daha uzun tut. Diğer tasarım kimliğini koru.",
            current_final_asset_id=master_asset,
        ),
    )
    assert rev.revision_intents == ["VIDEO_REVISE"]
    db.refresh(row)
    video2 = dict(row.context_json["phase5"]["videos"][sess["current_video_id"]])
    assert len(video2["versions"]) == 2
    assert video2["versions"][1]["parent_version_id"] == video2["versions"][0]["version_id"]
    assert video2["versions"][1]["asset_id"] is None
    assert deepcopy(row.context_json)["current_cover_asset_id"] == PRODUCTION_COVER_V2
    db.rollback()
    db.close()
