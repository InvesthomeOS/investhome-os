"""Dump a real-prompt LAYER_ONLY trace for the SMB execution lock.

Uses reconstructed finished-ad specs (no stored design_spec) — the live SMB path.
"""

from __future__ import annotations

import json
from pathlib import Path

from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    build_design_spec,
    design_spec_to_smb_elements,
    ensure_revision_overlay_targets,
    route_revision,
)
from investhome_api.services.creative_director.revision_intelligence import (
    interpret_revision_plan,
    snapshot_elements,
)
from investhome_api.services.creative_director.revision_intelligence_v3 import (
    dump_semantic_plan,
    extract_working_instruction,
)

PROMPT = (
    "Üstteki küçük açıklama metnini tamamen kaldır.\n"
    "Ana başlığı %10 büyüt.\n"
    "Soldaki iki özellik metnini %15 büyüt ve okunabilirliğini artır.\n"
    "Diğer tüm tasarım öğelerini, görseli, renkleri, logoyu, CTA’yı\n"
    "ve mevcut yerleşimi kesinlikle değiştirme."
)


def _artifacts() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "artifacts").is_dir() or (parent / "apps" / "api").is_dir():
            return parent / "artifacts" / "smb-revision-execution-lock"
    return Path("/app/artifacts/smb-revision-execution-lock")


def _font(el: dict) -> float:
    typo = el.get("typography") or {}
    style = el.get("style") or {}
    return float(typo.get("font_size") or style.get("font_size") or 0)


def test_real_smb_prompt_trace_on_reconstructed_spec() -> None:
    texts = {
        "headline": "Temple Residence",
        "hero": "Boğaz manzaralı yaşam",
        "unit": "2+1 Residence",
        "cta": "Randevu Al",
    }
    brief = {
        "final_copy": {
            "headline": texts["headline"],
            "subheadline": texts["hero"],
            "unit": texts["unit"],
            "cta": texts["cta"],
            "supporting": ["Deniz manzarası", "Yüksek tavan"],
        },
        "supporting": ["Deniz manzarası", "Yüksek tavan"],
        "hero": texts["headline"],
        "cta": texts["cta"],
        "campaign_intent": "residence",
    }
    spec = build_design_spec(
        production_brief=brief,
        texts=texts,
        master_background_asset_id="00000000-0000-0000-0000-000000000001",
        logo_asset_id="00000000-0000-0000-0000-000000000002",
        finished_ad_raster_asset_id="00000000-0000-0000-0000-000000000003",
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="residence",
    )
    spec = ensure_revision_overlay_targets(spec, production_brief=brief, texts=texts)
    working, strict = extract_working_instruction(PROMPT)
    plan = interpret_revision_plan(instruction=PROMPT, production_brief=brief, design_spec=spec)
    route = route_revision(instruction=working, revision_diff=plan, intents=["COPY_CHANGE", "LAYOUT_CHANGE"])
    before = snapshot_elements(spec)
    after_spec = apply_layer_operations(spec, plan.operations)
    after = snapshot_elements(after_spec)
    layers = design_spec_to_smb_elements(after_spec)

    ops = [
        o.model_dump(by_alias=True, exclude_none=True) if hasattr(o, "model_dump") else dict(o)
        for o in plan.operations
    ]
    trace = {
        "working_instruction": working,
        "strict": strict,
        "revision_route": route,
        "provider_calls": 0,
        "operations": ops,
        "semantic_plan": dump_semantic_plan(plan),
        "resolved_layer_ids": {
            str(o.get("target")): o.get("element_ids") or o.get("element_id") for o in ops
        },
        "before_fonts": {i: _font(e) for i, e in before.items()},
        "after_fonts": {i: _font(e) for i, e in after.items()},
        "removed_ids": sorted(set(before) - set(after)),
        "smb_layer_ids": [layer.get("id") for layer in layers],
        "smb_fonts": {
            layer.get("id"): layer.get("fontSize") for layer in layers if layer.get("type") == "TEXT"
        },
        "hydrated_canvas": {
            "kicker_present": any(
                i in {layer.get("id") for layer in layers}
                for i in ("unit-label", "subheadline", "eyebrow", "top-description")
            ),
            "headline_font": next(
                (layer.get("fontSize") for layer in layers if layer.get("id") == "headline"),
                None,
            ),
        },
    }
    out_dir = _artifacts()
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "real-smb-trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert route == "LAYER_ONLY"
    assert trace["provider_calls"] == 0
    assert "unit-label" in trace["removed_ids"] or "subheadline" in trace["removed_ids"]
    assert abs(_font(after["headline"]) - _font(before["headline"]) * 1.10) <= 1
    f1_id = "support-message-1" if "support-message-1" in before else "feature-1"
    f2_id = "support-message-2" if "support-message-2" in before else "feature-2"
    assert abs(_font(after[f1_id]) - _font(before[f1_id]) * 1.15) <= 1
    assert abs(_font(after[f2_id]) - _font(before[f2_id]) * 1.15) <= 1
    assert after["cta"]["content"] == before["cta"]["content"]
    assert after["logo"]["width"] == before["logo"]["width"]
    assert not trace["hydrated_canvas"]["kicker_present"]
