"""Ingest WordPress website form submissions into the live CRM lead/contact path.

Does not use Bitrix, marketing form pending_review, or a parallel lead table.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.core.request_context import get_request_id
from investhome_api.models.activity import ActivityAction, ActivityActorType, ActivityEntityType, ActivitySource
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.schemas.crm_contacts import CrmContactCreate, CrmDuplicateCheckRequest
from investhome_api.schemas.website_forms import (
    WEBSITE_FORM_SOURCE_CODE,
    WEBSITE_FORM_SOURCE_LABEL,
    WebsiteFormSubmit,
    WebsiteFormSubmitResponse,
)
from investhome_api.services.activity_service import log_activity
from investhome_api.services.crm.contact_service import check_duplicates, create_contact
from investhome_api.services.crm.crm_lead_service import (
    _apply_owner,
    _blank,
    _log,
    _put_meta,
    _split_name,
)
from investhome_api.services.crm.identity import normalize_email, normalize_phone, parse_phone, phone_digits


class WebsiteFormIngestError(Exception):
    def __init__(self, status_code: int, public_detail: str) -> None:
        super().__init__(public_detail)
        self.status_code = status_code
        self.public_detail = public_detail


def _normalize_phone_required(raw: str) -> str:
    parsed = parse_phone(raw)
    if parsed is None or len(phone_digits(parsed.raw)) < 7:
        raise WebsiteFormIngestError(400, "phone is invalid")
    phone = parsed.e164 or parsed.match_key or normalize_phone(raw)
    if not phone:
        raise WebsiteFormIngestError(400, "phone is invalid")
    return phone


def _append_unique(values: list[str] | None, candidate: str) -> list[str]:
    existing = [item for item in (values or []) if item]
    if candidate not in existing:
        existing.append(candidate)
    return existing


def _match_contact(db: Session, *, email: str, phone: str) -> CrmContact | None:
    found = check_duplicates(
        db,
        CrmDuplicateCheckRequest(primary_email=email, primary_phone=phone),
    )
    email_hits = [item for item in found if item.match_reason == "email" and item.match_score >= 1.0]
    phone_hits = [item for item in found if item.match_reason == "phone" and item.match_score >= 1.0]
    for group in (email_hits, phone_hits):
        for item in group:
            contact = db.get(CrmContact, item.contact_id)
            if contact is not None and contact.archived_at is None:
                return contact
    return None


def _inquiry_notes(payload: WebsiteFormSubmit) -> str:
    lines = [WEBSITE_FORM_SOURCE_LABEL]
    if payload.form_type:
        lines.append(f"Form: {payload.form_type}")
    if payload.page_title:
        lines.append(f"Sayfa: {payload.page_title}")
    if payload.page_url:
        lines.append(f"URL: {payload.page_url}")
    if payload.project:
        lines.append(f"Proje: {payload.project}")
    if payload.occupation:
        lines.append(f"Meslek: {payload.occupation}")
    if payload.message:
        lines.append(f"Mesaj: {payload.message}")
    return "\n".join(lines)


def _enrich_existing_contact(
    contact: CrmContact,
    *,
    email: str,
    phone: str,
    occupation: str | None,
    inquiry_notes: str,
    accepted_at: str,
) -> None:
    if not contact.primary_email:
        contact.primary_email = email
    elif normalize_email(contact.primary_email) != email:
        contact.secondary_emails = _append_unique(contact.secondary_emails, email)

    if not contact.primary_phone:
        contact.primary_phone = phone
    elif normalize_phone(contact.primary_phone) != phone and contact.primary_phone != phone:
        contact.secondary_phones = _append_unique(contact.secondary_phones, phone)

    if occupation and not _blank(contact.job_title):
        contact.job_title = occupation[:120]

    if not contact.source:
        contact.source = WEBSITE_FORM_SOURCE_CODE

    existing_notes = (contact.notes or "").strip()
    if inquiry_notes not in existing_notes:
        merged = f"{existing_notes}\n\n{inquiry_notes}".strip() if existing_notes else inquiry_notes
        contact.notes = merged[:5000]

    compliance = dict(contact.compliance_data) if isinstance(contact.compliance_data, dict) else {}
    compliance["kvkk_accepted"] = True
    compliance.setdefault("kvkk_accepted_at", accepted_at)
    compliance["kvkk_source"] = WEBSITE_FORM_SOURCE_LABEL
    contact.compliance_data = compliance


def ingest_website_form(
    db: Session,
    payload: WebsiteFormSubmit,
    *,
    request_id: str | None = None,
) -> WebsiteFormSubmitResponse:
    email = normalize_email(payload.email) or payload.email
    phone = _normalize_phone_required(payload.phone)
    accepted_at = datetime.now(UTC).isoformat()
    inquiry_notes = _inquiry_notes(payload)
    existing = _match_contact(db, email=email, phone=phone)
    first_name, last_name = _split_name(payload.full_name)

    if existing is None:
        contact = create_contact(
            db,
            CrmContactCreate(
                contact_type=CrmContactType.PROSPECT,
                record_kind=CrmRecordKind.PERSON,
                display_name=payload.full_name,
                first_name=first_name,
                last_name=last_name,
                primary_email=email,
                primary_phone=phone,
                job_title=payload.occupation,
                source=WEBSITE_FORM_SOURCE_CODE,
                notes=inquiry_notes,
                lifecycle_stage=CrmLifecycleStage.NEW,
                status=CrmContactStatus.PROSPECT,
                compliance_data={
                    "kvkk_accepted": True,
                    "kvkk_accepted_at": accepted_at,
                    "kvkk_source": WEBSITE_FORM_SOURCE_LABEL,
                },
            ),
            actor=None,
        )
        matched_existing = False
        owner_id = None
    else:
        _enrich_existing_contact(
            existing,
            email=email,
            phone=phone,
            occupation=payload.occupation,
            inquiry_notes=inquiry_notes,
            accepted_at=accepted_at,
        )
        contact = existing
        matched_existing = True
        owner_id = contact.owner_user_id

    lead = Lead(
        full_name=payload.full_name,
        email=email,
        phone=phone,
        source=WEBSITE_FORM_SOURCE_CODE,
        campaign=_blank(payload.utm_campaign),
        interested_project=_blank(payload.project),
        notes=inquiry_notes,
        status=LeadStatus.NEW,
        provider="website",
        ingest_status="ok",
        is_demo=False,
    )
    _apply_owner(db, lead, owner_id)
    db.add(lead)
    db.flush()

    if contact.lead_id is None:
        contact.lead_id = lead.id

    _put_meta(
        lead,
        intake="website_form",
        source_label=WEBSITE_FORM_SOURCE_LABEL,
        form_type=payload.form_type or "general_contact",
        page_url=payload.page_url,
        page_title=payload.page_title,
        referrer=payload.referrer,
        language=payload.language,
        occupation=payload.occupation,
        utm_source=payload.utm_source,
        utm_medium=payload.utm_medium,
        utm_campaign=payload.utm_campaign,
        utm_content=payload.utm_content,
        utm_term=payload.utm_term,
        kvkk_accepted=True,
        kvkk_accepted_at=accepted_at,
        existing_person_id=str(contact.id),
        existing_person_name=contact.display_name,
        matched_existing=matched_existing,
        request_id=request_id or get_request_id(),
    )
    _log(
        db,
        lead,
        action=ActivityAction.CREATED,
        description_key="crm.leads.website_form.received",
        actor=None,
        metadata={
            "source": WEBSITE_FORM_SOURCE_LABEL,
            "form_type": payload.form_type or "general_contact",
            "matched_existing": matched_existing,
            "page_url": payload.page_url,
        },
    )
    log_activity(
        db,
        action=ActivityAction.NOTE_ADDED if matched_existing else ActivityAction.CREATED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="crm.contacts.website_form.inquiry",
        actor_user=None,
        actor_type=ActivityActorType.INTEGRATION,
        actor_name=WEBSITE_FORM_SOURCE_LABEL,
        source=ActivitySource.INTEGRATION,
        metadata={
            "lead_id": str(lead.id),
            "form_type": payload.form_type or "general_contact",
            "page_url": payload.page_url,
            "page_title": payload.page_title,
            "message": payload.message,
            "kvkk_accepted": True,
        },
        commit=False,
    )
    db.flush()
    return WebsiteFormSubmitResponse(
        accepted=True,
        duplicate=False,
        matched_existing=matched_existing,
        inquiry_id=lead.id,
        request_id=request_id or get_request_id(),
    )


def website_form_result_payload(result: WebsiteFormSubmitResponse) -> dict[str, Any]:
    return {
        "accepted": result.accepted,
        "duplicate": result.duplicate,
        "matched_existing": result.matched_existing,
        "inquiry_id": str(result.inquiry_id),
        "request_id": result.request_id,
    }


def website_form_result_from_payload(payload: dict[str, Any]) -> WebsiteFormSubmitResponse:
    inquiry_raw = payload.get("inquiry_id")
    try:
        inquiry_id = UUID(str(inquiry_raw))
    except (TypeError, ValueError) as exc:
        raise WebsiteFormIngestError(409, "Duplicate request") from exc
    return WebsiteFormSubmitResponse(
        accepted=True,
        duplicate=True,
        matched_existing=bool(payload.get("matched_existing")),
        inquiry_id=inquiry_id,
        request_id=str(payload.get("request_id") or "") or None,
    )
