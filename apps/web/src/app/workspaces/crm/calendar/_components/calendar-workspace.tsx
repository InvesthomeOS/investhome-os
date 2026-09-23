'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { activityQueries } from '@/workspaces/crm/hooks/use-activities';
import type { CalendarViewMode } from '@/workspaces/crm/types/activities';
import { useActivityUiStore } from '@/workspaces/crm/stores/activity-ui-store';

import { ActivityFormModal } from '../../_components/activity-form-modal';

const VIEW_MODES: CalendarViewMode[] = ['day', 'week', 'month', 'agenda'];

function startOfWeek(date: Date): Date {
  const copy = new Date(date);
  const day = copy.getDay();
  const diff = copy.getDate() - day + (day === 0 ? -6 : 1);
  copy.setDate(diff);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function addDays(date: Date, days: number): Date {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

export function CalendarWorkspace() {
  const t = useTranslations('crm.calendar');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canRead: canView, canCreate } = useCrmAccess();
  const { calendarViewMode, setCalendarViewMode } = useActivityUiStore();
  const [cursor, setCursor] = useState(new Date());
  const [formOpen, setFormOpen] = useState(false);

  const range = useMemo(() => {
    if (calendarViewMode === 'day') {
      const start = new Date(cursor);
      start.setHours(0, 0, 0, 0);
      const end = addDays(start, 1);
      return { start, end };
    }
    if (calendarViewMode === 'month') {
      const start = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
      const end = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0, 23, 59, 59);
      return { start, end };
    }
    const start = startOfWeek(cursor);
    const end = addDays(start, calendarViewMode === 'agenda' ? 14 : 7);
    return { start, end };
  }, [calendarViewMode, cursor]);

  const calendarQuery = useQuery({
    ...activityQueries.calendar({
      start: range.start.toISOString(),
      end: range.end.toISOString(),
    }),
    enabled: !authLoading && canView,
  });

  const formatter = new Intl.DateTimeFormat(locale, { dateStyle: 'medium' });

  if (authLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (!canView) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (calendarQuery.isLoading) {
    return <LoadingState label={tCommon('loading')} />;
  }

  if (calendarQuery.isError) {
    return (
      <ErrorState
        title={t('loadFailed')}
        message={calendarQuery.error?.message ?? t('loadFailed')}
        action={
          <Button type="button" onClick={() => void calendarQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const events = calendarQuery.data?.events ?? [];

  return (
    <div className="crm-calendar">
      <header className="crm-calendar__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        <div className="crm-calendar__nav">
          <Button type="button" variant="secondary" onClick={() => setCursor(addDays(cursor, -7))}>
            {t('prev')}
          </Button>
          <span>{formatter.format(cursor)}</span>
          <Button type="button" variant="secondary" onClick={() => setCursor(addDays(cursor, 7))}>
            {t('next')}
          </Button>
          {canCreate && (
            <Button type="button" onClick={() => setFormOpen(true)}>
              {t('createMeeting')}
            </Button>
          )}
        </div>
      </header>

      <nav className="crm-view-tabs" aria-label={t('viewModes')}>
        {VIEW_MODES.map((mode) => (
          <button
            key={mode}
            type="button"
            className={calendarViewMode === mode ? 'crm-view-tabs__tab--active' : 'crm-view-tabs__tab'}
            onClick={() => setCalendarViewMode(mode)}
          >
            {t(`views.${mode}` as 'views.week')}
          </button>
        ))}
      </nav>

      {events.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className={calendarViewMode === 'month' ? 'crm-calendar__month' : 'crm-calendar__agenda'}>
          {events.map((event) => {
            const when = event.start_date ?? event.due_date;
            return (
              <article key={event.id} className="crm-calendar__event">
                <time dateTime={when ?? undefined}>
                  {when ? new Date(when).toLocaleString(locale) : t('noDate')}
                </time>
                <h3>{event.title}</h3>
                <span>{event.activity_type}</span>
              </article>
            );
          })}
        </div>
      )}

      <ActivityFormModal open={formOpen} onClose={() => setFormOpen(false)} mode="meeting" defaultType="meeting" />
    </div>
  );
}
