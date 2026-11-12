"""One definition of which projects a person belongs to.

Membership is the union of canonical links. It is not `Lead.project_id` alone.
Sources:
- CRM agreement (purchase) contact and participants
- converted lead linked to the project
- active inventory ownership through the contact's investor party
- project funding commitments through the contact's investor party

Funding commitments are project-level. A phase filter does not invent a phase
for them. Cancelled commitments are excluded, matching the finance totals that
treat every other FundingCommitment status as a live project relationship.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.inventory import InventoryAsset, ProjectPhase
from investhome_api.models.inventory_workflows import InventoryOwnership, OwnershipRecordStatus
from investhome_api.models.lead import Lead
from investhome_api.models.project import Project, ProjectStatus
from investhome_api.services.crm.bitrix_project_aliases import (
    BITRIX_PROJECT_GROUP_LABELS,
    BitrixProjectGroup,
    load_project_ids_by_name,
    resolve_project_alias,
)
from investhome_api.services.crm.unit_change import detached_relationship_clause


def person_project_contact_ids(
    db: Session,
    *,
    project_id: UUID | None = None,
    project_group: str | None = None,
    phase_id: UUID | None = None,
    include_leads: bool = True,
) -> list[UUID]:
    """Contact ids related to one project, optionally one phase.

    A phase filter keeps people linked to that phase. Addition-only customers
    do not match Historic. Clearing the project returns no restriction; the
    caller skips this function when no project is selected.
    """
    resolved_id = project_id
    group_value = (project_group or "").strip() or None
    if group_value:
        resolved = resolve_project_alias(group_value, project_ids_by_name=load_project_ids_by_name(db))
        if resolved.group is not None:
            group_value = resolved.group.value
        if resolved_id is None:
            resolved_id = resolved.project_id
    if resolved_id is None and group_value is None:
        return []

    ids: set[UUID] = set()
    agreement_filters = [~detached_relationship_clause()]
    if resolved_id is not None and group_value is not None:
        agreement_filters.append(
            or_(CrmAgreement.project_id == resolved_id, CrmAgreement.project_group == group_value)
        )
    elif resolved_id is not None:
        agreement_filters.append(CrmAgreement.project_id == resolved_id)
    else:
        agreement_filters.append(CrmAgreement.project_group == group_value)
    if phase_id is not None:
        agreement_filters.append(CrmAgreement.phase_id == phase_id)
    ids.update(db.scalars(select(CrmAgreement.contact_id).where(*agreement_filters)).all())
    participant_ids = db.scalars(
        select(CrmAgreementParticipant.contact_id)
        .join(CrmAgreement, CrmAgreement.id == CrmAgreementParticipant.agreement_id)
        .where(*agreement_filters)
    ).all()
    ids.update(participant_ids)

    if include_leads and resolved_id is not None:
        lead_filters = [
            Lead.project_id == resolved_id,
            Lead.converted_contact_id.is_not(None),
            Lead.archived_at.is_(None),
        ]
        if phase_id is not None:
            lead_filters.append(Lead.phase_id == phase_id)
        ids.update(db.scalars(select(Lead.converted_contact_id).where(*lead_filters)).all())

    if resolved_id is not None:
        ownership_filters = [
            InventoryAsset.project_id == resolved_id,
            InventoryOwnership.status == OwnershipRecordStatus.ACTIVE,
            CrmContact.investor_id.is_not(None),
        ]
        if phase_id is not None:
            ownership_filters.append(InventoryAsset.phase_id == phase_id)
        owner_ids = db.scalars(
            select(CrmContact.id)
            .join(InventoryOwnership, InventoryOwnership.party_id == CrmContact.investor_id)
            .join(InventoryAsset, InventoryAsset.id == InventoryOwnership.inventory_asset_id)
            .where(*ownership_filters)
        ).all()
        ids.update(owner_ids)
        if phase_id is None:
            from investhome_api.models.finance import CommitmentStatus, FundingCommitment
            from investhome_api.services.operational_child_scope import operational_child_clause

            funding_ids = db.scalars(
                select(CrmContact.id)
                .join(FundingCommitment, FundingCommitment.investor_id == CrmContact.investor_id)
                .where(
                    FundingCommitment.project_id == resolved_id,
                    FundingCommitment.status != CommitmentStatus.CANCELLED,
                    CrmContact.investor_id.is_not(None),
                    operational_child_clause(FundingCommitment.is_demo, FundingCommitment.project_id),
                )
            ).all()
            ids.update(funding_ids)
    return sorted((item for item in ids if item is not None), key=str)


def list_membership_projects(db: Session) -> list[dict[str, object]]:
    """Canonical project ids for the CRM project filter, with their phases."""
    names = load_project_ids_by_name(db)
    projects = {row.id: row for row in db.scalars(select(Project)).all()}
    phases = db.scalars(select(ProjectPhase).order_by(ProjectPhase.display_order, ProjectPhase.name)).all()
    by_project: dict[UUID, list[dict[str, object]]] = {}
    for phase in phases:
        by_project.setdefault(phase.project_id, []).append(
            {
                "id": str(phase.id),
                "name": phase.name,
                "display_order": phase.display_order,
                "active": phase.active,
            }
        )
    options: list[dict[str, object]] = []
    seen: set[str] = set()
    for group in BitrixProjectGroup:
        resolved = resolve_project_alias(group.value, project_ids_by_name=names)
        project = projects.get(resolved.project_id) if resolved.project_id else None
        if project is not None and project.project_status == ProjectStatus.CANCELLED:
            continue
        key = str(resolved.project_id) if resolved.project_id else group.value
        seen.add(key)
        options.append(
            {
                "project_id": str(resolved.project_id) if resolved.project_id else None,
                "project_group": group.value,
                "label": BITRIX_PROJECT_GROUP_LABELS[group],
                "uses_phases": bool(getattr(project, "uses_phases", False)),
                "currency": getattr(project, "currency", None) if project is not None else None,
                "phases": by_project.get(resolved.project_id, []) if resolved.project_id else [],
            }
        )
    for project in projects.values():
        if project.project_status == ProjectStatus.CANCELLED or str(project.id) in seen:
            continue
        options.append(
            {
                "project_id": str(project.id),
                "project_group": None,
                "label": project.project_name,
                "uses_phases": bool(project.uses_phases),
                "currency": project.currency,
                "phases": by_project.get(project.id, []),
            }
        )
    return options
