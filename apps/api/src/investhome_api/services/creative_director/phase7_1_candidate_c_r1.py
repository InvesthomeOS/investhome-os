"""Phase 7.1 — Candidate C project-reality lock. One C-R1. No redesign. No promotion."""

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
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, cover_fit_canvas
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import CONCEPT3_ASSET_ID, DAY007_ASSET_ID, load_day007
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import (
    PRODUCTION_DOCTRINE,
    empty_semantic_spec,
    semantic_revision_contract,
)
from investhome_api.services.creative_director.phase7_0_production_reset import (
    CRITIC_KEYS,
    _HISTORY_KEYS as _H70,
)
from investhome_api.services.creative_director.phase7_0_production_reset import _preserve as _preserve_70
from investhome_api.services.creative_director.phase7_0_production_reset import _restore_history as _restore_70
from investhome_api.services.creative_director.phase7_1_reality_lock import (
    PARENT_C_ASSET_ID,
    architecture_difference_map,
    immutable_architecture_mask,
    lock_real_architecture,
    paste_real_logo,
    project_pixel_provenance,
    render_mask_preview,
    render_provenance_preview,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_71 = "phase7_1_candidate_c_project_reality_lock"
_HISTORY_KEYS = _H70 + (("production_architecture_70_tests", "quality70"),)
DEFAULT_LOGO_BOX = (52, 38, 248, 214)
ARCH_KEYS = (
    "BUILDING_SILHOUETTE_FIDELITY",
    "SPIRE_FIDELITY",
    "FACADE_FIDELITY",
    "WINDOW_FIDELITY",
    "ROOF_FIDELITY",
    "ENTRANCE_FIDELITY",
    "PROJECT_GEOMETRY_FIDELITY",
    "PROJECT_PIXEL_PROVENANCE",
)
PRESERVE_KEYS = (
    "ART_DIRECTION_PRESERVATION",
    "COMPOSITION_PRESERVATION",
    "TYPOGRAPHIC_HIERARCHY_PRESERVATION",
    "COMMERCIAL_STORY_PRESERVATION",
    "GRAPHIC_DEPTH_PRESERVATION",
    "BRAND_RELATIONSHIP_PRESERVATION",
    "NEGATIVE_SPACE_PRESERVATION",
    "WHOLE_CANVAS_CHARACTER_PRESERVATION",
    "PREMIUM_CHARACTER_PRESERVATION",
)
APPROVED_COPY = (
    REQUIRED_FACTS["headline"],
    REQUIRED_FACTS["discount"],
    REQUIRED_FACTS["discount_label"],
    REQUIRED_FACTS["list_price"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["cta"],
    APPROVED_BOTTOM_COPY,
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_70(blob)
    preserved["quality70"] = list(blob.get("production_architecture_70_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_70(blob, preserved)
    blob["production_architecture_70_tests"] = preserved.get("quality70")


def load_candidate_c(db: Session) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(_read_bytes(db, UUID(PARENT_C_ASSET_ID)))).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        return image
    except Exception:
        for path in (
            Path("/tmp/phase7-0-production-architecture-reset/08-final-candidate-C.png"),
            Path("artifacts/phase7-0-production-architecture-reset/08-final-candidate-C.png"),
        ):
            if path.is_file():
                image = Image.open(path).convert("RGB")
                if image.size != CANVAS_4X5:
                    image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
                return image
        raise RuntimeError("Phase 7.0 Candidate C parent is not available")


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


def _score_board(title: str, scores: dict[str, float], *, extra: list[str] | None = None) -> Image.Image:
    rows = [f"{k}: {v}" for k, v in scores.items()]
    if extra:
        rows.extend(extra)
    return _text_board(title, rows, size=(1088, 1360))


def _score_map(raw: Any, keys: tuple[str, ...]) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in keys}


def _gate(scores: dict[str, float], floor: float) -> bool:
    return bool(scores) and all(float(v) >= floor for v in scores.values())


def request_logo_box(parent: Image.Image) -> tuple[tuple[int, int, int, int], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Locate the Temple logo mark. JSON only."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Return the pixel box of the Temple logo mark (figure, not body copy) on this 1088x1360 ad. "
                            'JSON {"box":[x0,y0,x1,y1]}.'
                        ),
                        _img(parent, quality=82),
                    ],
                },
            ],
        }
    )
    raw = parsed.get("box") if isinstance(parsed, dict) else None
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        x0, y0, x1, y1 = (int(_num(v, 0)) for v in raw)
        if x1 - x0 >= 24 and y1 - y0 >= 24:
            return (
                max(0, min(CANVAS_4X5[0] - 8, x0)),
                max(0, min(CANVAS_4X5[1] - 8, y0)),
                max(8, min(CANVAS_4X5[0], x1)),
                max(8, min(CANVAS_4X5[1], y1)),
            ), calls
    return DEFAULT_LOGO_BOX, calls


