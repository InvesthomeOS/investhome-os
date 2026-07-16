"""HTML proposal output generation — print-friendly, no external PDF deps."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.models.company_foundation import BrandProfile, CompanyProfile
from investhome_api.models.sales_proposal import (
    SalesProposal,
    SalesProposalItem,
    SalesProposalRecipient,
    SalesProposalVersion,
)


def _fmt_money(amount: Decimal | None, currency: str) -> str:
    if amount is None:
        return "—"
    return f"{currency} {amount:,.2f}"


def _load_branding(db: Session) -> dict[str, Any]:
    company = db.query(CompanyProfile).first()
    brand = db.query(BrandProfile).first()
    return {
        "company_name": company.legal_name if company else "Investhome",
        "brand_name": brand.brand_name if brand else None,
        "primary_color": brand.primary_color if brand else "#1a365d",
        "disclaimer": brand.standard_disclaimer_en if brand else None,
    }


def render_proposal_html(
    db: Session,
    proposal: SalesProposal,
    version: SalesProposalVersion,
    *,
    items: list[SalesProposalItem],
    recipients: list[SalesProposalRecipient],
    show_sensitive_prices: bool = True,
) -> str:
    branding = version.branding_snapshot or _load_branding(db)
    terms = version.terms_snapshot or {}
    content = version.content_snapshot or {}
    primary = next((r for r in recipients if r.is_primary), recipients[0] if recipients else None)

    rows = []
    for item in sorted(items, key=lambda i: i.sort_order):
        price_cell = _fmt_money(item.displayed_amount, item.currency) if show_sensitive_prices else "—"
        rows.append(
            f"<tr><td>{escape(item.item_title or str(item.inventory_asset_id))}</td>"
            f"<td class='num'>{price_cell}</td></tr>"
        )

    valid_until = proposal.valid_until.isoformat() if proposal.valid_until else "—"
    recipient_line = escape(primary.email_snapshot or "—") if primary else "—"

    disclaimer = terms.get("disclaimer") or branding.get("disclaimer") or (
        "This proposal is for informational purposes only and does not constitute a binding offer."
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{escape(proposal.title)} — {escape(proposal.proposal_number)}</title>
<style>
  @media print {{ @page {{ margin: 1.5cm; }} body {{ -webkit-print-color-adjust: exact; }} }}
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #222; max-width: 800px; margin: 0 auto; padding: 2rem; }}
  header {{ border-bottom: 3px solid {escape(str(branding.get('primary_color', '#1a365d')))}; padding-bottom: 1rem; margin-bottom: 2rem; }}
  h1 {{ font-size: 1.5rem; margin: 0 0 0.25rem; }}
  .meta {{ font-size: 0.85rem; color: #555; }}
  table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem 0.75rem; text-align: left; }}
  th {{ background: #f5f5f5; }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  .terms {{ margin-top: 2rem; font-size: 0.9rem; }}
  .disclaimer {{ margin-top: 2rem; font-size: 0.75rem; color: #666; border-top: 1px solid #eee; padding-top: 1rem; }}
</style>
</head>
<body>
<header>
  <h1>{escape(proposal.title)}</h1>
  <div class="meta">
    <div>Proposal: <strong>{escape(proposal.proposal_number)}</strong> · Version {version.version_number}</div>
    <div>Valid until: {valid_until} · Currency: {escape(proposal.currency)}</div>
    <div>Recipient: {recipient_line}</div>
  </div>
</header>
<section>
  <p>{escape(str(content.get('introduction', '')))}</p>
  <table>
    <thead><tr><th>Item</th><th>Price</th></tr></thead>
    <tbody>{''.join(rows) if rows else '<tr><td colspan="2">No items</td></tr>'}</tbody>
  </table>
</section>
<section class="terms">
  <h2>Terms</h2>
  <p>{escape(str(terms.get('payment_terms', '')))}</p>
  <p>{escape(str(terms.get('promotional_terms', '')))}</p>
</section>
<footer class="disclaimer">{escape(str(disclaimer))}</footer>
</body>
</html>"""
