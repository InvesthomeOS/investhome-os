"""Live editable finished-ad: generate once + LAYER_ONLY A–D (expect GPT=0 on revise)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
BRIEF = (
    "Unit 204 için lansman fiyat kampanyası. Liste $400,000, lansman $300,000 (~%25). "
    "Başlık: Modern. Şık. Tarihi. CTA: Lansman Fiyatını Kaçırmayın. Türkçe. "
    "Gerçek The Temple interior ve logo kullan."
)
BASE = "http://127.0.0.1:8000"
OUT = Path(__file__).resolve().parent


STEPS = [
    ("A", "Başlığı 'Zamansız Bir Yaşam' yap. Başka hiçbir şeyi değiştirme."),
    ("B", "%25 rozetini %30 küçült. Başka hiçbir şeyi değiştirme."),
    ("C", "CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme."),
    ("D", "Logoyu %20 küçült. Başka hiçbir şeyi değiştirme."),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with httpx.Client(base_url=BASE, timeout=420.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()

        camp = client.post(
            "/ai/creative-studio/campaigns",
            json={"project_id": PROJECT_ID, "brief": BRIEF, "mode": "project", "language": "tr"},
        )
        camp.raise_for_status()
        campaign_id = camp.json()["campaign_id"]
        (OUT / "campaign-create-response.json").write_text(
            json.dumps(camp.json(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

        gen = client.post(
            f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
            json={
                "language": "tr",
                "aspect_ratio": "4:5",
                "format_preset": "portrait",
                "production_mode": "editable_finished_ad",
            },
        )
        gen.raise_for_status()
        gen_body = gen.json()
        (OUT / "generate-ad-response.json").write_text(
            json.dumps(gen_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        tip = gen_body["final_asset_id"]
        step_reports = []
        for label, instruction in STEPS:
            rev = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                json={
                    "instruction": instruction,
                    "current_final_asset_id": tip,
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                },
            )
            rev.raise_for_status()
            body = rev.json()
            (OUT / f"revise-{label}.json").write_text(
                json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            tip = body["final_asset_id"]
            step_reports.append(
                {
                    "step": label,
                    "instruction": instruction,
                    "revision_route": body.get("revision_route"),
                    "gpt_image_call_count": body.get("gpt_image_call_count"),
                    "provider_call_count": body.get("provider_call_count"),
                    "has_design_spec": bool(body.get("design_spec")),
                    "editable_layer_count": len(body.get("editable_layers") or []),
                }
            )

        # Undo / redo GPT=0
        undo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/undo-revision")
        undo.raise_for_status()
        redo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/redo-revision")
        redo.raise_for_status()

        summary = {
            "campaign_id": campaign_id,
            "production_mode": gen_body.get("production_mode"),
            "master_background_asset_id": gen_body.get("master_background_asset_id"),
            "finished_ad_raster_asset_id": gen_body.get("finished_ad_raster_asset_id"),
            "design_spec_element_ids": [
                e.get("id") for e in (gen_body.get("design_spec") or {}).get("elements") or []
            ],
            "generate_gpt_image_call_count": gen_body.get("gpt_image_call_count"),
            "steps": step_reports,
            "undo_gpt": undo.json().get("gpt_image_call_count"),
            "redo_gpt": redo.json().get("gpt_image_call_count"),
            "visual_quality": "NOT_CLAIMED",
            "all_layer_only_gpt0": all(
                s.get("revision_route") == "LAYER_ONLY"
                and int(s.get("gpt_image_call_count") if s.get("gpt_image_call_count") is not None else -1)
                == 0
                for s in step_reports
            ),
        }
        (OUT / "live-summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["all_layer_only_gpt0"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