def request_difference_notes(*, parent: Image.Image, day007: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Architecture difference classifier. JSON only. Do not invent praise."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Compare Candidate C (image 1) against REAL Day_007 (image 2). "
                            "Separate PROJECT_ARCHITECTURE from ATMOSPHERIC / GRAPHIC TREATMENT. "
                            "JSON keys: silhouette, spire, windows, facade, roof, entrance, "
                            "neighboring_architecture, invented_plaza, generated_skyline, notes."
                        ),
                        _text("CANDIDATE C"),
                        _img(parent, quality=78),
                        _text("REAL Day_007"),
                        _img(day007, quality=78),
                    ],
                },
            ],
        }
    )
    return parsed if isinstance(parsed, dict) else {}, calls


def request_architecture_validation(*, day007: Image.Image, locked: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1200,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Project-architecture geometry critic. Grade/lighting may differ. Geometry must match Day_007. JSON only. Do not inflate.",
                },
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Score C-R1 against REAL Day_007. Grade and evening mood are allowed. "
                            "Invented windows, facade, spire, roof, or entrance geometry are not. "
                            "0-10 for: " + ", ".join(ARCH_KEYS) + ". "
                            "Also architecture_fidelity 0-10. JSON {scores:{...}, architecture_fidelity:n, notes:}."
                        ),
                        _text("REAL Day_007"),
                        _img(day007, quality=80),
                        _text("CANDIDATE C-R1"),
                        _img(locked, quality=82),
                    ],
                },
            ],
        }
    )
    scores = _score_map(parsed, ARCH_KEYS)
    arch = round(_num((parsed or {}).get("architecture_fidelity"), scores.get("PROJECT_GEOMETRY_FIDELITY", 0)), 2)
    return {
        "schema": "Phase71ArchitectureValidationV1",
        "scores": scores,
        "architecture_fidelity": arch,
        "notes": str((parsed or {}).get("notes") or ""),
        "floor": 9,
        "pass": _gate(scores, 9) and arch >= 9,
    }, calls


def request_creative_preservation(*, parent: Image.Image, locked: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1400,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Creative preservation critic. Ignore necessary architecture replacement. Do not treat this as Candidate B. JSON only. Do not inflate.",
                },
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Candidate C is the creative parent. C-R1 must keep C's art direction, composition, "
                            "typographic hierarchy, commercial story, graphic depth, brand relationship, "
                            "negative space, whole-canvas character, and premium character. "
                            "Ignore invented-architecture replacement. Score 0-10: " + ", ".join(PRESERVE_KEYS) + ". "
                            "JSON {scores:{...}, notes:}."
                        ),
                        _text("CANDIDATE C PARENT"),
                        _img(parent, quality=80),
                        _text("CANDIDATE C-R1"),
                        _img(locked, quality=82),
                    ],
                },
            ],
        }
    )
    scores = _score_map(parsed, PRESERVE_KEYS)
    return {
        "schema": "Phase71CreativePreservationV1",
        "scores": scores,
        "notes": str((parsed or {}).get("notes") or ""),
        "floor": 8,
        "pass": _gate(scores, 8),
    }, calls


