"""ONE-TIME repair: point The Temple SMB post cover at the approved master raster.

Does not generate images, call providers, change routing, or mutate the master asset.
Idempotent for:
  post 067c22d3-dcc3-4569-8f3c-127a0afbef98
  campaign a45f7a43-cade-447e-8aa5-b6d126688ff7
"""

from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

POST_ID = "067c22d3-dcc3-4569-8f3c-127a0afbef98"
CAMPAIGN_ID = "a45f7a43-cade-447e-8aa5-b6d126688ff7"
DOC_ID = "7439c442-1b50-40b6-bb36-49816fdeda9c"
BAD = "0537ce84-0faa-469f-bc8a-1f8347240c98"
MASTER = "f1310474-d9b9-45f9-8fde-99aaddbc2431"


def _as_dict(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise TypeError("expected JSON object")


def restore_campaign(ctx: dict) -> dict:
    out = deepcopy(ctx)
    if str(out.get("master_asset_id") or "") != MASTER:
        raise RuntimeError(f"refusing to restore: master_asset_id is {out.get('master_asset_id')}")
    if str(out.get("master_finished_ad_asset_id") or "") != MASTER:
        raise RuntimeError(
            f"refusing to restore: master_finished_ad_asset_id is {out.get('master_finished_ad_asset_id')}"
        )
    hist = out.get("revision_history") if isinstance(out.get("revision_history"), list) else []
    original = hist[0] if hist and isinstance(hist[0], dict) else None
    if not original or str(original.get("new_asset_id") or "") != MASTER:
        raise RuntimeError("refusing to restore: history[0] is not the approved master")

    out["finished_ad_raster_asset_id"] = MASTER
    out["latest_master_ad_asset_id"] = MASTER
    out["revision_index"] = 0
    out["current_revision_index"] = 0
    out["revision_operations"] = []
    if isinstance(original.get("design_spec"), dict):
        out["design_spec"] = deepcopy(original["design_spec"])
    out["one_time_master_cover_restore"] = {
        "post_id": POST_ID,
        "from_cover_asset_id": BAD,
        "to_cover_asset_id": MASTER,
        "provider_calls": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return out


def restore_draft(body: dict) -> dict:
    out = deepcopy(body)
    posts = out.get("posts") if isinstance(out.get("posts"), list) else []
    hit = None
    for post in posts:
        if isinstance(post, dict) and str(post.get("id") or "") == POST_ID:
            hit = post
            break
    if hit is None:
        raise RuntimeError(f"post {POST_ID} not found in draft")

    hit["coverAssetId"] = MASTER
    for el in hit.get("elements") or []:
        if not isinstance(el, dict):
            continue
        if str(el.get("id") or "") == "img-finished-ad" or str(el.get("role") or "") in {
            "finished_ad",
            "cover",
        }:
            if "assetId" in el or el.get("type") == "IMAGE":
                el["assetId"] = MASTER
            if "asset_id" in el:
                el["asset_id"] = MASTER

    meta = hit.get("generationMeta") if isinstance(hit.get("generationMeta"), dict) else {}
    meta["finished_ad_raster_asset_id"] = MASTER
    meta["master_finished_ad_asset_id"] = MASTER
    gpt = meta.get("gpt_image") if isinstance(meta.get("gpt_image"), dict) else None
    if gpt is not None:
        gpt["local_asset_id"] = MASTER
        meta["gpt_image"] = gpt
    spec = meta.get("design_spec") if isinstance(meta.get("design_spec"), dict) else None
    if spec is not None and spec.get("finished_ad_raster_asset_id"):
        spec["finished_ad_raster_asset_id"] = MASTER
        meta["design_spec"] = spec
    hit["generationMeta"] = meta

    ident = out.get("selectedIdentity") if isinstance(out.get("selectedIdentity"), dict) else {}
    ident["postId"] = POST_ID
    ident["campaignId"] = CAMPAIGN_ID
    ident["coverAssetId"] = MASTER
    ident["masterFinishedAdAssetId"] = MASTER
    out["selectedIdentity"] = ident
    out["selectedPostId"] = POST_ID
    cover = out.get("coverImage") if isinstance(out.get("coverImage"), dict) else {}
    cover["asset_id"] = MASTER
    cover.setdefault("role", "cover")
    out["coverImage"] = cover
    return out


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    with engine.begin() as conn:
        ctx_raw = conn.execute(
            text("SELECT context_json FROM creative_director_campaigns WHERE id = :id"),
            {"id": CAMPAIGN_ID},
        ).scalar()
        draft_raw = conn.execute(
            text("SELECT draft_body_json FROM creative_studio_documents WHERE id = :id"),
            {"id": DOC_ID},
        ).scalar()
        ctx = restore_campaign(_as_dict(ctx_raw))
        draft = restore_draft(_as_dict(draft_raw))
        conn.execute(
            text(
                "UPDATE creative_director_campaigns "
                "SET context_json = CAST(:ctx AS jsonb) WHERE id = :id"
            ),
            {"ctx": json.dumps(ctx), "id": CAMPAIGN_ID},
        )
        conn.execute(
            text(
                "UPDATE creative_studio_documents "
                "SET draft_body_json = CAST(:body AS jsonb), draft_updated_at = NOW() "
                "WHERE id = :id"
            ),
            {"body": json.dumps(draft), "id": DOC_ID},
        )

    post = next(p for p in draft["posts"] if p.get("id") == POST_ID)
    print(
        json.dumps(
            {
                "restore": "ok",
                "provider_calls": 0,
                "post_id": POST_ID,
                "cover_asset_id": post.get("coverAssetId"),
                "master_finished_ad_asset_id": (post.get("generationMeta") or {}).get(
                    "master_finished_ad_asset_id"
                ),
                "campaign_finished_ad_raster_asset_id": ctx.get("finished_ad_raster_asset_id"),
                "campaign_master_finished_ad_asset_id": ctx.get("master_finished_ad_asset_id"),
                "revision_index": ctx.get("revision_index"),
                "selected_post_id": draft.get("selectedPostId"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
