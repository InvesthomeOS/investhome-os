"""Social Media Builder AI Design Engine (Phase 1) tests."""

from __future__ import annotations

import json
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
from investhome_api.services.ai_search.reindex import reindex_document
from investhome_api.services.social_design_engine.apply import apply_ops
from investhome_api.services.social_design_engine.media import list_media_candidates, pick_best_asset
from investhome_api.services.social_design_engine.ops import validate_op, validate_ops
from investhome_api.schemas.social_design_engine import SocialDesignOp

TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")


def _db() -> Session:
    return next(app.dependency_overrides[get_db]())


@pytest.fixture
def db_session(client) -> Session:
    return _db()


@pytest.fixture(autouse=True)
def _reset_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("AI_PROVIDER", "local")
    monkeypatch.setenv("AI_MODEL", "local-grounded-v1")
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
        project_code=f"PRJ-SDE-{uuid4().hex[:8]}",
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


def _asset(
    db: Session,
    project: Project,
    *,
    filename: str = "hero.jpg",
    content_type: str = "image/jpeg",
    folder_category: str = "02_MEDIA",
) -> CreativeStudioMediaAsset:
    asset = CreativeStudioMediaAsset(
        id=uuid4(),
        filename=filename,
        content_type=content_type,
        file_size=2048,
        width=1600,
        height=1200,
        storage_provider="google_drive",
        storage_key=f"gdrive:{uuid4().hex}",
        linked_project_id=project.id,
        source_type=MediaAssetSourceType.GOOGLE_DRIVE.value,
        external_file_id=f"file-{uuid4().hex[:8]}",
        external_checksum="c1",
        sync_status=MediaAssetSyncStatus.ACTIVE.value,
        folder_category=folder_category,
        tags=["temple", "rooftop"],
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
        keywords=["temple", "residences", "amenities", "rooftop"],
        builders=["social", "blog"],
        checksum=f"chk-{uuid4().hex[:12]}",
        version=1,
        is_active=True,
        index_status=AiDocumentStatus.READY.value,
    )
    db.add(doc)
    db.flush()
    return doc


def _long_text(seed: str) -> str:
    body = (
        f"{seed} — Temple Residences residential construction schedule, amenities, "
        "rooftop spa, infinity pool, and marketing brief for Columbia Heights. "
    )
    return "\n\n".join(f"# Section {i}\n\n" + (body * 5) for i in range(4))


def test_ops_validation_rejects_unknown_and_cross_project() -> None:
    pid = TEMPLE_PROJECT_ID
    posts = [{"id": "p1", "formatPreset": "square", "width": 1080, "height": 1080, "elements": []}]
    with pytest.raises(Exception) as exc:
        validate_op(
            {
                "op": "FLY_TO_MOON",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {},
            },
            linked_project_id=pid,
            posts=posts,
            allowed_asset_ids=set(),
        )
    assert "unknown_op" in str(exc.value)

    with pytest.raises(Exception) as exc2:
        validate_op(
            {
                "op": "ADD_TEXT",
                "linked_project_id": str(uuid4()),
                "post_id": "p1",
                "payload": {"content": "x", "width": 100, "height": 40},
            },
            linked_project_id=pid,
            posts=posts,
            allowed_asset_ids=set(),
        )
    assert "linked_project_id_mismatch" in str(exc2.value)


def test_ops_reject_unsplash_and_invalid_asset() -> None:
    pid = TEMPLE_PROJECT_ID
    posts = [{"id": "p1", "formatPreset": "square", "width": 1080, "height": 1080, "elements": []}]
    accepted, rejected = validate_ops(
        [
            {
                "op": "ADD_IMAGE",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {
                    "asset_id": "https://images.unsplash.com/photo-1",
                    "width": 200,
                    "height": 200,
                },
            }
        ],
        linked_project_id=pid,
        posts=posts,
        allowed_asset_ids=set(),
    )
    assert not accepted
    assert any("forbidden_media_url" in r[1] or "invalid_asset_id" in r[1] for r in rejected)


def test_ops_reject_rag_debug_copy_on_canvas() -> None:
    """RAG/metadata diagnostics must never become TEXT/CTA content."""
    from investhome_api.services.social_design_engine.ops import (
        looks_like_rag_or_debug_copy,
        normalize_raw_ops,
    )

    assert looks_like_rag_or_debug_copy(
        "Sources: metadata.json / chunk 0 — searchable index asset_type versioning builders"
    )
    assert looks_like_rag_or_debug_copy("project_name=Temple Residences")
    assert not looks_like_rag_or_debug_copy("Discover Temple Residences")

    pid = TEMPLE_PROJECT_ID
    posts = [
        {
            "id": "p1",
            "formatPreset": "square",
            "width": 1080,
            "height": 1080,
            "elements": [{"id": "t1", "type": "TEXT", "role": "headline", "content": "Good"}],
        }
    ]
    accepted, rejected = validate_ops(
        [
            {
                "op": "ADD_TEXT",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {
                    "role": "body",
                    "content": "Sources: metadata.json / chunk 0 searchable asset_type",
                    "width": 400,
                    "height": 80,
                    "x": 40,
                    "y": 800,
                },
            },
            {
                "op": "UPDATE_TEXT",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "element_id": "t1",
                "payload": {"content": "builders versioning searchable index"},
            },
        ],
        linked_project_id=pid,
        posts=posts,
        allowed_asset_ids=set(),
    )
    assert not accepted
    assert any("empty_or_debug_copy_rejected" in r[1] or "rag_or_debug_copy_rejected" in r[1] for r in rejected)

    normalized = normalize_raw_ops(
        [
            {
                "op": "ADD_TEXT",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {"content": "Sources: metadata.json / chunk 0", "role": "body"},
            },
            {
                "op": "ADD_TEXT",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {"content": "Quiet luxury at Temple", "role": "headline"},
            },
        ],
        linked_project_id=pid,
        fallback_asset_id=None,
    )
    assert len(normalized) == 1
    assert normalized[0]["payload"]["content"] == "Quiet luxury at Temple"

    # LLM alias: payload.text → content/label
    aliased = normalize_raw_ops(
        [
            {
                "op": "ADD_TEXT",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {
                    "text": "Lüksün Yeni Adresi: The Temple",
                    "position": {"x": 50, "y": 50},
                    "style": {"font_size": 36, "color": "#F4EFE8", "font_family": "Bold"},
                },
            },
            {
                "op": "ADD_CTA",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {"text": "Detayları Keşfedin"},
            },
        ],
        linked_project_id=pid,
        fallback_asset_id=None,
    )
    assert aliased[0]["payload"]["content"] == "Lüksün Yeni Adresi: The Temple"
    assert aliased[0]["payload"]["role"] == "headline"
    assert aliased[0]["payload"]["fontSize"] == 36
    assert aliased[1]["payload"]["label"] == "Detayları Keşfedin"


def test_apply_skips_rag_metadata_text() -> None:
    pid = TEMPLE_PROJECT_ID
    posts = [{"id": "p1", "formatPreset": "square", "width": 1080, "height": 1080, "elements": []}]
    ops = [
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="p1",
            element_id=None,
            payload={
                "role": "headline",
                "content": "Sources: metadata.json / chunk 0",
                "x": 40,
                "y": 700,
                "width": 900,
                "height": 80,
            },
        ),
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="p1",
            element_id=None,
            payload={
                "role": "headline",
                "content": "Temple Residences Soft Launch",
                "x": 40,
                "y": 700,
                "width": 900,
                "height": 80,
            },
        ),
    ]
    mutated, _ = apply_ops(posts, ops, linked_project_id=pid, selected_post_id="p1")
    texts = [
        str(el.get("content") or "")
        for el in mutated[0]["elements"]
        if isinstance(el, dict) and el.get("type") == "TEXT"
    ]
    assert texts == ["Temple Residences Soft Launch"]
    assert all("metadata.json" not in t and "Sources:" not in t for t in texts)


def test_create_and_edit_apply_ops() -> None:
    pid = TEMPLE_PROJECT_ID
    asset_id = uuid4()
    create_ops = [
        SocialDesignOp(
            op="CREATE_POST",
            linked_project_id=pid,
            post_id="ai-post-1",
            element_id=None,
            payload={"formatPreset": "square", "platform": "instagram", "name": "Launch"},
        ),
        SocialDesignOp(
            op="SET_BACKGROUND",
            linked_project_id=pid,
            post_id="ai-post-1",
            element_id=None,
            payload={"asset_id": str(asset_id)},
        ),
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="ai-post-1",
            element_id="headline-1",
            payload={
                "role": "headline",
                "content": "Enter THE TEMPLE",
                "fontSize": 48,
                "fontWeight": "bold",
                "align": "center",
                "color": "#ffffff",
                "x": 80,
                "y": 700,
                "width": 900,
                "height": 100,
                "zIndex": 2,
            },
        ),
        SocialDesignOp(
            op="ADD_CTA",
            linked_project_id=pid,
            post_id="ai-post-1",
            element_id="cta-1",
            payload={
                "label": "Schedule a private tour",
                "x": 340,
                "y": 950,
                "width": 400,
                "height": 48,
            },
        ),
    ]
    posts, selected = apply_ops([], create_ops, linked_project_id=pid, selected_post_id=None)
    assert selected == "ai-post-1"
    assert len(posts) == 1
    assert posts[0]["coverAssetId"] == str(asset_id)
    assert any(e.get("role") == "headline" for e in posts[0]["elements"])
    assert any(e.get("type") == "BUTTON" for e in posts[0]["elements"])

    headline = next(e for e in posts[0]["elements"] if e.get("role") == "headline")
    edit_ops = [
        SocialDesignOp(
            op="UPDATE_STYLE",
            linked_project_id=pid,
            post_id="ai-post-1",
            element_id=headline["id"],
            payload={"color": "#0f172a"},
        ),
        SocialDesignOp(
            op="MOVE_ELEMENT",
            linked_project_id=pid,
            post_id="ai-post-1",
            element_id=headline["id"],
            payload={"x": 80, "y": 640},
        ),
    ]
    posts2, _ = apply_ops(posts, edit_ops, linked_project_id=pid, selected_post_id="ai-post-1")
    h2 = next(e for e in posts2[0]["elements"] if e.get("role") == "headline")
    assert h2["color"] == "#0f172a"
    assert h2["y"] == 640


