"""Stage 4.0 live. Foundation + production-master gate. No Story from Masters 01–03."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from PIL import Image, ImageDraw

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import _font, _wrap
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.premium_format_adapter_v1 import (
    STATUS_NO_PRODUCTION_MASTER,
    adapter_contract,
    format_master_fidelity_audit_schema,
    missing_master_requirement,
    semantic_lineage_schema,
    story_format_plan,
    story_safe_zone_v1,
)
from investhome_api.services.creative_director.stage4_0_proof import WORKFLOW_ID_40, generate_stage4_0_format_proof

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/stage4-0-premium-format-proof")


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _board(title: str, rows: list[str], size: tuple[int, int] = (1600, 2100)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), title, font=_font(28), fill=(232, 214, 170))
    y = 96
    for row in rows:
        for line in _wrap(str(row), 88):
            if y > size[1] - 48:
                return image
            draw.text((48, y), line, font=_font(18), fill=(226, 222, 214))
            y += 26
        y += 10
    return image


def _safe_zone_diagram() -> Image.Image:
    w, h = 1080, 1920
    image = Image.new("RGB", (w, h), (12, 14, 20))
    draw = ImageDraw.Draw(image)
    zone = story_safe_zone_v1()
    top = int(h * zone["top_ui_territory"]["y1"])
    bottom = int(h * zone["bottom_ui_territory"]["y0"])
    well = zone["content_well"]
    draw.rectangle((0, 0, w, top), fill=(72, 28, 32))
    draw.rectangle((0, bottom, w, h), fill=(72, 28, 32))
    draw.rectangle(
        (int(w * well["x0"]), int(h * well["y0"]), int(w * well["x1"]), int(h * well["y1"])),
        outline=(201, 168, 92),
        width=4,
    )
    draw.text((48, 36), "STORY SAFE ZONE V1 — NOT APPLIED", font=_font(28), fill=(232, 214, 170))
    draw.text((48, 88), "Top UI territory — protected", font=_font(20), fill=(236, 210, 210))
    draw.text((48, int(h * 0.48)), "Content well — project, offer, price, unit, CTA", font=_font(22), fill=(201, 168, 92))
    draw.text((48, bottom + 36), "Bottom UI territory — protected", font=_font(20), fill=(236, 210, 210))
    draw.text((48, h - 80), "9:16 is not a taller poster. Proof not executed.", font=_font(18), fill=(180, 176, 168))
    return image


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_stage4_0_format_proof(db, user, row, language="tr")
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    blob = dict((row.context_json or {}).get("phase5") or {})
    library = blob.get("project_creative_master_library") if isinstance(blob.get("project_creative_master_library"), dict) else {}
    adapted = result.get("adaptation") or {}
    requirement = adapted.get("requirement") or missing_master_requirement(library)
    status = str(result.get("status") or STATUS_NO_PRODUCTION_MASTER)

    _board(
        "01 SOURCE MASTER — NOT AVAILABLE",
        [
            "STATUS: NO_PRODUCTION_PREMIUM_MASTER_AVAILABLE",
            "Stage 4.0 will not silently use Masters 01–03 as the production source.",
            "Masters 01–03 remain research/system proofs, not the quality benchmark.",
            f"HUMAN_APPROVED premium count in library: {library.get('human_approved_premium_count')}",
            f"Library role for 01–03: {library.get('masters_01_03_role')}",
            "Required: ingested HUMAN_APPROVED production-quality design.",
            "No source master pixels were copied into this proof.",
        ],
    ).save(OUT / "01-source-master.png")
    _dump(
        "02-source-semantic-map.json",
        {
            "schema": "PremiumSemanticMapV1",
            "status": "NOT_EXTRACTED",
            "reason": STATUS_NO_PRODUCTION_MASTER,
            "doctrine": ["DESIGN FIRST", "SEMANTICS SECOND", "EDITABILITY THIRD"],
            "extracted": "AFTER the design exists — no production design was available",
        },
    )
    _dump("03-story-format-plan.json", story_format_plan(master=None))
    _safe_zone_diagram().save(OUT / "04-story-safe-zones.png")
    not_executed = [
        "STATUS: NO_PRODUCTION_PREMIUM_MASTER_AVAILABLE",
        "Story recomposition was not executed.",
        "No new Temple creative.",
        "No resize of Masters 01–03.",
        "GPT Image calls: 0",
    ]
    _board("05 STORY RECOMPOSITION — NOT EXECUTED", not_executed).save(OUT / "05-story-recomposition-development.png")
    _board("06 STORY FINAL — NOT GENERATED", not_executed).save(OUT / "06-story-final.png")
    _board("07 THUMBNAIL 25% — NOT EXECUTED", not_executed, (800, 1050)).save(OUT / "07-thumbnail-25.png")
    _board("08 THUMBNAIL 15% — NOT EXECUTED", not_executed, (480, 630)).save(OUT / "08-thumbnail-15.png")
    _board(
        "09 MASTER FIDELITY BOARD — NOT EXECUTED",
        ["No Format Child exists to compare against a production master.", *not_executed],
        (1920, 1080),
    ).save(OUT / "09-master-fidelity-board.png")
    _dump("10-format-fidelity-audit.json", format_master_fidelity_audit_schema())
    _dump("11-semantic-lineage.json", semantic_lineage_schema())
    _board(
        "12 HUMAN REVIEW — GATE",
        [
            "STATUS: NO_PRODUCTION_PREMIUM_MASTER_AVAILABLE",
            "APPROVAL: FAIL / STOP — missing production Premium Master",
            "Do not treat this board as a Story creative.",
            "Unblock: ingest and human-approve a production Premium Master, then retry Stage 4.0.",
            "Do not generate an autonomous Premium Master to unblock this stage.",
        ],
        (1920, 1080),
    ).save(OUT / "12-human-review-board.png")
    report = {
        "STAGE": "4.0 PREMIUM FORMAT ADAPTATION FOUNDATION + PROOF 01",
        "STATUS": status,
        "SOURCE MASTER": None,
        "SOURCE FORMAT": "4:5",
        "TARGET FORMAT": "9:16",
        "FORMAT CHILD": None,
        "SOURCE PROJECT PHOTO": None,
        "TARGET PROJECT PHOTO": None,
        "SAME PHOTO": None,
        "PROJECT REALITY": "NOT EXECUTED",
        "ARCHITECTURE FIDELITY": "NOT EXECUTED",
        "GENERATED PROJECT PIXELS": 0,
        "CREATIVE IDEA PRESERVATION": None,
        "VISUAL IDENTITY PRESERVATION": None,
        "TYPOGRAPHIC CHARACTER": None,
        "COMMERCIAL HIERARCHY": None,
        "PHOTO ROLE": None,
        "BRAND CHARACTER": None,
        "READING PATH": None,
        "15% TEST": "NOT EXECUTED",
        "25% TEST": "NOT EXECUTED",
        "LOOKS LIKE SAME CAMPAIGN": None,
        "LOOKS LIKE SIMPLE RESIZE": None,
        "SEMANTIC LINEAGE": "NOT CREATED",
        "GPT IMAGE CALLS": result.get("gpt_image_calls"),
        "APPROVAL": "FAIL",
        "USED MASTERS 01-03 AS SOURCE": False,
        "MISSING MASTER REQUIREMENT": requirement,
        "ADAPTER": adapter_contract()["schema"],
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_40,
        "IDENTITY": {"before": before, "after": after},
        "NEXT": result.get("next"),
    }
    _dump("13-stage4-0-report.json", report)
    print(json.dumps({"STAGE": report["STAGE"], "STATUS": report["STATUS"]}, indent=2))


if __name__ == "__main__":
    main()
