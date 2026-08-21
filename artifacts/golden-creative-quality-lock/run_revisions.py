"""Resume revision + undo/redo on existing PRICE campaign from golden run."""
from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
OUT = Path(__file__).resolve().parent

SUMMARY = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
TARGET = SUMMARY["revision_target"]
CAMPAIGN_ID = TARGET["campaign_id"]
MASTER = TARGET["master_asset_id"]
# Start from original PRICE final (not a prior failed tip)
TIP = next(c["final_asset_id"] for c in SUMMARY["campaigns"] if c["label"] == "PRICE")

REVISION_STEPS = [
    {"key": "r1_headline", "instruction": "Başlığı 'Zamansız Bir Yaşam' yap. Başka hiçbir şeyi değiştirme."},
    {"key": "r2_logo", "instruction": "Logoyu %20 küçült. Başka hiçbir şeyi değiştirme."},
    {"key": "r3_remove_cta", "instruction": "CTA'yı kaldır. Başka hiçbir şeyi değiştirme."},
]


def _download(client: httpx.Client, asset_id: str, dest: Path) -> bool:
    if not asset_id:
        return False
    r = client.get(f"/creative-studio/media/assets/{asset_id}/content")
    if r.status_code != 200:
        return False
    dest.write_bytes(r.content)
    return True


def main() -> int:
    tip = TIP
    revision_log: list[dict] = []
    total_calls = int(SUMMARY.get("total_provider_calls") or 3)

    with httpx.Client(base_url=BASE, timeout=420.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()

        for step in REVISION_STEPS:
            rev = client.post(
                f"/ai/creative-studio/campaigns/{CAMPAIGN_ID}/revise",
                json={
                    "instruction": step["instruction"],
                    "current_final_asset_id": tip,
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                },
            )
            if rev.status_code >= 400:
                body = rev.json() if rev.headers.get("content-type", "").startswith("application/json") else rev.text[:800]
                revision_log.append(
                    {
                        "step": step["key"],
                        "status": "rejected",
                        "http_status": rev.status_code,
                        "body": body,
                    }
                )
                (OUT / f"{step['key']}-revise.json").write_text(
                    json.dumps(revision_log[-1], indent=2, ensure_ascii=False), encoding="utf-8"
                )
                continue
            body = rev.json()
            calls = int(body.get("gpt_image_call_count") or body.get("provider_call_count") or 0)
            total_calls += calls
            new_id = body.get("final_asset_id")
            png = OUT / f"{step['key']}-final.png"
            _download(client, new_id, png)
            entry = {
                "step": step["key"],
                "status": "ok",
                "instruction": step["instruction"],
                "revision_route": body.get("revision_route"),
                "master_asset_id": body.get("master_asset_id"),
                "master_finished_ad_asset_id": body.get("master_finished_ad_asset_id"),
                "revision_source_asset_id": body.get("revision_source_asset_id"),
                "final_asset_id": new_id,
                "quality_guard": body.get("quality_guard"),
                "provider_call_count": calls,
                "master_unchanged": str(body.get("master_asset_id") or "") == str(MASTER),
                "source_is_master": str(body.get("revision_source_asset_id") or "") == str(MASTER),
            }
            revision_log.append(entry)
            (OUT / f"{step['key']}-revise.json").write_text(
                json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            tip = new_id or tip

        undo = client.post(f"/ai/creative-studio/campaigns/{CAMPAIGN_ID}/undo-revision", json={})
        undo_body = undo.json() if undo.status_code < 500 else {"error": undo.text}
        (OUT / "undo-response.json").write_text(
            json.dumps(undo_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        redo = client.post(f"/ai/creative-studio/campaigns/{CAMPAIGN_ID}/redo-revision", json={})
        redo_body = redo.json() if redo.status_code < 500 else {"error": redo.text}
        (OUT / "redo-response.json").write_text(
            json.dumps(redo_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        SUMMARY["total_provider_calls"] = total_calls
        SUMMARY["revisions"] = revision_log
        SUMMARY["undo_redo"] = {
            "undo_ok": undo.status_code == 200,
            "redo_ok": redo.status_code == 200,
            "undo_gpt_calls": undo_body.get("gpt_image_call_count") if isinstance(undo_body, dict) else None,
            "redo_gpt_calls": redo_body.get("gpt_image_call_count") if isinstance(redo_body, dict) else None,
            "undo_asset_id": undo_body.get("final_asset_id") if isinstance(undo_body, dict) else None,
            "redo_asset_id": redo_body.get("final_asset_id") if isinstance(redo_body, dict) else None,
        }
        (OUT / "summary.json").write_text(
            json.dumps(SUMMARY, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (OUT / "report.json").write_text(
            json.dumps(SUMMARY, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(SUMMARY["revisions"], indent=2, ensure_ascii=False))
        print(json.dumps(SUMMARY["undo_redo"], indent=2, ensure_ascii=False))
        print("total_provider_calls", total_calls)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
