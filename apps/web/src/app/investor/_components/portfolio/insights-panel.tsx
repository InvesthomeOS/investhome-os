'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { SectionHeader } from '../section-header';
import type { PortfolioInsight } from '../../_data/portfolio-types';
import { getAllInvestments } from '../../_data/investments';

const TYPE_ICONS: Record<PortfolioInsight['type'], string> = {
  top_performer: '▲',
  bottom_performer: '▼',
  concentration: '◆',
  highest_risk: '!',
  cash_flow: '$',
  closest_exit: '→',
  most_improved: '↑',
  target_missed: '○',
};

export interface InsightsPanelProps {
  insights: PortfolioInsight[];
}

export function InsightsPanel({ insights }: InsightsPanelProps) {
  const slugMap = new Map(getAllInvestments().map((i) => [i.id, i.slug]));

  return (
    <section className="inv-portfolio-panel inv-portfolio-insights">
      <SectionHeader
        title="Portfolio Insights"
        subtitle="Deterministic analysis derived from your holdings"
      />
      <ul className="inv-portfolio-insights__list">
        {insights.map((insight) => (
          <li key={insight.id} className="inv-portfolio-insights__item">
            <span className="inv-portfolio-insights__icon" aria-hidden="true">
              {TYPE_ICONS[insight.type]}
            </span>
            <div>
              <h3 className="inv-portfolio-insights__title">{insight.title}</h3>
              <p className="inv-portfolio-insights__desc">{insight.description}</p>
              {insight.metric ? (
                <span className="inv-portfolio-insights__metric">{insight.metric}</span>
              ) : null}
              {insight.investmentId ? (
                <Link
                  href={`/investor/investments/${slugMap.get(insight.investmentId) ?? insight.investmentId}` as Route}
                  className="inv-portfolio-table__link"
                >
                  View investment
                </Link>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
