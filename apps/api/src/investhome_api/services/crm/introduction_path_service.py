"""Introduction path finding — BFS/Dijkstra on relationship graph (backend only)."""

from __future__ import annotations

import heapq
from collections import deque
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.crm_relationship import CrmRelationship
from investhome_api.schemas.crm_relationships import (
    CrmGraphEdge,
    CrmGraphNode,
    CrmIntroductionPath,
    CrmIntroductionPathStep,
    CrmIntroductionPathsResponse,
    CrmRelationshipEntityTypeEnum,
    CrmRelationshipStrengthEnum,
)
from investhome_api.services.crm.relationship_graph_service import (
    _add_edge,
    _add_node,
    _node_id,
    _relationships_for_entity,
    _resolve_entity_label,
)

MAX_PATHS = 5
MAX_HOPS = 6

STRENGTH_SCORES = {
    "weak": 1,
    "moderate": 2,
    "strong": 3,
    "strategic": 4,
}


def _build_adjacency(
    db: Session,
    start_type: str,
    start_id: UUID,
    *,
    include_confidential: bool,
    max_hops: int,
) -> tuple[dict[str, list[tuple[str, CrmRelationship]]], dict[str, CrmGraphNode], dict[str, CrmGraphEdge]]:
    nodes: dict[str, CrmGraphNode] = {}
    edges: dict[str, CrmGraphEdge] = {}
    adjacency: dict[str, list[tuple[str, CrmRelationship]]] = {}

    queue: deque[tuple[str, UUID, int]] = deque([(start_type, start_id, 0)])
    visited: set[str] = set()

    while queue:
        et, eid, depth = queue.popleft()
        nid = _node_id(et, eid)
        if nid in visited:
            continue
        visited.add(nid)
        _add_node(nodes, db, et, eid)
        if depth >= max_hops:
            continue
        for rel in _relationships_for_entity(
            db, et, eid,
            include_confidential=include_confidential,
            include_archived=False,
        ):
            _add_edge(edges, rel)
            if rel.source_entity_type.value == et and rel.source_entity_id == eid:
                n_et, n_eid = rel.target_entity_type.value, rel.target_entity_id
            else:
                n_et, n_eid = rel.source_entity_type.value, rel.source_entity_id
            neighbor = _node_id(n_et, n_eid)
            adjacency.setdefault(nid, []).append((neighbor, rel))
            _add_node(nodes, db, n_et, n_eid)
            queue.append((n_et, n_eid, depth + 1))

    return adjacency, nodes, edges


def _path_from_trace(
    trace: list[tuple[str, CrmRelationship | None]],
    nodes: dict[str, CrmGraphNode],
    edges: dict[str, CrmGraphEdge],
    strategy: str,
) -> CrmIntroductionPath:
    steps: list[CrmIntroductionPathStep] = []
    total_score = 0
    for i, (node_id, rel) in enumerate(trace):
        edge = None
        explanation = None
        if rel:
            edge = edges.get(str(rel.id))
            total_score += rel.relationship_score
            explanation = (
                f"Connection via {rel.relationship_type} "
                f"(score {rel.relationship_score}, strength {rel.strength.value})"
            )
        steps.append(
            CrmIntroductionPathStep(
                node=nodes[node_id],
                edge=edge,
                explanation=explanation if i > 0 else "Starting point",
            )
        )
    return CrmIntroductionPath(
        steps=steps,
        total_score=total_score,
        total_hops=max(0, len(steps) - 1),
        strategy=strategy,
    )


