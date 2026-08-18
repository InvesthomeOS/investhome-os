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
    first_name = files[0][0] if files else ""
    assert first_name == "image[]"
    prompt = str(data.get("prompt") or "")
    assert "architecture" in prompt.lower() or "building" in prompt.lower()
    assert "19.5%" not in prompt
    assert "27.8%" not in prompt
    assert "$1450K" not in prompt and "$1,450K" not in prompt
    brief = body.get("brief") or {}
    assert "blocked_financial_tokens" in brief
    assert captured.get("json") is None
    assert body["provider_call_count"] == 1


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
    assert shared["user_campaign_facts"] == []
    assert "19.5%" in (shared.get("blocked_financial_tokens") or [])
