"""Document intelligence API tests."""

import io
import time
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.document import ProcessingStatus
from investhome_api.models.document_intelligence import DocumentChunk  # noqa: F401
from investhome_api.services.document_intelligence.pipeline import process_document

pytestmark = pytest.mark.usefixtures("client")


def _upload_txt(client: TestClient, content: bytes, **form: str) -> dict:
    files = {"files": ("lease-demo.txt", io.BytesIO(content), "text/plain")}
    response = client.post("/documents/upload", files=files, data=form)
    assert response.status_code == 201
    payload = response.json()
    assert payload["results"][0]["success"] is True
    return payload["results"][0]["document"]


def _wait_for_processing(client: TestClient, document_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = client.get(f"/documents/{document_id}/processing-status")
        assert response.status_code == 200
        payload = response.json()
        if payload["processing_status"] in {ProcessingStatus.COMPLETED.value, ProcessingStatus.FAILED.value, ProcessingStatus.NOT_SUPPORTED.value}:
            return payload
        time.sleep(0.2)
    raise AssertionError("processing timed out")


@pytest.fixture(autouse=True)
def _sync_processing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DOCUMENT_PROCESSING_SYNC", "true")
    get_settings.cache_clear()


def test_process_lease_document_end_to_end(client: TestClient) -> None:
    content = (
        b"LEASE AGREEMENT\n"
        b"Landlord: Investhome Properties LLC\n"
        b"Tenant: Demo Tenant Inc\n"
        b"Rent: USD 5,000 per month\n"
        b"Effective date: 2026-01-01\n"
        b"Expiration date: 2028-12-31\n"
        b"Tenant shall maintain insurance and pay rent on the first day of each month.\n"
        b"Termination: 90 days written notice required.\n"
    )
    doc = _upload_txt(client, content, document_type="lease", title="Demo Lease")
    status_payload = _wait_for_processing(client, doc["id"])
    assert status_payload["processing_status"] == ProcessingStatus.COMPLETED.value

    analysis_response = client.get(f"/documents/{doc['id']}/analysis")
    assert analysis_response.status_code == 200
    analysis = analysis_response.json()
    assert analysis["detected_document_type"] == "lease"
    assert analysis["user_document_type"] == "lease"
    assert analysis["ai_summary"]
    assert analysis["extracted_parties"]
    assert analysis["classification_status"] == "pending"

    accept = client.post(f"/documents/{doc['id']}/classification", json={"accept": True})
    assert accept.status_code == 200
    assert accept.json()["classification_status"] == "accepted"

    ask = client.post(
        f"/documents/{doc['id']}/ask",
        json={"question": "Who is the tenant?", "language": "en"},
    )
    assert ask.status_code == 200
    answer = ask.json()
    assert "tenant" in answer["answer"].lower() or answer["found"] is False

    export = client.get(f"/documents/{doc['id']}/analysis/export")
    assert export.status_code == 200
    assert export.json()["detected_document_type"] == "lease"


def test_reprocess_document(client: TestClient) -> None:
    doc = _upload_txt(client, b"Invoice amount due USD 1,200 on 2026-05-01", document_type="invoice")
    _wait_for_processing(client, doc["id"])
    response = client.post(f"/documents/{doc['id']}/reprocess")
    assert response.status_code == 200
    assert response.json()["processing_status"] in {
        ProcessingStatus.QUEUED.value,
        ProcessingStatus.PROCESSING.value,
        ProcessingStatus.COMPLETED.value,
    }


def test_ask_without_answer_does_not_hallucinate(client: TestClient) -> None:
    doc = _upload_txt(client, b"Simple memo without financial terms.", document_type="other")
    _wait_for_processing(client, doc["id"])
    response = client.post(
        f"/documents/{doc['id']}/ask",
        json={"question": "What is the interest rate?", "language": "en"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["found"] is False
    assert "not found" in payload["answer"].lower()


def test_pipeline_direct_call(client: TestClient) -> None:
    doc = _upload_txt(client, b"Permit number 12345 issued by city agency on 2026-02-01", document_type="permit")
    db = next(app.dependency_overrides[get_db]())
    process_document(db, UUID(doc["id"]))
    db.commit()
    refreshed = client.get(f"/documents/{doc['id']}/analysis")
    assert refreshed.status_code == 200
    assert refreshed.json()["detected_document_type"] in {"permit", "other"}
