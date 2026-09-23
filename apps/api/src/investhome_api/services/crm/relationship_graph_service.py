"""Server-side relationship graph queries with depth/limit controls."""

from __future__ import annotations

from collections import deque
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_company import CrmCompany
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.project import Project
from investhome_api.models.crm_relationship import (
    CrmRelationship,
    CrmRelationshipEntityType,
    CrmRelationshipStatus,
)
from investhome_api.schemas.crm_relationships import (
    CrmGraphEdge,
    CrmGraphNode,
    CrmRelationshipEntityTypeEnum,
    CrmRelationshipGraphResponse,
    CrmRelationshipStrengthEnum,
)
from investhome_api.services.crm.relationship_service import _pair_kind_clause, relationship_pair_kind

DEFAULT_GRAPH_DEPTH = 2
DEFAULT_GRAPH_LIMIT = 200
MAX_GRAPH_DEPTH = 5
MAX_GRAPH_LIMIT = 200

HIERARCHY_TYPES = frozenset({"parent", "subsidiary"})


def _node_id(entity_type: str, entity_id: UUID) -> str:
    return f"{entity_type}:{entity_id}"


def _parse_node_id(node_id: str) -> tuple[str, UUID]:
    entity_type, raw_id = node_id.split(":", 1)
    return entity_type, UUID(raw_id)


def _resolve_entity_label(
    db: Session,
    entity_type: CrmRelationshipEntityType,
    entity_id: UUID,
) -> str:
    if entity_type == CrmRelationshipEntityType.CONTACT:
        contact = db.get(CrmContact, entity_id)
        return contact.display_name if contact else str(entity_id)[:8]
    if entity_type == CrmRelationshipEntityType.COMPANY:
        company = db.get(CrmCompany, entity_id)
        return company.display_name if company else str(entity_id)[:8]
    if entity_type == CrmRelationshipEntityType.PROJECT:
        project = db.get(Project, entity_id)
        return project.project_name if project else str(entity_id)[:8]
    return f"{entity_type.value}:{str(entity_id)[:8]}"


def _entity_score(db: Session, entity_type: CrmRelationshipEntityType, entity_id: UUID) -> int:
    if entity_type == CrmRelationshipEntityType.CONTACT:
        contact = db.get(CrmContact, entity_id)
        return contact.relationship_score if contact else 0
    if entity_type == CrmRelationshipEntityType.COMPANY:
        company = db.get(CrmCompany, entity_id)
        return company.relationship_score if company else 0
    return 0


def _base_relationship_query(
    db: Session,
    *,
    include_confidential: bool,
    include_archived: bool,
):
    query = select(CrmRelationship)
    if not include_archived:
        query = query.where(
            CrmRelationship.archived_at.is_(None),
            CrmRelationship.status != CrmRelationshipStatus.ARCHIVED,
        )
    if not include_confidential:
        query = query.where(CrmRelationship.is_confidential.is_(False))
    return query


def _relationships_for_entity(
    db: Session,
    entity_type: str,
    entity_id: UUID,
    *,
    include_confidential: bool,
    include_archived: bool,
) -> list[CrmRelationship]:
    et = CrmRelationshipEntityType(entity_type)
    query = _base_relationship_query(
        db,
        include_confidential=include_confidential,
        include_archived=include_archived,
    ).where(
        or_(
            (CrmRelationship.source_entity_type == et) & (CrmRelationship.source_entity_id == entity_id),
            (CrmRelationship.target_entity_type == et) & (CrmRelationship.target_entity_id == entity_id),
        )
    )
    return list(db.scalars(query).all())


def _add_edge(
    edges: dict[str, CrmGraphEdge],
    rel: CrmRelationship,
    *,
    perspective_entity: tuple[str, UUID] | None = None,
) -> None:
    source_node = _node_id(rel.source_entity_type.value, rel.source_entity_id)
    target_node = _node_id(rel.target_entity_type.value, rel.target_entity_id)
    edge_id = str(rel.id)
    if edge_id in edges:
        return
    edges[edge_id] = CrmGraphEdge(
        id=edge_id,
        source=source_node,
        target=target_node,
        relationship_id=rel.id,
        relationship_type=rel.relationship_type,
        reciprocal_type=rel.reciprocal_type,
        strength=CrmRelationshipStrengthEnum(rel.strength.value),
        relationship_score=rel.relationship_score,
        is_confidential=rel.is_confidential,
    )


def _add_node(
    nodes: dict[str, CrmGraphNode],
    db: Session,
    entity_type: str,
    entity_id: UUID,
    *,
    is_center: bool = False,
) -> None:
    nid = _node_id(entity_type, entity_id)
    if nid in nodes:
        if is_center:
            nodes[nid].is_center = True
        return
    et = CrmRelationshipEntityType(entity_type)
    nodes[nid] = CrmGraphNode(
        id=nid,
        entity_type=CrmRelationshipEntityTypeEnum(entity_type),
        entity_id=entity_id,
        label=_resolve_entity_label(db, et, entity_id),
        score=_entity_score(db, et, entity_id),
        is_center=is_center,
    )