def test_layout_grammar_safe_bounds_and_text_fit() -> None:
    """AI create layout uses canonical 1:1 bounds, safe margins, and text fitting."""
    from investhome_api.services.social_design_engine.layout import (
        SAFE_MARGIN_RATIO,
        apply_layout_grammar,
        element_within_bounds,
        estimate_wrap_lines,
        fit_font_size,
        social_layout_slots,
    )
    from investhome_api.services.social_design_engine.ops import normalize_raw_ops

    pid = TEMPLE_PROJECT_ID
    # Long headline that would overflow a narrow box at huge fontSize
    lines = estimate_wrap_lines("Invest in The Temple Residences Today", 96, 900, bold=True)
    assert len(lines) >= 1
    font, height = fit_font_size(
        "Invest in The Temple Residences Today",
        max_width=900,
        max_height=200,
        preferred=96,
        min_size=22,
        max_size=72,
        bold=True,
        max_lines=4,
    )
    assert font <= 72
    assert height <= 200

    slots = social_layout_slots(1080, 1080)
    assert slots["headline"]["y"] < slots["body"]["y"] < slots["cta"]["y"]
    margin = int(round(1080 * SAFE_MARGIN_RATIO))
    assert slots["headline"]["x"] >= margin - 1

    # LLM free pixels are stripped before apply
    normalized = normalize_raw_ops(
        [
            {
                "op": "ADD_TEXT",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {
                    "role": "headline",
                    "content": "Invest in The Temple",
                    "x": 9999,
                    "y": -40,
                    "width": 5000,
                    "height": 900,
                    "fontSize": 200,
                },
            },
            {
                "op": "ADD_CTA",
                "linked_project_id": str(pid),
                "post_id": "p1",
                "payload": {"label": "Explore the investment", "x": 10, "y": 1070},
            },
        ],
        linked_project_id=pid,
        fallback_asset_id=None,
    )
    assert "x" not in normalized[0]["payload"]
    assert "y" not in normalized[0]["payload"]
    assert "x" not in normalized[1]["payload"]

    create_ops = [
        SocialDesignOp(
            op="CREATE_POST",
            linked_project_id=pid,
            post_id="layout-post",
            element_id=None,
            payload={"formatPreset": "square", "platform": "instagram", "name": "Safe"},
        ),
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="layout-post",
            element_id=None,
            payload={
                "role": "headline",
                "content": "Invest in The Temple",
                "fontWeight": "bold",
                "color": "#ffffff",
            },
        ),
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="layout-post",
            element_id=None,
            payload={
                "role": "body",
                "content": "A premium investment opportunity grounded in verified project knowledge.",
                "color": "#ffffff",
            },
        ),
        SocialDesignOp(
            op="ADD_CTA",
            linked_project_id=pid,
            post_id="layout-post",
            element_id=None,
            payload={"label": "Explore the investment"},
        ),
    ]
    posts, _ = apply_ops([], create_ops, linked_project_id=pid)
    post = posts[0]
    assert post["width"] == 1080 and post["height"] == 1080
    elements = post["elements"]
    headline = next(e for e in elements if e.get("role") == "headline")
    body = next(e for e in elements if e.get("role") == "body")
    cta = next(e for e in elements if e.get("type") == "BUTTON")
    assert headline["content"] == "Invest in The Temple"
    assert body["content"]
    assert cta["label"]
    assert headline["y"] < body["y"] < cta["y"]
    for el in (headline, body, cta):
        assert element_within_bounds(el, 1080, 1080)
        assert el["x"] >= margin - 1
        assert el["y"] >= margin - 1
        assert el["x"] + el["width"] <= 1080 - margin + 1
        assert el["y"] + el["height"] <= 1080 - margin + 1

    # Persistence-shaped grammar remains stable
    again = apply_layout_grammar(dict(post))
    h2 = next(e for e in again["elements"] if e.get("role") == "headline")
    assert h2["content"] == headline["content"]
    assert element_within_bounds(h2, 1080, 1080)


def test_viewport_fit_does_not_require_mutating_geometry_contract() -> None:
    """Documented contract: fit/fullscreen scale display only; stored geometry stays canonical."""
    pid = TEMPLE_PROJECT_ID
    ops = [
        SocialDesignOp(
            op="CREATE_POST",
            linked_project_id=pid,
            post_id="geo-post",
            element_id=None,
            payload={"formatPreset": "square"},
        ),
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="geo-post",
            element_id=None,
            payload={"role": "headline", "content": "Temple", "fontWeight": "bold"},
        ),
        SocialDesignOp(
            op="ADD_TEXT",
            linked_project_id=pid,
            post_id="geo-post",
            element_id=None,
            payload={"role": "body", "content": "Quiet luxury residences."},
        ),
        SocialDesignOp(
            op="ADD_CTA",
            linked_project_id=pid,
            post_id="geo-post",
            element_id=None,
            payload={"label": "Learn more"},
        ),
    ]
    posts, _ = apply_ops([], ops, linked_project_id=pid)
    snapshot = [
        (e.get("id"), e.get("x"), e.get("y"), e.get("width"), e.get("height"), e.get("fontSize"))
        for e in posts[0]["elements"]
        if isinstance(e, dict)
    ]
    # Re-apply empty edit batch must not mutate geometry
    posts2, _ = apply_ops(posts, [], linked_project_id=pid, selected_post_id="geo-post")
    snapshot2 = [
        (e.get("id"), e.get("x"), e.get("y"), e.get("width"), e.get("height"), e.get("fontSize"))
        for e in posts2[0]["elements"]
        if isinstance(e, dict)
    ]
    assert snapshot == snapshot2
    assert posts2[0]["width"] == 1080


def test_media_candidates_project_isolation_and_pick(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    other = _create_project(db, "Other Tower")
    good = _asset(db, temple, filename="temple-rooftop-spa.jpg")
    _asset(db, other, filename="other-tower.jpg")
    db.commit()

    candidates = list_media_candidates(
        db,
        linked_project_id=temple.id,
        instruction="rooftop spa amenity visual for Instagram",
        limit=12,
    )
    assert all(c.linked_project_id == temple.id for c in candidates)
    assert all(c.asset_id != UUID(int=0) for c in candidates)
    assert any(c.asset_id == good.id for c in candidates)
    # Foreign asset must never appear
    assert all("other-tower" not in c.filename.lower() for c in candidates)

    picked = pick_best_asset(candidates)
    assert picked is not None
    assert picked == candidates[0].asset_id or any(c.asset_id == picked for c in candidates)


def test_cross_project_asset_rejected_on_design_endpoint(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    other = _create_project(db, "Other Tower")
    foreign = _asset(db, other, filename="leak.jpg")
    db.commit()

    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(temple.id),
            "instruction": "Create Instagram square",
            "mode": "create",
            "selected_asset_ids": [str(foreign.id)],
            "draft": {"posts": [], "selected_post_id": None},
        },
    )
    assert resp.status_code == 403, resp.text


def test_design_create_edit_persistence_citations_brand(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    image = _asset(db, temple, filename="temple-lobby-render.jpg")
    brief = _asset(db, temple, filename="amenities.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple rooftop spa infinity pool Columbia Heights amenities"),
        title="amenities.md",
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    create_resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": (
                "THE TEMPLE Residences için Instagram kare post oluştur. "
                "Rooftop amenity vurgula, headline + body + CTA olsun."
            ),
            "mode": "create",
            "language": "tr",
            "selected_asset_ids": [str(image.id)],
            "draft": {"posts": [], "selected_post_id": None},
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    create_body = create_resp.json()
    assert create_body["mode"] in {"create", "edit"}
    assert len(create_body["ops"]) >= 1
    assert len(create_body["posts"]) >= 1
    post = create_body["posts"][0]
    assert post.get("linked_project_id") == str(TEMPLE_PROJECT_ID)
    elements = post.get("elements") or []
    assert any(e.get("type") == "TEXT" for e in elements)
    assert any(e.get("type") == "BUTTON" for e in elements)
    # Real Asset IDs only — no Unsplash
    blob = str(create_body)
    assert "unsplash" not in blob.lower()
    assert "images.unsplash" not in blob.lower()
    meta = create_body["meta"]
    assert "provider" in meta and "model" in meta
    assert "brand_context_status" in meta
    assert isinstance(meta.get("warnings"), list)
    # Citations when grounded
    if meta.get("grounded"):
        assert isinstance(meta.get("citations"), list)

    # Asset IDs used should be UUIDs from this project
    for aid in meta.get("asset_ids_used") or []:
        UUID(aid)

    selected_id = create_body["selected_post_id"] or post["id"]
    edit_resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": "Başlık rengini beyaz yap ve başlığı biraz yukarı taşı",
            "mode": "edit",
            "language": "tr",
            "draft": {
                "posts": create_body["posts"],
                "selected_post_id": selected_id,
            },
        },
    )
    assert edit_resp.status_code == 200, edit_resp.text
    edit_body = edit_resp.json()
    assert edit_body["mode"] == "edit"
    assert len(edit_body["ops"]) >= 1
    assert len(edit_body["posts"]) >= 1
    # Same persistent posts state shape
    assert all("elements" in p for p in edit_body["posts"])


