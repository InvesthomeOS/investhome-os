"""PRICE_BLOCK_ONLY — parser + leak-closed local zone (no GPT, no generation)."""

from __future__ import annotations

import io

from investhome_api.services.creative_director.price_block_revision import (
    apply_local_price_zone,
    parse_price_block,
)
from investhome_api.services.creative_director.revision_intelligence import interpret_revision_plan

INSTRUCTION = (
    "675.000 USD liste fiyatının üzerini çiz.\n"
    "Lansman fiyatını 438.750 USD yap.\n"
    "Altına Kazancınız 236.250 USD yaz.\n"
    "Tasarımın geri kalan hiçbir şeyini değiştirme."
)


def test_parse_price_block_real_turkish_command() -> None:
    intent = parse_price_block(INSTRUCTION)
    assert intent is not None
    assert intent.scope == "PRICE_BLOCK_ONLY"
    assert intent.list_amount == 675_000
    assert intent.launch_amount == 438_750
    assert intent.savings_amount == 236_250
    assert intent.list_strikethrough is True
    assert intent.launch_label == "LANSMAN FİYATI"
    assert intent.savings_label == "KAZANCINIZ"
    ops = intent.operations()
    ids = [o.element_id for o in ops]
    assert ids == ["old-price", "new-price", "savings-price"]
    assert ops[0].to_value == "675.000 USD"
    assert ops[1].to_value == "438.750 USD"
    assert ops[2].to_value == "236.250 USD"


def test_revision_plan_price_block_does_not_fall_through() -> None:
    plan = interpret_revision_plan(instruction=INSTRUCTION)
    assert plan.strict_preserve is True
    assert "headline" in plan.preserve
    assert "verified_prices" not in plan.preserve
    targets = {(o.element_id, o.to_value) for o in plan.operations}
    assert ("old-price", "675.000 USD") in targets
    assert ("new-price", "438.750 USD") in targets
    assert ("savings-price", "236.250 USD") in targets
    assert all(o.action != "minimum_change" for o in plan.operations)


def test_apply_local_price_zone_does_not_leak_outside_bbox() -> None:
    from PIL import Image

    img = Image.new("RGB", (400, 500), (28, 22, 18))
    for y in range(438, 472):
        for x in range(148, 252):
            if (x + y) % 2 == 0:
                img.putpixel((x, y), (245, 241, 234))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    source = buf.getvalue()

    intent = parse_price_block(INSTRUCTION)
    assert intent is not None
    patched, trace = apply_local_price_zone(source, spec=None, intent=intent)
    assert trace["provider_calls"] == 0
    assert trace["baked"] is True
    zone = trace["zone"]
    cleanup = trace["cleanup_box"]
    glyph = trace["glyph_zone"]
    x0, y0, x1, y1 = zone["x0"], zone["y0"], zone["x1"], zone["y1"]
    cw = cleanup["x1"] - cleanup["x0"]
    ch = cleanup["y1"] - cleanup["y0"]
    dw = x1 - x0
    dh = y1 - y0
    assert ch < dh
    assert cw * ch < dw * dh
    assert (glyph["y1"] - glyph["y0"]) <= ch

    original = Image.open(io.BytesIO(source)).convert("RGB")
    after = Image.open(io.BytesIO(patched)).convert("RGB")
    leaked = 0
    for y in range(original.size[1]):
        for x in range(original.size[0]):
            if x0 <= x < x1 and y0 <= y < y1:
                continue
            if original.getpixel((x, y)) != after.getpixel((x, y)):
                leaked += 1
    assert leaked == 0
    assert after.size == original.size


def test_oversized_design_spec_does_not_inflate_cleanup() -> None:
    from PIL import Image

    img = Image.new("RGB", (400, 500), (28, 22, 18))
    for y in range(438, 472):
        for x in range(148, 252):
            if (x + y) % 2 == 0:
                img.putpixel((x, y), (245, 241, 234))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    intent = parse_price_block(INSTRUCTION)
    assert intent is not None
    huge_spec = {
        "elements": [
            {"id": "old-price", "content": "675.000 USD", "x": 0, "y": 0, "width": 400, "height": 400}
        ]
    }
    _patched, trace = apply_local_price_zone(buf.getvalue(), spec=huge_spec, intent=intent)
    cleanup = trace["cleanup_box"]
    assert (cleanup["x1"] - cleanup["x0"]) * (cleanup["y1"] - cleanup["y0"]) < 0.12 * 400 * 500
    assert cleanup["y0"] > 350


def test_wood_grain_outside_glyph_mask_is_unchanged() -> None:
    from PIL import Image

    img = Image.new("RGB", (400, 500), (40, 28, 18))
    for y in range(400, 500):
        tone = 28 + (y % 7) * 4
        for x in range(400):
            img.putpixel((x, y), (tone + (x % 5), tone, 16))
    for y in range(438, 468):
        for x in range(150, 250):
            img.putpixel((x, y), (245, 241, 234))
    before = img.copy()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    intent = parse_price_block(INSTRUCTION)
    assert intent is not None
    patched, trace = apply_local_price_zone(buf.getvalue(), spec=None, intent=intent)
    after = Image.open(io.BytesIO(patched)).convert("RGB")
    far = 0
    for y in range(400, 500):
        for x in range(0, 40):
            if before.getpixel((x, y)) != after.getpixel((x, y)):
                far += 1
    assert far == 0
    zone = trace["zone"]
    leaked = 0
    for y in range(500):
        for x in range(400):
            if zone["x0"] <= x < zone["x1"] and zone["y0"] <= y < zone["y1"]:
                continue
            if before.getpixel((x, y)) != after.getpixel((x, y)):
                leaked += 1
    assert leaked == 0


def test_overlay_stats_band_price_does_not_touch_hero() -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (400, 500), (12, 16, 28))
    draw = ImageDraw.Draw(img)
    draw.rectangle((155, 132, 250, 168), fill=(245, 241, 234))
    for y in range(210, 500):
        for x in range(400):
            img.putpixel((x, y), (110, 100, 90))
    before = img.copy()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    intent = parse_price_block(INSTRUCTION)
    assert intent is not None
    patched, trace = apply_local_price_zone(buf.getvalue(), spec=None, intent=intent)
    assert trace["provider_calls"] == 0
    assert trace["method"] == "overlay_list_price_strikethrough"
    after = Image.open(io.BytesIO(patched)).convert("RGB")
    hero_changed = 0
    for y in range(210, 500):
        for x in range(400):
            if before.getpixel((x, y)) != after.getpixel((x, y)):
                hero_changed += 1
    assert hero_changed == 0
    assert after.size == before.size