def request_final_critic(*, locked: Image.Image, day007: Image.Image, parent: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. JSON only. Do not inflate."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Evaluate C-R1 independently as a finished campaign visual. "
                            "Architecture fidelity is whether REAL Day_007 geometry is intact. "
                            "Score 0-10: " + ", ".join(CRITIC_KEYS) + ". JSON {scores:{...}, notes:}."
                        ),
                        _text("CANDIDATE C-R1"),
                        _img(locked, quality=84),
                        _text("REAL Day_007"),
                        _img(day007, quality=72),
                        _text("CANDIDATE C parent for context only — score C-R1, not the parent."),
                        _img(parent, quality=60),
                    ],
                },
            ],
        }
    )
    scores = _score_map(parsed, CRITIC_KEYS)
    others_ok = all(float(scores[k]) >= 8 for k in CRITIC_KEYS if k != "architecture_fidelity")
    arch_ok = float(scores.get("architecture_fidelity") or 0) >= 9
    return {
        "schema": "Phase71FinalVisualCriticV1",
        "scores": scores,
        "notes": str((parsed or {}).get("notes") or ""),
        "pass": others_ok and arch_ok,
    }, calls


def request_semantic_dna(locked: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Record semantic understanding. Not a scene graph. JSON only."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Describe territories as approximate 0-1 boxes if visible, relationships, and creative DNA. "
                            "JSON with territories, relationships, creative_dna."
                        ),
                        _img(locked, quality=80),
                    ],
                },
            ],
        }
    )
    return parsed if isinstance(parsed, dict) else {}, calls


