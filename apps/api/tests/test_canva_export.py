"""Canva Connect export — PNG/asset upload, create design, token refresh. No secrets in responses."""

from __future__ import annotations

import io
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.services import canva_oauth_service as canva
from investhome_api.services.storage.factory import get_storage_provider

EDIT_URL = "https://www.canva.com/api/design/test-edit-token/edit"


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict[str, Any] | None = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeCanvaHttp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.refresh_count = 0
        self.upload_count = 0
        self.poll_count = 0
        self.design_count = 0
        self.seen_authorization: list[str] = []
        self.poll_in_progress_once = False
        self.fail_first_upload_auth = False
        self._upload_auth_failures = 0

    def __enter__(self) -> _FakeCanvaHttp:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def _record(self, method: str, url: str, headers: dict | None) -> None:
        self.calls.append((method, url))
        auth = (headers or {}).get("Authorization")
        if auth:
            self.seen_authorization.append(str(auth))

    def post(self, url: str, headers: dict | None = None, data: Any = None, content: Any = None, json: Any = None):
        self._record("POST", url, headers)
        if url == canva.CANVA_TOKEN_URL:
            form = data or {}
            assert form.get("grant_type") == "refresh_token"
            assert form.get("refresh_token")
            self.refresh_count += 1
            return _FakeResponse(
                200,
                {
                    "access_token": "access-refreshed",
                    "refresh_token": "refresh-rotated",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        if url.endswith("/asset-uploads"):
            if self.fail_first_upload_auth and self._upload_auth_failures == 0:
                self._upload_auth_failures += 1
                return _FakeResponse(401, {"code": "unauthorized"})
            self.upload_count += 1
            status = "in_progress" if self.poll_in_progress_once else "success"
            job: dict[str, Any] = {"id": "job-upload-1", "status": status}
            if status == "success":
                job["asset"] = {"id": "MsdCanvaAsset", "type": "image", "name": "Social post"}
            return _FakeResponse(200, {"job": job})
        if url.endswith("/designs"):
            self.design_count += 1
            assert json and json.get("asset_id") == "MsdCanvaAsset"
            return _FakeResponse(
                200,
                {
                    "design": {
                        "id": "DAFdesign1",
                        "title": json.get("title"),
                        "urls": {
                            "edit_url": EDIT_URL,
                            "view_url": "https://www.canva.com/api/design/test-edit-token/view",
                        },
                    }
                },
            )
        return _FakeResponse(404, {"code": "not_found"})

    def get(self, url: str, headers: dict | None = None):
        self._record("GET", url, headers)
        self.poll_count += 1
        return _FakeResponse(
            200,
            {
                "job": {
                    "id": "job-upload-1",
                    "status": "success",
                    "asset": {"id": "MsdCanvaAsset", "type": "image", "name": "Social post"},
                }
            },
        )


@pytest.fixture(autouse=True)
def _canva_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CANVA_CLIENT_ID", "test-canva-client-id")
    monkeypatch.setenv("CANVA_CLIENT_SECRET", "test-canva-client-secret")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _png_bytes(width: int = 64, height: int = 64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (12, 80, 160)).save(buf, format="PNG")
    return buf.getvalue()


def _store_tokens(db: Session, *, access: str = "access-live", refresh: str = "refresh-live", expires_in: int = 3600) -> None:
    canva.store_tokens(
        db,
        {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "scope": " ".join(canva.CANVA_SCOPES),
        },
    )
    db.commit()


def _secret_leak(payload: str) -> None:
    lowered = payload.lower()
    assert "access-live" not in lowered
    assert "refresh-live" not in lowered
    assert "access-refreshed" not in lowered
    assert "refresh-rotated" not in lowered
    assert "test-canva-client-secret" not in lowered
    assert "bearer access" not in lowered


def test_export_requires_canva_connection(client: TestClient) -> None:
    png = _png_bytes()
    response = client.post(
        "/platform/integrations/canva/export",
        files={"file": ("post.png", io.BytesIO(png), "image/png")},
        data={"title": "Temple post"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "canva_not_connected"
    _secret_leak(response.text)


def test_export_png_uploads_and_returns_edit_url(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCanvaHttp()
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    monkeypatch.setattr("investhome_api.services.canva_export_service._sleep", lambda _s: None)
    _store_tokens(db)

    png = _png_bytes(1080, 1080)
    response = client.post(
        "/platform/integrations/canva/export",
        files={"file": ("temple.png", io.BytesIO(png), "image/png")},
        data={"title": "Temple Instagram", "width": "1080", "height": "1080"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["edit_url"] == EDIT_URL
    assert body["design_id"] == "DAFdesign1"
    assert fake.upload_count == 1
    assert fake.design_count == 1
    assert fake.refresh_count == 0
    _secret_leak(response.text)
    assert "access_token" not in response.text.lower()
    assert "refresh_token" not in response.text.lower()


def test_export_polls_in_progress_upload_job(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCanvaHttp()
    fake.poll_in_progress_once = True
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    monkeypatch.setattr("investhome_api.services.canva_export_service._sleep", lambda _s: None)
    _store_tokens(db)

    response = client.post(
        "/platform/integrations/canva/export",
        files={"file": ("post.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Poll me"},
    )
    assert response.status_code == 200, response.text
    assert fake.poll_count >= 1
    assert response.json()["edit_url"] == EDIT_URL


def test_export_refreshes_expired_access_token(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCanvaHttp()
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    monkeypatch.setattr("investhome_api.services.canva_export_service._sleep", lambda _s: None)
    _store_tokens(db, access="access-expired", refresh="refresh-live", expires_in=-30)

    response = client.post(
        "/platform/integrations/canva/export",
        files={"file": ("post.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "Refresh path"},
    )
    assert response.status_code == 200, response.text
    assert fake.refresh_count == 1
    assert any(auth.endswith("access-refreshed") for auth in fake.seen_authorization)
    stored = canva.get_stored_tokens(db)
    assert stored is not None
    assert stored["access_token"] == "access-refreshed"
    assert stored["refresh_token"] == "refresh-rotated"
    _secret_leak(response.text)


def test_export_retries_upload_after_401(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCanvaHttp()
    fake.fail_first_upload_auth = True
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    monkeypatch.setattr("investhome_api.services.canva_export_service._sleep", lambda _s: None)
    _store_tokens(db, access="access-stale", refresh="refresh-live", expires_in=3600)

    response = client.post(
        "/platform/integrations/canva/export",
        files={"file": ("post.png", io.BytesIO(_png_bytes()), "image/png")},
        data={"title": "401 retry"},
    )
    assert response.status_code == 200, response.text
    assert fake.refresh_count == 1
    assert fake.upload_count == 1
    _secret_leak(response.text)


def test_export_rejects_non_png(client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCanvaHttp()
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    _store_tokens(db)
    response = client.post(
        "/platform/integrations/canva/export",
        files={"file": ("note.txt", io.BytesIO(b"not-an-image"), "text/plain")},
        data={"title": "bad"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "invalid_png"
    assert fake.upload_count == 0


def test_export_media_asset_enforces_project_isolation(
    client: TestClient,
    db: Session,
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from investhome_api.models.project import Project, ProjectStatus, ProjectType

    monkeypatch.setenv("DOCUMENT_STORAGE_ROOT", str(tmp_path / "media-storage"))
    get_settings.cache_clear()
    get_storage_provider.cache_clear()

    fake = _FakeCanvaHttp()
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    monkeypatch.setattr("investhome_api.services.canva_export_service._sleep", lambda _s: None)
    _store_tokens(db)

    project_a = Project(
        id=uuid4(),
        project_code=f"PRJ-A-{uuid4().hex[:6]}",
        project_name="Temple",
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    project_b = Project(
        id=uuid4(),
        project_code=f"PRJ-B-{uuid4().hex[:6]}",
        project_name="Other",
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.CONSTRUCTION,
    )
    db.add(project_a)
    db.add(project_b)
    db.commit()

    png = _png_bytes()
    upload = client.post(
        "/creative-studio/media/upload",
        files={"file": ("hero.png", io.BytesIO(png), "image/png")},
        data={"linked_project_id": str(project_a.id), "tags": "hero"},
    )
    assert upload.status_code == 201, upload.text
    asset_id = upload.json()["id"]

    denied = client.post(
        "/platform/integrations/canva/export",
        data={
            "media_asset_id": asset_id,
            "linked_project_id": str(project_b.id),
            "title": "cross project",
        },
    )
    assert denied.status_code == 404
    assert fake.upload_count == 0
    _secret_leak(denied.text)

    allowed = client.post(
        "/platform/integrations/canva/export",
        data={
            "media_asset_id": asset_id,
            "linked_project_id": str(project_a.id),
            "title": "same project",
        },
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["edit_url"] == EDIT_URL
    assert fake.upload_count == 1


def test_export_media_asset_requires_project_id(client: TestClient, db: Session) -> None:
    _store_tokens(db)
    response = client.post(
        "/platform/integrations/canva/export",
        data={"media_asset_id": str(uuid4()), "title": "no project"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "linked_project_id_required"


def test_get_valid_access_token_refreshes(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeCanvaHttp()
    monkeypatch.setattr(canva, "http_client", lambda: fake)
    _store_tokens(db, access="old", refresh="refresh-live", expires_in=-5)
    token = canva.get_valid_access_token(db)
    assert token == "access-refreshed"
    assert fake.refresh_count == 1
    stored = canva.get_stored_tokens(db)
    assert stored is not None
    assert stored["refresh_token"] == "refresh-rotated"
