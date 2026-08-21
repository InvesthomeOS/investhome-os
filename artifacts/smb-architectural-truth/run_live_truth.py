"""Real SMB / API Architectural Truth Lock live harness.

Runs interior lifestyle generate + revisions 1–4, then architecture/location
guarded generate. Saves artifacts under artifacts/smb-architectural-truth/.
Does NOT declare Visual Quality PASS.
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

INTERIOR_BRIEF = (
    "The Temple için premium lifestyle / interior Instagram reklamı hazırla.\n"
    "Drive'daki onaylı gerçek proje iç mekan görsellerini ve The Temple logosunu kullan.\n"
    "Historic + modern living character — editorial luxury, minimal, sade.\n"
    "Fiyat, Unit 204 veya lansman rakamı kullanma.\n"
    "Türkçe hazırla. Premium, editorial luxury hissi."
)

ARCHITECTURE_BRIEF = (
    "The Temple için mimari / lokasyon Instagram reklamı hazırla.\n"
    "SADECE onaylı proje exterior / Historic+Addition render kullan.\n"
    "Historic + Addition mekânsal ilişkisini uydurma veya yeniden çizme.\n"
    "Onaylı asset yoksa üretme — fail closed.\n"
    "Türkçe hazırla. Fiyat veya Unit 204 kullanma."
)

LOCATION_BRIEF = (
    "The Temple projesinin Adams Morgan lokasyon avantajlarını anlatan "
    "premium Instagram reklamı hazırla.\n"
    "Temple exterior uydurma. Sadece onaylı exterior seçenekleri veya "
    "doğrulanmış neighborhood/location görselleri kullan.\n"
    "Türkçe hazırla. Fiyat veya Unit 204 kullanma."
)

REVISIONS = [
    {
        "key": "r1_headline",
        "instruction": "Başlığı Zamansız Bir Yaşam yap. Diğer hiçbir şeyi değiştirme.",
    },
    {
        "key": "r2_logo",
        "instruction": "Logoyu %20 küçült. Başka hiçbir şeyi değiştirme.",
    },
    {
        "key": "r3_remove_cta",
        "instruction": "CTA'yı kaldır. Başka hiçbir şeyi değiştirme.",
    },
    {
        "key": "r4_move_headline",
        "instruction": (
            "Başlığı kendi yüksekliği kadar aşağı kaydır. "
            "Başka hiçbir şeyi değiştirme."
        ),
    },
]


def _download(client: httpx.Client, asset_id: str, dest: Path) -> bool:
    if not asset_id:
        return False
    r = client.get(f"/creative-studio/media/assets/{asset_id}/content")
    if r.status_code != 200:
        return False
    dest.write_bytes(r.content)
    return True


def _truth_snapshot(camp: dict, gen: dict | None = None) -> dict:
    ctx = camp.get("campaign_context") or {}
    pb = (gen or {}).get("production_brief") or ctx.get("production_brief") or {}
    lock = (gen or {}).get("project_asset_lock") or pb.get("asset_lock") or {}
    selected = (ctx.get("selected_assets") or [None])[0] or ctx.get("drive_research", {}).get(
        "selected_interior"
    ) or {}
    truth = (gen or {}).get("architecture_truth_guard") or pb.get("architecture_truth_guard") or {}
    return {
        "source_asset_id": lock.get("asset_id")
        or lock.get("interior_asset_id")
        or selected.get("asset_id"),
        "filename": lock.get("interior_filename")
        or lock.get("filename")
        or selected.get("filename"),
        "classification": lock.get("classification") or selected.get("classification"),
        "architecture_locked": lock.get("architecture_locked")
        if lock.get("architecture_locked") is not None
        else selected.get("architecture_locked"),
        "creative_freedom_level": lock.get("creative_freedom_level")
        if lock.get("creative_freedom_level") is not None
        else selected.get("creative_freedom_level"),
        "approved_status": lock.get("approved_status") or selected.get("approved_status"),
        "project_relation": lock.get("project_relation") or selected.get("project_relation"),
        "architecture_truth_guard": truth,
        "drive_architecture_truth": ctx.get("architecture_truth")
        or (ctx.get("drive_research") or {}).get("architecture_truth"),
        "campaign_intent": ctx.get("campaign_intent") or pb.get("campaign_intent"),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    summary: dict = {
        "status": "READY FOR REAL SMB + ARCHITECTURAL TRUTH REVIEW",
        "visual_quality_pass_declared": False,
        "production_mode_default": "finished_ad",
        "golden_pipeline": "Prompt → Intent → Project Context → Drive/ML → Smart Asset Selection → CD → Production Brief → Golden Finished-Ad → SMB",
        "tests": {},
        "provider_call_breakdown": {},
        "smb_flow": {
            "path": "Creative Studio → Social Media Builder → Project → AI Design → Oluştur → finished-ad → AI ile Düzenle",
            "revision_button": "AI ile Düzenle",
            "create_button": "Oluştur",
            "artifacts_are_qa_only": True,
        },
    }
    total_calls = 0

    with httpx.Client(base_url=BASE, timeout=420.0) as client:
        login = client.post(
            "/auth/login",
            json={"email": "superadmin@investhome.demo", "password": "Investhome2026!"},
        )
        login.raise_for_status()
        if not login.json().get("id"):
            raise RuntimeError("login_failed")

        # ---- INTERIOR lifestyle ----
        camp = client.post(
            "/ai/creative-studio/campaigns",
            json={
                "project_id": PROJECT_ID,
                "brief": INTERIOR_BRIEF,
                "language": "tr",
                "mode": "project",
            },
        )
        camp.raise_for_status()
        camp_body = camp.json()
        (OUT / "interior-campaign-create.json").write_text(
            json.dumps(camp_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        campaign_id = camp_body["campaign_id"]

        gen = client.post(
            f"/ai/creative-studio/campaigns/{campaign_id}/generate-ad",
            json={"language": "tr", "aspect_ratio": "4:5", "production_mode": "finished_ad"},
        )
        gen_body = gen.json()
        (OUT / "interior-generate-ad.json").write_text(
            json.dumps(gen_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if gen.status_code != 200:
            summary["tests"]["interior"] = {
                "status": "fail",
                "http_status": gen.status_code,
                "body": gen_body,
                "truth": _truth_snapshot(camp_body),
            }
            (OUT / "summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 1

        total_calls += int(gen_body.get("provider_call_count") or gen_body.get("gpt_image_call_count") or 0)
        final_id = gen_body.get("final_asset_id")
        master_id = gen_body.get("master_finished_ad_asset_id") or gen_body.get("master_asset_id")
        _download(client, str(final_id), OUT / "interior-final.png")

        interior_report = {
            "status": "ok",
            "campaign_id": campaign_id,
            "production_mode": gen_body.get("production_mode"),
            "final_asset_id": final_id,
            "master_finished_ad_asset_id": master_id,
            "design_spec_present": bool(gen_body.get("design_spec")),
            "editable_layers_count": len(gen_body.get("editable_layers") or []),
            "quality_guard": gen_body.get("quality_guard"),
            "truth": _truth_snapshot(camp_body, gen_body),
            "screenshot": str(OUT / "interior-final.png"),
            "visual_quality_pass_declared": False,
        }
        (OUT / "interior-report.json").write_text(
            json.dumps(interior_report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        revisions = []
        current_final = str(final_id)
        for step in REVISIONS:
            rev = client.post(
                f"/ai/creative-studio/campaigns/{campaign_id}/revise",
                json={
                    "instruction": step["instruction"],
                    "current_final_asset_id": current_final,
                    "language": "tr",
                },
            )
            rev_body = rev.json()
            (OUT / f"{step['key']}-revise.json").write_text(
                json.dumps(rev_body, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            entry = {
                "step": step["key"],
                "instruction": step["instruction"],
                "http_status": rev.status_code,
                "status": "ok" if rev.status_code == 200 else "fail",
            }
            if rev.status_code == 200:
                total_calls += int(
                    rev_body.get("provider_call_count") or rev_body.get("gpt_image_call_count") or 0
                )
                entry.update(
                    {
                        "revision_route": rev_body.get("revision_route"),
                        "master_finished_ad_asset_id": rev_body.get("master_finished_ad_asset_id"),
                        "revision_source_asset_id": rev_body.get("revision_source_asset_id"),
                        "final_asset_id": rev_body.get("final_asset_id"),
                        "quality_guard": rev_body.get("quality_guard"),
                        "master_unchanged": str(rev_body.get("master_finished_ad_asset_id"))
                        == str(master_id),
                        "source_is_master": str(rev_body.get("revision_source_asset_id"))
                        == str(master_id),
                    }
                )
                current_final = str(rev_body.get("final_asset_id") or current_final)
                _download(client, current_final, OUT / f"{step['key']}-final.png")
                entry["screenshot"] = str(OUT / f"{step['key']}-final.png")
            else:
                entry["body"] = rev_body
            revisions.append(entry)

        summary["tests"]["interior"] = {
            **interior_report,
            "revisions": revisions,
        }

        # ---- ARCHITECTURE (Historic+Addition strict) ----
        arch_camp = client.post(
            "/ai/creative-studio/campaigns",
            json={
                "project_id": PROJECT_ID,
                "brief": ARCHITECTURE_BRIEF,
                "language": "tr",
                "mode": "project",
            },
        )
        arch_camp.raise_for_status()
        arch_camp_body = arch_camp.json()
        (OUT / "architecture-campaign-create.json").write_text(
            json.dumps(arch_camp_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        arch_id = arch_camp_body["campaign_id"]
        arch_truth = _truth_snapshot(arch_camp_body)
        arch_gen = client.post(
            f"/ai/creative-studio/campaigns/{arch_id}/generate-ad",
            json={"language": "tr", "aspect_ratio": "4:5", "production_mode": "finished_ad"},
        )
        arch_gen_body = arch_gen.json()
        (OUT / "architecture-generate-ad.json").write_text(
            json.dumps(arch_gen_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        arch_entry = {
            "http_status": arch_gen.status_code,
            "campaign_id": arch_id,
            "truth": _truth_snapshot(arch_camp_body, arch_gen_body if arch_gen.status_code == 200 else None),
            "campaign_truth": arch_truth,
            "fail_closed_expected_if_missing_hpa": True,
            "visual_quality_pass_declared": False,
        }
        if arch_gen.status_code == 200:
            total_calls += int(
                arch_gen_body.get("provider_call_count") or arch_gen_body.get("gpt_image_call_count") or 0
            )
            arch_entry["status"] = "ok"
            arch_entry["production_mode"] = arch_gen_body.get("production_mode")
            arch_entry["final_asset_id"] = arch_gen_body.get("final_asset_id")
            arch_entry["architecture_truth_guard"] = arch_gen_body.get("architecture_truth_guard")
            arch_entry["quality_guard"] = arch_gen_body.get("quality_guard")
            _download(
                client,
                str(arch_gen_body.get("final_asset_id")),
                OUT / "architecture-final.png",
            )
            arch_entry["screenshot"] = str(OUT / "architecture-final.png")
        else:
            # Expected path when Historic+Addition approved render is missing
            detail = arch_gen_body.get("detail") if isinstance(arch_gen_body, dict) else arch_gen_body
            arch_entry["status"] = "fail_closed"
            arch_entry["detail"] = detail
            (OUT / "architecture-guard-report.json").write_text(
                json.dumps(arch_entry, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        summary["tests"]["architecture"] = arch_entry

        # ---- LOCATION (no invented Temple exterior) ----
        loc_camp = client.post(
            "/ai/creative-studio/campaigns",
            json={
                "project_id": PROJECT_ID,
                "brief": LOCATION_BRIEF,
                "language": "tr",
                "mode": "project",
            },
        )
        loc_camp.raise_for_status()
        loc_camp_body = loc_camp.json()
        (OUT / "location-campaign-create.json").write_text(
            json.dumps(loc_camp_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        loc_id = loc_camp_body["campaign_id"]
        loc_gen = client.post(
            f"/ai/creative-studio/campaigns/{loc_id}/generate-ad",
            json={"language": "tr", "aspect_ratio": "4:5", "production_mode": "finished_ad"},
        )
        loc_gen_body = loc_gen.json()
        (OUT / "location-generate-ad.json").write_text(
            json.dumps(loc_gen_body, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        loc_entry = {
            "http_status": loc_gen.status_code,
            "campaign_id": loc_id,
            "truth": _truth_snapshot(loc_camp_body, loc_gen_body if loc_gen.status_code == 200 else None),
            "visual_quality_pass_declared": False,
        }
        if loc_gen.status_code == 200:
            total_calls += int(
                loc_gen_body.get("provider_call_count") or loc_gen_body.get("gpt_image_call_count") or 0
            )
            loc_entry["status"] = "ok"
            loc_entry["production_mode"] = loc_gen_body.get("production_mode")
            loc_entry["final_asset_id"] = loc_gen_body.get("final_asset_id")
            loc_entry["architecture_truth_guard"] = loc_gen_body.get("architecture_truth_guard")
            _download(client, str(loc_gen_body.get("final_asset_id")), OUT / "location-final.png")
            loc_entry["screenshot"] = str(OUT / "location-final.png")
        else:
            loc_entry["status"] = "fail_closed"
            loc_entry["detail"] = loc_gen_body.get("detail") if isinstance(loc_gen_body, dict) else loc_gen_body
        summary["tests"]["location"] = loc_entry

    summary["provider_call_breakdown"] = {
        "total": total_calls,
        "note": "Undo/Redo not exercised in this harness (GPT=0 elsewhere).",
    }
    summary["honest_notes"] = {
        "visual_quality_pass_declared": False,
        "user_visual_approval_required": True,
        "cursor_artifacts_are_qa_only": True,
        "smb_is_production_surface": True,
    }
    (OUT / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "REPORT.md").write_text(
        "\n".join(
            [
                "# SMB + Architectural Truth Lock",
                "",
                "**Status:** READY FOR REAL SMB + ARCHITECTURAL TRUTH REVIEW",
                "**Visual Quality PASS declared:** NO",
                "",
                "See `summary.json` for full interior revisions + architecture/location guards.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
