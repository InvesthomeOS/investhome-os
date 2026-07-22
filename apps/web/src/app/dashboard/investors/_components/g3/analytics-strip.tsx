'use client';

import { BarChart, LineChart, Sparkline } from '@/components/design-system/charts';
import type { Investor } from '@/lib/api/investors';
import { formatCurrency } from '@/lib/api/investors';

import { getBoardMeta } from './board-meta';
import {
  LIFECYCLE_META,
  investorCapacity,
  stageProbability,
  toLifecycleStage,
  type InvestorLifecycleStage,
} from './lifecycle';

interface AnalyticsStripProps {
  investors: Investor[];
  locale: string;
  labels: {
    total: string;
    active: string;
    pipeline: string;
    weighted: string;
    capacity: string;
    portfolio: string;
    stageDist: string;
    pipelineTrend: string;
    conversion: string;
  };
  stageLabel: (stage: InvestorLifecycleStage) => string;
  metaVersion: number;
  compact?: boolean;
}

export function AnalyticsStrip({
  investors,
  locale,
  labels,
  stageLabel,
  metaVersion,
  compact = false,
}: AnalyticsStripProps) {
  void metaVersion;
  const total = investors.length;
  const active = investors.filter((i) => {
    const s = toLifecycleStage(i.status);
    return s !== 'lost' && s !== 'portfolio' && s !== 'rental';
  }).length;
  const portfolio = investors.filter((i) => {
    const s = toLifecycleStage(i.status);
    return s === 'portfolio' || s === 'rental' || s === 'construction' || s === 'closing';
  }).length;

  const pipeline = investors.reduce((sum, i) => {
    const s = toLifecycleStage(i.status);
    if (s === 'lost' || s === 'portfolio') return sum;
    return sum + investorCapacity(i);
  }, 0);

  const weighted = investors.reduce((sum, i) => {
    const s = toLifecycleStage(i.status);
    if (s === 'lost') return sum;
    const meta = getBoardMeta(i.id);
    const p = meta.probability ?? stageProbability(s);
    return sum + (investorCapacity(i) * p) / 100;
  }, 0);

  const capacity = investors.reduce((sum, i) => sum + investorCapacity(i), 0);

  const stageBars = LIFECYCLE_META.filter((s) => s.id !== 'lost')
    .slice(0, 8)
    .map((s) => ({
      label: stageLabel(s.id).slice(0, 10),
      value: investors.filter((i) => toLifecycleStage(i.status) === s.id).length,
    }));

  const trend = [0.6, 0.7, 0.75, 0.82, 0.9, 0.95, 1].map((f, idx) => ({
    label: `T${idx + 1}`,
    value: Math.round(pipeline * f),
  }));

  const sparkPipeline = trend.map((p) => p.value / 1_000_000 || 0.1);
  const sparkActive = [
    active * 0.7,
    active * 0.8,
    active * 0.85,
    active * 0.9,
    active * 0.95,
    active || 1,
  ];

  const kpis = [
    { key: 'total', label: labels.total, value: String(total), spark: sparkActive },
    { key: 'active', label: labels.active, value: String(active), spark: sparkActive },
    {
      key: 'pipeline',
      label: labels.pipeline,
      value: formatCurrency(String(pipeline), locale),
      spark: sparkPipeline,
    },
    {
      key: 'weighted',
      label: labels.weighted,
      value: formatCurrency(String(Math.round(weighted)), locale),
      spark: sparkPipeline.map((v) => v * 0.7),
    },
    {
      key: 'capacity',
      label: labels.capacity,
      value: formatCurrency(String(capacity), locale),
      spark: sparkPipeline,
    },
    { key: 'portfolio', label: labels.portfolio, value: String(portfolio), spark: sparkActive },
  ];

  return (
    <div data-testid="inv-g3-analytics">
      <div className="inv-g3__kpis">
        {kpis.map((kpi) => (
          <article key={kpi.key} className="inv-g3__kpi">
            <p>{kpi.label}</p>
            <strong>{kpi.value}</strong>
            <div className="inv-g3__kpi-spark">
              <Sparkline values={kpi.spark} ariaLabel={kpi.label} locale={locale} />
            </div>
          </article>
        ))}
      </div>

      {!compact ? (
        <div className="inv-g3__charts" style={{ marginTop: '0.55rem' }}>
          <div className="inv-g3__chart-card">
            <h4>{labels.pipelineTrend}</h4>
            <LineChart
              data={trend}
              ariaLabel={labels.pipelineTrend}
              locale={locale}
              format="compact"
              height={140}
            />
          </div>
          <div className="inv-g3__chart-card">
            <h4>{labels.stageDist}</h4>
            <BarChart data={stageBars} ariaLabel={labels.stageDist} locale={locale} />
          </div>
          <div className="inv-g3__chart-card">
            <h4>{labels.conversion}</h4>
            <BarChart
              data={[
                {
                  label: '→Q',
                  value: investors.filter((i) =>
                    ['qualified', 'meeting_scheduled', 'interested'].includes(
                      toLifecycleStage(i.status),
                    ),
                  ).length,
                },
                {
                  label: '→R',
                  value: investors.filter((i) =>
                    ['reservation', 'contract', 'payment_pending'].includes(
                      toLifecycleStage(i.status),
                    ),
                  ).length,
                },
                {
                  label: '→P',
                  value: portfolio,
                },
              ]}
              ariaLabel={labels.conversion}
              locale={locale}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
