"""ProjectCreativeMasterLibraryV1 — curated project Masters, not live templates."""

from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, TEMPLE_PROJECT_ID, _now
from investhome_api.services.creative_director.phase6_1_concept3_compose import DAY007_ASSET_ID
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import PROJECT_CREATIVE_RULE, revision_readiness_72

LIBRARY_SCHEMA = "ProjectCreativeMasterLibraryV1"
MASTER_TYPES = (
    "PREMIUM_CAMPAIGN",
    "EDITORIAL",
    "COMMERCIAL",
    "MINIMAL",
    "SOCIAL",
    "STORY",
    "ANNOUNCEMENT",
)
APPROVAL_STATUSES = ("DRAFT", "HUMAN_APPROVED", "ARCHIVED")
SUPPORTED_FORMATS = ("4:5", "1:1", "9:16", "16:9")

PRODUCTION_LEVELS = ("AI_QUICK_CREATIVE", "PROJECT_PREMIUM_MASTER")
AI_QUICK_GATES = (
    "real_project_photo",
    "real_project_logo",
    "no_invented_architecture",
    "content_correctness",
    "basic_readability",
    "publishability",
)


def format_strategy_schema() -> dict[str, Any]:
    return {
        "schema": "MasterFormatStrategyV1",
        "implemented": False,
        "formats": {fmt: {"ready": fmt == "4:5", "role": "native master" if fmt == "4:5" else "future restack"} for fmt in SUPPORTED_FORMATS},
        "format_strategy": "",
        "protected_relationships": [
            "photo_to_headline",
            "offer_as_one_identity",
            "brand_to_entry",
            "cta_as_closure_of_commercial_flow",
        ],
        "movable_groups": ["HEADLINE", "OFFER", "PRICE", "UNIT", "CTA", "BRAND", "EDITORIAL_CLOSURE"],
        "priority_groups": ["PROJECT_PHOTO_OBJECT", "HEADLINE", "OFFER", "PRICE", "BRAND", "CTA"],
        "minimum_safe_scale": 0.72,
        "photo_behavior": "preserve designed photographic mass; crop/scale/position only",
        "headline_behavior": "keep visual-mass role; restack, do not shrink to a caption",
        "commercial_behavior": "keep offer group + price relationship",
        "brand_behavior": "one real logo; do not invent a wordmark",
        "note": "Prepares intelligent recomposition. Full format adaptation is not implemented in Phase 8.0.",
    }


def design_references_policy() -> dict[str, Any]:
    return {
        "schema": "DesignReferencesPolicyV1",
        "folder": CANONICAL_FOLDER_NAME,
        "path": "Media Library → Investhome → DESIGN_REFERENCES",
        "is": [
            "inspiration",
            "future Master creation",
            "creative direction",
            "human-curated reference material",
        ],
        "is_not": [
            "a live template library",
            "project asset source",
            "automatic production layout source",
        ],
        "production_role": "human-curated craft input for creating Masters, never a runtime layout engine",
    }


def empty_master(
    *,
    project_id: str,
    master_name: str,
    master_type: str,
    approval_status: str = "DRAFT",
    visual_asset: str | None = None,
    research_phase: str | None = None,
    master_id: str | None = None,
) -> dict[str, Any]:
    if master_type not in MASTER_TYPES:
        raise ValueError(f"unknown master_type {master_type}")
    if approval_status not in APPROVAL_STATUSES:
        raise ValueError(f"unknown approval_status {approval_status}")
    now = _now()
    return {
        "master_id": master_id or str(uuid4()),
        "project_id": project_id,
        "master_name": master_name,
        "master_type": master_type,
        "approval_status": approval_status,
        "visual_asset": visual_asset,
        "semantic_spec": None,
        "revision_contract": revision_readiness_72(),
        "supported_formats": list(SUPPORTED_FORMATS),
        "creative_tags": [],
        "campaign_tags": [],
        "photo_compatibility": ["REAL_DAY_007"],
        "content_capacity": "full_campaign",
        "created_at": now,
        "approved_at": None,
        "version": 1,
        "format_strategy": format_strategy_schema(),
        "research_phase": research_phase,
        "router_eligible": approval_status == "HUMAN_APPROVED",
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "photo_object_source": DAY007_ASSET_ID,
    }


def _research_id(slug: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"investhome:project-master:research:{slug}"))


