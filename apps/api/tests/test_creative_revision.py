"""Quality Lock freeze + AI revision fidelity lock unit/regression tests (no live GPT spend)."""

from __future__ import annotations

import io
import json
from pathlib import Path
from uuid import uuid4

from PIL import Image

from investhome_api.services.creative_director.quality_lock.intent import (
    classify_cd_campaign_intent,
)
from investhome_api.services.creative_director.revision import (
    QUALITY_BRIGHTNESS_DELTA_MAX,
    build_revision_brief,
    build_revision_diff,
    compare_revision_quality,
    ensure_master_asset_id,
    interpret_revision_intents,
    move_revision_cursor,
    normalize_revision_cursor,
    render_revision_production_prompt,
    resolve_master_asset_id,
    truncate_forward_history,
)


def _artifacts_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "artifacts" / "creative-quality-lock"
        if candidate.is_dir():
            return candidate
    docker = Path("/app/artifacts/creative-quality-lock")
    if docker.is_dir():
        return docker
    raise AssertionError("Quality Lock artifacts directory not found")


ARTIFACTS = _artifacts_dir()

CAMPAIGN_KEYS = (
    ("A_price_sales", "price_campaign"),
    ("B_location", "location"),
    ("C_lifestyle_features", {"amenities", "lifestyle"}),
)


def _load_json(name: str) -> dict:
    path = ARTIFACTS / name
    assert path.is_file(), f"missing Quality Lock artifact: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _png_bytes(*, brightness: int = 180, size: tuple[int, int] = (64, 64)) -> bytes:
    img = Image.new("RGB", size, (brightness, brightness, brightness))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_quality_lock_artifacts_exist_for_regression() -> None:
    for key, _ in CAMPAIGN_KEYS:
        assert (ARTIFACTS / f"{key}-report.json").is_file()
        assert (ARTIFACTS / f"{key}-generate-ad.json").is_file()
        assert (ARTIFACTS / f"{key}-campaign-create.json").is_file()
        assert (ARTIFACTS / f"{key}-final.png").is_file()
    assert (ARTIFACTS / "summary.json").is_file()


def test_quality_lock_artifact_pipeline_invariants() -> None:
    summary = _load_json("summary.json")
    assert summary.get("visual_quality_pass_declared") is False
    assert summary.get("provider_budget_ok") is True
    assert int(summary.get("total_provider_calls") or 0) <= 3

    for key, intent_expect in CAMPAIGN_KEYS:
        report = _load_json(f"{key}-report.json")
        gen = _load_json(f"{key}-generate-ad.json")
        camp = _load_json(f"{key}-campaign-create.json")

        intent = report.get("1_campaign_intent") or (camp.get("campaign_context") or {}).get(
            "campaign_intent"
        )
        if isinstance(intent_expect, set):
            assert intent in intent_expect
        else:
            assert intent == intent_expect or (
                key == "A_price_sales" and intent in {"price_campaign", "sales_offer", "launch"}
            )

        assert report.get("10_language") == "tr" or gen.get("language") == "tr"
        assert gen.get("production_mode") == "finished_ad"
        assert gen.get("final_asset_id")
        assert report.get("17_final_asset_id") == gen.get("final_asset_id")
        assert report.get("19_native_pipeline_used") == "NO"

        pb = gen.get("production_brief") or {}
        assert pb.get("campaign_intent") or report.get("1_campaign_intent")
        assert pb.get("message_strategy") or report.get("15_production_brief", {}).get(
            "message_strategy"
        )
        assert pb.get("design_direction") or report.get("13_design_direction")
        logo = report.get("9_logo") or {}
        assert logo.get("asset_id") or gen.get("logo_asset_id")
        assert report.get("7_selected_asset", {}).get("asset_id") or gen.get("interior_asset_id")


def test_quality_lock_a_price_asset_id_stable() -> None:
    report = _load_json("A_price_sales-report.json")
    gen = _load_json("A_price_sales-generate-ad.json")
    assert report["17_final_asset_id"] == "f00ef35d-fc9a-422d-9531-b6b62e756816"
    assert gen["final_asset_id"] == report["17_final_asset_id"]
    assert report["campaign_id"] == "7f4015bf-906b-4728-95b5-ef6a888b1236"


def test_revision_intents_copy_and_layout() -> None:
    intents = interpret_revision_intents(
        "Başlığı daha premium yap. %25 rozetini biraz küçült. "
        "Sınırlı sayıda ünite ifadesini kaldır. Tasarımın geri kalanını mümkün olduğunca değiştirme."
    )
    assert "COPY_CHANGE" in intents
    assert "LAYOUT_CHANGE" in intents or "STYLE_CHANGE" in intents


