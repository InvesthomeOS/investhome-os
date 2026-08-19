"""Live recompose — OS layers only, reuse clean background 524ba26a, zero GPT Image calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import httpx

API_BASE = "http://localhost:8000"
CAMPAIGN_ID = "ec3021d7-3d2f-4eca-bd75-e747571e1bb9"
BACKGROUND_ASSET_ID = "524ba26a-c941-4c46-abd8-fe97f37242cc"
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
        print("Logged in")
        resp = client.post(
            f"/ai/creative-studio/campaigns/{CAMPAIGN_ID}/recompose",
            json={
                "language": "tr",
                "aspect_ratio": "4:5",
                "format_preset": "portrait",
                "background_asset_id": BACKGROUND_ASSET_ID,
            },
        )
        if resp.status_code != 200:
            print(resp.status_code, resp.text[:4000], file=sys.stderr)
            return 1
        body = resp.json()
        (OUT_DIR / "recompose-response.json").write_text(
            json.dumps(body, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        gpt = body.get("gpt_image") or {}
        output = (gpt.get("outputs") or [{}])[0]
        layers = output.get("layers") or []
        summary = {
            "campaign_id": body.get("campaign_id"),
            "composition_family": (body.get("creative_brief_summary") or {}).get("composition_family"),
            "composition_base_asset_id": output.get("composition_base_asset_id"),
            "final_asset_id": body.get("final_asset_id"),
            "gpt_image_call_count": body.get("gpt_image_call_count", body.get("provider_call_count")),
            "provider_call_count": body.get("provider_call_count"),
            "internal_leak_count": (body.get("duplication_guard") or {}).get("internal_leak_count"),
            "headline_layer": next((el for el in layers if el.get("id") == "text-headline"), None),
            "feature_layers": [el for el in layers if str(el.get("id", "")).startswith("feature-")],
            "cta_layer": next((el for el in layers if el.get("type") == "BUTTON"), None),
            "logo_layers": [el for el in layers if el.get("role") == "logo"],
            "editable_elements": [el.get("id") for el in layers if el.get("id")],
        }
        (OUT_DIR / "fidelity-summary.json").write_text(
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
        base_id = output.get("composition_base_asset_id") or BACKGROUND_ASSET_ID
        base_url = f"{API_BASE}/creative-studio/media/assets/{base_id}/content"
        base_img = client.get(base_url)
        if base_img.status_code == 200:
            (OUT_DIR / "background.png").write_bytes(base_img.content)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