def temple_research_catalog() -> list[dict[str, Any]]:
    """Historical experimental Masters. ARCHIVED. Router must not auto-select."""
    rows = (
        ("5.4-commercial-r1", "Research 5.4 Commercial R1", "COMMERCIAL", APPROVED_R1_ASSET_ID, MASTER_COMMERCIAL_R1_ID),
        ("5.5c-technical-master", "Research 5.5C Technical Master", "COMMERCIAL", APPROVED_R2_ASSET_ID, PARENT_MASTER_ID),
        ("7.2-A", "Research 7.2 Candidate A", "PREMIUM_CAMPAIGN", "8a9b5bd7-31f5-478a-bddb-f47b27d482ba", None),
        ("7.2-B", "Research 7.2 Candidate B", "PREMIUM_CAMPAIGN", "354abd47-98e4-47ea-8b42-c45b653d0d02", None),
        ("7.2-C", "Research 7.2 Candidate C", "PREMIUM_CAMPAIGN", "3d0ae3c4-5394-44bf-85f9-551337875b3c", None),
        ("7.2-R1", "Research 7.2-R1 Candidate C polish", "PREMIUM_CAMPAIGN", "5b7f4d0a-8c24-4936-8457-4ae4ec4080b7", None),
        ("7.3-A", "Research 7.3 Candidate A", "PREMIUM_CAMPAIGN", "8dff5925-50ff-45af-b715-ab80189d22ae", None),
        ("7.3-B", "Research 7.3 Candidate B", "PREMIUM_CAMPAIGN", "53da2774-ba3d-4f62-8dda-d7a0b8b26a8d", None),
        ("7.3-C", "Research 7.3 Candidate C", "PREMIUM_CAMPAIGN", "a2afcc5f-01b4-4e57-9e9c-ef5e12936be3", None),
        ("7.4-A", "Research 7.4 Candidate A", "PREMIUM_CAMPAIGN", "943b5b83-37ce-40e5-8729-aaa49a336c8b", None),
        ("7.4-B", "Research 7.4 Candidate B", "PREMIUM_CAMPAIGN", "bac1d3c4-312c-489e-9500-91abdac3fa2c", None),
        ("7.4-C", "Research 7.4 Candidate C", "PREMIUM_CAMPAIGN", "0375ace6-d430-43b9-a3d5-dc9a215c02f2", None),
    )
    catalog = []
    for slug, name, mtype, asset, existing_id in rows:
        item = empty_master(
            project_id=TEMPLE_PROJECT_ID,
            master_name=name,
            master_type=mtype,
            approval_status="ARCHIVED",
            visual_asset=asset,
            research_phase=slug.split("-")[0] if slug[0].isdigit() else slug,
            master_id=existing_id or _research_id(slug),
        )
        item["router_eligible"] = False
        item["research"] = True
        item["promoted"] = False
        item["creative_tags"] = ["RESEARCH", "ARCHIVED"]
        item["campaign_tags"] = ["PHASE_" + slug.split("-")[0].replace(".", "_")]
        catalog.append(item)
    return catalog


def empty_library(*, project_id: str, project_name: str) -> dict[str, Any]:
    return {
        "schema": LIBRARY_SCHEMA,
        "project_id": project_id,
        "project_name": project_name,
        "logical_path": f"{project_name} → Creative Masters",
        "masters": [],
        "human_approved_premium_count": 0,
        "archived_research_count": 0,
        "production_levels": list(PRODUCTION_LEVELS),
        "ai_quick_creative": {
            "status": "READY",
            "premium": False,
            "basis": "Phase 7.4 architecture retained as experimental basis",
            "required_gates": list(AI_QUICK_GATES),
            "score_floor": None,
        },
        "next_production_phase": "FIRST_PROJECT_PREMIUM_MASTER",
    }


def bootstrap_temple_library() -> dict[str, Any]:
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    research = temple_research_catalog()
    library["masters"] = research
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["archived_research_count"] = count_archived_research(library)
    library["note"] = (
        "Zero HUMAN_APPROVED premium Masters. Phase 7 candidates are ARCHIVED research. "
        "Router must not auto-select them. First real Temple Premium Master is the next phase."
    )
    return library


def count_approved_premium(library: dict[str, Any]) -> int:
    return sum(
        1
        for item in library.get("masters") or []
        if item.get("approval_status") == "HUMAN_APPROVED" and item.get("master_type") == "PREMIUM_CAMPAIGN"
    )


def count_archived_research(library: dict[str, Any]) -> int:
    return sum(1 for item in library.get("masters") or [] if item.get("approval_status") == "ARCHIVED" or item.get("research"))


