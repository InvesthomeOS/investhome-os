"""Platform metadata and feature flag introspection (non-secret)."""

from __future__ import annotations

from fastapi import APIRouter

from investhome_api.api.responses import ApiResponse, success_response
from investhome_api.config.feature_flags import FeatureFlags, get_feature_flags
from investhome_api.config.settings import get_settings

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("", response_model=ApiResponse[dict])
def get_platform_meta() -> ApiResponse[dict]:
    settings = get_settings()
    flags: FeatureFlags = get_feature_flags()
    return success_response(
        {
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "feature_flags": flags.model_dump(),
        }
    )
