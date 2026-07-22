"""Multi-currency helpers — never overwrite original amounts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.analytics_warehouse import WhFxRate

SUPPORTED_CURRENCIES = ("USD", "TRY", "EUR", "GBP", "AED")
REPORTING_CURRENCIES = ("USD", "TRY")


def date_key(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def get_fx_rate(
    db: Session,
    *,
    rate_date: date,
    from_currency: str,
    to_currency: str,
) -> Decimal | None:
    src = from_currency.upper()
    dst = to_currency.upper()
    if src == dst:
        return Decimal("1")
    row = db.scalar(
        select(WhFxRate).where(
            WhFxRate.rate_date == rate_date,
            WhFxRate.from_currency == src,
            WhFxRate.to_currency == dst,
        )
    )
    if row:
        return Decimal(row.rate)
    # Fall back to most recent prior rate (explicit; not silent invent)
    row = db.scalar(
        select(WhFxRate)
        .where(
            WhFxRate.rate_date <= rate_date,
            WhFxRate.from_currency == src,
            WhFxRate.to_currency == dst,
        )
        .order_by(WhFxRate.rate_date.desc())
        .limit(1)
    )
    return Decimal(row.rate) if row else None


def convert_reporting(
    db: Session,
    *,
    amount: Decimal,
    currency: str,
    as_of: date,
) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
    """Return (amount_usd, amount_try, fx_usd, fx_try). Missing FX → None (honest)."""
    ccy = (currency or "USD").upper()
    fx_usd = get_fx_rate(db, rate_date=as_of, from_currency=ccy, to_currency="USD")
    fx_try = get_fx_rate(db, rate_date=as_of, from_currency=ccy, to_currency="TRY")
    amount_usd = (amount * fx_usd).quantize(Decimal("0.01")) if fx_usd is not None else None
    amount_try = (amount * fx_try).quantize(Decimal("0.01")) if fx_try is not None else None
    return amount_usd, amount_try, fx_usd, fx_try


def ensure_identity_fx(db: Session, as_of: date) -> int:
    """Seed identity rates (1.0) for same-currency pairs — not market rates."""
    created = 0
    for ccy in SUPPORTED_CURRENCIES:
        existing = db.scalar(
            select(WhFxRate).where(
                WhFxRate.rate_date == as_of,
                WhFxRate.from_currency == ccy,
                WhFxRate.to_currency == ccy,
            )
        )
        if existing:
            continue
        db.add(
            WhFxRate(
                rate_date=as_of,
                from_currency=ccy,
                to_currency=ccy,
                rate=Decimal("1"),
                source="identity",
            )
        )
        created += 1
    if created:
        db.flush()
    return created
