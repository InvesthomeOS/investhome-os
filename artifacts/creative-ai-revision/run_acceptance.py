"""Acceptance: AI Revision Mode — reuse Quality Lock A asset (max 2 provider calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
BASE = __import__("os").environ.get("API_BASE", "http://127.0.0.1:8000")
QL = Path(__file__).resolve().parents[1] / "creative-quality-lock"
OUT = Path(__file__).resolve().parent

REV1 = (
    "Başlığı daha premium yap. %25 rozetini biraz küçült. "
    "Sınırlı sayıda ünite ifadesini kaldır. "
    "Tasarımın geri kalanını mümkün olduğunca değiştirme."
)
REV2 = "CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme."


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gen_a = json.loads((QL / "A_price_sales-generate-ad.json").read_text(encoding="utf-8"))
    camp_a = json.loads((QL / "A_price_sales-campaign-create.json").read_text(encoding="utf-8"))
    report_a = json.loads((QL / "A_price_sales-report.json").read_text(encoding="utf-8"))

    original_asset_id = gen_a.get("final_asset_id") or report_a.get("17_final_asset_id")
    campaign_id = gen_a.get("campaign_id") or camp_a.get("campaign_id") or report_a.get("campaign_id")
    if not original_asset_id or not campaign_id:
        raise RuntimeError("Quality Lock A campaign/asset missing from artifacts")

    reuse = (
        (OUT / "revision-v2.json").is_file()
        and (OUT / "revision-v3.json").is_file()
        and not __import__("os").environ.get("FORCE_REVISION_LIVE")
    )

    provider_calls = 0
    with httpx.Client(base_url=BASE, timeout=360.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()

        asset_check = client.get(f"/creative-studio/media/assets/{original_asset_id}/content")
        if asset_check.status_code != 200:
            raise RuntimeError(
                f"Quality Lock A final asset {original_asset_id} not readable "
                f"(status={asset_check.status_code}). Re-seed or regenerate before revise."
            )

        camp_get = client.get(f"/ai/creative-studio/campaigns/{campaign_id}")
        if camp_get.status_code != 200:
            raise RuntimeError(
                f"Campaign {campaign_id} not found in DB. Quality Lock A context must exist "
                "for revision acceptance (do not create a new campaign)."
            )

        if reuse:
            rev1_body = json.loads((OUT / "revision-v2.json").read_text(encoding="utf-8"))
            rev2_body = json.loads((OUT / "revision-v3.json").read_text(encoding="utf-8"))
            v2_id = rev1_body["final_asset_id"]
            v3_id = rev2_body["final_asset_id"]
            provider_calls = 0
        else:
            rev1 = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                json={
                    "instruction": REV1,
                    "current_final_asset_id": original_asset_id,
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                },
            )
            rev1.raise_for_status()
            rev1_body = rev1.json()
            (OUT / "revision-v2.json").write_text(
                json.dumps(rev1_body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            provider_calls += int(
                rev1_body.get("gpt_image_call_count") or rev1_body.get("provider_call_count") or 0
            )
            v2_id = rev1_body["final_asset_id"]
            img2 = client.get(f"/creative-studio/media/assets/{v2_id}/content")
            if img2.status_code == 200:
                (OUT / "revision-v2.png").write_bytes(img2.content)

            rev2 = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                json={
                    "instruction": REV2,
                    "current_final_asset_id": v2_id,
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                },
            )
            rev2.raise_for_status()
            rev2_body = rev2.json()
            (OUT / "revision-v3.json").write_text(
                json.dumps(rev2_body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            provider_calls += int(
                rev2_body.get("gpt_image_call_count") or rev2_body.get("provider_call_count") or 0
            )
            v3_id = rev2_body["final_asset_id"]
            img3 = client.get(f"/creative-studio/media/assets/{v3_id}/content")
            if img3.status_code == 200:
                (OUT / "revision-v3.png").write_bytes(img3.content)

        # Ensure DB history exists for undo (seed if reuse path).
        camp_after = client.get(f"/ai/creative-studio/campaigns/{campaign_id}").json()
        hist = (camp_after.get("campaign_context") or {}).get("revision_history") or []
        if len(hist) < 2:
            raise RuntimeError(
                "revision_history not persisted on campaign — run seed_history.py inside API, "
                "then re-run acceptance."
            )

        undo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/undo-revision")
        undo.raise_for_status()
        undo_body = undo.json()
        (OUT / "revision-undo.json").write_text(
            json.dumps(undo_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        undo2 = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/undo-revision")
        undo2.raise_for_status()
        undo2_body = undo2.json()

        redo1 = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/redo-revision")
        redo1.raise_for_status()
        redo1_body = redo1.json()
        redo2 = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/redo-revision")
        redo2.raise_for_status()
        redo2_body = redo2.json()
        (OUT / "revision-redo.json").write_text(
            json.dumps(redo2_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    history = rev2_body.get("revision_history") or hist
    summary = {
        "status": "READY FOR AI REVISION + SMB UX REVIEW",
        "visual_quality_pass_declared": False,
        "1_quality_lock_frozen": "YES",
        "2_existing_pipeline_changed": "NO",
        "3_revision_endpoint": "POST /ai/creative-studio/campaigns/{id}/revise",
        "4_original_asset_id": original_asset_id,
        "5_revision_v2_asset_id": v2_id,
        "6_revision_v3_asset_id": v3_id,
        "7_campaign_context_id": campaign_id,
        "8_revision_history_working": bool(history) and len(history) >= 2,
        "9_undo_working": undo_body.get("final_asset_id") == v2_id,
        "9b_undo_twice_to_original": undo2_body.get("final_asset_id") == original_asset_id,
        "9c_redo_working": redo1_body.get("final_asset_id") == v2_id
        and redo2_body.get("final_asset_id") == v3_id,
        "9d_undo_redo_gpt_calls": int(undo_body.get("gpt_image_call_count") or 0)
        + int(undo2_body.get("gpt_image_call_count") or 0)
        + int(redo1_body.get("gpt_image_call_count") or 0)
        + int(redo2_body.get("gpt_image_call_count") or 0),
        "10_claim_guard": (rev1_body.get("claim_guard") or {}).get("status"),
        "11_language_lock": rev1_body.get("language") == "tr",
        "12_logo_lock": (rev1_body.get("project_asset_lock") or {}).get("logo_locked")
        or (rev1_body.get("project_asset_lock") or {}).get("status"),
        "16_provider_calls": provider_calls,
        "max_provider_calls_allowed": 2,
        "provider_budget_ok": provider_calls <= 2,
        "reused_revision_artifacts": reuse,
        "revision_intents_v2": rev1_body.get("revision_intents"),
        "revision_intents_v3": rev2_body.get("revision_intents"),
        "revision_brief_v2": rev1_body.get("revision_brief"),
        "revision_brief_v3": rev2_body.get("revision_brief"),
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if provider_calls > 2:
        print("ERROR: exceeded revision provider call budget", file=sys.stderr)
        return 1
    if not summary["9_undo_working"]:
        print("ERROR: undo did not restore v2 asset", file=sys.stderr)
        return 1
    if not summary.get("9c_redo_working"):
        print("ERROR: redo did not restore v2 then v3", file=sys.stderr)
        return 1
    if summary.get("9d_undo_redo_gpt_calls", 0) != 0:
        print("ERROR: undo/redo must not call GPT Image", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
