"""Ideogram External Design AI POC tests — mock/disabled path by default."""

from __future__ import annotations

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
from investhome_api.services.ideogram_design_poc.brief import (
    build_shared_brief,
    render_variant_prompt,
)
from investhome_api.services.ideogram_design_poc.client import reset_provider_call_count
from investhome_api.services.ideogram_design_poc.config import (
    ART_DIRECTIONS,
    IDEOGRAM_REMIX_ENDPOINT,
)
from investhome_api.services.social_design_engine.copy_director import CopyDirection, CopyPackage
from investhome_api.services.social_design_engine.creative_director import CreativeConcept
from investhome_api.services.social_design_engine.generation import CampaignFact, GenerationIntent
from investhome_api.services.social_design_engine.marketing_strategist import MarketingStrategy
from investhome_api.services.social_design_engine.project_knowledge import ProjectKnowledgePackage
from investhome_api.services.social_design_engine.verified_facts import (
    CampaignIntelligencePackage,
    VerifiedFact,
)
from investhome_api.services.storage.factory import get_storage_provider

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")


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
def _ideogram_unit_defaults(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if request.node.get_closest_marker("ideogram_live"):
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
        return
    monkeypatch.setenv("IDEOGRAM_API_KEY", "")
    monkeypatch.setenv("IDEOGRAM_ENABLED", "false")
    monkeypatch.setenv("IDEOGRAM_MODEL", "V_4_0")
    monkeypatch.setenv("IDEOGRAM_DEFAULT_QUALITY", "QUALITY")
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
        project_code=f"PRJ-IDG-{uuid4().hex[:8]}",
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
) -> dict:
    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "ideogram-media"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    files = {"file": ("temple-aerial-exterior.png", io.BytesIO(_png_bytes(64, 64)), "image/png")}
    data = {
        "tags": "temple,aerial,exterior,hero",
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
    resp = client.get("/ai/creative-studio/social/ideogram/status")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["available"] is False
    assert body["configured"] is False
    assert body["provider"] == "ideogram"
    assert body["reason"] in {"ideogram_api_key_missing", "ideogram_disabled"}
    assert "api_key" not in str(body).lower() or "IDEOGRAM_API_KEY" not in str(body)


def test_generate_unavailable_does_not_mock_success(
    client: TestClient,
    db_session: Session,
) -> None:
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    resp = client.post(
        "/ai/creative-studio/social/ideogram/generate",
        json={
            "linked_project_id": str(temple.id),
            "instruction": (
                "Create an Instagram square investment post with $500,000 / 14% / 24 months."
            ),
        },
    )
    assert resp.status_code == 503, resp.text
    assert "ideogram" in resp.json()["detail"].lower()
    assert resp.json().get("outputs") is None or "outputs" not in resp.json()


def test_generate_three_variants_mocked(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEOGRAM_API_KEY", "test-ideogram-key")
    monkeypatch.setenv("IDEOGRAM_ENABLED", "true")
    get_settings.cache_clear()
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    asset = _upload_hero(client, tmp_path, monkeypatch, temple.id)
    prompts: list[str] = []
    seeds = {"n": 10}

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        assert url == IDEOGRAM_REMIX_ENDPOINT
        headers = kwargs.get("headers") or {}
        assert headers.get("Api-Key") == "test-ideogram-key"
        data = kwargs.get("data") or {}
        prompt = str(data.get("text_prompt") or "")
        prompts.append(prompt)
        assert data.get("resolution") == "1024x1024"
        assert "image" in (kwargs.get("files") or {})
        seeds["n"] += 1
        return _FakeResponse(
            200,
            {
                "created": "2026-08-13T00:00:00Z",
                "data": [
                    {
                        "prompt": "ok",
                        "resolution": "1024x1024",
                        "is_image_safe": True,
                        "seed": seeds["n"],
                        "url": f"https://ideogram.ai/api/images/ephemeral/fake-{seeds['n']}.png",
                    }
                ],
            },
        )

    def fake_get(url: str, **kwargs: Any) -> _FakeResponse:
        assert "ideogram.ai" in url
        return _FakeResponse(200, content=_png_bytes(32, 32, (12, 24, 48)))

    post_path = "investhome_api.services.ideogram_design_poc.client.httpx.post"
    get_path = "investhome_api.services.ideogram_design_poc.client.httpx.get"
    with patch(post_path, side_effect=fake_post), patch(get_path, side_effect=fake_get):
        resp = client.post(
            "/ai/creative-studio/social/ideogram/generate",
            json={
                "linked_project_id": str(temple.id),
                "instruction": (
                    "Create a premium Instagram square investment post in English. "
                    "Minimum investment $500,000, target return 14%, duration 24 months."
                ),
                "selected_asset_ids": [asset["id"]],
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "ideogram"
    assert body["endpoint"] == IDEOGRAM_REMIX_ENDPOINT
    assert body["aspect_ratio"] == "1:1"
    assert len(body["outputs"]) == 3
    variants = [row["variant"] for row in body["outputs"]]
    assert variants == ["A", "B", "C"]
    arts = [row["art_direction"] for row in body["outputs"]]
    assert arts == [name for _, name, _ in ART_DIRECTIONS]
    ids = {row["local_asset_id"] for row in body["outputs"]}
    assert len(ids) == 3
    assert all(row["local_asset_id"] for row in body["outputs"])
    assert all(row["metadata"]["provider"] == "ideogram" for row in body["outputs"])
    assert all(row["metadata"].get("original_remote_url") for row in body["outputs"])
    assert body["source_image"]["asset_id"] == asset["id"]
    blob = "\n".join(prompts)
    assert "Editorial Luxury" in blob
    assert "Institutional Investment" in blob
    assert "Architectural Premium" in blob
    assert "$500,000" in blob or "500,000" in blob or "$500000" in blob.replace(",", "")
    assert "14%" in blob
    assert "24" in blob
    assert "19.5%" not in blob
    assert "27.8%" not in blob
    assert "$1450K" not in blob and "$1,450K" not in blob
    assert body["provider_call_count"] == 3


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
        excluded_facts=[],
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
        qa_trace={"blocked_financial_tokens": ["19.5%", "27.8%", "$1450K"]},
    )
    shared = build_shared_brief(
        project_name="Temple Residences",
        instruction=(
            "The Temple'ın Washington DC'deki merkezi lokasyon avantajını "
            "anlatan premium Instagram kare postu hazırla."
        ),
        intent=intent,
        strategy=strategy,
        copy_direction=copy,
        creative=creative,
        campaign_facts=[],
        intel=intel,
        source_filename="temple-aerial-exterior.png",
        language="tr",
    )
    prompt = render_variant_prompt(
        shared,
        variant="A",
        art_direction_name="Editorial Luxury",
        art_direction_brief="editorial",
    )
    assert "19.5%" not in prompt
    assert "27.8%" not in prompt
    assert "$1450K" not in prompt
    assert "Washington" in prompt


def test_claim_guard_keeps_user_campaign_financials() -> None:
    intent = GenerationIntent(
        marketing_objective="investment",
        audience="investors",
        language="en",
        asset_preference="premium_hero",
        cta_hint="Request the investment brief",
    )
    facts = [
        CampaignFact(label="Minimum investment", display="$500,000", kind="money"),
        CampaignFact(label="Target return", display="14%", kind="percent"),
        CampaignFact(label="Duration", display="24 months", kind="duration"),
    ]
    strategy = MarketingStrategy(
        objective="investment",
        audience="investors",
        campaign_angle="opportunity",
        single_minded_message="Participate from $500,000.",
        supporting_evidence=["14%", "24 months"],
        excluded_facts=["19.5%", "27.8%"],
        tone="institutional",
        city="Washington",
        project_name="Temple Residences",
    )
    copy = CopyDirection(
        package=CopyPackage(
            eyebrow="Investment",
            headline="From $500,000",
            supporting_copy="14% target · 24 months",
            cta="Request the brief",
            language="en",
            tone="institutional",
        )
    )
    creative = CreativeConcept(
        objective="investment",
        concept="Investment case",
        visual_strategy="photography_is_hero",
        primary_message="From $500,000",
        supporting_message="14% · 24 months",
        cta="Request the brief",
        information_to_exclude=["19.5%", "27.8%", "$1450K"],
        composition_strategy="INVESTMENT",
        tone="institutional",
        text_density="moderate",
    )
    knowledge = ProjectKnowledgePackage(
        project_identity={"project_name": "Temple Residences"},
        location={"city": "Washington"},
    )
    intel = CampaignIntelligencePackage(
        campaign_intent="investment",
        campaign_intent_confidence=0.9,
        marketing_objective="investment",
        project_knowledge=knowledge,
        verified_campaign_facts=[],
        user_campaign_inputs=[{"label": f.label, "display": f.display} for f in facts],
        missing_relevant_facts=[],
        available_assets=[],
        marketing_safe_facts=[],
        qa_trace={"blocked_financial_tokens": ["19.5%", "27.8%", "$1450K"]},
    )
    shared = build_shared_brief(
        project_name="Temple Residences",
        instruction="Temple investment post $500,000 / 14% / 24 months English",
        intent=intent,
        strategy=strategy,
        copy_direction=copy,
        creative=creative,
        campaign_facts=facts,
        intel=intel,
        source_filename="temple-aerial-exterior.png",
        language="en",
    )
    prompt = render_variant_prompt(
        shared,
        variant="B",
        art_direction_name="Institutional Investment",
        art_direction_brief="institutional",
    )
    assert "$500,000" in prompt
    assert "14%" in prompt
    assert "24 months" in prompt
    assert "19.5%" not in prompt
    assert "27.8%" not in prompt
    assert "$1450K" not in prompt


def test_rejects_non_square(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IDEOGRAM_API_KEY", "test-ideogram-key")
    monkeypatch.setenv("IDEOGRAM_ENABLED", "true")
    get_settings.cache_clear()
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    resp = client.post(
        "/ai/creative-studio/social/ideogram/generate",
        json={
            "linked_project_id": str(temple.id),
            "instruction": "Create a story post",
            "aspect_ratio": "9:16",
        },
    )
    assert resp.status_code == 422


def _live_key_present() -> bool:
    here = Path(__file__).resolve()
    candidates = [here.parent / ".env"]
    candidates.extend(parent / ".env" for parent in here.parents)
    for env_path in candidates:
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped.startswith("IDEOGRAM_API_KEY="):
                continue
            value = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            return bool(value)
    return False


@pytest.mark.ideogram_live
@pytest.mark.skipif(not _live_key_present(), reason="IDEOGRAM_API_KEY missing")
def test_live_ideogram_remix(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IDEOGRAM_API_KEY", raising=False)
    monkeypatch.setenv("IDEOGRAM_ENABLED", "true")
    get_settings.cache_clear()
    status = client.get("/ai/creative-studio/social/ideogram/status").json()
    if not status.get("available"):
        pytest.skip("Ideogram provider unavailable")
    temple = _create_project(db_session, project_id=TEMPLE_PROJECT_ID)
    db_session.commit()
    asset = _upload_hero(client, tmp_path, monkeypatch, temple.id)
    resp = client.post(
        "/ai/creative-studio/social/ideogram/generate",
        json={
            "linked_project_id": str(temple.id),
            "instruction": (
                "Create a premium Instagram square investment post in English. "
                "Minimum investment $500,000, target return 14%, duration 24 months."
            ),
            "selected_asset_ids": [asset["id"]],
            "count": 3,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["outputs"]) == 3
    assert all(row["local_asset_id"] for row in body["outputs"])
    assert body["provider_call_count"] >= 3