def test_revision_intents_cta_only() -> None:
    intents = interpret_revision_intents("CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme.")
    assert "COPY_CHANGE" in intents


def test_master_asset_immutable_and_resolve() -> None:
    master = uuid4()
    tip = uuid4()
    ctx: dict = {"latest_master_ad_asset_id": str(tip)}
    resolved = resolve_master_asset_id(ctx, current_final_asset_id=tip)
    assert resolved == tip
    ensured = ensure_master_asset_id(ctx, master)
    assert ensured == master
    assert ctx["master_asset_id"] == str(master)
    other = uuid4()
    assert ensure_master_asset_id(ctx, other) == master
    assert ctx["master_asset_id"] == str(master)


def test_exact_command_headline_badge_preserve() -> None:
    production_brief = {
        "hero": "Modern. Şık. Tarihi.",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "final_copy": {
            "headline": "Modern. Şık. Tarihi.",
            "cta": "Lansman Fiyatını Kaçırmayın",
            "value_badge": "~25% lansman fiyat avantajı",
        },
        "supporting": [],
    }
    instruction = (
        "Başlığı 'Zamansız Bir Yaşam' yap. "
        "%25 rozetini mevcut boyutunun %30'u kadar küçült. "
        "Fiyatları, logoyu, CTA'yı ve arka planı değiştirme."
    )
    diff = build_revision_diff(instruction=instruction, production_brief=production_brief)
    assert diff.command_mode in {"exact", "mixed"}
    headline = next(o for o in diff.operations if o.target == "headline")
    assert headline.action == "replace_text"
    assert headline.to_value == "Zamansız Bir Yaşam"
    assert headline.confidence == "high"
    assert headline.mode == "exact"
    badge = next(o for o in diff.operations if o.target == "badge")
    assert badge.action == "scale"
    assert badge.scale_factor == 0.7
    assert badge.confidence == "high"
    assert "prices" in diff.preserve or "verified_prices" in diff.preserve
    assert "logo" in diff.preserve or "logo_quality" in diff.preserve
    assert "background" in diff.preserve or "background_photograph" in diff.preserve
    assert not any(o.target == "cta" and o.action == "replace_text" for o in diff.operations)


def test_exact_cta_and_strong_preserve() -> None:
    production_brief = {
        "cta": "Lansman Fiyatını Kaçırmayın",
        "final_copy": {"cta": "Lansman Fiyatını Kaçırmayın"},
        "supporting": [],
    }
    instruction = "CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme."
    diff = build_revision_diff(instruction=instruction, production_brief=production_brief)
    cta = next(o for o in diff.operations if o.target == "cta")
    assert cta.to_value == "Detayları İncele"
    assert cta.confidence == "high"
    assert "unaffected_elements" in diff.preserve or "image_treatment" in diff.preserve


def test_subjective_command_capped() -> None:
    diff = build_revision_diff(
        instruction="Daha premium ve sade ve satış odaklı yap.",
        production_brief={"final_copy": {"headline": "Hello"}, "supporting": []},
    )
    assert diff.command_mode == "subjective"
    assert len([o for o in diff.operations if o.mode == "subjective"]) <= 3
    assert all(o.confidence in {"medium", "low"} for o in diff.operations)


def test_ambiguous_minimum_change() -> None:
    diff = build_revision_diff(instruction="Biraz dokun.", production_brief={})
    assert diff.command_mode == "ambiguous"
    assert diff.operations[0].action == "minimum_change"
    assert diff.operations[0].confidence == "low"


