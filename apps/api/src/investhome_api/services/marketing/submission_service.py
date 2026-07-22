"""Form submission pipeline — server-side, idempotent, consent-aware."""

from __future__ import annotations

import hashlib
import math
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.marketing import MarketingLeadContext, MarketingLeadHandoffStatus
from investhome_api.models.marketing_landing_conversion import (
    ConsentEvidence,
    FormFieldType,
    FormStatus,
    MarketingConversionEvent,
    MarketingForm,
    MarketingFormField,
    MarketingFormSubmission,
    MarketingTrackingContext,
    ReviewItemStatus,
    SubmissionReviewItem,
    SubmissionStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.services.marketing.consent_eligibility_service import get_consent_status
from investhome_api.services.marketing.lead_capture_service import apply_routing_rules, record_conversion_event


def compute_pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total else 1


def _get_submission_or_404(db: Session, submission_id: UUID) -> MarketingFormSubmission:
    sub = db.get(MarketingFormSubmission, submission_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


def list_submissions(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    form_id: UUID | None = None,
    status_filter: str | None = None,
) -> tuple[list[MarketingFormSubmission], int]:
    query = select(MarketingFormSubmission)
    if form_id:
        query = query.where(MarketingFormSubmission.form_id == form_id)
    if status_filter:
        query = query.where(MarketingFormSubmission.status == SubmissionStatus(status_filter))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(MarketingFormSubmission.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def _validate_submission_values(db: Session, form: MarketingForm, values: dict) -> tuple[dict, list[str]]:
    """Server-side validation only — no client trust."""
    fields = db.scalars(select(MarketingFormField).where(MarketingFormField.form_id == form.id)).all()
    errors: list[str] = []
    normalized: dict = {}

    field_map = {f.field_key: f for f in fields}
    for field in fields:
        if not field.is_visible and field.field_type != FormFieldType.HIDDEN:
            continue
        raw = values.get(field.field_key)
        ft = field.field_type.value if hasattr(field.field_type, "value") else field.field_type
        if field.required and (raw is None or raw == ""):
            errors.append(f"required:{field.field_key}")
            continue
        if raw is None:
            continue
        if ft == "email" and isinstance(raw, str) and "@" not in raw:
            errors.append(f"invalid_email:{field.field_key}")
        elif ft == "consent" and field.required and raw is not True:
            errors.append(f"consent_required:{field.field_key}")
        normalized[field.field_key] = raw

    for key in values:
        if key not in field_map:
            errors.append(f"unknown_field:{key}")

    return normalized, errors


def _evaluate_consent(consent_payload: dict | None, form: MarketingForm) -> tuple[ConsentEvidence, bool]:
    """Unknown consent NEVER permits marketing."""
    snapshot = consent_payload or {}
    config = form.consent_config_json or {}
    marketing_eligible = False

    email_consent = snapshot.get("consent_email")
    if email_consent is True:
        marketing_eligible = True
    elif email_consent is False:
        marketing_eligible = False
    else:
        marketing_eligible = False

    if config.get("require_explicit_consent") and email_consent is not True:
        marketing_eligible = False

    evidence = ConsentEvidence(
        consent_snapshot_json=snapshot,
        marketing_eligible=marketing_eligible,
        evidence_source="form_submission",
    )
    return evidence, marketing_eligible


def _resolve_identity(db: Session, normalized: dict) -> tuple[CrmContact | None, bool]:
    email = normalized.get("email")
    if not email or not isinstance(email, str):
        return None, False
    email_lower = email.strip().lower()
    existing = db.scalar(select(CrmContact).where(CrmContact.primary_email == email_lower))
    return existing, existing is not None


def _find_duplicate_submission(
    db: Session, form_id: UUID, normalized: dict, *, exclude_submission_id: UUID | None = None
) -> MarketingFormSubmission | None:
    email = normalized.get("email")
    if not email:
        return None
    email_lower = str(email).strip().lower()
    recent = db.scalars(
        select(MarketingFormSubmission)
        .where(
            MarketingFormSubmission.form_id == form_id,
            MarketingFormSubmission.status.notin_([SubmissionStatus.FAILED, SubmissionStatus.REJECTED]),
        )
        .order_by(MarketingFormSubmission.created_at.desc())
        .limit(50)
    ).all()
    for sub in recent:
        if exclude_submission_id and sub.id == exclude_submission_id:
            continue
        if sub.normalized_values_json and str(sub.normalized_values_json.get("email", "")).strip().lower() == email_lower:
            return sub
    return None


def process_public_submission(
    db: Session,
    form_slug: str,
    payload: dict,
    *,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> MarketingFormSubmission:
    """Full submission pipeline — idempotent, no silent CRM creation."""
    form = db.scalar(select(MarketingForm).where(MarketingForm.slug == form_slug))
    if form is None:
        raise HTTPException(status_code=404, detail="Form not found")
    form_status = form.status.value if hasattr(form.status, "value") else form.status
    if form_status != "published":
        raise HTTPException(status_code=422, detail="Form is not published")

    idempotency_key = payload.get("idempotency_key")
    if idempotency_key:
        existing = db.scalar(
            select(MarketingFormSubmission).where(
                MarketingFormSubmission.form_id == form.id,
                MarketingFormSubmission.idempotency_key == idempotency_key,
            )
        )
        if existing:
            return existing

    values = payload.get("values") or {}
    tracking_data = payload.get("tracking") or {}
    consent_data = payload.get("consent") or {}

    submission = MarketingFormSubmission(
        form_id=form.id,
        landing_page_id=payload.get("landing_page_id"),
        idempotency_key=idempotency_key,
        status=SubmissionStatus.RECEIVED,
        raw_values_reference=f"inline:{hashlib.sha256(str(values).encode()).hexdigest()[:16]}",
    )
    db.add(submission)
    db.flush()

    submission.status = SubmissionStatus.VALIDATING
    normalized, errors = _validate_submission_values(db, form, values)
    if errors:
        submission.status = SubmissionStatus.FAILED
        submission.pipeline_errors_json = errors
        db.flush()
        raise HTTPException(status_code=422, detail={"message": "Validation failed", "errors": errors})

    submission.status = SubmissionStatus.NORMALIZED
    submission.normalized_values_json = normalized

    tracking = MarketingTrackingContext(
        utm_source=tracking_data.get("utm_source"),
        utm_medium=tracking_data.get("utm_medium"),
        utm_campaign=tracking_data.get("utm_campaign"),
        utm_term=tracking_data.get("utm_term"),
        utm_content=tracking_data.get("utm_content"),
        referrer=tracking_data.get("referrer"),
        landing_url=tracking_data.get("landing_url"),
        session_id=tracking_data.get("session_id"),
        campaign_id=form.campaign_id,
        source_id=form.source_id,
        ip_hash=hashlib.sha256(ip_address.encode()).hexdigest()[:16] if ip_address else None,
        user_agent_hash=hashlib.sha256(user_agent.encode()).hexdigest()[:16] if user_agent else None,
        raw_json=tracking_data,
    )
    db.add(tracking)
    db.flush()
    submission.tracking_context_id = tracking.id
    submission.status = SubmissionStatus.CONSENT_CHECKED

    evidence, marketing_eligible = _evaluate_consent(consent_data, form)
    evidence.submission_id = submission.id
    db.add(evidence)
    db.flush()
    submission.consent_evidence_id = evidence.id

    submission.status = SubmissionStatus.SPAM_CHECKED

    duplicate = _find_duplicate_submission(db, form.id, normalized, exclude_submission_id=submission.id)
    if duplicate:
        submission.status = SubmissionStatus.DUPLICATE_DETECTED
        submission.duplicate_of_submission_id = duplicate.id
        review = SubmissionReviewItem(
            submission_id=submission.id,
            review_type="duplicate",
            status=ReviewItemStatus.PENDING,
            reason=f"Duplicate of submission {duplicate.id}",
        )
        db.add(review)
        db.flush()
        record_conversion_event(db, "submission_duplicate", submission_id=submission.id, form_id=form.id)
        return submission

    contact, is_existing = _resolve_identity(db, normalized)
    submission.status = SubmissionStatus.IDENTITY_RESOLVED

    auto_create = (form.consent_config_json or {}).get("auto_create_contact", False)
    contact_created = False

    if contact is None and auto_create and marketing_eligible:
        name = normalized.get("full_name") or normalized.get("name") or normalized.get("email", "Unknown")
        phone = normalized.get("phone")
        if isinstance(phone, str):
            phone = phone.strip() or None
        contact_payload = CrmContactCreate(
            display_name=str(name),
            primary_email=str(normalized.get("email", "")).strip().lower(),
            primary_phone=phone if isinstance(phone, str) else None,
            contact_type=CrmContactType.PROSPECT,
        )
        contact = create_contact(db, contact_payload)
        contact_created = True
        submission.status = SubmissionStatus.CONTACT_CREATED

        pref = CrmCommunicationPreference(
            entity_type="contact",
            entity_id=contact.id,
            consent_email=consent_data.get("consent_email") is True,
            consent_sms=consent_data.get("consent_sms") is True,
            consent_whatsapp=consent_data.get("consent_whatsapp") is True,
            consent_phone=consent_data.get("consent_phone") is True,
            do_not_contact=consent_data.get("consent_email") is False,
        )
        db.add(pref)
        db.flush()
    elif contact is None:
        submission.status = SubmissionStatus.PENDING_REVIEW
        review = SubmissionReviewItem(
            submission_id=submission.id,
            review_type="contact_creation",
            status=ReviewItemStatus.PENDING,
            reason="No contact match and auto_create not authorized or consent insufficient",
        )
        db.add(review)
        db.flush()
        record_conversion_event(db, "submission_pending_review", submission_id=submission.id, form_id=form.id)
        return submission
    else:
        submission.contact_id = contact.id

    submission.contact_id = contact.id if contact else None

    ctx = MarketingLeadContext(
        contact_id=contact.id if contact else None,
        campaign_id=form.campaign_id,
        source_id=form.source_id,
        form_id=form.id,
        landing_page_id=payload.get("landing_page_id"),
        utm_data_json={
            "utm_source": tracking.utm_source,
            "utm_medium": tracking.utm_medium,
            "utm_campaign": tracking.utm_campaign,
        },
        consent_json=consent_data,
        marketing_status="captured" if marketing_eligible else "blocked_consent",
        verification_status="pending",
        handoff_status=MarketingLeadHandoffStatus.BLOCKED if not marketing_eligible else MarketingLeadHandoffStatus.NOT_READY,
    )
    db.add(ctx)
    db.flush()
    submission.lead_context_id = ctx.id
    submission.status = SubmissionStatus.LEAD_CONTEXT_CREATED

    if contact:
        consent = get_consent_status(db, contact.id, None)
        if consent.get("email") == "granted" and not ctx.suppression_json:
            ctx.handoff_status = MarketingLeadHandoffStatus.NOT_READY

    apply_routing_rules(db, ctx, submission)
    submission.status = SubmissionStatus.ROUTED

    record_conversion_event(
        db,
        "form_submission",
        submission_id=submission.id,
        lead_context_id=ctx.id,
        form_id=form.id,
        landing_page_id=payload.get("landing_page_id"),
        tracking_context_id=tracking.id,
        value_json={"contact_created": contact_created, "marketing_eligible": marketing_eligible},
    )
    db.flush()
    return submission


def review_submission(db: Session, submission_id: UUID, action: str, reason: str | None, user: User) -> MarketingFormSubmission:
    submission = _get_submission_or_404(db, submission_id)
    review = db.scalar(
        select(SubmissionReviewItem).where(
            SubmissionReviewItem.submission_id == submission_id,
            SubmissionReviewItem.status == ReviewItemStatus.PENDING,
        )
    )
    if not review:
        raise HTTPException(status_code=404, detail="No pending review item")

    if action == "approve":
        review.status = ReviewItemStatus.APPROVED
        review.reviewed_by_user_id = user.id
        config = db.get(MarketingForm, submission.form_id)
        if review.review_type == "contact_creation" and submission.normalized_values_json:
            auto_create = (config.consent_config_json or {}).get("auto_create_contact", False) if config else False
            evidence = db.get(ConsentEvidence, submission.consent_evidence_id) if submission.consent_evidence_id else None
            if not auto_create or not (evidence and evidence.marketing_eligible):
                raise HTTPException(status_code=422, detail="Authorized contact creation requires consent and config")
            normalized = submission.normalized_values_json
            name = normalized.get("full_name") or normalized.get("name") or normalized.get("email", "Unknown")
            contact_payload = CrmContactCreate(
                display_name=str(name),
                primary_email=str(normalized.get("email", "")).strip().lower(),
                contact_type=CrmContactType.PROSPECT,
            )
            contact = create_contact(db, contact_payload)
            submission.contact_id = contact.id
            submission.status = SubmissionStatus.CONTACT_CREATED
            ctx = MarketingLeadContext(
                contact_id=contact.id,
                form_id=submission.form_id,
                landing_page_id=submission.landing_page_id,
                handoff_status=MarketingLeadHandoffStatus.NOT_READY,
            )
            db.add(ctx)
            db.flush()
            submission.lead_context_id = ctx.id
            submission.status = SubmissionStatus.LEAD_CONTEXT_CREATED
    else:
        review.status = ReviewItemStatus.REJECTED
        review.reviewed_by_user_id = user.id
        submission.status = SubmissionStatus.REJECTED
        if reason:
            review.reason = reason

    db.flush()
    return submission


def list_review_queue(db: Session, page: int = 1, page_size: int = 25) -> tuple[list[SubmissionReviewItem], int]:
    query = select(SubmissionReviewItem).where(SubmissionReviewItem.status == ReviewItemStatus.PENDING)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(SubmissionReviewItem.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total
