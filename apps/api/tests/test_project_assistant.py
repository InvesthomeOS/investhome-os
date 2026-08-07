"""Sprint 7 — AI Project Assistant (RAG foundation) tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.ai_index import AiDocument, AiDocumentStatus, AiDocumentType
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.services.ai_search.hybrid_search import hybrid_search
from investhome_api.services.ai_search.reindex import reindex_document
from investhome_api.services.project_assistant.conversation import clear_conversations_for_tests
from investhome_api.services.project_assistant.llm_provider import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    LocalGroundedLLMProvider,
    get_llm_provider,
)
from investhome_api.services.project_assistant.prompt_builder import build_rag_prompt
from sqlalchemy import select


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


@pytest.fixture
def db_session(client) -> Session:
    clear_conversations_for_tests()
    return _db()


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    clear_conversations_for_tests()


def _create_project(db: Session, name: str = "Assistant Project") -> Project:
    project = Project(
        id=uuid4(),
        project_code=f"PRJ-A-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project)
    db.flush()
    return project


def _long_text(seed: str, paragraphs: int = 4) -> str:
    body = (
        f"{seed} — InvestHome residential construction schedule, amenities, "
        "floor plans, and marketing brief for the lakeside development. "
    )
    parts = []
    for i in range(paragraphs):
        parts.append(f"# Section {i + 1}\n\n" + (body * 6))
    return "\n\n".join(parts)


def _asset(
    db: Session,
    project: Project,
    *,
    filename: str = "brief.md",
) -> CreativeStudioMediaAsset:
    asset = CreativeStudioMediaAsset(
        id=uuid4(),
        filename=filename,
        content_type="text/markdown",
        file_size=100,
        storage_provider="google_drive",
        storage_key=f"gdrive:{uuid4().hex}",
        linked_project_id=project.id,
        source_type=MediaAssetSourceType.GOOGLE_DRIVE.value,
        external_file_id=f"file-{uuid4().hex[:8]}",
        external_checksum="c1",
        sync_status=MediaAssetSyncStatus.ACTIVE.value,
        folder_category="00_PROJECT_INFO",
    )
    db.add(asset)
    db.flush()
    return asset


def _ready_document(
    db: Session,
    project: Project,
    *,
    text: str,
    title: str = "brief.md",
    asset: CreativeStudioMediaAsset | None = None,
) -> AiDocument:
    doc = AiDocument(
        id=uuid4(),
        asset_id=asset.id if asset else None,
        project_id=project.id,
        drive_file_id=asset.external_file_id if asset else f"drive-{uuid4().hex[:8]}",
        document_type=AiDocumentType.MD.value,
        category="00_PROJECT_INFO",
        title=title,
        extracted_text=text,
        summary=text[:200],
        keywords=["residential", "amenities"],
        builders=["proposal"],
        checksum=f"chk-{uuid4().hex[:12]}",
        version=1,
        is_active=True,
        index_status=AiDocumentStatus.READY.value,
    )
    db.add(doc)
    db.flush()
    return doc


def test_local_llm_provider_grounded_from_chunks() -> None:
    provider = LocalGroundedLLMProvider()
    empty = provider.generate(system="sys", user="Question: anything?\n--- EVIDENCE_START ---\n[]\n--- EVIDENCE_END ---")
    assert empty.answer == INSUFFICIENT_EVIDENCE_MESSAGE

    evidence = (
        '[{"document_name":"amenities.md","chunk_order":0,'
        '"text":"The project includes a rooftop spa and lakeside pool."}]'
    )
    user = f"--- EVIDENCE_START ---\n{evidence}\n--- EVIDENCE_END ---\nQuestion: amenities?"
    filled = provider.generate(system="sys", user=user)
    assert "rooftop spa" in filled.answer.lower() or "According to verified" in filled.answer
    assert "amenities.md" in filled.answer


def test_get_llm_provider_falls_back_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    get_settings.cache_clear()
    provider = get_llm_provider()
    assert provider.name == "local"


def test_prompt_builder_token_budget(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("Huge amenities spa pool gym"))
    reindex_document(db, doc.id)
    hits = hybrid_search(
        db, query="amenities spa", project_scope="single", project_id=project.id, limit=5
    )
    assert hits
    prompt = build_rag_prompt(
        question="What amenities?",
        project_scope="single",
        project_id=project.id,
        project_ids=None,
        hits=hits,
        max_prompt_chars=2_500,
        max_chunks=8,
        max_chunk_chars=200,
    )
    assert len(prompt.system) + len(prompt.user) <= 2_500 + 200  # small slack for formatting
    assert prompt.chunk_count >= 1
    assert "EVIDENCE_START" in prompt.user
    assert str(project.id) in prompt.user


def test_single_project_qa(client, db_session: Session) -> None:
    db = db_session
    project = _create_project(db, "Single QA")
    asset = _asset(db, project, filename="amenities.md")
    doc = _ready_document(
        db,
        project,
        text=_long_text("Lakeside rooftop spa and infinity pool amenities"),
        title="amenities.md",
        asset=asset,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/project-assistant",
        json={
            "question": "What amenities does the lakeside project include?",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["grounded"] is True
    assert body["confidence"] > 0
    assert body["citations"]
    assert body["citations"][0]["document_name"] == "amenities.md"
    assert body["citations"][0]["asset_id"] == str(asset.id)
    assert body["citations"][0]["project_id"] == str(project.id)
    assert body["citations"][0]["chunk_reference"].startswith("chunk:")
    assert body["assets"]
    assert body["documents"]
    assert str(project.id) in [str(p) for p in body["projects"]]
    assert INSUFFICIENT_EVIDENCE_MESSAGE not in body["answer"]
    assert body["search_time_ms"] >= 0
    assert body["latency_ms"] >= 0
    assert body["provider"] == "local"
    assert body["conversation_id"]


def test_multi_project_qa(client, db_session: Session) -> None:
    db = db_session
    p1 = _create_project(db, "Multi A")
    p2 = _create_project(db, "Multi B")
    d1 = _ready_document(db, p1, text=_long_text("Alpha tower rooftop garden amenities"))
    d2 = _ready_document(db, p2, text=_long_text("Beta tower underground parking amenities"))
    reindex_document(db, d1.id)
    reindex_document(db, d2.id)
    db.commit()

    resp = client.post(
        "/ai/project-assistant",
        json={
            "question": "What amenities are mentioned for the towers?",
            "project_ids": [str(p1.id), str(p2.id)],
            "project_scope": "multi",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["grounded"] is True
    cited_projects = {c["project_id"] for c in body["citations"]}
    assert cited_projects <= {str(p1.id), str(p2.id)}


def test_insufficient_evidence(client, db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    # No indexed documents → must refuse to fabricate
    db.commit()

    resp = client.post(
        "/ai/project-assistant",
        json={
            "question": "What is the guaranteed ROI for investors?",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["grounded"] is False
    assert body["answer"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert body["citations"] == []
    assert body["confidence"] == 0.0


def test_permission_isolation_no_cross_project_leak(client, db_session: Session) -> None:
    db = db_session
    p1 = _create_project(db, "Secret One")
    p2 = _create_project(db, "Secret Two")
    d1 = _ready_document(db, p1, text=_long_text("Secret Alpha exclusive rooftop spa code ALPHA-ONLY"))
    d2 = _ready_document(db, p2, text=_long_text("Secret Beta exclusive underground vault code BETA-ONLY"))
    reindex_document(db, d1.id)
    reindex_document(db, d2.id)
    db.commit()

    resp = client.post(
        "/ai/project-assistant",
        json={
            "question": "What is the exclusive code ALPHA-ONLY rooftop spa?",
            "project_id": str(p1.id),
            "project_scope": "single",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for c in body["citations"]:
        assert c["project_id"] == str(p1.id)
        assert c["document_id"] != str(d2.id)
    assert "BETA-ONLY" not in body["answer"]

    missing = client.post(
        "/ai/project-assistant",
        json={
            "question": "amenities?",
            "project_id": str(uuid4()),
            "project_scope": "single",
        },
    )
    assert missing.status_code == 404


def test_citations_and_audit(client, db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    asset = _asset(db, project, filename="brief.md")
    doc = _ready_document(
        db,
        project,
        text=_long_text("Verified lakeside amenity brief with spa"),
        title="brief.md",
        asset=asset,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/project-assistant",
        json={
            "question": "Describe the lakeside amenity spa",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["citations"]
    cite = body["citations"][0]
    assert cite["asset_id"] == str(asset.id)
    assert cite["document_name"] == "brief.md"
    assert cite["chunk_id"]
    assert cite["project_id"] == str(project.id)

    logs = list(
        db.scalars(
            select(ActivityLog).where(ActivityLog.entity_type == ActivityEntityType.PROJECT_AI)
        ).all()
    )
    assert logs
    meta = logs[-1].metadata_json or {}
    assert "question" in meta
    assert meta.get("provider")
    assert "api_key" not in meta
    assert "latency_ms" in meta


def test_follow_up_conversation(client, db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(
        db,
        project,
        text=_long_text("Phase one includes rooftop spa; phase two adds a cinema lounge"),
        title="phases.md",
    )
    reindex_document(db, doc.id)
    db.commit()

    first = client.post(
        "/ai/project-assistant",
        json={
            "question": "What amenities are in phase one?",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert first.status_code == 200
    conv = first.json()["conversation_id"]

    second = client.post(
        "/ai/project-assistant",
        json={
            "question": "And phase two?",
            "project_id": str(project.id),
            "project_scope": "single",
            "conversation_id": conv,
        },
    )
    assert second.status_code == 200
    body = second.json()
    assert body["conversation_id"] == conv
    # Follow-up should still be scoped and return something coherent
    assert body["answer"]
    assert body["latency_ms"] >= 0


def test_latency_smoke(client, db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("Latency smoke amenities spa"))
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/project-assistant",
        json={
            "question": "amenities spa?",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["latency_ms"] < 15_000
    assert body["search_time_ms"] < 15_000


def test_regression_search_still_works(client, db_session: Session) -> None:
    """Assistant must not break hybrid search / AI index retrieval."""
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("Regression lakeside amenities spa"))
    reindex_document(db, doc.id)
    db.commit()

    search = client.post(
        "/ai/search",
        json={
            "query": "lakeside amenities",
            "project_id": str(project.id),
            "project_scope": "single",
            "limit": 5,
        },
    )
    assert search.status_code == 200
    assert search.json()["total"] >= 1

    ask = client.post(
        "/ai/project-assistant",
        json={
            "question": "lakeside amenities?",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert ask.status_code == 200

    # Search again after assistant call
    search2 = client.post(
        "/ai/search",
        json={
            "query": "lakeside amenities",
            "project_id": str(project.id),
            "project_scope": "single",
        },
    )
    assert search2.status_code == 200
    assert search2.json()["total"] >= 1


def test_missing_project_scope_rejected(client, db_session: Session) -> None:
    bad = client.post(
        "/ai/project-assistant",
        json={"question": "anything?", "project_scope": "single"},
    )
    assert bad.status_code == 400
