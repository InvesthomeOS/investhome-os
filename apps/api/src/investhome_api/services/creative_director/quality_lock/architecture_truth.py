"""Architectural Truth Lock — architecture is verified fact, never invented.

Uses existing Drive/ML metadata (visual_subject, folder_category, filename, tags,
provenance). Does not invent a parallel media taxonomy.
"""

from __future__ import annotations

from typing import Any

from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate

# Canonical classifications (derived from existing metadata — not a new DB system).
ASSET_CLASSIFICATIONS = (
    "EXTERIOR_APPROVED",
    "EXTERIOR_HISTORIC",
    "EXTERIOR_ADDITION",
    "EXTERIOR_HISTORIC_PLUS_ADDITION",
    "INTERIOR_APPROVED",
    "FLOORPLAN",
    "LOCATION",
    "NEIGHBORHOOD",
    "LIFESTYLE",
    "LOGO_PRIMARY",
    "LOGO_WHITE",
    "LOGO_DARK",
    "UNCLASSIFIED",
)

# Exterior options A/B/C/D for location/architecture — approved project architecture only.
APPROVED_EXTERIOR_OPTIONS = (
    "EXTERIOR_APPROVED",
    "EXTERIOR_HISTORIC",
    "EXTERIOR_ADDITION",
    "EXTERIOR_HISTORIC_PLUS_ADDITION",
)

ARCHITECTURE_LOCKED_CLASSIFICATIONS = frozenset(
    {
        "EXTERIOR_APPROVED",
        "EXTERIOR_HISTORIC",
        "EXTERIOR_ADDITION",
        "EXTERIOR_HISTORIC_PLUS_ADDITION",
        "INTERIOR_APPROVED",
    }
)

# Freedom levels: 0 = STRICT exterior, 1 = controlled interior, 2 = creative lifestyle/place
CREATIVE_FREEDOM_STRICT = 0
CREATIVE_FREEDOM_CONTROLLED = 1
CREATIVE_FREEDOM_CREATIVE = 2

_HISTORIC_TOKENS = (
    "historic",
    "historical",
    "heritage",
    "chapel",
    "façade historic",
    "historic facade",
    "tarihi",
)
_ADDITION_TOKENS = (
    "addition",
    "extension",
    "new wing",
    "modern wing",
    "ek bina",
    "ekleme",
    "historic_plus",
    "historic-plus",
    "historic+",
)
_NEIGHBOR_TOKENS = (
    "neighbor",
    "neighbour",
    "adjacent",
    "next door",
    "streetscape",
    "context only",
)
WORKSPACE_SCREENSHOT_TOKENS = (
    "screencapture",
    "localhost",
    "127.0.0.1",
    "ai-chat",
    "workspaces-creative-studio",
)


def is_workspace_screenshot(hay: str | None) -> bool:
    """UI/localhost captures are never approved project architecture."""
    blob = (hay or "").lower()
    return any(tok in blob for tok in WORKSPACE_SCREENSHOT_TOKENS)
