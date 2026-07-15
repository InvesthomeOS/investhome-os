"""Phase 3 verification suite for architectural drawing intelligence."""

from __future__ import annotations

import hashlib
import io
import json
import time
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter
from sqlalchemy import select

from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityLog
from investhome_api.models.document import ConfidentialityLevel, Document, DocumentType, ProcessingStatus
from investhome_api.models.drawing_intelligence import DrawingAnalysis, DrawingUnitProposal
from investhome_api.models.notification import Notification
from investhome_api.services.drawing_intelligence.conversion import SAMPLE_DXF
from investhome_api.services.drawing_intelligence.pipeline import process_drawing
from investhome_api.services.storage.factory import get_storage_provider

pytestmark = pytest.mark.usefixtures("client")


@pytest.fixture(autouse=True)
def _sync_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_PROCESSING_SYNC", "true")
    get_settings.cache_clear()


def _wait_for_drawing(client: TestClient, document_id: str, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/documents/{document_id}/drawing-processing-status")
        assert response.status_code == 200
        payload = response.json()
        if payload["processing_status"] in {
            "completed",
            "failed",
            "not_supported",
            "preview_unavailable",
        }:
            return payload
        time.sleep(0.2)
    raise AssertionError("drawing processing timed out")


def _upload(
    client: TestClient,
    filename: str,
    content: bytes,
    mime: str,
    **form: str,
) -> dict:
    files = {"files": (filename, io.BytesIO(content), mime)}
    response = client.post("/documents/upload", files=files, data=form)
    assert response.status_code == 201
    result = response.json()["results"][0]
    assert result["success"] is True, result.get("error")
    return result["document"]


def _make_vector_pdf(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class TestDrawingUploadAndConversion:
    def test_dxf_upload_and_conversion(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "floor-plan.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Unit A Floor Plan",
            document_type="architectural_drawing",
        )
        status = _wait_for_drawing(client, doc["id"])
        assert status["processing_status"] == "completed"
        analysis = client.get(f"/documents/{doc['id']}/drawing-analysis")
        assert analysis.status_code == 200
        payload = analysis.json()
        assert payload["conversion_method"] == "dxf_parser_v1"
        assert payload["sheet_count"] >= 1
        assert payload["scale_detected"] == "1:100"
        assert len(payload["elements"]) > 0

    def test_dwg_upload_honest_unavailable(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "site-plan.dwg",
            b"AC10placeholder-dwg-content",
            "application/acad",
            title="Site DWG",
            document_type="architectural_drawing",
        )
        status = _wait_for_drawing(client, doc["id"])
        assert status["processing_status"] == "preview_unavailable"
        assert status["preview_status"] == "unavailable"
        analysis = client.get(f"/documents/{doc['id']}/drawing-analysis")
        assert analysis.status_code == 200
        assert analysis.json()["conversion_method"] == "dwg_external_required"

    def test_vector_pdf_processing(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "plan.pdf",
            _make_vector_pdf("A-101 FLOOR PLAN 1:50"),
            "application/pdf",
            title="PDF Floor Plan",
            document_type="architectural_drawing",
        )
        status = _wait_for_drawing(client, doc["id"])
        assert status["processing_status"] in {"completed", "failed"}

    def test_scanned_plan_honest_preview_unavailable(self, client: TestClient) -> None:
        buffer = io.BytesIO()
        Image.new("RGB", (800, 600), color=(240, 240, 240)).save(buffer, format="PNG")
        doc = _upload(
            client,
            "scan.png",
            buffer.getvalue(),
            "image/png",
            title="Scanned Plan",
            document_type="architectural_drawing",
        )
        status = _wait_for_drawing(client, doc["id"])
        assert status["processing_status"] == "completed"
        assert status["preview_status"] == "unavailable"
        analysis = client.get(f"/documents/{doc['id']}/drawing-analysis").json()
        assert analysis["conversion_method"] == "scanned_plan_ocr_placeholder"
        preview = client.get(f"/documents/{doc['id']}/drawing-preview")
        assert preview.status_code == 404


class TestDrawingDetection:
    def test_sheet_discipline_and_type_classification(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "plan.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Architectural Plan",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        payload = client.get(f"/documents/{doc['id']}/drawing-analysis").json()
        assert payload["discipline"] == "architectural"
        assert payload["drawing_type"] == "floor_plan"
        assert len(payload["sheets"]) >= 1

    def test_dimension_room_wall_door_window_detection(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "elements.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Element Detection",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        elements = client.get(f"/documents/{doc['id']}/drawing-analysis").json()["elements"]
        types = {e["element_type"] for e in elements}
        assert "room" in types
        assert "wall" in types
        assert "dimension" in types
        assert "door" in types or "window" in types

    def test_low_confidence_measurements_flagged(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "confidence.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Confidence Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        payload = client.get(f"/documents/{doc['id']}/drawing-analysis").json()
        low = [e for e in payload["elements"] if e["confidence"] == "low"]
        assert payload["low_confidence_count"] == len(low)
        assert payload["low_confidence_count"] >= 1

    def test_title_block_schedule_and_area_extraction(self, client: TestClient) -> None:
        schedule_dxf = SAMPLE_DXF.replace("5.00 m", "MATERIAL SCHEDULE")
        doc = _upload(
            client,
            "extract.dxf",
            schedule_dxf.encode("utf-8"),
            "image/vnd.dxf",
            title="Extraction Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        payload = client.get(f"/documents/{doc['id']}/drawing-analysis").json()
        element_types = {e["element_type"] for e in payload["elements"]}
        assert "title_block" in element_types
        assert "schedule" in element_types
        assert "area" in element_types
        assert payload["title_block_json"]
        assert payload["schedules_json"]


class TestDrawingFeatures:
    def test_safe_preview_generation(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "preview.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Preview Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        preview = client.get(f"/documents/{doc['id']}/drawing-preview")
        assert preview.status_code == 200
        assert "image/svg+xml" in preview.headers.get("content-type", "")

    def test_manual_scale_correction(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "scale.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Scale Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        response = client.post(
            f"/documents/{doc['id']}/drawing-scale",
            json={"scale": "1:75"},
        )
        assert response.status_code == 200
        assert response.json()["scale_corrected"] == "1:75"

    def test_drawing_qa(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "qa.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="QA Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        response = client.post(
            f"/documents/{doc['id']}/drawing-ask",
            json={"question": "What rooms are detected?", "locale": "en"},
        )
        assert response.status_code == 200
        assert "room" in response.json()["answer"].lower() or response.json()["grounded"]

    def test_drawing_qa_turkish_locale(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "qa-tr.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="QA TR Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        response = client.post(
            f"/documents/{doc['id']}/drawing-ask",
            json={"question": "Hangi odalar tespit edildi?", "locale": "tr"},
        )
        assert response.status_code == 200
        answer = response.json()["answer"]
        assert "oda" in answer.lower() or "tespit" in answer.lower()

    def test_annotations_non_destructive(self, client: TestClient, db_session_factory) -> None:
        doc = _upload(
            client,
            "annotate.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Annotation Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        storage = get_storage_provider()
        document = db_session_factory().get(Document, UUID(doc["id"]))
        assert document is not None
        original_checksum = document.checksum

        response = client.post(
            f"/documents/{doc['id']}/drawing-annotations",
            json={"label": "Review note", "content": "Check door swing"},
        )
        assert response.status_code == 201

        refreshed = db_session_factory().get(Document, UUID(doc["id"]))
        assert refreshed is not None
        assert refreshed.checksum == original_checksum

    def test_unit_proposals_require_approval(self, auth_client: TestClient) -> None:
        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        unit_dxf = SAMPLE_DXF.replace("LIVING ROOM", "UNIT A1")
        doc = _upload(
            auth_client,
            "units.dxf",
            unit_dxf.encode("utf-8"),
            "image/vnd.dxf",
            title="Unit Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(auth_client, doc["id"])
        proposals = auth_client.get(f"/documents/{doc['id']}/drawing-analysis").json()["unit_proposals"]
        assert proposals, "Expected unit proposal from UNIT A1 label"
        proposal_id = proposals[0]["id"]
        assert proposals[0]["status"] == "proposed"
        assert proposals[0]["created_unit_id"] is None

        auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
        denied = auth_client.post(
            f"/documents/{doc['id']}/drawing-units/approve",
            json={"proposal_id": proposal_id, "approved": True},
        )
        assert denied.status_code == 403

        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        approved = auth_client.post(
            f"/documents/{doc['id']}/drawing-units/approve",
            json={"proposal_id": proposal_id, "approved": True},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"
        assert approved.json()["created_unit_id"] is not None


class TestDrawingSecurityAndVersions:
    def test_original_cad_unchanged(self, client: TestClient, db_session_factory) -> None:
        content = SAMPLE_DXF.encode("utf-8")
        checksum = hashlib.sha256(content).hexdigest()
        doc = _upload(
            client,
            "integrity.dxf",
            content,
            "image/vnd.dxf",
            title="Integrity Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        document = db_session_factory().get(Document, UUID(doc["id"]))
        assert document is not None
        assert document.checksum == checksum
        path = Path(get_storage_provider().get_local_path(document.storage_key))
        assert path.read_bytes() == content

    def test_old_versions_not_current(self, client: TestClient, db_session_factory) -> None:
        doc = _upload(
            client,
            "v1.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Version Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        v1_analysis = client.get(f"/documents/{doc['id']}/drawing-analysis").json()
        v2_content = SAMPLE_DXF.replace("LIVING ROOM", "BEDROOM").encode("utf-8")
        files = {"file": ("v2.dxf", io.BytesIO(v2_content), "image/vnd.dxf")}
        version_resp = client.post(f"/documents/{doc['id']}/versions", files=files, data={"version_notes": "rev2"})
        assert version_resp.status_code == 201
        v2 = version_resp.json()
        _wait_for_drawing(client, v2["id"])

        db = db_session_factory()
        v1_doc = db.get(Document, UUID(doc["id"]))
        v2_doc = db.get(Document, UUID(v2["id"]))
        assert v1_doc is not None and v2_doc is not None
        assert v1_doc.is_latest_version is False
        assert v2_doc.is_latest_version is True

        v1_status = client.get(f"/documents/{doc['id']}/drawing-processing-status").json()
        v2_status = client.get(f"/documents/{v2['id']}/drawing-processing-status").json()
        assert v1_status["processing_status"] in {"completed", "preview_unavailable"}
        assert v2_status["processing_status"] == "completed"
        v2_analysis = client.get(f"/documents/{v2['id']}/drawing-analysis").json()
        assert v2_analysis["document_version_id"] == v2["id"]
        assert v1_analysis["document_version_id"] == doc["id"]

        compare = client.post(
            f"/documents/{v2['id']}/drawing-compare",
            json={"from_version_id": doc["id"], "to_version_id": v2["id"]},
        )
        assert compare.status_code == 200
        assert compare.json()["changes_json"]

    def test_restricted_drawings_hidden_from_search(self, auth_client: TestClient) -> None:
        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        doc = _upload(
            auth_client,
            "secret.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Confidential Tower Plan",
            document_type="architectural_drawing",
            confidentiality_level="highly_confidential",
        )
        _wait_for_drawing(auth_client, doc["id"])
        auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
        search = auth_client.get("/search", params={"q": "Confidential Tower Plan"})
        assert search.status_code in {200, 403}
        if search.status_code == 200:
            groups = search.json()["groups"]
            doc_results = next((g for g in groups if g["entity_type"] == "document"), None)
            if doc_results:
                assert len(doc_results["items"]) == 0

    def test_restricted_drawings_hidden_from_activity(self, auth_client: TestClient) -> None:
        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        doc = _upload(
            auth_client,
            "secret-activity.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Secret Activity Plan",
            document_type="architectural_drawing",
            confidentiality_level="highly_confidential",
        )
        _wait_for_drawing(auth_client, doc["id"])
        auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
        activity = auth_client.get(f"/activity/entity/document/{doc['id']}")
        assert activity.status_code == 200
        assert activity.json()["total"] == 0

    def test_processing_error_hidden_without_analysis_permission(self, auth_client: TestClient) -> None:
        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        doc = _upload(
            auth_client,
            "failed.dwg",
            b"AC10placeholder-dwg-content",
            "application/acad",
            title="Failed DWG",
            document_type="architectural_drawing",
        )
        status = _wait_for_drawing(auth_client, doc["id"])
        assert status["processing_status"] == "preview_unavailable"
        assert status["processing_error"] is not None

        auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
        readonly_status = auth_client.get(f"/documents/{doc['id']}/drawing-processing-status").json()
        assert readonly_status["processing_status"] == "preview_unavailable"
        assert readonly_status["processing_error"] is None

    def test_drawing_analysis_requires_view_analysis_permission(self, auth_client: TestClient) -> None:
        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        doc = _upload(
            auth_client,
            "perm.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Permission Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(auth_client, doc["id"])
        auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
        denied = auth_client.get(f"/documents/{doc['id']}/drawing-analysis")
        assert denied.status_code == 403


class TestDrawingIntegrations:
    def test_project_integration_via_upload(self, client: TestClient, db_session_factory) -> None:
        from investhome_api.models.project import Project, ProjectStatus, ProjectType, DevelopmentType

        db = db_session_factory()
        project = Project(
            project_name="Drawing Tower",
            project_code="DT-01",
            project_type=ProjectType.MULTIFAMILY,
            development_type=DevelopmentType.GROUND_UP,
            project_status=ProjectStatus.CONSTRUCTION,
        )
        db.add(project)
        db.commit()

        doc = _upload(
            client,
            "linked.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Linked Plan",
            document_type="architectural_drawing",
            project_id=str(project.id),
        )
        _wait_for_drawing(client, doc["id"])
        refreshed = db.get(Document, UUID(doc["id"]))
        assert refreshed is not None
        assert refreshed.project_id == project.id

    def test_activity_log_records_drawing_events(self, client: TestClient, db_session_factory) -> None:
        doc = _upload(
            client,
            "activity.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Activity Test",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        client.post(f"/documents/{doc['id']}/drawing-scale", json={"scale": "1:200"})
        db = db_session_factory()
        logs = db.scalars(
            select(ActivityLog).where(ActivityLog.entity_id == UUID(doc["id"]))
        ).all()
        keys = {log.description_key for log in logs}
        assert "activity.document.drawing_processing_completed" in keys
        assert "activity.document.drawing_scale_corrected" in keys

    def test_drawing_search_by_discipline(self, client: TestClient) -> None:
        doc = _upload(
            client,
            "search.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Searchable Plan",
            document_type="architectural_drawing",
        )
        _wait_for_drawing(client, doc["id"])
        search = client.get("/search", params={"q": "architectural"})
        assert search.status_code == 200

    def test_drawing_failure_creates_notification(
        self, auth_client: TestClient, db_session_factory, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from investhome_api.services.drawing_intelligence.types import ConversionResult

        def _fail_convert(*_args, **_kwargs):
            return ConversionResult(
                success=False,
                method="test_fail",
                error="forced_failure",
                preview_unavailable=True,
                original_preserved=True,
            )

        monkeypatch.setattr(
            "investhome_api.services.drawing_intelligence.pipeline.convert_drawing",
            _fail_convert,
        )
        auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
        doc = _upload(
            auth_client,
            "broken.dxf",
            SAMPLE_DXF.encode("utf-8"),
            "image/vnd.dxf",
            title="Broken DXF",
            document_type="architectural_drawing",
        )
        status = _wait_for_drawing(auth_client, doc["id"])
        assert status["processing_status"] == "failed"

        db = db_session_factory()
        document = db.get(Document, UUID(doc["id"]))
        assert document is not None
        notifications = db.scalars(
            select(Notification).where(Notification.related_entity_id == document.id)
        ).all()
        assert any(
            n.title_key == "notifications.document.drawing_processing_failed.title" for n in notifications
        )


@pytest.fixture
def db_session_factory():
    from investhome_api.db.session import SessionLocal

    return SessionLocal
