"""CRM financial field access: crm:read does not imply crm:view_financial."""

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContactType
from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.auth_service import hash_password
from investhome_api.services.crm.contact_service import create_contact


DEMO_PASSWORD = "Demo123!"
SALES_EMAIL = "sales@example.com"


def _login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _crm_read_user(db: Session) -> str:
    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one()
    role = Role(name="crm_read_only", code=f"crm_read_{uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    email = f"crm.read.{uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="CRM Read Only",
        hashed_password=hash_password(DEMO_PASSWORD),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    return email


def _seed_financial_contact(db: Session) -> tuple[UUID, UUID, UUID]:
    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.INVESTOR,
            display_name=f"Financial Deal Owner {uuid4().hex[:6]}",
        ),
    )
    unit = CrmAgreement(
        contact_id=contact.id,
        project_group="uniloft",
        source="bitrix",
        source_external_id=f"unit:{uuid4().hex[:8]}",
        unit_number="12A",
        investment_amount="450000",
        metadata_json={
            "purchase_price": "450000",
            "deposit": "25000",
            "kapora": "25000",
            "payment_amount": "120000",
            "opportunity": "450000",
            "currency": "USD",
            "payment_dates": "2026-01-15",
        },
    )
    reit = CrmAgreement(
        contact_id=contact.id,
        project_group="reit",
        source="bitrix",
        source_external_id=f"reit:{uuid4().hex[:8]}",
        investment_amount="75000",
        metadata_json={"currency": "USD", "opportunity": "75000"},
    )
    db.add_all([unit, reit])
    db.commit()
    db.refresh(unit)
    db.refresh(reit)
    return contact.id, unit.id, reit.id


def _assert_no_financial_amounts(payload: dict) -> None:
    financial_keys = {
        "investment_amount",
        "amount_label",
        "deposit_amount",
        "payment_dates",
        "share_ratio",
        "amount",
        "currency",
        "purchase_price",
        "deposit",
        "payment_amount",
        "amount_and_currency_amount",
        "amount_and_currency_currency",
        "amount_and_currency_label",
        "amount_and_currency_field_id",
    }
    for key in financial_keys:
        if key in payload:
            assert payload[key] in (None, "", [], {}), key
    if "payment" in payload:
        assert payload["payment"] in (None, {}, [])
    if "payment_fields" in payload:
        assert payload["payment_fields"] == []
    if "extra_fields" in payload:
        assert payload["extra_fields"] == []
    if "verified_amount_totals" in payload:
        assert payload["verified_amount_totals"] == []
    for participant in payload.get("participants") or []:
        assert participant.get("ownership_pct") in (None, "")
    for related in payload.get("related_purchases") or []:
        assert related.get("amount_label") in (None, "")


def test_crm_read_without_view_financial_hides_amounts(auth_client: TestClient, db: Session) -> None:
    contact_id, unit_id, reit_id = _seed_financial_contact(db)
    email = _crm_read_user(db)
    db.commit()
    _login(auth_client, email)

    detail = auth_client.get(f"/crm/contacts/{contact_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["id"] == str(contact_id)
    assert body["display_name"]
    assert body["verified_amount_totals"] == []
    _assert_no_financial_amounts(body)

    agreements = body["crm_agreements"]
    unit = next(item for item in agreements if item["project_group"] == "uniloft")
    reit = next(item for item in agreements if item["project_group"] == "reit")
    assert unit["unit_number"] == "12A"
    assert unit["status"]
    _assert_no_financial_amounts(unit)
    assert reit["investment_amount"] is None
    assert reit["unit_number"] in {None, ""}

    purchases = body["purchases"]
    assert purchases
    for purchase in purchases:
        assert purchase["project_group"] in {"uniloft", "reit"}
        _assert_no_financial_amounts(purchase)

    listed = auth_client.get("/crm/contacts", params={"search": body["display_name"]})
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json()["items"] if item["id"] == str(contact_id))
    assert row["agreement_count"] >= 2
    assert row["verified_amount_totals"] == []

    agreement_list = auth_client.get("/crm/agreements", params={"contact_id": str(contact_id)})
    assert agreement_list.status_code == 200, agreement_list.text
    list_items = agreement_list.json()["items"]
    assert {item["id"] for item in list_items} >= {str(unit_id), str(reit_id)}
    list_unit = next(item for item in list_items if item["id"] == str(unit_id))
    assert list_unit["unit_number"] == "12A"
    assert list_unit["project_group"] == "uniloft"
    _assert_no_financial_amounts(list_unit)
    list_reit = next(item for item in list_items if item["id"] == str(reit_id))
    _assert_no_financial_amounts(list_reit)

    card = auth_client.get(f"/crm/agreements/{unit_id}")
    assert card.status_code == 200, card.text
    card_body = card.json()
    assert card_body["agreement_id"] == str(unit_id)
    assert card_body["unit_number"] == "12A"
    assert card_body["project_group"] == "uniloft"
    _assert_no_financial_amounts(card_body)


def test_view_financial_user_sees_full_deal_economics(auth_client: TestClient, db: Session) -> None:
    contact_id, unit_id, reit_id = _seed_financial_contact(db)
    _login(auth_client, SALES_EMAIL)

    detail = auth_client.get(f"/crm/contacts/{contact_id}")
    assert detail.status_code == 200, detail.text
    body = detail.json()
    totals = {item["total"] for item in body["verified_amount_totals"]}
    assert "525000" in totals
    unit = next(item for item in body["crm_agreements"] if item["project_group"] == "uniloft")
    reit = next(item for item in body["crm_agreements"] if item["project_group"] == "reit")
    assert unit["purchase_price"] == "450000"
    assert unit["deposit"] == "25000"
    assert unit["payment_amount"] == "120000"
    assert reit["investment_amount"] == "75000"

    purchase = next(item for item in body["purchases"] if item["agreement_id"] == str(unit_id))
    assert purchase["amount"] == "450000"
    assert purchase["currency"] == "USD"

    listed = auth_client.get("/crm/contacts", params={"search": body["display_name"]})
    row = next(item for item in listed.json()["items"] if item["id"] == str(contact_id))
    assert {item["total"] for item in row["verified_amount_totals"]} == {"525000"}

    agreement_list = auth_client.get("/crm/agreements", params={"contact_id": str(contact_id)})
    list_unit = next(item for item in agreement_list.json()["items"] if item["id"] == str(unit_id))
    assert list_unit["investment_amount"] == "450000"
    assert list_unit["amount_label"]
    assert list_unit["deposit_amount"] == "25000"

    card = auth_client.get(f"/crm/agreements/{unit_id}")
    card_body = card.json()
    assert card_body["amount"] == "450000"
    assert card_body["currency"] == "USD"
    assert card_body["payment"].get("amount") == "450000" or card_body["payment"].get("deposit") == "25000"
    assert card_body["payment"].get("deposit") == "25000" or card_body["payment"].get("kapora") == "25000"

    reit_card = auth_client.get(f"/crm/agreements/{reit_id}")
    assert reit_card.status_code == 200
    assert reit_card.json()["amount"] in {"75000", "75000.00"} or reit_card.json()["amount_label"]