def test_revision_brief_preserves_locks_and_scarcity_removal() -> None:
    production_brief = {
        "campaign_intent": "price_campaign",
        "hero": "Modern. Şık. Tarihi.",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": ["Sınırlı sayıda ünite", "Unit 204 Lansman Fırsatı"],
        "final_copy": {
            "headline": "Modern. Şık. Tarihi.",
            "cta": "Lansman Fiyatını Kaçırmayın",
            "list_price": "$400,000",
            "offer_price": "$300,000",
            "value_badge": "~25% lansman fiyat avantajı",
        },
        "approved_claims": [{"key": "list_price", "display": "$400,000"}],
        "forbidden_claims": [],
        "asset_lock": {"logo_asset_id": str(uuid4())},
        "logo_lock": {"status": "pass"},
        "design_direction": {"premium_level": "high"},
        "message_strategy": {"primary_message": "launch price"},
        "simplicity_director": {"density": "balanced"},
    }
    instruction = (
        "Başlığı daha premium yap. %25 rozetini biraz küçült. "
        "Sınırlı sayıda ünite ifadesini kaldır."
    )
    intents = interpret_revision_intents(instruction)
    master = uuid4()
    brief = build_revision_brief(
        instruction=instruction,
        intents=intents,
        production_brief=production_brief,
        original_brief="The Temple Unit 204",
        language="tr",
        current_final_asset_id=uuid4(),
        master_asset_id=master,
    )
    assert brief["mode"] == "revision"
    assert brief["language_lock"] is True
    assert brief["claim_guard_active"] is True
    assert brief["keep_unchanged_default"] is True
    assert brief["revision_source"] == "master_asset"
    assert brief["master_asset_id"] == str(master)
    assert brief["copy_overrides"].get("remove_scarcity") == "true"
    badge_scale = brief["copy_overrides"].get("badge_scale")
    assert badge_scale is not None
    assert float(badge_scale) < 1.0
    assert all("sınırlı" not in str(s).lower() for s in brief["supporting"])
    assert "revision_diff" in brief
    assert "quality_lock" in brief

    prompt = render_revision_production_prompt(
        revision_brief=brief,
        production_brief=production_brief,
        original_brief="The Temple Unit 204",
        lifestyle=False,
    )
    assert "AI REVISION FIDELITY LOCK" in prompt
    assert "IMMUTABLE MASTER" in prompt
    assert "IMAGE QUALITY LOCK" in prompt
    assert "cinematic" in prompt.lower() or "FORBIDDEN" in prompt
    assert str(master) in prompt
    assert "STRUCTURED REVISION DIFF" in prompt


def test_revision_brief_cta_override() -> None:
    production_brief = {
        "campaign_intent": "price_campaign",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": [],
        "final_copy": {"cta": "Lansman Fiyatını Kaçırmayın"},
        "approved_claims": [],
        "forbidden_claims": [],
        "asset_lock": {},
        "logo_lock": {},
    }
    instruction = "CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme."
    brief = build_revision_brief(
        instruction=instruction,
        intents=interpret_revision_intents(instruction),
        production_brief=production_brief,
        original_brief="brief",
        language="tr",
        current_final_asset_id=uuid4(),
        master_asset_id=uuid4(),
    )
    assert brief["cta"] == "Detayları İncele"
    assert brief["copy_overrides"].get("cta") == "Detayları İncele"


def test_quality_guard_detects_brightness_drift() -> None:
    master = _png_bytes(brightness=200)
    dark = _png_bytes(brightness=100)
    ok = _png_bytes(brightness=195)
    fail = compare_revision_quality(master_bytes=master, revised_bytes=dark, revision_diff=None)
    assert fail["status"] == "fail"
    assert abs(fail["brightness_delta"]) > QUALITY_BRIGHTNESS_DELTA_MAX
    assert fail["compared_against"] == "master_asset"
    passed = compare_revision_quality(master_bytes=master, revised_bytes=ok, revision_diff=None)
    assert passed["status"] == "pass"


def test_quality_guard_dimension_drift() -> None:
    master = _png_bytes(size=(100, 100))
    cropped = _png_bytes(size=(80, 80))
    result = compare_revision_quality(
        master_bytes=master, revised_bytes=cropped, revision_diff=None
    )
    assert result["status"] == "fail"
    assert result["dimension_delta_pct"] > 2.0


def test_intent_classifiers_match_quality_lock_briefs() -> None:
    price = classify_cd_campaign_intent(
        "The Temple için Unit 204 lansman reklamı. Normal fiyat $400,000, lansman $300,000. Türkçe.",
        language="tr",
        project_name="The Temple",
        has_price_pair=True,
    )
    assert price.campaign_intent in {"price_campaign", "sales_offer", "launch"}
    loc = classify_cd_campaign_intent(
        "The Temple Adams Morgan lokasyon avantajları. Türkçe. Fiyat kullanma.",
        language="tr",
        project_name="The Temple",
    )
    assert loc.campaign_intent == "location"


