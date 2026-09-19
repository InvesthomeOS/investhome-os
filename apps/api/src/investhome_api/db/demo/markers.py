"""Demo-data markers for CRM demo cleanup (no Creative Studio seed)."""

from __future__ import annotations

from typing import Any

INTEGRATED_DEMO_SOURCE = "integrated_demo_seed"

DEMO_METADATA: dict[str, Any] = {
    "demo_seed": True,
    "source": INTEGRATED_DEMO_SOURCE,
}


def mark_demo_payload(payload: dict[str, Any], *, has_is_demo: bool = True) -> dict[str, Any]:
    """Return a copy of *payload* stamped with demo markers.

    Prefer ``is_demo=True`` when the model has that column. Always attach
    ``source`` / ``metadata_json`` when those keys are accepted by the caller.
    """
    marked = dict(payload)
    if has_is_demo:
        marked.setdefault("is_demo", True)
    if "source" not in marked:
        marked["source"] = INTEGRATED_DEMO_SOURCE
    existing_meta = marked.get("metadata_json")
    if isinstance(existing_meta, dict):
        marked["metadata_json"] = {**DEMO_METADATA, **existing_meta}
    else:
        marked["metadata_json"] = dict(DEMO_METADATA)
    return marked


def is_demo_metadata(value: object | None) -> bool:
    """True when a JSON/metadata blob was produced by the integrated demo seed."""
    if not isinstance(value, dict):
        return False
    if value.get("demo_seed") is True:
        return True
    return value.get("source") == INTEGRATED_DEMO_SOURCE


def is_demo_source(value: object | None) -> bool:
    return value == INTEGRATED_DEMO_SOURCE
