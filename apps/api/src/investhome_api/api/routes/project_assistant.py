"""AI Project Assistant API — grounded RAG over indexed project knowledge."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.project_assistant import (
    ProjectAssistantRequest,
    ProjectAssistantResponse,
)
from investhome_api.services.project_assistant.service import ask_project_assistant

router = APIRouter(tags=["ai-project-assistant"])

_cs_view = Depends(require_permission("creative_studio", "view"))


@router.post("/ai/project-assistant", response_model=ProjectAssistantResponse)
def project_assistant(
    body: ProjectAssistantRequest,
    db: Session = Depends(get_db),
    user: User = _cs_view,
) -> ProjectAssistantResponse:
    """
    Ask a question grounded in indexed project documents.

    Flow: scope → hybrid search → prompt → LLM → citations + confidence.
    Never fabricates when evidence is insufficient.
    """
    result = ask_project_assistant(db, user, body)
    db.commit()
    return result
