"""Phase 5.0 — real AI creative workflow: session, version, revision, approval."""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image

from investhome_api.schemas.creative_director import CreativeDirectorGenerateAdRequest
from investhome_api.schemas.gpt_image_design import (
    GptImageDesignResponse,
    GptImageOutput,
    GptImageSourceImage,
)
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    WORKFLOW_ID,
    interpret_revision,
    interpret_user_turn,
    revision_drift_qa,
    should_route_generate_to_phase5,
    should_route_revise_to_phase5,
)


def _png(color: tuple[int, int, int]) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (64, 80), color).save(buf, format="PNG")
    return buf.getvalue()


def test_generate_routes_only_when_workflow_phase5() -> None:
    assert should_route_generate_to_phase5(CreativeDirectorGenerateAdRequest()) is False
    assert should_route_generate_to_phase5(CreativeDirectorGenerateAdRequest(workflow="phase5")) is True
    assert (
        should_route_generate_to_phase5(
            CreativeDirectorGenerateAdRequest(workflow="phase5", production_mode="golden_native_v1")
        )
        is False
    )


def test_approval_and_revision_interpreter() -> None:
    assert interpret_user_turn("Tamam, bunu onayla.")["intent"] == "APPROVE"
    assert interpret_user_turn("Diğer ölçülere uyarla")["intent"] == "FORMAT_ADAPTATION_ALL"
    assert interpret_user_turn("Bundan bir Reels video hazırla.")["intent"] == "VIDEO_GENERATE"
    assert interpret_user_turn("Tamam, videoyu onayla.")["intent"] == "VIDEO_APPROVE"
    assert interpret_user_turn("Videoyu biraz daha yavaş ve premium yap.")["intent"] == "VIDEO_REVISE"
    plan = interpret_revision(
        "675.000 USD fiyatı 438.750 USD olarak değiştir. Başka hiçbir şeyi değiştirme."
    )
    assert plan["text_change_request"]["list_price"] == "438.750 USD"
    assert plan["scope"] == "local"
    assert "composition" in plan["explicitly_locked_content"]
    emph = interpret_revision("%35 lansman avantajını biraz daha belirgin yap. Diğer tasarımı koru.")
    assert "style_emphasis_discount" in emph["requested_changes"]


def test_revision_drift_qa_flags_unrelated_redesign() -> None:
    parent = Image.new("RGB", (200, 250), (40, 50, 60))
    close = Image.new("RGB", (200, 250), (42, 52, 62))
    other = Image.new("RGB", (200, 250), (200, 20, 20))
    local = {"scope": "local", "explicitly_locked_content": ["composition"]}
    ok = revision_drift_qa(parent, close, local)
    bad = revision_drift_qa(parent, other, local)
    assert ok["unexpected_redesign"] is False
    assert ok["revision_fidelity_score"] > 0.5
    assert bad["unexpected_redesign"] is True


