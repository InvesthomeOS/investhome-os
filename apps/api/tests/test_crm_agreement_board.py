"""Agreement board totals count the full filtered set, not a 200-row page."""

from datetime import date, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.unit_change import HISTORICAL_UNIT_CHANGE_SOURCE


def _contact(client: TestClient, name: str) -> str:
    response = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": name,
            "primary_email": f"{uuid4().hex[:8]}@example.com",
            "primary_phone": "+15551234567",
            "lifecycle_stage": "new",
            "priority": "normal",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["contact"]["id"]


def _row(
    *,
    contact_id: str,
    when: date,
    unit: str,
    stage: str,
    responsible: str,
    project_group: str = "uniloft",
    status: str = "active",
    source: str = "bitrix",
    metadata: dict | None = None,
) -> CrmAgreement:
    body = {"stage_label": stage, "responsible_person": responsible}
    if metadata:
        body.update(metadata)
    return CrmAgreement(
        contact_id=UUID(contact_id),
        project_group=project_group,
        source=source,
        source_external_id=f"board-{uuid4().hex}",
        status=status,
        agreement_date=when,
        unit_number=unit,
        hemen_kira=False,
        metadata_json=body,
    )


def test_board_counts_more_than_two_hundred_agreements(client: TestClient, db: Session) -> None:
    buyer = _contact(client, "Board Buyer")
    start = date(2020, 1, 1)
    rows: list[CrmAgreement] = []
    beyond = None
    for index in range(202):
        row = _row(
            contact_id=buyer,
            when=start + timedelta(days=index),
            unit="BOARD-BEYOND" if index == 0 else f"U-{index}",
            stage="Kazanıldı",
            responsible="Beyond" if index == 0 else "Ada",
        )
        if index == 0:
            beyond = row
        rows.append(row)
    rows.append(
        _row(
            contact_id=buyer,
            when=start + timedelta(days=400),
            unit="DEAL-WON",
            stage="deal won",
            responsible="Ada",
        )
    )
    rows.append(
        _row(
            contact_id=buyer,
            when=start + timedelta(days=401),
            unit="CODE-STAGE",
            stage="C1:NEW",
            responsible="Ada",
        )
    )
    for index in range(4):
        rows.append(
            _row(
                contact_id=buyer,
                when=start + timedelta(days=410 + index),
                unit=f"KIM-{index}",
                stage="Kimlik Bilgileri",
                responsible="Kim",
            )
        )
    for index in range(2):
        rows.append(
            _row(
                contact_id=buyer,
                when=start + timedelta(days=420 + index),
                unit=f"TEMPLE-{index}",
                stage="Kazanıldı",
                responsible="Temple",
                project_group="the_temple",
            )
        )
    rows.append(
        _row(
            contact_id=buyer,
            when=start + timedelta(days=300),
            unit="CANCELLED-1",
            stage="Kazanıldı",
            responsible="Cancelled Owner",
            status="cancelled",
        )
    )
    rows.append(
        _row(
            contact_id=buyer,
            when=start + timedelta(days=430),
            unit="HIST-1",
            stage="Kazanıldı",
            responsible="Ada",
            source=HISTORICAL_UNIT_CHANGE_SOURCE,
        )
    )
    rows.append(
        _row(
            contact_id=buyer,
            when=start + timedelta(days=431),
            unit="DET-1",
            stage="Kazanıldı",
            responsible="Ada",
            status="cancelled",
            metadata={"relationship_detached": True},
        )
    )
    db.add_all(rows)
    db.commit()
    assert beyond is not None

    listed = client.get("/crm/agreements", params={"page": 1, "page_size": 10})
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 211
    assert len(listed.json()["items"]) == 10

    page_two = client.get(
        "/crm/agreements",
        params={"page": 2, "page_size": 10, "sort_by": "agreement_date", "sort_dir": "desc"},
    )
    assert page_two.json()["total"] == 211
    assert len(page_two.json()["items"]) == 10
    page_one_ids = {item["id"] for item in listed.json()["items"]}
    assert page_one_ids.isdisjoint({item["id"] for item in page_two.json()["items"]})

    board = client.get("/crm/agreements/board", params={"page_size": 25})
    assert board.status_code == 200, board.text
    body = board.json()
    assert body["kpis"]["total"] == 211
    assert body["kpis"]["won"] == 206
    assert body["kpis"]["progress"] == 4
    assert body["kpis"]["unstaged"] == 1
    assert "Beyond" in body["responsibles"]
    assert "Ada" in body["responsibles"]
    assert "Kimlik Bilgileri" in body["stages"]
    assert "Kazanıldı" in body["stages"]
    assert "Aşamasız" in body["stages"]
    won = next(column for column in body["columns"] if column["stage"] == "Kazanıldı")
    assert won["total"] == 206
    assert len(won["items"]) == 25

    uniloft = client.get("/crm/agreements", params={"project_group": "uniloft", "page_size": 10})
    uniloft_board = client.get("/crm/agreements/board", params={"project_group": "uniloft"})
    assert uniloft.json()["total"] == 209
    assert uniloft_board.json()["kpis"]["total"] == 209
    assert uniloft_board.json()["kpis"]["won"] == 204

    temple = client.get("/crm/agreements", params={"project_group": "the_temple", "page_size": 10})
    temple_board = client.get("/crm/agreements/board", params={"project_group": "the_temple"})
    assert temple.json()["total"] == 2
    assert temple_board.json()["kpis"]["total"] == 2

    cancelled = client.get("/crm/agreements", params={"status": "cancelled", "page_size": 10})
    cancelled_board = client.get("/crm/agreements/board", params={"status": "cancelled"})
    assert cancelled.json()["total"] == 2
    assert cancelled_board.json()["kpis"]["total"] == 2

    found = client.get("/crm/agreements", params={"q": "BOARD-BEYOND", "page_size": 10})
    found_board = client.get("/crm/agreements/board", params={"q": "BOARD-BEYOND"})
    assert found.json()["total"] == 1
    assert found_board.json()["kpis"]["total"] == 1
    assert found.json()["items"][0]["id"] == str(beyond.id)

    hidden = client.get("/crm/agreements", params={"q": "HIST-1", "page_size": 10})
    hidden_board = client.get("/crm/agreements/board", params={"q": "HIST-1"})
    assert hidden.json()["total"] == 0
    assert hidden_board.json()["kpis"]["total"] == 0
    detached = client.get("/crm/agreements", params={"q": "DET-1", "page_size": 10})
    detached_board = client.get("/crm/agreements/board", params={"q": "DET-1"})
    assert detached.json()["total"] == 0
    assert detached_board.json()["kpis"]["total"] == 0
    detached_status = client.get(
        "/crm/agreements",
        params={"q": "DET-1", "status": "cancelled", "page_size": 10},
    )
    assert detached_status.json()["total"] == 1

    seen: list[str] = []
    page = 1
    reported_total = None
    while True:
        cards = client.get(
            "/crm/agreements/board/cards",
            params={
                "project_group": "uniloft",
                "stage": "Kazanıldı",
                "page": page,
                "page_size": 50,
            },
        )
        assert cards.status_code == 200, cards.text
        payload = cards.json()
        reported_total = payload["total"]
        assert payload["total"] == 204
        seen.extend(item["id"] for item in payload["items"])
        if page >= payload["pages"]:
            break
        page += 1
    assert reported_total == 204
    assert len(seen) == 204
    assert len(set(seen)) == 204
    assert str(beyond.id) == seen[-1]
    assert str(beyond.id) not in seen[:200]

    opened = client.get(f"/crm/agreements/{beyond.id}")
    assert opened.status_code == 200, opened.text


