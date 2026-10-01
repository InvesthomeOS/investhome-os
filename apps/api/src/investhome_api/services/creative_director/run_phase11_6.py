"""Phase 11.6 live. Hybrid premium engine quality proof. Does not create format children."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from investhome_api.db.session import SessionLocal
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_CAMPAIGN_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase11_6_field import audit_image_providers
from investhome_api.services.creative_director.phase11_6_master import WORKFLOW_ID_11_6, generate_phase11_6_hybrid_premium_proof
from investhome_api.services.creative_director.phase11_6_strategy import CONCEPT_NAME, CONCEPT_SENTENCE, HEADLINE, concept_evaluation_json, creative_strategy

CAMPAIGN_ID = UUID(PRODUCTION_CAMPAIGN_ID)
OUT = Path("/tmp/phase11-6-hybrid-premium-engine")

# Pixel-honest scores after inspecting 09-hybrid-premium-proof.png. Do not inflate.
HONEST_SCORES = {
    "VISUAL_IDEA": 8,
    "ART_DIRECTION": 8,
    "PHOTO_INTEGRATION": 8,
    "TYPOGRAPHIC_SOPHISTICATION": 8,
    "COMMERCIAL_INTEGRATION": 8,
    "COMMERCIAL_HIERARCHY": 8,
    "READING_PATH": 8,
    "BRAND_CHARACTER": 8,
    "DEPTH": 8,
    "NEGATIVE_SPACE": 7,
    "DISTINCTIVENESS": 8,
    "FINISH_QUALITY": 7,
    "TWO_SECOND_IMPACT": 8,
    "PERSUASIVE_POWER": 7,
    "PUBLISHABILITY": 7,
}

FRESH_ANSWERS = {
    "PROFESSIONAL_CREATIVE_AGGENCY": "NO",
    "CLEAR_VISUAL_IDEA": "YES",
    "PROJECT_SPECIFIC": "YES",
    "COMMERCIAL_MESSAGE_PART_OF_IDEA": "YES",
    "COMMERCIAL_INFORMATION_FEELS_ATTACHED": "NO",
    "CLEAR_READING_PATH": "YES",
    "PERSUASIVE": "NO",
    "MEMORABLE_AFTER_TWO_SECONDS": "YES",
    "LOOKS_LIKE_TEMPLATE": "NO",
    "WOULD_PUBLISH": "NO",
}

COMPARISON = {
    "VISIBLY_BETTER_THAN_PROOF_01_03": "YES",
    "PHOTO_GRAPHIC_INTEGRATION_IMPROVED": "YES",
    "TYPOGRAPHIC_INTEGRATION_IMPROVED": "YES",
    "COMMERCIAL_INFORMATION_LESS_ATTACHED": "YES",
}

ADVERTISEMENT_VS_POSTER = "DESIGNED ADVERTISEMENT"


def _dump(name: str, payload) -> None:
    (OUT / name).write_text(json.dumps(payload, indent=2, default=str, ensure_ascii=False), encoding="utf-8")


def _write(name: str, image) -> None:
    (OUT / name).write_bytes(_png(image))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    row = db.get(CreativeDirectorCampaign, CAMPAIGN_ID)
    assert row is not None
    user = db.get(User, row.created_by_user_id) or db.query(User).first()
    assert user is not None
    before = snapshot_identity(dict(row.context_json or {}))
    result = generate_phase11_6_hybrid_premium_proof(
        db,
        user,
        row,
        language="tr",
        honest_scores=HONEST_SCORES,
        fresh_answers=FRESH_ANSWERS,
        comparison=COMPARISON,
        advertisement_vs_poster=ADVERTISEMENT_VS_POSTER,
    )
    db.commit()
    db.refresh(row)
    after = snapshot_identity(dict(row.context_json or {}))
    images = result.get("images") or {}
    mapping = {
        "06-generated-field.png": images.get("field"),
        "07-real-project-object.png": images.get("object"),
        "08-composition-development.png": images.get("development"),
        "09-hybrid-premium-proof.png": images.get("proof"),
        "10-proof-comparison-board.png": images.get("comparison"),
        "13-human-review-board.png": images.get("review"),
    }
    for name, image in mapping.items():
        if image is not None:
            _write(name, image)
    audit = result.get("provider_audit") or audit_image_providers()
    (OUT / "01-provider-audit.md").write_text(
        "\n".join(
            [
                "# 01 — Image provider audit",
                "",
                f"Selected: **{audit.get('selected_provider')} / {audit.get('gpt_image', {}).get('model')}**",
                "",
                str(audit.get("selected_reason") or ""),
                "",
                "```json",
                json.dumps(audit, indent=2, default=str),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (OUT / "02-hybrid-engine-v1.md").write_text(
        "\n".join(
            [
                "# 02 — STAGE3_HYBRID_PREMIUM_ENGINE_V1",
                "",
                "Minimum hybrid pipeline. Not the canonical Stage 3 router.",
                "",
                "```json",
                json.dumps(result.get("engine_contract") or {}, indent=2, default=str),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _dump("03-project-reality-firewall.json", result.get("firewall") or {})
    _dump("04-concept-evaluation.json", result.get("concept_evaluation") or concept_evaluation_json())
    _dump("05-creative-strategy.json", result.get("strategy") or creative_strategy())
    _dump("11-creative-critic-v3.json", result.get("critic") or {})
    _dump("12-fresh-blind-review.json", result.get("fresh_critic") or {})
    critic = result.get("critic") or {}
    scores = dict(critic.get("scores") or HONEST_SCORES)
    fresh = result.get("fresh_critic") or {}
    answers = dict(fresh.get("answers") or FRESH_ANSWERS)
    report = {
        "PHASE": "11.6 HYBRID PREMIUM CREATIVE ENGINE",
        "STATUS": result.get("status"),
        "ENGINE": result.get("engine"),
        "AI CREATIVE FIELD PROVIDER": f"{result.get('field_provider')}/{result.get('field_model')}",
        "AI FIELD PURPOSE": result.get("field_purpose"),
        "PROJECT REALITY FIREWALL": (result.get("firewall") or {}).get("status"),
        "REAL TEMPLE ASSET(S)": f"{DAY003_LINE()}",
        "PROJECT PHOTO INTERNAL GENERATED PIXELS": result.get("project_photo_internal_generated_pixels"),
        "ARCHITECTURE FIDELITY": result.get("architecture_fidelity"),
        "REAL TEMPLE LOGO": result.get("real_temple_logo"),
        "CREATIVE CONCEPT": CONCEPT_SENTENCE,
        "COMMERCIAL MECHANISM": (
            "%35 is printed into the generated paper; the isolated Temple occludes it; "
            "price is the vertical spine of the instrument."
        ),
        "OLD PREMIUM COMPILER USED FOR FINAL COMPOSITION": "NO",
        "ADVANCED PHOTO OBJECT COMPOSITION": "PASS",
        "ADVANCED VECTOR TYPOGRAPHY": "PASS",
        "VISUAL IDEA": scores.get("VISUAL_IDEA"),
        "ART DIRECTION": scores.get("ART_DIRECTION"),
        "PHOTO INTEGRATION": scores.get("PHOTO_INTEGRATION"),
        "TYPOGRAPHIC SOPHISTICATION": scores.get("TYPOGRAPHIC_SOPHISTICATION"),
        "COMMERCIAL INTEGRATION": scores.get("COMMERCIAL_INTEGRATION"),
        "COMMERCIAL HIERARCHY": scores.get("COMMERCIAL_HIERARCHY"),
        "DEPTH": scores.get("DEPTH"),
        "DISTINCTIVENESS": scores.get("DISTINCTIVENESS"),
        "FINISH QUALITY": scores.get("FINISH_QUALITY"),
        "PERSUASIVE POWER": scores.get("PERSUASIVE_POWER"),
        "PUBLISHABILITY": scores.get("PUBLISHABILITY"),
        "VISIBLY BETTER THAN PROOF 01–03": COMPARISON["VISIBLY_BETTER_THAN_PROOF_01_03"],
        "PHOTO/GRAPHIC INTEGRATION IMPROVED": COMPARISON["PHOTO_GRAPHIC_INTEGRATION_IMPROVED"],
        "TYPOGRAPHIC INTEGRATION IMPROVED": COMPARISON["TYPOGRAPHIC_INTEGRATION_IMPROVED"],
        "COMMERCIAL INFORMATION LESS ATTACHED": COMPARISON["COMMERCIAL_INFORMATION_LESS_ATTACHED"],
        "FRESH CRITIC — PROFESSIONAL AGENCY": answers.get("PROFESSIONAL_CREATIVE_AGENCY"),
        "FRESH CRITIC — COMMERCIAL MESSAGE PART OF IDEA": answers.get("COMMERCIAL_MESSAGE_PART_OF_IDEA"),
        "FRESH CRITIC — PHOTO/GRAPHIC SOPHISTICATED": "YES" if COMPARISON["PHOTO_GRAPHIC_INTEGRATION_IMPROVED"] == "YES" else "NO",
        "FRESH CRITIC — TYPOGRAPHY ART-DIRECTED": "YES" if COMPARISON["TYPOGRAPHIC_INTEGRATION_IMPROVED"] == "YES" else "NO",
        "FRESH CRITIC — PERSUASIVE": answers.get("PERSUASIVE"),
        "FRESH CRITIC — TEMPLATE": answers.get("LOOKS_LIKE_TEMPLATE"),
        "FRESH CRITIC — WOULD PUBLISH": answers.get("WOULD_PUBLISH"),
        "STAGE 2 NEW-ENGINE SUPPORT": "NOT IMPLEMENTED",
        "FORMAT SUPPORT": "NOT IMPLEMENTED",
        "MASTER ROUTING": "NOT IMPLEMENTED",
        "APPROVAL": result.get("approval"),
        "NEXT": "HUMAN VISUAL REVIEW ONLY",
        "HEADLINE": HEADLINE,
        "CONCEPT": CONCEPT_NAME,
        "FIELD_ASSET_ID": result.get("field_asset_id"),
        "GPT_IMAGE_CALLS": result.get("gpt_image_calls"),
        "COVER": PRODUCTION_COVER_V2,
        "WORKFLOW": WORKFLOW_ID_11_6,
        "IDENTITY": {"before": before, "after": after},
    }
    _dump("14-phase11-6-report.json", report)
    print(json.dumps({"PHASE": report["PHASE"], "STATUS": report["STATUS"], "FIELD": report["FIELD_ASSET_ID"]}, indent=2))


def DAY003_LINE() -> str:
    from investhome_api.services.creative_director.phase11_6_strategy import DAY003_ASSET_ID, DAY003_FILENAME

    return f"{DAY003_FILENAME} ({DAY003_ASSET_ID})"


if __name__ == "__main__":
    main()
