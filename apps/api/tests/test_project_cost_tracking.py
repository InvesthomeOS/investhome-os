"""Sprint 10A4B — Commitments, vendor bills, payments, retainage, cost rollups."""

from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_project(client: TestClient, code: str = "PRJ-COST-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Cost Tracking Project",
            "address": "10 Cost Lane",
            "city": "Austin",
            "state": "TX",
            "country": "United States",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
            "currency": "USD",
            "construction_budget": "1000000.00",
            "total_development_cost": "1500000.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _approved_budget_with_line(client: TestClient, project_id: str) -> tuple[str, str]:
    budget = client.post(
        f"/projects/{project_id}/budgets",
        json={"name": "Baseline", "effective_date": date.today().isoformat()},
    ).json()
    categories = client.get("/budget-categories").json()
    hard = next(item for item in categories if item["code"] == "HARD")
    codes = client.get("/cost-codes", params={"category_id": hard["id"]}).json()
    line = client.post(
        f"/projects/{project_id}/budgets/{budget['id']}/lines",
        json={
            "category_id": hard["id"],
            "cost_code_id": codes[0]["id"] if codes else None,
            "line_number": "1000",
            "name": "Structure",
            "original_budget": "250000.00",
        },
    ).json()
    assert client.post(f"/projects/{project_id}/budgets/{budget['id']}/submit").status_code == 200
    assert client.post(f"/projects/{project_id}/budgets/{budget['id']}/approve").status_code == 200
    return budget["id"], line["id"]


def _create_vendor(client: TestClient, code: str = "VND-001") -> dict:
    response = client.post(
        "/vendors",
        json={
            "name": "Acme Construction",
            "vendor_code": code,
            "vendor_type": "general_contractor",
            "status": "active",
            "default_currency": "USD",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _activate_commitment(
    client: TestClient, project_id: str, vendor_id: str, budget_line_id: str, amount: str = "100000.00"
) -> dict:
    created = client.post(
        f"/projects/{project_id}/commitments",
        json={
            "vendor_id": vendor_id,
            "commitment_type": "contract",
            "title": "GC Contract",
            "retainage_percentage": "10.00",
            "lines": [
                {
                    "budget_line_id": budget_line_id,
                    "description": "Structure work",
                    "original_amount": amount,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    commitment = created.json()
    cid = commitment["id"]
    assert client.post(f"/projects/{project_id}/commitments/{cid}/submit").status_code == 200
    approved = client.post(f"/projects/{project_id}/commitments/{cid}/approve")
    assert approved.status_code == 200, approved.text
    assert client.post(f"/projects/{project_id}/commitments/{cid}/execute").status_code == 200
    activated = client.post(f"/projects/{project_id}/commitments/{cid}/activate")
    assert activated.status_code == 200, activated.text
    return activated.json()


def test_vendor_and_project_vendor(client: TestClient) -> None:
    project = _create_project(client)
    vendor = _create_vendor(client)
    linked = client.post(
        f"/projects/{project['id']}/vendors",
        json={"vendor_id": vendor["id"], "role": "general_contractor"},
    )
    assert linked.status_code == 201, linked.text
    duplicate = client.post(
        f"/projects/{project['id']}/vendors",
        json={"vendor_id": vendor["id"], "role": "general_contractor"},
    )
    assert duplicate.status_code in {409, 422}


def test_commitment_lifecycle_and_lock(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-002")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-002")
    commitment = _activate_commitment(client, project["id"], vendor["id"], budget_line_id)
    assert commitment["status"] == "active"
    assert Decimal(commitment["current_committed_amount"]) == Decimal("100000.00")
    assert commitment["commitment_number"].startswith("CTR-")

    locked = client.post(
        f"/projects/{project['id']}/commitments/{commitment['id']}/lines",
        json={
            "budget_line_id": budget_line_id,
            "description": "Should fail",
            "original_amount": "1.00",
        },
    )
    assert locked.status_code == 409


def test_change_order_preserves_original(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-003")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-003")
    commitment = _activate_commitment(client, project["id"], vendor["id"], budget_line_id)
    line_id = commitment["lines"][0]["id"]
    original = Decimal(commitment["original_amount"])

    co = client.post(
        f"/projects/{project['id']}/commitments/{commitment['id']}/change-orders",
        json={
            "title": "Extra steel",
            "reason": "Scope increase",
            "lines": [
                {
                    "commitment_line_id": line_id,
                    "budget_line_id": budget_line_id,
                    "amount": "15000.00",
                    "description": "Additional steel",
                }
            ],
        },
    )
    assert co.status_code == 201, co.text
    co_id = co.json()["id"]
    assert client.post(
        f"/projects/{project['id']}/commitments/{commitment['id']}/change-orders/{co_id}/submit"
    ).status_code == 200
    approved = client.post(
        f"/projects/{project['id']}/commitments/{commitment['id']}/change-orders/{co_id}/approve"
    )
    assert approved.status_code == 200, approved.text

    refreshed = client.get(f"/projects/{project['id']}/commitments/{commitment['id']}").json()
    assert Decimal(refreshed["original_amount"]) == original
    assert Decimal(refreshed["approved_change_orders"]) == Decimal("15000.00")
    assert Decimal(refreshed["current_committed_amount"]) == Decimal("115000.00")

    # Double application blocked
    again = client.post(
        f"/projects/{project['id']}/commitments/{commitment['id']}/change-orders/{co_id}/approve"
    )
    assert again.status_code in {409, 422}


def test_bill_posting_creates_actual_cost_not_draft(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-004")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-004")
    commitment = _activate_commitment(client, project["id"], vendor["id"], budget_line_id)
    line_id = commitment["lines"][0]["id"]

    draft_bill = client.post(
        f"/projects/{project['id']}/vendor-bills",
        json={
            "vendor_id": vendor["id"],
            "commitment_id": commitment["id"],
            "vendor_invoice_number": "INV-100",
            "invoice_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "lines": [
                {
                    "budget_line_id": budget_line_id,
                    "commitment_id": commitment["id"],
                    "commitment_line_id": line_id,
                    "description": "Progress billing 1",
                    "gross_amount": "40000.00",
                    "retainage_amount": "4000.00",
                }
            ],
        },
    )
    assert draft_bill.status_code == 201, draft_bill.text
    bill_id = draft_bill.json()["id"]

    summary_before = client.get(f"/projects/{project['id']}/budget-summary").json()
    assert Decimal(summary_before["totals"]["actual_cost"]["value"]) == Decimal("0")
    assert Decimal(summary_before["totals"]["committed_cost"]["value"]) == Decimal("100000.00")

    assert client.post(f"/projects/{project['id']}/vendor-bills/{bill_id}/submit").status_code == 200
    assert client.post(f"/projects/{project['id']}/vendor-bills/{bill_id}/approve").status_code == 200

    summary_approved = client.get(f"/projects/{project['id']}/budget-summary").json()
    assert Decimal(summary_approved["totals"]["actual_cost"]["value"]) == Decimal("0")

    posted = client.post(f"/projects/{project['id']}/vendor-bills/{bill_id}/post")
    assert posted.status_code == 200, posted.text
    bill = posted.json()
    assert bill["status"] == "posted"
    # approved_amount = total - retainage; actual uses net+tax convention
    assert Decimal(bill["retainage_amount"]) == Decimal("4000.00")

    summary_posted = client.get(f"/projects/{project['id']}/budget-summary").json()
    assert summary_posted["totals"]["actual_cost"]["available"] is True
    assert Decimal(summary_posted["totals"]["actual_cost"]["value"]) > Decimal("0")
    assert Decimal(summary_posted["totals"]["retained_cost"]["value"]) == Decimal("4000.00")

    locked = client.patch(
        f"/projects/{project['id']}/vendor-bills/{bill_id}",
        json={"description": "nope"},
    )
    assert locked.status_code == 409


def test_payment_partial_and_full(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-005")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-005")
    commitment = _activate_commitment(client, project["id"], vendor["id"], budget_line_id)
    line_id = commitment["lines"][0]["id"]

    bill = client.post(
        f"/projects/{project['id']}/vendor-bills",
        json={
            "vendor_id": vendor["id"],
            "commitment_id": commitment["id"],
            "vendor_invoice_number": "INV-200",
            "invoice_date": date.today().isoformat(),
            "lines": [
                {
                    "budget_line_id": budget_line_id,
                    "commitment_line_id": line_id,
                    "description": "Billing",
                    "gross_amount": "50000.00",
                    "retainage_amount": "5000.00",
                }
            ],
        },
    ).json()
    bill_id = bill["id"]
    for action in ("submit", "approve", "post"):
        assert client.post(f"/projects/{project['id']}/vendor-bills/{bill_id}/{action}").status_code == 200

    bill = client.get(f"/projects/{project['id']}/vendor-bills/{bill_id}").json()
    balance = Decimal(bill["balance_due"])
    partial_amount = (balance / 2).quantize(Decimal("0.01"))

    payment = client.post(
        f"/projects/{project['id']}/payments",
        json={
            "vendor_id": vendor["id"],
            "payment_date": date.today().isoformat(),
            "payment_method": "ach",
            "gross_amount": str(partial_amount),
            "allocations": [
                {"vendor_bill_id": bill_id, "allocated_amount": str(partial_amount)}
            ],
        },
    )
    assert payment.status_code == 201, payment.text
    payment_id = payment.json()["id"]
    posted = client.post(f"/projects/{project['id']}/payments/{payment_id}/post")
    assert posted.status_code == 200, posted.text

    bill_mid = client.get(f"/projects/{project['id']}/vendor-bills/{bill_id}").json()
    assert bill_mid["status"] == "partially_paid"

    remaining = Decimal(bill_mid["balance_due"])
    payment2 = client.post(
        f"/projects/{project['id']}/payments",
        json={
            "vendor_id": vendor["id"],
            "payment_date": date.today().isoformat(),
            "payment_method": "wire",
            "gross_amount": str(remaining),
            "allocations": [{"vendor_bill_id": bill_id, "allocated_amount": str(remaining)}],
        },
    ).json()
    assert (
        client.post(f"/projects/{project['id']}/payments/{payment2['id']}/post").status_code == 200
    )
    bill_paid = client.get(f"/projects/{project['id']}/vendor-bills/{bill_id}").json()
    assert bill_paid["status"] == "paid"

    over = client.post(
        f"/projects/{project['id']}/payments",
        json={
            "vendor_id": vendor["id"],
            "payment_date": date.today().isoformat(),
            "gross_amount": "10.00",
            "allocations": [{"vendor_bill_id": bill_id, "allocated_amount": "10.00"}],
        },
    )
    # Create may succeed as draft; posting or allocation should fail on overpayment
    if over.status_code == 201:
        fail = client.post(f"/projects/{project['id']}/payments/{over.json()['id']}/post")
        assert fail.status_code in {409, 422}
    else:
        assert over.status_code in {409, 422}


def test_retainage_release_and_over_release(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-006")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-006")
    commitment = _activate_commitment(client, project["id"], vendor["id"], budget_line_id)
    line_id = commitment["lines"][0]["id"]

    bill = client.post(
        f"/projects/{project['id']}/vendor-bills",
        json={
            "vendor_id": vendor["id"],
            "commitment_id": commitment["id"],
            "vendor_invoice_number": "INV-300",
            "invoice_date": date.today().isoformat(),
            "lines": [
                {
                    "budget_line_id": budget_line_id,
                    "commitment_line_id": line_id,
                    "description": "Billing",
                    "gross_amount": "20000.00",
                    "retainage_amount": "2000.00",
                }
            ],
        },
    ).json()
    for action in ("submit", "approve", "post"):
        assert client.post(
            f"/projects/{project['id']}/vendor-bills/{bill['id']}/{action}"
        ).status_code == 200

    release = client.post(
        f"/projects/{project['id']}/retainage-releases",
        json={
            "vendor_id": vendor["id"],
            "commitment_id": commitment["id"],
            "vendor_bill_id": bill["id"],
            "release_date": date.today().isoformat(),
            "amount": "2000.00",
            "description": "Final retainage",
        },
    )
    assert release.status_code == 201, release.text
    release_id = release.json()["id"]
    assert client.post(
        f"/projects/{project['id']}/retainage-releases/{release_id}/submit"
    ).status_code == 200
    assert client.post(
        f"/projects/{project['id']}/retainage-releases/{release_id}/approve"
    ).status_code == 200
    posted = client.post(f"/projects/{project['id']}/retainage-releases/{release_id}/post")
    assert posted.status_code == 200, posted.text

    over = client.post(
        f"/projects/{project['id']}/retainage-releases",
        json={
            "vendor_id": vendor["id"],
            "commitment_id": commitment["id"],
            "vendor_bill_id": bill["id"],
            "release_date": date.today().isoformat(),
            "amount": "1.00",
        },
    )
    if over.status_code == 201:
        rid = over.json()["id"]
        client.post(f"/projects/{project['id']}/retainage-releases/{rid}/submit")
        client.post(f"/projects/{project['id']}/retainage-releases/{rid}/approve")
        fail = client.post(f"/projects/{project['id']}/retainage-releases/{rid}/post")
        assert fail.status_code in {409, 422}
    else:
        assert over.status_code in {409, 422}


def test_budget_summary_rollups_and_forecast_label(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-007")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-007")
    _activate_commitment(client, project["id"], vendor["id"], budget_line_id, "80000.00")

    summary = client.get(f"/projects/{project['id']}/budget-summary").json()
    totals = summary["totals"]
    assert totals["committed_cost"]["available"] is True
    assert Decimal(totals["committed_cost"]["value"]) == Decimal("80000.00")
    assert totals["actual_cost"]["available"] is True
    assert Decimal(totals["actual_cost"]["value"]) == Decimal("0")
    assert totals["available_to_commit"]["available"] is True
    assert Decimal(totals["available_to_commit"]["value"]) == Decimal("170000.00")
    assert totals["basic_forecast_at_completion"]["available"] is True
    assert any("commitment-based" in w.lower() for w in summary["warnings"])

    cost = client.get(f"/projects/{project['id']}/cost-summary").json()
    assert "committed_cost" in cost["totals"] or "committed_cost" in cost


def test_legacy_project_budget_still_works(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-008")
    legacy = client.post(
        "/finance/project-budgets",
        json={
            "project_id": project["id"],
            "budget_name": "Legacy Line",
            "category": "construction",
            "original_budget": "50000.00",
            "currency": "USD",
        },
    )
    assert legacy.status_code == 201, legacy.text
    listed = client.get("/finance/project-budgets", params={"project_id": project["id"]})
    assert listed.status_code == 200
    body = listed.json()
    items = body["items"] if isinstance(body, dict) else body
    assert any(item["budget_name"] == "Legacy Line" for item in items)


def test_export_commitments_csv(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-009")
    _, budget_line_id = _approved_budget_with_line(client, project["id"])
    vendor = _create_vendor(client, "VND-009")
    _activate_commitment(client, project["id"], vendor["id"], budget_line_id)
    export = client.get(f"/projects/{project['id']}/exports/commitments")
    assert export.status_code == 200
    assert "text/csv" in export.headers.get("content-type", "")
    assert "CTR-" in export.text or "commitment" in export.text.lower()


def test_budget_foundation_regression(client: TestClient) -> None:
    project = _create_project(client, "PRJ-COST-010")
    budget_id, _ = _approved_budget_with_line(client, project["id"])
    versions = client.get(f"/projects/{project['id']}/budgets")
    assert versions.status_code == 200
    assert any(item["id"] == budget_id and item["status"] == "approved" for item in versions.json()["items"])
