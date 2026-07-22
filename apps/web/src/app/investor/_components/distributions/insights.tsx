'use client';

import type { DistributionInsight } from '../../_data/distribution-types';
import { SectionHeader } from '../section-header';

export interface InsightsPanelProps {
  insights: DistributionInsight[];
}

const ICONS: Record<DistributionInsight['type'], string> = {
  positive: '↑',
  neutral: '◆',
  attention: '!',
};

export function InsightsPanel({ insights }: InsightsPanelProps) {
  return (
    <section className="inv-distributions__panel inv-distributions__insights">
      <SectionHeader title="Insights" subtitle="Derived from your distribution history" />

      <ul className="inv-distributions__insights-list">
        {insights.map((insight) => (
          <li
            key={insight.id}
            className={`inv-distributions__insight inv-distributions__insight--${insight.type}`}
          >
            <span className="inv-distributions__insight-icon" aria-hidden="true">
              {ICONS[insight.type]}
            </span>
            <div>
              <h3>{insight.title}</h3>
              <p>{insight.description}</p>
              {insight.metric ? (
                <span className="inv-distributions__insight-metric">{insight.metric}</span>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
