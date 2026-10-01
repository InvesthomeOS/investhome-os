"""Non-project designed void for ORNEK_00013 DNA. Not navy. Not paper. Not THE_REGISTER shaft."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.project_reality_firewall_v1 import (
    MAX_FIELD_ATTEMPTS,
    run_project_reality_firewall,
)
from investhome_api.services.gpt_image_design.client import decode_remote_image, generate_image
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
)
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image, sniff_image_content_type

FIELD_PROMPT = (
    "Create a vertical 4:5 editorial color field for graphic composition. "
    "A deep oxidized bronze-charcoal void, almost even, with quiet mineral grain "
    "and a slightly lighter falloff toward the upper right as designed emptiness, not a landscape. "
    "No shaft of light, no paper sheet, no vellum, no folds, no navy blue, no cobalt, no sky, no clouds, no horizon. "
    "Material and atmosphere only. Abstract. "
    "NO buildings, NO architecture, NO interiors, NO exteriors, NO windows, NO columns, NO spires, "
    "NO towers, NO city, NO streets, NO people, NO furniture, NO logos, NO letters, NO numbers, "
    "NO watermarks, NO fake text, NO captions, NO UI. Do not depict The Temple or any real-estate project."
)


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def generate_void_field(
    db: Session,
    user: User,
    *,
    project_id: UUID,
    session_id: str,
    quality: str = "high",
    reuse_path: Path | None = None,
) -> dict[str, Any]:
    if reuse_path is not None and reuse_path.is_file():
        image = Image.open(reuse_path).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        raw = _png(image)
        firewall = run_project_reality_firewall(image)
        return {
            "image": image,
            "bytes": raw,
            "asset_id": None,
            "provider": "gpt-image",
            "model": "reused",
            "quality": quality,
            "prompt": FIELD_PROMPT,
            "purpose": "NON_PROJECT_CREATIVE_FIELD",
            "firewall": firewall,
            "attempts": [{"attempt": 0, "firewall": firewall.get("status"), "reused": True}],
            "passed": firewall.get("status") == "PASS",
        }
    avail = provider_availability()
    if not avail.available:
        raise RuntimeError(f"GPT Image unavailable for reference-guided field: {avail.reason}")
    model = resolve_model(avail.model or DEFAULT_MODEL)
    attempts: list[dict[str, Any]] = []
    last_image: Image.Image | None = None
    last_bytes: bytes | None = None
    last_firewall: dict[str, Any] | None = None
    for attempt in range(1, MAX_FIELD_ATTEMPTS + 1):
        remote = generate_image(
            api_key=openai_api_key(),
            model=model,
            prompt=FIELD_PROMPT,
            size="1088x1360",
            quality=quality,
            base_url=resolve_base_url(get_settings()),
            variant=f"phase11_11_void_field_{attempt}",
        )
        raw = decode_remote_image(remote)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
            raw = _png(image)
        firewall = run_project_reality_firewall(image)
        attempts.append(
            {
                "attempt": attempt,
                "firewall": firewall.get("status"),
                "hits": firewall.get("hits"),
                "reason": firewall.get("reason"),
            }
        )
        last_image, last_bytes, last_firewall = image, raw, firewall
        if firewall.get("status") == "PASS":
            break
    assert last_image is not None and last_bytes is not None and last_firewall is not None
    asset_id = None
    try:
        asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=project_id,
            content=last_bytes,
            content_type=sniff_image_content_type(last_bytes),
            campaign_mode="phase11_11_non_project_void",
            session_id=session_id,
            provider_generation_id=None,
            campaign_context_id=session_id,
            brief_excerpt="non-project oxidized bronze void; no architecture",
        )
        asset_id = str(asset.id)
    except Exception:
        asset_id = None
    return {
        "image": last_image,
        "bytes": last_bytes,
        "asset_id": asset_id,
        "provider": "gpt-image",
        "model": model,
        "quality": quality,
        "prompt": FIELD_PROMPT,
        "purpose": "NON_PROJECT_CREATIVE_FIELD",
        "firewall": last_firewall,
        "attempts": attempts,
        "passed": last_firewall.get("status") == "PASS",
    }