def approved_masters(library: dict[str, Any], *, project_id: str | None = None) -> list[dict[str, Any]]:
    out = []
    for item in library.get("masters") or []:
        if item.get("approval_status") != "HUMAN_APPROVED":
            continue
        if item.get("router_eligible") is False:
            continue
        if str(item.get("master_scope") or "PROJECT") == "BRAND":
            # Brand masters are not project masters. CROSS_PROJECT_REUSE is false.
            if project_id:
                continue
        elif project_id and str(item.get("project_id") or "") != str(project_id):
            continue
        out.append(item)
    return out


def approved_brand_masters(library: dict[str, Any], *, brand_id: str = "INVESTHOME") -> list[dict[str, Any]]:
    out = []
    for item in library.get("masters") or []:
        if item.get("approval_status") != "HUMAN_APPROVED":
            continue
        if item.get("router_eligible") is False:
            continue
        if str(item.get("master_scope") or "PROJECT") != "BRAND":
            continue
        if str(item.get("brand_id") or "") != str(brand_id):
            continue
        if item.get("project_id") not in (None, "", "null"):
            continue
        out.append(item)
    return out


def add_master(library: dict[str, Any], master: dict[str, Any]) -> dict[str, Any]:
    masters = list(library.get("masters") or [])
    masters.append(master)
    library["masters"] = masters
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["archived_research_count"] = count_archived_research(library)
    return library


def archive_superseded_draft(
    library: dict[str, Any],
    *,
    master_id: str,
    superseded_by: str,
) -> dict[str, Any]:
    for item in library.get("masters") or []:
        if str(item.get("master_id")) != str(master_id):
            continue
        if item.get("approval_status") == "HUMAN_APPROVED":
            raise RuntimeError("refused to archive a HUMAN_APPROVED Master as superseded")
        item["approval_status"] = "ARCHIVED"
        item["router_eligible"] = False
        item["human_review"] = "SUPERSEDED"
        item["superseded_by"] = superseded_by
        item["promoted"] = False
        break
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["archived_research_count"] = count_archived_research(library)
    return library


def activate_locked_revision_contract() -> dict[str, Any]:
    rev = revision_readiness_72()
    for key in ("PRICE_EDIT_ONLY", "COPY_EDIT_ONLY", "VISUAL_REPLACE_ONLY"):
        block = dict(rev.get(key) or {})
        block["status"] = "ACTIVE"
        block["creates_child_revision"] = True
        block["never_overwrite_canonical"] = True
        rev[key] = block
    visual = dict(rev["VISUAL_REPLACE_ONLY"])
    visual["allowed"] = ["PROJECT_PHOTO_OBJECT"]
    visual["recalculate"] = [
        "crop",
        "focal_positioning",
        "natural_negative_space",
        "text_territory",
        "contrast_treatment",
    ]
    visual["preserve"] = "Premium Campaign 01 identity"
    visual["note"] = (
        "Replace PROJECT_PHOTO_OBJECT as a child revision. Recalculate crop, negative space, "
        "text territory, and contrast. Never overwrite the canonical approved Master."
    )
    rev["VISUAL_REPLACE_ONLY"] = visual
    rev["executed"] = False
    return rev


def approve_and_lock_master(
    library: dict[str, Any],
    *,
    master_id: str,
    asset_id: str,
    master_name: str,
    lock: dict[str, Any],
) -> dict[str, Any]:
    found = None
    for item in library.get("masters") or []:
        if str(item.get("master_id")) != str(master_id):
            continue
        if str(item.get("visual_asset") or "") != str(asset_id):
            raise RuntimeError("approved asset does not match the locked R1 visual")
        found = item
        break
    if found is None:
        raise RuntimeError(f"master {master_id} not in ProjectCreativeMasterLibraryV1")
    now = _now()
    found["approval_status"] = "HUMAN_APPROVED"
    found["human_review"] = "APPROVED"
    found["master_state"] = "LOCKED_MASTER"
    found["router_eligible"] = True
    found["approved_at"] = now
    found["canonical_format"] = "4:5"
    found["master_name"] = master_name
    found["promoted"] = False
    found["locked_identity"] = lock
    found["revision_contract"] = activate_locked_revision_contract()
    fmt = dict(found.get("format_strategy") or format_strategy_schema())
    fmt["canonical_format"] = "4:5"
    fmt["implemented"] = False
    fmt["rendered_adaptations"] = False
    fmt["next_phase"] = "8.4 INTELLIGENT FORMAT ADAPTATION — 1:1"
    formats = dict(fmt.get("formats") or {})
    for name in ("4:5", "1:1", "9:16", "16:9"):
        row = dict(formats.get(name) or {})
        row["ready"] = True
        row["role"] = "canonical visual source" if name == "4:5" else "future restack — not rendered"
        formats[name] = row
    fmt["formats"] = formats
    found["format_strategy"] = fmt
    found["creative_tags"] = ["PREMIUM_CAMPAIGN", "THE_TEMPLE", "HUMAN_APPROVED", "LOCKED_MASTER", "ORNEK_00001", "R1"]
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["archived_research_count"] = count_archived_research(library)
    library["next_production_phase"] = "8.4 INTELLIGENT FORMAT ADAPTATION — 1:1"
    library["note"] = "First HUMAN_APPROVED The Temple Premium Master is locked. Router prefers it over AI Quick Creative."
    return found


