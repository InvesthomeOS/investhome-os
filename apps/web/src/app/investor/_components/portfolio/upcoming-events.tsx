'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

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
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-portfolio-panel">
      <SectionHeader
        title={tChrome('k4be21b6781')}
        subtitle={tChrome('kb2ea6a55eb')}
      />
      {events.length === 0 ? (
        <p className="inv-portfolio-panel__empty">{tChrome('kaa2c126821')}</p>
      ) : (
        <ol className="inv-portfolio-events">
          {events.map((event) => (
            <li key={event.id} className="inv-portfolio-events__item">
              <div className="inv-portfolio-events__date">
                <time dateTime={event.date}>{formatInvestorDate(event.date)}</time>
              </div>
              <div className="inv-portfolio-events__body">
                <span className="inv-portfolio-events__type">{investorChrome(tChrome, EVENT_LABELS[event.eventType])}</span>
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
                    <dt>{tChrome('kd9fdae55f9')}</dt>
                    <dd>{(event.probability * 100).toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt>{tChrome('k434652b901')}</dt>
                    <dd>{formatInvestorCurrency(event.projectedProceeds, currency)}</dd>
                  </div>
                  <div>
                    <dt>{tChrome('kbae7d5be70')}</dt>
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
