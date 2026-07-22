'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { SectionHeader } from '../section-header';
import type { PortfolioExitEvent } from '../../_data/portfolio-types';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';

export interface UpcomingEventsProps {
  events: PortfolioExitEvent[];
  currency: string;
}

const EVENT_LABELS: Record<PortfolioExitEvent['eventType'], string> = {
  exit: 'Projected Exit',
  distribution: 'Distribution',
  milestone: 'Milestone',
  refinance: 'Refinance',
};

export function UpcomingEvents({ events, currency }: UpcomingEventsProps) {
  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title="Upcoming Exits & Milestones"
        subtitle="Scheduled events across the portfolio"
      />
      {events.length === 0 ? (
        <p className="inv-portfolio-panel__empty">No upcoming events in the selected portfolio.</p>
      ) : (
        <ol className="inv-portfolio-events">
          {events.map((event) => (
            <li key={event.id} className="inv-portfolio-events__item">
              <div className="inv-portfolio-events__date">
                <time dateTime={event.date}>{formatInvestorDate(event.date)}</time>
              </div>
              <div className="inv-portfolio-events__body">
                <span className="inv-portfolio-events__type">{EVENT_LABELS[event.eventType]}</span>
                <h3 className="inv-portfolio-events__title">
                  <Link
                    href={`/investor/investments/${event.slug}` as Route}
                    className="inv-portfolio-table__link"
                  >
                    {event.projectName}
                  </Link>
                </h3>
                <dl className="inv-portfolio-events__meta">
                  <div>
                    <dt>Probability</dt>
                    <dd>{(event.probability * 100).toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt>Proceeds</dt>
                    <dd>{formatInvestorCurrency(event.projectedProceeds, currency)}</dd>
                  </div>
                  <div>
                    <dt>Status</dt>
                    <dd>{event.status}</dd>
                  </div>
                </dl>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