def attach_format_child(
    library: dict[str, Any],
    *,
    parent_master_id: str,
    child: dict[str, Any],
) -> dict[str, Any]:
    """Attach a format adaptation child. Never overwrite the canonical Master visual or approval."""
    found = None
    for item in library.get("masters") or []:
        if str(item.get("master_id")) == str(parent_master_id):
            found = item
            break
    if found is None:
        raise RuntimeError(f"parent master {parent_master_id} not in ProjectCreativeMasterLibraryV1")
    if found.get("approval_status") != "HUMAN_APPROVED" or found.get("master_state") != "LOCKED_MASTER":
        raise RuntimeError("format child requires a HUMAN_APPROVED LOCKED_MASTER parent")
    if child.get("is_premium_master") is True:
        raise RuntimeError("format child must not be registered as a Premium Master")
    visual_before = found.get("visual_asset")
    approval_before = found.get("approval_status")
    eligible_before = found.get("router_eligible")
    children = [c for c in list(found.get("format_children") or []) if str(c.get("target_format")) != str(child.get("target_format"))]
    children.append(child)
    found["format_children"] = children
    fmt = dict(found.get("format_strategy") or format_strategy_schema())
    fmt["canonical_format"] = "4:5"
    fmt["implemented"] = True
    fmt["rendered_adaptations"] = True
    fmt["rendered_formats"] = sorted({*(fmt.get("rendered_formats") or []), str(child.get("target_format"))})
    fmt["next_phase"] = "8.5 INTELLIGENT FORMAT ADAPTATION — 9:16"
    formats = dict(fmt.get("formats") or {})
    row = dict(formats.get(str(child.get("target_format"))) or {})
    row["ready"] = True
    row["role"] = "format child of canonical 4:5 — pending human approval"
    row["child_id"] = child.get("child_id")
    row["asset_id"] = child.get("visual_asset")
    formats[str(child.get("target_format"))] = row
    fmt["formats"] = formats
    found["format_strategy"] = fmt
    if found.get("visual_asset") != visual_before:
        raise RuntimeError("format child refused to mutate the canonical visual_asset")
    if found.get("approval_status") != approval_before or found.get("router_eligible") != eligible_before:
        raise RuntimeError("format child refused to mutate Master approval or router eligibility")
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["next_production_phase"] = "8.5 INTELLIGENT FORMAT ADAPTATION — 9:16"
    library["note"] = (
        "Canonical 4:5 Premium Campaign 01 remains the only HUMAN_APPROVED Premium Master. "
        "1:1 is a format child, not a new Master."
    )
    return found


def archive_human_rejected_master(
    library: dict[str, Any],
    *,
    master_id: str,
    reason: str,
) -> dict[str, Any]:
    found = False
    for item in library.get("masters") or []:
        if str(item.get("master_id")) != str(master_id):
            continue
        item["approval_status"] = "ARCHIVED"
        item["router_eligible"] = False
        item["human_review"] = "REJECTED"
        item["promoted"] = False
        item["rejected_at"] = _now()
        item["human_review_reason"] = reason
        found = True
        break
    if not found:
        raise RuntimeError(f"master {master_id} not in ProjectCreativeMasterLibraryV1")
    library["human_approved_premium_count"] = count_approved_premium(library)
    library["archived_research_count"] = count_archived_research(library)
    return library


def synthetic_approved_temple_library() -> dict[str, Any]:
    """Deterministic library used only for routing tests. Not persisted as production Masters."""
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    premium = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="The Temple Premium Master 01",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="HUMAN_APPROVED",
        visual_asset=None,
        master_id="synthetic-premium-01",
    )
    premium["approved_at"] = _now()
    premium["router_eligible"] = True
    editorial = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="The Temple Editorial 01",
        master_type="EDITORIAL",
        approval_status="HUMAN_APPROVED",
        visual_asset=None,
        master_id="synthetic-editorial-01",
    )
    editorial["approved_at"] = _now()
    editorial["router_eligible"] = True
    add_master(library, premium)
    add_master(library, editorial)
    return library