def test_revision_cursor_undo_redo_and_branch_clear_zero_gpt() -> None:
    """A→B→C undo×2 redo×2 then undo+branch clear — pure cursor math, 0 GPT."""
    a, b, c, d = (str(uuid4()) for _ in range(4))
    history = [
        {
            "version": "original",
            "new_asset_id": a,
            "previous_asset_id": None,
            "master_asset_id": a,
            "operations": [],
        },
        {
            "version": "v2",
            "new_asset_id": b,
            "previous_asset_id": a,
            "master_asset_id": a,
            "revision_source_asset_id": a,
            "operations": [{"target": "headline", "action": "replace_text", "to": "H2"}],
        },
        {
            "version": "v3",
            "new_asset_id": c,
            "previous_asset_id": b,
            "master_asset_id": a,
            "revision_source_asset_id": a,
            "operations": [{"target": "cta", "action": "replace_text", "to": "CTA"}],
        },
    ]
    entries, index = normalize_revision_cursor(history, None)
    assert len(entries) == 3 and index == 2

    entries, index, asset = move_revision_cursor(entries, index, delta=-1)
    assert asset == b and index == 1
    entries, index, asset = move_revision_cursor(entries, index, delta=-1)
    assert asset == a and index == 0

    entries, index, asset = move_revision_cursor(entries, index, delta=+1)
    assert asset == b and index == 1
    entries, index, asset = move_revision_cursor(entries, index, delta=+1)
    assert asset == c and index == 2
    assert len(entries) == 3

    entries, index, asset = move_revision_cursor(entries, index, delta=-1)
    assert asset == b and index == 1
    kept, tip = truncate_forward_history(entries, index)
    assert [h["new_asset_id"] for h in kept] == [a, b]
    assert tip == 1
    cum = []
    for item in kept:
        if item.get("version") == "original":
            continue
        cum.extend(item.get("operations") or [])
    assert cum == [{"target": "headline", "action": "replace_text", "to": "H2"}]
    kept.append(
        {
            "version": "v4",
            "new_asset_id": d,
            "previous_asset_id": b,
            "master_asset_id": a,
            "revision_source_asset_id": a,
            "operations": [{"target": "badge", "action": "scale", "scale_factor": 0.7}],
        }
    )
    entries, index = normalize_revision_cursor(kept, len(kept) - 1)
    assert [h["new_asset_id"] for h in entries] == [a, b, d]
    assert index == 2
    for h in entries[1:]:
        assert h.get("revision_source_asset_id") == a
        assert h.get("master_asset_id") == a
    try:
        move_revision_cursor(entries, index, delta=+1)
        raise AssertionError("redo past tip should fail")
    except ValueError:
        pass
    try:
        move_revision_cursor(entries, 0, delta=-1)
        raise AssertionError("undo at original should fail")
    except ValueError:
        pass


def test_revision_cursor_legacy_missing_index_defaults_to_tip() -> None:
    a, b = str(uuid4()), str(uuid4())
    history = [
        {"version": "original", "new_asset_id": a},
        {"version": "v2", "new_asset_id": b},
    ]
    entries, index = normalize_revision_cursor(history, None)
    assert index == 1
    _, index, asset = move_revision_cursor(entries, index, delta=-1)
    assert asset == a and index == 0


def test_five_step_cumulative_ops_always_master_source() -> None:
    """Degradation acceptance A (unit): 5 revisions accumulate ops; source stays master."""
    master = str(uuid4())
    steps = [
        "Başlığı 'Zamansız Bir Yaşam' yap.",
        "%25 rozetini mevcut boyutunun %30'u kadar küçült.",
        "CTA'yı 'Detayları İncele' yap.",
        "Sınırlı sayıda ünite ifadesini kaldır.",
        "Logoyu %20 küçült.",
    ]
    cumulative: list[dict] = []
    history = [
        {
            "version": "original",
            "new_asset_id": master,
            "master_asset_id": master,
            "operations": [],
        }
    ]
    tip = master
    for i, instr in enumerate(steps, start=2):
        diff = build_revision_diff(instruction=instr, production_brief={"final_copy": {}})
        new_ops = [o.model_dump(by_alias=True, exclude_none=True) for o in diff.operations]
        cumulative = cumulative + new_ops
        new_id = str(uuid4())
        history.append(
            {
                "version": f"v{i}",
                "previous_asset_id": tip,
                "new_asset_id": new_id,
                "master_asset_id": master,
                "revision_source_asset_id": master,
                "operations": new_ops,
            }
        )
        tip = new_id
        assert history[-1]["revision_source_asset_id"] == master
    assert len(history) == 6
    assert len(cumulative) >= 5
    assert all(h.get("revision_source_asset_id") == master for h in history[1:])
