"""Project Assistant orchestration — permission scope → hybrid search → grounded LLM."""

from __future__ import annotations

import time
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_assistant import (
    ProjectAssistantAssetRef,
    ProjectAssistantCitation,
    ProjectAssistantDocumentRef,
    ProjectAssistantRequest,
    ProjectAssistantResponse,
)
from investhome_api.services.activity_service import ActivityRequestContext, log_activity
from investhome_api.services.ai_search.hybrid_search import ProjectScopeError, hybrid_search
from investhome_api.services.project_assistant.conversation import (
    append_turn,
    get_history,
    get_or_create_conversation,
)
from investhome_api.services.project_assistant.grounding import evaluate_grounding
from investhome_api.services.project_assistant.llm_provider import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    get_llm_provider,
)
from investhome_api.services.project_assistant.prompt_builder import build_rag_prompt

DEFAULT_RETRIEVAL_LIMIT = 8


def _ensure_projects_accessible(db: Session, project_ids: list[UUID]) -> None:
    """Only allow questions against existing (non-archived) projects."""
    missing: list[str] = []
    for pid in project_ids:
        project = db.get(Project, pid)
        if project is None or project.archived_at is not None:
            missing.append(str(pid))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found or inaccessible: {', '.join(missing)}",
        )


def _resolve_scope(body: ProjectAssistantRequest) -> tuple[str, UUID | None, list[UUID] | None]:
    scope = (body.project_scope or "single").strip().lower()
    return scope, body.project_id, list(body.project_ids) if body.project_ids else None


def _citations_from_evidence(evidence: list[dict]) -> list[ProjectAssistantCitation]:
    out: list[ProjectAssistantCitation] = []
    for row in evidence:
        out.append(
            ProjectAssistantCitation(
                asset_id=UUID(row["asset_id"]) if row.get("asset_id") else None,
                document_id=UUID(row["document_id"]),
                document_name=str(row.get("document_name") or "untitled"),
                chunk_id=UUID(row["chunk_id"]),
                chunk_reference=str(row.get("chunk_reference") or f"chunk:{row.get('chunk_order', 0)}"),
                chunk_order=int(row.get("chunk_order") or 0),
                project_id=UUID(row["project_id"]),
                score=float(row.get("score") or 0.0),
                excerpt=str(row.get("text") or "")[:280] or None,
            )
        )
    return out


def _asset_docs(
    evidence: list[dict],
) -> tuple[list[ProjectAssistantAssetRef], list[ProjectAssistantDocumentRef], list[UUID]]:
    assets: dict[UUID, ProjectAssistantAssetRef] = {}
    documents: dict[UUID, ProjectAssistantDocumentRef] = {}
    projects: set[UUID] = set()
    for row in evidence:
        pid = UUID(row["project_id"])
        projects.add(pid)
        doc_id = UUID(row["document_id"])
        if doc_id not in documents:
            documents[doc_id] = ProjectAssistantDocumentRef(
                document_id=doc_id,
                document_name=str(row.get("document_name") or "untitled"),
                project_id=pid,
                asset_id=UUID(row["asset_id"]) if row.get("asset_id") else None,
            )
        if row.get("asset_id"):
            aid = UUID(row["asset_id"])
            if aid not in assets:
                assets[aid] = ProjectAssistantAssetRef(
                    asset_id=aid,
                    document_name=str(row.get("document_name") or "untitled"),
                    project_id=pid,
                )
    return list(assets.values()), list(documents.values()), sorted(projects, key=str)


def _audit(
    db: Session,
    user: User,
    *,
    entity_id: UUID,
    metadata: dict,
) -> None:
    # Never log secrets / API keys / raw prompts with credentials
    safe = {
        k: v
        for k, v in metadata.items()
        if k
        not in {
            "api_key",
            "authorization",
            "prompt",
            "system",
            "user_prompt",
            "raw",
        }
    }
    log_activity(
        db,
        action=ActivityAction.VIEWED,
        entity_type=ActivityEntityType.PROJECT_AI,
        entity_id=entity_id,
        description_key="ai.project_assistant.asked",
        actor_user=user,
        source=ActivitySource.AI_SERVICE,
        metadata=safe,
        request_context=ActivityRequestContext(source=ActivitySource.AI_SERVICE),
    )


