'use client';

import type { Distribution } from '../../_data/distribution-types';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface DistributionDetailBreakdownProps {
  distribution: Distribution;
}

export function DistributionDetailBreakdown({ distribution: d }: DistributionDetailBreakdownProps) {
  const { breakdown: b } = d;
  const lines = [
    { label: 'Preferred Return', value: b.preferredReturnAmount, sign: '+' as const },
    { label: 'Return of Capital', value: b.returnOfCapitalAmount, sign: '+' as const },
    { label: 'Profit Share', value: b.profitShareAmount, sign: '+' as const },
    { label: 'Refinance Proceeds', value: b.refinanceAmount, sign: '+' as const },
    { label: 'Sale Proceeds', value: b.saleAmount, sign: '+' as const },
  ].filter((l) => l.value > 0);

  const reconciled =
    b.grossAmount === lines.reduce((s, l) => s + l.value, 0) &&
    b.netAmount === b.grossAmount - b.fees - b.withholding;

  return (
    <section className="inv-distributions__panel">
      <SectionHeader title="Distribution Breakdown" subtitle="Gross − fees − withholding = net" />

      <div className="inv-distributions__breakdown">
        {lines.map((l) => (
          <div key={l.label} className="inv-distributions__breakdown-row">
            <span>{l.label}</span>
            <span>{formatInvestorCurrency(l.value, d.currency)}</span>
          </div>
        ))}

        <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--subtotal">
          <span>Gross Total</span>
          <strong>{formatInvestorCurrency(b.grossAmount, d.currency)}</strong>
        </div>

        {b.fees > 0 ? (
          <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--deduction">
            <span>Fees</span>
            <span>− {formatInvestorCurrency(b.fees, d.currency)}</span>
          </div>
        ) : null}

        {b.withholding > 0 ? (
          <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--deduction">
            <span>Withholding</span>
            <span>− {formatInvestorCurrency(b.withholding, d.currency)}</span>
          </div>
        ) : null}

        <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--total">
          <span>Net Distribution</span>
          <strong>{formatInvestorCurrency(b.netAmount, d.currency)}</strong>
        </div>
      </div>

      <p className="inv-distributions__reconciliation" role="status">
        {reconciled
          ? '✓ Reconciliation verified: gross − fees − withholding = net'
          : '⚠ Reconciliation mismatch detected'}
      </p>

      {d.notes ? <p className="inv-distributions__notes">{d.notes}</p> : null}
    </section>
  );
}