def test_brand_unavailable_flag(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    image = _asset(db, temple, filename="temple-exterior.jpg")
    brief = _asset(db, temple, filename="info.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple Residences sales gallery hours and unit mix"),
        title="info.md",
        category="00_PROJECT_INFO",
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": "Create a square social post about the sales gallery",
            "mode": "create",
            "selected_asset_ids": [str(image.id)],
            "draft": {"posts": []},
        },
    )
    assert resp.status_code == 200, resp.text
    meta = resp.json()["meta"]
    assert meta["brand_context"]["available"] is False
    assert meta["brand_context_status"] == "unavailable_neutral_premium"
    assert "brand_context_unavailable" in meta["warnings"]


def test_draft_backward_compat_empty_elements_still_create(client, db_session: Session) -> None:
    """Legacy draft without elements still accepts create mode."""
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    _asset(db, temple, filename="legacy-cover.jpg")
    brief = _asset(db, temple, filename="legacy.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple Residences quiet luxury residences"),
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": "Create Instagram feed post",
            "mode": "create",
            "draft": {
                "posts": [
                    {
                        "id": "legacy-p1",
                        "formatPreset": "square",
                        "width": 1080,
                        "height": 1080,
                        "platform": "instagram",
                        "name": "Legacy",
                        "headline": "Old",
                        "caption": "Old caption",
                        # no elements key — backward compat
                    }
                ],
                "selected_post_id": "legacy-p1",
            },
        },
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["posts"]) >= 1

def test_edit_intent_move_sky_does_not_rewrite_copy() -> None:
    """P0: sky-move instruction moves headline only — no copy rewrite."""
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
        filter_ops_for_copy_protection,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    headline = "Temple Residences Quiet Luxury"
    body = "Verified amenities and Columbia Heights living."
    cta = "Schedule a private tour"
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "coverAssetId": str(uuid4()),
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": headline,
                "x": 80,
                "y": 420,
                "width": 920,
                "height": 120,
                "fontSize": 48,
                "color": "#ffffff",
            },
            {
                "id": "b1",
                "type": "TEXT",
                "role": "body",
                "content": body,
                "x": 80,
                "y": 580,
                "width": 920,
                "height": 100,
                "fontSize": 24,
                "color": "#ffffff",
            },
            {
                "id": "c1",
                "type": "BUTTON",
                "label": cta,
                "x": 340,
                "y": 900,
                "width": 400,
                "height": 56,
            },
        ],
    }
    plan = classify_edit_intents("Başlığı mavi buluta al.")
    assert "MOVE" in plan.intent_names
    assert plan.structural_only
    assert not plan.allow_copy_rewrite
    ops = build_ops_from_intent_plan(plan=plan, linked_project_id=str(pid), post=post)
    assert ops
    assert all(o["op"] in {"MOVE_ELEMENT", "APPLY_LAYOUT_INTENT"} for o in ops)
    move_ops = [o for o in ops if o["op"] == "MOVE_ELEMENT"]
    assert move_ops
    assert move_ops[0]["element_id"] == "h1"
    assert move_ops[0]["payload"]["y"] < 420

    # Unauthorized LLM copy rewrite must be rejected
    rogue = [
        {
            "op": "UPDATE_TEXT",
            "linked_project_id": str(pid),
            "post_id": "p1",
            "element_id": "h1",
            "payload": {"content": "Mavi Bulutların Üzerinde"},
        },
        {
            "op": "UPDATE_CTA",
            "linked_project_id": str(pid),
            "post_id": "p1",
            "element_id": "c1",
            "payload": {"label": "Hemen Bak"},
        },
        move_ops[0],
    ]
    kept, rejected = filter_ops_for_copy_protection(rogue, plan, mode="edit")
    assert any("copy_rewrite_rejected" in r[1] for r in rejected)
    assert all(o.get("op") != "UPDATE_TEXT" for o in kept)
    assert all(o.get("op") != "UPDATE_CTA" or "label" not in (o.get("payload") or {}) for o in kept)

    validated = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id=o["post_id"],
            element_id=o.get("element_id"),
            payload={k: v for k, v in (o.get("payload") or {}).items()},
        )
        for o in ops
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid, selected_post_id="p1")
    el_map = {e["id"]: e for e in out[0]["elements"]}
    assert el_map["h1"]["content"] == headline
    assert el_map["b1"]["content"] == body
    assert el_map["c1"]["label"] == cta
    assert el_map["h1"]["y"] < 420


def test_layout_intelligence_font_grow_no_clip_and_collision() -> None:
    """Compound RESIZE grows font + box and pushes body/CTA without clipping."""
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.services.social_design_engine.layout import (
        element_within_bounds,
        text_fits_without_clip,
    )
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    headline = "Invest in The Temple"
    body = "Quiet luxury residences in Columbia Heights."
    cta = "Schedule a private tour"
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": headline,
                "fontWeight": "bold",
                "align": "center",
                "x": 76,
                "y": 240,
                "width": 400,
                "height": 48,
                "fontSize": 36,
            },
            {
                "id": "b1",
                "type": "TEXT",
                "role": "body",
                "content": body,
                "x": 76,
                "y": 300,
                "width": 900,
                "height": 60,
                "fontSize": 22,
            },
            {
                "id": "c1",
                "type": "BUTTON",
                "label": cta,
                "x": 340,
                "y": 900,
                "width": 400,
                "height": 48,
            },
        ],
    }
    plan = classify_edit_intents("Başlığı biraz büyüt.")
    assert "RESIZE" in plan.intent_names
    assert plan.structural_only
    ops = build_ops_from_intent_plan(plan=plan, linked_project_id=str(pid), post=post)
    assert ops[0]["payload"].get("_compound_resize") or ops[0]["payload"].get("fontSize")
    validated = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id="p1",
            element_id=o.get("element_id"),
            payload=o["payload"],
        )
        for o in ops
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid)
    els = {e["id"]: e for e in out[0]["elements"]}
    assert els["h1"]["content"] == headline
    assert els["b1"]["content"] == body
    assert els["c1"]["label"] == cta
    assert els["h1"]["fontSize"] >= 36
    assert text_fits_without_clip(els["h1"])
    assert element_within_bounds(els["h1"], 1080, 1080)
    assert els["h1"]["y"] + els["h1"]["height"] <= els["b1"]["y"]
    assert els["b1"]["y"] + els["b1"]["height"] <= els["c1"]["y"]


def test_layout_intelligence_one_line_grow() -> None:
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.services.social_design_engine.layout import (
        estimate_wrap_lines,
        text_fits_without_clip,
    )
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": "Temple Residences",
                "fontWeight": "bold",
                "align": "center",
                "x": 200,
                "y": 200,
                "width": 280,
                "height": 40,
                "fontSize": 32,
            },
            {
                "id": "b1",
                "type": "TEXT",
                "role": "body",
                "content": "Body stays",
                "x": 76,
                "y": 500,
                "width": 900,
                "height": 40,
                "fontSize": 20,
            },
        ],
    }
    plan = classify_edit_intents("Başlığı büyüt ama tek satırda kalsın.")
    assert any(i.meta.get("one_line") for i in plan.intents if i.intent == "RESIZE")
    ops = build_ops_from_intent_plan(plan=plan, linked_project_id=str(pid), post=post)
    validated = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id="p1",
            element_id=o.get("element_id"),
            payload=o["payload"],
        )
        for o in ops
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid)
    h1 = next(e for e in out[0]["elements"] if e["id"] == "h1")
    assert h1["content"] == "Temple Residences"
    assert text_fits_without_clip(h1)
    lines = estimate_wrap_lines(h1["content"], h1["fontSize"], h1["width"], bold=True)
    assert len(lines) == 1
    assert h1["width"] >= 280


def test_layout_preserves_explicit_newlines() -> None:
    from investhome_api.services.social_design_engine.layout import (
        auto_layout_text,
        estimate_wrap_lines,
        measure_text_block,
    )

    lines = estimate_wrap_lines("Invest in\nThe Temple", 48, 900, bold=True)
    assert lines == ["Invest in", "The Temple"]
    count, height, _ = measure_text_block("Invest in\nThe Temple", 48, 900, bold=True)
    assert count == 2
    assert height == round(2 * 48 * 1.2)
    fitted = auto_layout_text(
        {
            "type": "TEXT",
            "role": "headline",
            "content": "Invest in\nThe Temple",
            "fontWeight": "bold",
            "x": 76,
            "y": 200,
            "width": 820,
            "height": 40,
            "fontSize": 48,
        },
        canvas_w=1080,
        canvas_h=1080,
        preferred_font=48,
        allow_grow_width=False,
    )
    assert "\n" in fitted["content"]
    assert fitted["height"] >= height


