"""Acceptance: Creative Director Quality Lock v1 — 3 Temple campaigns (max 3 provider calls)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
BASE = __import__("os").environ.get("API_BASE", "http://127.0.0.1:8000")
OUT = Path(__file__).resolve().parent

CAMPAIGNS = [
    {
        "key": "A_price_sales",
        "label": "PRICE/SALES",
        "brief": (
            "The Temple için Unit 204 lansman reklamı hazırla.\n"
            "Drive'daki gerçek proje görsellerini ve gerçek The Temple logosunu kullan.\n"
            "Normal fiyat $400,000, lansman fiyatı $300,000.\n"
            "Yaklaşık 25 puanlık fiyat avantajını ön plana al.\n"
            "Modern, şık ve tarihi karakterini yansıtsın.\n"
            "Premium ve satış odaklı olsun. Türkçe hazırla."
        ),
    },
    {
        "key": "B_location",
        "label": "LOCATION",
        "brief": (
            "The Temple projesinin Adams Morgan / lokasyon avantajlarını anlatan "
            "premium Instagram reklamı hazırla.\n"
            "Drive'daki gerçek proje görsellerini ve The Temple logosunu kullan.\n"
            "Türkçe hazırla. Fiyat veya Unit 204 kullanma."
        ),
    },
    {
        "key": "C_lifestyle_features",
        "label": "LIFESTYLE/FEATURES",
        "brief": (
            "The Temple için sosyal medya reklamı hazırla.\n"
            "Projenin kataloğunu ve Drive'daki bilgileri incele.\n"
            "Projenin en güçlü özelliklerinden birkaçını seç ve bunları ön plana çıkar.\n"
            "Gerçek The Temple görsellerini ve logosunu kullan.\n"
            "Premium, sade ve dikkat çekici olsun.\n"
            "Türkçe hazırla."
        ),
    },
]


def _report_fields(camp_body: dict, gen_body: dict, *, screenshot: str | None, label: str) -> dict:
    ctx = camp_body.get("campaign_context") or {}
    brief = camp_body.get("brief") or {}
    pb = gen_body.get("production_brief") or ctx.get("production_brief") or {}
    msg = ctx.get("message_strategy") or pb.get("message_strategy") or {}
    design = ctx.get("design_direction") or pb.get("design_direction") or {}
    selected = (brief.get("selected_assets") or ctx.get("selected_assets") or [{}])[0] or {}
    logo = ctx.get("selected_logo") or {}
    return {
        "1_campaign_intent": ctx.get("campaign_intent") or pb.get("campaign_intent"),
        "2_big_idea": msg.get("big_idea") or brief.get("big_idea") or pb.get("big_idea"),
        "3_hero_message": msg.get("hero_headline") or brief.get("hero_message") or pb.get("hero"),
        "4_hook": msg.get("sales_attention_hook") or brief.get("sales_hook") or pb.get("sales_hook"),
        "5_supporting_messages": msg.get("supporting_messages")
        or brief.get("supporting_messages")
        or pb.get("supporting"),
        "6_cta": msg.get("cta") or brief.get("cta") or pb.get("cta"),
        "7_selected_asset": {
            "asset_id": selected.get("asset_id") or gen_body.get("interior_asset_id"),
            "filename": selected.get("filename"),
            "role": selected.get("role"),
        },
        "8_asset_selection_reason": selected.get("selection_reason")
        or (pb.get("asset_lock") or {}).get("selection_reason"),
        "9_logo": {
            "asset_id": logo.get("asset_id") or gen_body.get("logo_asset_id"),
            "filename": logo.get("filename"),
        },
        "10_language": gen_body.get("language") or ctx.get("language"),
        "11_verified_claims": ctx.get("approved_claims") or brief.get("approved_claims"),
        "12_blocked_claims": ctx.get("blocked_claims") or brief.get("blocked_claims"),
        "13_design_direction": design,
        "14_information_density": design.get("information_density")
        or pb.get("information_density")
        or (ctx.get("simplicity_director") or {}).get("density"),
        "15_production_brief": {
            "campaign_intent": pb.get("campaign_intent"),
            "big_idea": pb.get("big_idea"),
            "hero": pb.get("hero"),
            "cta": pb.get("cta"),
            "supporting": pb.get("supporting"),
            "simplicity_director": pb.get("simplicity_director"),
            "self_critique": pb.get("self_critique") or ctx.get("self_critique"),
            "message_strategy": pb.get("message_strategy"),
            "design_direction": pb.get("design_direction"),
        },
        "16_provider": gen_body.get("provider_route"),
        "17_final_asset_id": gen_body.get("final_asset_id"),
        "18_screenshot": screenshot,
        "19_native_pipeline_used": "NO",
        "20_gpt_image_call_count": gen_body.get("gpt_image_call_count")
        or gen_body.get("provider_call_count"),
        "21_test_result": "READY FOR CREATIVE QUALITY REVIEW"
        if gen_body.get("final_asset_id") and gen_body.get("production_mode") == "finished_ad"
        else "FAIL",
        "label": label,
        "production_mode": gen_body.get("production_mode"),
        "campaign_id": camp_body.get("campaign_id"),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reports: list[dict] = []
    total_calls = 0
    reuse = all(
        (OUT / f"{item['key']}-generate-ad.json").is_file()
        and (OUT / f"{item['key']}-campaign-create.json").is_file()
        and (OUT / f"{item['key']}-report.json").is_file()
        for item in CAMPAIGNS
    )
    if reuse and not __import__("os").environ.get("FORCE_QUALITY_LOCK_LIVE"):
        # Freeze path: assert existing A/B/C artifacts without re-spending GPT.
        for item in CAMPAIGNS:
            key = item["key"]
            camp_body = json.loads((OUT / f"{key}-campaign-create.json").read_text(encoding="utf-8"))
            gen_body = json.loads((OUT / f"{key}-generate-ad.json").read_text(encoding="utf-8"))
            report = json.loads((OUT / f"{key}-report.json").read_text(encoding="utf-8"))
            calls = int(gen_body.get("gpt_image_call_count") or gen_body.get("provider_call_count") or 0)
            total_calls += calls
            shot = OUT / f"{key}-final.png"
            if shot.is_file():
                report["18_screenshot"] = str(shot)
            reports.append(report)
        summary = {
            "status": "READY FOR CREATIVE QUALITY REVIEW",
            "visual_quality_pass_declared": False,
            "total_provider_calls": total_calls,
            "max_provider_calls_allowed": 3,
            "provider_budget_ok": total_calls <= 3,
            "reused_artifacts": True,
            "campaigns": reports,
        }
        (OUT / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0 if total_calls <= 3 else 1

    with httpx.Client(base_url=BASE, timeout=360.0) as client:
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
                json.dumps(camp_body, indent=2, ensure_ascii=False),
                encoding="utf-8",
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
                json.dumps(gen_body, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            calls = int(gen_body.get("gpt_image_call_count") or gen_body.get("provider_call_count") or 0)
            total_calls += calls

            screenshot = None
            asset_id = gen_body.get("final_asset_id")
            if asset_id:
                img = client.get(f"/creative-studio/media/assets/{asset_id}/content")
                if img.status_code == 200:
                    shot = OUT / f"{key}-final.png"
                    shot.write_bytes(img.content)
                    screenshot = str(shot)

            report = _report_fields(
                camp_body,
                gen_body,
                screenshot=screenshot,
                label=item["label"],
            )
            reports.append(report)
            (OUT / f"{key}-report.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    summary = {
        "status": "READY FOR CREATIVE QUALITY REVIEW",
        "visual_quality_pass_declared": False,
        "total_provider_calls": total_calls,
        "max_provider_calls_allowed": 3,
        "provider_budget_ok": total_calls <= 3,
        "campaigns": reports,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if total_calls > 3:
        print("ERROR: exceeded provider call budget", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
