"""Acceptance: Temple Unit 204 — CD + finished_ad generate (max 1 GPT Image call)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
BRIEF = (
    "The Temple için Unit 204 lansman reklamı hazırla.\n"
    "Drive'daki gerçek iç mekan görsellerini ve gerçek The Temple logosunu kullan.\n"
    "Normal fiyat $400,000, lansman fiyatı $300,000.\n"
    "Yaklaşık %25 fiyat avantajını öne çıkar.\n"
    "Modern, şık ve tarihi karakteri vurgula.\n"
    "Premium ve satış odaklı olsun."
)
BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parents[1] / "campaign-orchestration-unit204"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=300.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()
        token = login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        camp = client.post(
            "/ai/creative-studio/campaigns",
            headers=headers,
            json={
                "project_id": PROJECT_ID,
                "brief": BRIEF,
                "mode": "project",
                "language": "tr",
            },
        )
        camp.raise_for_status()
        camp_body = camp.json()
        (OUT / "campaign-create-response.json").write_text(
            json.dumps(camp_body, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        campaign_id = camp_body["campaign_id"]
        strategy = (camp_body.get("brief") or {}).get("big_idea") or (camp_body.get("campaign_context") or {}).get(
            "cd_strategy", {}
        ).get("big_idea")

        gen = client.post(
            f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
            headers=headers,
            json={
                "language": "tr",
                "aspect_ratio": "4:5",
                "format_preset": "portrait",
                "production_mode": "finished_ad",
            },
        )
        gen.raise_for_status()
        gen_body = gen.json()
        (OUT / "generate-ad-response.json").write_text(
            json.dumps(gen_body, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        asset_id = gen_body.get("final_asset_id")
        if asset_id:
            img = client.get(
                f"/creative-studio/media/assets/{asset_id}/content",
                headers=headers,
            )
            if img.status_code == 200:
                (OUT / "composed.png").write_bytes(img.content)

        summary = {
            "creative_director_big_idea": strategy,
            "interior_asset_id": gen_body.get("interior_asset_id"),
            "logo_asset_id": gen_body.get("logo_asset_id"),
            "provider_route": gen_body.get("provider_route"),
            "production_mode": gen_body.get("production_mode"),
            "campaign_id": campaign_id,
            "final_asset_id": asset_id,
            "screenshot": str(OUT / "composed.png"),
        }
        (OUT / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