def test_phase5_generate_revise_approve_does_not_touch_production_v2(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.schemas.creative_director import CreativeDirectorReviseRequest
    from investhome_api.services.creative_director import phase5_workflow as wf
    from investhome_api.services.creative_director.phase5_workflow import generate_ad_phase5, revise_ad_phase5

    db = SessionLocal()
    existing = db.get(Project, UUID(TEMPLE_PROJECT_ID))
    if existing is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"PH5-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    project_id = UUID(TEMPLE_PROJECT_ID)
    user = db.query(User).first()
    assert user is not None
    v1_id, v2_id, v3_id = uuid4(), uuid4(), uuid4()
    hero_id = UUID(LOCKED_HERO_ASSET_ID)
    logo_id = UUID(LOCKED_LOGO_ASSET_ID)
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
    }
    row = CreativeDirectorCampaign(
        linked_project_id=project_id,
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
            "The Temple için ALIRKEN KAZAN",
            False,
            [],
            "tr",
            "portrait",
            "4:5",
            hero_id,
            logo_id,
            {"asset_id": str(hero_id), "filename": "IH_DC_TMP_001_Render_Exterior_Day_004.jpg"},
            {"asset_id": str(logo_id), "filename": "logo.svg"},
            {"headline": "ALIRKEN KAZAN", "cta": "PROJEYİ KEŞFET"},
            ["675.000 USD"],
            {},
            {},
        )

    outputs = iter([v1_id, v2_id, v3_id])

    def fake_generate(db, user, body):
        oid = next(outputs)
        assert body.builder_context["finished_ad"] is True
        assert body.builder_context["phase5_workflow"] is True
        assert "top panel" not in (body.instruction or "").lower()
        if body.builder_context.get("revision_visual_reference_asset_id"):
            assert body.builder_context["revision_route"] == "CREATIVE_RECOMPOSE"
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id=str(body.session_id or "s"),
            linked_project_id=project_id,
            generation_context_id=str(uuid4()),
            aspect_ratio="4:5",
            format_preset="portrait",
            source_image=GptImageSourceImage(
                asset_id=hero_id,
                filename="IH_DC_TMP_001_Render_Exterior_Day_004.jpg",
                content_type="image/jpeg",
                role="source",
            ),
            outputs=[
                GptImageOutput(
                    local_asset_id=oid,
                    local_asset_url=f"/creative-studio/media/assets/{oid}/content",
                )
            ],
            provider_call_count=1,
            latency_ms=9,
        )

    monkeypatch.setattr(wf, "_prepare_campaign_ad_context", fake_prep)
    monkeypatch.setattr(wf, "generate_gpt_image_creatives", fake_generate)
    monkeypatch.setattr(
        wf,
        "provider_capability_record",
        lambda: {
            "provider": "gpt-image",
            "model": "gpt-image-2",
            "available": True,
            "usable_for_project_locked": True,
            "reference_image_support": True,
            "revision_reference_workflow": True,
            "project_asset_fidelity": "edits_with_locked_project_references",
            "reason": None,
        },
    )
    monkeypatch.setattr(wf, "assert_image_provider_available", lambda route: None)
    monkeypatch.setattr(
        wf,
        "route_ad_social_image",
        lambda **kwargs: type("R", (), {"to_dict": lambda self: {"provider_id": "gpt_image", "model": "gpt-image-2"}})(),
    )
    pngs = [_png((10, 20, 30)), _png((12, 22, 32)), _png((14, 24, 34))]
    monkeypatch.setattr(wf, "_read_bytes", lambda db, asset_id: pngs[0])

    body = CreativeDirectorGenerateAdRequest(
        workflow="phase5",
        user_request=(
            "The Temple için ALIRKEN KAZAN konseptinde premium bir Instagram reklamı hazırla. "
            "2+1 daire. Fiyat 675.000 USD. Lansman avantajı %35. CTA: PROJEYİ KEŞFET."
        ),
    )
    gen = generate_ad_phase5(db, user, row.id, body)
    assert gen.quality_guard["workflow"] == WORKFLOW_ID
    assert gen.quality_guard["phase4_renderer_used"] is False
    assert str(gen.interior_asset_id) == LOCKED_HERO_ASSET_ID
    assert str(gen.logo_asset_id) == LOCKED_LOGO_ASSET_ID
    db.refresh(row)
    ctx1 = dict(row.context_json or {})
    assert ctx1["current_cover_asset_id"] == PRODUCTION_COVER_V2
    assert ctx1["master_creative"]["current_version"] == 2
    session = ctx1["phase5"]["sessions"][ctx1["phase5"]["current_session_id"]]
    assert session["versions"][0]["generation_type"] == "INITIAL_GENERATION"
    assert should_route_revise_to_phase5(ctx1, UUID(session["versions"][0]["asset_id"])) is True

    monkeypatch.setattr(wf, "_read_bytes", lambda db, asset_id: pngs[1] if str(asset_id) == str(v2_id) else pngs[0])
    rev = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction="675.000 USD fiyatı 438.750 USD olarak değiştir. Başka hiçbir şeyi değiştirme.",
            current_final_asset_id=v1_id,
        ),
    )
    assert rev.quality_guard["version_number"] == 2
    assert rev.previous_asset_id == v1_id
    assert rev.interpreted_plan["text_change_request"]["list_price"] == "438.750 USD"
    db.refresh(row)
    assert row.context_json["current_cover_asset_id"] == PRODUCTION_COVER_V2

    monkeypatch.setattr(wf, "_read_bytes", lambda db, asset_id: pngs[2] if str(asset_id) == str(v3_id) else pngs[1])
    rev2 = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction="%35 lansman avantajını biraz daha belirgin yap. Diğer tasarımı koru.",
            current_final_asset_id=v2_id,
        ),
    )
    assert rev2.quality_guard["version_number"] == 3
    assert str(rev2.previous_asset_id) == str(v2_id)

    approved = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(instruction="Tamam, bunu onayla.", current_final_asset_id=v3_id),
    )
    assert approved.provider_call_count == 0
    assert approved.quality_guard["session_status"] == "APPROVED"
    assert approved.quality_guard["format_adaptation_started"] is False
    assert approved.quality_guard["video_started"] is False
    db.refresh(row)
    final_ctx = dict(row.context_json or {})
    assert final_ctx["current_cover_asset_id"] == PRODUCTION_COVER_V2
    assert final_ctx["master_creative"]["current_version"] == 2
    session = final_ctx["phase5"]["sessions"][final_ctx["phase5"]["current_session_id"]]
    assert session["status"] == "APPROVED"
    assert session["approved_master"]["approved_version_id"] == session["current_version_id"]
    assert len(session["versions"]) == 3
    copied = deepcopy(final_ctx)
    assert copied["current_cover_asset_id"] == PRODUCTION_COVER_V2
    db.rollback()
    db.close()