def find_shortest_path(
    db: Session,
    *,
    source_entity_type: str,
    source_entity_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
    include_confidential: bool = False,
) -> CrmIntroductionPath | None:
    start = _node_id(source_entity_type, source_entity_id)
    goal = _node_id(target_entity_type, target_entity_id)
    if start == goal:
        return None

    adjacency, nodes, edges = _build_adjacency(
        db, source_entity_type, source_entity_id,
        include_confidential=include_confidential,
        max_hops=MAX_HOPS,
    )
    if goal not in nodes and goal != start:
        # BFS may not have reached target; try direct expansion from goal side
        adjacency2, nodes2, edges2 = _build_adjacency(
            db, target_entity_type, target_entity_id,
            include_confidential=include_confidential,
            max_hops=MAX_HOPS,
        )
        nodes.update(nodes2)
        edges.update(edges2)
        for k, v in adjacency2.items():
            adjacency.setdefault(k, []).extend(v)

    queue: deque[tuple[str, list[tuple[str, CrmRelationship | None]]]] = deque([(start, [(start, None)])])
    visited: set[str] = {start}

    while queue:
        current, trace = queue.popleft()
        if current == goal:
            return _path_from_trace(trace, nodes, edges, "shortest")
        for neighbor, rel in adjacency.get(current, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            queue.append((neighbor, trace + [(neighbor, rel)]))
    return None


def find_strongest_path(
    db: Session,
    *,
    source_entity_type: str,
    source_entity_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
    include_confidential: bool = False,
) -> CrmIntroductionPath | None:
    start = _node_id(source_entity_type, source_entity_id)
    goal = _node_id(target_entity_type, target_entity_id)

    adjacency, nodes, edges = _build_adjacency(
        db, source_entity_type, source_entity_id,
        include_confidential=include_confidential,
        max_hops=MAX_HOPS,
    )

    # Dijkstra maximizing score: use negative weight
    heap: list[tuple[float, str, list[tuple[str, CrmRelationship | None]]]] = [(0.0, start, [(start, None)])]
    best: dict[str, float] = {start: 0.0}

    while heap:
        neg_score, current, trace = heapq.heappop(heap)
        score = -neg_score
        if current == goal:
            return _path_from_trace(trace, nodes, edges, "strongest")
        if score > best.get(current, float("inf")):
            continue
        for neighbor, rel in adjacency.get(current, []):
            edge_score = rel.relationship_score + STRENGTH_SCORES.get(rel.strength.value, 1) * 10
            new_score = score + edge_score
            if new_score < best.get(neighbor, float("inf")):
                continue
            best[neighbor] = new_score
            heapq.heappush(heap, (-new_score, neighbor, trace + [(neighbor, rel)]))
    return None


def find_highest_influence_path(
    db: Session,
    *,
    source_entity_type: str,
    source_entity_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
    include_confidential: bool = False,
) -> CrmIntroductionPath | None:
    start = _node_id(source_entity_type, source_entity_id)
    goal = _node_id(target_entity_type, target_entity_id)

    adjacency, nodes, edges = _build_adjacency(
        db, source_entity_type, source_entity_id,
        include_confidential=include_confidential,
        max_hops=MAX_HOPS,
    )

    heap: list[tuple[float, str, list[tuple[str, CrmRelationship | None]]]] = [(0.0, start, [(start, None)])]
    best: dict[str, float] = {start: 0.0}

    while heap:
        neg_score, current, trace = heapq.heappop(heap)
        score = -neg_score
        if current == goal:
            return _path_from_trace(trace, nodes, edges, "highest_influence")
        if score > best.get(current, float("inf")):
            continue
        for neighbor, rel in adjacency.get(current, []):
            edge_score = rel.influence_score
            new_score = score + edge_score
            if new_score < best.get(neighbor, float("inf")):
                continue
            best[neighbor] = new_score
            heapq.heappush(heap, (-new_score, neighbor, trace + [(neighbor, rel)]))
    return None


def find_introduction_paths(
    db: Session,
    *,
    source_entity_type: str,
    source_entity_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
    strategy: str = "shortest",
    include_confidential: bool = False,
) -> CrmIntroductionPathsResponse:
    paths: list[CrmIntroductionPath] = []
    if strategy in ("shortest", "all"):
        p = find_shortest_path(
            db,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            include_confidential=include_confidential,
        )
        if p:
            paths.append(p)
    if strategy in ("strongest", "all"):
        p = find_strongest_path(
            db,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            include_confidential=include_confidential,
        )
        if p and not any(x.total_hops == p.total_hops and x.strategy == p.strategy for x in paths):
            paths.append(p)
    if strategy in ("highest_influence", "all"):
        p = find_highest_influence_path(
            db,
            source_entity_type=source_entity_type,
            source_entity_id=source_entity_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            include_confidential=include_confidential,
        )
        if p and not any(x.total_hops == p.total_hops and x.strategy == p.strategy for x in paths):
            paths.append(p)

    return CrmIntroductionPathsResponse(
        paths=paths[:MAX_PATHS],
        source_entity_type=CrmRelationshipEntityTypeEnum(source_entity_type),
        source_entity_id=source_entity_id,
        target_entity_type=CrmRelationshipEntityTypeEnum(target_entity_type),
        target_entity_id=target_entity_id,
    )
