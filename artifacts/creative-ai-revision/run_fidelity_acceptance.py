"""Live/acceptance: AI Revision Fidelity Lock (master + cumulative ops).

GPT calls only when FORCE_REVISION_LIVE=1 (or missing cached artifacts for live path).
Undo/redo always 0 GPT. Documents GPT call counts in summary.json.

Usage:
  python artifacts/creative-ai-revision/run_fidelity_acceptance.py
  FORCE_REVISION_LIVE=1 python artifacts/creative-ai-revision/run_fidelity_acceptance.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

PROJECT_ID = "d50708cb-60b3-465a-8b16-6d30f802af8d"
CAMPAIGN_ID = "7f4015bf-906b-4728-95b5-ef6a888b1236"
BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
QL = Path(__file__).resolve().parents[1] / "creative-quality-lock"
OUT = Path(__file__).resolve().parent

# Acceptance B — command fidelity (single revise when live)
FIDELITY_CMD = (
    "Başlığı 'Zamansız Bir Yaşam' yap. "
    "%25 rozetini mevcut boyutunun %30'u kadar küçült. "
    "Fiyatları, logoyu, CTA'yı ve arka planı değiştirme."
)

# Acceptance A — 5-step degradation (each from same MASTER via cumulative ops)
DEGRADATION_STEPS = [
    "Başlığı 'Zamansız Bir Yaşam' yap. Başka hiçbir şeyi değiştirme.",
    "%25 rozetini mevcut boyutunun %30'u kadar küçült. Başka hiçbir şeyi değiştirme.",
    "CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme.",
    "Sınırlı sayıda ünite ifadesini kaldır. Başka hiçbir şeyi değiştirme.",
    "Logoyu %20 küçült. Başka hiçbir şeyi değiştirme.",
]


def _assert_master_source(body: dict, master_id: str, label: str) -> None:
    src = body.get("revision_source_asset_id") or (body.get("project_asset_lock") or {}).get(
        "revision_source_used"
    )
    mid = str(body.get("master_asset_id") or "")
    if mid and mid != str(master_id):
        raise RuntimeError(f"{label}: master_asset_id drift {mid} != {master_id}")
    if src and str(src) != str(master_id):
        raise RuntimeError(f"{label}: revision source {src} is not master {master_id}")
    lock = body.get("project_asset_lock") or {}
    if lock.get("revision_model") and lock.get("revision_model") != "master_plus_cumulative_ops":
        raise RuntimeError(f"{label}: unexpected revision_model {lock.get('revision_model')}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    gen_a = json.loads((QL / "A_price_sales-generate-ad.json").read_text(encoding="utf-8"))
    report_a = json.loads((QL / "A_price_sales-report.json").read_text(encoding="utf-8"))
    master_asset_id = (
        gen_a.get("final_asset_id") or report_a.get("17_final_asset_id")
    )
    campaign_id = (
        gen_a.get("campaign_id")
        or report_a.get("campaign_id")
        or CAMPAIGN_ID
    )
    if not master_asset_id or not campaign_id:
        raise RuntimeError("Quality Lock A campaign/asset missing")

    force_live = bool(os.environ.get("FORCE_REVISION_LIVE"))
    run_degradation = bool(os.environ.get("RUN_DEGRADATION_5"))
    # Default: unit-level fidelity checks via API revise×1 only when forced;
    # otherwise document expected invariants from prior artifacts + cursor.
    provider_calls = 0
    fidelity_body: dict | None = None
    degradation_bodies: list[dict] = []

    with httpx.Client(base_url=BASE, timeout=360.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()

        camp = client.get(f"/ai/creative-studio/campaigns/{campaign_id}")
        if camp.status_code != 200:
            raise RuntimeError(f"Campaign {campaign_id} not found")

        tip = master_asset_id
        if force_live:
            # Command fidelity revise (1 GPT)
            rev = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                json={
                    "instruction": FIDELITY_CMD,
                    "current_final_asset_id": tip,
                    "language": "tr",
                    "aspect_ratio": "4:5",
                    "format_preset": "portrait",
                },
            )
            rev.raise_for_status()
            fidelity_body = rev.json()
            (OUT / "fidelity-cmd.json").write_text(
                json.dumps(fidelity_body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            provider_calls += int(
                fidelity_body.get("gpt_image_call_count")
                or fidelity_body.get("provider_call_count")
                or 0
            )
            _assert_master_source(fidelity_body, master_asset_id, "fidelity")
            tip = fidelity_body["final_asset_id"]
            img = client.get(f"/creative-studio/media/assets/{tip}/content")
            if img.status_code == 200:
                (OUT / "fidelity-cmd.png").write_bytes(img.content)

            if run_degradation:
                tip = master_asset_id  # start from master tip for clean 5-step
                # Prefer resetting history by using campaign as-is; each call still
                # sources master_asset_id.
                for i, instr in enumerate(DEGRADATION_STEPS, start=1):
                    r = client.post(
                        f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                        json={
                            "instruction": instr,
                            "current_final_asset_id": tip,
                            "language": "tr",
                            "aspect_ratio": "4:5",
                            "format_preset": "portrait",
                        },
                    )
                    r.raise_for_status()
                    body = r.json()
                    degradation_bodies.append(body)
                    (OUT / f"degradation-v{i}.json").write_text(
                        json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8"
                    )
                    provider_calls += int(
                        body.get("gpt_image_call_count") or body.get("provider_call_count") or 0
                    )
                    _assert_master_source(body, str(body.get("master_asset_id") or master_asset_id), f"deg-{i}")
                    tip = body["final_asset_id"]
                    png = client.get(f"/creative-studio/media/assets/{tip}/content")
                    if png.status_code == 200:
                        (OUT / f"degradation-v{i}.png").write_bytes(png.content)

        # Undo/redo regression (0 GPT) — needs history; seed path or live path
        hist = (camp.json().get("campaign_context") or {}).get("revision_history") or []
        if fidelity_body:
            hist = fidelity_body.get("revision_history") or hist
        undo_ok = None
        redo_ok = None
        undo_redo_gpt = 0
        if len(hist) >= 2:
            undo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/undo-revision")
            if undo.status_code == 200:
                undo_body = undo.json()
                undo_redo_gpt += int(undo_body.get("gpt_image_call_count") or 0)
                undo_ok = True
                redo = client.post(f"/ai/creative-studio/campaigns/{campaign_id}/redo-revision")
                if redo.status_code == 200:
                    redo_body = redo.json()
                    undo_redo_gpt += int(redo_body.get("gpt_image_call_count") or 0)
                    redo_ok = True

    # Offline structural asserts for fidelity command parsing (0 GPT)
    from investhome_api.services.creative_director.revision import (  # noqa: WPS433
        build_revision_diff,
    )

    diff = build_revision_diff(instruction=FIDELITY_CMD, production_brief={
        "final_copy": {"headline": "X", "cta": "Y", "value_badge": "~25%"},
    })
    hl = next(o for o in diff.operations if o.target == "headline")
    badge = next(o for o in diff.operations if o.target == "badge")
    parse_ok = hl.to_value == "Zamansız Bir Yaşam" and badge.scale_factor == 0.7

    summary = {
        "status": "READY FOR REVISION FIDELITY RETEST",
        "visual_quality_pass_declared": False,
        "project_id": PROJECT_ID,
        "campaign_id": campaign_id,
        "master_asset_id": master_asset_id,
        "revision_model": "master_plus_cumulative_ops",
        "forbidden_chain": "A→edit A→B, B→edit B→C (DISABLED)",
        "fidelity_command": FIDELITY_CMD,
        "fidelity_parse_ok": parse_ok,
        "fidelity_headline": hl.to_value,
        "fidelity_badge_scale_factor": badge.scale_factor,
        "fidelity_live_ran": bool(fidelity_body),
        "fidelity_live_master_source_ok": bool(fidelity_body)
        and str(fidelity_body.get("revision_source_asset_id")) == str(
            fidelity_body.get("master_asset_id") or master_asset_id
        ),
        "degradation_steps_live": len(degradation_bodies),
        "degradation_all_master_sourced": all(
            str(b.get("revision_source_asset_id"))
            == str(b.get("master_asset_id") or master_asset_id)
            for b in degradation_bodies
        )
        if degradation_bodies
        else None,
        "undo_ok": undo_ok,
        "redo_ok": redo_ok,
        "undo_redo_gpt_calls": undo_redo_gpt,
        "gpt_image_call_count": provider_calls,
        "gpt_calls_note": (
            "0 unless FORCE_REVISION_LIVE=1; "
            "add RUN_DEGRADATION_5=1 for 5 live revises (+5 GPT)."
        ),
        "force_revision_live": force_live,
        "run_degradation_5": run_degradation,
    }
    (OUT / "fidelity-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not parse_ok:
        print("ERROR: fidelity command parse failed", file=sys.stderr)
        return 1
    if undo_redo_gpt != 0:
        print("ERROR: undo/redo must be 0 GPT", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
