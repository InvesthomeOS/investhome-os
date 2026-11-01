'use client';

import { useTranslations } from 'next-intl';
import type { CapitalStructure } from '../../_data/investment-detail-types';
import { formatInvestorCurrency } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface CapitalStructureCardProps {
  structure: CapitalStructure;
  currency?: string;
}

export function CapitalStructureCard({ structure, currency = 'USD' }: CapitalStructureCardProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-detail-panel inv-capital-structure" aria-labelledby="capital-heading">
      <SectionHeader
        title={tChrome('kd911ca20ab')}
        subtitle={`Total capitalization ${formatInvestorCurrency(structure.totalCapitalization, currency)}`}
      />
      <div className="inv-capital-structure__body">
        <div className="inv-capital-structure__chart" role="img" aria-label={tChrome('k371a718bcd')}>
          <svg viewBox="0 0 120 120" className="inv-capital-structure__donut">
            {(() => {
              let offset = 0;
              const circumference = 2 * Math.PI * 45;
              return structure.items.map((item) => {
                const dash = (item.percent / 100) * circumference;
                const circle = (
                  <circle
                    key={item.label}
                    cx="60"
                    cy="60"
                    r="45"
                    fill="none"
                    stroke={item.color}
                    strokeWidth="18"
                    strokeDasharray={`${dash} ${circumference - dash}`}
                    strokeDashoffset={-offset}
                    transform="rotate(-90 60 60)"
                  />
                );
                offset += dash;
                return circle;
              });
            })()}
          </svg>
          <div className="inv-capital-structure__donut-center">
            <strong>{structure.items.length}</strong>
            <span>{tChrome('kd5df272608')}</span>
          </div>
        </div>
        <ul className="inv-capital-structure__legend">
          {structure.items.map((item) => (
            <li key={item.label}>
              <span className="inv-capital-structure__swatch" style={{ backgroundColor: item.color }} aria-hidden="true" />
              <span className="inv-capital-structure__legend-label">{item.label}</span>
              <span className="inv-capital-structure__legend-value">
                {formatInvestorCurrency(item.amount, currency)} ({item.percent}%)
              </span>
            </li>
          ))}
        </ul>
        <dl className="inv-capital-structure__summary">
          <div>
            <dt>{tChrome('kd64626c4e8')}</dt>
            <dd>{formatInvestorCurrency(structure.investorEquity, currency)}</dd>
          </div>
        </dl>
      </div>
    </section>
  );
}
