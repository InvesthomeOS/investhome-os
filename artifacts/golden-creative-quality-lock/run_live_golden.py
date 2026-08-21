"""Golden Creative Quality Lock — hybrid AI design (GPT Image designer first).

Produces 3 finished_ad rasters (A lifestyle / B price / C location), revision
suite on best of A/B/C, undo/redo, and comparison notes vs golden baseline +
FAIL fidelity-v2. Does NOT declare Visual Quality PASS.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
OUT = Path(__file__).resolve().parent
GOLDEN_BASE = Path(__file__).resolve().parent.parent / "creative-quality-lock"
FAIL_REF = Path(__file__).resolve().parent.parent / "editable-layer-fidelity-v2"

CAMPAIGNS = [
    {
        "key": "A_lifestyle",
        "label": "LIFESTYLE",
        "brief": (
            "The Temple için premium lifestyle Instagram reklamı hazırla.\n"
            "Historic + modern interior character — editorial luxury, minimal, sade.\n"
            "Drive'daki gerçek proje iç mekan görsellerini ve The Temple logosunu kullan.\n"
            "Fiyat, Unit 204 veya lansman rakamı kullanma.\n"
            "Türkçe hazırla. Premium, editorial luxury hissi."
        ),
    },
    {
        "key": "B_price",
        "label": "PRICE",
        "brief": (
            "The Temple için Unit 204 lansman reklamı hazırla.\n"
            "Drive'daki gerçek proje görsellerini ve gerçek The Temple logosunu kullan.\n"
            "Normal fiyat $400,000, lansman fiyatı $300,000.\n"
            "Yaklaşık 25 puanlık fiyat avantajını ön plana al.\n"
            "Premium ve satış odaklı olsun. Türkçe hazırla."
        ),
    },
    {
        "key": "C_location",
        "label": "LOCATION",
        "brief": (
            "The Temple projesinin Adams Morgan / lokasyon avantajlarını anlatan "
            "premium Instagram reklamı hazırla.\n"
            "Drive'daki gerçek proje görsellerini ve The Temple logosunu kullan.\n"
            "Türkçe hazırla. Fiyat veya Unit 204 kullanma."
        ),
    },
]

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


def _report(camp_body: dict, gen_body: dict, *, screenshot: str | None, label: str) -> dict:
    ctx = camp_body.get("campaign_context") or {}
    brief = camp_body.get("brief") or {}
    pb = gen_body.get("production_brief") or ctx.get("production_brief") or {}
    msg = ctx.get("message_strategy") or pb.get("message_strategy") or {}
    return {
        "label": label,
        "campaign_id": camp_body.get("campaign_id"),
        "production_mode": gen_body.get("production_mode"),
        "final_asset_id": gen_body.get("final_asset_id"),
        "master_asset_id": gen_body.get("master_asset_id")
        or gen_body.get("master_finished_ad_asset_id"),
        "master_finished_ad_asset_id": gen_body.get("master_finished_ad_asset_id")
        or gen_body.get("master_asset_id"),
        "finished_ad_raster_asset_id": gen_body.get("finished_ad_raster_asset_id"),
        "design_spec_present": bool(gen_body.get("design_spec")),
        "editable_layers_count": len(gen_body.get("editable_layers") or []),
        "provider_call_count": gen_body.get("provider_call_count")
        or gen_body.get("gpt_image_call_count"),
        "quality_guard": gen_body.get("quality_guard"),
        "campaign_intent": ctx.get("campaign_intent") or pb.get("campaign_intent"),
        "hero": msg.get("hero_headline") or pb.get("hero"),
        "cta": msg.get("cta") or pb.get("cta"),
        "screenshot": screenshot,
        "native_pipeline_used": "NO",
        "visual_quality_pass_declared": False,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []
    total_calls = 0

    with httpx.Client(base_url=BASE, timeout=420.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()
        if not login.json().get("id"):
            raise RuntimeError("login_failed")

        for item in CAMPAIGNS:
            key = item["key"]
            camp = client.post(
                "/ai/creative-studio/campaigns",
                json={
                    "project_id": PROJECT_ID,
                    "brief": item["brief"],
                    "mode": "project",
                    "language": "tr",
                },
            )
            camp.raise_for_status()
            camp_body = camp.json()
            (OUT / f"{key}-campaign-create.json").write_text(
                json.dumps(camp_body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            campaign_id = camp_body["campaign_id"]

            gen = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
                json={
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                    "production_mode": "finished_ad",
                },
            )
            gen.raise_for_status()
            gen_body = gen.json()
            (OUT / f"{key}-generate-ad.json").write_text(
                json.dumps(gen_body, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            calls = int(gen_body.get("gpt_image_call_count") or gen_body.get("provider_call_count") or 0)
            total_calls += calls
            png = OUT / f"{key}-final.png"
            asset_id = gen_body.get("final_asset_id")
            shot = str(png) if _download(client, asset_id, png) else None
            report = _report(camp_body, gen_body, screenshot=shot, label=item["label"])
            (OUT / f"{key}-report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            reports.append(report)

            # Hard asserts for golden hybrid path
            assert gen_body.get("production_mode") == "finished_ad", key
            assert not gen_body.get("design_spec"), f"{key}: design_spec must be absent"
            assert not (gen_body.get("editable_layers") or []), f"{key}: no editable layers"
            assert gen_body.get("master_asset_id") or gen_body.get("master_finished_ad_asset_id"), key

        # Pick best for revision: prefer B (price) if present, else first with asset
        revise_target = next((r for r in reports if r["label"] == "PRICE"), reports[0])
        campaign_id = revise_target["campaign_id"]
        tip = revise_target["final_asset_id"]
        master = revise_target["master_finished_ad_asset_id"] or tip
        revision_log: list[dict] = []

        for step in REVISION_STEPS:
            rev = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                json={
                    "instruction": step["instruction"],
                    "current_final_asset_id": tip,
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                },
            )
            if rev.status_code >= 400:
                revision_log.append(
                    {
                        "step": step["key"],
                        "status": "rejected",
                        "http_status": rev.status_code,
                        "body": rev.json() if rev.headers.get("content-type", "").startswith("application/json") else rev.text[:500],
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
                "master_unchanged": str(body.get("master_asset_id") or "") == str(master),
                "source_is_master": str(body.get("revision_source_asset_id") or "") == str(master),
            }
            revision_log.append(entry)
            (OUT / f"{step['key']}-revise.json").write_text(
                json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            tip = new_id or tip

        # Undo / Redo (GPT=0)
        undo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/undo-revision")
        undo_body = undo.json() if undo.status_code < 500 else {"error": undo.text}
        (OUT / "undo-response.json").write_text(
            json.dumps(undo_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        redo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/redo-revision")
        redo_body = redo.json() if redo.status_code < 500 else {"error": redo.text}
        (OUT / "redo-response.json").write_text(
            json.dumps(redo_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        undo_redo = {
            "undo_ok": undo.status_code == 200,
            "redo_ok": redo.status_code == 200,
            "undo_gpt_calls": (undo_body or {}).get("gpt_image_call_count")
            if isinstance(undo_body, dict)
            else None,
            "redo_gpt_calls": (redo_body or {}).get("gpt_image_call_count")
            if isinstance(redo_body, dict)
            else None,
            "undo_asset_id": (undo_body or {}).get("final_asset_id")
            if isinstance(undo_body, dict)
            else None,
            "redo_asset_id": (redo_body or {}).get("final_asset_id")
            if isinstance(redo_body, dict)
            else None,
        }

        comparison_notes = {
            "vs_golden_baseline": {
                "baseline_dir": str(GOLDEN_BASE),
                "baseline_exists": GOLDEN_BASE.is_dir(),
                "notes": [
                    "Compare A/B/C PNGs visually to artifacts/creative-quality-lock PRICE/LOCATION/LIFESTYLE finals.",
                    "Expect finished_ad GPT Image premium editorial language — not OS layer templates.",
                    "User visual approval required; do not declare Visual Quality PASS.",
                ],
            },
            "vs_fail_fidelity_v2": {
                "fail_dir": str(FAIL_REF),
                "fail_exists": FAIL_REF.is_dir(),
                "avoid": [
                    "overflow headlines",
                    "crude white price boxes",
                    "meaningless gold bars",
                    "random overlays",
                    "weak logo",
                    "generic templates",
                    "text outside canvas",
                ],
                "notes": [
                    "artifacts/editable-layer-fidelity-v2 A/B/C are FAILURE REFERENCES — not production.",
                    "This run uses finished_ad raster hydration only (no layer reconstruction).",
                ],
            },
        }
        (OUT / "comparison-notes.json").write_text(
            json.dumps(comparison_notes, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        summary = {
            "status": "READY FOR GOLDEN CREATIVE QUALITY REVIEW",
            "visual_quality_pass_declared": False,
            "architecture": "hybrid_ai_design — GPT Image primary designer; editability second",
            "production_mode_default": "finished_ad",
            "layer_reconstruction": "NOT production default",
            "total_provider_calls": total_calls,
            "campaigns": reports,
            "revision_target": {
                "label": revise_target["label"],
                "campaign_id": campaign_id,
                "master_asset_id": master,
            },
            "revisions": revision_log,
            "undo_redo": undo_redo,
            "comparison_notes": comparison_notes,
        }
        (OUT / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (OUT / "report.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise
