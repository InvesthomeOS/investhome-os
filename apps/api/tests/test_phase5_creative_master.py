"""Phase 5.1E — AI graphic design on an immutable project photograph.

OS compositor is not the designer. R1/R2 overlay history must stay untouched.
"""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_master import (
    WORKFLOW_ID_51E,
    critique_rejected,
    generate_creative_master_4x5,
    graphic_design_prompt,
    normalize_composition_plan,
    plan_to_generation_brief,
)
from investhome_api.services.creative_director.phase5_creative_overlay import (
    PARENT_51D_ASSET_ID,
    PARENT_R1_ASSET_ID,
    WORKFLOW_ID_51D,
    WORKFLOW_ID_51D_R1,
    WORKFLOW_ID_51D_R2,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)

PARENT_R2_ASSET_ID = "05f2b004-a672-41a1-9faa-81529e074418"


def _png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _day004_like() -> Image.Image:
    im = Image.new("RGB", (2268, 1234), (176, 196, 214))
    draw = ImageDraw.Draw(im)
    draw.rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    draw.rectangle((1680, 80, 1820, 280), fill=(208, 198, 180))
    return im


def _sample_plan(**overrides) -> dict:
    plan = {
        "plan_id": "plan-a",
        "concept": "sky-left editorial lockup, architecture remains hero",
        "visual_story": "read headline in quiet sky, then commercial group on quiet ground",
        "focal_point": "gothic spire",
        "protected_architecture": "spire and façade stay uncovered",
        "headline_strategy": "quiet upper-left sky, clear of the spire",
        "commercial_information_strategy": "one lockup in lower quiet ground, not five widgets",
        "cta_strategy": "belongs to the commercial lockup",
        "logo_strategy": "top-left reservation, empty for real SVG",
        "typography_strategy": "campaign hierarchy by proportion, not giant type",
        "contrast_strategy": "local tonal fields only",
        "negative_space_strategy": "keep the tower column empty",
        "depth_strategy": "subtle local contrast behind type",
        "graphic_language": "restrained editorial rules, no badges",
        "color_language": "navy / gold / ivory",
        "reading_order": "headline → price → unit/%35 → CTA",
        "element_relationships": "commercial facts share one axis",
        "regions": {
            "spire": {"x": 0.30, "y": 0.02, "w": 0.22, "h": 0.58},
            "architecture": {"x": 0.18, "y": 0.28, "w": 0.52, "h": 0.50},
            "headline": {"x": 0.04, "y": 0.10, "w": 0.24, "h": 0.12},
            "commercial": {"x": 0.04, "y": 0.62, "w": 0.30, "h": 0.22},
            "cta": {"x": 0.04, "y": 0.86, "w": 0.28, "h": 0.08},
            "logo": {"x": 0.04, "y": 0.03, "w": 0.20, "h": 0.07},
        },
        "safe_regions": [{"x": 0.02, "y": 0.04, "w": 0.26, "h": 0.22}],
        "forbidden_regions": [{"x": 0.30, "y": 0.02, "w": 0.22, "h": 0.58}],
        "mode": "vision",
    }
    plan.update(overrides)
    return plan


def _overlay_png() -> bytes:
    im = Image.new("RGB", CANVAS_4X5, (255, 0, 255))
    ImageDraw.Draw(im).rectangle((40, 80, 280, 220), fill=(201, 168, 92))
    return _png(im)


def test_plan_is_created_before_graphic_generation() -> None:
    plan = normalize_composition_plan(_sample_plan())
    assert plan["created_before_graphic_generation"] is True
    assert plan["schema"] == "CreativeCompositionPlanV1"
    brief = plan_to_generation_brief(plan, dict(REQUIRED_FACTS))
    folded = brief.casefold()
    assert "protected architecture" in folded
    assert "commercial system" in folded
    assert "spire" in folded
    prompt = graphic_design_prompt(dict(REQUIRED_FACTS), plan, chroma=False)
    folded_p = prompt.casefold()
    assert "luxury ad overlay" not in folded_p
    assert "right-side type stack" in folded_p
    assert "bottom fact strip" in folded_p
    assert "do not draw buildings" in folded_p
    assert "dejavu" not in folded_p
    assert "images/edits" not in folded_p
    assert REQUIRED_FACTS["headline"] in prompt
    assert REQUIRED_FACTS["list_price"] in prompt
    assert REQUIRED_FACTS["cta"] in prompt


def test_critique_rejects_r1_r2_failure_modes() -> None:
    assert critique_rejected({"pass": True}) is False
    assert critique_rejected({"pass": False}) is True
    assert critique_rejected({"headline_intersects_spire": True}) is True
    assert critique_rejected({"price_dominates": True}) is True
    assert critique_rejected({"text_on_photo": True}) is True
    assert critique_rejected({"dashboard_cards": True}) is True
    assert critique_rejected({"giant_opaque_panel": True}) is True
    assert critique_rejected({"missing_required": ["ALIRKEN KAZAN"]}) is True
    assert critique_rejected({"pass": None, "failures": []}) is False


def _history_ctx() -> dict:
    return {
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
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {
                "5765e350-06f5-45d6-9e70-a63cd4dd2072": {
                    "master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"
                }
            },
            "photo_foundation_tests": [{"workflow": "phase5_1b_photo_foundation", "keep": True}],
            "creative_design_tests": [{"workflow": "phase5_1c_creative_design", "keep": True}],
            "creative_overlay_tests": [
                {"workflow": WORKFLOW_ID_51D, "final_asset_id": PARENT_51D_ASSET_ID, "keep": True},
                {"workflow": WORKFLOW_ID_51D_R1, "final_asset_id": PARENT_R1_ASSET_ID, "keep": True},
                {"workflow": WORKFLOW_ID_51D_R2, "final_asset_id": PARENT_R2_ASSET_ID, "keep": True},
            ],
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }


