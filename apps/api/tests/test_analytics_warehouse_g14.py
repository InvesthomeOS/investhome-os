"""G14 warehouse — currency, certification, recon helpers (unit-level)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from investhome_api.config.analytics_metric_registry import (
    CERTIFIED_METRIC_KEYS,
    get_metric,
    list_metrics,
)
from investhome_api.services.analytics_warehouse.currency import (
    REPORTING_CURRENCIES,
    SUPPORTED_CURRENCIES,
    date_key,
)
from investhome_api.services.analytics_warehouse.seed_catalog import CERTIFIED_KEYS


def test_supported_and_reporting_currencies() -> None:
    assert set(REPORTING_CURRENCIES).issubset(set(SUPPORTED_CURRENCIES))
    assert "USD" in REPORTING_CURRENCIES and "TRY" in REPORTING_CURRENCIES
    for ccy in ("EUR", "GBP", "AED"):
        assert ccy in SUPPORTED_CURRENCIES


def test_date_key_format() -> None:
    assert date_key(date(2026, 7, 20)) == 20260720


def test_certified_metric_subset_aligned() -> None:
    assert CERTIFIED_KEYS == CERTIFIED_METRIC_KEYS
    for key in CERTIFIED_METRIC_KEYS:
        m = get_metric(key)
        assert m is not None
        assert m.certification_status == "certified"


def test_no_duplicate_metric_keys() -> None:
    keys = [m.key for m in list_metrics()]
    assert len(keys) == len(set(keys))


def test_identity_fx_math() -> None:
    amount = Decimal("100.00")
    # Identity conversion: same currency rate 1.0
    assert (amount * Decimal("1")).quantize(Decimal("0.01")) == Decimal("100.00")
