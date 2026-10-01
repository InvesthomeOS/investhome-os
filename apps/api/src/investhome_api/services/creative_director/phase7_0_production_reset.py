"""Phase 7.0 — production architecture reset.

AI visual master + semantic spec. No structured reconstruction. No promotion.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageOps
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import _logo_board
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
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase6_4_ai_native_authoring import _HISTORY_KEYS as _H64
from investhome_api.services.creative_director.phase6_4_ai_native_authoring import _preserve as _preserve_64
from investhome_api.services.creative_director.phase7_0_doctrine import (
    MASTER_TYPE,
    PRIMARY_CREATIVE_ENGINE,
    PRODUCTION_DOCTRINE,
    RETIRED_RESEARCH_BRANCHES,
    empty_semantic_spec,
    format_adaptation_spec,
    production_doctrine,
    semantic_revision_contract,
)
from investhome_api.services.creative_director.visual_composition_draft import _jpeg_bytes, _png_bytes
from investhome_api.services.gpt_image_design.client import (
    GptImageProviderError,
    decode_remote_image,
    edit_image,
    provider_call_count,
    reset_provider_call_count,
)
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
)
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_70 = "phase7_0_production_architecture_reset"
MAX_IMAGE_CALLS = 3
CANDIDATE_IDS = ("A", "B", "C")
CRITIC_KEYS = (
    "agency_campaign_feel",
    "art_direction",
    "composition",
    "photo_graphic_integration",
    "typographic_authority",
    "commercial_storytelling",
    "brand_integration",
    "graphic_depth",
    "negative_space",
    "whole_canvas_character",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)
_HISTORY_KEYS = _H64 + (("ai_native_authoring_64_tests", "quality64"),)
CAMPAIGN_COPY = (
    REQUIRED_FACTS["headline"],
    f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
    REQUIRED_FACTS["list_price"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["cta"],
    APPROVED_BOTTOM_COPY,
    "THE TEMPLE",
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_64(blob)
    preserved["quality64"] = list(blob.get("ai_native_authoring_64_tests") or [])
    return preserved


def _scores(raw: Any) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in CRITIC_KEYS}


def _avg(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return round(sum(float(v) for v in scores.values()) / max(len(scores), 1), 2)


def artist_prompt(brief: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Create one finished 4:5 premium real-estate campaign advertisement.",
            "Image 1 is the REAL project photograph (Day_007). This building is architectural ground truth.",
            "Do not invent a different building. Do not add the US Capitol, Washington Monument, or any invented skyline.",
            "You may grade, light, and art-direct the photograph. You may add graphic treatment, overlays, decorative geometry, and typographic art direction.",
            "Do not replace the architecture.",
            "Image 2 is the REAL Temple logo. Use it as the brand mark. Do not invent a logo.",
            "Image 3 is approved Concept 3 — campaign DNA for sophistication, typographic drama, graphic depth, and whole-canvas character.",
            "Do not pixel-copy Concept 3. Do not reproduce its invented architecture.",
            "Visual idea: " + str(brief.get("visual_idea") or ""),
            "Creative brief: " + str(brief.get("creative_brief") or ""),
            "Required copy only: " + " / ".join(CAMPAIGN_COPY) + ".",
            "The result must feel like finished agency advertising, not a listing card and not text placed beside a property photo.",
        ]
    )


def request_three_briefs(*, photo: Image.Image, logo: Image.Image, concept3: Image.Image) -> tuple[list[dict[str, Any]], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.75,
            "max_tokens": 2200,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Independent advertising Creative Director. Invent finished campaign visuals. JSON only.",
                },
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Invent THREE genuinely different finished campaign concepts for The Temple. "
                            "All three use THIS real photograph as architectural truth. "
                            "Concept 3 is campaign DNA, not a template and not a skyline to copy. "
                            "Each concept needs visual_idea and creative_brief for an image artist. "
                            "Required copy only: " + " / ".join(CAMPAIGN_COPY) + ". "
                            'JSON {"concepts":[{"id":"A","visual_idea":"","creative_brief":""}, ...]} exactly three.'
                        ),
                        _text("REAL Day_007 photograph:"),
                        _img(photo, quality=78),
                        _text("REAL Temple logo:"),
                        _img(logo, quality=88),
                        _text("Approved Concept 3 campaign DNA:"),
                        _img(concept3, quality=78),
                    ],
                },
            ],
        }
    )
    raw = parsed.get("concepts") if isinstance(parsed.get("concepts"), list) else []
    briefs = []
    fallback = (
        "Create a sophisticated premium architectural campaign composition inspired by Concept 3 art direction. "
        "Use the real project photograph as photographic truth. Feel art-directed across the entire canvas."
    )
    for i, sid in enumerate(CANDIDATE_IDS):
        data = dict(raw[i]) if i < len(raw) and isinstance(raw[i], dict) else {}
        briefs.append(
            {
                "id": sid,
                "visual_idea": str(data.get("visual_idea") or data.get("idea") or f"Independent campaign idea {sid}").strip(),
                "creative_brief": str(data.get("creative_brief") or data.get("brief") or "").strip() or fallback,
            }
        )
    return briefs, calls


def generate_visual_master(
    *,
    photo: Image.Image,
    logo: Image.Image,
    concept3: Image.Image,
    brief: dict[str, Any],
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        return {"ok": False, "reason": avail.reason, "image_calls": 0}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    images = [
        (_png_bytes(photo), "day007-project-photo.png", "image/png"),
        (_png_bytes(logo.convert("RGB")), "temple-logo.png", "image/png"),
        (_jpeg_bytes(concept3, 86), "concept3-campaign-dna.jpg", "image/jpeg"),
    ]
    try:
        remote = edit_image(
            api_key=openai_api_key(),
            model=model,
            prompt=artist_prompt(brief),
            images=images,
            size="1088x1360",
            quality="high",
            base_url=resolve_base_url(settings),
            variant=f"phase7_0_candidate_{brief.get('id')}",
            timeout=300.0,
        )
        image = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        return {"ok": True, "image": image, "image_calls": 1, "model": model, "method": PRIMARY_CREATIVE_ENGINE}
    except GptImageProviderError as exc:
        return {
            "ok": False,
            "reason": str(exc.detail)[:240],
            "image_calls": 1,
            "model": model,
            "method": PRIMARY_CREATIVE_ENGINE,
        }


def request_visual_critic(
    *,
    concept3: Image.Image,
    day007: Image.Image,
    candidates: dict[str, Image.Image],
) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "You are a senior advertising critic seeing these images for the first time. "
            "Concept 3 is campaign-quality DNA, not a skyline to match. "
            "Architecture fidelity is whether the REAL Day_007 building is intact — not invented DC landmarks. "
            "Do not inflate. Do not use occupancy as quality. Score each candidate 0-10: "
            + ", ".join(CRITIC_KEYS)
            + '. JSON {"A": {...}, "B": {...}, "C": {...}, "ranking": ["A","B","C"], "notes": ""}'
        ),
        _text("Concept 3 campaign DNA:"),
        _img(concept3, quality=78),
        _text("Real Day_007 architectural ground truth:"),
        _img(day007, quality=72),
    ]
    for sid in CANDIDATE_IDS:
        content.append(_text(f"CANDIDATE {sid}"))
        content.append(_img(candidates[sid], quality=82))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    blocks = {}
    for sid in CANDIDATE_IDS:
        scores = _scores(parsed.get(sid))
        blocks[sid] = {
            "scores": scores,
            "average": _avg(scores),
            "architecture_fidelity": scores.get("architecture_fidelity", 0),
        }
    ranking = parsed.get("ranking") if isinstance(parsed.get("ranking"), list) else []
    ranking = [str(v).strip().upper() for v in ranking if str(v).strip().upper() in CANDIDATE_IDS]
    return {
        "schema": "Phase70VisualCriticV1",
        "candidates": blocks,
        "ranking": ranking,
        "notes": str(parsed.get("notes") or ""),
        "vision_model": VISION_MODEL,
    }, calls


def request_semantic_dna(candidate: Image.Image, concept3: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Record semantic understanding of a campaign visual. Not a scene graph. JSON only.",
                },
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Describe territories as approximate 0-1 boxes if visible, relationships, and creative DNA. "
                            "Do not describe every pixel. JSON with territories, relationships, creative_dna."
                        ),
                        _text("CANDIDATE"),
                        _img(candidate, quality=80),
                        _text("Concept 3 DNA reference"),
                        _img(concept3, quality=60),
                    ],
                },
            ],
        }
    )
    return parsed if isinstance(parsed, dict) else {}, calls


def _pick_recommended(critic: dict[str, Any]) -> str:
    blocks = critic.get("candidates") or {}

    def rank(sid: str) -> tuple[float, float, float]:
        block = blocks.get(sid) or {}
        scores = block.get("scores") or {}
        arch = float(block.get("architecture_fidelity") or scores.get("architecture_fidelity") or 0)
        avg = float(block.get("average") or 0)
        return (arch, avg, float(scores.get("agency_campaign_feel") or 0))

    return max(CANDIDATE_IDS, key=rank)


def _triple(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    x = 28
    for label, image in tiles[:3]:
        tile = image.copy()
        tile.thumbnail((600, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 910), label[:42], font=_font(16), fill=(226, 222, 214))
        x += 630
    return canvas


def _quad(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (2200, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    x = 28
    for label, image in tiles[:4]:
        tile = image.copy()
        tile.thumbnail((510, 980), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1050), label[:42], font=_font(16), fill=(226, 222, 214))
        x += 534
    return canvas


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c"] = preserved.get("human_master")
    blob["human_approved_master_55c_id"] = preserved.get("human_master_id")
    blob["new_premium_master_58_tests"] = preserved.get("quality58")
    blob["ai_draft_structured_master_59_tests"] = preserved.get("quality59")
    blob["pure_creative_director_60_tests"] = preserved.get("quality60")
    blob["concept3_production_master_61_tests"] = preserved.get("quality61")
    blob["concept3_r1_61_tests"] = preserved.get("quality61r1")
    blob["real_photo_native_62_tests"] = preserved.get("quality62")
    blob["renderer_capability_63_tests"] = preserved.get("quality63")
    blob["chromium_craft_63a_tests"] = preserved.get("quality63a")
    blob["integrated_craft_63b_tests"] = preserved.get("quality63b")
    blob["ai_native_authoring_64_tests"] = preserved.get("quality64")


def generate_phase7_0_production_reset(
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

    concept3 = load_approved_concept3(db)
    if concept3.size != CANVAS_4X5:
        concept3 = ImageOps.fit(concept3, CANVAS_4X5, method=Image.Resampling.LANCZOS)
    source = load_day007(db)
    photo, transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.68, 0.20))
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    logo_board = _logo_board(logo_rgba) if logo_rgba is not None else Image.new("RGB", (720, 420), (16, 18, 22))

    briefs, n = request_three_briefs(photo=photo, logo=logo_board, concept3=concept3)
    vision_calls += n

    candidates: dict[str, dict[str, Any]] = {}
    renders: dict[str, Image.Image] = {}
    missing = _text_board("CANDIDATE MISSING", ["Visual master generation failed."], size=CANVAS_4X5)
    for brief in briefs:
        sid = brief["id"]
        pack = generate_visual_master(photo=photo, logo=logo_board, concept3=concept3, brief=brief)
        image = pack.get("image") if pack.get("ok") else None
        asset_id = None
        if isinstance(image, Image.Image):
            stored = persist_gpt_image(
                db,
                actor=user,
                linked_project_id=row.linked_project_id,
                content=_png(image),
                content_type="image/png",
                campaign_mode=f"project-v3-70-candidate-{sid.lower()}",
                session_id=str(uuid4()),
                provider_generation_id=None,
                campaign_context_id=str(row.id),
                brief_excerpt=f"PHASE 7.0 visual master candidate {sid} — not promoted",
            )
            asset_id = str(stored.id)
            renders[sid] = image
        else:
            renders[sid] = missing
        candidates[sid] = {
            **brief,
            "ok": bool(pack.get("ok")),
            "reason": pack.get("reason"),
            "asset_id": asset_id,
            "method": pack.get("method") or PRIMARY_CREATIVE_ENGINE,
            "model": pack.get("model"),
            "photo_transform": transform,
        }

    if provider_call_count() > MAX_IMAGE_CALLS:
        raise RuntimeError("Phase 7.0 exceeded the image-model budget")

    critic, n = request_visual_critic(concept3=concept3, day007=photo, candidates=renders)
    vision_calls += n
    for sid in CANDIDATE_IDS:
        block = critic["candidates"][sid]
        candidates[sid]["scores"] = block["scores"]
        candidates[sid]["average"] = block["average"]
        candidates[sid]["architecture_fidelity"] = block["architecture_fidelity"]

    recommended = _pick_recommended(critic)
    spec = empty_semantic_spec(master_id=None, visual_asset_id=candidates[recommended].get("asset_id"))
    dna, n = request_semantic_dna(renders[recommended], concept3)
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
    spec["recommended_candidate"] = recommended
    spec["status"] = "PASS" if candidates[recommended].get("ok") else "FAIL"

    rev = semantic_revision_contract()
    fmt = format_adaptation_spec()
    doctrine = production_doctrine()
    status = (
        "CANDIDATES_PENDING_HUMAN_REVIEW"
        if any(candidates[s].get("ok") for s in CANDIDATE_IDS)
        else "VISUAL_MASTER_GENERATION_FAILED"
    )

    images = {
        "doctrine": _text_board(
            "01  PRODUCTION DOCTRINE",
            [
                PRODUCTION_DOCTRINE,
                "QUALITY FIRST. Visual master + semantic spec + controlled revision.",
                "User sees only natural language.",
                "Full pixel editability is not required.",
                f"Retired research: {', '.join(RETIRED_RESEARCH_BRANCHES)}",
                "No Phase 6.5. No V4/V5 as primary engine. No Chromium reconstruction.",
            ],
        ),
        "flow": _text_board(
            "02  ARCHITECTURE FLOW",
            [
                "USER REQUEST → CREATIVE DIRECTOR → AI VISUAL MASTER",
                "→ SEMANTIC DESIGN SPEC → MASTER LOCK",
                "→ CONTROLLED REVISION ENGINE → FORMAT ADAPTATION ENGINE",
                f"engine {PRIMARY_CREATIVE_ENGINE}",
                f"master {MASTER_TYPE}",
            ],
        ),
        "spec": _text_board(
            "03  SEMANTIC CREATIVE SPEC V1",
            [
                f"candidate {recommended}",
                f"visual {spec.get('approved_visual_asset')}",
                f"photo {DAY007_ASSET_ID}",
                f"logo {LOCKED_LOGO_ASSET_ID}",
                *[f"{k}: {v}" for k, v in (spec.get("semantic_copy") or {}).items()],
                "pixel-complete scene graph: NO",
            ],
        ),
        "revision": _text_board(
            "04  SEMANTIC REVISION CONTRACT",
            [
                f"PRICE_EDIT_ONLY {(rev.get('PRICE_EDIT_ONLY') or {}).get('status')}",
                f"COPY_EDIT_ONLY {(rev.get('COPY_EDIT_ONLY') or {}).get('status')}",
                f"VISUAL_REPLACE_ONLY {(rev.get('VISUAL_REPLACE_ONLY') or {}).get('status')}",
                "Low confidence → review candidate. Do not silently redesign.",
            ],
        ),
        "format": _text_board(
            "05  FORMAT ADAPTATION SPEC  —  not implemented",
            [f"{k}: {v}" for k, v in (fmt.get("formats") or {}).items()]
            + ["intelligent recomposition, not crop/stretch/resize"],
        ),
        "A": renders["A"],
        "B": renders["B"],
        "C": renders["C"],
        "compare": _triple(
            "09  FINAL CANDIDATE COMPARISON",
            [("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])],
        ),
        "review": _quad(
            "10  HUMAN REVIEW BOARD",
            [
                ("CONCEPT 3 DNA", concept3),
                ("CANDIDATE A", renders["A"]),
                ("CANDIDATE B", renders["B"]),
                ("CANDIDATE C", renders["C"]),
            ],
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_70,
        "created_at": _now(),
        "status": status,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "primary_creative_engine": PRIMARY_CREATIVE_ENGINE,
        "master_type": MASTER_TYPE,
        "semantic_spec_status": spec.get("status"),
        "price_revision_contract": (rev.get("PRICE_EDIT_ONLY") or {}).get("status"),
        "copy_revision_contract": (rev.get("COPY_EDIT_ONLY") or {}).get("status"),
        "visual_replace_contract": (rev.get("VISUAL_REPLACE_ONLY") or {}).get("status"),
        "format_adaptation_spec": fmt.get("status"),
        "candidates": {
            sid: {
                "ok": candidates[sid].get("ok"),
                "asset_id": candidates[sid].get("asset_id"),
                "scores": candidates[sid].get("scores"),
                "average": candidates[sid].get("average"),
                "architecture_fidelity": candidates[sid].get("architecture_fidelity"),
                "visual_idea": candidates[sid].get("visual_idea"),
            }
            for sid in CANDIDATE_IDS
        },
        "visual_critic": critic,
        "recommended_human_review_candidate": recommended,
        "semantic_creative_spec": spec,
        "semantic_revision_contract": rev,
        "format_adaptation_spec_payload": fmt,
        "production_doctrine_payload": doctrine,
        "research_branches_retired": list(RETIRED_RESEARCH_BRANCHES),
        "image_model_calls": provider_call_count(),
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
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "day007_asset_id": DAY007_ASSET_ID,
        "gold_standard": CONCEPT3_ASSET_ID,
        "language": language,
        "next_decision": "HUMAN VISUAL REVIEW",
    }
    tests = list(blob.get("production_architecture_70_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["production_architecture_70_tests"] = tests
    _restore_history(blob, preserved)
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 7.0 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