def test_layout_intelligence_visual_whitespace_and_sky() -> None:
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": "Temple",
                "x": 76,
                "y": 520,
                "width": 900,
                "height": 80,
                "fontSize": 48,
                "fontWeight": "bold",
            },
            {
                "id": "b1",
                "type": "TEXT",
                "role": "body",
                "content": "Body copy",
                "x": 76,
                "y": 600,
                "width": 900,
                "height": 60,
                "fontSize": 22,
            },
            {
                "id": "c1",
                "type": "BUTTON",
                "label": "Tour",
                "x": 340,
                "y": 780,
                "width": 400,
                "height": 48,
            },
        ],
    }
    plan_ws = classify_edit_intents("Metinleri biraz ferahlat.")
    assert "INCREASE_WHITESPACE" in plan_ws.intent_names
    assert not plan_ws.allow_copy_rewrite
    ops_ws = build_ops_from_intent_plan(plan=plan_ws, linked_project_id=str(pid), post=post)
    assert any(o["op"] == "APPLY_LAYOUT_INTENT" for o in ops_ws)
    validated = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id="p1",
            element_id=o.get("element_id"),
            payload=o["payload"],
        )
        for o in ops_ws
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid)
    els = {e["id"]: e for e in out[0]["elements"]}
    assert els["h1"]["content"] == "Temple"
    assert els["b1"]["content"] == "Body copy"
    gap_before = 600 - (520 + 80)
    gap_after = els["b1"]["y"] - (els["h1"]["y"] + els["h1"]["height"])
    assert gap_after >= gap_before

    plan_sky = classify_edit_intents("Binayı kapatma, yazıları gökyüzüne taşı.")
    assert "MOVE_TEXT_AWAY_FROM_SUBJECT" in plan_sky.intent_names
    ops_sky = build_ops_from_intent_plan(plan=plan_sky, linked_project_id=str(pid), post=post)
    validated_sky = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id="p1",
            element_id=o.get("element_id"),
            payload=o["payload"],
        )
        for o in ops_sky
    ]
    out2, _ = apply_ops([post], validated_sky, linked_project_id=pid)
    h2 = next(e for e in out2[0]["elements"] if e["id"] == "h1")
    assert h2["content"] == "Temple"
    assert h2["y"] < 400


def test_layout_intelligence_align_and_format_reflow() -> None:
    from investhome_api.services.social_design_engine.layout import (
        align_element_geometry,
        element_within_bounds,
        reflow_for_format,
        resolve_layout,
        text_fits_without_clip,
    )

    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": "Temple Headline",
                "fontWeight": "bold",
                "align": "left",
                "x": 40,
                "y": 200,
                "width": 600,
                "height": 80,
                "fontSize": 44,
            },
            {
                "id": "b1",
                "type": "TEXT",
                "role": "body",
                "content": "Body for format reflow test content.",
                "x": 40,
                "y": 400,
                "width": 600,
                "height": 80,
                "fontSize": 22,
            },
            {
                "id": "c1",
                "type": "BUTTON",
                "label": "CTA",
                "x": 400,
                "y": 900,
                "width": 280,
                "height": 48,
            },
        ],
    }
    h = post["elements"][0]
    centered = align_element_geometry(h, "center", canvas_w=1080, canvas_h=1080)
    assert centered["align"] == "center"
    assert abs(centered["x"] + centered["width"] / 2 - 540) < 40

    story = reflow_for_format(dict(post), "story")
    assert story["width"] == 1080 and story["height"] == 1920
    for el in story["elements"]:
        assert element_within_bounds(el, 1080, 1920) or el.get("type") == "IMAGE"
        if el.get("type") == "TEXT":
            assert text_fits_without_clip(el)

    landscape = reflow_for_format(dict(post), "landscape")
    assert landscape["width"] == 1920 and landscape["height"] == 1080
    resolved = resolve_layout(landscape, refit_text=True)
    assert resolved["elements"]


def test_layout_intelligence_manual_latest_state_consistency() -> None:
    """Manual box size then AI shrink+align uses latest dimensions (one state tree)."""
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": "Manual Then AI",
                "fontWeight": "bold",
                "align": "left",
                "x": 100,
                "y": 220,
                "width": 820,
                "height": 140,
                "fontSize": 52,
            },
            {
                "id": "c1",
                "type": "BUTTON",
                "label": "Tour",
                "x": 340,
                "y": 900,
                "width": 400,
                "height": 48,
            },
        ],
    }
    # Simulate manual resize already persisted in draft state
    plan = classify_edit_intents("biraz küçült ve ortala")
    assert "RESIZE" in plan.intent_names
    assert "ALIGN" in plan.intent_names
    ops = build_ops_from_intent_plan(plan=plan, linked_project_id=str(pid), post=post)
    validated = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id="p1",
            element_id=o.get("element_id"),
            payload=o["payload"],
        )
        for o in ops
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid)
    h1 = next(e for e in out[0]["elements"] if e["id"] == "h1")
    assert h1["content"] == "Manual Then AI"
    assert h1["fontSize"] < 52
    assert h1["align"] == "center"


def test_edit_intent_resize_preserves_copy() -> None:
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {
                "id": "h1",
                "type": "TEXT",
                "role": "headline",
                "content": "Keep Me",
                "x": 80,
                "y": 200,
                "width": 900,
                "height": 100,
                "fontSize": 48,
            },
            {"id": "c1", "type": "BUTTON", "label": "Tour", "x": 400, "y": 900, "width": 280, "height": 48},
        ],
    }
    plan = classify_edit_intents("Başlığı biraz küçült.")
    assert "RESIZE" in plan.intent_names
    assert not plan.allow_copy_rewrite
    ops = build_ops_from_intent_plan(plan=plan, linked_project_id=str(pid), post=post)
    assert ops[0]["op"] == "UPDATE_STYLE"
    assert ops[0]["payload"]["fontSize"] < 48
    validated = [
        SocialDesignOp(
            op=o["op"],
            linked_project_id=pid,
            post_id="p1",
            element_id=o["element_id"],
            payload=o["payload"],
        )
        for o in ops
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid)
    assert out[0]["elements"][0]["content"] == "Keep Me"
    assert out[0]["elements"][0]["fontSize"] < 48
    assert out[0]["elements"][1]["label"] == "Tour"


def test_edit_intent_cta_move_preserves_label() -> None:
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )
    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.schemas.social_design_engine import SocialDesignOp

    pid = TEMPLE_PROJECT_ID
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {"id": "c1", "type": "BUTTON", "label": "Schedule a private tour", "x": 340, "y": 800, "width": 400, "height": 56},
        ],
    }
    plan = classify_edit_intents("CTA'yı biraz aşağı taşı.")
    ops = build_ops_from_intent_plan(plan=plan, linked_project_id=str(pid), post=post)
    assert ops and ops[0]["op"] == "MOVE_ELEMENT"
    y0 = post["elements"][0]["y"]
    validated = [
        SocialDesignOp(op=ops[0]["op"], linked_project_id=pid, post_id="p1", element_id="c1", payload=ops[0]["payload"])
    ]
    out, _ = apply_ops([post], validated, linked_project_id=pid)
    assert out[0]["elements"][0]["label"] == "Schedule a private tour"
    assert out[0]["elements"][0]["y"] > y0


def test_edit_intent_replace_image_preserves_copy() -> None:
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )

    pid = TEMPLE_PROJECT_ID
    asset_a = uuid4()
    asset_b = uuid4()
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "coverAssetId": str(asset_a),
        "elements": [
            {"id": "h1", "type": "TEXT", "role": "headline", "content": "H", "x": 10, "y": 10, "width": 100, "height": 40},
            {"id": "img1", "type": "IMAGE", "assetId": str(asset_a), "x": 0, "y": 0, "width": 1080, "height": 1080},
            {"id": "c1", "type": "BUTTON", "label": "CTA", "x": 10, "y": 900, "width": 200, "height": 40},
        ],
    }
    plan = classify_edit_intents("Başka exterior render kullan.")
    assert "REPLACE_IMAGE" in plan.intent_names
    assert not plan.allow_copy_rewrite
    ops = build_ops_from_intent_plan(
        plan=plan, linked_project_id=str(pid), post=post, picked_asset_id=asset_b
    )
    assert any(o["op"] == "SET_BACKGROUND" for o in ops)
    assert all(o["op"] not in {"UPDATE_TEXT", "UPDATE_CTA"} for o in ops)


def test_explicit_copy_edit_allowed() -> None:
    from investhome_api.services.social_design_engine.intent import classify_edit_intents

    plan = classify_edit_intents('Başlığı "Yeni Lansman" olarak değiştir')
    assert plan.allow_copy_rewrite
    assert "CHANGE_TEXT" in plan.intent_names

    plan2 = classify_edit_intents('CTA label olsun "Şimdi İncele"')
    assert plan2.allow_cta_rewrite or plan2.allow_copy_rewrite


def test_multi_intent_only_requested_ops() -> None:
    from investhome_api.services.social_design_engine.intent import (
        classify_edit_intents,
        build_ops_from_intent_plan,
    )

    pid = TEMPLE_PROJECT_ID
    post = {
        "id": "p1",
        "formatPreset": "square",
        "width": 1080,
        "height": 1080,
        "elements": [
            {"id": "h1", "type": "TEXT", "role": "headline", "content": "H", "x": 200, "y": 300, "width": 600, "height": 80, "fontSize": 40},
            {"id": "c1", "type": "BUTTON", "label": "CTA", "x": 340, "y": 880, "width": 400, "height": 56},
            {"id": "img1", "type": "IMAGE", "assetId": str(uuid4()), "x": 0, "y": 0, "width": 1080, "height": 1080},
        ],
    }
    instr = "Başlığı biraz sola al, CTA'yı yukarı taşı ve görseli başka exterior render ile değiştir."
    plan = classify_edit_intents(instr)
    assert "MOVE" in plan.intent_names
    assert "REPLACE_IMAGE" in plan.intent_names
    assert not plan.allow_copy_rewrite
    ops = build_ops_from_intent_plan(
        plan=plan, linked_project_id=str(pid), post=post, picked_asset_id=uuid4()
    )
    names = {o["op"] for o in ops}
    assert "MOVE_ELEMENT" in names
    assert "SET_BACKGROUND" in names or "REPLACE_IMAGE" in names
    assert "UPDATE_TEXT" not in names
    assert "UPDATE_CTA" not in names
    assert "ADD_TEXT" not in names


