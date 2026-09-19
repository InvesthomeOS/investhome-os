"""Safe-add verified Bitrix profile/payment/LLC fields for Nedim and Izzet only."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact

NEDIM = UUID("811c6aed-5f58-4c89-a9b1-0eebed64b9cf")
IZZET = UUID("339559ed-0d11-4e7c-a021-a07b388a817b")
AGREEMENT_198 = UUID("d30d258a-3b89-458a-bfa0-a2de4f9f0ba2")
AGREEMENT_656 = UUID("bdfd5ca1-e491-4896-b5d4-4b401ef428ac")
AGREEMENT_720 = UUID("444f6517-595a-4067-9c0c-3521708d2223")

NEDIM_ADDRESS = "Maslak Mah.Maslak Meydan Sk.No:3 Veko Giz Plaza P.K34398 Sarıyer/İstanbul/Türkiye"
IZZET_ADDRESS = "Rte de Hermance 31 A 1222 Vésenaz Geneva Switzerland"
ONTARIO_PAYMENT_NOTE = (
    "Acentemiz Keller Williams Platin Karma ofisinden Sunny Levi vasıtası satış gerçekleşiyor. "
    "Ontario Unit 403, $800.250 karşılığında Mortgage seçeneği ile alım yapılacak. "
    "$280.088 Peşinat 3 Hafta içinde gönderilecek "
    "$5.000 Kapora elden alındı."
)
UNILOFT_403_NOTE = (
    "Nedim Bey ve İzzet Bey Uniloft daire 403'ü erken teslim kampanyası peşin alım ile "
    "$470.000'a %50 %50 hisseli alım yaptılar."
)


def merge_live(row: CrmContact | CrmAgreement, payload: dict) -> list[str]:
    meta = dict(row.metadata_json or {}) if isinstance(row.metadata_json, dict) else {}
    live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
    changed: list[str] = []
    for key, value in payload.items():
        if value in (None, "", [], {}):
            continue
        current = live.get(key)
        if current in (None, "", [], {}) or current != value:
            live[key] = value
            changed.append(key)
    meta["bitrix_live"] = live
    row.metadata_json = meta
    flag_modified(row, "metadata_json")
    return changed


def fill_empty(row: CrmContact | CrmAgreement, field: str, value: object) -> bool:
    if value in (None, "", [], {}):
        return False
    current = getattr(row, field)
    if current not in (None, "", [], {}):
        return False
    setattr(row, field, value)
    return True


def main() -> None:
    db = SessionLocal()
    report: dict[str, object] = {}
    try:
        nedim = db.get(CrmContact, NEDIM)
        izzet = db.get(CrmContact, IZZET)
        ontario = db.get(CrmAgreement, AGREEMENT_198)
        uniloft_209 = db.get(CrmAgreement, AGREEMENT_656)
        uniloft_403 = db.get(CrmAgreement, AGREEMENT_720)
        if None in {nedim, izzet, ontario, uniloft_209, uniloft_403}:
            raise SystemExit("missing locked Nedim/Izzet entities")

        nedim_contact_fields: list[str] = []
        if fill_empty(nedim, "address_line1", NEDIM_ADDRESS):
            nedim_contact_fields.append("address_line1")
        if fill_empty(nedim, "job_title", "Factoring"):
            nedim_contact_fields.append("job_title")
        if fill_empty(nedim, "primary_phone", "+905324339513"):
            nedim_contact_fields.append("primary_phone")
        if fill_empty(nedim, "primary_email", "nkondu@gmail.com"):
            nedim_contact_fields.append("primary_email")
        report["nedim_contact_filled"] = nedim_contact_fields
        report["nedim_live"] = merge_live(
            nedim,
            {
                "contact_id": "588",
                "lead_id": "12512",
                "assigned_by_id": "1",
                "assigned_name": "Erman Devay",
                "source_id": "UC_37VR5B",
                "source_name": "Acenta Müşterisi",
                "address": NEDIM_ADDRESS,
                "profile_fields": [
                    {"label": "Adres", "value": NEDIM_ADDRESS},
                    {"label": "Pozisyon", "value": "Factoring"},
                    {"label": "Acente ofis", "value": "Keller Williams Platin&Karma"},
                    {"label": "Acente yatırım danışmanı", "value": "Sunny Levi"},
                    {"label": "Yatırım modeli", "value": "Ev Yatırımı"},
                    {"label": "Alım gücü", "value": "Yüksek"},
                ],
            },
        )

        izzet_contact_fields: list[str] = []
        if fill_empty(izzet, "address_line1", IZZET_ADDRESS):
            izzet_contact_fields.append("address_line1")
        if fill_empty(izzet, "primary_phone", "+41795969733"):
            izzet_contact_fields.append("primary_phone")
        if fill_empty(izzet, "primary_email", "izzetk@gmail.com"):
            izzet_contact_fields.append("primary_email")
        report["izzet_contact_filled"] = izzet_contact_fields
        report["izzet_live"] = merge_live(
            izzet,
            {
                "contact_id": "1160",
                "assigned_by_id": "92",
                "assigned_name": "Beyza Karakuş",
                "source_id": "UC_LPEQFO",
                "source_name": "Genel",
                "address": IZZET_ADDRESS,
                "profile_fields": [{"label": "Adres", "value": IZZET_ADDRESS}],
            },
        )

        for row, unit, amount, currency, begin, close in (
            (ontario, "403", "800250.00", "USD", date(2024, 7, 31), date(2025, 2, 27)),
            (uniloft_209, "209", "330757.00", "USD", date(2025, 11, 14), date(2025, 11, 21)),
            (uniloft_403, "403", "470000.00", "USD", date(2026, 3, 17), date(2026, 3, 24)),
        ):
            fill_empty(row, "unit_number", unit)
            fill_empty(row, "investment_amount", amount)
            fill_empty(row, "agreement_date", begin)

        report["ontario_live"] = merge_live(
            ontario,
            {
                "bitrix_deal_id": "198",
                "purchase_card_verified": True,
                "opportunity": "800250.00",
                "currency": "USD",
                "stage_id": "C8:WON",
                "stage_label": "Deal won",
                "begin_date": "2024-07-31",
                "close_date": "2025-02-27",
                "assigned_by_id": "8",
                "assigned_name": "Emin Berk Sever",
                "comments": ONTARIO_PAYMENT_NOTE,
                "payment_notes": ONTARIO_PAYMENT_NOTE,
                "llc_name": "2319 Ontario 403 LLC Nedim Kondu",
                "payment_fields": [
                    {"label": "Ödeme notu", "value": ONTARIO_PAYMENT_NOTE},
                    {"label": "Kapora", "value": "$5.000 elden alındı"},
                    {"label": "Peşinat", "value": "$280.088 — 3 hafta içinde gönderilecek"},
                    {"label": "Mortgage", "value": "Mortgage seçeneği ile alım"},
                ],
                "llc_fields": [{"label": "Şirket / LLC", "value": "2319 Ontario 403 LLC Nedim Kondu"}],
                "extra_fields": [
                    {"label": "Acente yatırım danışmanı", "value": "Sunny Levi"},
                    {"label": "Yatırım modeli", "value": "Ev Yatırımı"},
                    {"label": "Alım gücü", "value": "Yüksek"},
                ],
            },
        )
        report["uniloft_209_live"] = merge_live(
            uniloft_209,
            {
                "bitrix_deal_id": "656",
                "purchase_card_verified": True,
                "opportunity": "330757.00",
                "currency": "USD",
                "stage_id": "C26:FINAL_INVOICE",
                "stage_label": "Ev Teslim Süreci",
                "begin_date": "2025-11-14",
                "close_date": "2025-11-21",
                "assigned_by_id": "8",
                "assigned_name": "Emin Berk Sever",
                "llc_name": "Uniloft 209 LLC / Nedim Kondu",
                "llc_fields": [
                    {"label": "Şirket / LLC", "value": "Uniloft 209 LLC / Nedim Kondu"},
                    {"label": "Şirket belgeleri", "value": "4 dosya"},
                ],
            },
        )
        report["uniloft_403_live"] = merge_live(
            uniloft_403,
            {
                "bitrix_deal_id": "720",
                "purchase_card_verified": True,
                "opportunity": "470000.00",
                "currency": "USD",
                "stage_id": "C26:FINAL_INVOICE",
                "stage_label": "Ev Teslim Süreci",
                "begin_date": "2026-03-17",
                "close_date": "2026-03-24",
                "assigned_by_id": "92",
                "assigned_name": "Beyza Karakuş",
                "comments": UNILOFT_403_NOTE,
                "llc_name": "Uniloft 403 LLC / Nedim Kondu - İzzet Levi Dinçer",
                "llc_fields": [
                    {"label": "Şirket / LLC", "value": "Uniloft 403 LLC / Nedim Kondu - İzzet Levi Dinçer"},
                    {"label": "Şirket belgeleri", "value": "4 dosya"},
                ],
            },
        )
        db.commit()
        print(report)
    finally:
        db.close()


if __name__ == "__main__":
    main()
