'use client';

import { useTranslations } from 'next-intl';

import { SectionHeader } from '../section-header';
import type { PortfolioBenchmark, PortfolioSummary } from '../../_data/portfolio-types';
import { formatInvestorPercent } from '../../_data/mock-data';

export interface BenchmarksSectionProps {
  benchmarks: PortfolioBenchmark[];
  summary: PortfolioSummary;
}

export function BenchmarksSection({ benchmarks, summary }: BenchmarksSectionProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const actualMap: Record<string, number> = {
    'target-roi': summary.portfolioRoi,
    'target-irr': summary.portfolioIrr,
    'target-em': summary.equityMultiple,
    'cash-yield':
      summary.currentValue > 0 ? (summary.annualNetCashFlow / summary.currentValue) * 100 : 0,
  };

  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('k4f46ac72b3')}
        subtitle={tChrome('k4067def710')}
      />
      <p className="inv-portfolio-panel__notice" role="note">
        All benchmarks below are illustrative mock data for dashboard demonstration purposes.
      </p>
      <div className="inv-portfolio-benchmarks">
        {benchmarks.map((bench) => {
          const actual = actualMap[bench.id];
          const formatBench =
            bench.unit === 'multiple'
              ? (v: number) => `${v.toFixed(2)}x`
              : bench.unit === 'currency'
                ? (v: number) => `$${v.toLocaleString()}`
                : (v: number) => formatInvestorPercent(v);

          return (
            <article key={bench.id} className="inv-portfolio-benchmark">
              <div className="inv-portfolio-benchmark__header">
                <h3>{bench.label}</h3>
                <span className="inv-portfolio-benchmark__mock">{tChrome('k3bba2a47cc')}</span>
              </div>
              <p className="inv-portfolio-benchmark__desc">{bench.description}</p>
              <div className="inv-portfolio-benchmark__values">
                <div>
                  <span className="inv-portfolio-benchmark__label">{tChrome('k9ed99e75a9')}</span>
                  <strong>{formatBench(bench.value)}</strong>
                </div>
                {actual !== undefined ? (
                  <div>
                    <span className="inv-portfolio-benchmark__label">{tChrome('k036b18f02a')}</span>
                    <strong>{formatBench(actual)}</strong>
                  </div>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
