"""Marketing AI intelligence API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivitySource
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_ai import (
    AcceptRecommendationRequest,
    AIAnomalyListResponse,
    AIBriefingResponse,
    AIDashboardResponse,
    AIInsightListResponse,
    AIMarketingHealthResponse,
    AIPredictionsResponse,
    AIRecommendationItem,
    AIRecommendationListResponse,
    AISettingsResponse,
    AISettingsUpdate,
    CopilotQueryRequest,
    CopilotQueryResponse,
)
from investhome_api.schemas.marketing_ai_assistant import (
    AssistantArchiveRequest,
    AssistantGenerateRequest,
    AssistantGenerateResponse,
    AssistantModesResponse,
    AssistantOutputListResponse,
    AssistantSaveRequest,
)
from investhome_api.services.activity_service import ActivityRequestContext, log_activity
from investhome_api.services.marketing.ai_intelligence_service import (
    accept_recommendation,
    build_ai_dashboard,
    get_ai_settings,
    get_anomalies,
    get_executive_briefing,
    get_marketing_health,
    get_marketing_insights,
    get_predictions,
    get_recommendations,
    query_copilot,
    update_ai_settings,
)
from investhome_api.services.marketing import assistant_service

router = APIRouter(prefix="/marketing/ai", tags=["marketing-ai"])


def _audit(
    db: Session,
    user: User,
    *,
    description_key: str,
    entity_id: UUID,
    action: ActivityAction = ActivityAction.VIEWED,
    metadata: dict | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.MARKETING_AI,
        entity_id=entity_id,
        description_key=description_key,
        actor_user=user,
        source=ActivitySource.API,
        metadata=metadata,
        request_context=ActivityRequestContext(source=ActivitySource.API),
    )


@router.get("/dashboard", response_model=AIDashboardResponse)
def get_ai_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AIDashboardResponse:
    result = build_ai_dashboard(db, user)
    _audit(db, user, description_key="marketing.ai.dashboard.viewed", entity_id=user.id)
    db.commit()
    return result


@router.get("/insights", response_model=AIInsightListResponse)
def list_ai_insights(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
    category: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> AIInsightListResponse:
    result = get_marketing_insights(db, user, category=category, limit=limit)
    _audit(
        db,
        user,
        description_key="marketing.ai.insight.viewed",
        entity_id=user.id,
        metadata={"category": category, "count": result.total},
    )
    db.commit()
    return result


@router.get("/recommendations", response_model=AIRecommendationListResponse)
def list_ai_recommendations(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
    recommendation_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> AIRecommendationListResponse:
    return get_recommendations(db, user, recommendation_type=recommendation_type, limit=limit)


@router.post("/recommendations/{recommendation_id}/accept", response_model=AIRecommendationItem)
def accept_ai_recommendation(
    recommendation_id: UUID,
    payload: AcceptRecommendationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AIRecommendationItem:
    result = accept_recommendation(db, user, recommendation_id)
    _audit(
        db,
        user,
        description_key="marketing.ai.recommendation.accepted",
        entity_id=recommendation_id,
        action=ActivityAction.UPDATED,
        metadata={"notes": payload.notes},
    )
    db.commit()
    return result


@router.get("/predictions", response_model=AIPredictionsResponse)
def list_ai_predictions(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AIPredictionsResponse:
    return get_predictions(db)


@router.get("/anomalies", response_model=AIAnomalyListResponse)
def list_ai_anomalies(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
    limit: int = Query(50, ge=1, le=200),
) -> AIAnomalyListResponse:
    return get_anomalies(db, limit=limit)


@router.get("/briefings", response_model=AIBriefingResponse)
def get_ai_briefing(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
    period: str = Query("weekly"),
) -> AIBriefingResponse:
    result = get_executive_briefing(db, user, period=period)
    _audit(
        db,
        user,
        description_key="marketing.ai.brief.generated",
        entity_id=user.id,
        metadata={"period": period},
    )
    db.commit()
    return result


@router.post("/copilot", response_model=CopilotQueryResponse)
def post_copilot_query(
    payload: CopilotQueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "query_copilot")),
) -> CopilotQueryResponse:
    result = query_copilot(
        db,
        user,
        query_text=payload.query,
        preset=payload.preset,
        timezone=payload.timezone,
    )
    db.commit()
    return result


@router.get("/health", response_model=AIMarketingHealthResponse)
def get_ai_health(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AIMarketingHealthResponse:
    return get_marketing_health(db, user)


@router.get("/settings", response_model=AISettingsResponse)
def get_ai_settings_route(
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AISettingsResponse:
    return get_ai_settings()


@router.put("/settings", response_model=AISettingsResponse)
def put_ai_settings(
    payload: AISettingsUpdate,
    user: User = Depends(require_permission("marketing", "manage_ai_settings")),
) -> AISettingsResponse:
    return update_ai_settings(payload)


# --- Sprint 8A4: AI Marketing Assistant (draft-only) ---


@router.get("/assistant/modes", response_model=AssistantModesResponse)
def get_assistant_modes(
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AssistantModesResponse:
    return assistant_service.list_modes()


@router.post("/assistant/generate", response_model=AssistantGenerateResponse)
def generate_assistant_output(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    result = assistant_service.generate(db, user, payload)
    db.commit()
    return result


def _generate_mode(
    db: Session,
    user: User,
    payload: AssistantGenerateRequest,
    mode: str,
) -> AssistantGenerateResponse:
    result = assistant_service.generate(db, user, payload.model_copy(update={"mode": mode}))
    db.commit()
    return result


@router.post("/assistant/summary", response_model=AssistantGenerateResponse)
def generate_marketing_summary(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "marketing_summary")


@router.post("/assistant/campaign-analysis", response_model=AssistantGenerateResponse)
def generate_campaign_analysis(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "campaign_analysis")


@router.post("/assistant/content-draft", response_model=AssistantGenerateResponse)
def generate_content_draft(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "content_draft")


@router.post("/assistant/campaign-brief", response_model=AssistantGenerateResponse)
def generate_campaign_brief(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "campaign_brief")


@router.post("/assistant/audience-suggestions", response_model=AssistantGenerateResponse)
def generate_audience_suggestions(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "audience_suggestion")


@router.post("/assistant/channel-suggestions", response_model=AssistantGenerateResponse)
def generate_channel_suggestions(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "channel_suggestion")


@router.post("/assistant/translate", response_model=AssistantGenerateResponse)
def generate_translation(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "translation")


@router.post("/assistant/next-actions", response_model=AssistantGenerateResponse)
def generate_next_actions(
    payload: AssistantGenerateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "use_ai")),
) -> AssistantGenerateResponse:
    return _generate_mode(db, user, payload, "next_actions")


@router.get("/assistant/outputs", response_model=AssistantOutputListResponse)
def list_assistant_outputs(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
    organization_id: UUID | None = None,
    output_type: str | None = None,
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> AssistantOutputListResponse:
    return assistant_service.list_outputs(
        db,
        user,
        organization_id=organization_id,
        output_type=output_type,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/assistant/outputs/{output_id}", response_model=AssistantGenerateResponse)
def get_assistant_output(
    output_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "view_ai")),
) -> AssistantGenerateResponse:
    return assistant_service.get_output(db, user, output_id)


@router.post("/assistant/outputs/{output_id}/save", response_model=AssistantGenerateResponse)
def save_assistant_output(
    output_id: UUID,
    payload: AssistantSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "save_ai")),
) -> AssistantGenerateResponse:
    result = assistant_service.save_output(db, user, output_id, payload)
    db.commit()
    return result


@router.post("/assistant/outputs/{output_id}/archive", response_model=AssistantGenerateResponse)
def archive_assistant_output(
    output_id: UUID,
    payload: AssistantArchiveRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "save_ai")),
) -> AssistantGenerateResponse:
    result = assistant_service.archive_output(db, user, output_id, payload)
    db.commit()
    return result
