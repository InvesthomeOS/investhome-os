"""Deterministic campaign pricing helpers — no invented yields."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


_MONEY_RE = re.compile(
    r"\$\s*([\d]{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(k|m|mn|million)?\b",
    re.I,
)
_UNIT_RE = re.compile(
    r"\b(?:unit|daire|apt\.?|apartment)\s*#?\s*([A-Za-z0-9\-]+)\b",
    re.I,
)


@dataclass(frozen=True)
class MoneyMention:
    raw: str
    amount: Decimal
    role_hint: str | None  # list | launch | None


@dataclass(frozen=True)
class ClaimRecord:
    key: str
    display: str
    value: str | float | int | None
    source: str  # user_campaign_input | retrieved | project_db | derived_safe
    source_reference: str
    verified: bool
    is_financial: bool
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_money_token(token: str) -> Decimal | None:
    m = _MONEY_RE.search(token or "")
    if not m:
        return None
    number = m.group(1).replace(",", "")
    suffix = (m.group(2) or "").lower()
    try:
        amount = Decimal(number)
    except InvalidOperation:
        return None
    if suffix in {"k"}:
        amount *= Decimal(1000)
    elif suffix in {"m", "mn", "million"}:
        amount *= Decimal(1_000_000)
    return amount


def _role_for_span(text: str, start: int, end: int) -> str | None:
    """Classify list vs launch from role keywords that precede the money token.

    Labels almost always appear *before* the amount ("Normal fiyat $400,000").
    Looking after the token incorrectly attributes the next clause's label.
    """
    window_start = max(0, start - 56)
    window = text[window_start:start].lower()

    launch_keys = ("lansman", "launch", "campaign price", "kampanya fiyat", "offer price", "indirimli")
    list_keys = ("normal", "list price", "regular", "standart", "standard", "liste fiyat")

    def _nearest_from_end(keys: tuple[str, ...]) -> int | None:
        best: int | None = None
        for key in keys:
            idx = 0
            while True:
                found = window.find(key, idx)
                if found < 0:
                    break
                # Distance from keyword end to the money token.
                dist = len(window) - (found + len(key))
                if best is None or dist < best:
                    best = dist
                idx = found + 1
        return best

    launch_dist = _nearest_from_end(launch_keys)
    list_dist = _nearest_from_end(list_keys)
    if launch_dist is None and list_dist is None:
        return None
    if launch_dist is None:
        return "list"
    if list_dist is None:
        return "launch"
    if launch_dist < list_dist:
        return "launch"
    return "list"


def extract_money_mentions(brief: str) -> list[MoneyMention]:
    out: list[MoneyMention] = []
    for m in _MONEY_RE.finditer(brief or ""):
        raw = m.group(0).replace(" ", "")
        amount = parse_money_token(m.group(0))
        if amount is None:
            continue
        out.append(
            MoneyMention(
                raw=raw if raw.startswith("$") else f"${raw.lstrip('$')}",
                amount=amount,
                role_hint=_role_for_span(brief or "", m.start(), m.end()),
            )
        )
    return out


def extract_unit_codes(brief: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _UNIT_RE.finditer(brief or ""):
        code = m.group(1).strip().upper()
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def format_usd(amount: Decimal) -> str:
    quantized = amount.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral():
        return f"${int(quantized):,}"
    return f"${quantized:,.2f}"


def compute_discount_percent(list_price: Decimal, offer_price: Decimal) -> Decimal:
    """Deterministic percent off. Both prices must be supplied as a verified pair."""
    if list_price <= 0:
        raise ValueError("list_price must be positive")
    pct = (list_price - offer_price) / list_price * Decimal(100)
    return pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_pricing_claims(
    *,
    brief: str,
    drive_prices: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve list/launch prices from brief + Drive; derive % only for a verified pair.

    User-supplied campaign offer prices are tagged ``user_campaign_input``.
    Drive/RAG matches are tagged ``retrieved``. Never invent other yields.
    """
    mentions = extract_money_mentions(brief)
    units = extract_unit_codes(brief)
    drive_prices = drive_prices or {}

    list_price: Decimal | None = None
    launch_price: Decimal | None = None
    list_source = "user_campaign_input"
    launch_source = "user_campaign_input"
    list_ref = "user_brief"
    launch_ref = "user_brief"

    for mention in mentions:
        if mention.role_hint == "list" and list_price is None:
            list_price = mention.amount
        elif mention.role_hint == "launch" and launch_price is None:
            launch_price = mention.amount

    # If roles were not labeled, take first two distinct amounts as list→launch.
    distinct = []
    for m in mentions:
        if not any(d.amount == m.amount for d in distinct):
            distinct.append(m)
    if list_price is None and len(distinct) >= 1:
        list_price = distinct[0].amount
    if launch_price is None and len(distinct) >= 2:
        launch_price = distinct[1].amount

    # Prefer Drive match when present for the same unit.
    unit_key = units[0] if units else None
    drive_unit = None
    if unit_key and isinstance(drive_prices.get("units"), dict):
        drive_unit = drive_prices["units"].get(unit_key) or drive_prices["units"].get(unit_key.lower())

    claims: list[ClaimRecord] = []
    if unit_key:
        unit_in_drive = bool(drive_unit)
        claims.append(
            ClaimRecord(
                key="unit_code",
                display=f"Unit {unit_key}",
                value=unit_key,
                source="retrieved" if unit_in_drive else "user_campaign_input",
                source_reference=(
                    str(drive_unit.get("source_reference") or "drive_price_list")
                    if unit_in_drive and isinstance(drive_unit, dict)
                    else "user_brief"
                ),
                verified=unit_in_drive,
                is_financial=False,
                notes=None if unit_in_drive else "Unit referenced in brief; not confirmed in Drive price list",
            )
        )

    if list_price is not None:
        claims.append(
            ClaimRecord(
                key="list_price",
                display=format_usd(list_price),
                value=float(list_price),
                source=list_source,
                source_reference=list_ref,
                verified=True,
                is_financial=True,
                notes="User-supplied campaign list price" if list_source == "user_campaign_input" else None,
            )
        )
    if launch_price is not None:
        claims.append(
            ClaimRecord(
                key="launch_price",
                display=format_usd(launch_price),
                value=float(launch_price),
                source=launch_source,
                source_reference=launch_ref,
                verified=True,
                is_financial=True,
                notes="User-supplied campaign launch/offer price"
                if launch_source == "user_campaign_input"
                else None,
            )
        )

    discount: dict[str, Any] | None = None
    if list_price is not None and launch_price is not None and list_price > 0:
        pct = compute_discount_percent(list_price, launch_price)
        # Round to nearest whole percent for presentation when clean.
        whole = pct.to_integral_value(rounding=ROUND_HALF_UP)
        display = f"~{int(whole)}%" if pct == whole else f"~{pct}%"
        discount = {
            "percent": float(pct),
            "display": display,
            "formula": "(list_price - launch_price) / list_price * 100",
            "list_price": float(list_price),
            "launch_price": float(launch_price),
            "source": "derived_safe",
            "source_reference": "deterministic_from_user_supplied_price_pair",
            "inputs_verified": True,
            "input_sources": [list_source, launch_source],
        }
        claims.append(
            ClaimRecord(
                key="launch_discount_percent",
                display=display,
                value=float(pct),
                source="derived_safe",
                source_reference="deterministic_from_user_supplied_price_pair",
                verified=True,
                is_financial=True,
                notes="Derived only because both list and launch prices were supplied as a pair",
            )
        )

    price_presentation = None
    if list_price is not None and launch_price is not None:
        # Deterministic pair framing — % is launch price advantage, never ROI/return.
        advantage = (
            f" ({discount['display']} launch price advantage)" if discount else ""
        )
        price_presentation = {
            "list": format_usd(list_price),
            "offer": format_usd(launch_price),
            "discount": discount,
            "copy": f"{format_usd(list_price)} → {format_usd(launch_price)}{advantage}",
            "framing": "launch_price_advantage",
        }
    elif launch_price is not None:
        price_presentation = {"offer": format_usd(launch_price), "copy": format_usd(launch_price)}
    elif list_price is not None:
        price_presentation = {"list": format_usd(list_price), "copy": format_usd(list_price)}

    return {
        "unit_codes": units,
        "list_price": float(list_price) if list_price is not None else None,
        "launch_price": float(launch_price) if launch_price is not None else None,
        "discount": discount,
        "price_presentation": price_presentation,
        "claims": [c.to_dict() for c in claims],
        "honesty": {
            "prices_from_user_brief": list_source == "user_campaign_input"
            or launch_source == "user_campaign_input",
            "unit_confirmed_in_drive": bool(drive_unit) if unit_key else None,
            "invented_yields": False,
        },
    }
