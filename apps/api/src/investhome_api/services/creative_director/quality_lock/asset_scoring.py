"""Intent-aware Drive/ML asset scoring for Creative Director Quality Lock."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
from investhome_api.services.creative_director.quality_lock.architecture_truth import (
    is_workspace_screenshot,
)
from investhome_api.services.creative_director.quality_lock.intent import intent_to_asset_preference
from investhome_api.services.social_design_engine.generation import AssetPreference, asset_preference_tokens
from investhome_api.services.social_design_engine.media import pick_best_asset

# Subject families preferred per CD intent: (keyword_tuple, weight)
_INTENT_SUBJECT_BONUS: dict[str, tuple[tuple[tuple[str, ...], float], ...]] = {
    "location": (
        (("neighborhood", "street", "streetscape", "aerial", "drone", "location", "exterior", "context"), 10.0),
        (("facade", "façade", "building", "hero"), 6.0),
        (("interior", "living", "bedroom"), -6.0),
    ),
    "architecture": (
        (("exterior", "facade", "façade", "architectural", "detail", "cephe"), 10.0),
        (("aerial", "building"), 5.0),
        (("interior",), -2.0),
    ),
    "lifestyle": (
        (("living", "lounge", "interior", "salon", "oturma", "kitchen"), 10.0),
        (("amenity", "lobby", "rooftop"), 4.0),
        (("exterior", "aerial"), -3.0),
    ),
    "amenities": (
        (("amenity", "spa", "pool", "rooftop", "lobby", "gym", "fitness"), 10.0),
        (("interior", "living"), 5.0),
        (("exterior",), -1.0),
    ),
    "sales_offer": (
        (("living", "interior", "hero", "lobby"), 8.0),
        (("exterior", "premium"), 5.0),
    ),
    "price_campaign": (
        (("living", "interior", "hero", "lobby"), 8.0),
        (("exterior", "premium"), 5.0),
    ),
    "investment": (
        (("exterior", "hero", "building", "aerial", "facade"), 9.0),
        (("interior", "living"), 4.0),
    ),
    "launch": (
        (("living", "interior", "hero"), 7.0),
        (("exterior",), 5.0),
    ),
    "project_brand": (
        (("exterior", "hero", "building"), 8.0),
        (("interior",), 3.0),
    ),
    "general_awareness": (
        (("exterior", "hero", "living", "interior"), 5.0),
    ),
}

_ROOM_WEIGHTS: tuple[tuple[tuple[str, ...], float], ...] = (
    (("living", "lounge", "great.?room", "oturma", "salon"), 8.0),
    (("lobby", "lobby.?lounge", "reception", "atrium"), 7.0),
    (("kitchen", "mutfak", "dining"), 6.0),
    (("suite", "master", "bedroom", "yatak"), 3.5),
    (("bathroom", "bath", "banyo"), 1.0),
    (("corridor", "hallway", "closet", "detail"), 0.5),
)


def _haystack(cand: SocialDesignMediaCandidate) -> str:
    return " ".join(
        [
            cand.filename or "",
            cand.folder_category or "",
            cand.visual_subject or "",
            " ".join(cand.tags or []),
        ]
    ).lower()


def _is_interior(cand: SocialDesignMediaCandidate) -> bool:
    subject = (cand.visual_subject or "").upper()
    if subject == "INTERIOR":
        return True
    hay = _haystack(cand)
    return any(k in hay for k in ("interior", "living", "bedroom", "kitchen", "bathroom", "lobby", "suite"))


def _is_exterior_primary(cand: SocialDesignMediaCandidate) -> bool:
    subject = (cand.visual_subject or "").upper()
    return subject in {"EXTERIOR", "AERIAL", "NEIGHBORHOOD", "LOCATION"}


def _subject_family(cand: SocialDesignMediaCandidate) -> str:
    subject = (cand.visual_subject or "").upper()
    if subject in {"EXTERIOR", "AERIAL", "NEIGHBORHOOD", "LOCATION"}:
        return "exterior"
    if subject == "INTERIOR":
        return "interior"
    if subject == "BRANDING":
        return "branding"
    if subject == "FLOOR_PLAN":
        return "floor_plan"
    hay = _haystack(cand)
    if any(k in hay for k in ("amenity", "spa", "pool", "rooftop", "gym")):
        return "amenity"
    if _is_exterior_primary(cand):
        return "exterior"
    if _is_interior(cand):
        return "interior"
    return "other"


def _quality_composition_score(
    cand: SocialDesignMediaCandidate,
    *,
    brief: str,
    width: int | None,
    height: int | None,
) -> tuple[float, str]:
    reasons: list[str] = []
    score = 0.0
    hay = _haystack(cand)
    base = float(cand.score or 0.0)
    score += min(base, 12.0) * 0.35
    reasons.append(f"base_media={base:.2f}")

    ctype = (cand.content_type or "").lower()
    if ctype in {"image/jpeg", "image/jpg", "image/png", "image/webp"}:
        score += 3.0
        reasons.append("photo_render")
    elif ctype == "image/svg+xml":
        score -= 20.0
        reasons.append("svg_penalty")

    if width and height and width > 0 and height > 0:
        area = int(width) * int(height)
        if area >= 2_000_000:
            score += 5.0
            reasons.append("hi_res")
        elif area >= 1_000_000:
            score += 3.5
            reasons.append("good_res")
        elif area >= 400_000:
            score += 2.0
            reasons.append("ok_res")
        else:
            score -= 1.5
            reasons.append("low_res")
        aspect = width / height
        if 1.15 <= aspect <= 1.9:
            score += 3.0
            reasons.append("landscape_text_space")
        elif 0.85 <= aspect <= 1.15:
            score += 2.0
            reasons.append("square_editorial")
        elif aspect < 0.7:
            score -= 1.0
            reasons.append("tall_tight")
        if width >= 1600:
            score += 1.0
            reasons.append("neg_space_width")

    room_bonus = 0.0
    room_label = "generic"
    for keys, weight in _ROOM_WEIGHTS:
        if any(re.search(k, hay) for k in keys):
            room_bonus = weight
            room_label = keys[0]
            break
    else:
        if (cand.visual_subject or "").upper() == "INTERIOR":
            room_bonus = 4.0
            room_label = "interior_generic"
    score += room_bonus
    reasons.append(f"room={room_label}:{room_bonus}")

    brief_l = (brief or "").lower()
    if any(k in brief_l for k in ("tarihi", "historic", "modern", "şık", "sik", "karakter", "character")):
        if room_label in {"living", "lobby", "kitchen"}:
            score += 4.0
            reasons.append("brief_character_fit")

    prov = (cand.provenance_source or cand.source_type or "").lower()
    if "drive" in prov or "google" in prov:
        score += 1.5
        reasons.append("drive_provenance")

    return score, "; ".join(reasons)


def score_candidate_for_intent(
    cand: SocialDesignMediaCandidate,
    *,
    campaign_intent: str,
    brief: str = "",
    width: int | None = None,
    height: int | None = None,
    recent_asset_ids: set[str] | None = None,
) -> tuple[float, str]:
    """Score a real project media candidate for the given CD campaign intent."""
    intent = str(campaign_intent or "general_awareness").strip().lower()
    reasons: list[str] = []
    family = _subject_family(cand)

    if family in {"branding", "floor_plan"}:
        return -50.0, f"excluded_{family}"

    score, quality_reason = _quality_composition_score(
        cand, brief=brief, width=width, height=height
    )
    reasons.append(quality_reason)

    for keys, weight in _INTENT_SUBJECT_BONUS.get(intent, _INTENT_SUBJECT_BONUS["general_awareness"]):
        if any(k == family or k in _haystack(cand) for k in keys):
            score += weight
            reasons.append(f"intent_subject:{keys[0]}:{weight}")
            break

    pref: AssetPreference = intent_to_asset_preference(intent)
    tokens = asset_preference_tokens(pref)
    hay = _haystack(cand)
    token_hits = sum(1 for tok in tokens if tok in hay)
    if token_hits:
        score += min(token_hits, 4) * 1.5
        reasons.append(f"pref_tokens={token_hits}")

    if intent in {"sales_offer", "price_campaign", "launch"} and width and height and width > 0 and height > 0:
        if (width / height) >= 1.1:
            score += 2.5
            reasons.append("sales_text_placement")

    brief_l = (brief or "").lower()
    for token in ("adams", "morgan", "living", "lobby", "exterior", "facade", "amenity", "rooftop"):
        if token in brief_l and token in hay:
            score += 1.5
            reasons.append(f"brief_overlap:{token}")
            break

    recent = recent_asset_ids or set()
    aid = str(cand.asset_id)
    if aid in recent:
        score -= 2.5
        reasons.append("recent_repeat_soft_penalty")

    return score, "; ".join(reasons)


def pick_hero_asset_for_intent(
    candidates: list[SocialDesignMediaCandidate],
    *,
    campaign_intent: str,
    brief: str = "",
    dimensions: dict[UUID, tuple[int | None, int | None]] | None = None,
    recent_asset_ids: set[str] | None = None,
) -> tuple[SocialDesignMediaCandidate | None, float | None, str | None]:
    """Pick best real project hero visual for intent — never invent assets."""
    intent = str(campaign_intent or "general_awareness").strip().lower()
    dims = dimensions or {}
    ranked: list[tuple[float, str, SocialDesignMediaCandidate]] = []

    for cand in candidates:
        ctype = (cand.content_type or "").lower()
        if ctype == "image/svg+xml" or not ctype.startswith("image/"):
            continue
        if is_workspace_screenshot(_haystack(cand)):
            continue
        if _subject_family(cand) in {"branding", "floor_plan"}:
            continue
        w, h = dims.get(cand.asset_id, (None, None))
        s, reason = score_candidate_for_intent(
            cand,
            campaign_intent=intent,
            brief=brief,
            width=w,
            height=h,
            recent_asset_ids=recent_asset_ids,
        )
        ranked.append((s, reason, cand))

    if not ranked:
        interiors = [
            c
            for c in candidates
            if _is_interior(c)
            and not _is_exterior_primary(c)
            and not is_workspace_screenshot(_haystack(c))
        ]
        pool = interiors or [
            c
            for c in candidates
            if _subject_family(c) not in {"branding", "floor_plan"}
            and not is_workspace_screenshot(_haystack(c))
        ]
        picked_id = pick_best_asset(pool, require_image=True, campaign_type="LIFESTYLE")
        by_id = {c.asset_id: c for c in pool}
        if picked_id and picked_id in by_id:
            return by_id[picked_id], None, "fallback_pick_best_asset"
        return None, None, None

    ranked.sort(key=lambda row: (-row[0], (row[2].filename or "").lower()))
    best_score, best_reason, best = ranked[0]
    return best, best_score, f"intent={intent}; {best_reason}"


def selection_role_for_intent(campaign_intent: str) -> str:
    intent = str(campaign_intent or "").strip().lower()
    if intent in {"location", "architecture", "investment", "project_brand"}:
        return "hero_exterior"
    if intent in {"lifestyle", "amenities"}:
        return "hero_interior"
    return "hero"