def _person(client: TestClient, name: str, contact_type: str = "prospect") -> str:
    response = client.post(
        "/crm/contacts",
        json={
            "contact_type": contact_type,
            "record_kind": "person",
            "display_name": name,
            "primary_email": f"{uuid4().hex[:8]}@example.com",
            "primary_phone": "+15551234567",
            "lifecycle_stage": "new",
            "priority": "normal",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["contact"]["id"]


def test_responsible_filter_uses_the_card_participant_source(
    client: TestClient, db: Session
) -> None:
    buyer = _person(client, "Board Buyer")
    owner = db.get(CrmContact, UUID(_person(client, "Zara Owner")))
    other = db.get(CrmContact, UUID(_person(client, "Aaa Other")))
    advisor = db.get(CrmContact, UUID(_person(client, "Acenta Danışmanı 1")))
    broker = db.get(CrmContact, UUID(_person(client, "Broker Pat", "broker")))
    assert owner is not None and other is not None and advisor is not None and broker is not None
    owner.metadata_json = {"bitrix_import": {"source_extras": {"responsible": "Card Owner"}}}
    other.metadata_json = {"bitrix_import": {"source_extras": {"responsible": "Unrelated Person"}}}
    advisor.metadata_json = {"bitrix_live": {"assigned_name": "Advisor Person"}}
    broker.metadata_json = {"bitrix_live": {"assigned_name": "Broker Person"}}

    from_participant = _row(
        contact_id=buyer,
        when=date(2024, 1, 1),
        unit="RESP-PART",
        stage="Kazanıldı",
        responsible="",
        metadata={"bitrix_live": {"assigned_name": ""}},
    )
    from_metadata = _row(
        contact_id=buyer,
        when=date(2024, 6, 1),
        unit="RESP-META",
        stage="Kazanıldı",
        responsible="Card Owner",
    )
    other_responsible = _row(
        contact_id=buyer,
        when=date(2024, 3, 1),
        unit="RESP-ADA",
        stage="Kimlik Bilgileri",
        responsible="Ada",
    )
    db.add_all([from_participant, from_metadata, other_responsible])
    db.flush()
    db.add_all(
        [
            CrmAgreementParticipant(
                agreement_id=from_participant.id,
                contact_id=owner.id,
                role="owner",
                is_primary=True,
                source="bitrix_live",
            ),
            CrmAgreementParticipant(
                agreement_id=from_participant.id,
                contact_id=other.id,
                role="owner",
                is_primary=False,
                source="bitrix_live",
            ),
            CrmAgreementParticipant(
                agreement_id=from_participant.id,
                contact_id=advisor.id,
                role="owner",
                is_primary=True,
                source="bitrix_live",
            ),
            CrmAgreementParticipant(
                agreement_id=from_participant.id,
                contact_id=broker.id,
                role="owner",
                is_primary=True,
                source="bitrix_live",
            ),
        ]
    )
    db.commit()

    board = client.get("/crm/agreements/board")
    assert board.status_code == 200, board.text
    body = board.json()
    assert body["responsibles"] == ["Ada", "Card Owner"]
    assert "Unrelated Person" not in body["responsibles"]
    assert "Advisor Person" not in body["responsibles"]
    assert "Broker Person" not in body["responsibles"]

    selected = client.get("/crm/agreements/board", params={"responsible": "Card Owner"})
    assert selected.status_code == 200, selected.text
    chosen = selected.json()
    assert chosen["kpis"]["total"] == 2
    assert chosen["kpis"]["won"] == 2
    assert chosen["kpis"]["progress"] == 0
    column = next(item for item in chosen["columns"] if item["stage"] == "Kazanıldı")
    assert column["total"] == 2
    assert {item["responsible_name"] for item in column["items"]} == {"Card Owner"}
    assert "Kimlik Bilgileri" not in {item["stage"] for item in chosen["columns"]}

    seen: list[str] = []
    for page in (1, 2):
        cards = client.get(
            "/crm/agreements/board/cards",
            params={
                "stage": "Kazanıldı",
                "responsible": "Card Owner",
                "page": page,
                "page_size": 1,
            },
        )
        assert cards.status_code == 200, cards.text
        payload = cards.json()
        assert payload["total"] == 2
        assert [item["responsible_name"] for item in payload["items"]] == ["Card Owner"]
        seen.extend(item["id"] for item in payload["items"])
    assert seen == [str(from_metadata.id), str(from_participant.id)]
    assert len(set(seen)) == 2

    unrelated = client.get("/crm/agreements/board", params={"responsible": "Unrelated Person"})
    assert unrelated.json()["kpis"]["total"] == 0
    listed = client.get("/crm/agreements", params={"page": 1, "page_size": 10})
    assert listed.json()["total"] == 3