def ask_project_assistant(
    db: Session,
    user: User,
    body: ProjectAssistantRequest,
) -> ProjectAssistantResponse:
    """
    Full RAG flow:
    Question → Permission (caller) → Project Scope → Hybrid Search →
    Top Chunks → Prompt Builder → LLM → Structured Answer → Citations → Confidence
    """
    started = time.perf_counter()
    settings = get_settings()
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="question is required",
        )

    scope, project_id, project_ids = _resolve_scope(body)

    # Validate accessible projects (existence) for single/multi
    if scope == "single":
        if project_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id is required when project_scope=single",
            )
        _ensure_projects_accessible(db, [project_id])
    elif scope == "multi":
        ids = list(project_ids or [])
        if project_id is not None and project_id not in ids:
            ids.append(project_id)
        if not ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_ids is required when project_scope=multi",
            )
        _ensure_projects_accessible(db, ids)
        project_ids = ids
    elif scope == "global":
        # Explicit opt-in only — still permission-gated at the route
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid project_scope: {scope}",
        )

    conversation = get_or_create_conversation(body.conversation_id)
    history = get_history(conversation.id)

    # Follow-up: lightly expand query with prior question context for retrieval
    search_query = question
    if history:
        prior_q = history[-1].get("question") or ""
        if prior_q and len(question.split()) <= 8:
            search_query = f"{prior_q} {question}".strip()

    retrieval_limit = min(
        max(1, int(getattr(settings, "ai_assistant_retrieval_limit", DEFAULT_RETRIEVAL_LIMIT) or DEFAULT_RETRIEVAL_LIMIT)),
        20,
    )
    min_score = float(getattr(settings, "ai_assistant_min_score", 0.12) or 0.12)

    search_started = time.perf_counter()
    try:
        hits = hybrid_search(
            db,
            query=search_query,
            project_scope=scope,
            project_id=project_id,
            project_ids=project_ids,
            limit=retrieval_limit,
        )
    except ProjectScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    search_time_ms = int((time.perf_counter() - search_started) * 1000)

    grounding = evaluate_grounding(hits, min_score=min_score)
    provider = get_llm_provider(settings)
    event_id = uuid4()

    if not grounding.sufficient:
        answer = grounding.message or INSUFFICIENT_EVIDENCE_MESSAGE
        latency_ms = int((time.perf_counter() - started) * 1000)
        append_turn(conversation.id, question=question, answer=answer)
        _audit(
            db,
            user,
            entity_id=event_id,
            metadata={
                "question": question[:500],
                "project_scope": scope,
                "project_id": str(project_id) if project_id else None,
                "project_ids": [str(p) for p in (project_ids or [])] or None,
                "conversation_id": str(conversation.id),
                "provider": provider.name,
                "model": provider.model,
                "latency_ms": latency_ms,
                "search_time_ms": search_time_ms,
                "hit_count": 0,
                "asset_ids": [],
                "chunk_ids": [],
                "confidence": grounding.confidence,
                "grounded": False,
            },
        )
        return ProjectAssistantResponse(
            answer=answer,
            confidence=grounding.confidence,
            citations=[],
            assets=[],
            documents=[],
            projects=[project_id] if project_id else (project_ids or []),
            search_time_ms=search_time_ms,
            latency_ms=latency_ms,
            conversation_id=conversation.id,
            provider=provider.name,
            model=provider.model,
            grounded=False,
        )

    max_prompt_chars = int(
        getattr(settings, "ai_assistant_max_prompt_chars", 12_000) or 12_000
    )
    prompt = build_rag_prompt(
        question=question,
        project_scope=scope,
        project_id=project_id,
        project_ids=project_ids,
        hits=hits,
        history=history,
        max_prompt_chars=max_prompt_chars,
        max_chunks=retrieval_limit,
    )

    try:
        llm = provider.generate(system=prompt.system, user=prompt.user)
        answer = (llm.answer or "").strip() or INSUFFICIENT_EVIDENCE_MESSAGE
        # Safety: if model ignored instructions and answered without evidence cues, keep message
        if answer and prompt.chunk_count == 0:
            answer = INSUFFICIENT_EVIDENCE_MESSAGE
            confidence = 0.0
            grounded = False
            evidence: list[dict] = []
        else:
            confidence = grounding.confidence
            grounded = True
            evidence = prompt.evidence_payload
            # If model returns the insufficient template, treat as ungrounded
            if answer.strip() == INSUFFICIENT_EVIDENCE_MESSAGE:
                grounded = False
                confidence = min(confidence, 0.2)
                evidence = []
    except Exception:
        answer = INSUFFICIENT_EVIDENCE_MESSAGE
        confidence = 0.0
        grounded = False
        evidence = []
        llm = None

    citations = _citations_from_evidence(evidence) if grounded else []
    assets, documents, projects = _asset_docs(evidence) if grounded else ([], [], [])
    if not projects:
        if project_id:
            projects = [project_id]
        elif project_ids:
            projects = list(project_ids)

    latency_ms = int((time.perf_counter() - started) * 1000)
    append_turn(conversation.id, question=question, answer=answer)

    _audit(
        db,
        user,
        entity_id=event_id,
        metadata={
            "question": question[:500],
            "project_scope": scope,
            "project_id": str(project_id) if project_id else None,
            "project_ids": [str(p) for p in (project_ids or [])] or None,
            "conversation_id": str(conversation.id),
            "provider": getattr(llm, "provider", provider.name) if llm else provider.name,
            "model": getattr(llm, "model", provider.model) if llm else provider.model,
            "latency_ms": latency_ms,
            "search_time_ms": search_time_ms,
            "hit_count": len(hits),
            "asset_ids": [str(a.asset_id) for a in assets],
            "chunk_ids": [str(c.chunk_id) for c in citations],
            "document_ids": [str(d.document_id) for d in documents],
            "confidence": confidence,
            "grounded": grounded,
            "prompt_truncated": prompt.truncated,
            "prompt_version": prompt.prompt_version,
        },
    )

    return ProjectAssistantResponse(
        answer=answer,
        confidence=confidence,
        citations=citations,
        assets=assets,
        documents=documents,
        projects=projects,
        search_time_ms=search_time_ms,
        latency_ms=latency_ms,
        conversation_id=conversation.id,
        provider=getattr(llm, "provider", provider.name) if llm else provider.name,
        model=getattr(llm, "model", provider.model) if llm else provider.model,
        grounded=grounded,
    )
