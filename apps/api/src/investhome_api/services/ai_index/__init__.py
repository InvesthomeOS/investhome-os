"""AI Index foundation — read-only text knowledge layer over Drive-backed assets."""

# Intentionally light: avoid importing pipeline at package import time (circular with Drive).

__all__ = [
    "index_asset",
    "index_special_drive_file",
    "mark_inactive_for_asset",
    "mark_inactive_for_drive_file",
    "reindex_project",
]


def __getattr__(name: str):
    if name in __all__:
        from investhome_api.services.ai_index import pipeline

        return getattr(pipeline, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