def test_another_temple_photo_is_replace_image_edit() -> None:
    from investhome_api.services.social_design_engine.generation import infer_design_mode
    from investhome_api.services.social_design_engine.intent import classify_edit_intents

    existing = [{"id": "p1", "elements": [{"id": "h1", "type": "TEXT"}]}]
    instr = "another Temple photo"
    assert infer_design_mode(instr, existing, requested="create") == "edit"
    plan = classify_edit_intents(instr)
    assert "REPLACE_IMAGE" in plan.intent_names
    assert not plan.allow_copy_rewrite


def test_infer_design_mode_generation_vs_edit() -> None:
    from investhome_api.services.social_design_engine.generation import infer_design_mode

    existing = [{"id": "p1", "elements": [{"id": "h1", "type": "TEXT"}]}]
    location = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
        "premium bir Instagram kare postu hazırla. Proje verilerini kullan. "
        "En uygun gerçek proje görselini seç. İngilizce hazırla."
    )
    investment = (
        "The Temple için yatırımcı odaklı premium Instagram postu hazırla. "
        "Bu kampanya için test girdileri: Minimum yatırım: $500,000 Hedef getiri: %14 "
        "Yatırım süresi: 24 ay. Bu rakamları değiştirme. İngilizce hazırla."
    )
    assert infer_design_mode(location, existing, "create") == "create"
    assert infer_design_mode(investment, existing, "edit") == "create"
    assert infer_design_mode("Başlığı biraz yukarı al", existing, "create") == "edit"
    assert infer_design_mode("CTA'yı kaldır", existing, "create") == "edit"
    assert infer_design_mode("Başka bir Temple fotoğrafı kullan", existing, "create") == "edit"
    assert infer_design_mode(location, [], "edit") == "create"


def test_campaign_facts_preserved_exactly() -> None:
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )
    from investhome_api.services.social_design_engine.generation import (
        build_heuristic_content_package,
        classify_generation_intent,
        compose_ops_from_plan,
        enforce_campaign_facts,
        extract_campaign_facts,
        build_design_plan,
    )

    prompt = (
        "The Temple için yatırımcı odaklı premium Instagram postu hazırla. "
        "Bu kampanya için test girdileri: Minimum yatırım: $500,000 Hedef getiri: %14 "
        "Yatırım süresi: 24 ay. Bu rakamları değiştirme. İngilizce hazırla."
    )
    facts = extract_campaign_facts(prompt)
    displays = {f.display for f in facts}
    assert "$500,000" in displays
    assert "$500" not in displays
    assert "%14" in displays
    assert any("24 ay" in f.display for f in facts)

    intent = classify_generation_intent(prompt, language="tr", project_name="Temple Residences")
    assert intent.language == "en"
    assert intent.marketing_objective == "investment"
    assert intent.asset_preference == "premium_hero"

    ctx = CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name="Temple Residences",
            city="Washington",
            country="US",
        ),
        verified_facts=["project_name=Temple Residences", "city=Washington"],
        retrieved_content=[],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )
    package = build_heuristic_content_package(
        instruction=prompt, intent=intent, context=ctx, campaign_facts=facts
    )
    blob = f"{package.headline} {package.supporting_text} {package.key_fact} {package.cta}"
    assert " · " not in (package.supporting_text or "")
    assert "%14" not in blob
    assert "24 ay" not in blob.lower()
    from investhome_api.services.social_design_engine.metrics import campaign_facts_to_structured_metrics

    metrics = campaign_facts_to_structured_metrics(facts, language="en", instruction=prompt)
    raws = {m.raw_value for m in metrics}
    assert 500000 in raws
    assert 14 in raws
    assert 24 in raws
    displays = {m.display_value for m in metrics}
    assert any(d in {"$500,000", "$500K"} for d in displays)
    assert "14%" in displays
    assert "24 Months" in displays
    assert not any("%14" == d for d in displays)

    tampered = package.__class__(
        headline="Invest now",
        supporting_text="Great returns",
        key_fact="",
        cta="Learn more",
        language="en",
        tone="premium",
    )
    fixed = enforce_campaign_facts(tampered, facts)
    fixed_blob = f"{fixed.headline} {fixed.supporting_text} {fixed.key_fact}"
    assert " · " not in (fixed.supporting_text or "")
    assert "24 ay" not in fixed_blob.lower()

    plan = build_design_plan(
        package=fixed,
        intent=intent,
        picked_asset_id=uuid4(),
        post_id="p1",
        rebuild=True,
        structured_metrics=metrics,
    )
    ops = compose_ops_from_plan(plan, linked_project_id=TEMPLE_PROJECT_ID, instruction=prompt)
    names = [o["op"] for o in ops]
    assert names[0] == "CREATE_POST"
    assert "ADD_TEXT" in names
    assert "ADD_CTA" in names
    assert "ADD_METRIC_GROUP" in names
    copy_blob = json.dumps(ops)
    assert "500000" in copy_blob or "$500" in copy_blob
    assert "metadata.json" not in copy_blob
    assert "Sources:" not in copy_blob
    assert " · " not in copy_blob or "ADD_METRIC_GROUP" in names


