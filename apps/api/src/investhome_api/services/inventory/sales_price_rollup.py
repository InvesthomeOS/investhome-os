"""Read-only project totals for inventory sale prices.

This does not write budget lines, proforma versions, or inventory rows.
Internal and customer proformas stay on project_budget_versions.audience.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.inventory import InventoryAsset, InventoryAssetPrice, PriceStatus, PriceType

SALE_PRICE_TYPES = (
    PriceType.LIST,
    PriceType.CONTRACTED,
    PriceType.ESTIMATED_RENT,
)


def project_sales_price_totals(db: Session, project_id: UUID) -> dict[str, object]:
    """Sum active inventory prices for one project, grouped by currency and type."""
    rows = db.execute(
        select(
            InventoryAssetPrice.currency,
            InventoryAssetPrice.price_type,
            InventoryAssetPrice.source,
            func.coalesce(func.sum(InventoryAssetPrice.amount), 0),
            func.count(InventoryAssetPrice.id),
        )
        .join(InventoryAsset, InventoryAsset.id == InventoryAssetPrice.inventory_asset_id)
        .where(
            InventoryAsset.project_id == project_id,
            InventoryAsset.archived_at.is_(None),
            InventoryAssetPrice.status == PriceStatus.ACTIVE,
            InventoryAssetPrice.archived_at.is_(None),
            InventoryAssetPrice.price_type.in_(SALE_PRICE_TYPES),
        )
        .group_by(
            InventoryAssetPrice.currency,
            InventoryAssetPrice.price_type,
            InventoryAssetPrice.source,
        )
    ).all()

    currencies: dict[str, dict[str, str]] = {}
    sources: dict[str, dict[str, int]] = {}
    for currency, price_type, source, amount, count in rows:
        bucket = currencies.setdefault(
            currency,
            {"list": "0.00", "contracted": "0.00", "estimated_rent": "0.00"},
        )
        key = price_type.value
        bucket[key] = str(
            (Decimal(bucket[key]) + Decimal(amount)).quantize(Decimal("0.01"))
        )
        source_bucket = sources.setdefault(key, {})
        source_name = source.value if hasattr(source, "value") else str(source)
        source_bucket[source_name] = source_bucket.get(source_name, 0) + int(count)

    return {
        "project_id": str(project_id),
        "currencies": currencies,
        "active_price_sources": sources,
        "scenario_estimate": None,
        "budget_written": False,
        "proforma_audience": {
            "internal": "project_budget_versions.audience = internal",
            "customer": "project_budget_versions.audience = customer",
        },
    }
