from datetime import UTC, datetime

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from investhome_api.api.responses import ApiResponse, success_response
from investhome_api.config.settings import get_settings
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import engine

router = APIRouter(tags=["health"])


def _database_status() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "unavailable"


class HealthData(BaseModel):
    status: str = Field(examples=["ok"])
    service: str
    version: str
    environment: str
    timestamp: datetime
    database: str


class HealthResponse(BaseModel):
    """Legacy health shape (kept for backward compatibility)."""

    status: str = Field(examples=["ok"])
    service: str
    version: str
    environment: str
    timestamp: datetime
    database: str
    request_id: str | None = None


@router.get("/health", response_model=HealthResponse)
def health_check(_request: Request) -> HealthResponse:
    """Liveness-oriented check (always 200). Prefer /live and /ready for probes."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
        database=_database_status(),
        request_id=get_request_id(),
    )


@router.get("/live")
def liveness(_request: Request) -> dict[str, str]:
    """Process is up — does not check dependencies."""
    return {"status": "alive", "request_id": get_request_id() or ""}


@router.get("/ready")
def readiness(_request: Request, response: Response) -> dict[str, str]:
    """Ready to serve traffic — requires database connectivity."""
    database = _database_status()
    if database != "connected":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": database, "request_id": get_request_id() or ""}
    return {"status": "ready", "database": database, "request_id": get_request_id() or ""}


@router.get("/health/v2", response_model=ApiResponse[HealthData])
def health_check_v2(_request: Request) -> ApiResponse[HealthData]:
    legacy = health_check(_request)
    return success_response(
        HealthData(
            status=legacy.status,
            service=legacy.service,
            version=legacy.version,
            environment=legacy.environment,
            timestamp=legacy.timestamp,
            database=legacy.database,
        )
    )
