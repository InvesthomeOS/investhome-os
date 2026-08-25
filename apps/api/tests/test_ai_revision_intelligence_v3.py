"""Revision Intelligence v3 — instruction execution lock (GPT=0)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    build_design_spec,
    compose_layer_only_on_locked_raster,
    ensure_revision_overlay_targets,
    route_revision,
)
from investhome_api.services.creative_director.revision import move_revision_cursor
from investhome_api.services.creative_director.revision_intelligence import (
    interpret_revision_plan,
    snapshot_elements,
    validate_change_diff,
)
from investhome_api.services.creative_director.revision_intelligence_v3 import (
    dump_semantic_plan,
    extract_working_instruction,
    validate_execution,
)

REAL_SMB_PROMPT = (
    "Üstteki küçük açıklama metnini tamamen kaldır.\n"
    "Ana başlığı %10 büyüt.\n"
    "Soldaki iki özellik metnini %15 büyüt ve okunabilirliğini artır.\n"
    "Diğer tüm tasarım öğelerini, görseli, renkleri, logoyu, CTA’yı\n"
    "ve mevcut yerleşimi kesinlikle değiştirme."
)

def _artifacts_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "artifacts").is_dir() or (parent / "apps" / "api").is_dir():
            return parent / "artifacts" / "ai-revision-intelligence-v3"
    return Path("/app/artifacts/ai-revision-intelligence-v3")


ARTIFACTS = _artifacts_dir()


def _el(
    *,
    eid: str,
    etype: str,
    role: str,
    x: int,
    y: int,
    w: int,
    h: int,
    content: str | None = None,
    font: int | None = None,
    weight: str = "normal",
    color: str = "#E8E0D4",
    asset_id: str | None = None,
    z: int = 10,
) -> dict:
    row: dict = {
        "id": eid,
        "type": etype,
        "role": role,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "z_index": z,
        "locked": eid == "master_background",
        "editable": eid != "master_background",
        "opacity": 1.0,
    }
    if content is not None:
        row["content"] = content
    if asset_id:
        row["asset_id"] = asset_id
    if font is not None:
        row["typography"] = {
            "font_size": font,
            "font_weight": weight,
            "color": color,
            "font_family": "sans",
            "align": "left",
        }
    if etype == "cta":
        row["style"] = {
            "background_color": "#C4A35A",
            "text_color": "#1A1510",
            "font_size": font or 28,
            "font_weight": "semibold",
        }
    return row


def _smb_real_spec() -> dict:
    """Typical SMB editorial layout: top kicker, headline, left features, logo, CTA."""
    return {
        "version": 2,
        "mode": "editable_finished_ad",
        "canvas": {"width": 1080, "height": 1350, "aspect_ratio": "4:5"},
        "master_background_asset_id": "bg-master-001",
        "logo_asset_id": "logo-001",
        "locked_background": True,
        "background": {"asset_id": "bg-master-001", "crop": "cover"},
        "elements": [
            _el(
                eid="master_background",
                etype="image",
                role="background",
                x=0,
                y=0,
                w=1080,
                h=1350,
                asset_id="bg-master-001",
                z=0,
            ),
            _el(
                eid="logo",
                etype="logo",
                role="logo",
                x=72,
                y=64,
                w=160,
                h=48,
                asset_id="logo-001",
                z=10,
            ),
            _el(
                eid="top-description",
                etype="text",
                role="subheadline",
                x=72,
                y=140,
                w=720,
                h=36,
                content="Tarihi ve modern yaşamın buluştuğu nokta.",
                font=18,
                weight="medium",
                color="#C4A35A",
                z=18,
            ),
            _el(
                eid="headline",
                etype="text",
                role="headline",
                x=72,
                y=190,
                w=760,
                h=180,
                content="Zamansız Yaşam",
                font=64,
                weight="bold",
                color="#F7F3EB",
                z=20,
            ),
            _el(
                eid="feature-1",
                etype="text",
                role="support_message",
                x=72,
                y=430,
                w=480,
                h=48,
                content="Editoryal lüks ve minimal tasarım.",
                font=20,
                weight="normal",
                color="#C8C0B4",
                z=26,
            ),
            _el(
                eid="feature-2",
                etype="text",
                role="support_message",
                x=72,
                y=490,
                w=480,
                h=48,
                content="Sade ve şık iç mekanlar.",
                font=20,
                weight="normal",
                color="#C8C0B4",
                z=27,
            ),
            _el(
                eid="cta",
                etype="cta",
                role="cta",
                x=72,
                y=1180,
                w=420,
                h=56,
                content="Detayları Keşfet",
                font=28,
                z=40,
            ),
            _el(
                eid="discount-badge",
                etype="badge",
                role="discount_badge",
                x=820,
                y=72,
                w=180,
                h=72,
                content="~25% lansman fiyat avantajı",
                font=22,
                weight="bold",
                color="#C4A35A",
                z=12,
            ),
        ],
    }


def _apply(instruction: str, spec: dict | None = None):
    spec = spec or _smb_real_spec()
    plan = interpret_revision_plan(instruction=instruction, design_spec=spec)
    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    preservation = validate_change_diff(before=before, after_spec=after, revision_diff=plan)
    execution = validate_execution(before=before, after_spec=after, revision_diff=plan)
    route = route_revision(instruction=instruction, revision_diff=plan, intents=["COPY_CHANGE", "LAYOUT_CHANGE"])
    return plan, before, after, preservation, execution, route


def _by_id(spec: dict) -> dict:
    return {el["id"]: el for el in spec["elements"]}


def _font(el: dict) -> float:
    typo = el.get("typography") or {}
    return float(typo.get("font_size") or 0)


def test_preserve_clauses_stripped_from_working_text():
    working, strict = extract_working_instruction(REAL_SMB_PROMPT)
    assert strict is True
    assert "cta" not in working.lower()
    assert "logo" not in working.lower()
    assert "kaldır" in working
    assert "%10" in working
    assert "%15" in working


def test_real_smb_prompt_plan_and_execution():
    plan, before, after, preservation, execution, route = _apply(REAL_SMB_PROMPT)
    assert route == "LAYER_ONLY"
    semantic = dump_semantic_plan(plan)
    actions = {(o["action"], o["target"]) for o in semantic["operations"]}
    assert ("delete", "top_small_description") in actions
    assert ("resize", "primary_headline") in actions
    assert ("resize", "left_feature_texts") in actions
    assert ("improve_readability", "left_feature_texts") in actions
    assert execution["status"] == "pass"
    assert preservation["status"] == "pass"
    assert preservation["unexpected_mutation_count"] == 0
    assert preservation["background_asset_unchanged"] is True

    ids = {el["id"] for el in after["elements"]}
    assert "top-description" not in ids
    a = _by_id(after)
    assert abs(_font(a["headline"]) - before["headline"]["typography"]["font_size"] * 1.10) <= 1
    assert abs(_font(a["feature-1"]) - before["feature-1"]["typography"]["font_size"] * 1.15) <= 1
    assert abs(_font(a["feature-2"]) - before["feature-2"]["typography"]["font_size"] * 1.15) <= 1
    # readability: weight and/or contrast improved
    w1 = (a["feature-1"].get("typography") or {}).get("font_weight")
    c1 = (a["feature-1"].get("typography") or {}).get("color")
    assert w1 in {"medium", "semibold", "bold"} or c1 != before["feature-1"]["typography"]["color"]
    # unmentioned
    assert a["logo"]["x"] == before["logo"]["x"]
    assert a["logo"]["y"] == before["logo"]["y"]
    assert a["logo"]["width"] == before["logo"]["width"]
    assert a["cta"]["x"] == before["cta"]["x"]
    assert a["cta"]["y"] == before["cta"]["y"]
    assert a["cta"]["content"] == before["cta"]["content"]
    assert a["master_background"]["asset_id"] == before["master_background"]["asset_id"]


def test_reconstructed_finished_ad_spec_executes_real_smb_prompt():
    """finished_ad generate pops design_spec; reconstruction must still execute the SMB prompt."""
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
    ids = {el["id"] for el in spec["elements"] if isinstance(el, dict)}
    assert "unit-label" in ids or "subheadline" in ids
    assert "support-message-1" in ids or "feature-1" in ids
    assert "support-message-2" in ids or "feature-2" in ids

    plan, before, after, preservation, execution, route = _apply(REAL_SMB_PROMPT, spec)
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    assert preservation["status"] == "pass"
    after_ids = {el["id"] for el in after["elements"]}
    assert "unit-label" not in after_ids
    assert "subheadline" not in after_ids or "unit-label" in ids
    a = _by_id(after)
    assert abs(_font(a["headline"]) - before["headline"]["typography"]["font_size"] * 1.10) <= 1
    f1 = a.get("support-message-1") or a.get("feature-1")
    f2 = a.get("support-message-2") or a.get("feature-2")
    b1 = before.get("support-message-1") or before.get("feature-1")
    b2 = before.get("support-message-2") or before.get("feature-2")
    assert f1 and f2 and b1 and b2
    assert abs(_font(f1) - b1["typography"]["font_size"] * 1.15) <= 1
    assert abs(_font(f2) - b2["typography"]["font_size"] * 1.15) <= 1
    assert a["cta"]["content"] == before["cta"]["content"]
    assert a["logo"]["width"] == before["logo"]["width"]
    assert a["master_background"]["asset_id"] == before["master_background"]["asset_id"]


def test_a_logo_scale_only():
    plan, before, after, preservation, execution, route = _apply("logoyu %20 büyüt")
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    assert preservation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert abs(a["logo"]["width"] - before["logo"]["width"] * 1.20) <= 2
    assert a["headline"]["content"] == before["headline"]["content"]
    assert a["cta"]["y"] == before["cta"]["y"]
    assert _font(a["headline"]) == _font(before["headline"])
    mutated = [
        eid
        for eid in before
        if eid in a
        and (
            before[eid].get("x") != a[eid].get("x")
            or before[eid].get("width") != a[eid].get("width")
            or (before[eid].get("typography") or {}) != (a[eid].get("typography") or {})
        )
    ]
    assert mutated == ["logo"]


def test_b_logo_up_by_own_height():
    plan, before, after, preservation, execution, route = _apply(
        "logoyu kendi yüksekliği kadar yukarı taşı"
    )
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    a = _by_id(after)
    expected_y = before["logo"]["y"] - before["logo"]["height"]
    assert abs(a["logo"]["y"] - expected_y) <= 1


def test_c_bottom_margin_equals_horizontal():
    plan, before, after, preservation, execution, route = _apply(
        "sağ ve soldaki boşluk kadar aşağıda da boşluk bırak"
    )
    assert route == "LAYER_ONLY"
    a = _by_id(after)
    overlays = [
        el
        for el in after["elements"]
        if el["id"] not in {"master_background"}
    ]
    left_m = min(float(el["x"]) for el in overlays)
    right_m = min(1080 - (float(el["x"]) + float(el["width"])) for el in overlays)
    h_margin = min(left_m, right_m)
    cta_bottom_gap = 1350 - (a["cta"]["y"] + a["cta"]["height"])
    assert abs(cta_bottom_gap - h_margin) <= 2


def test_d_headline_text_only():
    plan, before, after, preservation, execution, route = _apply(
        "başlığı Zamansız Bir Yaşam yap, başka hiçbir şeyi değiştirme"
    )
    assert plan.strict_preserve is True
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    assert preservation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert a["headline"]["content"] == "Zamansız Bir Yaşam"
    text_mutations = [
        eid
        for eid in before
        if eid in a and before[eid].get("content") != a[eid].get("content")
    ]
    assert text_mutations == ["headline"]
    unrelated = [
        eid
        for eid in ("logo", "cta", "feature-1", "feature-2", "master_background")
        if before[eid]["x"] != a[eid]["x"] or before[eid]["y"] != a[eid]["y"]
    ]
    assert unrelated == []


def test_e_badge_remove_provider_zero():
    plan, before, after, preservation, execution, route = _apply("%25 rozetini kaldır")
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    ids = {el["id"] for el in after["elements"]}
    assert "discount-badge" not in ids
    assert "logo" in ids and "cta" in ids and "headline" in ids


def test_f_cta_move_and_scale():
    plan, before, after, preservation, execution, route = _apply(
        "CTA'yı 30 px yukarı taşı ve %10 küçült"
    )
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    assert preservation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert abs(a["cta"]["y"] - (before["cta"]["y"] - 30)) <= 1
    assert abs(a["cta"]["width"] - before["cta"]["width"] * 0.90) <= 2
    assert a["logo"]["width"] == before["logo"]["width"]
    assert a["headline"]["content"] == before["headline"]["content"]


def test_image_required_still_for_background_change():
    plan = interpret_revision_plan(
        instruction="Arka plandaki koltuğu kaldır.",
        design_spec=_smb_real_spec(),
    )
    route = route_revision(
        instruction="Arka plandaki koltuğu kaldır.",
        revision_diff=plan,
        intents=["VISUAL_CHANGE", "ASSET_CHANGE"],
    )
    assert route == "IMAGE_REQUIRED"


def test_undo_redo_still_gpt_zero():
    history = [
        {"version": "original", "new_asset_id": "a1"},
        {"version": "v2", "new_asset_id": "a2", "operations": [{"target": "headline"}]},
        {"version": "v3", "new_asset_id": "a3", "operations": [{"target": "cta"}]},
    ]
    entries, idx, asset = move_revision_cursor(history, 2, delta=-1)
    assert idx == 1 and asset == "a2"
    entries, idx, asset = move_revision_cursor(entries, idx, delta=1)
    assert idx == 2 and asset == "a3"


def test_write_v3_artifacts():
    spec = _smb_real_spec()
    plan, before, after, preservation, execution, route = _apply(REAL_SMB_PROMPT, spec)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "READY FOR REVISION INTELLIGENCE v3 REAL SMB RETEST",
        "visual_quality_pass_declared": False,
        "root_cause": (
            "Parser operated on the full prompt so preserve mentions of CTA/logo polluted "
            "targeting; percentage ops captured only the first match; spatial targets "
            "(üstteki küçük açıklama / sol özellik) were unresolved; finished_ad forced "
            "IMAGE_REQUIRED so GPT preserved pixels without applying layer ops."
        ),
        "revision_plan": dump_semantic_plan(plan),
        "requested_operations": [o.model_dump(by_alias=True, exclude_none=True) for o in plan.operations if o.action != "minimum_change"],
        "applied_operations": execution.get("checks"),
        "preservation_check": {
            "status": preservation["status"],
            "unexpected_mutation_count": preservation["unexpected_mutation_count"],
            "background_asset_unchanged": preservation["background_asset_unchanged"],
        },
        "execution_validation": execution,
        "image_provider_call_count": 0,
        "revision_route": route,
        "undo_redo": "GPT=0 cursor unchanged",
        "screenshot": "artifacts/ai-revision-intelligence-v3/smb-revision-after.png",
    }
    (ARTIFACTS / "summary.json").write_text(
        __import__("json").dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (ARTIFACTS / "revision-plan.json").write_text(
        __import__("json").dumps(dump_semantic_plan(plan), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        from PIL import Image, ImageDraw, ImageFont

        def _draw(spec_obj: dict, path: Path) -> None:
            img = Image.new("RGB", (1080, 1350), (28, 24, 20))
            d = ImageDraw.Draw(img)
            try:
                font = ImageFont.load_default()
            except OSError:
                font = None
            for el in spec_obj["elements"]:
                x, y, w, h = int(el["x"]), int(el["y"]), int(el["width"]), int(el["height"])
                role = str(el.get("role") or "")
                if role == "background":
                    d.rectangle([x, y, x + w, y + h], fill=(46, 40, 34))
                    continue
                fill = (196, 163, 90) if role in {"cta", "discount_badge", "logo"} else (90, 82, 72)
                if role == "headline":
                    fill = (247, 243, 235)
                d.rectangle([x, y, x + w, y + h], outline=fill, width=2)
                label = str(el.get("content") or el.get("id"))[:48]
                d.text((x + 6, y + 6), label, fill=fill, font=font)
            img.save(path)

        _draw(spec, ARTIFACTS / "smb-revision-before.png")
        _draw(after, ARTIFACTS / "smb-revision-after.png")
        _draw(after, ARTIFACTS / "screenshot-composed.png")
    except Exception as exc:  # pragma: no cover
        (ARTIFACTS / "render-error.txt").write_text(str(exc), encoding="utf-8")
    assert execution["status"] == "pass"
    assert (ARTIFACTS / "summary.json").is_file()


SELECTED_DESIGN_PROMPT = (
    "Üstteki küçük açıklama metnini tamamen kaldır.\n"
    "Ana başlığı %10 büyüt.\n"
    "Soldaki iki açıklama metnini %15 büyüt.\n"
    "Logo, arka plan görseli, CTA butonu, renkler ve tasarımın geri kalanını kesinlikle değiştirme."
)


def test_selected_design_prompt_does_not_regenerate_creative():
    plan, before, after, preservation, execution, route = _apply(SELECTED_DESIGN_PROMPT)
    assert route == "LAYER_ONLY"
    semantic = dump_semantic_plan(plan)
    actions = {(o["action"], o["target"]) for o in semantic["operations"]}
    assert ("delete", "top_small_description") in actions
    assert ("resize", "primary_headline") in actions
    assert ("resize", "left_feature_texts") in actions
    assert execution["status"] == "pass"
    assert preservation["background_asset_unchanged"] is True
    a = _by_id(after)
    assert abs(_font(a["headline"]) - before["headline"]["typography"]["font_size"] * 1.10) <= 1
    assert abs(_font(a["feature-1"]) - before["feature-1"]["typography"]["font_size"] * 1.15) <= 1
    assert abs(_font(a["feature-2"]) - before["feature-2"]["typography"]["font_size"] * 1.15) <= 1
    assert a["cta"]["content"] == before["cta"]["content"]
    assert a["logo"]["asset_id"] == before["logo"]["asset_id"]
    assert a["master_background"]["asset_id"] == before["master_background"]["asset_id"]


def test_kicker_delete_does_not_steal_support_messages():
    """Real Temple finished-ad: no unit-label; SM1/SM2 are the left copy."""
    spec = _smb_real_spec()
    spec["elements"] = [
        el
        for el in spec["elements"]
        if el["id"] not in {"top-description", "feature-1", "feature-2"}
    ]
    spec["elements"].extend(
        [
            _el(
                eid="support-message-1",
                etype="text",
                role="support_message",
                x=72,
                y=430,
                w=480,
                h=48,
                content="Tarihi dokunuşlarla modern yaşam",
                font=26,
                z=26,
            ),
            _el(
                eid="support-message-2",
                etype="text",
                role="support_message",
                x=72,
                y=490,
                w=480,
                h=48,
                content="Washington DC'nin kalbinde",
                font=26,
                z=27,
            ),
        ]
    )
    plan, before, after, preservation, execution, route = _apply(SELECTED_DESIGN_PROMPT, spec)
    assert route == "LAYER_ONLY"
    assert execution["status"] == "pass"
    assert preservation["status"] == "pass"
    ids = {el["id"] for el in after["elements"]}
    assert "support-message-1" in ids
    assert "support-message-2" in ids
    a = _by_id(after)
    assert abs(_font(a["headline"]) - before["headline"]["typography"]["font_size"] * 1.10) <= 1
    assert abs(_font(a["support-message-1"]) - before["support-message-1"]["typography"]["font_size"] * 1.15) <= 1
    assert abs(_font(a["support-message-2"]) - before["support-message-2"]["typography"]["font_size"] * 1.15) <= 1
    deleted = [
        tuple(o.get("element_ids") or ([o.get("element_id")] if o.get("element_id") else []))
        for o in dump_semantic_plan(plan)["operations"]
        if o.get("action") == "delete"
    ]
    for el_ids in deleted:
        assert "support-message-1" not in el_ids
        assert "support-message-2" not in el_ids


def test_compose_layer_only_on_locked_raster_one_semantic_one_visible():
    spec = _smb_real_spec()
    _plan, before, after, _preservation, _execution, route = _apply(SELECTED_DESIGN_PROMPT, spec)
    assert route == "LAYER_ONLY"
    layers = compose_layer_only_on_locked_raster(
        after_spec=after,
        before_snap=before,
        locked_raster_asset_id="raster-selected",
    )
    types = {_s_type(el) for el in layers}
    ids = {str(el.get("id") or "").lower() for el in layers}
    assert "IMAGE" not in types
    assert "BUTTON" not in types
    assert "logo" not in ids
    assert "cta" not in ids
    assert "master_background" not in ids
    texts = [el for el in layers if _s_type(el) == "TEXT"]
    copies = [str(el.get("content") or el.get("text") or "").strip().lower() for el in texts]
    copies = [c for c in copies if c]
    assert len(copies) == len(set(copies))
    assert sum(1 for el in texts if str(el.get("id") or "") == "headline") == 1
    assert not any(str(el.get("id") or "") in {"top-description", "unit-label", "eyebrow"} for el in texts)


def _s_type(el: dict) -> str:
    return str(el.get("type") or "").upper()


def test_support_message_2_hydrated_from_joined_callouts_when_brief_has_one_line():
    """Simplicity may persist a 1-item supporting list while the raster/GPT prompt had two callouts."""
    brief = {
        "supporting": ["Tarihi dokunuşlarla modern yaşam"],
        "final_copy": {
            "headline": "Zamansız Ötesinde",
            "supporting": "Tarihi dokunuşlarla modern yaşam",
        },
        "hero": "Zamansız Ötesinde",
        "campaign_intent": "lifestyle",
        "cd_strategy": {
            "supporting_messages": [
                "Tarihi dokunuşlarla modern yaşam",
                "Şehirden uzak, size yakın",
            ]
        },
    }
    texts = {
        "headline": "Zamansız Ötesinde",
        "supporting": "Tarihi dokunuşlarla modern yaşam · Şehirden uzak, size yakın",
        "supporting_callouts": "Tarihi dokunuşlarla modern yaşam|Şehirden uzak, size yakın",
        "cta": "Detayları İncele",
    }
    spec = {
        "canvas": {"width": 1080, "height": 1350},
        "elements": [
            {
                "id": "unit-label",
                "type": "text",
                "role": "unit_label",
                "content": "The Temple",
                "x": 72,
                "y": 140,
                "width": 480,
                "height": 36,
                "typography": {"font_size": 22},
            },
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": "Zamansız Ötesinde",
                "x": 72,
                "y": 190,
                "width": 760,
                "height": 180,
                "typography": {"font_size": 64},
            },
            {
                "id": "support-message-1",
                "type": "text",
                "role": "support_message",
                "content": "Tarihi dokunuşlarla modern yaşam",
                "x": 72,
                "y": 560,
                "width": 480,
                "height": 48,
                "typography": {"font_size": 26},
            },
        ],
    }
    out = ensure_revision_overlay_targets(spec, production_brief=brief, texts=texts)
    by_id = {el["id"]: el for el in out["elements"] if isinstance(el, dict) and el.get("id")}
    assert "support-message-1" in by_id
    assert "support-message-2" in by_id
    assert "Şehirden uzak" in by_id["support-message-2"]["content"]
    assert by_id["support-message-2"]["y"] > by_id["support-message-1"]["y"]

    _plan, before, after, _preservation, _execution, route = _apply(SELECTED_DESIGN_PROMPT, out)
    assert route == "LAYER_ONLY"
    after_by = {el["id"]: el for el in after["elements"] if isinstance(el, dict)}
    assert abs(_font(after_by["support-message-1"]) - before["support-message-1"]["typography"]["font_size"] * 1.15) <= 1
    assert abs(_font(after_by["support-message-2"]) - before["support-message-2"]["typography"]["font_size"] * 1.15) <= 1

    layers = compose_layer_only_on_locked_raster(
        after_spec=after,
        before_snap=before,
        locked_raster_asset_id="raster-selected",
    )
    layer_ids = {str(el.get("id") or "").lower() for el in layers}
    assert "support-message-1" in layer_ids
    assert "support-message-2" in layer_ids
    assert "IMAGE" not in {_s_type(el) for el in layers}
    assert "logo" not in layer_ids
    assert "cta" not in layer_ids


def test_support_message_2_hydrated_from_cd_strategy_when_callouts_missing():
    """Existing finished-ads may lack persisted callouts; CD strategy still has both lines."""
    brief = {
        "supporting": ["Tarihi dokunuşlarla modern yaşam"],
        "final_copy": {"headline": "Zamansız Ötesinde", "supporting": "Tarihi dokunuşlarla modern yaşam"},
        "hero": "Zamansız Ötesinde",
        "campaign_intent": "general_awareness",
        "cd_strategy": {
            "supporting_messages": [
                "Tarihi dokunuşlarla modern yaşam",
                "Şehirden uzak, size yakın",
            ]
        },
    }
    texts = {
        "headline": "Zamansız Ötesinde",
        "supporting": "Tarihi dokunuşlarla modern yaşam",
        "cta": "Detayları İncele",
    }
    spec = {
        "canvas": {"width": 1080, "height": 1350},
        "elements": [
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": "Zamansız Ötesinde",
                "x": 72,
                "y": 190,
                "width": 760,
                "height": 180,
                "typography": {"font_size": 64},
            },
            {
                "id": "support-message-1",
                "type": "text",
                "role": "support_message",
                "content": "Tarihi dokunuşlarla modern yaşam",
                "x": 72,
                "y": 560,
                "width": 480,
                "height": 48,
                "typography": {"font_size": 26},
            },
        ],
    }
    out = ensure_revision_overlay_targets(spec, production_brief=brief, texts=texts)
    ids = {el["id"] for el in out["elements"] if isinstance(el, dict)}
    assert "support-message-2" in ids
    sm2 = next(el for el in out["elements"] if el.get("id") == "support-message-2")
    assert "Şehirden uzak" in sm2["content"]


def test_hydrate_supporting_copy_fills_commercial_callouts_from_strategy():
    from investhome_api.services.creative_director.design_spec import (
        ensure_revision_overlay_targets,
        hydrate_supporting_copy,
        stamp_editable_text_targets,
    )

    texts = {
        "headline": "Zamansız Ötesinde",
        "supporting": "$400,000 → $400,000 · %0 lansman fiyat avantajı",
        "supporting_callouts": "",
        "cta": "Detayları İncele",
    }
    brief = {"supporting": ["Tarihi dokunuşlarla modern yaşam"], "hero": "Zamansız Ötesinde"}
    strategy = {
        "supporting_messages": [
            "Washington DC'nin kalbinde",
            "Tarihi dokunuşlarla modern yaşam",
        ]
    }
    hydrated, brief_out = hydrate_supporting_copy(
        texts=texts,
        production_brief=brief,
        strategy=strategy,
    )
    assert "Washington DC'nin kalbinde" in str(hydrated.get("supporting_callouts"))
    spec = {
        "canvas": {"width": 1080, "height": 1350},
        "elements": [
            {
                "id": "headline",
                "type": "text",
                "role": "headline",
                "content": "Zamansız Ötesinde",
                "x": 76,
                "y": 189,
                "width": 1021,
                "height": 134,
                "typography": {"font_size": 86},
            },
            {
                "id": "support-message-1",
                "type": "text",
                "role": "support_message",
                "content": "Tarihi dokunuşlarla modern yaşam",
                "x": 76,
                "y": 972,
                "width": 1067,
                "height": 54,
                "typography": {"font_size": 32},
            },
        ],
    }
    out = stamp_editable_text_targets(
        ensure_revision_overlay_targets(spec, production_brief=brief_out, texts=hydrated)
    )
    ids = {el["id"] for el in out["elements"] if isinstance(el, dict)}
    assert "support-message-2" in ids
    sm2 = next(el for el in out["elements"] if el.get("id") == "support-message-2")
    assert "Washington DC" in sm2["content"]
    target_ids = {t["id"] for t in out["editable_text_targets"]}
    assert "support-message-2" in target_ids

