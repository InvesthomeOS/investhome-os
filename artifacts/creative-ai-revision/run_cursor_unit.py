"""Zero-GPT unit check for revision cursor (run inside API container)."""
from uuid import uuid4

from investhome_api.services.creative_director.revision import (
    move_revision_cursor,
    normalize_revision_cursor,
    truncate_forward_history,
)

a, b, c, d = (str(uuid4()) for _ in range(4))
history = [
    {"version": "original", "new_asset_id": a, "previous_asset_id": None},
    {"version": "v2", "new_asset_id": b, "previous_asset_id": a},
    {"version": "v3", "new_asset_id": c, "previous_asset_id": b},
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
entries, index, asset = move_revision_cursor(entries, index, delta=-1)
assert asset == b and index == 1
kept, tip = truncate_forward_history(entries, index)
assert [h["new_asset_id"] for h in kept] == [a, b]
kept.append({"version": "v4", "new_asset_id": d, "previous_asset_id": b})
entries, index = normalize_revision_cursor(kept, len(kept) - 1)
assert [h["new_asset_id"] for h in entries] == [a, b, d]
assert index == 2
print({"ok": True, "gpt_calls": 0, "history": [a[:8], b[:8], d[:8]], "index": index})