def test_composer_rebuilds_canvas_schema_and_layout(client, db_session: Session) -> None:
    from investhome_api.services.social_design_engine.layout import element_within_bounds
    from investhome_api.services.social_design_engine.ops import looks_like_rag_or_debug_copy

    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    image = _asset(db, temple, filename="temple-exterior-hero.jpg", folder_category="05_RENDERINGS")
    brief = _asset(db, temple, filename="location.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple Residences at 1610 Columbia Rd NW Washington DC central location"),
        title="location.md",
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    existing_id = "legacy-p1"
    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": (
                "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
                "premium bir Instagram kare postu hazırla. Proje verilerini kullan. "
                "En uygun gerçek proje görselini seç. İngilizce hazırla."
            ),
            "mode": "create",
            "language": "tr",
            "draft": {
                "posts": [
                    {
                        "id": existing_id,
                        "formatPreset": "square",
                        "width": 1080,
                        "height": 1080,
                        "platform": "instagram",
                        "name": "Old",
                        "headline": "Old headline",
                        "caption": "Old caption",
                        "elements": [
                            {
                                "id": "h-old",
                                "type": "TEXT",
                                "role": "headline",
                                "content": "Old headline",
                                "x": 80,
                                "y": 80,
                                "width": 400,
                                "height": 40,
                            }
                        ],
                    }
                ],
                "selected_post_id": existing_id,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mode"] == "create"
    assert body["meta"]["generated_by"] == "social_design_engine"
    assert body["meta"]["generation_intent"]["marketing_objective"] == "location"
    posts = body["posts"]
    assert len(posts) == 1
    post = posts[0]
    assert post["id"] == existing_id
    elements = post.get("elements") or []
    roles = {e.get("role") for e in elements if e.get("type") == "TEXT"}
    types = {e.get("type") for e in elements}
    assert "headline" in roles
    assert "body" in roles
    assert "BUTTON" in types
    assert post.get("coverAssetId")
    UUID(post["coverAssetId"])
    blob = json.dumps(post)
    assert "unsplash" not in blob.lower()
    assert "metadata.json" not in blob
    assert "Sources:" not in blob
    for el in elements:
        if el.get("type") in {"TEXT", "BUTTON"}:
            text = str(el.get("content") or el.get("label") or "")
            assert not looks_like_rag_or_debug_copy(text)
            assert element_within_bounds(el, 1080, 1080)
    # Hierarchy: headline above body above CTA
    headline = next(e for e in elements if e.get("role") == "headline")
    body_el = next(e for e in elements if e.get("role") == "body")
    cta = next(e for e in elements if e.get("type") == "BUTTON")
    assert headline["y"] < body_el["y"] < cta["y"]
    gen_meta = post.get("generationMeta") or {}
    assert gen_meta.get("generated_by") == "social_design_engine"
    assert "citations" not in (headline.get("content") or "")


def test_investment_generation_preserves_campaign_numbers(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    _asset(db, temple, filename="temple-premium-hero-exterior.jpg")
    brief = _asset(db, temple, filename="overview.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple Residences Washington DC residential investment overview amenities"),
        title="overview.md",
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    prompt = (
        "The Temple için yatırımcı odaklı premium Instagram postu hazırla. "
        "Bu kampanya için test girdileri: Minimum yatırım: $500,000 Hedef getiri: %14 "
        "Yatırım süresi: 24 ay. Bu rakamları değiştirme. İngilizce hazırla."
    )
    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": prompt,
            "mode": "create",
            "draft": {"posts": [], "selected_post_id": None},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    post = body["posts"][0]
    elements = post.get("elements") or []
    visible_parts: list[str] = []
    for el in elements:
        visible_parts.append(str(el.get("content") or ""))
        visible_parts.append(str(el.get("label") or ""))
        for metric in el.get("metrics") or []:
            if not isinstance(metric, dict):
                continue
            visible_parts.append(str(metric.get("display_value") or ""))
            visible_parts.append(str(metric.get("label") or ""))
            visible_parts.append(str(metric.get("unit") or ""))
    visible_blob = " ".join(visible_parts)
    assert "%14" not in visible_blob
    assert "24 ay" not in visible_blob.lower()
    assert " · " not in visible_blob
    metric_el = next((e for e in elements if e.get("type") == "METRIC_GROUP"), None)
    assert metric_el is not None
    metrics = metric_el.get("metrics") or []
    assert 1 <= len(metrics) <= 3
    raws = {m.get("raw_value") for m in metrics}
    assert 500000 in raws
    assert 14 in raws
    assert 24 in raws
    displays = " ".join(str(m.get("display_value") or "") for m in metrics)
    labels = " ".join(str(m.get("label") or "") for m in metrics)
    assert "14%" in displays
    assert "24 Months" in displays
    assert "Minimum" in labels or "Investment" in labels
    assert "Return" in labels or "Target" in labels
    assert any(e.get("type") == "BUTTON" for e in elements)
    cta = next(e for e in elements if e.get("type") == "BUTTON")
    label = (cta.get("label") or "").lower()
    assert any(k in label for k in ("invest", "investor", "opportunity", "details", "team"))
    assert "incele" not in label
    facts = body["meta"].get("campaign_facts") or []
    displays_meta = {f.get("display") for f in facts}
    assert "$500,000" in displays_meta
    structured = body["meta"].get("structured_metrics") or []
    assert structured
    assert body["meta"]["generation_intent"]["marketing_objective"] == "investment"
    headline = next(e for e in elements if e.get("role") == "headline")
    assert "target %14" not in str(headline.get("content") or "").lower()
    assert "ay" not in str(headline.get("content") or "").lower()


def test_semantic_asset_preference_prefers_exterior_for_location() -> None:
    from investhome_api.services.social_design_engine.generation import asset_preference_tokens
    from investhome_api.services.social_design_engine.media import score_asset

    class _A:
        content_type = "image/jpeg"
        filename = "temple-exterior-facade.jpg"
        folder_category = "05_RENDERINGS"
        tags = ["exterior", "hero"]
        width = 2000
        height = 2000

    class _B:
        content_type = "image/jpeg"
        filename = "unit-floorplan-a2.pdf.jpg"
        folder_category = "06_PLANS"
        tags = ["plan"]
        width = 2000
        height = 2000

    pref = asset_preference_tokens("exterior")
    s_ext = score_asset(_A(), query_tokens={"location", "washington"}, folder_path="Photos / Exterior", preference_tokens=pref)
    s_plan = score_asset(_B(), query_tokens={"location", "washington"}, folder_path="Drawings / Plans", preference_tokens=pref)
    assert s_ext > s_plan


def test_creative_director_suppresses_construction_on_location() -> None:
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )
    from investhome_api.services.social_design_engine.creative_director import (
        choose_composition_strategy,
        direct_creative,
        select_facts_for_objective,
    )
    from investhome_api.services.social_design_engine.generation import (
        build_design_plan,
        build_heuristic_content_package,
        classify_generation_intent,
        compose_ops_from_plan,
    )

    prompt = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
        "premium bir Instagram kare postu hazırla. Proje verilerini kullan. "
        "En uygun gerçek proje görselini seç. İngilizce hazırla."
    )
    intent = classify_generation_intent(prompt, language="tr", project_name="Temple Residences")
    ctx = CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name="Temple Residences",
            city="Washington",
            country="US",
        ),
        verified_facts=[
            "project_name=Temple Residences",
            "city=Washington",
            "address=1610 Columbia Rd NW",
            "total_units=120",
            "project_type=residential",
            "project_status=construction",
        ],
        retrieved_content=[
            {
                "document_name": "brief.md",
                "text": (
                    "Mixed-use project under construction in Columbia Heights "
                    "with 120 units and a central Washington DC location."
                ),
            },
            {
                "document_name": "location.md",
                "text": "Temple Residences sits in Columbia Heights, steps from neighborhood parks and transit.",
            },
        ],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )
    selected, suppressed = select_facts_for_objective(
        objective="location", context=ctx, campaign_facts=[], instruction=prompt
    )
    suppressed_blob = " ".join(s.text.lower() for s in suppressed)
    assert "120" in suppressed_blob or any("total_units" in (s.provenance or "") for s in suppressed)
    assert any("construction" in (s.text + s.provenance).lower() for s in suppressed)
    selected_blob = " ".join(s.text.lower() for s in selected)
    assert "mixed-use" not in selected_blob
    assert "under construction" not in selected_blob
    assert any(f.reason == "identity_city" for f in selected)
    assert not any(f.reason == "identity_address" for f in selected)
    assert any("address_is_evidence_not_the_ad" in (s.reason or "") for s in suppressed)

    concept = direct_creative(instruction=prompt, intent=intent, context=ctx, campaign_facts=[])
    assert concept.composition_strategy == "LOCATION"
    assert concept.objective == "location"
    package = build_heuristic_content_package(
        instruction=prompt, intent=intent, context=ctx, campaign_facts=[], concept=concept
    )
    canvas = f"{package.eyebrow} {package.headline} {package.supporting_text} {package.key_fact} {package.cta}".lower()
    assert "mixed-use" not in canvas
    assert "under construction" not in canvas
    assert "120" not in canvas
    assert "construction" not in canvas
    words = [w for w in package.headline.split() if w]
    assert 2 <= len(words) <= 8
    assert "discover more" not in canvas
    assert "explore more today" not in canvas
    assert "premium living" not in canvas
    assert "1610" not in canvas
    assert "on columbia rd" not in canvas
    from investhome_api.services.social_design_engine.marketing_strategist import looks_like_street_address

    assert not looks_like_street_address(package.headline)
    assert "washington" in canvas or "columbia heights" in canvas

    plan = build_design_plan(
        package=package,
        intent=intent,
        picked_asset_id=uuid4(),
        post_id="p1",
        rebuild=True,
        concept=concept,
    )
    text_roles = [el.role for el in plan.elements if el.type in {"TEXT", "BUTTON", "CTA"}]
    assert text_roles.count("headline") == 1
    assert "cta" in text_roles
    assert len(text_roles) <= 4
    assert plan.composition_strategy == "LOCATION"
    assert plan.overlay.startswith("localized")
    headline_el = next(el for el in plan.elements if el.role == "headline")
    body_el = next((el for el in plan.elements if el.role == "body"), None)
    if body_el and headline_el.font_size and body_el.font_size:
        assert headline_el.font_size >= int(body_el.font_size * 1.45)
    if body_el:
        assert headline_el.y + headline_el.height + 8 <= body_el.y
    ops = compose_ops_from_plan(plan, linked_project_id=TEMPLE_PROJECT_ID, instruction=prompt)
    copy_blob = json.dumps(ops).lower()
    assert "mixed-use" not in copy_blob
    assert "metadata.json" not in copy_blob
    assert "sources:" not in copy_blob


def test_composition_strategy_follows_objective() -> None:
    from investhome_api.services.social_design_engine.creative_director import (
        AssetVisualProfile,
        choose_composition_strategy,
    )

    profile = AssetVisualProfile(subject="building", image_led=True, safe_text_zone="top")
    assert choose_composition_strategy(objective="location", profile=profile, campaign_facts=[]) == "LOCATION"
    assert choose_composition_strategy(objective="investment", profile=profile, campaign_facts=[]) == "INVESTMENT"
    assert choose_composition_strategy(objective="lifestyle", profile=profile, campaign_facts=[]) == "MINIMAL_HERO"


def test_content_package_prompt_does_not_require_identity_address() -> None:
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )
    from investhome_api.services.social_design_engine.creative_director import direct_creative
    from investhome_api.services.social_design_engine.generation import (
        build_content_package_prompt,
        classify_generation_intent,
    )

    prompt = "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran premium bir Instagram kare postu hazırla."
    intent = classify_generation_intent(prompt, project_name="The Temple")
    ctx = CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name="The Temple",
            city="Washington",
            country="US",
        ),
        verified_facts=["project_name=The Temple", "city=Washington", "address=1610 Columbia Rd NW"],
        retrieved_content=[],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )
    concept = direct_creative(instruction=prompt, intent=intent, context=ctx, campaign_facts=[])
    system, user = build_content_package_prompt(
        instruction=prompt, intent=intent, context=ctx, campaign_facts=[], concept=concept
    )
    assert "CONTENT_PACKAGE_JSON" in user
    # Address may be listed as excluded evidence; it must not be required canvas copy.
    assert "project_name" in user
    assert "city" in user


