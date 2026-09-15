"""Bitrix import dry-run API. Zero database writes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_bitrix import BitrixDryRunRequest, BitrixDryRunResponse
from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow, classify_bitrix_filename, run_bitrix_dry_run

router = APIRouter(prefix="/crm/bitrix", tags=["crm-bitrix"])


@router.post("/dry-run", response_model=BitrixDryRunResponse)
def post_bitrix_dry_run(
    body: BitrixDryRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("crm", "read")),
) -> BitrixDryRunResponse:
    del user
    bundle = BitrixBundle()
    for item in body.rows:
        role = item.role
        hint = item.project_hint
        if role is None:
            role, classified_hint = classify_bitrix_filename(item.source_file)
            hint = hint or classified_hint
        bundle.rows.append(
            BitrixSourceRow(
                source_file=item.source_file,
                role=role,
                bitrix_id=item.bitrix_id,
                full_name=item.full_name,
                phone=item.phone,
                email=item.email,
                comment=item.comment,
                project_hint=hint,
                agreement_date=item.agreement_date,
                extra=item.extra,
                parse_error=item.parse_error,
            )
        )
    report = run_bitrix_dry_run(bundle, db=db if body.read_db else None)
    payload = report.to_dict()
    return BitrixDryRunResponse(console=report.format_console(), **payload)
