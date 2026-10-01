"""Phase 13.0 FINAL — lock Live Creative Studio Premium Campaigns as production.

Does not redesign the UI. Does not generate creatives. Does not start a proof chain.
Rejected Story adaptation experiments stay archived and off the production route.
"""

from __future__ import annotations

from typing import Any

STATUS = "LIVE_CREATIVE_STUDIO_PRODUCTION_LOCKED"
UI_STATUS = "HUMAN_APPROVED"
PRODUCT_STATUS = "PRODUCTION_READY"
ROUTING_STATUS = "ACTIVE"
APPROVED_ROUTE = "/workspaces/creative-studio/premium-campaigns/d0e00220-5f9b-530a-847d-17c1f82bbad9"
UNILOFT_FAMILY_ID = "d0e00220-5f9b-530a-847d-17c1f82bbad9"
NEXT_PRODUCT_WORK = "AI QUICK CREATIVE — LIVE PROJECT WORKFLOW"

LOCKED_UI = (
    "Premium Campaign workspace",
    "large creative preview",
    "4:5 / 9:16 / 1:1 format selector",
    "natural-language instruction box",
    "Bu tasarım / Tüm kampanya scope",
    "Uygula",
    "compact suggestion commands",
    "Onayla",
    "Geri Al",
    "İndir",
    "honest disabled Yayınla",
    "zoom controls",
    "Dashboard Design System",
)

PRODUCTION_CAPABILITIES = {
    "premium_creative_family": "READY",
    "human_approved_independent_format_masters": "READY",
    "single_format_natural_language_revision": "READY",
    "family_wide_revision": "READY",
    "target_not_present_skip": "READY",
    "missing_format_behavior": "READY",
    "immutable_master_revision_child": "READY",
    "approval_rollback": "READY",
    "download": "READY",
    "ai_quick_creative": "PRESERVED",
    "project_reality_firewall": "PRESERVED",
}

NON_PRODUCTION_FORMAT_ENGINES = (
    "premium_format_adapter_v1",
    "premium_format_recomposer_v1",
    "premium_story_recomposer_v1",
    "stage4_1_recompose",
)

DO_NOT_CREATE = (
    "13.1 proof",
    "13.2 proof",
    "new renderer experiments",
    "new format engines",
    "new Premium generation experiments",
)


def live_creative_studio_lock() -> dict[str, Any]:
    return {
        "schema": "LiveCreativeStudioProductionLockV1",
        "status": STATUS,
        "ui": UI_STATUS,
        "premium_campaigns": PRODUCT_STATUS,
        "natural_language_revision": PRODUCT_STATUS,
        "family_wide_revision": PRODUCT_STATUS,
        "download": PRODUCT_STATUS,
        "routing": ROUTING_STATUS,
        "approved_route": APPROVED_ROUTE,
        "family_id": UNILOFT_FAMILY_ID,
        "locked_ui": list(LOCKED_UI),
        "capabilities": dict(PRODUCTION_CAPABILITIES),
        "ai_quick_creative": "PRESERVED",
        "next": NEXT_PRODUCT_WORK,
        "do_not_create": list(DO_NOT_CREATE),
        "non_production_format_engines": list(NON_PRODUCTION_FORMAT_ENGINES),
        "require_additional_proof_before_product_work": False,
        "new_creative_generated": False,
    }
