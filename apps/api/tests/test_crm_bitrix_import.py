"""CRM Bitrix import Phase 2 — identity, aliases, dry-run (zero writes)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User

from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.bitrix_import import (
    BitrixBundle,
    BitrixSourceRow,
    classify_bitrix_filename,
    run_bitrix_dry_run,
)
from investhome_api.services.crm.bitrix_commit import (
    BitrixCommitPermissionError,
    build_safe_contact_plans,
    commit_safe_bitrix_contacts,
)
from investhome_api.services.crm.bitrix_comment_commit import (
    commit_safe_historical_comments,
)
from investhome_api.services.crm.bitrix_agent_commit import (
    BitrixAgentPreflightError,
    commit_safe_agent_roles,
)
from investhome_api.services.crm.bitrix_agreement_commit import (
    BitrixAgreementPreflightError,
    commit_safe_agreements,
)
from investhome_api.services.crm.bitrix_project_aliases import BitrixProjectGroup, resolve_project_alias
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.services.crm.identity import IdentityIndex, IdentityMatchKind, IdentityRecord, parse_phone


def _row(**kwargs) -> BitrixSourceRow:
    defaults = {
        "source_file": "Aktif Müşteriler.xls",
        "role": "active_customers",
        "full_name": "Ada Soyad",
    }
    defaults.update(kwargs)
    return BitrixSourceRow(**defaults)


def _actor() -> User:
    # Authentication is disabled in these service tests; production calls still
    # require a loaded user with crm.import.
    return cast(User, SimpleNamespace(id=uuid4()))


def test_turkish_phone_normalization() -> None:
    plus = parse_phone("+90 532 123 45 67")
    zero = parse_phone("0532 123 45 67")
    national = parse_phone("5321234567")
    country = parse_phone("905321234567")
    assert plus is not None and plus.country == "TR" and plus.e164 == "+905321234567"
    assert zero is not None and zero.country == "TR" and zero.e164 == "+905321234567"
    assert national is not None and national.country == "TR" and national.e164 == "+905321234567"
    assert country is not None and country.country == "TR" and country.e164 == "+905321234567"
    assert plus.match_key == zero.match_key == national.match_key


def test_us_phone_normalization_does_not_assume_plus_one() -> None:
    explicit = parse_phone("+1 (202) 555-1234")
    eleven = parse_phone("12025551234")
    bare = parse_phone("2025551234")
    assert explicit is not None and explicit.country == "US" and explicit.e164 == "+12025551234"
    assert eleven is not None and eleven.country == "US" and eleven.e164 == "+12025551234"
    assert bare is not None
    assert bare.e164 is None
    assert bare.suspicious is True
    assert bare.match_key == "d:2025551234"


def test_phone_first_matching() -> None:
    index = IdentityIndex()
    phone_hit = IdentityRecord(
        key="phone",
        display_name="Phone Person",
        phone=parse_phone("+905321111111"),
        email="other@example.com",
        name_key="phone person",
        origin="os",
        contact_id=uuid4(),
    )
    email_hit = IdentityRecord(
        key="email",
        display_name="Email Person",
        phone=parse_phone("+905322222222"),
        email="same@example.com",
        name_key="email person",
        origin="os",
        contact_id=uuid4(),
    )
    index.add(phone_hit)
    index.add(email_hit)
    match = index.match("+90 532 111 11 11", "same@example.com", "Email Person")
    assert match.kind == IdentityMatchKind.PHONE
    assert match.record is not None
    assert match.record.key == "phone"


def test_email_fallback_matching() -> None:
    index = IdentityIndex()
    index.add(
        IdentityRecord(
            key="email",
            display_name="Mail Person",
            phone=parse_phone("+905323333333"),
            email="only@example.com",
            name_key="mail person",
            origin="os",
            contact_id=uuid4(),
        )
    )
    match = index.match(None, "only@example.com", "Someone Else")
    assert match.kind == IdentityMatchKind.EMAIL
    assert match.record is not None
    assert match.record.key == "email"


def test_name_only_is_review_never_auto_link() -> None:
    index = IdentityIndex()
    index.add(
        IdentityRecord(
            key="named",
            display_name="Ali Kaya",
            phone=parse_phone("+905324444444"),
            email="ali@example.com",
            name_key="ali kaya",
            origin="os",
            contact_id=uuid4(),
        )
    )
    match = index.match(None, None, "Ali Kaya")
    assert match.kind == IdentityMatchKind.NAME_REVIEW
    assert match.record is None
    assert len(match.candidates) == 1

    empty = index.match(None, None, None)
    assert empty.kind == IdentityMatchKind.NO_IDENTITY


def test_bare_us_ten_digit_does_not_match_without_safe_country_context() -> None:
    index = IdentityIndex()
    index.add(
        IdentityRecord(
            key="us",
            display_name="US Person",
            phone=parse_phone("+12025551234"),
            email=None,
            name_key="us person",
            origin="os",
            contact_id=uuid4(),
        )
    )
    match = index.match("2025551234", None, "US Person")
    assert match.kind == IdentityMatchKind.NAME_REVIEW


def test_safe_identity_precedes_same_name_collision() -> None:
    index = IdentityIndex()
    index.add(
        IdentityRecord(
            key="quarantined",
            display_name="Same Name",
            phone=None,
            email=None,
            name_key="same name",
            origin="junk",
        )
    )

    match = index.match("+905321234567", "safe@example.com", "Same Name")

    assert match.kind == IdentityMatchKind.NONE
    assert match.reason == "deterministic_unmatched_same_name_warning"
    assert len(match.candidates) == 1


def test_unsafe_phone_and_invalid_email_are_not_deterministic_keys() -> None:
    index = IdentityIndex()
    index.add(
        IdentityRecord(
            key="unsafe",
            display_name="Unsafe Identity",
            phone=parse_phone("12345"),
            email="invalid-email",
            name_key="unsafe identity",
            origin="junk",
        )
    )

    assert index.match("12345", None, "Different Name").kind == IdentityMatchKind.NO_IDENTITY
    assert index.match(None, "invalid-email", "Different Name").kind == IdentityMatchKind.NO_IDENTITY
    assert index.match("12345", None, "Unsafe Identity").kind == IdentityMatchKind.NAME_REVIEW


def test_agreement_project_alias_resolution() -> None:
    known = resolve_project_alias("1307 K St.xls")
    assert known.group == BitrixProjectGroup.KST_1307
    assert known.label == "1307 K St"
    reit = resolve_project_alias("REIT", project_ids_by_name={"1307": uuid4()})
    assert reit.group == BitrixProjectGroup.REIT
    assert reit.project_id is None
    unknown = resolve_project_alias("Random Tower")
    assert unknown.group is None
    assert unknown.unknown_value == "Random Tower"
    fuzzy_rejected = resolve_project_alias("almost uniloft maybe")
    assert fuzzy_rejected.group is None


def test_classify_turkish_bitrix_filenames() -> None:
    assert classify_bitrix_filename("Aktif Müşteriler.xls") == ("active_customers", None)
    assert classify_bitrix_filename("Aktif uzun dönem yorumları olan iyi müşteriler.xls")[0] == "active_comments"
    assert classify_bitrix_filename("Junklar.xls")[0] == "junk"
    assert classify_bitrix_filename("Junk yorumları olan iyi müşteriler.xls")[0] == "junk_comments"
    assert classify_bitrix_filename("Aktif Acentalar.xls") == ("agents", None)
    assert classify_bitrix_filename("1307 K St.xls") == ("agreements", "1307_k_st")
    assert classify_bitrix_filename("Anlaşmalar 1307 k st.xls") == ("agreements", "1307_k_st")
    assert classify_bitrix_filename("Anlaşmalar 1313 Penn.xls") == ("agreements", "1313_penn")
    assert classify_bitrix_filename("Anlaşmalar 1812 H Pl.xls") == ("agreements", "1812_h_pl")
    assert classify_bitrix_filename("Anlaşmalar 2319 ontario.xls") == ("agreements", "2319_ontario")
    assert classify_bitrix_filename("Anlaşmalar Reit.xls") == ("agreements", "reit")
    assert classify_bitrix_filename("Anlaşmalar Reıt.xls") == ("agreements", "reit")
    assert classify_bitrix_filename("Anlaşmalar The Temple.xls") == ("agreements", "the_temple")
    assert classify_bitrix_filename("Anlaşmalar Uniloft.xls") == ("agreements", "uniloft")


def test_fold_alias_maps_turkish_dotted_i_headers() -> None:
    from investhome_api.services.crm.bitrix_project_aliases import fold_alias

    assert fold_alias("İlk adı") == "ilk adi"
    assert fold_alias("İş E-postası") == "is e-postasi"
    assert fold_alias("Kişi: Mobil") == "kisi mobil"


def test_active_overrides_junk() -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="1", full_name="Same Person", phone="+905321000001", source_file="Aktif Müşteriler.xls"),
            _row(
                bitrix_id="9",
                role="junk",
                source_file="Junklar.xls",
                full_name="Same Person",
                phone="0532 100 00 01",
            ),
        ]
    )
    report = run_bitrix_dry_run(bundle)
    assert report.active_junk["present_in_both"] == 1
    assert report.active_junk["resolved_final_state_active"] == 1
    assert report.active_junk["resolved_final_state_junk"] == 0
    assert report.contacts["cross_file_duplicate_identities"] == 1


def test_supplementary_comments_never_create_contacts() -> None:
    bundle = BitrixBundle(
        rows=[
            _row(
                role="active_comments",
                source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                full_name="Comment Only",
                phone="+905321000002",
                comment="Long-term client",
            ),
            _row(
                role="junk_comments",
                source_file="Junk yorumları olan iyi müşteriler.xls",
                full_name="No Identity Comment",
                comment="orphan note",
            ),
        ]
    )
    report = run_bitrix_dry_run(bundle)
    assert report.contacts["total_main_source_rows"] == 0
    assert report.contacts["new_contact_candidates"] == 0
    assert report.comments["total_supplementary_comment_rows"] == 2
    assert report.comments["unmatched_comments"] >= 1


def test_agent_enriches_existing_contact(db: Session) -> None:
    created = create_contact(
        db,
        CrmContactCreate(
            contact_type="buyer",
            record_kind="person",
            display_name="Broker Buyer",
            primary_phone="+12025550100",
            primary_email="broker.buyer@example.com",
        ),
        actor=None,
    )
    db.commit()
    bundle = BitrixBundle(
        rows=[
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                full_name="Broker Buyer",
                phone="+1 202 555 0100",
                email="broker.buyer@example.com",
                bitrix_id="A-1",
            )
        ]
    )
    before = (frozenset(id(obj) for obj in db.new), frozenset(id(obj) for obj in db.dirty), frozenset(id(obj) for obj in db.deleted))
    report = run_bitrix_dry_run(bundle, db=db)
    after = (frozenset(id(obj) for obj in db.new), frozenset(id(obj) for obj in db.dirty), frozenset(id(obj) for obj in db.deleted))
    assert report.agents["total_agents"] == 1
    assert report.agents["matched_existing_contacts"] == 1
    assert report.agents["role_profile_enrichments"] == 1
    assert report.agents["new_contact_candidates"] == 0
    assert report.contacts["new_contact_candidates"] == 0
    assert created.id is not None
    assert before == after
    assert report.writes["db_writes"] == 0
    assert report.writes["session_mutated"] is False


def test_idempotent_dry_run_and_zero_db_writes(db: Session) -> None:
    contacts_before = db.query(CrmContact).count()
    agreements_before = db.query(CrmAgreement).count()
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="10", phone="+905321000010", email="one@example.com"),
            _row(bitrix_id="10", phone="+905321000010", email="one@example.com"),
            _row(
                role="agreements",
                source_file="Uniloft.xls",
                project_hint="Uniloft",
                bitrix_id="AGR-1",
                phone="+905321000010",
                full_name="Ada Soyad",
            ),
            _row(
                role="agreements",
                source_file="Mystery.xls",
                project_hint="Unknown Site",
                bitrix_id="AGR-2",
                phone="+905321000010",
            ),
        ]
    )
    first = run_bitrix_dry_run(bundle, db=db)
    second = run_bitrix_dry_run(bundle, db=db)
    assert first.to_dict() == second.to_dict()
    assert first.writes["db_writes"] == 0
    assert first.writes["session_mutated"] is False
    assert first.agreements["project_alias_matches"] == 1
    assert first.agreements["unknown_project_values"] == 1
    assert first.agreements["by_project"]["uniloft"]["source_rows"] == 1
    assert "invalid_email_samples" not in first.to_dict()["data_quality"]
    assert first.data_quality["duplicate_bitrix_ids"] >= 1
    assert db.query(CrmContact).count() == contacts_before
    assert db.query(CrmAgreement).count() == agreements_before


def test_dry_run_http_and_agreements_list(client: TestClient) -> None:
    dry = client.post(
        "/crm/bitrix/dry-run",
        json={
            "read_db": False,
            "rows": [
                {
                    "source_file": "Aktif Müşteriler.xls",
                    "full_name": "HTTP Person",
                    "phone": "+905321000099",
                    "email": "http@example.com",
                    "bitrix_id": "HTTP-1",
                }
            ],
        },
    )
    assert dry.status_code == 200, dry.text
    body = dry.json()
    assert body["writes"]["db_writes"] == 0
    assert "BITRIX DRY-RUN" in body["console"]
    assert body["contacts"]["new_contact_candidates"] == 1

    listed = client.get("/crm/agreements")
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["items"] == []
    labels = {item["label"] for item in payload["project_groups"]}
    assert labels == {
        "1307 K St",
        "1313 Penn",
        "1812 H Pl",
        "2319 Ontario",
        "REIT",
        "The Temple",
        "Uniloft",
    }


def test_name_only_rows_are_review_not_merged() -> None:
    bundle = BitrixBundle(
        rows=[
            _row(full_name="Ayşe Yılmaz", bitrix_id="N1", phone=None, email=None),
            _row(full_name="Ayse Yilmaz", bitrix_id="N2", phone=None, email=None, source_file="Junklar.xls", role="junk"),
        ]
    )
    report = run_bitrix_dry_run(bundle)
    assert report.contacts["rows_with_no_usable_identity"] >= 1
    assert report.contacts["name_only_review_candidates"] >= 1
    assert report.contacts["new_contact_candidates"] == 0
    assert report.active_junk["present_in_both"] == 0


def test_deterministic_row_bypasses_name_only_quarantine() -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="Q1", full_name="Same Name", phone=None, email=None),
            _row(
                bitrix_id="D1",
                full_name="Same Name",
                phone="+905321000099",
                email="deterministic@example.com",
                source_file="Junklar.xls",
                role="junk",
            ),
        ]
    )
    report = run_bitrix_dry_run(bundle)

    assert report.contacts["new_contact_candidates"] == 1
    assert report.contacts["rows_with_no_usable_identity"] == 1
    assert report.contacts["name_only_review_candidates"] == 0
    assert report.contacts["same_name_collision_warnings"] == 1
    assert report.contacts["same_name_quarantined_warnings"] == 1


def test_suspicious_phone_only_rows_are_review_not_collapsed() -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="S1", full_name="First Name", phone="12345", email=None),
            _row(
                bitrix_id="S2",
                full_name="Second Name",
                phone="12345",
                email=None,
                source_file="Junklar.xls",
                role="junk",
            ),
        ]
    )
    report = run_bitrix_dry_run(bundle)

    assert report.contacts["new_contact_candidates"] == 0
    assert report.contacts["suspicious_phone_review_candidates"] == 2
    assert report.contacts["cross_file_duplicate_identities"] == 0


def test_load_csv_directory_dry_run(tmp_path: Path) -> None:
    from investhome_api.services.crm.bitrix_import import load_bundle_from_directory

    csv_path = tmp_path / "Aktif Musteriler.csv"
    csv_path.write_text("id,Ad Soyad,Telefon,Email\n1,CSV Person,+905321000020,csv@example.com\n", encoding="utf-8")
    bundle = load_bundle_from_directory(tmp_path)
    report = run_bitrix_dry_run(bundle)
    assert report.contacts["total_main_source_rows"] == 1
    assert report.contacts["new_contact_candidates"] == 1
    assert report.writes["db_writes"] == 0
    assert "csv@example.com" not in report.format_console()


def test_real_bitrix_header_aliases_do_not_require_pii() -> None:
    from investhome_api.services.crm.bitrix_import import _map_headers, rows_from_table

    turkish = _map_headers(["ID", "Ad", "Soyad", "Cep telefonu", "İş telefonu", "E-posta", "Yorumlar"])
    assert turkish["bitrix_id"] == 0
    assert turkish["first_name"] == 1
    assert turkish["last_name"] == 2
    assert "phone" in turkish
    assert turkish["email"] == 5
    assert turkish["comment"] == 6

    english = _map_headers(["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "COMMENTS"])
    assert english["last_name"] == 2
    assert english["phone"] == 3
    assert english["email"] == 4

    bitrix_tr = _map_headers(
        ["ID", "İlk adı", "Soyadı", "Mobil", "İş E-postası", "Ev E-postası", "Yorum", "Müşteri Yorumu"]
    )
    assert bitrix_tr["first_name"] == 1
    assert bitrix_tr["last_name"] == 2
    assert bitrix_tr["phone"] == 3
    assert bitrix_tr["email"] == 4
    assert bitrix_tr["comment"] == 7

    deal = _map_headers(["ID", "Ad / Soyad", "E-Posta (R)", "Telefon (R)", "Kişi: Mobil", "Kişi: İş E-postası"])
    assert deal["full_name"] == 1
    assert deal["email"] == 2
    assert "phone" in deal

    rows = rows_from_table(
        source_file="Aktif Müşteriler.xls",
        headers=["ID", "Ad", "Soyad", "Cep telefonu", "E-posta"],
        records=[["11", "Ada", "Soyad", "+905321000030", "alias@example.com"]],
    )
    assert len(rows) == 1
    assert rows[0].role == "active_customers"
    assert rows[0].full_name == "Ada Soyad"
    assert rows[0].phone == "+905321000030"
    assert rows[0].email == "alias@example.com"


def test_comment_files_split_and_never_create_contacts() -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="C1", phone="+905321000040", email="keep@example.com"),
            _row(
                role="active_comments",
                source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                phone="+905321000040",
                comment="secret-note",
            ),
            _row(
                role="junk_comments",
                source_file="Junk yorumları olan iyi müşteriler.xls",
                full_name="Orphan",
                comment="other-secret",
            ),
        ]
    )
    report = run_bitrix_dry_run(bundle)
    assert report.comments["active_comments"]["matched_by_phone"] == 1
    assert report.comments["junk_comments"]["unmatched_comments"] == 1
    assert "secret-note" not in report.format_console()
    assert "other-secret" not in report.format_console()
    assert report.contacts["new_contact_candidates"] == 1


def test_safe_commit_is_idempotent_and_excludes_unsafe_rows(db: Session) -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="A1", full_name="Safe Active", phone="+905321000101", email=None),
            _row(
                bitrix_id="J1",
                full_name="Safe Active",
                phone="0532 100 01 01",
                email="safe@example.com",
                source_file="Junklar.xls",
                role="junk",
            ),
            _row(
                bitrix_id="S1",
                full_name="Suspicious",
                phone="12345",
                source_file="Junklar.xls",
                role="junk",
            ),
            _row(
                bitrix_id="Q1",
                full_name="Quarantine",
                phone=None,
                email=None,
                source_file="Junklar.xls",
                role="junk",
            ),
        ]
    )

    first = commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=100)
    assert first.attempted == 1
    assert first.created == 1
    assert first.updated == first.skipped == first.failed == 0
    assert first.review_excluded == 1
    assert first.quarantine_excluded == 1

    contact = db.query(CrmContact).one()
    assert contact.status.value == "active"
    assert contact.source == "Bitrix"
    metadata = (contact.metadata_json or {})["bitrix_import"]
    assert len(metadata["external_ids"]) == 2
    assert metadata["historical_junk"] is True
    assert set(metadata["source_roles"]) == {"active_customers", "junk"}

    second = commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=100)
    assert second.batch_identifier == first.batch_identifier
    assert second.created == second.updated == second.failed == 0
    assert second.skipped == 1
    assert db.query(CrmContact).count() == 1


def test_safe_commit_never_merges_by_name(db: Session) -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="N1", full_name="Same Display", phone="+905321000111"),
            _row(
                bitrix_id="N2",
                full_name="Same Display",
                phone="+905321000112",
                source_file="Junklar.xls",
                role="junk",
            ),
        ]
    )

    result = commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=100)

    assert result.created == 2
    assert db.query(CrmContact).count() == 2
    assert all(
        "same_name_deterministic_collision"
        in ((contact.metadata_json or {})["bitrix_import"]["warning_flags"])
        for contact in db.query(CrmContact).all()
    )


def test_safe_commit_rolls_back_whole_batch(db: Session, monkeypatch) -> None:
    import investhome_api.services.crm.bitrix_commit as commit_module

    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id="R1", full_name="Rollback One", phone="+905321000121"),
            _row(bitrix_id="R2", full_name="Rollback Two", phone="+905321000122"),
        ]
    )
    original = commit_module._apply_plan
    calls = 0

    def fail_second(session, plan):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated batch failure")
        return original(session, plan)

    monkeypatch.setattr(commit_module, "_apply_plan", fail_second)
    with pytest.raises(RuntimeError, match="simulated batch failure"):
        commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=100)

    assert db.query(CrmContact).count() == 0


def test_safe_commit_requires_crm_import_permission(db: Session, monkeypatch) -> None:
    import investhome_api.services.crm.bitrix_commit as commit_module

    monkeypatch.setattr(commit_module, "user_has_permission", lambda *_args, **_kwargs: False)
    bundle = BitrixBundle(rows=[_row(bitrix_id="P1", phone="+905321000131")])

    with pytest.raises(BitrixCommitPermissionError):
        commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=1)

    assert db.query(CrmContact).count() == 0


def test_full_contact_pool_creates_plain_agent_and_agreement_contacts(db: Session) -> None:
    bundle = BitrixBundle(
        rows=[
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                bitrix_id="AG1",
                phone="+905321000141",
            ),
            _row(
                role="agreements",
                source_file="Anlaşmalar Uniloft.xls",
                bitrix_id="D1",
                phone="+905321000142",
            ),
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                bitrix_id="D2",
                phone="+905321000142",
            ),
            _row(
                role="active_comments",
                source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                bitrix_id="C1",
                phone="+905321000141",
                comment="must not be written",
            ),
        ]
    )

    result = commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=100)

    assert result.created == 2
    assert db.query(CrmContact).count() == 2
    assert db.query(CrmAgreement).count() == 0
    assert all(contact.contact_type.value == "prospect" for contact in db.query(CrmContact).all())
    role_sets = {
        tuple((contact.metadata_json or {})["bitrix_import"]["source_roles"])
        for contact in db.query(CrmContact).all()
    }
    assert role_sets == {("agents",), ("agreements",)}
    comment_result = commit_safe_historical_comments(
        db,
        BitrixBundle(
            rows=[
                _row(
                    role="active_comments",
                    source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                    bitrix_id="C1",
                    phone="+905321000141",
                    comment="must remain review",
                )
            ]
        ),
        actor=_actor(),
    )
    assert comment_result.attempted == 0
    assert comment_result.review_excluded == 1
    assert db.query(CrmActivity).count() == 0


def test_safe_commit_offset_selects_non_overlapping_batch(db: Session) -> None:
    bundle = BitrixBundle(
        rows=[
            _row(bitrix_id=f"B{index}", full_name=f"Batch {index}", phone=f"+90532100{index:04d}")
            for index in range(1, 4)
        ]
    )

    result = commit_safe_bitrix_contacts(
        db,
        bundle,
        actor=_actor(),
        offset=1,
        limit=1,
    )

    assert result.attempted == 1
    assert result.created == 1
    assert db.query(CrmContact).count() == 1


def test_review_exclusions_stay_stable_after_idempotent_import(db: Session) -> None:
    bundle = BitrixBundle(
        rows=[
            _row(
                role="agreements",
                source_file=f"Anlaşmalar {index}.xls",
                bitrix_id=f"D{index}",
                phone="+905321000151",
            )
            for index in range(1, 4)
        ]
    )
    before = build_safe_contact_plans(db, bundle)
    assert before.ambiguous_excluded == 1

    first = commit_safe_bitrix_contacts(db, bundle, actor=_actor(), limit=100)
    after = build_safe_contact_plans(db, bundle)

    assert first.created == 1
    assert after.ambiguous_excluded == before.ambiguous_excluded
    assert after.review_excluded == before.review_excluded


def test_safe_historical_comments_attach_only_by_phone_or_email(db: Session) -> None:
    contacts = BitrixBundle(
        rows=[
            _row(bitrix_id="P1", full_name="Phone Target", phone="+905321000161"),
            _row(bitrix_id="E1", full_name="Email Target", phone=None, email="target@example.com"),
        ]
    )
    commit_safe_bitrix_contacts(db, contacts, actor=_actor(), limit=100)
    contacts_before = db.query(CrmContact).count()
    statuses_before = {contact.id: contact.status for contact in db.query(CrmContact).all()}
    comments = BitrixBundle(
        rows=[
            _row(
                role="active_comments",
                source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                bitrix_id="C1",
                full_name="Phone Target",
                phone="0532 100 01 61",
                comment="historical one",
            ),
            _row(
                role="junk_comments",
                source_file="Junk yorumları olan iyi müşteriler.xls",
                bitrix_id="C2",
                full_name="Email Target",
                phone=None,
                email="TARGET@example.com",
                comment="historical two",
            ),
            _row(
                role="active_comments",
                source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                bitrix_id="C3",
                full_name="Phone Target",
                phone=None,
                email=None,
                comment="name only",
            ),
            _row(
                role="junk_comments",
                source_file="Junk yorumları olan iyi müşteriler.xls",
                bitrix_id="C4",
                full_name="Unknown",
                phone=None,
                email="unknown@example.com",
                comment="unmatched",
            ),
        ]
    )

    first = commit_safe_historical_comments(db, comments, actor=_actor())
    assert first.attempted == 2
    assert first.created == 2
    assert first.skipped == first.failed == 0
    assert first.review_excluded == 2
    assert first.matched_by_phone == 1
    assert first.matched_by_email == 1
    assert db.query(CrmContact).count() == contacts_before
    assert {contact.id: contact.status for contact in db.query(CrmContact).all()} == statuses_before

    activities = db.query(CrmActivity).all()
    assert len(activities) == 2
    assert all(activity.activity_type.value == "comment" for activity in activities)
    assert all(activity.description for activity in activities)
    assert all(
        (activity.metadata_json or {})["bitrix_historical_comment"][
            "imported_historical_comment"
        ]
        is True
        for activity in activities
    )

    second = commit_safe_historical_comments(db, comments, actor=_actor())
    assert second.batch_identifier == first.batch_identifier
    assert second.created == 0
    assert second.skipped == 2
    assert second.duplicate_activities == 0
    assert db.query(CrmActivity).count() == 2


def test_historical_comment_batch_rolls_back_on_failure(db: Session, monkeypatch) -> None:
    import investhome_api.services.crm.bitrix_comment_commit as comment_module

    contacts = BitrixBundle(
        rows=[
            _row(bitrix_id="P1", phone="+905321000171"),
            _row(bitrix_id="P2", phone="+905321000172"),
        ]
    )
    commit_safe_bitrix_contacts(db, contacts, actor=_actor(), limit=100)
    comments = BitrixBundle(
        rows=[
            _row(
                role="active_comments",
                source_file="Aktif uzun dönem yorumları olan iyi müşteriler.xls",
                bitrix_id="C1",
                phone="+905321000171",
                comment="first",
            ),
            _row(
                role="junk_comments",
                source_file="Junk yorumları olan iyi müşteriler.xls",
                bitrix_id="C2",
                phone="+905321000172",
                comment="second",
            ),
        ]
    )
    original = comment_module._create_activity
    calls = 0

    def fail_second(session, plan, actor):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated comment failure")
        return original(session, plan, actor)

    monkeypatch.setattr(comment_module, "_create_activity", fail_second)
    with pytest.raises(RuntimeError, match="simulated comment failure"):
        commit_safe_historical_comments(db, comments, actor=_actor())

    assert db.query(CrmActivity).count() == 0


def test_safe_agent_enrichment_is_idempotent_and_preserves_primary_type(db: Session) -> None:
    source = BitrixBundle(
        rows=[
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                bitrix_id="A1",
                phone="+905321000181",
            ),
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                bitrix_id="A2",
                phone="0532 100 01 81",
            ),
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                bitrix_id="Q1",
                phone=None,
                email=None,
            ),
        ]
    )
    commit_safe_bitrix_contacts(db, source, actor=_actor(), limit=100)
    contact = db.query(CrmContact).one()
    original_phone = contact.primary_phone

    first = commit_safe_agent_roles(db, source, actor=_actor())
    db.refresh(contact)
    assert first.attempted == first.contacts_matched == 1
    assert first.role_type_additions == 1
    assert first.broker_profiles_created == 1
    assert first.broker_profiles_reused == 0
    assert first.agent_statuses_active == 1
    assert first.duplicate_source_rows == 1
    assert first.quarantine_excluded == 1
    assert first.contacts_created_accidentally == 0
    assert contact.contact_type.value == "prospect"
    assert {assignment.contact_type.value for assignment in contact.type_assignments} == {
        "prospect",
        "broker",
    }
    assert contact.broker_profile is not None
    assert contact.status.value == "active"
    assert contact.primary_phone == original_phone

    second = commit_safe_agent_roles(db, source, actor=_actor())
    assert second.role_type_additions == 0
    assert second.broker_profiles_created == 0
    assert second.broker_profiles_reused == 1
    assert second.skipped == 1
    assert second.duplicate_agent_rows == 0
    assert db.query(CrmContact).count() == 1


def test_safe_agent_enrichment_stops_before_write_if_contact_missing(db: Session) -> None:
    source = BitrixBundle(
        rows=[
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                bitrix_id="A1",
                phone="+905321000191",
            )
        ]
    )

    with pytest.raises(BitrixAgentPreflightError):
        commit_safe_agent_roles(db, source, actor=_actor())

    assert db.query(CrmContact).count() == 0


def test_safe_agent_enrichment_rolls_back_whole_batch(db: Session, monkeypatch) -> None:
    import investhome_api.services.crm.bitrix_agent_commit as agent_module

    source = BitrixBundle(
        rows=[
            _row(
                role="agents",
                source_file="Aktif Acentalar.xls",
                bitrix_id=f"A{index}",
                phone=f"+9053210002{index:02d}",
            )
            for index in range(1, 3)
        ]
    )
    commit_safe_bitrix_contacts(db, source, actor=_actor(), limit=100)
    original = agent_module._enrich_agent
    calls = 0

    def fail_second(session, contact, plan):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated agent failure")
        return original(session, contact, plan)

    monkeypatch.setattr(agent_module, "_enrich_agent", fail_second)
    with pytest.raises(RuntimeError, match="simulated agent failure"):
        commit_safe_agent_roles(db, source, actor=_actor())

    for contact in db.query(CrmContact).all():
        assert contact.broker_profile is None
        assert not contact.type_assignments


def test_safe_agreement_commit_is_idempotent_and_reuses_one_contact(db: Session) -> None:
    source = BitrixBundle(
        rows=[
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="D1",
                phone="+905321000211",
            ),
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="D2",
                phone="+905321000211",
            ),
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="Q1",
                phone=None,
                email=None,
                full_name="Review Only",
            ),
        ]
    )
    commit_safe_bitrix_contacts(db, source, actor=_actor(), limit=100)
    assert db.query(CrmContact).count() == 1

    first = commit_safe_agreements(db, source, actor=_actor())
    assert first.attempted == first.contact_matches == 2
    assert first.agreements_created == 2
    assert first.agreements_reused == 0
    assert first.quarantine_excluded == 1
    assert first.contacts_created_accidentally == 0
    agreements = db.query(CrmAgreement).all()
    assert len({agreement.contact_id for agreement in agreements}) == 1
    assert all(agreement.project_group == "reit" for agreement in agreements)
    assert all(agreement.project_id is None for agreement in agreements)

    second = commit_safe_agreements(db, source, actor=_actor())
    assert second.agreements_created == 0
    assert second.agreements_reused == second.skipped == 2
    assert second.duplicate_agreements == 0
    assert db.query(CrmAgreement).count() == 2


def test_safe_agreement_resolves_explicit_project_and_preserves_source_data(db: Session) -> None:
    project = Project(project_code="P-1307", project_name="1307")
    db.add(project)
    db.flush()
    source = BitrixBundle(
        rows=[
            _row(
                role="agreements",
                source_file="Anlaşmalar 1307 K St.xls",
                project_hint="1307_k_st",
                bitrix_id="D1",
                phone="+905321000221",
                extra={"source_fields": {"7:Payment": "preserved"}},
            )
        ]
    )
    commit_safe_bitrix_contacts(db, source, actor=_actor(), limit=100)

    result = commit_safe_agreements(db, source, actor=_actor())
    agreement = db.query(CrmAgreement).one()
    assert result.by_project["1307_k_st"]["project_id_resolved"] is True
    assert agreement.project_id == project.id
    assert agreement.metadata_json["source_data"] == source.rows[0].extra


def test_agreement_duplicate_and_name_only_rows_are_excluded(db: Session) -> None:
    existing_source = BitrixBundle(
        rows=[
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="D1",
                full_name="Canonical Person",
                phone="+905321000231",
            )
        ]
    )
    commit_safe_bitrix_contacts(db, existing_source, actor=_actor(), limit=100)
    duplicate_and_review = BitrixBundle(
        rows=[
            existing_source.rows[0],
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="D1",
                phone="+905321000231",
            ),
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="Q1",
                full_name="Canonical Person",
                phone=None,
                email=None,
            ),
        ]
    )

    result = commit_safe_agreements(db, duplicate_and_review, actor=_actor())
    assert result.agreements_created == 0
    assert result.review_excluded == 2
    assert result.quarantine_excluded == 1
    assert db.query(CrmAgreement).count() == 0


def test_safe_agreement_stops_before_write_if_deterministic_contact_missing(db: Session) -> None:
    source = BitrixBundle(
        rows=[
            _row(
                role="agreements",
                source_file="Anlaşmalar Reıt.xls",
                project_hint="reit",
                bitrix_id="D1",
                phone="+905321000241",
            )
        ]
    )

    with pytest.raises(BitrixAgreementPreflightError):
        commit_safe_agreements(db, source, actor=_actor())

    assert db.query(CrmAgreement).count() == 0
    assert db.query(CrmContact).count() == 0


def test_asama_header_maps_to_stage_without_fuzzy_match() -> None:
    from investhome_api.services.crm.bitrix_import import _map_headers, rows_from_table
    from investhome_api.services.crm.bitrix_stage_mapping import map_bitrix_stage

    mapping = _map_headers(["ID", "Aşama", "Müşteri Adayı İsmi", "Mobil"])
    assert mapping["stage"] == 1
    assert mapping["full_name"] == 2
    rows = rows_from_table(
        source_file="Aktif Müşteriler.xls",
        headers=["ID", "Aşama", "Müşteri Adayı İsmi", "Mobil"],
        records=[["9", "Potansiyel", "Ada Soyad", "+905321000301"]],
    )
    assert rows[0].stage == "Potansiyel"
    assert map_bitrix_stage("Potansiyel").value == "new"
    assert map_bitrix_stage("Ön Bilgi / Teklif Aşaması").value == "proposal_preparation"
    assert map_bitrix_stage("Uzun Dönem Yatırımcı") is None
    assert map_bitrix_stage("Acenta Müşterileri") is None
    assert map_bitrix_stage("Proje Ortaklığı") is None
    assert map_bitrix_stage("Junk Lead") is None
    assert map_bitrix_stage("potential") is None


def test_pipeline_commit_places_all_active_customers_in_yeni(db: Session) -> None:
    from investhome_api.models.sales import OpportunityPartyType, OpportunityStage, SalesOpportunity
    from investhome_api.services.crm.bitrix_pipeline_commit import run_bitrix_pipeline

    seed = BitrixBundle(
        rows=[
            _row(
                bitrix_id="P1",
                full_name="Potential Person",
                phone="+905321000401",
                stage="Potansiyel",
            ),
            _row(
                bitrix_id="T1",
                full_name="Proposal Person",
                phone="+905321000402",
                stage="Ön Bilgi / Teklif Aşaması",
            ),
            _row(
                bitrix_id="L1",
                full_name="Long Term Person",
                phone="+905321000403",
                stage="Uzun Dönem Yatırımcı",
            ),
            _row(
                bitrix_id="J9",
                full_name="Junk Only Person",
                phone="+905321000404",
                source_file="Junklar.xls",
                role="junk",
                stage="Junk Lead",
            ),
        ]
    )
    commit_safe_bitrix_contacts(db, seed, actor=_actor(), limit=100)
    contact_count = db.query(CrmContact).count()
    assert contact_count == 4

    dry = run_bitrix_pipeline(db, seed, actor=_actor(), dry_run=True)
    assert dry.dry_run is True
    assert dry.historical_sales_records_created == 0
    assert dry.historical_sales_records_planned == 3
    assert dry.unmapped_review_stages["Uzun Dönem Yatırımcı"] == 1
    assert dry.junk_excluded_from_pipeline == 0
    assert dry.active_source_rows == 3
    assert dry.canonical_active_customers == 3
    assert db.query(SalesOpportunity).count() == 0
    assert db.query(CrmContact).count() == contact_count

    first = run_bitrix_pipeline(db, seed, actor=_actor(), dry_run=False)
    assert first.historical_sales_records_created == 3
    assert first.pipeline_yeni_count == 3
    assert db.query(CrmContact).count() == contact_count
    opps = list(db.query(SalesOpportunity).all())
    assert len(opps) == 3
    assert {item.stage for item in opps} == {OpportunityStage.NEW}
    assert all(item.party_type == OpportunityPartyType.CRM_CONTACT for item in opps)
    assert all(item.crm_contact_id is not None for item in opps)
    junk = db.query(CrmContact).filter(CrmContact.display_name == "Junk Only Person").one()
    assert junk.status.value == "archived"
    assert all(item.crm_contact_id != junk.id for item in opps)

    second = run_bitrix_pipeline(db, seed, actor=_actor(), dry_run=False)
    assert second.historical_sales_records_created == 0
    assert second.historical_sales_records_reused == 3
    assert db.query(SalesOpportunity).count() == 3
    assert db.query(CrmContact).count() == contact_count


def test_junk_rows_capture_all_phones_and_emails() -> None:
    from investhome_api.services.crm.bitrix_import import rows_from_table

    rows = rows_from_table(
        source_file="Junklar.xls",
        headers=[
            "ID",
            "Aşama",
            "Müşteri Adayı İsmi",
            "Mobil",
            "İş Telefonu",
            "Diğer Telefon Numarası",
            "İş E-postası",
            "Ev E-postası",
            "Diğer E-posta",
            "Şirket Adı",
            "Pozisyon",
            "Adres",
            "Kaynak",
            "Junk Sebebi",
        ],
        records=[[
            "77",
            "Junk Lead",
            "Ada Soyad",
            "+905321000501",
            "+905321000502",
            "+905321000503",
            "work@example.com",
            "home@example.com",
            "other@example.com",
            "Acme A.S.",
            "Yonetici",
            "Istanbul",
            "Web Formu",
            "Ulaşılamadı",
        ]],
    )
    row = rows[0]
    assert row.role == "junk"
    assert row.phones == ["+905321000501", "+905321000502", "+905321000503"]
    assert row.emails == ["work@example.com", "other@example.com", "home@example.com"]
    assert row.company == "Acme A.S."
    assert row.job_title == "Yonetici"
    assert row.address == "Istanbul"
    assert row.source_channel == "Web Formu"
    assert row.junk_reason == "Ulaşılamadı"


def test_junk_field_backfill_fills_missing_without_overwrite_or_new_contact(db: Session) -> None:
    from investhome_api.services.crm.bitrix_field_backfill import run_bitrix_junk_field_backfill

    seed = BitrixBundle(
        rows=[
            _row(
                source_file="Junklar.xls",
                role="junk",
                bitrix_id="77",
                full_name="Junk Completeness",
                phone="+905321000601",
                phones=["+905321000601", "+905321000602"],
                email="keep@example.com",
                emails=["keep@example.com", "second@example.com"],
                company="Acme",
                job_title="Broker",
                address="Ankara",
                source_channel="Web",
                stage="Junk Lead",
                junk_reason="İlgilenmiyorum",
            )
        ]
    )
    commit_safe_bitrix_contacts(db, seed, actor=_actor(), limit=100)
    contact = db.query(CrmContact).filter(CrmContact.display_name == "Junk Completeness").one()
    contact.primary_email = "keep@example.com"
    contact.primary_phone = "+905321000601"
    db.flush()
    before = db.query(CrmContact).count()

    first = run_bitrix_junk_field_backfill(db, seed, actor=_actor(), dry_run=False)
    db.refresh(contact)
    assert first.contacts_updated == 1
    assert contact.primary_email == "keep@example.com"
    assert contact.secondary_phones == ["+905321000602"]
    assert contact.secondary_emails == ["second@example.com"]
    assert contact.organization_name == "Acme"
    assert contact.job_title == "Broker"
    assert contact.address_line1 == "Ankara"
    assert contact.junk_reason == "İlgilenmiyorum"
    assert db.query(CrmContact).count() == before

    second = run_bitrix_junk_field_backfill(db, seed, actor=_actor(), dry_run=False)
    assert second.contacts_updated == 0
    assert db.query(CrmContact).count() == before


def test_crm_demo_cleanup_deletes_only_deterministic_demo_records(db: Session) -> None:
    from investhome_api.db.demo.markers import INTEGRATED_DEMO_SOURCE
    from investhome_api.services.crm.demo_cleanup import cleanup_crm_demo_records

    keep = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="QA Keep Contact",
        source=None,
        status=CrmContactStatus.ACTIVE,
        is_demo=False,
    )
    bitrix = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Bitrix Keep Contact",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        is_demo=False,
    )
    demo = CrmContact(
        contact_type=CrmContactType.BROKER,
        display_name="Leyla Demo Agent",
        source=INTEGRATED_DEMO_SOURCE,
        status=CrmContactStatus.ACTIVE,
        is_demo=True,
    )
    db.add_all([keep, bitrix, demo])
    db.commit()

    dry = cleanup_crm_demo_records(db, dry_run=True)
    assert dry.planned["crm_contacts"] == 1
    assert db.query(CrmContact).count() == 3

    committed = cleanup_crm_demo_records(db, dry_run=False)
    db.commit()
    names = {row.display_name for row in db.query(CrmContact).all()}
    assert committed.deleted["crm_contacts"] == 1
    assert names == {"QA Keep Contact", "Bitrix Keep Contact"}


def test_split_multi_values_and_agreement_unit_company_headers() -> None:
    from investhome_api.services.crm.bitrix_import import _map_headers, rows_from_table
    from investhome_api.services.crm.identity import split_multi_values

    assert split_multi_values("+90 532 323 35 26, +90354300449") == [
        "+90 532 323 35 26",
        "+90354300449",
    ]
    mapping = _map_headers(
        ["ID", "Ad / Soyad", "Şirket", "Acente Ofis İsmi - Şirket", "Daire No", "E-Posta (R)", "Telefon (R)"]
    )
    assert mapping["unit_number"] == 4
    assert mapping["company"] == 3
    rows = rows_from_table(
        source_file="Anlaşmalar 1812 H Pl.xls",
        headers=["ID", "Ad / Soyad", "Daire No", "E-Posta (R)", "Telefon (R)", "Şirket"],
        records=[["54", "Berk Çimen", "12A", "c.berkcimen@gmail.com", "905304000000, 905322000001", "Acme"]],
    )
    assert rows[0].unit_number == "12A"
    assert rows[0].company == "Acme"
    assert rows[0].phones == ["905304000000", "905322000001"]
    assert rows[0].email == "c.berkcimen@gmail.com"


def test_forensic_repair_preserves_no_identity_and_filename_project(db: Session) -> None:
    from investhome_api.models.sales import SalesOpportunity
    from investhome_api.services.crm.bitrix_forensic_repair import run_bitrix_forensic_repair
    from investhome_api.services.crm.bitrix_import import BitrixBundle

    bundle = BitrixBundle(
        rows=[
            _row(
                source_file="Aktif Müşteriler.xls",
                role="active_customers",
                bitrix_id="37084",
                full_name="Eko Faktoring",
                phone=None,
                email=None,
                stage="Proje Ortaklığı",
            ),
            _row(
                source_file="Junklar.xls",
                role="junk",
                bitrix_id="38202",
                full_name="Anar Omarova",
                phone=None,
                email=None,
                junk_reason="Ulaşılamadı",
                stage="Junk Lead",
            ),
            _row(
                source_file="Aktif Acentalar.xls",
                role="agents",
                bitrix_id="738",
                full_name="Review Agent",
                phone=None,
                email=None,
                company="Prime Brokers",
            ),
            _row(
                source_file="Anlaşmalar 2319 ontario.xls",
                role="agreements",
                bitrix_id="426",
                full_name="Can Aydemir",
                email="aydemir.can@gmail.com",
                unit_number="4B",
            ),
        ]
    )
    report = run_bitrix_forensic_repair(db, bundle, actor=_actor(), dry_run=False)
    db.flush()
    assert report.active["represented"] == 1
    assert report.active["missing"] == 0
    assert report.junk["represented_source_rows"] == 1
    assert report.agents["represented_source_rows"] == 1
    assert report.agreements["by_project"]["2319_ontario"] == 1
    eko = db.query(CrmContact).filter(CrmContact.display_name == "Eko Faktoring").one()
    assert eko.review_required is True
    assert eko.status == CrmContactStatus.ACTIVE
    junk = db.query(CrmContact).filter(CrmContact.display_name == "Anar Omarova").one()
    assert junk.status == CrmContactStatus.ARCHIVED
    assert junk.junk_reason == "Ulaşılamadı"
    agent = db.query(CrmContact).filter(CrmContact.display_name == "Review Agent").one()
    assert agent.organization_name == "Prime Brokers"
    assert agent.contact_type == CrmContactType.BROKER
    agreement = db.query(CrmAgreement).one()
    assert agreement.project_group == "2319_ontario"
    assert agreement.unit_number == "4B"
    assert db.query(SalesOpportunity).count() == 1


def test_forensic_does_not_merge_placeholder_phone_by_name(db: Session) -> None:
    from investhome_api.services.crm.bitrix_forensic_repair import run_bitrix_forensic_repair

    existing = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Burak Bey",
        primary_phone="+905457956065",
        source="Bitrix",
        status=CrmContactStatus.ARCHIVED,
        metadata_json={"bitrix_import": {"external_ids": ["Junklar.xls:999"], "source_roles": ["junk"]}},
    )
    db.add(existing)
    db.flush()
    bundle = BitrixBundle(
        rows=[
            _row(
                source_file="Aktif Müşteriler.xls",
                role="active_customers",
                bitrix_id="37234",
                full_name="Burak Bey",
                phone="31615453186",
                email=None,
                stage="Acenta Müşterileri",
            )
        ]
    )
    run_bitrix_forensic_repair(db, bundle, actor=_actor(), dry_run=False)
    db.flush()
    named = list(db.query(CrmContact).filter(CrmContact.display_name == "Burak Bey").all())
    assert len(named) == 2
    active = [row for row in named if row.status == CrmContactStatus.ACTIVE][0]
    assert active.review_required is True
    assert "37234" in " ".join((active.metadata_json or {}).get("bitrix_import", {}).get("external_ids") or [])


def test_excel_number_as_text_never_uses_scientific_notation() -> None:
    from investhome_api.services.crm.bitrix_import import excel_number_as_text

    assert excel_number_as_text(905321234567.0) == "905321234567"
    assert excel_number_as_text(102.0) == "102"
    assert excel_number_as_text("9.05321234567E+11") == "905321234567"
    assert "e" not in excel_number_as_text(905321234567.0).lower()
    assert excel_number_as_text(905304000000.0) == "905304000000"


def test_extract_unit_number_copies_source_tokens_only() -> None:
    from investhome_api.services.crm.bitrix_import import extract_unit_number, rows_from_table

    assert extract_unit_number(daire_no="102", deal_name="1307 K ST 202 / Names") == "102"
    assert extract_unit_number(deal_name="1307 K ST 202 / Hayati - Eyyub - Göksel Canlılar") == "202"
    assert extract_unit_number(deal_name="1307 K ST 002 LLC / Galip, Muhsin Emre") == "002"
    assert extract_unit_number(deal_name="1313 Penn Unit101 LLC / Oraj Özgövde") == "Unit101"
    assert extract_unit_number(deal_name="1313 Penn 5 LLC / 302 Gizem, Bahar Basara") is None
    assert extract_unit_number(product="1812 H Pl B05", deal_name="1812 H PL 101 LLC Zafer") == "B05"
    assert extract_unit_number(deal_name="Uniloft Unit 208 LLC / Canlılar") == "Unit 208"
    assert extract_unit_number(deal_name="Uniloft C02 LLC / Aslı Acar") == "C02"
    assert extract_unit_number(deal_name="REIT Bilgehan Eryılmaz", project_hint="reit") is None
    assert extract_unit_number(deal_name="Albert Levi", project_hint="the_temple") is None

    rows = rows_from_table(
        source_file="Anlaşmalar 1812 H Pl.xls",
        headers=["ID", "Ad / Soyad", "Anlaşma Adı", "Ürün", "Daire No", "Telefon (R)"],
        records=[[78, "Zafer Yıldırım", "1812 H PL 101 LLC Zafer Yıldırım", "1812 H Pl 108", None, 905326000000.0]],
    )
    assert rows[0].unit_number == "108"
    assert rows[0].raw_source_phone == "905326000000"
    assert rows[0].phone == "905326000000"


def test_prefer_better_phone_does_not_overwrite_good_with_masked() -> None:
    from investhome_api.services.crm.identity import phone_is_better, prefer_better_phone

    good = "+905079172666"
    masked = "905079000000"
    assert phone_is_better(good, masked) is True
    assert phone_is_better(masked, good) is False
    assert prefer_better_phone(good, masked) == good
    assert prefer_better_phone(masked, None) == masked
    assert phone_is_better("1810640000000", "905322000000") is False


def test_agreement_unit_phone_repair_does_not_create_contacts(db: Session) -> None:
    from investhome_api.models.crm_agreement import CrmAgreementStatus
    from investhome_api.services.crm.bitrix_agreement_unit_phone_repair import (
        repair_agreement_units_and_phones,
    )
    from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow

    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Lale Şenyol",
        primary_email="lsenyol@gmail.com",
        primary_phone="905079000000",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
    )
    db.add(contact)
    db.flush()
    agreement = CrmAgreement(
        contact_id=contact.id,
        project_group="1812_h_pl",
        source="bitrix",
        source_external_id="Anlaşmalar 1812 H Pl.xls:116",
        status=CrmAgreementStatus.UNKNOWN,
        metadata_json={"contact_phone": "905079000000", "contact_email": "lsenyol@gmail.com"},
    )
    db.add(agreement)
    db.commit()
    before = db.query(CrmContact).count()
    bundle = BitrixBundle(
        rows=[
            BitrixSourceRow(
                source_file="Anlaşmalar 1812 H Pl.xls",
                role="agreements",
                bitrix_id="116",
                full_name="Lale Şenyol",
                email="lsenyol@gmail.com",
                phone="905079000000",
                raw_source_phone="905079000000",
                phones=["905079000000"],
                emails=["lsenyol@gmail.com"],
                deal_name="1820 H PL B008 LLC Lale Şenyol",
                product="1812 H Pl B08",
                unit_number="B08",
                project_hint="1812_h_pl",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar Reıt.xls",
                role="agreements",
                bitrix_id="206",
                full_name="Lale Şenyol",
                email="lsenyol@gmail.com",
                phone="905079172666",
                raw_source_phone="905079172666",
                phones=["905079172666"],
                emails=["lsenyol@gmail.com"],
                deal_name="#16400 Lale Şenyol / REIT",
                project_hint="reit",
            ),
        ]
    )
    report = repair_agreement_units_and_phones(db, bundle, dry_run=False)
    db.commit()
    db.refresh(contact)
    db.refresh(agreement)
    assert db.query(CrmContact).count() == before
    assert report.contacts_created == 0
    assert agreement.unit_number == "B08"
    assert contact.primary_phone == "+905079172666"
    assert report.phones_repaired


def test_crm_demo_cleanup_removes_known_qa_opportunity_only(db: Session) -> None:
    from investhome_api.models.lead import Lead
    from investhome_api.models.sales import OpportunityPartyType, OpportunityStage, SalesOpportunity
    from investhome_api.services.crm.demo_cleanup import cleanup_crm_demo_records

    qa_lead = Lead(full_name="API Verify Lead", email="api-verify@example.com")
    real_lead = Lead(full_name="Real Pipeline Lead", email="real-pipeline@example.com")
    db.add_all([qa_lead, real_lead])
    db.flush()
    qa_opp = SalesOpportunity(
        opportunity_code="OPP-20260716-0001",
        lead_id=qa_lead.id,
        party_id=qa_lead.id,
        party_type=OpportunityPartyType.LEAD,
        stage=OpportunityStage.PROPOSAL_SENT,
        is_demo=False,
        source=None,
    )
    bitrix_opp = SalesOpportunity(
        opportunity_code="BITRIX-HIST-0001",
        lead_id=real_lead.id,
        party_id=real_lead.id,
        party_type=OpportunityPartyType.LEAD,
        stage=OpportunityStage.NEW,
        is_demo=False,
        source="bitrix",
    )
    db.add_all([qa_opp, bitrix_opp])
    db.commit()

    report = cleanup_crm_demo_records(db, dry_run=False)
    db.commit()
    codes = {row.opportunity_code for row in db.query(SalesOpportunity).all()}
    names = {row.full_name for row in db.query(Lead).all()}
    assert report.deleted["sales_opportunities"] == 1
    assert codes == {"BITRIX-HIST-0001"}
    assert "API Verify Lead" not in names
    assert "Real Pipeline Lead" in names


def test_displayable_phone_hides_zero_masked_values() -> None:
    from investhome_api.services.crm.identity import displayable_phone

    assert displayable_phone("+905304000000") is None
    assert displayable_phone("905079000000", "+905079172666") == "+905079172666"
    assert displayable_phone(None, "") is None


def test_final_normalization_reit_junk_relink_and_rescue(db: Session, tmp_path: Path) -> None:
    from openpyxl import Workbook

    from investhome_api.models.crm_agreement import CrmAgreementStatus
    from investhome_api.services.crm.bitrix_final_normalization import (
        run_bitrix_final_normalization,
    )
    from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow

    wrong = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Burcu Muratoğlu Savaş",
        primary_email="burcumm@gmail.com",
        primary_phone="905304000000",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar 1812 H Pl.xls:68"]}},
    )
    berk = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Berk Çimen",
        primary_email="c.berkcimen@gmail.com",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
    )
    junk = CrmContact(
        contact_type=CrmContactType.PROSPECT,
        display_name="Junk Person",
        primary_email="junk.reason@example.com",
        source="Bitrix",
        status=CrmContactStatus.ARCHIVED,
        metadata_json={"bitrix_import": {"external_ids": ["Junklar.xls:99"], "source_files": ["Junklar.xls"]}},
    )
    db.add_all([wrong, berk, junk])
    db.flush()
    unit_sale = CrmAgreement(
        contact_id=wrong.id,
        project_group="1812_h_pl",
        source="bitrix",
        source_external_id="Anlaşmalar 1812 H Pl.xls:68",
        status=CrmAgreementStatus.UNKNOWN,
        metadata_json={
            "imported_historical_agreement": True,
            "source_file": "Anlaşmalar 1812 H Pl.xls",
            "source_name": "Berk Çimen",
            "contact_email": "c.berkcimen@gmail.com",
        },
    )
    reit = CrmAgreement(
        contact_id=berk.id,
        project_group="reit",
        source="bitrix",
        source_external_id="Anlaşmalar Reıt.xls:206",
        status=CrmAgreementStatus.UNKNOWN,
        unit_number="should-not-show",
        metadata_json={
            "imported_historical_agreement": True,
            "source_file": "Anlaşmalar Reıt.xls",
            "source_name": "Lale Şenyol",
        },
    )
    db.add_all([unit_sale, reit])
    db.commit()

    rescue = tmp_path / "rescue.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "4 Bitrix rescue checklist"
    sheet.append(
        [
            "Source full name",
            "Email",
            "Bitrix external/source ID",
            "Corrected phone",
            "Notes",
        ]
    )
    sheet.append(["Berk Çimen", "c.berkcimen@gmail.com", "Anlaşmalar 1812 H Pl.xls:54", "+905321112233", "Manual Bitrix note"])
    sheet.append(["Burcu", "burcumm@gmail.com", "Anlaşmalar 1812 H Pl.xls:68", "", ""])
    workbook.save(rescue)

    bundle = BitrixBundle(
        rows=[
            BitrixSourceRow(
                source_file="Anlaşmalar 1812 H Pl.xls",
                role="agreements",
                bitrix_id="68",
                full_name="Berk Çimen",
                email="c.berkcimen@gmail.com",
                project_hint="1812_h_pl",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar Reıt.xls",
                role="agreements",
                bitrix_id="206",
                full_name="Lale Şenyol",
                email="lsenyol@gmail.com",
                payment_amount="100000.00",
                project_hint="reit",
            ),
            BitrixSourceRow(
                source_file="Junklar.xls",
                role="junk",
                bitrix_id="99",
                full_name="Junk Person",
                email="junk.reason@example.com",
                junk_reason="İlgilenmiyorum",
            ),
        ]
    )
    before_contacts = db.query(CrmContact).count()
    before_agreements = db.query(CrmAgreement).count()
    report = run_bitrix_final_normalization(
        db,
        bundle,
        rescue_xlsx=rescue,
        reconciliation_xlsx=tmp_path / "recon.xlsx",
        dry_run=False,
    )
    db.commit()
    db.refresh(wrong)
    db.refresh(berk)
    db.refresh(junk)
    db.refresh(unit_sale)
    db.refresh(reit)

    assert db.query(CrmContact).count() == before_contacts
    assert db.query(CrmAgreement).count() == before_agreements
    assert unit_sale.contact_id == berk.id
    assert reit.investment_amount == "100000.00"
    assert reit.unit_number is None
    assert junk.junk_reason == "İlgilenmiyorum"
    assert berk.primary_phone == "+905321112233"
    assert "Manual Bitrix note" in (berk.notes or "")
    assert (berk.metadata_json or {}).get("bitrix_import", {}).get("manual_bitrix_verification") is True
    assert report.wrong_contact_repaired == 1
    assert report.reit_investment_updated == 1
    assert report.rescue_corrections_applied >= 1

    second = run_bitrix_final_normalization(
        db,
        bundle,
        rescue_xlsx=rescue,
        reconciliation_xlsx=tmp_path / "recon2.xlsx",
        dry_run=False,
    )
    db.commit()
    assert second.wrong_contact_repaired == 0
    assert second.reit_investment_updated == 0
    assert (tmp_path / "recon.xlsx").exists()


def test_rescue_blank_does_not_overwrite_existing_phone(db: Session, tmp_path: Path) -> None:
    from openpyxl import Workbook

    from investhome_api.services.crm.bitrix_final_normalization import run_bitrix_final_normalization
    from investhome_api.services.crm.bitrix_import import BitrixBundle

    contact = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Kept Phone",
        primary_email="kept@example.com",
        primary_phone="+905551112233",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["x:1"]}},
    )
    db.add(contact)
    db.commit()
    rescue = tmp_path / "blank.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Email", "Corrected phone"])
    sheet.append(["kept@example.com", ""])
    workbook.save(rescue)
    run_bitrix_final_normalization(
        db,
        BitrixBundle(rows=[]),
        rescue_xlsx=rescue,
        dry_run=False,
    )
    db.commit()
    db.refresh(contact)
    assert contact.primary_phone == "+905551112233"


def _reit_bundle_twelve(*, blank_ids: tuple[str, str] = ("586", "588")) -> BitrixBundle:
    from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow

    rows: list[BitrixSourceRow] = []
    for index in range(1, 13):
        bitrix_id = str(500 + index) if index <= 10 else blank_ids[index - 11]
        amount = "" if bitrix_id in blank_ids else "50000.00"
        rows.append(
            BitrixSourceRow(
                source_file="Anlaşmalar Reıt.xls",
                role="agreements",
                bitrix_id=bitrix_id,
                full_name=f"REIT Person {bitrix_id}",
                email=f"reit{bitrix_id}@example.com",
                payment_amount=amount,
                project_hint="reit",
            )
        )
    return BitrixBundle(rows=rows)


def test_detect_excluded_reit_uses_blank_gelir_for_required_ten() -> None:
    from investhome_api.services.crm.bitrix_reit_membership import detect_excluded_reit_source_ids

    excluded, reason = detect_excluded_reit_source_ids(_reit_bundle_twelve())
    assert reason == "operator_count_blank_gelir"
    assert excluded == {"Anlaşmalar Reıt.xls:586", "Anlaşmalar Reıt.xls:588"}


def test_workbook_reit_membership_is_authoritative(tmp_path: Path) -> None:
    from openpyxl import Workbook

    from investhome_api.services.crm.bitrix_reit_membership import detect_excluded_reit_source_ids

    bundle = _reit_bundle_twelve()
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "2 Missing units"
    sheet.append(
        [
            "Class",
            "Full Name",
            "Agreement Project",
            "Source Excel filename",
            "Bitrix external/source ID",
        ]
    )
    keep_ids = [str(500 + index) for index in range(1, 10)] + ["588"]
    for bitrix_id in keep_ids:
        sheet.append(
            ["A", f"REIT Person {bitrix_id}", "REIT", "Anlaşmalar Reıt.xls", f"Anlaşmalar Reıt.xls:{bitrix_id}"]
        )
    path = tmp_path / "rescue.xlsx"
    workbook.save(path)
    excluded, reason = detect_excluded_reit_source_ids(bundle, rescue_xlsx=path)
    assert reason == "workbook_membership"
    assert excluded == {"Anlaşmalar Reıt.xls:510", "Anlaşmalar Reıt.xls:586"}


def test_reit_membership_removes_agreements_keeps_contacts(db: Session) -> None:
    from investhome_api.models.crm_agreement import CrmAgreementStatus
    from investhome_api.services.crm.bitrix_final_normalization import run_bitrix_final_normalization

    bundle = _reit_bundle_twelve()
    contacts: list[CrmContact] = []
    for row in bundle.rows:
        contact = CrmContact(
            contact_type=CrmContactType.BUYER,
            display_name=row.full_name,
            primary_email=row.email,
            source="Bitrix",
            status=CrmContactStatus.ACTIVE,
            metadata_json={"bitrix_import": {"external_ids": [f"{row.source_file}:{row.bitrix_id}"]}},
        )
        contacts.append(contact)
    db.add_all(contacts)
    db.flush()
    for contact, row in zip(contacts, bundle.rows, strict=True):
        db.add(
            CrmAgreement(
                contact_id=contact.id,
                project_group="reit",
                source="bitrix",
                source_external_id=f"{row.source_file}:{row.bitrix_id}",
                status=CrmAgreementStatus.UNKNOWN,
                investment_amount=row.payment_amount or None,
                metadata_json={"imported_historical_agreement": True, "source_file": row.source_file},
            )
        )
    db.commit()
    before_contacts = db.query(CrmContact).count()
    report = run_bitrix_final_normalization(db, bundle, dry_run=False)
    db.commit()
    assert before_contacts == db.query(CrmContact).count()
    assert db.query(CrmAgreement).count() == 10
    remaining = {row.source_external_id for row in db.query(CrmAgreement).all()}
    assert "Anlaşmalar Reıt.xls:586" not in remaining
    assert "Anlaşmalar Reıt.xls:588" not in remaining
    assert db.query(CrmContact).filter(CrmContact.primary_email == "reit586@example.com").count() == 1
    assert db.query(CrmContact).filter(CrmContact.primary_email == "reit588@example.com").count() == 1
    assert report.reit_membership_reason == "operator_count_blank_gelir"
    assert report.reit_contacts_preserved == 2
    second = run_bitrix_final_normalization(db, bundle, dry_run=False)
    db.commit()
    assert db.query(CrmAgreement).count() == 10
    assert db.query(CrmContact).count() == before_contacts
    assert second.reit_membership_removed == []


def _workbook_row_headers() -> list[str]:
    return [
        "Source full name",
        "Email",
        "Bitrix external/source ID",
        "Corrected phone",
        "Unit number",
        "Project unit",
        "Classification reason",
        "OS contact name",
    ]


def test_workbook_correction_relinks_merges_and_is_idempotent(db: Session, tmp_path: Path) -> None:
    from openpyxl import Workbook

    from investhome_api.models.crm_agreement import CrmAgreementStatus
    from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow
    from investhome_api.services.crm.bitrix_workbook_correction import (
        detect_workbook_changes,
        run_bitrix_workbook_correction,
    )

    semra = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Semra Arli",
        primary_email="semra@example.com",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar 1812 H Pl.xls:72"]}},
    )
    gokhan = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Gökhan Bülbül",
        primary_email="gokhan@example.com",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar 2319 Ontario.xls:424"]}},
    )
    levi = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Levi Sunny",
        primary_email="sunny.levi@kww.com.tr",
        primary_phone="+905323617374",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar Reıt.xls:238", "Aktif Acentalar.xls:482"]}},
    )
    lale_1812 = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Lale Şenyol",
        primary_email="lsenyol@gmail.com",
        primary_phone="+905079172666",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar 1812 H Pl.xls:116"]}},
    )
    lale_reit = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Lale Şenyol",
        primary_email="lsenyol@gmail.com",
        primary_phone="+905079172666",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar Reıt.xls:206"]}},
    )
    gizem = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Gizem Basara",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar 1313 Penn.xls:124"]}},
    )
    albert = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Albert Levi",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar The Temple.xls:728"]}},
    )
    berk = CrmContact(
        contact_type=CrmContactType.BUYER,
        display_name="Berk Çimen",
        primary_email="c.berkcimen@gmail.com",
        source="Bitrix",
        status=CrmContactStatus.ACTIVE,
        metadata_json={"bitrix_import": {"external_ids": ["Anlaşmalar 1812 H Pl.xls:68"]}},
    )
    db.add_all([semra, gokhan, levi, lale_1812, lale_reit, gizem, albert, berk])
    db.flush()
    db.add_all(
        [
            CrmAgreement(
                contact_id=semra.id,
                project_group="1812_h_pl",
                source="bitrix",
                source_external_id="Anlaşmalar 1812 H Pl.xls:72",
                status=CrmAgreementStatus.UNKNOWN,
                unit_number="206",
            ),
            CrmAgreement(
                contact_id=gokhan.id,
                project_group="2319_ontario",
                source="bitrix",
                source_external_id="Anlaşmalar 2319 Ontario.xls:424",
                status=CrmAgreementStatus.UNKNOWN,
            ),
            CrmAgreement(
                contact_id=levi.id,
                project_group="reit",
                source="bitrix",
                source_external_id="Anlaşmalar Reıt.xls:238",
                status=CrmAgreementStatus.UNKNOWN,
                investment_amount="50000.00",
            ),
            CrmAgreement(
                contact_id=lale_1812.id,
                project_group="1812_h_pl",
                source="bitrix",
                source_external_id="Anlaşmalar 1812 H Pl.xls:116",
                status=CrmAgreementStatus.UNKNOWN,
                unit_number="B08",
            ),
            CrmAgreement(
                contact_id=lale_reit.id,
                project_group="reit",
                source="bitrix",
                source_external_id="Anlaşmalar Reıt.xls:206",
                status=CrmAgreementStatus.UNKNOWN,
                investment_amount="100000.00",
            ),
            CrmAgreement(
                contact_id=gizem.id,
                project_group="1313_penn",
                source="bitrix",
                source_external_id="Anlaşmalar 1313 Penn.xls:124",
                status=CrmAgreementStatus.UNKNOWN,
            ),
            CrmAgreement(
                contact_id=albert.id,
                project_group="the_temple",
                source="bitrix",
                source_external_id="Anlaşmalar The Temple.xls:728",
                status=CrmAgreementStatus.UNKNOWN,
            ),
            CrmAgreement(
                contact_id=berk.id,
                project_group="1812_h_pl",
                source="bitrix",
                source_external_id="Anlaşmalar 1812 H Pl.xls:68",
                status=CrmAgreementStatus.UNKNOWN,
                unit_number="305",
            ),
        ]
    )
    db.commit()

    original = tmp_path / "original.xlsx"
    current = tmp_path / "current.xlsx"
    orig_wb = Workbook()
    orig_sheet = orig_wb.active
    orig_sheet.title = "2 Missing units"
    orig_sheet.append(_workbook_row_headers())
    orig_sheet.append(
        ["Bilgehan Eryılmaz", "", "Anlaşmalar Reıt.xls:588", "", "", "REIT / —", "Unit genuinely not applicable", ""]
    )
    orig_sheet.append(["Oya Nermin Uyan", "oyanerminuyan@gmail.com", "Anlaşmalar 1812 H Pl.xls:72", "905323000000", "206", "1812 H Pl / 206", "", "Semra Arli"])
    orig_wb.save(original)

    cur_wb = Workbook()
    phones = cur_wb.active
    phones.title = "1 Unresolved phones"
    phones.append(_workbook_row_headers())
    phones.append(["Oya Nermin Uyan", "oyanerminuyan@gmail.com", "Anlaşmalar 1812 H Pl.xls:72", "905323121150", "206", "1812 H Pl / 206", "", "Semra Arli"])
    phones.append(["Arda Efe", "efearda@gmail.com", "Anlaşmalar 2319 Ontario.xls:424", "905324000000", "", "2319 Ontario / —", "", "Gökhan Bülbül"])
    phones.append(["Albert Levı", "", "Anlaşmalar The Temple.xls:728", "905300766720", "301-302", "The Temple / 301-302", "", "Albert Levi"])
    phones.append(["Berk Çimen", "c.berkcimen@gmail.com", "Anlaşmalar 1812 H Pl.xls:68", "905304150866", "304", "1812 H Pl / 304", "", "Burcu Muratoğlu Savaş"])
    units = cur_wb.create_sheet("2 Missing units")
    units.append(_workbook_row_headers())
    units.append(["Gizem Basara", "", "Anlaşmalar 1313 Penn.xls:124", "", "", "1313 Penn / —", "Unit 302", ""])
    units.append(["Lale Şenyol", "lsenyol@gmail.com", "Anlaşmalar Reıt.xls:206", "", "", "REIT / —", "Unit genuinely not applicable", ""])
    units.append(["Selim Levi Beceren", "sunnylevy@gmail.com", "Anlaşmalar Reıt.xls:238", "905323617374", "", "REIT / —", "Unit genuinely not applicable", "Levi Sunny"])
    checklist = cur_wb.create_sheet("4 Bitrix rescue checklist")
    checklist.append(_workbook_row_headers())
    checklist.append(["Oya Nermin Uyan", "oyanerminuyan@gmail.com", "Anlaşmalar 1812 H Pl.xls:72", "905323121150", "206", "1812 H Pl / 206", "", "Semra Arli"])
    checklist.append(["Lale Şenyol", "lsenyol@gmail.com", "Anlaşmalar 1812 H Pl.xls:116", "", "B08", "1812 H Pl / B08", "", ""])
    cur_wb.save(current)

    changes = detect_workbook_changes(original, current)
    kinds = {item["kind"] for item in changes}
    assert "deleted_row" in kinds
    assert any(item["source_id"] == "Anlaşmalar Reıt.xls:588" for item in changes if item["kind"] == "deleted_row")

    bundle = BitrixBundle(
        rows=[
            BitrixSourceRow(
                source_file="Anlaşmalar 1812 H Pl.xls",
                role="agreements",
                bitrix_id="72",
                full_name="Oya Nermin Uyan",
                email="oyanerminuyan@gmail.com",
                project_hint="1812_h_pl",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar 2319 Ontario.xls",
                role="agreements",
                bitrix_id="424",
                full_name="Arda Efe",
                email="efearda@gmail.com",
                phone="905324000000",
                project_hint="2319_ontario",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar Reıt.xls",
                role="agreements",
                bitrix_id="238",
                full_name="Selim Levi Beceren",
                email="sunnylevy@gmail.com",
                phone="905323617374",
                project_hint="reit",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar 1812 H Pl.xls",
                role="agreements",
                bitrix_id="116",
                full_name="Lale Şenyol",
                email="lsenyol@gmail.com",
                project_hint="1812_h_pl",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar Reıt.xls",
                role="agreements",
                bitrix_id="206",
                full_name="Lale Şenyol",
                email="lsenyol@gmail.com",
                payment_amount="100000.00",
                project_hint="reit",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar 1313 Penn.xls",
                role="agreements",
                bitrix_id="124",
                full_name="Gizem Basara",
                project_hint="1313_penn",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar The Temple.xls",
                role="agreements",
                bitrix_id="728",
                full_name="Albert Levı",
                project_hint="the_temple",
            ),
            BitrixSourceRow(
                source_file="Anlaşmalar 1812 H Pl.xls",
                role="agreements",
                bitrix_id="68",
                full_name="Berk Çimen",
                email="c.berkcimen@gmail.com",
                project_hint="1812_h_pl",
            ),
        ]
    )
    before_contacts = db.query(CrmContact).count()
    report = run_bitrix_workbook_correction(
        db, bundle, rescue_xlsx=current, original_xlsx=original, dry_run=False
    )
    db.commit()
    oya = db.query(CrmContact).filter(CrmContact.primary_email == "oyanerminuyan@gmail.com").one()
    arda = db.query(CrmContact).filter(CrmContact.primary_email == "efearda@gmail.com").one()
    selim = db.query(CrmContact).filter(CrmContact.primary_email == "sunnylevy@gmail.com").one()
    oya_ag = db.query(CrmAgreement).filter(CrmAgreement.source_external_id == "Anlaşmalar 1812 H Pl.xls:72").one()
    arda_ag = db.query(CrmAgreement).filter(CrmAgreement.source_external_id == "Anlaşmalar 2319 Ontario.xls:424").one()
    selim_ag = db.query(CrmAgreement).filter(CrmAgreement.source_external_id == "Anlaşmalar Reıt.xls:238").one()
    gizem_ag = db.query(CrmAgreement).filter(CrmAgreement.source_external_id == "Anlaşmalar 1313 Penn.xls:124").one()
    albert_ag = db.query(CrmAgreement).filter(CrmAgreement.source_external_id == "Anlaşmalar The Temple.xls:728").one()
    berk_ag = db.query(CrmAgreement).filter(CrmAgreement.source_external_id == "Anlaşmalar 1812 H Pl.xls:68").one()
    lale_ags = db.query(CrmAgreement).filter(
        CrmAgreement.source_external_id.in_(
            ["Anlaşmalar 1812 H Pl.xls:116", "Anlaşmalar Reıt.xls:206"]
        )
    ).all()
    active_lales = (
        db.query(CrmContact)
        .filter(CrmContact.display_name == "Lale Şenyol", CrmContact.status == CrmContactStatus.ACTIVE)
        .all()
    )
    db.refresh(levi)
    db.refresh(berk)
    db.refresh(albert)

    assert oya_ag.contact_id == oya.id
    assert oya.primary_phone == "+905323121150"
    assert oya.review_required is True
    assert arda_ag.contact_id == arda.id
    assert arda.primary_phone is None
    assert selim_ag.contact_id == selim.id
    assert selim.display_name == "Selim Levi Beceren"
    assert levi.status == CrmContactStatus.ACTIVE
    assert "Anlaşmalar Reıt.xls:238" not in (levi.metadata_json or {}).get("bitrix_import", {}).get("external_ids", [])
    assert gizem_ag.unit_number == "302"
    assert albert_ag.unit_number == "301-302"
    assert albert.primary_phone == "+905300766720"
    assert berk_ag.unit_number == "304"
    assert berk.primary_phone == "+905304150866"
    assert len(active_lales) == 1
    assert {row.contact_id for row in lale_ags} == {active_lales[0].id}
    assert db.query(CrmContact).count() == before_contacts + 3
    assert report.lale_merge and report.lale_merge["agreements_moved"] == 1
    assert "Arda Efe" in report.phones_left_blank or arda.display_name in report.phones_left_blank

    second = run_bitrix_workbook_correction(
        db, bundle, rescue_xlsx=current, original_xlsx=original, dry_run=False
    )
    db.commit()
    assert second.contacts_created == []
    assert second.links_repaired == []
    assert db.query(CrmContact).filter(CrmContact.primary_email == "oyanerminuyan@gmail.com").count() == 1
    assert db.query(CrmAgreement).count() == 8
    assert (
        db.query(CrmContact)
        .filter(CrmContact.display_name == "Lale Şenyol", CrmContact.status == CrmContactStatus.ACTIVE)
        .count()
        == 1
    )