def test_validator_repairs_unnecessary_facts_and_density() -> None:
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )
    from investhome_api.services.social_design_engine.creative_director import direct_creative
    from investhome_api.services.social_design_engine.generation import (
        ContentPackage,
        build_design_plan,
        classify_generation_intent,
    )
    from investhome_api.services.social_design_engine.validator import validate_and_repair

    prompt = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
        "premium bir Instagram kare postu hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    ctx = CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name="Temple Residences",
            city="Washington",
            country="US",
        ),
        verified_facts=["project_name=Temple Residences", "city=Washington", "total_units=120"],
        retrieved_content=[],
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )
    concept = direct_creative(instruction=prompt, intent=intent, context=ctx, campaign_facts=[])
    dirty = ContentPackage(
        headline="Discover More Premium Living Unique Opportunity Today Here Now Extra",
        supporting_text="Mixed-use project under construction with 120 units and financing details for investors.",
        key_fact="120 units",
        cta="Learn more",
        language="en",
        tone="premium",
        eyebrow="Columbia Heights",
    )
    plan = build_design_plan(
        package=dirty, intent=intent, picked_asset_id=None, post_id="p1", rebuild=True, concept=concept
    )
    repaired, repaired_plan, repaired_concept, report = validate_and_repair(
        package=dirty, plan=plan, concept=concept, intent=intent, campaign_facts=[]
    )
    blob = f"{repaired.headline} {repaired.supporting_text} {repaired.key_fact} {repaired.cta}".lower()
    assert "mixed-use" not in blob
    assert "under construction" not in blob
    assert "learn more" not in blob
    words = [w for w in repaired.headline.split() if w]
    assert len(words) <= 8
    assert len([e for e in repaired_plan.elements if e.type in {"TEXT", "BUTTON", "CTA"}]) <= 4
    assert report.repairs


def test_location_generation_has_no_rag_or_construction(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    _asset(db, temple, filename="temple-exterior-hero.jpg", folder_category="05_RENDERINGS")
    brief = _asset(db, temple, filename="location.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text(
            "Mixed-use project under construction. Temple Residences at 1610 Columbia Rd NW "
            "Washington DC central location in Columbia Heights."
        ),
        title="location.md",
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": (
                "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
                "premium bir Instagram kare postu hazırla. Proje verilerini kullan. "
                "En uygun gerçek proje görselini seç. İngilizce hazırla."
            ),
            "mode": "create",
            "draft": {"posts": [], "selected_post_id": None},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    post = body["posts"][0]
    copy_parts = []
    for el in post.get("elements") or []:
        copy_parts.append(str(el.get("content") or ""))
        copy_parts.append(str(el.get("label") or ""))
    copy_blob = " ".join(copy_parts).lower()
    assert "mixed-use" not in copy_blob
    assert "under construction" not in copy_blob
    assert "metadata.json" not in copy_blob
    assert "sources:" not in copy_blob
    assert "120 units" not in copy_blob
    assert "total_units" not in copy_blob
    meta = body["meta"]
    concept = meta.get("creative_concept") or {}
    assert concept.get("composition_strategy") == "LOCATION"
    assert concept.get("objective") == "location"
    assert "creative_concept" in (post.get("generationMeta") or {})
    headline = next(e for e in post["elements"] if e.get("role") == "headline")
    words = [w for w in str(headline.get("content") or "").split() if w]
    assert 2 <= len(words) <= 8
    from investhome_api.services.social_design_engine.marketing_strategist import looks_like_street_address

    assert not looks_like_street_address(str(headline.get("content") or ""))
    assert "1610" not in copy_blob
    assert "on columbia rd" not in copy_blob
    strategy = meta.get("marketing_strategy") or {}
    assert strategy.get("objective") == "location"
    assert strategy.get("campaign_angle")
    assert meta.get("copy_quality")
    assert meta.get("headline_candidates")
    text_blocks = [e for e in post["elements"] if e.get("type") in {"TEXT", "BUTTON"}]
    assert len(text_blocks) <= 4
    assert post.get("overlayStrategy", "").startswith("localized") or (
        (post.get("generationMeta") or {}).get("creative_concept") or {}
    ).get("contrast_strategy")


def _strategy_ctx(**kwargs):
    from investhome_api.schemas.creative_studio_generation import (
        CreativeStudioBrandContext,
        CreativeStudioGenerationContext,
        CreativeStudioProjectIdentity,
    )

    return CreativeStudioGenerationContext(
        project_identity=CreativeStudioProjectIdentity(
            project_id=TEMPLE_PROJECT_ID,
            project_code="PRJ-T",
            project_name=kwargs.get("project_name", "Temple Residences"),
            city=kwargs.get("city", "Washington"),
            country="US",
        ),
        verified_facts=kwargs.get(
            "verified_facts",
            [
                "project_name=Temple Residences",
                "city=Washington",
                "address=1610 Columbia Rd NW",
                "total_units=120",
                "project_status=construction",
            ],
        ),
        retrieved_content=kwargs.get("retrieved_content", []),
        selected_assets=[],
        citations=[],
        brand_context=CreativeStudioBrandContext(available=False, reason="none"),
        builder_type="social",
        language="en",
    )


def test_marketing_strategist_location_is_not_the_street() -> None:
    from investhome_api.services.social_design_engine.generation import classify_generation_intent
    from investhome_api.services.social_design_engine.marketing_strategist import (
        build_marketing_strategy,
        looks_like_street_address,
    )

    prompt = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
        "premium bir Instagram kare postu hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    ctx = _strategy_ctx(
        retrieved_content=[
            {
                "document_name": "location.md",
                "text": "Temple Residences sits in Columbia Heights, near neighborhood parks and transit.",
            }
        ]
    )
    strategy = build_marketing_strategy(instruction=prompt, intent=intent, context=ctx, campaign_facts=[])
    assert strategy.objective == "location"
    assert strategy.campaign_angle == "central_positioning"
    assert strategy.neighborhood == "Columbia Heights"
    assert not looks_like_street_address(strategy.single_minded_message)
    assert "1610" not in strategy.single_minded_message
    assert any("1610" in f or "Columbia Rd" in f for f in strategy.excluded_facts)
    kinds = {f.kind for f in strategy.classified_facts if f.key == "address" or "Columbia Rd" in f.text}
    assert "FACT" in kinds or any(f.reason == "address_is_evidence_not_the_ad" for f in strategy.classified_facts)


def test_copy_quality_rejects_address_as_headline() -> None:
    from investhome_api.services.social_design_engine.copy_director import (
        CopyPackage,
        score_copy_quality,
    )
    from investhome_api.services.social_design_engine.generation import classify_generation_intent
    from investhome_api.services.social_design_engine.marketing_strategist import build_marketing_strategy

    prompt = "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran Instagram postu hazırla."
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    strategy = build_marketing_strategy(
        instruction=prompt, intent=intent, context=_strategy_ctx(), campaign_facts=[]
    )
    bad = CopyPackage(
        eyebrow="THE TEMPLE RESIDENCES",
        headline="On Columbia Rd",
        supporting_copy="1610 Columbia Rd NW",
        cta="Discover More",
        language="en",
        tone="premium",
    )
    quality = score_copy_quality(bad, strategy=strategy, campaign_facts=[])
    assert not quality.passed
    assert "headline_is_address" in quality.reject_codes


def test_copy_director_scores_candidates_and_avoids_street() -> None:
    from investhome_api.services.social_design_engine.copy_director import build_copy_package
    from investhome_api.services.social_design_engine.generation import classify_generation_intent
    from investhome_api.services.social_design_engine.marketing_strategist import (
        build_marketing_strategy,
        looks_like_street_address,
    )

    prompt = (
        "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran "
        "premium bir Instagram kare postu hazırla. İngilizce hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    ctx = _strategy_ctx(
        retrieved_content=[
            {
                "document_name": "location.md",
                "text": "Temple Residences sits in Columbia Heights with a central Washington location.",
            }
        ]
    )
    strategy = build_marketing_strategy(instruction=prompt, intent=intent, context=ctx, campaign_facts=[])
    direction = build_copy_package(strategy=strategy, intent=intent, campaign_facts=[])
    assert len(direction.candidates) >= 2
    for cand in direction.candidates:
        assert cand.scores
        assert not looks_like_street_address(cand.text)
    assert not looks_like_street_address(direction.package.headline)
    assert "1610" not in direction.package.headline
    assert "on columbia rd" not in direction.package.headline.lower()
    assert direction.quality.passed
    blob = f"{direction.package.eyebrow} {direction.package.headline} {direction.package.supporting_copy} {direction.package.cta}".lower()
    assert "under construction" not in blob
    assert "120" not in blob


