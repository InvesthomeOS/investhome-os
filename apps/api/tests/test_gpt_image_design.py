"""GPT Image SMB engine tests — mock OpenAI HTTP. Do not spend credits."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.services.gpt_image_design.brief import (
    build_shared_brief,
    render_project_edit_prompt,
)
from investhome_api.services.gpt_image_design.client import (
    edits_url,
    generations_url,
    reset_provider_call_count,
)
from investhome_api.services.gpt_image_design.config import DEFAULT_MODEL
from investhome_api.services.social_design_engine.copy_director import CopyDirection, CopyPackage
from investhome_api.services.social_design_engine.creative_director import CreativeConcept
from investhome_api.services.social_design_engine.generation import GenerationIntent
from investhome_api.services.social_design_engine.marketing_strategist import MarketingStrategy
from investhome_api.services.social_design_engine.project_knowledge import ProjectKnowledgePackage
from investhome_api.services.social_design_engine.verified_facts import (
    CampaignIntelligencePackage,
    VerifiedFact,
)
from investhome_api.services.storage.factory import get_storage_provider

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")
EDITS_URL = edits_url("https://api.openai.com/v1")
GENERATIONS_URL = generations_url("https://api.openai.com/v1")


def _png_bytes(
    width: int = 48,
    height: int = 48,
    color: tuple[int, int, int] = (40, 80, 120),
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


@pytest.fixture
def db_session(client) -> Session:
    return _db()


@pytest.fixture(autouse=True)
def _gpt_image_unit_defaults(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if request.node.get_closest_marker("gpt_image_live"):
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
        return
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("GPT_IMAGE_ENABLED", "false")
    monkeypatch.setenv("GPT_IMAGE_MODEL", DEFAULT_MODEL)
    monkeypatch.setenv("GPT_IMAGE_QUALITY", "medium")
    monkeypatch.setenv("AI_PROVIDER", "local")
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    reset_provider_call_count()
    yield
    get_settings.cache_clear()
    get_storage_provider.cache_clear()


def _create_project(
    db: Session,
    name: str = "Temple Residences",
    *,
    project_id: UUID | None = None,
) -> Project:
    existing = db.get(Project, project_id) if project_id else None
    if existing is not None:
        return existing
    project = Project(
        id=project_id or uuid4(),
        project_code=f"PRJ-GPT-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
        city="Washington",
        country="US",
        address="1610 Columbia Rd NW",
        total_units=120,
    )
    db.add(project)
    db.flush()
    return project


def _upload_hero(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    project_id: UUID,
    *,
    filename: str = "temple-aerial-exterior.png",
    tags: str = "temple,aerial,exterior,hero",
) -> dict:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "gpt-image-media"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    files = {"file": (filename, io.BytesIO(_png_bytes(64, 64)), "image/png")}
    data = {
        "tags": tags,
        "linked_project_id": str(project_id),
    }
    response = client.post("/creative-studio/media/upload", files=files, data=data)
    assert response.status_code == 201, response.text
    return response.json()


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_data: dict | None = None,
        content: bytes = b"",
    ) -> None:
        self.status_code = status_code
        self._json = json_data
        self.content = content

    def json(self) -> dict:
        if self._json is None:
            raise ValueError("no json")
        return self._json


def test_status_unavailable_without_key(client: TestClient) -> None:
    resp = client.get("/ai/creative-studio/social/gpt-image/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["available"] is False
    assert body["configured"] is False
    assert body["provider"] == "gpt-image"
    assert body["model"] == DEFAULT_MODEL
    assert body["reason"] in {"ai_api_key_missing", "gpt_image_disabled"}
    assert "sk-" not in str(body).lower()


def test_generate_unavailable_does_not_mock_success(
    client: TestClient,
    db_session: Session,
) -> None:
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    resp = client.post(
        "/ai/creative-studio/social/gpt-image/generate",
        json={
            "linked_project_id": str(temple.id),
            "instruction": "The Temple projesinin lokasyon avantajını anlatan premium Instagram postu hazırla.",
            "design_provider": "gpt-image",
            "campaign_mode": "project",
            "format_preset": "portrait",
        },
    )
    assert resp.status_code == 503, resp.text
    assert "gpt image" in resp.json()["detail"].lower()
    assert "native" in resp.json()["detail"].lower()
    assert resp.json().get("outputs") is None or "outputs" not in resp.json()


def test_native_endpoint_rejects_gpt_image_provider(
    client: TestClient,
    db_session: Session,
) -> None:
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(temple.id),
            "instruction": "Create an Instagram portrait location post.",
            "mode": "create",
            "design_provider": "gpt-image",
            "draft": {"posts": [], "selected_post_id": None},
        },
    )
    assert resp.status_code == 409, resp.text
    detail = str(resp.json().get("detail") or "").lower()
    assert "gpt-image" in detail
    assert "native generation was not invoked" in detail


def test_edits_without_source_does_not_switch_to_generations() -> None:
    from investhome_api.services.gpt_image_design.client import (
        GptImageProviderError,
        edit_image,
    )

    with pytest.raises(GptImageProviderError) as exc:
        edit_image(
            api_key="test-key",
            model=DEFAULT_MODEL,
            prompt="test",
            images=[],
            size="1088x1360",
            quality="medium",
        )
    assert exc.value.status_code == 422
    assert "text-to-image was not used" in str(exc.value.detail).lower()


def test_project_mode_sends_source_image_persists_and_does_not_fallback(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_API_KEY", "test-ai-api-key")
    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    monkeypatch.setenv("GPT_IMAGE_MODEL", DEFAULT_MODEL)
    monkeypatch.setenv("AI_PROVIDER", "local")
    get_settings.cache_clear()
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    asset = _upload_hero(client, tmp_path, monkeypatch, temple.id)
    _upload_hero(
        client,
        tmp_path,
        monkeypatch,
        temple.id,
        filename="IH_DC_TMP_001_Logo_Primary.png",
        tags="logo,investhome,brand,primary",
    )
    captured: dict[str, Any] = {}
    png = _png_bytes(32, 40, (12, 24, 48))

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["data"] = kwargs.get("data") or {}
        captured["files"] = kwargs.get("files") or []
        captured["headers"] = kwargs.get("headers") or {}
        captured["json"] = kwargs.get("json")
        assert url == EDITS_URL
        assert GENERATIONS_URL not in url
        return _FakeResponse(
            200,
            {
                "created": 1,
                "data": [{"b64_json": base64.b64encode(png).decode("ascii")}],
            },
        )

    post_path = "investhome_api.services.gpt_image_design.client.httpx.post"
    with patch(post_path, side_effect=fake_post):
        resp = client.post(
            "/ai/creative-studio/social/gpt-image/generate",
            json={
                "linked_project_id": str(temple.id),
                "instruction": (
                    "The Temple projesinin lokasyon avantajını anlatan premium bir "
                    "Instagram postu hazırla."
                ),
                "design_provider": "gpt-image",
                "campaign_mode": "project",
                "format_preset": "portrait",
                "aspect_ratio": "4:5",
                "language": "tr",
                "selected_asset_ids": [asset["id"]],
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "gpt-image"
    assert body["model"] == DEFAULT_MODEL
    assert body["campaign_mode"] == "project"
    assert body["endpoint"] == EDITS_URL
    assert body["aspect_ratio"] == "4:5"
    assert body["format_preset"] == "portrait"
    assert len(body["outputs"]) == 1
    assert body["outputs"][0]["local_asset_id"]
    assert body["source_image"]["asset_id"] == asset["id"]
    assert captured["url"] == EDITS_URL
    headers = captured["headers"]
    assert headers.get("Authorization") == "Bearer test-ai-api-key"
    data = captured["data"]
    assert data.get("model") == DEFAULT_MODEL
    assert data.get("size") == "1088x1360"
    files = captured["files"]
    assert files, "project mode must send source image"
    assert len(files) == 1, "GPT Image edits receive the architecture photo only; logos overlay after"
    first_name = files[0][0] if files else ""
    assert first_name == "image[]"
    prompt = str(data.get("prompt") or "")
    assert "architecture" in prompt.lower() or "building" in prompt.lower()
    assert "composited" in prompt.lower() or "do not draw" in prompt.lower() or "final composition" in prompt.lower()
    assert "do not place washington monument" in prompt.lower()
    assert "19.5%" not in prompt
    assert "27.8%" not in prompt
    assert "$1450K" not in prompt and "$1,450K" not in prompt
    brief = body.get("brief") or {}
    assert "blocked_financial_tokens" in brief
    extras = body.get("extra_images") or []
    # Project logo may be SVG composited by OS; investhome global may be absent (reported in warnings).
    output = body["outputs"][0]
    layers = output.get("layers") or []
    assert layers, "Final Composition Layer must return editable layers"
    assert output.get("composition_base_asset_id")
    assert body["provider_call_count"] == 1
    warnings = list(body.get("warnings") or []) + list(output.get("composition_warnings") or [])
    if not any(row.get("role") == "investhome_logo" for row in extras):
        assert any("Investhome global logo asset bulunamadı" in str(w) for w in warnings)


def test_gpt_image_error_is_truthful_without_native_fallback(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_API_KEY", "test-ai-api-key")
    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    get_settings.cache_clear()
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    asset = _upload_hero(client, tmp_path, monkeypatch, temple.id)

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        assert url == EDITS_URL
        return _FakeResponse(402, {"error": {"message": "Payment required", "code": "billing"}})

    post_path = "investhome_api.services.gpt_image_design.client.httpx.post"
    with patch(post_path, side_effect=fake_post):
        resp = client.post(
            "/ai/creative-studio/social/gpt-image/generate",
            json={
                "linked_project_id": str(temple.id),
                "instruction": "The Temple projesinin lokasyon avantajını anlatan premium Instagram postu hazırla.",
                "design_provider": "gpt-image",
                "campaign_mode": "project",
                "format_preset": "portrait",
                "selected_asset_ids": [asset["id"]],
            },
        )
    assert resp.status_code == 402, resp.text
    detail = str(resp.json().get("detail") or "").lower()
    assert "402" in detail
    assert "native" in detail
    assert "ideogram" in detail


def test_general_mode_uses_generations_not_edits(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_API_KEY", "test-ai-api-key")
    monkeypatch.setenv("GPT_IMAGE_ENABLED", "true")
    monkeypatch.setenv("AI_PROVIDER", "local")
    get_settings.cache_clear()
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "gpt-image-media"))
    get_storage_provider.cache_clear()
    png = _png_bytes(32, 32)
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        captured["files"] = kwargs.get("files")
        assert url == GENERATIONS_URL
        return _FakeResponse(
            200,
            {"created": 1, "data": [{"b64_json": base64.b64encode(png).decode("ascii")}]},
        )

    post_path = "investhome_api.services.gpt_image_design.client.httpx.post"
    with patch(post_path, side_effect=fake_post):
        resp = client.post(
            "/ai/creative-studio/social/gpt-image/generate",
            json={
                "instruction": "Investhome DC lifestyle investment post.",
                "design_provider": "gpt-image",
                "campaign_mode": "general",
                "format_preset": "portrait",
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["campaign_mode"] == "general"
    assert body["endpoint"] == GENERATIONS_URL
    assert body["source_image"] is None
    assert captured["url"] == GENERATIONS_URL
    assert captured.get("files") is None
    assert body["outputs"][0]["local_asset_id"]


def test_location_prompt_blocks_financial_leak_in_brief() -> None:
    intent = GenerationIntent(
        marketing_objective="location",
        audience="buyers",
        language="tr",
        asset_preference="exterior",
        cta_hint="Plan a private tour",
    )
    strategy = MarketingStrategy(
        objective="location",
        audience="buyers",
        campaign_angle="central_positioning",
        single_minded_message="A central Washington DC address.",
        supporting_evidence=["Washington DC"],
        excluded_facts=["19.5%", "27.8%"],
        tone="refined",
        neighborhood="",
        city="Washington",
        project_name="Temple Residences",
    )
    copy = CopyDirection(
        package=CopyPackage(
            eyebrow="Washington DC",
            headline="Centered in the city",
            supporting_copy="A refined address in Washington.",
            cta="Plan a private tour",
            language="en",
            tone="refined",
        )
    )
    creative = CreativeConcept(
        objective="location",
        concept="Place-led",
        visual_strategy="photography_is_hero",
        primary_message="Centered in the city",
        supporting_message="Washington DC",
        cta="Plan a private tour",
        information_to_exclude=["19.5%", "27.8%"],
        composition_strategy="LOCATION",
        tone="refined",
        text_density="sparse",
    )
    knowledge = ProjectKnowledgePackage(
        project_identity={"project_name": "Temple Residences"},
        location={"city": "Washington", "country": "US"},
    )
    intel = CampaignIntelligencePackage(
        campaign_intent="location",
        campaign_intent_confidence=0.9,
        marketing_objective="location",
        project_knowledge=knowledge,
        verified_campaign_facts=[],
        user_campaign_inputs=[],
        missing_relevant_facts=[],
        available_assets=[],
        marketing_safe_facts=[
            VerifiedFact(
                fact_id="loc1",
                category="location",
                key="city",
                value="Washington",
                display_value="Washington DC",
                source="project_db",
                source_reference="project",
                confidence=1.0,
                verified=True,
                is_financial=False,
                marketing_status="approved",
                derivation_type="canonical",
            )
        ],
        claim_eligibility_trace=[
            {"is_financial": True, "eligible": False, "value": "19.5%"},
            {"is_financial": True, "eligible": False, "value": "27.8%"},
        ],
        can_proceed=True,
        qa_trace={"blocked_financial_tokens": ["19.5%", "27.8%", "$1450K"]},
    )
    shared = build_shared_brief(
        project_name="Temple Residences",
        instruction="The Temple projesinin lokasyon avantajını anlatan premium Instagram postu hazırla.",
        intent=intent,
        strategy=strategy,
        copy_direction=copy,
        creative=creative,
        campaign_facts=[],
        intel=intel,
        source_filename="temple-aerial.png",
        language="tr",
        format_label="Instagram 4:5",
        resolution="1088x1360",
        extra_image_roles=["project_logo"],
        logo_notes=[],
        design_reference_names=["moodboard.png"],
    )
    prompt = render_project_edit_prompt(shared)
    assert "Washington" in prompt
    assert "19.5%" not in prompt
    assert "27.8%" not in prompt
    assert "$1450K" not in prompt
    assert "do not invent" in prompt.lower() or "do not invent" in str(shared).lower()
    assert "architecture" in prompt.lower()
    assert "composited" in prompt.lower() or "do not draw" in prompt.lower() or "final composition" in prompt.lower()
    assert "do not place washington monument" in prompt.lower()
    assert "walk time" in prompt.lower() or "distance" in prompt.lower() or "rasterize" in prompt.lower()
    assert "reserved" in prompt.lower() or "safe" in prompt.lower() or "do not rasterize" in prompt.lower()
    assert shared["user_campaign_facts"] == []
    assert "19.5%" in (shared.get("blocked_financial_tokens") or [])


def test_overlay_brand_lockups_pastes_real_logo_files() -> None:
    from uuid import uuid4

    from investhome_api.services.gpt_image_design.compose import overlay_brand_lockups
    from investhome_api.services.gpt_image_design.source import ResolvedSourceImage

    base = _png_bytes(200, 250, (30, 60, 90))
    project_logo = ResolvedSourceImage(
        asset_id=uuid4(),
        filename="temple-logo.png",
        content_type="image/png",
        folder_category="01_BRAND",
        tags=["logo"],
        image_bytes=_png_bytes(40, 16, (220, 40, 40)),
        width=40,
        height=16,
        role="project_logo",
    )
    ih_logo = ResolvedSourceImage(
        asset_id=uuid4(),
        filename="investhome-logo.png",
        content_type="image/png",
        folder_category="01_BRAND",
        tags=["logo", "investhome"],
        image_bytes=_png_bytes(32, 12, (20, 180, 80)),
        width=32,
        height=12,
        role="investhome_logo",
    )
    composed = overlay_brand_lockups(base, [project_logo, ih_logo])
    assert composed != base
    with Image.open(io.BytesIO(composed)) as img:
        assert img.size == (200, 250)
        sample = img.convert("RGB")
        pixels = list(sample.getdata())
        assert any(p[0] > 180 and p[1] < 100 for p in pixels), "project logo red missing"
        assert any(p[1] > 140 and p[0] < 80 for p in pixels), "investhome logo green missing"


def test_compose_svg_logo_and_turkish_text_layers() -> None:
    from uuid import uuid4

    from investhome_api.services.gpt_image_design.brief import INVESHOME_SLOGAN
    from investhome_api.services.gpt_image_design.compose import (
        CompositionSlotPlan,
        compose_final_layers,
        svg_bytes_to_png,
    )
    from investhome_api.services.gpt_image_design.source import ResolvedSourceImage

    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40">'
        b'<rect width="120" height="40" fill="#dc2828"/>'
        b'<text x="8" y="28" fill="white" font-size="16">TMP</text>'
        b"</svg>"
    )
    raster = svg_bytes_to_png(svg)
    if raster is None:
        pytest.skip("SVG rasterizer (cairosvg/svglib) unavailable in this environment")
    with Image.open(io.BytesIO(raster)) as check:
        assert check.size[0] > 0 and check.size[1] > 0

    project_logo = ResolvedSourceImage(
        asset_id=uuid4(),
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category="01_BRAND",
        tags=["logo", "primary"],
        image_bytes=svg,
        width=120,
        height=40,
        role="project_logo",
        original_content_type="image/svg+xml",
    )
    base = _png_bytes(400, 500, (20, 40, 70))
    slots = CompositionSlotPlan(
        headline="Washington'da güvenli konum",
        subhead="Columbia Rd NW",
        verified_data="Washington DC",
        cta="Özel tur planla",
        include_slogan=True,
    )
    result = compose_final_layers(
        base,
        logos=[project_logo],
        slots=slots,
        base_asset_id=uuid4(),
    )
    assert result.png_bytes != base
    assert "project_logo" in result.used_slots
    assert "headline" in result.used_slots
    assert "slogan" in result.used_slots
    assert any(el.get("id") == "logo-project" for el in result.layers)
    assert any(el.get("role") == "headline" for el in result.layers)
    headline = next(el for el in result.layers if el.get("role") == "headline")
    assert "ğ" in headline["content"] or "ü" in headline["content"] or "'" in headline["content"]
    slogan = next(el for el in result.layers if el.get("id") == "text-slogan")
    assert slogan["content"] == INVESHOME_SLOGAN
    assert "guven" not in slogan["content"]  # must keep Turkish spelling, not ASCII mangling
    assert "güven" in slogan["content"]


def test_compose_claim_guard_blocks_invented_finance_in_slots() -> None:
    from investhome_api.services.gpt_image_design.compose import build_slot_plan
    from investhome_api.services.social_design_engine.fact_governance import (
        strip_ineligible_financial_claims,
        text_contains_ineligible_financial,
    )

    allowed: list[str] = []
    blocked = ["19.5%", "27.8%", "$1450K"]
    dirty = {
        "headline": "Temple with 19.5% yield",
        "supporting": "Only $1450K left",
        "cta": "Plan a private tour",
    }
    cleaned = {
        key: strip_ineligible_financial_claims(
            value,
            allowed_tokens=allowed,
            blocked_tokens=blocked,
        )
        for key, value in dirty.items()
    }
    for value in cleaned.values():
        assert not text_contains_ineligible_financial(
            value,
            allowed_tokens=allowed,
            blocked_tokens=blocked,
        )
    slots = build_slot_plan(visible_copy=cleaned, verified_lines=["19.5% ROI"], include_slogan=True)
    # Verified line still passed in — service must claim-guard before build_slot_plan.
    assert "19.5%" not in (slots.headline or "")
    assert "$1450K" not in (slots.subhead or "")


def test_art_director_plan_v2_zones_groups_linebreaks() -> None:
    from investhome_api.services.gpt_image_design.design_plan import (
        build_gpt_image_design_plan,
        choose_composition_type,
        decide_headline_line_breaks,
    )

    temple = (
        "The Temple projesinin Washington DC lokasyon avantajını anlatan premium bir Instagram postu hazırla."
    )
    assert choose_composition_type(instruction=temple, objective="location") == "location_story"
    # Location without premium is LOCATION STORY — not a hashed/random left panel.
    assert choose_composition_type(instruction="lokasyon avantajını anlat", objective="location") == "location_story"
    assert choose_composition_type(instruction="mimari cephe minimal", objective="architecture") == "architecture_focus"
    assert choose_composition_type(instruction="marka kampanyası", objective="launch") == "project_intro"
    a = choose_composition_type(instruction="lokasyon avantajı")
    b = choose_composition_type(instruction="lokasyon avantajı")
    assert a == b == "location_story"

    editorial = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="editorial_hero",
        headline="Washington merkezinde",
        has_project_logo=True,
        include_slogan=True,
    )
    assert editorial.composition_type == "EDITORIAL HERO"
    assert editorial.variation == "editorial_hero"
    assert editorial.visual_focal_point
    assert editorial.negative_space
    assert editorial.content_zone and editorial.image_zone and editorial.headline_zone
    assert editorial.brand_zone and editorial.cta_zone
    assert editorial.groups
    group_names = {g.name for g in editorial.groups}
    assert {"brand", "message", "action", "proof", "footer"} <= group_names
    assert editorial.headline_line_breaks == ["Washington", "merkezinde"]
    assert decide_headline_line_breaks("Washington merkezinde", typography_scale="editorial") == [
        "Washington",
        "merkezinde",
    ]
    headline_spec = next(row for row in editorial.layers if row.id == "text-headline")
    assert headline_spec.group == "message"
    assert headline_spec.font_family == "serif"
    assert 64 <= int(headline_spec.font_size or 0) <= 84
    cta_spec = next(row for row in editorial.layers if row.id == "cta-primary")
    loc_spec = next(row for row in editorial.layers if row.id == "text-location")
    # Proof/location is not stacked inside the message column.
    assert loc_spec.y > cta_spec.y
    assert loc_spec.group == "proof"
    assert any(row.shape_kind in {"line", "accent"} for row in editorial.layers if row.type == "SHAPE")
    assert not any(
        row.id == "shape-direction" or (row.shape_kind == "line" and row.height > row.width * 4)
        for row in editorial.layers
    )

    plan = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        instruction=temple,
        headline="Washington merkezinde",
        has_project_logo=True,
        include_slogan=True,
    )
    assert plan.composition_type == "LOCATION STORY"
    assert plan.variation == "location_story"


def test_compose_uses_design_plan_coordinates_not_default_template() -> None:
    from investhome_api.services.gpt_image_design.compose import (
        CompositionSlotPlan,
        compose_final_layers,
    )
    from investhome_api.services.gpt_image_design.design_plan import (
        build_gpt_image_design_plan,
        choose_art_direction,
    )
    from investhome_api.services.gpt_image_design.source import ResolvedSourceImage

    instruction = (
        "The Temple projesinin Washington DC lokasyon avantajını anlatan premium bir Instagram postu hazırla."
    )
    assert choose_art_direction(instruction=instruction, objective="location") == "location_story"
    plan = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="editorial_hero",
        headline="Washington merkezinde",
        has_project_logo=True,
        has_investhome_logo=False,
        include_slogan=True,
    )
    headline_spec = next(row for row in plan.layers if row.id == "text-headline")
    assert (headline_spec.x, headline_spec.y) != (600, 500)
    assert headline_spec.font_family == "serif"
    assert headline_spec.color and headline_spec.color.lower() != "#ffffff"
    assert 64 <= int(headline_spec.font_size or 0) <= 84

    other = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="brand_campaign",
        has_project_logo=True,
        include_slogan=True,
    )
    other_h = next(row for row in other.layers if row.id == "text-headline")
    assert (other_h.x, other_h.y) != (headline_spec.x, headline_spec.y)
    lifestyle = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="lifestyle",
        has_project_logo=True,
        include_slogan=True,
    )
    life_h = next(row for row in lifestyle.layers if row.id == "text-headline")
    assert life_h.x > headline_spec.x
    assert life_h.align == "right"

    base = _png_bytes(1080, 1350, (20, 40, 70))
    logo = ResolvedSourceImage(
        asset_id=uuid4(),
        filename="temple-logo.png",
        content_type="image/png",
        folder_category="01_BRAND",
        tags=["logo"],
        image_bytes=_png_bytes(80, 32, (220, 40, 40)),
        width=80,
        height=32,
        role="project_logo",
    )
    result = compose_final_layers(
        base,
        logos=[logo],
        slots=CompositionSlotPlan(
            headline="Washington merkezinde",
            subhead="Columbia Rd NW",
            verified_data="Washington DC",
            cta="Özel tur planla",
            include_slogan=True,
        ),
        canvas_width=1080,
        canvas_height=1350,
        plan=plan,
    )
    headline = next(el for el in result.layers if el.get("id") == "text-headline")
    assert headline["x"] == headline_spec.x
    assert headline["y"] == headline_spec.y
    assert headline["fontSize"] == headline_spec.font_size
    assert headline["fontFamily"] == "serif"
    assert headline["color"].lower() != "#ffffff"
    assert "\n" in headline["content"]
    assert headline["content"].split("\n") == ["Washington", "merkezinde"]
    cta = next(el for el in result.layers if el.get("id") == "cta-primary")
    assert cta["x"] == next(row for row in plan.layers if row.id == "cta-primary").x
    assert any(el.get("type") == "SHAPE" for el in result.layers)
    assert any(el.get("id") == "logo-project" for el in result.layers)
    assert any(el.get("id") == "text-location" for el in result.layers)


def test_logo_min_size_no_vertical_gold_and_cta_not_always_rect() -> None:
    from investhome_api.services.gpt_image_design.design_plan import (
        DesignPlanLayer,
        MIN_PROJECT_LOGO_H_REF,
        MIN_PROJECT_LOGO_W_REF,
        apply_visual_quality_guard,
        build_gpt_image_design_plan,
        choose_composition_type,
    )

    location_prompt = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu anlatan premium "
        "Instagram postu hazırla. Luxury editorial gayrimenkul reklamı."
    )
    assert choose_composition_type(instruction=location_prompt, objective="location") == "location_story"
    assert choose_composition_type(instruction="mimari cepheyi koru", objective="architecture") != "editorial_hero"
    assert choose_composition_type(instruction="sade minimal lüks tasarım") == "minimal_luxury"

    editorial = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="editorial_hero",
        has_project_logo=True,
        include_slogan=True,
    )
    logo = next(row for row in editorial.layers if row.id == "logo-project")
    assert logo.width >= MIN_PROJECT_LOGO_W_REF
    assert logo.height >= MIN_PROJECT_LOGO_H_REF
    assert not any(
        row.type == "SHAPE"
        and (row.shape_kind or "") == "line"
        and row.height > row.width * 4
        and row.height > 40
        for row in editorial.layers
    )
    for row in editorial.layers:
        if row.type == "SHAPE" and row.role == "decoration":
            assert row.decoration_purpose in {"hierarchy", "direction", "framing", "brand_signature"}

    styles = set()
    filled_gold = 0
    families = ("editorial_hero", "location_story", "architecture_focus", "minimal_luxury")
    for variation in families:
        plan = build_gpt_image_design_plan(
            canvas_width=1080,
            canvas_height=1350,
            art_direction=variation,
            has_project_logo=True,
        )
        cta = next(row for row in plan.layers if row.id == "cta-primary")
        styles.add(cta.cta_style)
        assert cta.cta_style in {"pill", "outline", "editorial_link", "text_arrow", "minimal"}
        if (cta.background_color or "").upper() == "#C4A35A":
            filled_gold += 1
    assert "editorial_link" in styles
    assert len(styles) >= 2
    assert filled_gold < len(families)

    tiny = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="editorial_hero",
        has_project_logo=True,
    )
    logo_layer = next(row for row in tiny.layers if row.id == "logo-project")
    logo_layer.width, logo_layer.height = 80, 24
    tiny.layers.append(
        DesignPlanLayer(
            id="shape-direction",
            type="SHAPE",
            role="decoration",
            x=40,
            y=160,
            width=2,
            height=180,
            content_slot="shape",
            fill="#C4A35A",
            shape_kind="line",
        )
    )
    fixed = apply_visual_quality_guard(tiny)
    logo_fixed = next(row for row in fixed.layers if row.id == "logo-project")
    assert logo_fixed.width >= MIN_PROJECT_LOGO_W_REF
    assert logo_fixed.height >= MIN_PROJECT_LOGO_H_REF
    assert not any(row.id == "shape-direction" for row in fixed.layers)
    assert fixed.visual_review_status == "READY FOR USER VISUAL REVIEW"
    assert "Visual Quality PASS" not in (fixed.visual_review_status or "")


def test_no_metadata_leakage_and_contrast_safe_area_guard() -> None:
    from investhome_api.services.gpt_image_design.compose import (
        CompositionSlotPlan,
        compose_final_layers,
    )
    from investhome_api.services.gpt_image_design.design_plan import (
        apply_visual_quality_guard,
        build_gpt_image_design_plan,
        looks_like_metadata_leak,
        sanitize_creative_text,
    )
    from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
    from investhome_api.services.gpt_image_design.service import _verified_creative_line

    assert looks_like_metadata_leak("project name: The Temple")
    assert sanitize_creative_text("project name: The Temple") == ""
    assert sanitize_creative_text("city: Washington") == "Washington"
    assert _verified_creative_line("project name", "The Temple") == ""
    assert _verified_creative_line("city", "Washington DC") == "Washington DC"

    plan = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="location_story",
        has_project_logo=True,
        include_slogan=True,
    )
    margins = plan.safe_margins
    assert margins["bottom"] >= 64
    for row in plan.layers:
        if row.type in {"TEXT", "IMAGE", "BUTTON"}:
            assert row.x >= margins["left"] - 1
            assert row.y >= margins["top"] - 1
            assert row.x + row.width <= 1080 - margins["right"] + 1
            assert row.y + row.height <= 1350 - margins["bottom"] + 1
    slogan = next(row for row in plan.layers if row.id == "text-slogan")
    assert slogan.color and slogan.color.lower() not in {"#6b7280", "#1b2a4a"}
    assert plan.needs_scrim is True
    assert plan.visual_review_status == "READY FOR USER VISUAL REVIEW"

    dark_navy = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        art_direction="location_story",
        has_project_logo=True,
        include_slogan=True,
    )
    headline = next(row for row in dark_navy.layers if row.id == "text-headline")
    slogan_dark = next(row for row in dark_navy.layers if row.id == "text-slogan")
    headline.color = "#1B2A4A"
    slogan_dark.color = "#6B7280"
    slogan_dark.y = 1330
    fixed = apply_visual_quality_guard(dark_navy)
    headline2 = next(row for row in fixed.layers if row.id == "text-headline")
    slogan2 = next(row for row in fixed.layers if row.id == "text-slogan")
    assert headline2.color and headline2.color.lower() not in {"#1b2a4a"}
    assert slogan2.y + slogan2.height <= 1350 - fixed.safe_margins["bottom"] + 1
    assert "contrast_text_color" in fixed.quality_corrections or "slogan_contrast" in fixed.quality_corrections
    assert "safe_area_bottom" in fixed.quality_corrections or slogan2.y < 1330

    base = _png_bytes(1080, 1350, (20, 40, 70))
    logo = ResolvedSourceImage(
        asset_id=uuid4(),
        filename="temple-logo.png",
        content_type="image/png",
        folder_category="01_BRAND",
        tags=["logo"],
        image_bytes=_png_bytes(80, 32, (220, 40, 40)),
        width=80,
        height=32,
        role="project_logo",
    )
    result = compose_final_layers(
        base,
        logos=[logo],
        slots=CompositionSlotPlan(
            headline="Washington merkezinde",
            subhead="Columbia Rd NW",
            verified_data="project name: The Temple",
            cta="Özel tur planla",
            include_slogan=True,
        ),
        canvas_width=1080,
        canvas_height=1350,
        plan=plan,
    )
    assert not any(el.get("id") == "text-location" for el in result.layers)
    for el in result.layers:
        blob = f"{el.get('content') or ''} {el.get('label') or ''}"
        assert "project name:" not in blob.lower()
    logo_el = next(el for el in result.layers if el.get("id") == "logo-project")
    assert int(logo_el["height"]) >= 56
    assert int(logo_el["width"]) >= 160


def test_architecture_lock_still_in_project_brief() -> None:
    from investhome_api.services.gpt_image_design.brief import ARCHITECTURE_LOCK
    from investhome_api.services.gpt_image_design.design_plan import (
        build_gpt_image_design_plan,
        design_plan_to_dict,
    )

    intent = GenerationIntent(
        marketing_objective="location",
        audience="buyers",
        language="tr",
        asset_preference="exterior",
        cta_hint="Plan a private tour",
    )
    strategy = MarketingStrategy(
        objective="location",
        audience="buyers",
        campaign_angle="central_positioning",
        single_minded_message="A central Washington DC address.",
        supporting_evidence=["Washington DC"],
        excluded_facts=["19.5%"],
        tone="refined",
        neighborhood="",
        city="Washington",
        project_name="Temple Residences",
    )
    copy = CopyDirection(
        package=CopyPackage(
            eyebrow="Washington DC",
            headline="Washington merkezinde",
            supporting_copy="A refined address in Washington.",
            cta="Özel tur planla",
            language="tr",
            tone="refined",
        )
    )
    creative = CreativeConcept(
        objective="location",
        concept="Place-led",
        visual_strategy="photography_is_hero",
        primary_message="Washington merkezinde",
        supporting_message="Washington DC",
        cta="Özel tur planla",
        information_to_exclude=["19.5%"],
        composition_strategy="LOCATION",
        tone="refined",
        text_density="sparse",
    )
    knowledge = ProjectKnowledgePackage(
        project_identity={"project_name": "Temple Residences"},
        location={"city": "Washington", "country": "US"},
    )
    intel = CampaignIntelligencePackage(
        campaign_intent="location",
        campaign_intent_confidence=0.9,
        marketing_objective="location",
        project_knowledge=knowledge,
        verified_campaign_facts=[],
        user_campaign_inputs=[],
        missing_relevant_facts=[],
        available_assets=[],
        marketing_safe_facts=[],
        can_proceed=True,
        qa_trace={"blocked_financial_tokens": ["19.5%"]},
    )
    plan = build_gpt_image_design_plan(
        canvas_width=1080,
        canvas_height=1350,
        instruction="The Temple projesinin Washington DC lokasyon avantajını anlatan premium bir Instagram postu hazırla.",
        headline="Washington merkezinde",
        has_project_logo=True,
    )
    shared = build_shared_brief(
        project_name="Temple Residences",
        instruction="The Temple projesinin Washington DC lokasyon avantajını anlatan premium bir Instagram postu hazırla.",
        intent=intent,
        strategy=strategy,
        copy_direction=copy,
        creative=creative,
        campaign_facts=[],
        intel=intel,
        source_filename="temple-aerial.png",
        language="tr",
        format_label="Instagram 4:5",
        resolution="1088x1360",
        extra_image_roles=["project_logo"],
        logo_notes=[],
        design_reference_names=[],
    )
    shared["design_plan"] = design_plan_to_dict(plan)
    prompt = render_project_edit_prompt(shared)
    assert "do not redesign" in prompt.lower()
    assert "preserve this building" in prompt.lower()
    assert "architecture lock" in prompt.lower()
    assert "art direction plan" in prompt.lower()
    assert plan.composition_type == "LOCATION STORY"
    assert "visual focal point" in prompt.lower()
    assert "location story" in prompt.lower()
    assert plan.headline_zone is not None
    assert f"x={plan.headline_zone.x}" in prompt
    assert "19.5%" not in prompt
    assert "do not rasterize" in prompt.lower() or "do not paint" in prompt.lower()
    assert "blank template" in prompt.lower() or "template panel" in prompt.lower() or "campaign air" in prompt.lower()


def test_brief_clean_canvas_lock_in_project_prompt() -> None:
    from investhome_api.services.gpt_image_design.brief import CLEAN_CANVAS_LOCK, render_project_edit_prompt

    shared = {
        "project": "The Temple",
        "objective": "lifestyle",
        "audience": "buyers",
        "language": "tr",
        "tone": "premium",
        "campaign_angle": "interior",
        "single_minded_message": "Calm sanctuary",
        "user_campaign_facts": [],
        "marketing_safe_facts": [],
        "allowed_financial_tokens": [],
        "blocked_financial_tokens": [],
        "visible_copy": {"headline": "Eviniz, Sığınak", "cta": "Detayları Keşfet"},
        "composition": {"format": "Instagram 4:5", "resolution": "1088x1360"},
        "source_image": "living.jpg",
        "extra_image_roles": ["project_logo"],
        "architecture_lock": [],
        "brand_restraint": [],
        "user_instruction": "Interior lifestyle ad",
        "interior_lock": True,
    }
    prompt = render_project_edit_prompt(shared)
    upper = prompt.upper()
    for rule in CLEAN_CANVAS_LOCK[:2]:
        assert rule.split(",")[0].strip().upper() in upper or "NO TEXT" in upper
    assert "NO LOGOS" in upper
    assert "do not rasterize" in prompt.lower()


def test_find_global_investhome_logo_no_silent_fallback(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from investhome_api.models.creative_studio_media import (
        CreativeStudioMediaAsset,
        MediaAssetSourceType,
    )
    from investhome_api.services.gpt_image_design.source import (
        INVESHOME_GLOBAL_LOGO_MISSING,
        find_global_investhome_logo,
        resolve_project_inputs,
    )
    from investhome_api.services.storage.factory import get_storage_provider, provider_enum

    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    _upload_hero(client, tmp_path, monkeypatch, temple.id)

    # Project-local Temple logo must NOT count as global Investhome mark.
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "gpt-image-media"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    storage = get_storage_provider()
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="20">'
        b'<rect width="40" height="20" fill="red"/></svg>'
    )
    key = f"creative-studio/media/2026/08/{uuid4().hex}.svg"
    storage.save(key, io.BytesIO(svg), content_length=len(svg))
    asset = CreativeStudioMediaAsset(
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        file_size=len(svg),
        storage_provider=provider_enum().value,
        storage_key=key,
        linked_project_id=temple.id,
        folder_category="01_BRAND",
        source_type=MediaAssetSourceType.UPLOAD.value,
        tags=["logo", "primary", "temple"],
    )
    db_session.add(asset)
    db_session.commit()

    assert find_global_investhome_logo(db_session) is None
    _source, extras, _refs, notes, warnings = resolve_project_inputs(
        db_session,
        linked_project_id=temple.id,
        instruction="lokasyon avantajı Instagram postu",
        selected_asset_ids=[],
        project_name=temple.project_name,
        project_code=temple.project_code,
    )
    assert not any(row.role == "investhome_logo" for row in extras)
    assert INVESHOME_GLOBAL_LOGO_MISSING in warnings
    assert any(INVESHOME_GLOBAL_LOGO_MISSING in n for n in notes)


@pytest.mark.gpt_image_live
def test_live_temple_final_composition_once(
    client: TestClient,
    db_session: Session,
) -> None:
    """Exactly one paid GPT Image call — Temple Instagram 4:5 location post."""
    settings = get_settings()
    if not (settings.ai_api_key or "").strip():
        pytest.skip("AI_API_KEY required for live GPT Image call")
    if not bool(getattr(settings, "gpt_image_enabled", True)):
        pytest.skip("GPT_IMAGE_ENABLED=false")

    temple = db_session.get(Project, TEMPLE_PROJECT_ID)
    if temple is None:
        pytest.skip("Temple project not seeded in this database")

    reset_provider_call_count()
    resp = client.post(
        "/ai/creative-studio/social/gpt-image/generate",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": (
                "The Temple projesinin Washington DC'deki merkezi lokasyonunu anlatan premium Instagram postu hazırla. "
                "Projenin mimarisini değiştirme. Luxury editorial gayrimenkul reklamı seviyesinde sade, güçlü ve sofistike bir tasarım oluştur."
            ),
            "design_provider": "gpt-image",
            "campaign_mode": "project",
            "format_preset": "portrait",
            "aspect_ratio": "4:5",
            "language": "tr",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider_call_count"] == 1
    assert body["campaign_mode"] == "project"
    assert len(body["outputs"]) == 1
    output = body["outputs"][0]
    assert output["local_asset_id"]
    assert output.get("composition_base_asset_id")
    layers = output.get("layers") or []
    assert layers, "editable OS layers required"
    roles = {el.get("role") for el in layers if isinstance(el, dict)}
    types = {el.get("type") for el in layers if isinstance(el, dict)}
    assert "IMAGE" in types or "TEXT" in types
    warnings = list(body.get("warnings") or []) + list(output.get("composition_warnings") or [])
    # Global IH logo is currently absent in seeded ML — must report clearly, no silent fake.
    if not any(row.get("role") == "investhome_logo" for row in (body.get("extra_images") or [])):
        assert any("Investhome global logo asset bulunamadı" in str(w) for w in warnings)
    brief = body.get("brief") or {}
    prompt = str(brief.get("prompt") or "")
    assert "19.5%" not in prompt
    assert "do not rasterize" in prompt.lower() or "reserved" in prompt.lower() or "safe" in prompt.lower()
    print("LIVE_FINAL_ASSET_ID", output["local_asset_id"])
    print("LIVE_BASE_ASSET_ID", output.get("composition_base_asset_id"))
    print("LIVE_LAYER_COUNT", len(layers))
    print("LIVE_LAYER_ROLES", sorted(r for r in roles if r))

