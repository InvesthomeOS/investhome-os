"""Sprint 6 — Semantic search + vector index foundation tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.ai_index import AiDocument, AiDocumentStatus, AiDocumentType
from investhome_api.models.ai_search import AiChunk, AiEmbedding
from investhome_api.models.creative_studio_media import (
    CreativeStudioMediaAsset,
    MediaAssetSourceType,
    MediaAssetSyncStatus,
)
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.services.ai_search.chunking import build_chunks
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.ai_search.providers import (
    LocalHashEmbeddingProvider,
    get_embedding_provider,
)
from investhome_api.services.ai_search.reindex import (
    embed_new_or_changed_chunks,
    reindex_document,
    remove_document_vectors,
    sync_document_chunks,
)
from investhome_api.services.ai_search.vector_store import cosine_similarity, get_vector_store


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


@pytest.fixture
def db_session(client) -> Session:
    return _db()


def _create_project(db: Session, name: str = "Search Project") -> Project:
    project = Project(
        id=uuid4(),
        project_code=f"PRJ-S-{uuid4().hex[:8]}",
        project_name=name,
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project)
    db.flush()
    return project


def _long_text(seed: str, paragraphs: int = 4) -> str:
    """Build multi-paragraph text large enough to chunk (>1200 chars)."""
    body = (
        f"{seed} — InvestHome residential construction schedule, amenities, "
        "floor plans, and marketing brief for the lakeside development. "
    )
    parts = []
    for i in range(paragraphs):
        parts.append(f"# Section {i + 1}\n\n" + (body * 6))
    return "\n\n".join(parts)


def _ready_document(
    db: Session,
    project: Project,
    *,
    text: str,
    title: str = "brief.md",
    category: str = "00_PROJECT_INFO",
    builders: list[str] | None = None,
    asset: CreativeStudioMediaAsset | None = None,
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
        keywords=["residential", "construction"],
        builders=builders,
        checksum=f"chk-{uuid4().hex[:12]}",
        version=1,
        is_active=True,
        index_status=AiDocumentStatus.READY.value,
    )
    db.add(doc)
    db.flush()
    return doc


def _asset(
    db: Session,
    project: Project,
    *,
    filename: str = "brief.md",
    sync_status: str = MediaAssetSyncStatus.ACTIVE.value,
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
        sync_status=sync_status,
        folder_category="00_PROJECT_INFO",
    )
    db.add(asset)
    db.flush()
    return asset


def test_chunk_generation_respects_structure_and_limits() -> None:
    text = _long_text("Chunking validation")
    chunks = build_chunks(text, min_chars=600, max_chars=1200)
    assert len(chunks) >= 2
    for c in chunks:
        assert c.text.strip()
        assert len(c.text) <= 1200 + 50  # soft bound from packing
        # No mid-word: last char not alphanumeric stuck without space before cut — basic check
        assert c.checksum
    # Orders contiguous
    assert [c.chunk_order for c in chunks] == list(range(len(chunks)))


def test_chunk_update_and_deleted_chunk_removal(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("Original lakeside amenities"))
    chunks1 = sync_document_chunks(db, doc)
    assert len(chunks1) >= 2
    n1 = len(chunks1)

    # Shrink text → fewer chunks; stale orders removed
    doc.extracted_text = "Short note about amenities only."
    chunks2 = sync_document_chunks(db, doc)
    assert len(chunks2) == 1
    remaining = db.scalars(select(AiChunk).where(AiChunk.document_id == doc.id)).all()
    assert len(remaining) == 1
    assert remaining[0].chunk_order == 0
    assert n1 > 1


def test_embedding_generation_incremental_no_duplicates(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("Embedding incremental test"))
    chunks = sync_document_chunks(db, doc)
    provider = LocalHashEmbeddingProvider(dimensions=32)
    store = get_vector_store()

    stats1 = embed_new_or_changed_chunks(db, chunks, provider=provider, store=store)
    assert stats1["embedded"] == len(chunks)
    assert stats1["skipped"] == 0
    count1 = db.scalar(select(func.count()).select_from(AiEmbedding)) or 0
    assert count1 == len(chunks)

    stats2 = embed_new_or_changed_chunks(db, chunks, provider=provider, store=store)
    assert stats2["embedded"] == 0
    assert stats2["skipped"] == len(chunks)
    count2 = db.scalar(select(func.count()).select_from(AiEmbedding)) or 0
    assert count2 == count1  # no duplicates


def test_changed_chunk_reembeds(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("First version content here"))
    reindex_document(db, doc.id)
    before = {
        (e.chunk_id, e.model): e.checksum
        for e in db.scalars(select(AiEmbedding)).all()
    }
    assert before

    doc.extracted_text = _long_text("Second version with different marketing copy")
    reindex_document(db, doc.id)
    after_rows = list(db.scalars(select(AiEmbedding)).all())
    assert after_rows
    # Unique constraint: one embedding per chunk+model
    models = {(e.chunk_id, e.model) for e in after_rows}
    assert len(models) == len(after_rows)
    # Content change should refresh at least one embedding checksum
    after = {(e.chunk_id, e.model): e.checksum for e in after_rows}
    assert before != after or set(before.keys()) != set(after.keys())


def test_deleted_chunks_remove_embeddings(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    doc = _ready_document(db, project, text=_long_text("Delete vectors test"))
    reindex_document(db, doc.id)
    assert (db.scalar(select(func.count()).select_from(AiChunk)) or 0) >= 1
    assert (db.scalar(select(func.count()).select_from(AiEmbedding)) or 0) >= 1

    removed = remove_document_vectors(db, doc.id)
    assert removed >= 1
    assert (db.scalar(select(func.count()).select_from(AiChunk)) or 0) == 0
    assert (db.scalar(select(func.count()).select_from(AiEmbedding)) or 0) == 0


def test_hybrid_search_and_ranking(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    asset_a = _asset(db, project, filename="amenities.md")
    asset_b = _asset(db, project, filename="budget.md")
    doc_a = _ready_document(
        db,
        project,
        text=_long_text("Lakeside residential amenities spa pool fitness center"),
        title="amenities.md",
        asset=asset_a,
    )
    doc_b = _ready_document(
        db,
        project,
        text=_long_text("Construction budget spreadsheet and cost tracking notes"),
        title="budget.md",
        asset=asset_b,
    )
    reindex_document(db, doc_a.id)
    reindex_document(db, doc_b.id)

    hits = hybrid_search(
        db,
        query="lakeside amenities spa pool",
        project_scope="single",
        project_id=project.id,
        limit=5,
    )
    assert hits
    assert hits[0].document_id == doc_a.id
    assert hits[0].score >= hits[-1].score
    assert hits[0].file == "amenities.md"
    assert hits[0].summary
    # Never expose vectors in hit dataclass fields
    assert not hasattr(hits[0], "vector")


def test_project_filter_mandatory_no_leak(db_session: Session) -> None:
    db = db_session
    p1 = _create_project(db, "P1")
    p2 = _create_project(db, "P2")
    d1 = _ready_document(db, p1, text=_long_text("Secret project one tower plans"))
    d2 = _ready_document(db, p2, text=_long_text("Secret project two tower plans"))
    reindex_document(db, d1.id)
    reindex_document(db, d2.id)

    with pytest.raises(ProjectScopeError):
        hybrid_search(db, query="tower plans", project_scope="single", project_id=None)

    hits = hybrid_search(
        db, query="tower plans", project_scope="single", project_id=p1.id, limit=10
    )
    assert hits
    assert all(h.project_id == p1.id for h in hits)
    assert all(h.document_id != d2.id for h in hits)

    multi = hybrid_search(
        db,
        query="tower plans",
        project_scope="multi",
        project_ids=[p1.id, p2.id],
        limit=10,
    )
    assert {h.project_id for h in multi} <= {p1.id, p2.id}

    global_hits = hybrid_search(
        db, query="tower plans", project_scope="global", limit=20
    )
    assert {h.document_id for h in global_hits} >= {d1.id, d2.id}


def test_inactive_and_missing_excluded(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    asset_ok = _asset(db, project, filename="ok.md")
    asset_miss = _asset(
        db, project, filename="gone.md", sync_status=MediaAssetSyncStatus.MISSING.value
    )
    doc_ok = _ready_document(
        db, project, text=_long_text("Active document amenities"), asset=asset_ok
    )
    doc_inactive = _ready_document(
        db, project, text=_long_text("Inactive document amenities")
    )
    doc_inactive.is_active = False
    doc_inactive.index_status = AiDocumentStatus.INACTIVE.value
    doc_missing = _ready_document(
        db, project, text=_long_text("Missing drive amenities"), asset=asset_miss
    )
    reindex_document(db, doc_ok.id)
    reindex_document(db, doc_inactive.id)
    reindex_document(db, doc_missing.id)

    hits = hybrid_search(
        db, query="amenities", project_scope="single", project_id=project.id, limit=20
    )
    ids = {h.document_id for h in hits}
    assert doc_ok.id in ids
    assert doc_inactive.id not in ids
    assert doc_missing.id not in ids


def test_builder_and_category_filters(db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    d1 = _ready_document(
        db,
        project,
        text=_long_text("Proposal website content for residential"),
        category="05_MARKETING",
        builders=["website", "proposal"],
    )
    d2 = _ready_document(
        db,
        project,
        text=_long_text("Legal meta residential notes"),
        category="90_LEGAL",
        builders=["legal"],
    )
    reindex_document(db, d1.id)
    reindex_document(db, d2.id)

    hits = hybrid_search(
        db,
        query="residential",
        project_scope="single",
        project_id=project.id,
        category="05_MARKETING",
        builder="website",
        limit=10,
    )
    assert hits
    assert all(h.document_id == d1.id for h in hits)


def test_local_provider_default_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")
    monkeypatch.delenv("EMBEDDING_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    get_settings.cache_clear()
    try:
        provider = get_embedding_provider()
        assert provider.name == "local"
        a = provider.embed(["hello world"])
        b = provider.embed(["hello world"])
        assert a.vectors[0] == b.vectors[0]
        assert cosine_similarity(a.vectors[0], b.vectors[0]) > 0.99
    finally:
        get_settings.cache_clear()


def test_api_search_endpoint(client, db_session: Session) -> None:
    db = db_session
    project = _create_project(db)
    asset = _asset(db, project)
    doc = _ready_document(
        db,
        project,
        text=_long_text("API search lakeside amenities and spa"),
        asset=asset,
        title="amenities.md",
    )
    reindex_document(db, doc.id)
    db.commit()

    # Missing project scope → 400
    bad = client.post("/ai/search", json={"query": "amenities", "project_scope": "single"})
    assert bad.status_code == 400

    resp = client.post(
        "/ai/search",
        json={
            "query": "lakeside amenities spa",
            "project_id": str(project.id),
            "project_scope": "single",
            "limit": 5,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    item = body["items"][0]
    assert item["document_id"] == str(doc.id)
    assert item["asset_id"] == str(asset.id)
    assert item["chunk"]
    assert item["score"] is not None
    assert item["summary"]
    assert item["file"] == "amenities.md"
    assert item["project_id"] == str(project.id)
    assert "vector" not in item
    assert "embedding" not in item


def test_ai_index_pipeline_hooks_vectors(db_session: Session) -> None:
    """Regression: indexing an asset also creates chunks/embeddings."""
    from investhome_api.services.ai_index.pipeline import index_asset
    from investhome_api.services.google_drive.errors import GoogleDriveApiError
    from investhome_api.services.google_drive.provider import DriveFileMeta

    db = db_session
    project = _create_project(db)
    asset = _asset(db, project, filename="notes.txt")

    class Prov:
        root_folder_id = "root"

        def download_bytes(self, file_id: str, *, max_bytes: int | None = None) -> bytes:
            return _long_text("Pipeline hook amenities residential").encode("utf-8")

        def get_file(self, file_id: str) -> DriveFileMeta:
            raise GoogleDriveApiError("n/a", code="x")

    doc = index_asset(db, asset.id, provider=Prov(), force=True)
    assert doc is not None
    assert doc.index_status == AiDocumentStatus.READY.value
    chunks = list(db.scalars(select(AiChunk).where(AiChunk.document_id == doc.id)).all())
    assert chunks
    embeddings = list(db.scalars(select(AiEmbedding)).all())
    assert embeddings
    assert len(embeddings) == len(chunks)