def test_master_generate_does_not_touch_history_or_use_edits(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_master as master

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51E-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    ctx = _history_ctx()
    overlay_before = list((ctx["phase5"].get("creative_overlay_tests") or []))
    photo_before = list(ctx["phase5"]["photo_foundation_tests"])
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1e test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))
    order: list[str] = []
    edit_calls: list[str] = []

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    def fake_plan(*_a, **_k):
        order.append("plan")
        return normalize_composition_plan(_sample_plan()), 0

    def fake_layer(**k):
        order.append("layer")
        assert k["plan"]["created_before_graphic_generation"] is True
        return _overlay_png(), "generations_magenta_chroma", 1

    def boom_edit(*_a, **_k):
        edit_calls.append("edit")
        raise AssertionError("images/edits must not be used")

    monkeypatch.setattr(master, "_read_bytes", fake_read)
    monkeypatch.setattr(master, "request_composition_plan", fake_plan)
    monkeypatch.setattr(master, "request_graphic_layer", fake_layer)
    monkeypatch.setattr(
        master,
        "request_design_critique",
        lambda **k: ({"pass": True, "mode": "mock", "failures": []}, 0),
    )
    monkeypatch.setattr(master, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(master, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        master,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="medium", base_url="https://api.openai.com/v1"),
    )
    monkeypatch.setattr(master, "edit_image", boom_edit, raising=False)

    result = generate_creative_master_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert order == ["plan", "layer"]
    assert edit_calls == []
    assert result["workflow"] == WORKFLOW_ID_51E
    assert result["architecture_generation_used"] is False
    assert result["os_compositor_primary_designer"] is False
    assert result["plan_executed_by_os"] is False
    assert result["gpt_image_edit_calls"] == 0
    assert result["final_size"] == list(CANVAS_4X5)
    assert result["source_asset_id"] == LOCKED_HERO_ASSET_ID
    assert result["logo_asset_id"] == LOCKED_LOGO_ASSET_ID
    assert result["design_retry_count"] == 0
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("photo_foundation_tests") == photo_before
    assert phase5.get("creative_overlay_tests") == overlay_before
    masters = list(phase5.get("creative_master_tests") or [])
    assert any(t.get("workflow") == WORKFLOW_ID_51E for t in masters)
    assert "images" not in masters[0]
    db.rollback()
    db.close()


def test_rejected_critique_triggers_new_composition_not_nudge(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_master as master

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51ER-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1e retry test",
        context_json=_history_ctx(),
    )
    db.add(row)
    db.flush()
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))
    plans: list[str] = []
    layers: list[str] = []

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    def fake_plan(*_a, critique_feedback=None, **_k):
        if critique_feedback:
            plans.append("retry")
            return normalize_composition_plan(_sample_plan(plan_id="plan-b", concept="new lower-left lockup")), 0
        plans.append("first")
        return normalize_composition_plan(_sample_plan()), 0

    def fake_layer(**k):
        layers.append(str((k.get("plan") or {}).get("plan_id")))
        return _overlay_png(), "generations_magenta_chroma", 1

    critiques = iter(
        [
            ({"pass": False, "headline_intersects_spire": True, "failures": ["headline_intersects_spire"]}, 0),
            ({"pass": True, "mode": "mock", "failures": []}, 0),
        ]
    )

    monkeypatch.setattr(master, "_read_bytes", fake_read)
    monkeypatch.setattr(master, "request_composition_plan", fake_plan)
    monkeypatch.setattr(master, "request_graphic_layer", fake_layer)
    monkeypatch.setattr(master, "request_design_critique", lambda **k: next(critiques))
    monkeypatch.setattr(master, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(master, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        master,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="medium", base_url="https://api.openai.com/v1"),
    )

    result = generate_creative_master_4x5(db, user, row, language="tr")
    assert plans == ["first", "retry"]
    assert layers == ["plan-a", "plan-b"]
    assert result["design_retry_count"] == 1
    assert result["creative_composition_plan"]["plan_id"] == "plan-b"
    assert result["provider_call_count"] >= 2
    db.rollback()
    db.close()


def test_optional_source_and_logo_asset_ids(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_master as master

    other_photo = str(uuid4())
    other_logo = str(uuid4())
    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51EO-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1e reusable contract",
        context_json=_history_ctx(),
    )
    db.add(row)
    db.flush()
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))
    seen: list[str] = []

    def fake_read(_db, asset_id):
        seen.append(str(asset_id))
        if str(asset_id) == other_logo:
            return logo
        return hero

    monkeypatch.setattr(master, "_read_bytes", fake_read)
    monkeypatch.setattr(master, "request_composition_plan", lambda *a, **k: (normalize_composition_plan(_sample_plan()), 0))
    monkeypatch.setattr(master, "request_graphic_layer", lambda **k: (_overlay_png(), "generations_magenta_chroma", 1))
    monkeypatch.setattr(
        master,
        "request_design_critique",
        lambda **k: ({"pass": True, "mode": "mock", "failures": []}, 0),
    )
    monkeypatch.setattr(master, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(master, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        master,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="medium", base_url="https://api.openai.com/v1"),
    )

    result = generate_creative_master_4x5(
        db,
        user,
        row,
        language="tr",
        source_asset_id=other_photo,
        logo_asset_id=other_logo,
        source_filename="approved-project-hero.jpg",
    )
    assert other_photo in seen
    assert other_logo in seen
    assert result["source_asset_id"] == other_photo
    assert result["logo_asset_id"] == other_logo
    assert result["reusable_contract"]["source_asset_parameter"] is True
    db.rollback()
    db.close()