_LOCATION_TOKENS = (
    "neighborhood",
    "neighbourhood",
    "adams",
    "morgan",
    "streetscape",
    "location",
    "district",
    "lokasyon",
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _haystack_from_parts(
    *,
    filename: str | None = None,
    folder_category: str | None = None,
    visual_subject: str | None = None,
    tags: list[str] | None = None,
    selection_reason: str | None = None,
    role: str | None = None,
) -> str:
    return " ".join(
        [
            filename or "",
            folder_category or "",
            visual_subject or "",
            " ".join(tags or []),
            selection_reason or "",
            role or "",
        ]
    ).lower()


def _haystack_candidate(cand: SocialDesignMediaCandidate) -> str:
    return _haystack_from_parts(
        filename=cand.filename,
        folder_category=cand.folder_category,
        visual_subject=cand.visual_subject,
        tags=list(cand.tags or []),
    )


def _haystack_meta(meta: dict[str, Any]) -> str:
    return _haystack_from_parts(
        filename=str(meta.get("filename") or ""),
        folder_category=str(meta.get("folder_category") or ""),
        visual_subject=str(meta.get("visual_subject") or ""),
        tags=[str(t) for t in (meta.get("tags") or [])],
        selection_reason=str(meta.get("selection_reason") or ""),
        role=str(meta.get("role") or ""),
    )


def _is_drive_backed(provenance: str | None, source_type: str | None = None) -> bool:
    blob = f"{provenance or ''} {source_type or ''}".lower()
    return "drive" in blob or "google" in blob or "media_library" in blob or "upload" in blob


def classify_architecture_asset(
    *,
    filename: str | None = None,
    folder_category: str | None = None,
    visual_subject: str | None = None,
    tags: list[str] | None = None,
    role: str | None = None,
    provenance_source: str | None = None,
) -> str:
    """Map existing metadata → architectural truth classification."""
    subject = (visual_subject or "").upper().strip()
    hay = _haystack_from_parts(
        filename=filename,
        folder_category=folder_category,
        visual_subject=visual_subject,
        tags=tags,
        role=role,
    )
    role_l = (role or "").lower()

    if subject == "BRANDING" or "logo" in hay or role_l in {
        "project_logo",
        "logo",
        "investhome_logo",
        "brand_logo",
    }:
        if any(k in hay for k in ("white", "light", "reversed")):
            return "LOGO_WHITE"
        if any(k in hay for k in ("dark", "black", "navy")):
            return "LOGO_DARK"
        return "LOGO_PRIMARY"

    if subject == "FLOOR_PLAN" or "floorplan" in hay or "floor_plan" in hay:
        return "FLOORPLAN"

    # Prefer explicit visual_subject before folder heuristics (02_RENDER contains "render").
    if subject == "INTERIOR":
        return "INTERIOR_APPROVED"
    if subject == "NEIGHBORHOOD":
        return "NEIGHBORHOOD"
    if subject == "LOCATION":
        return "LOCATION"
    if subject == "AMENITY":
        return "LIFESTYLE"

    has_historic = any(t in hay for t in _HISTORIC_TOKENS)
    has_addition = any(t in hay for t in _ADDITION_TOKENS)
    is_exterior_family = subject in {
        "EXTERIOR",
        "AERIAL",
        "ARCHITECTURAL_RENDER",
    } or any(
        k in hay
        for k in (
            "exterior",
            "facade",
            "façade",
            "cephe",
            "massing",
            "roofline",
            "elevation",
        )
    )
    # "render" alone is too weak (folder 02_RENDER); require exterior cues or subject.
    if subject == "ARCHITECTURAL_RENDER" or (
        "render" in hay and any(k in hay for k in ("exterior", "facade", "façade", "street", "building"))
    ):
        is_exterior_family = True

    if is_exterior_family or (has_historic and has_addition):
        if has_historic and has_addition:
            return "EXTERIOR_HISTORIC_PLUS_ADDITION"
        if has_addition:
            return "EXTERIOR_ADDITION"
        if has_historic:
            return "EXTERIOR_HISTORIC"
        if subject in {"EXTERIOR", "AERIAL", "ARCHITECTURAL_RENDER"} or is_exterior_family:
            return "EXTERIOR_APPROVED"

    if any(t in hay for t in ("neighborhood", "streetscape")) and not is_exterior_family:
        return "NEIGHBORHOOD"

    if any(t in hay for t in _LOCATION_TOKENS) and not is_exterior_family:
        return "LOCATION"

    if any(
        k in hay for k in ("interior", "living", "bedroom", "kitchen", "lobby", "suite", "oturma")
    ):
        return "INTERIOR_APPROVED"

    if any(k in hay for k in ("amenity", "lifestyle", "rooftop", "spa")):
        return "LIFESTYLE"

    return "UNCLASSIFIED"


def classify_candidate(cand: SocialDesignMediaCandidate, *, role: str | None = None) -> str:
    return classify_architecture_asset(
        filename=cand.filename,
        folder_category=cand.folder_category,
        visual_subject=cand.visual_subject,
        tags=list(cand.tags or []),
        role=role,
        provenance_source=cand.provenance_source,
    )


def classify_meta(meta: dict[str, Any]) -> str:
    return classify_architecture_asset(
        filename=str(meta.get("filename") or "") or None,
        folder_category=str(meta.get("folder_category") or "") or None,
        visual_subject=str(meta.get("visual_subject") or "") or None,
        tags=[str(t) for t in (meta.get("tags") or [])],
        role=str(meta.get("role") or "") or None,
        provenance_source=str(meta.get("provenance_source") or "") or None,
    )


def is_architecture_locked(classification: str) -> bool:
    return classification in ARCHITECTURE_LOCKED_CLASSIFICATIONS


def creative_freedom_level_for(classification: str) -> int:
    if classification in APPROVED_EXTERIOR_OPTIONS:
        return CREATIVE_FREEDOM_STRICT
    if classification == "INTERIOR_APPROVED":
        return CREATIVE_FREEDOM_CONTROLLED
    if classification in {"LOCATION", "NEIGHBORHOOD", "LIFESTYLE"}:
        return CREATIVE_FREEDOM_CREATIVE
    if classification.startswith("LOGO"):
        return CREATIVE_FREEDOM_STRICT
    if classification == "FLOORPLAN":
        return CREATIVE_FREEDOM_STRICT
    return CREATIVE_FREEDOM_CONTROLLED


def is_approved_project_asset(
    *,
    provenance_source: str | None = None,
    source_type: str | None = None,
    asset_id: str | None = None,
    classification: str | None = None,
) -> bool:
    """Approved = real project-linked media with traceable ID (Drive/ML/upload)."""
    if not asset_id:
        return False
    if classification in {"UNCLASSIFIED", "FLOORPLAN"}:
        return False
    return _is_drive_backed(provenance_source, source_type) or bool(asset_id)


def looks_like_neighbor_as_project(hay: str) -> bool:
    return any(t in hay for t in _NEIGHBOR_TOKENS) and any(
        t in hay for t in ("project", "temple", "hero", "primary")
    )


def annotate_asset_truth(
    meta: dict[str, Any],
    *,
    project_relation: str | None = None,
) -> dict[str, Any]:
    """Attach architectural truth fields onto a selected-asset dict (in place + return)."""
    out = dict(meta)
    classification = classify_meta(out)
    locked = is_architecture_locked(classification)
    freedom = creative_freedom_level_for(classification)
    approved = is_approved_project_asset(
        provenance_source=str(out.get("provenance_source") or "") or None,
        source_type=str(out.get("source_type") or "") or None,
        asset_id=str(out.get("asset_id") or out.get("id") or "") or None,
        classification=classification,
    )
    role = str(out.get("role") or "").strip().lower()
    existing = str(out.get("project_relation") or "").strip()
    brand_roles = {"city_visual", "investhome_logo", "brand_logo"}
    brand_relations = {"brand_independent", "place_not_project"}
    if role in brand_roles or existing in brand_relations:
        relation = "brand_independent"
    elif project_relation:
        relation = project_relation
    elif existing:
        relation = existing
    else:
        relation = "project_primary"
    if role in brand_roles:
        relation = "brand_independent"
    out["classification"] = classification
    out["architecture_locked"] = locked
    out["creative_freedom_level"] = freedom
    out["project_relation"] = relation
    out["approved"] = approved
    out["approved_status"] = "approved" if approved else "unapproved"
    return out


def freedom_prompt_text(level: int) -> str:
    if level <= CREATIVE_FREEDOM_STRICT:
        return (
            "LEVEL 0 STRICT — Exterior/architecture locked. Allowed: crop, position, typography, "
            "gradient overlays, controlled color treatment, CTA, graphics. FORBIDDEN: regenerate, "
            "redesign, invent, extend, remove, or reinterpret buildings/facades/Addition/massing."
        )
    if level == CREATIVE_FREEDOM_CONTROLLED:
        return (
            "LEVEL 1 CONTROLLED — Approved interior. Preserve room geometry, windows, materials, "
            "and furniture layout. Atmosphere/grade/typography only — do not invent another room."
        )
    return (
        "LEVEL 2 CREATIVE — Generic lifestyle / place imagery. Do not invent project architectural "
        "facts, Historic+Addition relationships, or present neighbor buildings as The Temple."
    )


def architecture_lock_prompt_block(asset_meta: dict[str, Any]) -> list[str]:
    """Provider-facing immutable architecture instructions."""
    meta = annotate_asset_truth(asset_meta)
    classification = str(meta.get("classification") or "UNCLASSIFIED")
    locked = bool(meta.get("architecture_locked"))
    freedom = int(meta.get("creative_freedom_level") or CREATIVE_FREEDOM_CONTROLLED)
    lines = [
        "ARCHITECTURAL TRUTH LOCK (mandatory — architecture is verified fact):",
        f"- Source asset_id: {meta.get('asset_id')}",
        f"- Filename: {meta.get('filename')}",
        f"- Classification: {classification}",
        f"- architecture_locked: {locked}",
        f"- creative_freedom_level: {freedom}",
        f"- project_relation: {meta.get('project_relation')}",
        f"- approved_status: {meta.get('approved_status')}",
        f"- {freedom_prompt_text(freedom)}",
    ]
    if locked:
        lines.extend(
            [
                "- Use the supplied architecture photograph EXACTLY as visual truth.",
                "- Do NOT redesign, regenerate, replace, extend, remove, or reinterpret buildings.",
                "- Do NOT invent or relocate The Temple Addition; Historic+Addition spatial "
                "relationship only from this approved asset.",
                "- Do NOT treat a neighbor building as project architecture.",
                "- Prefer edit/composition that preserves source pixels of the building fabric.",
            ]
        )
    else:
        lines.extend(
            [
                "- This source is NOT an architecture-locked project exterior.",
                "- Do NOT invent The Temple exterior, facade, or Addition from this image.",
            ]
        )
    return lines


def pick_truthful_hero_for_intent(
    candidates: list[SocialDesignMediaCandidate],
    *,
    campaign_intent: str,
    require_historic_plus_addition: bool = False,
) -> tuple[SocialDesignMediaCandidate | None, str | None, dict[str, Any]]:
    """Select hero under architectural truth rules (fail-closed metadata in report).

    Location / architecture must never invent exteriors. Prefer approved exterior
    options A/B/C/D, else LOCATION/NEIGHBORHOOD, else INTERIOR — never fake architecture.
    """
    intent = str(campaign_intent or "").strip().lower()
    report: dict[str, Any] = {
        "intent": intent,
        "require_historic_plus_addition": require_historic_plus_addition,
        "candidates_reviewed": len(candidates),
        "approved_exterior_options": [],
        "fallback_pool": [],
        "selected": None,
        "status": "pending",
        "fail_closed": False,
        "message": None,
    }

    classified: list[tuple[SocialDesignMediaCandidate, str]] = []
    for cand in candidates:
        ctype = (cand.content_type or "").lower()
        if ctype == "image/svg+xml" or not ctype.startswith("image/"):
            continue
        if is_workspace_screenshot(_haystack_candidate(cand)):
            continue
        classification = classify_candidate(cand)
        if classification == "FLOORPLAN" or classification.startswith("LOGO"):
            continue
        classified.append((cand, classification))
        if classification in APPROVED_EXTERIOR_OPTIONS:
            report["approved_exterior_options"].append(
                {
                    "asset_id": str(cand.asset_id),
                    "filename": cand.filename,
                    "classification": classification,
                }
            )

    if require_historic_plus_addition:
        hpa = [
            (c, cl)
            for c, cl in classified
            if cl == "EXTERIOR_HISTORIC_PLUS_ADDITION"
        ]
        if not hpa:
            report["status"] = "fail_closed"
            report["fail_closed"] = True
            report["message"] = (
                "Approved Historic+Addition exterior render missing. "
                "Cannot invent The Temple Addition — FAIL CLOSED."
            )
            return None, report["message"], report
        best = hpa[0][0]
        report["selected"] = {
            "asset_id": str(best.asset_id),
            "filename": best.filename,
            "classification": "EXTERIOR_HISTORIC_PLUS_ADDITION",
        }
        report["status"] = "pass"
        return best, "historic_plus_addition_approved", report

    exterior_need = intent in {"architecture", "project_brand", "investment"}
    location_intent = intent == "location"

    # Option pools in priority order for exterior-sensitive intents
    pools: list[tuple[str, tuple[str, ...]]] = []
    if exterior_need or location_intent:
        pools.append(("approved_exterior", APPROVED_EXTERIOR_OPTIONS))
        pools.append(("place", ("LOCATION", "NEIGHBORHOOD")))
        if location_intent:
            pools.append(("interior_fallback", ("INTERIOR_APPROVED", "LIFESTYLE")))
    elif intent in {"lifestyle", "amenities"}:
        pools.append(("interior", ("INTERIOR_APPROVED", "LIFESTYLE")))
        pools.append(("place", ("LOCATION", "NEIGHBORHOOD")))
    else:
        pools.append(("interior", ("INTERIOR_APPROVED", "LIFESTYLE")))
        pools.append(("approved_exterior", APPROVED_EXTERIOR_OPTIONS))
        pools.append(("place", ("LOCATION", "NEIGHBORHOOD")))

    for pool_name, allowed in pools:
        matches = [(c, cl) for c, cl in classified if cl in allowed]
        report["fallback_pool"].append({"pool": pool_name, "count": len(matches)})
        if not matches:
            continue
        # Prefer drive-backed + higher existing score
        matches.sort(
            key=lambda row: (
                0 if _is_drive_backed(row[0].provenance_source, row[0].source_type) else 1,
                # Prefer more specific exterior classifications within the pool
                {
                    "EXTERIOR_HISTORIC_PLUS_ADDITION": 0,
                    "EXTERIOR_HISTORIC": 1,
                    "EXTERIOR_ADDITION": 2,
                    "EXTERIOR_APPROVED": 3,
                    "LOCATION": 4,
                    "NEIGHBORHOOD": 5,
                    "INTERIOR_APPROVED": 6,
                    "LIFESTYLE": 7,
                }.get(row[1], 9),
                -(float(row[0].score or 0.0)),
                (row[0].filename or "").lower(),
            )
        )
        best, cl = matches[0]
        # Reject neighbor-as-project exteriors
        if cl in APPROVED_EXTERIOR_OPTIONS and looks_like_neighbor_as_project(
            _haystack_candidate(best)
        ):
            continue
        report["selected"] = {
            "asset_id": str(best.asset_id),
            "filename": best.filename,
            "classification": cl,
            "pool": pool_name,
        }
        report["status"] = "pass"
        return best, f"truth_pool={pool_name}; classification={cl}", report

    if exterior_need:
        report["status"] = "fail_closed"
        report["fail_closed"] = True
        report["message"] = (
            "No approved exterior / neighborhood / interior asset available. "
            "Fake architecture fallback FORBIDDEN — FAIL CLOSED."
        )
        return None, report["message"], report

    report["status"] = "fail_closed"
    report["fail_closed"] = True
    report["message"] = (
        "No approved project visual found for this intent. "
        "Cannot invent architecture or interiors — FAIL CLOSED."
    )
    return None, report["message"], report


def architecture_truth_guard(
    *,
    hero_meta: dict[str, Any],
    source_asset_id: str | None,
    campaign_intent: str | None = None,
    require_historic_plus_addition: bool = False,
    allow_publish_without_lock: bool = False,
) -> dict[str, Any]:
    """Fail-closed acceptance guard before publishing a finished-ad.

    Checks: approved source exists, source ID traceable, architecture_locked respected,
    no unapproved exterior as project truth, Historic+Addition not invented.
    """
    meta = annotate_asset_truth(_as_dict(hero_meta))
    classification = str(meta.get("classification") or "UNCLASSIFIED")
    locked = bool(meta.get("architecture_locked"))
    raw_freedom = meta.get("creative_freedom_level")
    freedom = (
        int(raw_freedom)
        if raw_freedom is not None
        else creative_freedom_level_for(classification)
    )
    asset_id = str(meta.get("asset_id") or meta.get("id") or "").strip() or None
    approved = bool(meta.get("approved"))
    intent = str(campaign_intent or "").strip().lower()

    failures: list[str] = []
    checks: dict[str, bool] = {}

    checks["approved_source_exists"] = bool(asset_id) and approved
    if not checks["approved_source_exists"]:
        failures.append("missing_or_unapproved_source")

    checks["source_id_traceable"] = bool(source_asset_id) and (
        not asset_id or str(source_asset_id) == str(asset_id)
    )
    if not checks["source_id_traceable"]:
        failures.append("source_id_not_traceable")

    checks["architecture_locked_respected"] = True
    if locked and not approved:
        checks["architecture_locked_respected"] = False
        failures.append("architecture_lock_without_approval")

    # Unapproved exterior must never become project architectural truth
    checks["no_unapproved_exterior"] = True
    if classification in APPROVED_EXTERIOR_OPTIONS and not approved:
        checks["no_unapproved_exterior"] = False
        failures.append("unapproved_exterior_as_project_truth")

    checks["no_generated_architecture_as_truth"] = classification != "UNCLASSIFIED" or intent not in {
        "architecture",
        "location",
        "project_brand",
    }
    if classification == "UNCLASSIFIED" and intent in {"architecture", "location", "project_brand"}:
        checks["no_generated_architecture_as_truth"] = False
        failures.append("unclassified_architecture_source")

    checks["historic_addition_not_invented"] = True
    if require_historic_plus_addition:
        if classification != "EXTERIOR_HISTORIC_PLUS_ADDITION":
            checks["historic_addition_not_invented"] = False
            failures.append("historic_addition_missing_or_invented")

    if looks_like_neighbor_as_project(_haystack_meta(meta)):
        checks["no_neighbor_as_project"] = False
        failures.append("neighbor_treated_as_project")
    else:
        checks["no_neighbor_as_project"] = True

    hay = _haystack_meta(meta)
    checks["not_workspace_screenshot"] = not is_workspace_screenshot(hay)
    if not checks["not_workspace_screenshot"]:
        failures.append("workspace_screenshot_not_project_visual")

    fail_closed = bool(failures) and not allow_publish_without_lock
    status_val = "fail" if fail_closed else ("pass" if not failures else "review")

    return {
        "status": status_val,
        "fail_closed": fail_closed,
        "checks": checks,
        "failures": failures,
        "asset_id": asset_id,
        "filename": meta.get("filename"),
        "classification": classification,
        "architecture_locked": locked,
        "creative_freedom_level": freedom,
        "project_relation": meta.get("project_relation"),
        "approved_status": meta.get("approved_status"),
        "source_used_asset_id": source_asset_id,
        "campaign_intent": intent or None,
        "message": (
            "; ".join(failures)
            if failures
            else "Architectural truth established from approved project asset."
        ),
        "note": "User visual approval required — do not declare Visual Quality PASS.",
    }
