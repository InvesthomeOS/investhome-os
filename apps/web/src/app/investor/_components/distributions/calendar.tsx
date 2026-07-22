'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';

import type { DistributionEvent } from '../../_data/distribution-types';
import { DISTRIBUTION_REFERENCE_DATE } from '../../_data/distributions';
import { DISTRIBUTION_STATUS_LABELS, DISTRIBUTION_TYPE_LABELS } from '../../_data/distributions';
import { formatInvestorCurrency, formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

type CalendarView = 'list' | 'month' | 'timeline';

export interface DistributionCalendarProps {
  events: DistributionEvent[];
}

export function DistributionCalendar({ events }: DistributionCalendarProps) {
  const [view, setView] = useState<CalendarView>('list');
  const [monthOffset, setMonthOffset] = useState(0);

  const displayMonth = useMemo(() => {
    const refDate = new Date(`${DISTRIBUTION_REFERENCE_DATE}T12:00:00`);
    refDate.setMonth(refDate.getMonth() + monthOffset);
    return refDate;
  }, [monthOffset]);

  const monthEvents = useMemo(() => {
    const y = displayMonth.getFullYear();
    const m = displayMonth.getMonth();
    return events.filter((e) => {
      const d = new Date(`${e.date}T12:00:00`);
      return d.getFullYear() === y && d.getMonth() === m;
    });
  }, [events, displayMonth]);

  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()),
    [events],
  );

  const calendarDays = useMemo(() => {
    const y = displayMonth.getFullYear();
    const m = displayMonth.getMonth();
    const firstDay = new Date(y, m, 1).getDay();
    const daysInMonth = new Date(y, m + 1, 0).getDate();
    const cells: { day: number | null; events: DistributionEvent[] }[] = [];

    for (let i = 0; i < firstDay; i++) cells.push({ day: null, events: [] });
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${y}-${String(m + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      const dayEvents = events.filter((e) => e.date === dateStr);
      cells.push({ day, events: dayEvents });
    }
    return cells;
  }, [displayMonth, events]);

  return (
    <section className="inv-distributions__panel">
      <SectionHeader title="Distribution Calendar" subtitle="Scheduled and completed distribution events" />

      <div className="inv-distributions__toggle-group" role="group" aria-label="Calendar view">
        {(['list', 'month', 'timeline'] as const).map((v) => (
          <button
            key={v}
            type="button"
            className={`inv-distributions__toggle${view === v ? ' inv-distributions__toggle--active' : ''}`}
            onClick={() => setView(v)}
            aria-pressed={view === v}
          >
            {v === 'list' ? 'List' : v === 'month' ? 'Monthly' : 'Timeline'}
          </button>
        ))}
      </div>

      {view === 'list' && (
        <ul className="inv-distributions__calendar-list">
          {sortedEvents.slice(0, 12).map((e) => (
            <li key={e.id}>
              <time dateTime={e.date}>{formatInvestorDate(e.date)}</time>
              <div>
                <Link href={`/investor/distributions/${e.distributionId}` as Route} className="inv-distributions__link">
                  {e.title}
                </Link>
                <span className={`inv-distributions__status inv-distributions__status--${e.status}`}>
                  {DISTRIBUTION_STATUS_LABELS[e.status]}
                </span>
              </div>
              <strong>{formatInvestorCurrency(e.amount, 'USD')}</strong>
            </li>
          ))}
        </ul>
      )}

      {view === 'month' && (
        <>
          <div className="inv-distributions__calendar-nav">
            <button type="button" onClick={() => setMonthOffset((o) => o - 1)} aria-label="Previous month">
              ‹
            </button>
            <strong>
              {displayMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            </strong>
            <button type="button" onClick={() => setMonthOffset((o) => o + 1)} aria-label="Next month">
              ›
            </button>
          </div>
          <div className="inv-distributions__calendar-grid" role="grid" aria-label="Monthly calendar">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
              <div key={d} className="inv-distributions__calendar-dow" role="columnheader">
                {d}
              </div>
            ))}
            {calendarDays.map((cell, i) => (
              <div
                key={i}
                className={`inv-distributions__calendar-cell${cell.events.length ? ' inv-distributions__calendar-cell--has-event' : ''}`}
                role="gridcell"
              >
                {cell.day !== null ? (
                  <>
                    <span className="inv-distributions__calendar-day">{cell.day}</span>
                    {cell.events.map((e) => (
                      <Link
                        key={e.id}
                        href={`/investor/distributions/${e.distributionId}` as Route}
                        className="inv-distributions__calendar-event"
                        title={e.title}
                      >
                        {DISTRIBUTION_TYPE_LABELS[e.type].split(' ')[0]}
                      </Link>
                    ))}
                  </>
                ) : null}
              </div>
            ))}
          </div>
          {monthEvents.length === 0 ? (
            <p className="inv-distributions__empty-note">No events this month.</p>
          ) : null}
        </>
      )}

      {view === 'timeline' && (
        <ol className="inv-distributions__timeline">
          {sortedEvents.map((e) => (
            <li key={e.id} className="inv-distributions__timeline-item">
              <div className="inv-distributions__timeline-marker" aria-hidden="true" />
              <div className="inv-distributions__timeline-content">
                <time dateTime={e.date}>{formatInvestorDate(e.date)}</time>
                <Link href={`/investor/distributions/${e.distributionId}` as Route} className="inv-distributions__link">
                  {e.investmentName}
                </Link>
                <p>{DISTRIBUTION_TYPE_LABELS[e.type]} · {formatInvestorCurrency(e.amount, 'USD')}</p>
                <span className={`inv-distributions__status inv-distributions__status--${e.status}`}>
                  {DISTRIBUTION_STATUS_LABELS[e.status]}
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
