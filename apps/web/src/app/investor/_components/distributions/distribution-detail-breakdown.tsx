'use client';

import { useTranslations } from 'next-intl';

import type { Distribution } from '../../_data/distribution-types';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface DistributionDetailBreakdownProps {
  distribution: Distribution;
}

export function DistributionDetailBreakdown({ distribution: d }: DistributionDetailBreakdownProps) {
  const tChrome = useTranslations('investorPortal.chrome');
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
      <SectionHeader title={tChrome('ke9304f60c3')} subtitle={tChrome('k5b6039043e')} />

      <div className="inv-distributions__breakdown">
        {lines.map((l) => (
          <div key={l.label} className="inv-distributions__breakdown-row">
            <span>{l.label}</span>
            <span>{formatInvestorCurrency(l.value, d.currency)}</span>
          </div>
        ))}

        <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--subtotal">
          <span>{tChrome('kfa70e8a6cd')}</span>
          <strong>{formatInvestorCurrency(b.grossAmount, d.currency)}</strong>
        </div>

        {b.fees > 0 ? (
          <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--deduction">
            <span>{tChrome('k72abbc9284')}</span>
            <span>− {formatInvestorCurrency(b.fees, d.currency)}</span>
          </div>
        ) : null}

        {b.withholding > 0 ? (
          <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--deduction">
            <span>{tChrome('kc5f5e432d6')}</span>
            <span>− {formatInvestorCurrency(b.withholding, d.currency)}</span>
          </div>
        ) : null}

        <div className="inv-distributions__breakdown-row inv-distributions__breakdown-row--total">
          <span>{tChrome('k496e68bbea')}</span>
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