def generate_phase7_1_candidate_c_r1(
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

    parent = load_candidate_c(db)
    source = load_day007(db)
    foundation, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.68, 0.20))
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    if logo_rgba is None:
        raise RuntimeError("Real Temple logo is required")

    mask, mask_payload = immutable_architecture_mask(foundation)
    diff_img, diff_payload = architecture_difference_map(parent, foundation, mask)
    notes, n = request_difference_notes(parent=parent, day007=foundation)
    vision_calls += n
    diff_payload["vision"] = notes

    locked, lock_meta, used_mask = lock_real_architecture(parent=parent, foundation=foundation, mask=mask)
    logo_box, n = request_logo_box(parent)
    vision_calls += n
    locked = paste_real_logo(locked, logo_rgba, box=logo_box, on_dark=True)
    provenance = project_pixel_provenance(used_mask)
    provenance["generated_logo_pixels"] = 0
    provenance["logo_box"] = list(logo_box)
    provenance["logo_asset_id"] = LOCKED_LOGO_ASSET_ID

    stored = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(locked),
        content_type="image/png",
        campaign_mode="project-v3-71-candidate-c-r1",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 7.1 Candidate C-R1 project-reality lock — not promoted",
    )
    asset_id = str(stored.id)

    arch, n = request_architecture_validation(day007=foundation, locked=locked)
    vision_calls += n
    preserve, n = request_creative_preservation(parent=parent, locked=locked)
    vision_calls += n
    critic, n = request_final_critic(locked=locked, day007=foundation, parent=parent)
    vision_calls += n

    spec = empty_semantic_spec(master_id=None, visual_asset_id=asset_id)
    dna, n = request_semantic_dna(locked)
    vision_calls += n
    territories = dna.get("territories") if isinstance(dna.get("territories"), dict) else {}
    for name, payload in territories.items():
        if name in spec["visual_territories"] and isinstance(payload, dict):
            spec["visual_territories"][name].update({k: payload.get(k) for k in ("box", "notes") if k in payload})
    relationships = dna.get("relationships") if isinstance(dna.get("relationships"), dict) else {}
    for name, payload in relationships.items():
        if name in spec["relationships"]:
            spec["relationships"][name] = payload if isinstance(payload, dict) else {"notes": str(payload)}
    if isinstance(dna.get("creative_dna"), dict):
        spec["creative_dna"].update({k: dna["creative_dna"].get(k, "") for k in spec["creative_dna"]})
    spec["protected_project_territory"] = {
        "source": "REAL_DAY_007",
        "asset_id": DAY007_ASSET_ID,
        "mask": mask_payload,
        "generated_project_architecture_pixels": 0,
    }
    spec["commercial_territory"] = spec["visual_territories"].get("COMMERCIAL_TERRITORY")
    spec["brand_territory"] = spec["visual_territories"].get("BRAND_TERRITORY")
    spec["cta_territory"] = spec["visual_territories"].get("CTA_TERRITORY")
    spec["editorial_closure_territory"] = spec["visual_territories"].get("EDITORIAL_CLOSURE_TERRITORY")
    spec["approved_copy"] = list(APPROVED_COPY)
    spec["parent"] = "Candidate C"
    spec["parent_asset_id"] = PARENT_C_ASSET_ID
    spec["lock_method"] = lock_meta.get("method")
    spec["status"] = "PASS"
    spec["revision_contracts"] = semantic_revision_contract()

    rev = semantic_revision_contract()
    image_calls = provider_call_count()
    if image_calls != 0:
        raise RuntimeError("Phase 7.1 forbids GPT Image generation of protected project architecture")

    status = "FINAL_VISUAL_MASTER_PENDING_HUMAN_APPROVAL"
    images = {
        "day007": foundation,
        "parent": parent,
        "difference": diff_img,
        "mask": render_mask_preview(foundation, mask),
        "cr1": locked,
        "c_vs_cr1": _pair("06  CANDIDATE C vs C-R1", ("Candidate C", parent), ("Candidate C-R1", locked)),
        "day007_vs_cr1": _pair("07  Day_007 vs C-R1", ("REAL Day_007", foundation), ("Candidate C-R1", locked)),
        "provenance": render_provenance_preview(locked, used_mask),
        "architecture": _score_board(
            "09  ARCHITECTURE VALIDATION",
            arch.get("scores") or {},
            extra=[
                f"architecture_fidelity {arch.get('architecture_fidelity')}",
                f"pass {arch.get('pass')}",
                str(arch.get("notes") or "")[:240],
            ],
        ),
        "preservation": _score_board(
            "10  CREATIVE PRESERVATION",
            preserve.get("scores") or {},
            extra=[f"pass {preserve.get('pass')}", str(preserve.get("notes") or "")[:240]],
        ),
        "critic": _score_board(
            "11  FINAL VISUAL CRITIC",
            critic.get("scores") or {},
            extra=[f"pass {critic.get('pass')}", str(critic.get("notes") or "")[:240]],
        ),
        "spec": _text_board(
            "12  SEMANTIC MASTER SPEC",
            [
                f"C-R1 {asset_id}",
                f"parent Candidate C {PARENT_C_ASSET_ID}",
                f"photo {DAY007_ASSET_ID}",
                f"logo {LOCKED_LOGO_ASSET_ID}",
                *list(APPROVED_COPY),
                "protected project territory: REAL_DAY_007",
                "generated_project_architecture_pixels: 0",
                "pixel-complete scene graph: NO",
            ],
        ),
        "review": _pair("13  HUMAN REVIEW BOARD", ("Candidate C parent", parent), ("Candidate C-R1", locked)),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_71,
        "created_at": _now(),
        "status": status,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "parent": "Candidate C",
        "parent_asset_id": PARENT_C_ASSET_ID,
        "c_r1_asset_id": asset_id,
        "day007_asset_id": DAY007_ASSET_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_transform": transform,
        "difference_map": diff_payload,
        "immutable_mask": mask_payload,
        "lock_meta": lock_meta,
        "project_pixel_provenance": provenance,
        "architecture_validation": arch,
        "creative_preservation": preserve,
        "final_visual_critic": critic,
        "semantic_creative_spec": spec,
        "revision_readiness": rev,
        "semantic_spec_status": spec.get("status"),
        "price_revision": (rev.get("PRICE_EDIT_ONLY") or {}).get("status"),
        "copy_revision": (rev.get("COPY_EDIT_ONLY") or {}).get("status"),
        "visual_replace": (rev.get("VISUAL_REPLACE_ONLY") or {}).get("status"),
        "image_model_calls": image_calls,
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "generated_project_architecture_pixels": 0,
        "generated_logo_pixels": 0,
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
    }
    tests = list(blob.get("candidate_c_r1_71_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["candidate_c_r1_71_tests"] = tests
    _restore_history(blob, preserved)
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 7.1 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
