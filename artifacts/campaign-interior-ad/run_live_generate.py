"""Live generate-ad for Temple interior lifestyle campaign ec3021d7."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"
CAMPAIGN_ID = "ec3021d7-3d2f-4eca-bd75-e747571e1bb9"
OUT_DIR = Path(__file__).resolve().parent


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=API_BASE, timeout=600.0, follow_redirects=True) as client:
        login = client.post(
            f"{API_BASE}/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        if login.status_code != 200:
            print(login.status_code, login.text[:2000], file=sys.stderr)
            return 1
        print("Logged in as superadmin@investhome.demo")
        resp = client.post(
            f"/ai/creative-studio/campaigns/{CAMPAIGN_ID}/generate-ad",
            json={"language": "tr", "aspect_ratio": "4:5", "format_preset": "portrait"},
        )
        if resp.status_code != 200:
            print(resp.status_code, resp.text[:4000], file=sys.stderr)
            return 1
        body = resp.json()
        (OUT_DIR / "generate-ad-response.json").write_text(
            json.dumps(body, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        art = (body.get("creative_brief_summary") or {}).get("art_direction") or {}
        summary = {
            "campaign_id": body.get("campaign_id"),
            "commercial_priority": art.get("commercial_priority"),
            "visual_hierarchy": art.get("visual_hierarchy"),
            "emphasis_strategy": art.get("emphasis_strategy"),
            "supporting_messages": (body.get("creative_brief_summary") or {}).get("supporting"),
            "cta": (body.get("final_turkish_texts") or {}).get("cta"),
            "first_notice": art.get("first_notice"),
            "second_notice": art.get("second_notice"),
            "final_asset_id": body.get("final_asset_id"),
            "interior_asset_id": body.get("interior_asset_id"),
            "logo_asset_id": body.get("logo_asset_id"),
            "claim_guard": body.get("claim_guard"),
            "project_asset_lock": body.get("project_asset_lock"),
            "provider_call_count": body.get("provider_call_count"),
            "final_turkish_texts": body.get("final_turkish_texts"),
        }
        (OUT_DIR / "art-direction-summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        asset_url = body.get("final_asset_url") or ""
        if asset_url.startswith("/"):
            asset_url = f"{API_BASE}{asset_url}"
        if asset_url:
            img = client.get(asset_url)
            if img.status_code == 200:
                (OUT_DIR / "composed.png").write_bytes(img.content)
                (OUT_DIR / "screenshot-composed.png").write_bytes(img.content)
                print(f"Saved screenshot: {OUT_DIR / 'screenshot-composed.png'}")
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