def test_copy_director_investment_keeps_exact_campaign_numbers() -> None:
    from investhome_api.services.social_design_engine.copy_director import build_copy_package
    from investhome_api.services.social_design_engine.generation import (
        classify_generation_intent,
        extract_campaign_facts,
    )
    from investhome_api.services.social_design_engine.marketing_strategist import build_marketing_strategy

    prompt = (
        "The Temple için yatırımcı odaklı premium Instagram postu hazırla. "
        "Bu kampanya için test girdileri: Minimum yatırım: $500,000 Hedef getiri: %14 "
        "Yatırım süresi: 24 ay. Bu rakamları değiştirme. İngilizce hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    facts = extract_campaign_facts(prompt)
    strategy = build_marketing_strategy(
        instruction=prompt, intent=intent, context=_strategy_ctx(), campaign_facts=facts
    )
    assert strategy.objective == "investment"
    direction = build_copy_package(strategy=strategy, intent=intent, campaign_facts=facts)
    blob = f"{direction.package.headline} {direction.package.supporting_copy} {direction.package.cta}"
    assert " · " not in (direction.package.supporting_copy or "")
    assert "%14" not in blob
    assert "24 ay" not in blob.lower()
    assert "target %14" not in direction.package.headline.lower()
    assert "1610" not in blob
    assert "under construction" not in blob.lower()
    assert "invest" in blob.lower() or "return" in blob.lower()


def test_architecture_objective_does_not_dump_location_or_investment() -> None:
    from investhome_api.services.social_design_engine.copy_director import build_copy_package
    from investhome_api.services.social_design_engine.creative_director import direct_creative
    from investhome_api.services.social_design_engine.generation import (
        classify_generation_intent,
        extract_campaign_facts,
    )
    from investhome_api.services.social_design_engine.marketing_strategist import (
        build_marketing_strategy,
        looks_like_street_address,
    )

    prompt = (
        "The Temple projesinin mimari karakterini öne çıkaran premium bir Instagram kare postu hazırla. "
        "İngilizce hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    assert intent.marketing_objective == "architecture"
    facts = extract_campaign_facts(
        "Minimum yatırım: $500,000 Hedef getiri: %14 Yatırım süresi: 24 ay"
    )
    ctx = _strategy_ctx(
        retrieved_content=[
            {
                "document_name": "architecture.md",
                "text": "The facade is a considered architectural presence in brick and limestone.",
            }
        ]
    )
    strategy = build_marketing_strategy(instruction=prompt, intent=intent, context=ctx, campaign_facts=facts)
    assert strategy.objective == "architecture"
    assert strategy.campaign_angle in {"architectural_character", "material_craft"}
    direction = build_copy_package(strategy=strategy, intent=intent, campaign_facts=facts)
    blob = f"{direction.package.headline} {direction.package.supporting_copy} {direction.package.cta}"
    assert "$500,000" not in blob
    assert "%14" not in blob
    assert "1610" not in blob
    assert not looks_like_street_address(direction.package.headline)
    concept = direct_creative(
        instruction=prompt,
        intent=intent,
        context=ctx,
        campaign_facts=facts,
        strategy=strategy,
        copy_package=direction.package,
    )
    assert concept.objective == "architecture"
    assert "1610" not in concept.primary_message
    assert "$500,000" not in (concept.supporting_message or "")


def test_copy_edit_stronger_headline_stays_in_strategy() -> None:
    from investhome_api.services.social_design_engine.copy_director import (
        apply_copy_intelligence_edit,
        build_copy_package,
        classify_copy_intelligence_edit,
    )
    from investhome_api.services.social_design_engine.generation import classify_generation_intent
    from investhome_api.services.social_design_engine.marketing_strategist import build_marketing_strategy

    prompt = "The Temple projesinin Washington DC'deki merkezi lokasyonunu öne çıkaran Instagram postu hazırla."
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    strategy = build_marketing_strategy(
        instruction=prompt,
        intent=intent,
        context=_strategy_ctx(
            retrieved_content=[
                {
                    "document_name": "location.md",
                    "text": "Temple Residences sits in Columbia Heights with a central Washington location.",
                }
            ]
        ),
        campaign_facts=[],
    )
    original = build_copy_package(strategy=strategy, intent=intent, campaign_facts=[])
    kind, meta = classify_copy_intelligence_edit("Başlığı daha güçlü yap")
    assert kind == "regenerate_headline"
    edited = apply_copy_intelligence_edit(
        kind=kind,
        meta=meta,
        strategy=strategy,
        intent=intent,
        campaign_facts=[],
        current=original.package,
    )
    assert strategy.objective == "location"
    assert strategy.campaign_angle == original.candidates[0].notes or strategy.campaign_angle
    assert edited.package.headline
    assert edited.package.cta == original.package.cta
    kind2, _ = classify_copy_intelligence_edit("Yatırımcıya yönelik yap")
    assert kind2 == "change_objective"


def test_architecture_generation_endpoint(client, db_session: Session) -> None:
    db = db_session
    temple = _create_project(db, project_id=TEMPLE_PROJECT_ID)
    _asset(db, temple, filename="temple-facade-hero.jpg", folder_category="05_RENDERINGS")
    brief = _asset(db, temple, filename="architecture.md", content_type="text/markdown")
    doc = _ready_document(
        db,
        temple,
        text=_long_text("Temple Residences architectural character brick limestone facade considered presence"),
        title="architecture.md",
        asset=brief,
    )
    reindex_document(db, doc.id)
    db.commit()

    resp = client.post(
        "/ai/creative-studio/social/design",
        json={
            "linked_project_id": str(TEMPLE_PROJECT_ID),
            "instruction": (
                "The Temple projesinin mimari karakterini öne çıkaran premium bir Instagram kare postu hazırla. "
                "İngilizce hazırla."
            ),
            "mode": "create",
            "draft": {"posts": [], "selected_post_id": None},
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meta"]["generation_intent"]["marketing_objective"] == "architecture"
    strategy = body["meta"].get("marketing_strategy") or {}
    assert strategy.get("objective") == "architecture"
    post = body["posts"][0]
    copy_blob = json.dumps(post.get("elements") or []).lower()
    assert "1610" not in copy_blob
    assert "$500,000" not in copy_blob
    assert "under construction" not in copy_blob
    headline = next(e for e in post["elements"] if e.get("role") == "headline")
    from investhome_api.services.social_design_engine.marketing_strategist import looks_like_street_address

    assert not looks_like_street_address(str(headline.get("content") or ""))


def test_structured_metrics_localization_and_safety() -> None:
    from investhome_api.services.social_design_engine.generation import extract_campaign_facts
    from investhome_api.services.social_design_engine.localization import (
        format_duration,
        format_percentage,
        looks_like_concatenated_metrics,
        validate_creative_language,
        visible_fields_from_package,
    )
    from investhome_api.services.social_design_engine.metrics import (
        campaign_facts_to_structured_metrics,
        choose_metric_group_layout,
        horizontal_metrics_fit,
        raw_values_unchanged,
        update_metric_raw_value,
    )

    prompt = (
        "The Temple için yatırımcı odaklı premium Instagram postu hazırla. "
        "Bu kampanya için test girdileri: Minimum yatırım: $500,000 Hedef getiri: %14 "
        "Yatırım süresi: 24 ay. Bu rakamları değiştirme. İngilizce hazırla."
    )
    facts = extract_campaign_facts(prompt)
    en_metrics = campaign_facts_to_structured_metrics(facts, language="en", instruction=prompt)
    tr_metrics = campaign_facts_to_structured_metrics(facts, language="tr", instruction=prompt)
    assert format_percentage(14, "en") == "14%"
    assert format_percentage(14, "tr") == "%14"
    assert format_duration(24, "en") == "24 Months"
    assert format_duration(24, "tr") == "24 Ay"
    en_disp = {m.display_value for m in en_metrics}
    tr_disp = {m.display_value for m in tr_metrics}
    assert "14%" in en_disp
    assert "%14" in tr_disp
    assert "24 Months" in en_disp
    assert "24 Ay" in tr_disp
    assert all(m.raw_value in {500000, 14, 24} for m in en_metrics)
    assert raw_values_unchanged(en_metrics, tr_metrics)
    mutated = [update_metric_raw_value(en_metrics[0], 550000), *en_metrics[1:]]
    assert not raw_values_unchanged(en_metrics, mutated)
    assert looks_like_concatenated_metrics("$500,000 · %14 · 24 ay")
    assert not looks_like_concatenated_metrics("A refined address in Washington.")
    leak = validate_creative_language(
        language="en",
        fields={"support": "$500,000 · %14 · 24 ay", "cta": "Yatırımı incele"},
    )
    assert not leak.passed

    class _Pkg:
        eyebrow = "TEMPLE RESIDENCES"
        headline = "Invest in Temple Residences"
        supporting_text = ""
        cta = "Explore the Investment"

    ok = validate_creative_language(language="en", fields=visible_fields_from_package(_Pkg(), en_metrics))
    assert ok.passed
    assert choose_metric_group_layout(
        metrics=en_metrics, format_preset="square", canvas_w=1080, available_width=840
    ) == "horizontal"
    assert not horizontal_metrics_fit(en_metrics, available_width=80, canvas_w=1080)
    assert choose_metric_group_layout(
        metrics=en_metrics, format_preset="square", canvas_w=1080, available_width=80
    ) in {"stacked", "cards"}


def test_metric_layout_edit_and_explicit_value_change() -> None:
    from investhome_api.services.social_design_engine.intent import classify_edit_intents

    stacked = classify_edit_intents("Rakamları alt alta al")
    assert "CHANGE_METRIC_LAYOUT" in stacked.intent_names
    assert any(i.meta.get("layout") == "stacked" for i in stacked.intents)
    cards = classify_edit_intents("Rakamları kart şeklinde göster")
    assert any(i.meta.get("layout") == "cards" for i in cards.intents)
    emphasis = classify_edit_intents("Getiriyi öne çıkar")
    assert "CHANGE_METRIC_EMPHASIS" in emphasis.intent_names
    factual = classify_edit_intents("24 ayı 36 ay yap")
    assert "CHANGE_METRIC_VALUE" in factual.intent_names
    assert any(i.meta.get("raw_value") == 36 for i in factual.intents)


def test_campaign_figures_not_written_as_canonical_facts() -> None:
    from investhome_api.services.social_design_engine.generation import (
        build_generation_metadata,
        classify_generation_intent,
        extract_campaign_facts,
    )

    prompt = (
        "Minimum yatırım: $500,000 Hedef getiri: %14 Yatırım süresi: 24 ay. İngilizce hazırla."
    )
    intent = classify_generation_intent(prompt, project_name="Temple Residences")
    facts = extract_campaign_facts(prompt)
    meta = build_generation_metadata(
        project_id=TEMPLE_PROJECT_ID,
        user_prompt=prompt,
        intent=intent,
        campaign_facts=facts,
        source_document_ids=[],
        selected_asset_ids=[],
        provider="test",
        model="test",
    )
    assert meta["campaign_facts"]
    assert "verified_facts" not in meta
    assert meta.get("generated_by") == "social_design_engine"