def _project_ids_for_group(db: Session, project_group: str) -> list[UUID]:
    return list(
        db.scalars(
            select(CrmAgreement.project_id).where(
                CrmAgreement.project_group == project_group,
                CrmAgreement.project_id.is_not(None),
            ).distinct()
        ).all()
    )


def get_relationship_graph(
    db: Session,
    *,
    center_entity_type: str | None = None,
    center_entity_id: UUID | None = None,
    depth: int = DEFAULT_GRAPH_DEPTH,
    limit: int = DEFAULT_GRAPH_LIMIT,
    include_confidential: bool = False,
    include_archived: bool = False,
    category: str | None = None,
    relationship_type: str | None = None,
    project_group: str | None = None,
    pair_kind: str | None = None,
) -> CrmRelationshipGraphResponse:
    depth = max(1, min(depth, MAX_GRAPH_DEPTH))
    limit = max(1, min(limit, MAX_GRAPH_LIMIT))

    nodes: dict[str, CrmGraphNode] = {}
    edges: dict[str, CrmGraphEdge] = {}
    truncated = False
    warning: str | None = None
    project_ids = set(_project_ids_for_group(db, project_group)) if project_group else None

    def _matches_project(rel: CrmRelationship) -> bool:
        if project_ids is None:
            return True
        return (
            rel.source_entity_type == CrmRelationshipEntityType.PROJECT
            and rel.source_entity_id in project_ids
        ) or (
            rel.target_entity_type == CrmRelationshipEntityType.PROJECT
            and rel.target_entity_id in project_ids
        )

    if center_entity_type and center_entity_id:
        queue: deque[tuple[str, UUID, int]] = deque([(center_entity_type, center_entity_id, 0)])
        visited: set[str] = set()
        while queue and len(edges) < limit:
            et, eid, current_depth = queue.popleft()
            nid = _node_id(et, eid)
            if nid in visited:
                continue
            visited.add(nid)
            _add_node(nodes, db, et, eid, is_center=(current_depth == 0))
            if current_depth >= depth:
                continue
            for rel in _relationships_for_entity(
                db, et, eid,
                include_confidential=include_confidential,
                include_archived=include_archived,
            ):
                if category and rel.category.value != category:
                    continue
                if relationship_type and rel.relationship_type != relationship_type:
                    continue
                if not _matches_project(rel):
                    continue
                if pair_kind and relationship_pair_kind(rel) != pair_kind:
                    continue
                if len(edges) >= limit:
                    truncated = True
                    break
                _add_edge(edges, rel)
                neighbor = (
                    rel.target_entity_type.value,
                    rel.target_entity_id,
                ) if rel.source_entity_id == eid and rel.source_entity_type.value == et else (
                    rel.source_entity_type.value,
                    rel.source_entity_id,
                )
                _add_node(nodes, db, neighbor[0], neighbor[1])
                queue.append((neighbor[0], neighbor[1], current_depth + 1))
        if truncated:
            warning = f"Graph truncated at {limit} edges. Increase limit or reduce depth to see more."
    else:
        query = _base_relationship_query(
            db,
            include_confidential=include_confidential,
            include_archived=include_archived,
        )
        if category:
            from investhome_api.models.crm_relationship import CrmRelationshipCategory
            query = query.where(CrmRelationship.category == CrmRelationshipCategory(category))
        if relationship_type:
            query = query.where(CrmRelationship.relationship_type == relationship_type)
        if project_ids is not None:
            query = query.where(
                or_(
                    (CrmRelationship.source_entity_type == CrmRelationshipEntityType.PROJECT)
                    & CrmRelationship.source_entity_id.in_(project_ids),
                    (CrmRelationship.target_entity_type == CrmRelationshipEntityType.PROJECT)
                    & CrmRelationship.target_entity_id.in_(project_ids),
                )
            )
        pair_clause = _pair_kind_clause(pair_kind) if pair_kind else None
        if pair_clause is not None:
            query = query.where(pair_clause)
        query = query.order_by(CrmRelationship.updated_at.desc()).limit(limit)
        rels = list(db.scalars(query).all())
        if len(rels) >= limit:
            truncated = True
            warning = "Showing matching relationships only. Search or filter to focus the graph."
        for rel in rels:
            _add_edge(edges, rel)
            _add_node(nodes, db, rel.source_entity_type.value, rel.source_entity_id)
            _add_node(nodes, db, rel.target_entity_type.value, rel.target_entity_id)

    return CrmRelationshipGraphResponse(
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        truncated=truncated,
        warning=warning,
        depth=depth,
        limit=limit,
    )


def expand_node(
    db: Session,
    *,
    node_id: str,
    depth: int = 1,
    limit: int = DEFAULT_GRAPH_LIMIT,
    include_confidential: bool = False,
    include_archived: bool = False,
) -> CrmRelationshipGraphResponse:
    entity_type, entity_id = _parse_node_id(node_id)
    return get_relationship_graph(
        db,
        center_entity_type=entity_type,
        center_entity_id=entity_id,
        depth=depth,
        limit=limit,
        include_confidential=include_confidential,
        include_archived=include_archived,
    )
