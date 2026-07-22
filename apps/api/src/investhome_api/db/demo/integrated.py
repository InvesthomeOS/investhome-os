"""Orchestrator for integrated demo data layers (idempotent)."""

from __future__ import annotations

from investhome_api.db.demo.safety import assert_demo_seed_allowed
from investhome_api.db.demo.seed_crm import seed_crm
from investhome_api.db.demo.seed_finance_links import seed_finance_links
from investhome_api.db.demo.seed_inventory_units import seed_inventory_units
from investhome_api.db.demo.seed_marketing import seed_marketing
from investhome_api.db.demo.seed_ops_reports_ai import seed_ops_reports_ai
from investhome_api.db.demo.seed_projects_extended import seed_projects_extended
from investhome_api.db.demo.seed_sales_chain import seed_sales_chain
from investhome_api.db.demo.seed_users_extended import seed_users_extended


def seed_integrated_demo() -> dict[str, object]:
    """Run all extended/idempotent demo layers after foundational seed.

    Returns a nested counts dict suitable for logging / CLI output.
    Each domain is isolated so one failure does not block the others.
    """
    assert_demo_seed_allowed()

    results: dict[str, object] = {}
    steps = [
        ("users_extended", seed_users_extended),
        ("projects_extended", seed_projects_extended),
        ("inventory_units", seed_inventory_units),
        ("crm", seed_crm),
        ("sales_chain", seed_sales_chain),
        ("marketing", seed_marketing),
        ("finance_links", seed_finance_links),
        ("ops_reports_ai", seed_ops_reports_ai),
    ]
    for key, fn in steps:
        try:
            results[key] = fn()
        except Exception as exc:  # noqa: BLE001 — domain isolation for demo seed
            results[key] = {"error": f"{type(exc).__name__}: {exc}"}
            print(f"Demo seed step '{key}' failed: {type(exc).__name__}: {exc}")
    return results

