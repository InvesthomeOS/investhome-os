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
    x0, y0, x1, y1 = zone["x0"], zone["y0"], zone["x1"], zone["y1"]

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
