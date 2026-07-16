'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { EmptyState, LoadingState } from '@investhome/ui';

import type { CalendarEvent } from '@/lib/api/work-items';
import { useWorkItemLabels } from '@/lib/i18n/work-item-labels';

type CalendarMode = 'day' | 'week' | 'month';

interface InternalCalendarViewProps {
  events: CalendarEvent[];
  loading: boolean;
  onSelectEvent: (event: CalendarEvent) => void;
}

export function InternalCalendarView({ events, loading, onSelectEvent }: InternalCalendarViewProps) {
  const t = useTranslations('work');
  const locale = useLocale();
  const { getTypeLabel } = useWorkItemLabels();
  const [mode, setMode] = useState<CalendarMode>('week');

  const grouped = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const event of events) {
      const key = (event.start_at ?? event.due_at ?? '').slice(0, 10);
      if (!key) continue;
      const list = map.get(key) ?? [];
      list.push(event);
      map.set(key, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [events]);

  if (loading) return <LoadingState label={t('loading')} />;
  if (events.length === 0) {
    return (
      <EmptyState
        title={t('calendar.emptyTitle')}
        description={t('calendar.emptyDescription')}
      />
    );
  }

  return (
    <div className="sales-work-calendar">
      <div className="sales-work-calendar__toolbar">
        {(['day', 'week', 'month'] as CalendarMode[]).map((m) => (
          <button
            key={m}
            type="button"
            className={mode === m ? 'sales-work-calendar__mode--active' : undefined}
            onClick={() => setMode(m)}
          >
            {t(`calendar.${m}` as never)}
          </button>
        ))}
        <span className="sales-work-calendar__hint">{t('calendar.internalOnly')}</span>
      </div>
      <div className="sales-work-calendar__grid">
        {grouped.map(([day, dayEvents]) => (
          <section key={day} className="sales-work-calendar__day">
            <h3>{new Intl.DateTimeFormat(locale, { dateStyle: 'full' }).format(new Date(day))}</h3>
            <ul>
              {dayEvents.map((event) => (
                <li key={event.id}>
                  <button type="button" onClick={() => onSelectEvent(event)}>
                    <strong>{event.title}</strong>
                    <span>{getTypeLabel(event.work_item_type)}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
