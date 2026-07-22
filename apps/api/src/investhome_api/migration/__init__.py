"""G12 controlled data migration — dry-run, validate, reconcile.

Safety rules (non-negotiable):
- Never invent fake production data and call it migrated.
- Never auto-merge financial records.
- Prefer dry-run / staging; never claim production go-live without real sources + recon.
- Demo records must remain marked as demo until a real import + reconciliation passes.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
