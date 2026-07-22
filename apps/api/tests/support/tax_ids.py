"""Valid tax-ID fixtures matching company_management_service.COUNTRY_TAX_ID_STUBS."""

from __future__ import annotations

# TR: 10–11 digits. US: NN-NNNNNNN.
VALID_TR_TAX_IDS = (
    "1234567890",
    "9876543210",
    "1111111111",
    "2222222222",
    "3333333333",
    "4444444444",
    "5555555555",
    "6666666666",
    "7777777777",
    "8888888888",
    "9999999990",
    "9999999991",
    "9999999992",
    "9999999993",
    "9999999994",
    "9999999995",
    "9999999996",
    "9999999997",
    "9999999998",
    "9999999999",
    "12345678901",
)

VALID_US_TAX_ID = "12-3456789"


def tr_tax_id(seed: int = 0) -> str:
    """Return a unique valid TR tax ID for fixtures (10 digits)."""
    return f"{(1000000000 + (seed % 9000000000)):010d}"


def us_tax_id(seed: int = 0) -> str:
    """Return a unique valid US EIN-style tax ID for fixtures."""
    suffix = 3456789 + (seed % 1000000)
    prefix = 10 + (seed % 89)
    return f"{prefix:02d}-{suffix:07d}"
