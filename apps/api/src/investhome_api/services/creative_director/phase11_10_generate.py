"""One gpt-image-2 protected-source edit. No creative R1 loop."""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy.orm import Session

from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase11_10_source import encode_png
from investhome_api.services.creative_director.phase11_10_strategy import campaign_prompt
from investhome_api.services.gpt_image_design.client import decode_remote_image, edit_image
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
    resolve_quality,
)
from investhome_api.config.settings import get_settings
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image, sniff_image_content_type
from investhome_api.services.gpt_image_design.svg_raster import svg_bytes_to_png


def raster_logo(logo_bytes: bytes) -> bytes:
    png = svg_bytes_to_png(logo_bytes, max_side=1024)
    if png:
        return png
    return logo_bytes


def generate_ai_native_master(
    db: Session,
    user: User,
    *,
    project_id: UUID,
    session_id: str,
    source_png: bytes,
    mask_png: bytes,
    logo_bytes: bytes,
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        raise RuntimeError(f"GPT Image unavailable: {avail.reason}")
    model = resolve_model(avail.model or DEFAULT_MODEL)
    quality = resolve_quality("high")
    prompt = campaign_prompt()
    logo_png = raster_logo(logo_bytes)
    remote = edit_image(
        api_key=openai_api_key(),
        model=model,
        prompt=prompt,
        images=[
            (source_png, "image1-temple-source.png", "image/png"),
            (logo_png, "image2-temple-logo.png", "image/png"),
        ],
        mask=mask_png,
        size="1088x1360",
        quality=quality,
        base_url=resolve_base_url(get_settings()),
        variant="phase11_10_ai_native_master",
        timeout=180.0,
    )
    raw = decode_remote_image(remote)
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if image.size != (1088, 1360):
        image = image.resize((1088, 1360), Image.Resampling.LANCZOS)
        raw = encode_png(image)
    asset_id = None
    try:
        asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=project_id,
            content=raw,
            content_type=sniff_image_content_type(raw),
            campaign_mode="ai_native_premium_feasibility",
            session_id=session_id,
            provider_generation_id=None,
            campaign_context_id=session_id,
            brief_excerpt="AI-native Temple master; protected source edit; feasibility only",
        )
        asset_id = str(asset.id)
    except Exception:
        asset_id = None
    return {
        "image": image,
        "bytes": raw,
        "asset_id": asset_id,
        "provider": "gpt-image",
        "model": model,
        "quality": quality,
        "prompt": prompt,
        "method": "images_edits_source_plus_architecture_mask_plus_real_logo",
    }
