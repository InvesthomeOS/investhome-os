"""Social Media Builder AI Design Engine (Phase 1) tests."""

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
