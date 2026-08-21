"""Zero-GPT unit check for revision fidelity lock (run inside API container / venv)."""

from uuid import uuid4

from investhome_api.services.creative_director.revision import (
    build_revision_diff,
    compare_revision_quality,
    ensure_master_asset_id,
    move_revision_cursor,
    normalize_revision_cursor,
    truncate_forward_history,
)
from PIL import Image
import io


def _png(brightness: int = 180) -> bytes:
    img = Image.new("RGB", (32, 32), (brightness, brightness, brightness))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


a, b, c, d = (str(uuid4()) for _ in range(4))
history = [
    {"version": "original", "new_asset_id": a, "master_asset_id": a, "operations": []},
    {
        "version": "v2",
        "new_asset_id": b,
        "previous_asset_id": a,
        "master_asset_id": a,
        "revision_source_asset_id": a,
        "operations": [{"target": "headline", "action": "replace_text", "to": "H"}],
    },
    {
        "version": "v3",
        "new_asset_id": c,
        "previous_asset_id": b,
        "master_asset_id": a,
        "revision_source_asset_id": a,
        "operations": [{"target": "cta", "action": "replace_text", "to": "C"}],
    },
]
entries, index = normalize_revision_cursor(history, None)
assert index == 2
entries, index, asset = move_revision_cursor(entries, index, delta=-1)
assert asset == b
kept, tip = truncate_forward_history(entries, index)
assert [h["new_asset_id"] for h in kept] == [a, b]
kept.append(
    {
        "version": "v4",
        "new_asset_id": d,
        "master_asset_id": a,
        "revision_source_asset_id": a,
        "operations": [{"target": "badge", "action": "scale", "scale_factor": 0.7}],
    }
)
assert all(h.get("revision_source_asset_id") == a for h in kept[1:])

ctx: dict = {}
ensure_master_asset_id(ctx, uuid4())
m1 = ctx["master_asset_id"]
ensure_master_asset_id(ctx, uuid4())
assert ctx["master_asset_id"] == m1

diff = build_revision_diff(
    instruction=(
        "Başlığı 'Zamansız Bir Yaşam' yap. "
        "%25 rozetini mevcut boyutunun %30'u kadar küçült. "
        "Fiyatları, logoyu, CTA'yı ve arka planı değiştirme."
    ),
    production_brief={"final_copy": {"headline": "X"}},
)
assert next(o for o in diff.operations if o.target == "headline").to_value == "Zamansız Bir Yaşam"
assert next(o for o in diff.operations if o.target == "badge").scale_factor == 0.7

qg = compare_revision_quality(master_bytes=_png(200), revised_bytes=_png(80))
assert qg["status"] == "fail"

print(
    {
        "ok": True,
        "gpt_calls": 0,
        "master_immutable": True,
        "badge_scale": 0.7,
        "quality_guard_fail_on_darken": True,
    }
)
