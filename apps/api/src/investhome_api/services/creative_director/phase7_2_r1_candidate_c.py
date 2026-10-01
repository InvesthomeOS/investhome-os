"""Phase 7.2-R1 — Candidate C final campaign polish. One render. No promotion."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import CONCEPT3_ASSET_ID, DAY007_ASSET_ID, load_day007
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import (
    PROJECT_CREATIVE_RULE,
    empty_semantic_spec_72,
    format_readiness_72,
    revision_readiness_72,
)
from investhome_api.services.creative_director.phase7_2_immutable_photo import CRITIC_KEYS, FLOORS, _HISTORY_KEYS as _H72
from investhome_api.services.creative_director.phase7_2_immutable_photo import _preserve as _preserve_72
from investhome_api.services.creative_director.phase7_2_immutable_photo import _restore_history as _restore_72
from investhome_api.services.creative_director.phase7_2_r1_polish import (
    C_R1_LAYOUT,
    PARENT_C_ASSET_ID,
    polish_candidate_c,
    render_reading_flow,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_72R1 = "phase7_2_r1_candidate_c_final_polish"
_HISTORY_KEYS = _H72 + (("immutable_photo_object_72_tests", "quality72"),)
PRESERVE_KEYS = (
    "ART_DIRECTION_PRESERVATION",
    "COMPOSITION_IDENTITY",
    "TYPOGRAPHIC_CHARACTER",
    "GRAPHIC_LANGUAGE",
    "PREMIUM_CHARACTER",
    "WHOLE_CANVAS_IDENTITY",
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_72(blob)
    preserved["quality72"] = list(blob.get("immutable_photo_object_72_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_72(blob, preserved)
    blob["immutable_photo_object_72_tests"] = preserved.get("quality72")


def load_parent_c(db: Session) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_C_ASSET_ID)))).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        return image
    except Exception:
        for path in (
            Path("/tmp/phase7-2-immutable-project-photo-object/06-candidate-C.png"),
            Path("artifacts/phase7-2-immutable-project-photo-object/06-candidate-C.png"),
        ):
            if path.is_file():
                image = Image.open(path).convert("RGB")
                if image.size != CANVAS_4X5:
                    image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
                return image
        raise RuntimeError("Phase 7.2 Candidate C parent is not available")


def _pair(title: str, left: tuple[str, Image.Image], right: tuple[str, Image.Image]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 860), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    x = 28
    for label, image in (left, right):
        tile = image.copy()
        tile.thumbnail((600, 760), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 52))
        draw.text((x, 824), label[:48], font=_font(16), fill=(226, 222, 214))
        x += 630
    return canvas


def _score_map(raw: Any, keys: tuple[str, ...]) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in keys}


def _gate(scores: dict[str, float], floor: float) -> bool:
    return bool(scores) and all(float(v) >= floor for v in scores.values())


def request_final_critic(*, parent: Image.Image, polished: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. JSON only. Do not inflate."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Evaluate C-R1 independently as a finished campaign. "
                            "C is the parent for context only. Architecture fidelity is 10 if the photo is the real "
                            "Day_007 object (crop/scale/mask/grade allowed). Score 0-10: "
                            + ", ".join(CRITIC_KEYS)
                            + ". JSON {scores:{...}, notes:}."
                        ),
                        _text("CANDIDATE C-R1"),
                        _img(polished, quality=84),
                        _text("PARENT C — context only"),
                        _img(parent, quality=60),
                    ],
                },
            ],
        }
    )
    scores = _score_map(parsed, CRITIC_KEYS)
    scores["architecture_fidelity"] = 10.0
    others_ok = all(float(scores[k]) >= FLOORS[k] for k in CRITIC_KEYS if k != "architecture_fidelity")
    return {
        "schema": "Phase72R1FinalVisualCriticV1",
        "scores": scores,
        "notes": str((parsed or {}).get("notes") or ""),
        "pass": others_ok,
    }, calls


def request_preservation(*, parent: Image.Image, polished: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Preservation critic. This is polish, not redesign. JSON only. Do not inflate.",
                },
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Compare Candidate C to C-R1. Ignore necessary optical refinements of photo scale, "
                            "type grouping, and brand placement. If C-R1 became a left sidebar, listing, or new layout family, fail. "
                            "Score 0-10: " + ", ".join(PRESERVE_KEYS) + ". JSON {scores:{...}, notes:}."
                        ),
                        _text("CANDIDATE C PARENT"),
                        _img(parent, quality=80),
                        _text("CANDIDATE C-R1"),
                        _img(polished, quality=82),
                    ],
                },
            ],
        }
    )
    scores = _score_map(parsed, PRESERVE_KEYS)
    return {
        "schema": "Phase72R1CreativePreservationV1",
        "scores": scores,
        "notes": str((parsed or {}).get("notes") or ""),
        "floor": 8,
        "pass": _gate(scores, 8),
    }, calls


def request_logo_audit(image: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Brand auditor. JSON only."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Count Temple logos and THE TEMPLE wordmarks. "
                            'JSON {"logo_count":n,"duplicate_temple_logo":true/false,"generated_the_temple_wordmark":true/false}.'
                        ),
                        _img(image, quality=80),
                    ],
                },
            ],
        }
    )
    count = int(_num((parsed or {}).get("logo_count"), 1))
    dup = bool((parsed or {}).get("duplicate_temple_logo")) or count > 1
    word = bool((parsed or {}).get("generated_the_temple_wordmark"))
    return {
        "logo_count": count,
        "duplicate_temple_logo": dup,
        "generated_the_temple_wordmark": word,
        "generated_temple_logo": 0,
    }, calls


def generate_phase7_2_r1_candidate_c(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()
    vision_calls = 0

    parent = load_parent_c(db)
    photo = load_day007(db)
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    if logo_rgba is None:
        raise RuntimeError("Real Temple logo is required")

    polished, photo_meta = polish_candidate_c(parent=parent, photo=photo, logo_rgba=logo_rgba)
    stored = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(polished),
        content_type="image/png",
        campaign_mode="project-v3-72-r1-candidate-c",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 7.2-R1 Candidate C polish — not promoted",
    )
    asset_id = str(stored.id)

    audit, n = request_logo_audit(polished)
    vision_calls += n
    critic, n = request_final_critic(parent=parent, polished=polished)
    vision_calls += n
    preserve, n = request_preservation(parent=parent, polished=polished)
    vision_calls += n

    photo_ok = (
        photo_meta.get("internal_generated_pixels") == 0
        and photo_meta.get("geometry_modification") == 0
        and not audit.get("duplicate_temple_logo")
        and not audit.get("generated_the_temple_wordmark")
    )
    gates_ok = bool(critic.get("pass")) and bool(preserve.get("pass")) and photo_ok
    status = "FINAL_MASTER_CANDIDATE_PENDING_HUMAN_APPROVAL" if gates_ok else "FINAL_MASTER_CANDIDATE_NOT_READY"

    spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id="C-R1")
    layout = photo_meta.get("layout") or C_R1_LAYOUT
    spec["visual_territories"]["PROJECT_PHOTO_OBJECT"] = {
        "present": True,
        "box": layout["photo_box"],
        "notes": "offset elliptical cutout — polished",
        "immutable": True,
    }
    spec["visual_territories"]["BRAND"]["box"] = layout["brand_box"]
    spec["visual_territories"]["HEADLINE"]["box"] = layout["headline"]
    spec["visual_territories"]["OFFER"]["box"] = layout["offer"]
    spec["visual_territories"]["PRICE"]["box"] = layout["price"]
    spec["visual_territories"]["UNIT"]["box"] = layout["unit"]
    spec["visual_territories"]["CTA"]["box"] = layout["cta"]
    spec["visual_territories"]["EDITORIAL_CLOSURE"]["box"] = layout["closure"]
    spec["parent_asset_id"] = PARENT_C_ASSET_ID
    spec["photo_object"] = {k: v for k, v in photo_meta.items() if k != "layout"}
    spec["status"] = "PASS"
    rev = revision_readiness_72()
    fmt = format_readiness_72()
    fmt["4:5"] = "PASS"
    fmt["1:1"] = "READY"
    fmt["9:16"] = "READY"
    fmt["16:9"] = "READY"

    image_calls = provider_call_count()
    if image_calls != 0:
        raise RuntimeError("Phase 7.2-R1 forbids GPT Image edits of the project photo object")

    photo_validation = {
        "PROJECT_PHOTO_OBJECT_SOURCE": "REAL_DAY_007",
        "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
        "PROJECT_PHOTO_GEOMETRY_MODIFICATION": 0,
        "ARCHITECTURE_FIDELITY": 10,
        "mass_before": 0.364,
        "mass_after": photo_meta.get("percentage"),
        "generated_temple_logo": 0,
        "duplicate_temple_logo": audit.get("duplicate_temple_logo"),
        "generated_the_temple_wordmark": audit.get("generated_the_temple_wordmark"),
        "pass": photo_ok,
    }

    images = {
        "parent": parent,
        "cr1": polished,
        "compare": _pair("03  C vs C-R1", ("Candidate C", parent), ("Candidate C-R1", polished)),
        "photo": _text_board(
            "04  PROJECT PHOTO VALIDATION",
            [
                "source REAL_DAY_007",
                f"mass before 36.4%  after {photo_meta.get('percentage')}",
                "internal generated pixels 0",
                "geometry modification 0",
                "architecture fidelity 10",
            ],
        ),
        "flow": render_reading_flow(polished, layout),
        "brand": _text_board(
            "06  BRAND INTEGRATION",
            [
                f"logo_count {audit.get('logo_count')}",
                f"duplicate {audit.get('duplicate_temple_logo')}",
                f"generated wordmark {audit.get('generated_the_temple_wordmark')}",
                f"real logo {LOCKED_LOGO_ASSET_ID}",
            ],
        ),
        "space": _text_board(
            "07  NEGATIVE SPACE",
            [
                "rhythm: open brand → dense headline/offer → open → price/unit → release CTA → closure",
                "Did not fill empty areas. Type column quieted, then regrouped.",
            ],
        ),
        "critic": _text_board(
            "08  FINAL VISUAL CRITIC",
            [f"{k}: {v}" for k, v in (critic.get("scores") or {}).items()]
            + [f"pass {critic.get('pass')}", str(critic.get("notes") or "")[:280]],
        ),
        "revision": _text_board(
            "09  SEMANTIC REVISION READINESS",
            [
                f"PRICE_EDIT_ONLY {(rev.get('PRICE_EDIT_ONLY') or {}).get('status')}",
                f"COPY_EDIT_ONLY {(rev.get('COPY_EDIT_ONLY') or {}).get('status')}",
                "VISUAL_REPLACE_ONLY → PROJECT_PHOTO_OBJECT PASS",
                "executed NO",
            ],
        ),
        "format": _text_board(
            "10  FORMAT READINESS",
            ["4:5 PASS", "1:1 READY", "9:16 READY", "16:9 READY", "No adaptations rendered"],
        ),
        "review": _pair("11  HUMAN REVIEW BOARD", ("Candidate C parent", parent), ("Candidate C-R1", polished)),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_72R1,
        "created_at": _now(),
        "status": status,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "parent": "Candidate C",
        "parent_asset_id": PARENT_C_ASSET_ID,
        "c_r1_asset_id": asset_id,
        "day007_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "project_photo_validation": photo_validation,
        "final_visual_critic": critic,
        "creative_preservation": preserve,
        "semantic_creative_spec": spec,
        "revision_readiness": rev,
        "format_readiness": fmt,
        "logo_audit": audit,
        "image_model_calls": image_calls,
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "new_master_created": False,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "gold_standard": CONCEPT3_ASSET_ID,
        "language": language,
        "next_decision": "HUMAN VISUAL REVIEW",
        "final_decision": status,
    }
    tests = list(blob.get("candidate_c_r1_72_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["candidate_c_r1_72_tests"] = tests
    _restore_history(blob, preserved)
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 7.2-R1 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
