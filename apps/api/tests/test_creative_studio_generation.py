"""Creative Studio shared AI generation foundation (Phase 1) tests."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.ai_index import AiDocument, AiDocumentStatus, AiDocumentType
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerateRequest
from investhome_api.services.ai_search.hybrid_search import hybrid_search
from investhome_api.services.ai_search.reindex import reindex_document
from investhome_api.services.creative_studio_generation.context import (
    assert_context_has_no_forbidden_media,
    load_brand_context,
    sanitize_builder_context,
)
from investhome_api.services.project_assistant.llm_provider import INSUFFICIENT_EVIDENCE_MESSAGE

# Temple Residences — prefer this id when seeded in docker; otherwise create fixture.
TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


@pytest.fixture
def db_session(client) -> Session:
    return _db()


@pytest.fixture(autouse=True)
def _reset_settings() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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
        project_code=f"PRJ-CS-{uuid4().hex[:8]}",
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


def _long_text(seed: str, paragraphs: int = 4) -> str:
    body = (
        f"{seed} — Temple Residences residential construction schedule, amenities, "
        "floor plans, and marketing brief for the Columbia Heights development. "
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
    folder_category: str = "00_PROJECT_INFO",
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
        folder_category=folder_category,
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
    category: str = "00_PROJECT_INFO",
    asset: CreativeStudioMediaAsset | None = None,
    builders: list[str] | None = None,
) -> AiDocument:
    doc = AiDocument(
        id=uuid4(),
        asset_id=asset.id if asset else None,
        project_id=project.id,
        drive_file_id=asset.external_file_id if asset else f"drive-{uuid4().hex[:8]}",
        document_type=AiDocumentType.MD.value,
        category=category,
        title=title,
        extracted_text=text,
        summary=text[:200],
        keywords=["temple", "residences", "amenities"],
        builders=builders or ["blog", "email", "social", "proposal"],
        checksum=f"chk-{uuid4().hex[:12]}",
        version=1,
        is_active=True,
        index_status=AiDocumentStatus.READY.value,
    )
    db.add(doc)
    db.flush()
    return doc


def test_missing_linked_project_id_rejected(client) -> None:
    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "builder_type": "blog",
            "instruction": "Write a short amenities blurb",
        },
    )
    assert resp.status_code == 422


def test_cross_project_asset_id_rejected(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    other = _create_project(db, "Other Tower")
    foreign_asset = _asset(db, other, filename="other.md")
    db.commit()

    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "linked_project_id": str(temple.id),
            "builder_type": "blog",
            "instruction": "Write a blurb using selected assets",
            "selected_asset_ids": [str(foreign_asset.id)],
        },
    )
    assert resp.status_code == 403, resp.text
    assert "does not belong" in resp.json()["detail"]


def test_temple_generation_context_and_citations(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    asset = _asset(db, temple, filename="amenities.md")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple rooftop spa infinity pool Columbia Heights amenities"),
        title="amenities.md",
        asset=asset,
        builders=["blog"],
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "builder_type": "blog",
            "instruction": "Write a short blog intro about Temple amenities and spa",
            "selected_asset_ids": [str(asset.id)],
            "language": "en",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["project_id"] == str(TEMPLE_PROJECT_ID)
    assert data["builder_type"] == "blog"
    assert str(asset.id) in data["asset_ids_used"]
    assert data["retrieval_confidence"] > 0
    assert data["grounded"] is True
    assert data["citations"], "expected citation/source metadata"
    for cit in data["citations"]:
        assert cit["project_id"] == str(TEMPLE_PROJECT_ID)
        assert cit["document_id"]
        assert cit["chunk_id"]
        assert cit["document_name"]
    assert data["context"] is not None
    assert data["context"]["project_identity"]["project_name"] == "Temple Residences"
    assert data["context"]["verified_facts"]
    # No mock / Unsplash in context
    blob = str(data["context"]).lower()
    assert "unsplash" not in blob
    assert "picsum" not in blob


def test_project_scoped_rag_isolation(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    other = _create_project(db, "Secret Other Project")
    temple_asset = _asset(db, temple, filename="temple.md")
    other_asset = _asset(db, other, filename="secret.md")
    temple_doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple public lakeside courtyard and lobby lounge"),
        title="temple.md",
        asset=temple_asset,
    )
    other_doc = _ready_document(
        db,
        other,
        text=_long_text("SECRET_CROSS_PROJECT_MARKER exclusive vault amenities nowhere else"),
        title="secret.md",
        asset=other_asset,
    )
    reindex_document(db, temple_doc.id)
    reindex_document(db, other_doc.id)
    db.commit()

    # Direct hybrid search isolation
    hits = hybrid_search(
        db,
        query="SECRET_CROSS_PROJECT_MARKER vault",
        project_scope="single",
        project_id=temple.id,
        limit=10,
    )
    assert all(h.project_id == temple.id for h in hits)
    assert not any("SECRET_CROSS_PROJECT_MARKER" in (h.chunk_text or "") for h in hits)

    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "linked_project_id": str(temple.id),
            "builder_type": "proposal",
            "instruction": "Describe SECRET_CROSS_PROJECT_MARKER vault amenities",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "SECRET_CROSS_PROJECT_MARKER" not in data["generated_content"]
    for cit in data["citations"]:
        assert cit["project_id"] == str(temple.id)
    if data.get("context"):
        blob = str(data["context"])
        assert "SECRET_CROSS_PROJECT_MARKER" not in blob


def test_missing_brand_context_behavior(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    asset = _asset(db, temple, filename="info.md")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple location Columbia Heights residential tower facts"),
        title="info.md",
        asset=asset,
        category="00_PROJECT_INFO",
    )
    reindex_document(db, doc.id)
    db.commit()

    brand = load_brand_context(db, project_id=temple.id)
    assert brand.available is False
    assert brand.reason == "brand_context_unavailable"

    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "linked_project_id": str(temple.id),
            "builder_type": "email",
            "instruction": "Write an email about Temple location",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["brand_context"]["available"] is False
    assert data["brand_context"]["reason"] == "brand_context_unavailable"
    assert "brand_context_unavailable" in data["warnings"]


def test_brand_context_when_indexed(db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    brand_asset = _asset(db, temple, filename="brand-guide.md", folder_category="01_BRAND")
    brand_doc = _ready_document(
        db,
        temple,
        text="Official Temple brand voice: warm, precise, never use the word luxury casually.",
        title="brand-guide.md",
        asset=brand_asset,
        category="01_BRAND",
    )
    reindex_document(db, brand_doc.id)
    db.flush()

    brand = load_brand_context(db, project_id=temple.id)
    assert brand.available is True
    assert brand.excerpts
    assert "warm" in brand.excerpts[0].lower()
    assert brand_doc.id in brand.document_ids


def test_insufficient_context_behavior(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "linked_project_id": str(temple.id),
            "builder_type": "social",
            "instruction": "Write a caption about nonexistent quantum rooftop orchards",
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["grounded"] is False
    assert data["generated_content"] == INSUFFICIENT_EVIDENCE_MESSAGE
    assert "insufficient_context" in data["warnings"] or "insufficient_retrieved_content" in data[
        "warnings"
    ]
    assert data["citations"] == []


def test_no_unsplash_or_mock_in_context(db_session: Session) -> None:
    cleaned, warnings = sanitize_builder_context(
        {
            "headline": "Temple opening",
            "hero_image": "https://images.unsplash.com/photo-123",
            "unsplash": ["https://unsplash.com/x"],
            "ok_field": "Columbia Heights",
        }
    )
    assert cleaned is not None
    assert cleaned.get("ok_field") == "Columbia Heights"
    assert "hero_image" not in cleaned or cleaned.get("hero_image") is None
    assert "unsplash" not in cleaned
    assert warnings

    # Service path rejects forbidden media if somehow present
    temple = _create_project(db_session, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )

    ctx = CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=temple.id,
            project_code=temple.project_code,
            project_name=temple.project_name,
        ),
        verified_facts=["project_name=Temple Residences"],
        retrieved_content=[],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="brand_context_unavailable"),
        builder_type="blog",
    )
    assert_context_has_no_forbidden_media(ctx)


def test_generate_request_requires_linked_project_id() -> None:
    """linked_project_id is mandatory at the schema layer."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreativeStudioGenerateRequest(
            builder_type="blog",
            instruction="Write something",
        )  # type: ignore[call-arg]


def test_citation_source_metadata_present(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, "Temple Residences", project_id=TEMPLE_PROJECT_ID)
    asset = _asset(db, temple, filename="facts.md")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple residences verified construction timeline and unit mix"),
        title="facts.md",
        asset=asset,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/generate",
        json={
            "linked_project_id": str(temple.id),
            "builder_type": "presentation",
            "instruction": "Summarize Temple construction timeline",
            "selected_asset_ids": [str(asset.id)],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["citations"]
    cit = data["citations"][0]
    assert cit["document_id"] == str(doc.id)
    assert cit["chunk_reference"].startswith("chunk:")
    assert "score" in cit
    assert cit.get("excerpt")
