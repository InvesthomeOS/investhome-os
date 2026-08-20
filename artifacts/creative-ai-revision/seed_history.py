"""Seed Quality Lock A campaign revision_history from acceptance artifacts (0 GPT calls)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign

ART = Path("/app/artifacts/creative-ai-revision")
CAMPAIGN_ID = UUID("7f4015bf-906b-4728-95b5-ef6a888b1236")
ORIGINAL = "f00ef35d-fc9a-422d-9531-b6b62e756816"


def main() -> None:
    v2 = json.loads((ART / "revision-v2.json").read_text(encoding="utf-8"))
    v3 = json.loads((ART / "revision-v3.json").read_text(encoding="utf-8"))
    v2_id = v2["final_asset_id"]
    v3_id = v3["final_asset_id"]
    history = [
        {
            "version": "original",
            "previous_asset_id": None,
            "new_asset_id": ORIGINAL,
            "instruction": None,
            "revision_brief": None,
            "provider": None,
            "timestamp": None,
            "campaign_context_id": str(CAMPAIGN_ID),
        },
        {
            "version": "v2",
            "previous_asset_id": ORIGINAL,
            "new_asset_id": v2_id,
            "instruction": v2.get("revision_brief", {}).get("instruction"),
            "revision_brief": {
                "mode": "revision",
                "instruction": v2.get("revision_brief", {}).get("instruction"),
                "intents": v2.get("revision_intents"),
                "copy_overrides": (v2.get("revision_brief") or {}).get("copy_overrides"),
                "cta": (v2.get("revision_brief") or {}).get("cta"),
                "language": "tr",
            },
            "intents": v2.get("revision_intents"),
            "provider": (v2.get("provider_route") or {}).get("provider_id"),
            "timestamp": None,
            "campaign_context_id": str(CAMPAIGN_ID),
            "claim_guard": (v2.get("claim_guard") or {}).get("status"),
            "language": "tr",
        },
        {
            "version": "v3",
            "previous_asset_id": v2_id,
            "new_asset_id": v3_id,
            "instruction": v3.get("revision_brief", {}).get("instruction"),
            "revision_brief": {
                "mode": "revision",
                "instruction": v3.get("revision_brief", {}).get("instruction"),
                "intents": v3.get("revision_intents"),
                "copy_overrides": (v3.get("revision_brief") or {}).get("copy_overrides"),
                "cta": (v3.get("revision_brief") or {}).get("cta"),
                "language": "tr",
            },
            "intents": v3.get("revision_intents"),
            "provider": (v3.get("provider_route") or {}).get("provider_id"),
            "timestamp": None,
            "campaign_context_id": str(CAMPAIGN_ID),
            "claim_guard": (v3.get("claim_guard") or {}).get("status"),
            "language": "tr",
        },
    ]
    db = SessionLocal()
    try:
        row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
        if row is None:
            raise SystemExit(f"campaign {CAMPAIGN_ID} not found")
        ctx = dict(row.context_json or {})
        ctx["revision_history"] = history
        ctx["latest_master_ad_asset_id"] = v3_id
        ctx["latest_revision_instruction"] = history[-1]["instruction"]
        row.context_json = dict(ctx)
        flag_modified(row, "context_json")
        db.commit()
        print(json.dumps({"seeded": True, "history_len": len(history), "latest": v3_id}))
    finally:
        db.close()


if __name__ == "__main__":
    main()
