'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, KpiCard, LoadingState, SegmentedControl } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { fetchCalendar } from '@/workspaces/crm/api/activities';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { buildCalendarPreview, toDateIso } from '@/workspaces/crm/lib/map-live-workspace';

import {
  CALENDAR_DAY_KEYS,
  CALENDAR_EVENT_TYPE_ICONS,
  CALENDAR_HOURS,
  CALENDAR_KPI_ICONS,
  CALENDAR_QUICK_CREATE,
  CALENDAR_VIEW_ORDER,
  type CalendarEvent,
  type CalendarViewMode,
  type CalendarWorkspacePreview,
} from '../calendar-model';

/** Slightly taller hour rows for operational density + readable event padding. */
const HOUR_HEIGHT = 60;
const DAY_START_MINUTE = 8 * 60;

function formatHour(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`;
}

function eventTop(startMinute: number): number {
  return (startMinute / 60) * HOUR_HEIGHT;
}

function eventHeight(durationMinutes: number): number {
  return Math.max((durationMinutes / 60) * HOUR_HEIGHT, 40);
}

function EventCard({
  event,
  compact,
  onOpen,
}: {
  event: CalendarEvent;
  compact?: boolean;
  onOpen?: (event: CalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const startHour = event.startMinute == null ? null : Math.floor((DAY_START_MINUTE + event.startMinute) / 60);
  const startMin = event.startMinute == null ? null : (DAY_START_MINUTE + event.startMinute) % 60;
  const endTotal =
    event.startMinute == null ? null : DAY_START_MINUTE + event.startMinute + event.durationMinutes;
  const endHour = endTotal == null ? null : Math.floor(endTotal / 60);
  const endMin = endTotal == null ? null : endTotal % 60;
  const timeLabel =
    startHour == null || startMin == null
      ? t('allDay.label')
      : endHour == null || endMin == null
        ? `${String(startHour).padStart(2, '0')}:${String(startMin).padStart(2, '0')}`
        : `${String(startHour).padStart(2, '0')}:${String(startMin).padStart(2, '0')} – ${String(endHour).padStart(2, '0')}:${String(endMin).padStart(2, '0')}`;
  const typeLabel = t(`types.${event.type}`);
  const title = event.title ?? t(`events.${event.titleKey}`);

  return (
    <article
      className={`crm-calendar-ds__event is-${event.type}${compact ? ' is-compact' : ''}`}
      data-testid={`calendar-event-${event.id}`}
      tabIndex={0}
      role="button"
      onClick={() => onOpen?.(event)}
      onKeyDown={(eventKey) => {
        if (eventKey.key === 'Enter' || eventKey.key === ' ') onOpen?.(event);
      }}
      title={`${timeLabel} · ${title} · ${typeLabel}`}
    >
      <header className="crm-calendar-ds__event-head">
        <span className="crm-calendar-ds__event-time">{timeLabel}</span>
        <span
          className="crm-calendar-ds__event-icon"
          aria-hidden="true"
          title={typeLabel}
        >
          <IhIcon name={CALENDAR_EVENT_TYPE_ICONS[event.type]} size={11} />
        </span>
      </header>
      <strong className="crm-calendar-ds__event-title" title={title}>
        {title}
      </strong>
      {!compact ? (
        <>
          <span className="crm-calendar-ds__event-meta" title={event.customer}>
            {event.customer}
          </span>
          <span className="crm-calendar-ds__event-meta" title={event.project}>
            {event.project}
          </span>
        </>
      ) : null}
      {event.participantCount > 0 ? (
        <span
          className="crm-calendar-ds__event-people"
          aria-label={t('participants', { count: event.participantCount })}
        >
          <IhIcon name="users" size={10} />
          {event.participantCount}
        </span>
      ) : null}
    </article>
  );
}

function WeekView({
  preview,
  onOpen,
}: {
  preview: CalendarWorkspacePreview;
  onOpen?: (event: CalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const timedEvents = preview.events.filter((e) => !e.allDay && e.startMinute != null);
  const allDayEvents = preview.events.filter((e) => e.allDay);
  const gridHours = CALENDAR_HOURS.slice(0, -1);

  return (
    <div className="crm-calendar-ds__week" role="region" aria-label={t('views.week')}>
      <div className="crm-calendar-ds__week-head" role="row">
        <div className="crm-calendar-ds__gutter" aria-hidden="true" />
        {CALENDAR_DAY_KEYS.map((dayKey, index) => {
          const date = new Date(`${preview.weekStartIso}T00:00:00`);
          date.setDate(date.getDate() + index);
          const isToday = index === preview.currentDayIndex;
          return (
            <div
              key={dayKey}
              className={`crm-calendar-ds__day-head${isToday ? ' is-today' : ''}`}
              role="columnheader"
            >
              <span className="crm-calendar-ds__day-name">{t(`days.${dayKey}`)}</span>
              <span className={`crm-calendar-ds__day-num${isToday ? ' is-today' : ''}`}>
                {date.getDate()}
              </span>
            </div>
          );
        })}
      </div>

      <div className="crm-calendar-ds__all-day" role="row" aria-label={t('allDay.aria')}>
        <div className="crm-calendar-ds__gutter">
          <span>{t('allDay.short')}</span>
        </div>
        {CALENDAR_DAY_KEYS.map((dayKey, index) => (
          <div key={dayKey} className="crm-calendar-ds__all-day-cell">
            {allDayEvents
              .filter((e) => e.dayIndex === index)
              .map((event) => (
                <EventCard key={event.id} event={event} compact onOpen={onOpen} />
              ))}
          </div>
        ))}
      </div>

      <div className="crm-calendar-ds__week-body">
        <div className="crm-calendar-ds__gutter-col" aria-hidden="true">
          {gridHours.map((hour) => (
            <div key={hour} className="crm-calendar-ds__hour-label" style={{ height: HOUR_HEIGHT }}>
              {formatHour(hour)}
            </div>
          ))}
        </div>
        <div
          className="crm-calendar-ds__days"
          style={{ height: gridHours.length * HOUR_HEIGHT }}
        >
          {CALENDAR_DAY_KEYS.map((dayKey, dayIndex) => {
            const isToday = dayIndex === preview.currentDayIndex;
            const dayEvents = timedEvents.filter((e) => e.dayIndex === dayIndex);
            return (
              <div
                key={dayKey}
                className={`crm-calendar-ds__day-col${isToday ? ' is-today' : ''}`}
                role="gridcell"
                aria-label={t(`days.${dayKey}`)}
              >
                {gridHours.map((hour) => (
                  <div
                    key={hour}
                    className="crm-calendar-ds__hour-slot"
                    style={{ height: HOUR_HEIGHT }}
                  />
                ))}
                {isToday ? (
                  <div
                    className="crm-calendar-ds__now-line"
                    style={{ top: eventTop(preview.nowMinute) }}
                    aria-hidden="true"
                  />
                ) : null}
                {dayEvents.map((event) => (
                  <div
                    key={event.id}
                    className="crm-calendar-ds__event-pos"
                    style={{
                      top: eventTop(event.startMinute ?? 0),
                      height: eventHeight(event.durationMinutes),
                    }}
                  >
                    <EventCard event={event} onOpen={onOpen} />
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function DayView({
  preview,
  onOpen,
}: {
  preview: CalendarWorkspacePreview;
  onOpen?: (event: CalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const dayEvents = preview.events.filter(
    (e) => e.dayIndex === preview.currentDayIndex && !e.allDay && e.startMinute != null,
  );
  const allDay = preview.events.filter(
    (e) => e.dayIndex === preview.currentDayIndex && e.allDay,
  );
  const gridHours = CALENDAR_HOURS.slice(0, -1);

  return (
    <div className="crm-calendar-ds__day-view" role="region" aria-label={t('views.day')}>
      {allDay.length > 0 ? (
        <div className="crm-calendar-ds__day-allday">
          {allDay.map((event) => (
            <EventCard key={event.id} event={event} compact onOpen={onOpen} />
          ))}
        </div>
      ) : null}
      <div className="crm-calendar-ds__day-grid" style={{ height: gridHours.length * HOUR_HEIGHT }}>
        <div className="crm-calendar-ds__gutter-col" aria-hidden="true">
          {gridHours.map((hour) => (
            <div key={hour} className="crm-calendar-ds__hour-label" style={{ height: HOUR_HEIGHT }}>
              {formatHour(hour)}
            </div>
          ))}
        </div>
        <div className="crm-calendar-ds__day-col is-today">
          {gridHours.map((hour) => (
            <div key={hour} className="crm-calendar-ds__hour-slot" style={{ height: HOUR_HEIGHT }} />
          ))}
          <div
            className="crm-calendar-ds__now-line"
            style={{ top: eventTop(preview.nowMinute) }}
            aria-hidden="true"
          />
          {dayEvents.map((event) => (
            <div
              key={event.id}
              className="crm-calendar-ds__event-pos"
              style={{
                top: eventTop(event.startMinute ?? 0),
                height: eventHeight(event.durationMinutes),
              }}
            >
              <EventCard event={event} onOpen={onOpen} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function MonthView({
  preview,
  onOpen,
}: {
  preview: CalendarWorkspacePreview;
  onOpen?: (event: CalendarEvent) => void;
}) {
  const t = useTranslations('crm.calendar');
  const cells = useMemo(() => {
    const start = new Date(`${preview.weekStartIso}T00:00:00`);
    start.setDate(start.getDate() - 7);
    return Array.from({ length: 35 }, (_, i) => {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
      const events = preview.events.filter((e) => (e.dateIso ?? '') === iso).slice(0, 3);
      return { key: `${iso}-${i}`, date: d, events, iso };
    });
  }, [preview]);

  return (
    <div className="crm-calendar-ds__month" role="region" aria-label={t('views.month')}>
      <div className="crm-calendar-ds__month-head">
        {CALENDAR_DAY_KEYS.map((dayKey) => (
          <div key={dayKey}>{t(`days.${dayKey}`)}</div>
        ))}
      </div>
      <div className="crm-calendar-ds__month-grid">
        {cells.map((cell) => {
          const isToday = cell.iso === toDateIso(new Date());
          return (
            <div
              key={cell.key}
              className={`crm-calendar-ds__month-cell${isToday ? ' is-today' : ''}`}
            >
              <span className={`crm-calendar-ds__month-num${isToday ? ' is-today' : ''}`}>
                {cell.date.getDate()}
              </span>
              <ul className="crm-calendar-ds__month-events">
                {cell.events.map((event) => (
                  <li key={event.id} className={`is-${event.type}`}>
                    <button type="button" onClick={() => onOpen?.(event)}>
                      <IhIcon name={CALENDAR_EVENT_TYPE_ICONS[event.type]} size={10} />
                      <span>{event.title ?? t(`events.${event.titleKey}`)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function AgendaView({ preview }: { preview: CalendarWorkspacePreview }) {
  const t = useTranslations('crm.calendar');
  const items = [...preview.events].sort((a, b) => {
    if (a.dayIndex !== b.dayIndex) return a.dayIndex - b.dayIndex;
    return (a.startMinute ?? -1) - (b.startMinute ?? -1);
  });

  return (
    <div className="crm-calendar-ds__agenda" role="region" aria-label={t('views.agenda')}>
      <ul className="crm-calendar-ds__agenda-list">
        {items.map((event) => {
          const dayKey = CALENDAR_DAY_KEYS[event.dayIndex];
          const startHour =
            event.startMinute == null
              ? null
              : Math.floor((DAY_START_MINUTE + event.startMinute) / 60);
          const startMin =
            event.startMinute == null ? null : (DAY_START_MINUTE + event.startMinute) % 60;
          const timeLabel =
            startHour == null || startMin == null
              ? t('allDay.label')
              : `${String(startHour).padStart(2, '0')}:${String(startMin).padStart(2, '0')}`;
          return (
            <li key={event.id} className={`crm-calendar-ds__agenda-item is-${event.type}`}>
              <div className="crm-calendar-ds__agenda-when">
                <strong>{t(`days.${dayKey}`)}</strong>
                <span>{timeLabel}</span>
              </div>
              <div className="crm-calendar-ds__agenda-body">
                <strong>{event.title ?? t(`events.${event.titleKey}`)}</strong>
                <span>
                  {event.customer} · {event.project}
                </span>
                <em>{t(`types.${event.type}`)}</em>
              </div>
              <span className="crm-calendar-ds__event-icon" aria-hidden="true">
                <IhIcon name={CALENDAR_EVENT_TYPE_ICONS[event.type]} size={14} />
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function CrmCalendarWorkspace({
  preview: previewProp,
  onOpenAi,
}: {
  preview?: CalendarWorkspacePreview;
  onOpenAi?: (prompt?: string) => void;
}) {
  const t = useTranslations('crm.calendar');
  const { openContact } = useContactCard();
  const [view, setView] = useState<CalendarViewMode>('month');
  const [filtersOpen, setFiltersOpen] = useState(false);
  const now = new Date();
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  monthStart.setDate(monthStart.getDate() - 7);
  const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 7, 23, 59, 59);
  const liveQuery = useQuery({
    queryKey: ['crm', 'calendar', monthStart.toISOString(), monthEnd.toISOString()],
    queryFn: () =>
      fetchCalendar({
        start: monthStart.toISOString(),
        end: monthEnd.toISOString(),
      }),
    enabled: !previewProp,
  });
  const preview =
    previewProp ?? buildCalendarPreview(liveQuery.data?.events ?? []);
  const openItem = (event: CalendarEvent) => {
    if (event.customerId) openContact(event.customerId);
  };

  if (!previewProp && liveQuery.isLoading) {
    return <LoadingState />;
  }

  return (
    <div className="crm-calendar-ds" data-testid="crm-calendar-workspace">
      <header className="crm-calendar-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-calendar-ds__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="crm-calendar-ds__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`)}
            delta={
              kpi.delta
                ? `${kpi.delta} ${t('kpis.trendSuffix')}`
                : undefined
            }
            {...(kpi.deltaTone ? { deltaTone: kpi.deltaTone } : {})}
            tone={kpi.tone === 'success' ? 'success' : 'default'}
            icon={<IhIcon name={CALENDAR_KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-calendar-ds__ai" aria-label={t('ai.aria')}>
        <button
          type="button"
          className="crm-calendar-ds__ai-cta"
          onClick={() => onOpenAi?.(t('ai.newEventPrompt'))}
        >
          <span className="crm-calendar-ds__ai-icon" aria-hidden="true">
            <IhIcon name="plus" size={15} />
          </span>
          <span>{t('actions.newEvent')}</span>
        </button>
        <button type="button" onClick={() => onOpenAi?.(t('ai.planPrompt'))}>
          <span className="crm-calendar-ds__ai-icon" aria-hidden="true">
            <IhIcon name="sparkles" size={15} />
          </span>
          <span>{t('actions.aiPlan')}</span>
        </button>
        <button
          type="button"
          aria-pressed={filtersOpen}
          className={filtersOpen ? 'is-featured' : undefined}
          onClick={() => setFiltersOpen((v) => !v)}
        >
          <span className="crm-calendar-ds__ai-icon" aria-hidden="true">
            <IhIcon name="search" size={15} />
          </span>
          <span>{t('actions.filters')}</span>
        </button>
        <button
          type="button"
          className="screenshot-dashboard__intro-ai-primary"
          onClick={() => onOpenAi?.(t('ai.openPrompt'))}
        >
          <IhIcon name="sparkles" size={15} />
          {t('ai.title')}
        </button>
      </nav>

      {filtersOpen ? (
        <div className="crm-calendar-ds__filters-stub" role="region" aria-label={t('actions.filters')}>
          <p>{t('filters.stub')}</p>
        </div>
      ) : null}

      <div className="crm-calendar-ds__layout">
        <div className="crm-calendar-ds__main">
          <div className="crm-calendar-ds__toolbar">
            <SegmentedControl
              ariaLabel={t('viewAria')}
              value={view}
              onChange={setView}
              options={CALENDAR_VIEW_ORDER.map((mode) => ({
                value: mode,
                label: t(`views.${mode}`),
              }))}
            />

            <div className="crm-calendar-ds__date-nav" role="group" aria-label={t('dateNav.aria')}>
              <Button type="button" variant="primary" size="sm" className="crm-calendar-ds__today-btn">
                {t('dateNav.today')}
              </Button>
              <button
                type="button"
                className="crm-calendar-ds__nav-btn"
                aria-label={t('dateNav.prev')}
                title={t('dateNav.prev')}
              >
                <IhIcon name="chevronLeft" size={14} />
              </button>
              <button
                type="button"
                className="crm-calendar-ds__nav-btn"
                aria-label={t('dateNav.next')}
                title={t('dateNav.next')}
              >
                <IhIcon name="chevronRight" size={14} />
              </button>
              <button
                type="button"
                className="crm-calendar-ds__range-btn"
                aria-label={t('dateNav.pick')}
                title={t('dateNav.pick')}
              >
                <IhIcon name="calendar" size={14} />
                <span>{preview.rangeLabel ?? t(`dateNav.ranges.${preview.rangeLabelKey}`)}</span>
              </button>
            </div>
          </div>

          {view === 'week' ? <WeekView preview={preview} onOpen={openItem} /> : null}
          {view === 'day' ? <DayView preview={preview} onOpen={openItem} /> : null}
          {view === 'month' ? <MonthView preview={preview} onOpen={openItem} /> : null}
          {view === 'agenda' ? <AgendaView preview={preview} /> : null}
        </div>

        <aside className="crm-calendar-ds__rail" aria-label={t('rail.aria')}>
          <section className="crm-calendar-ds__rail-card">
            <h3>{t('rail.upcoming')}</h3>
            <ul className="crm-calendar-ds__upcoming">
              {preview.upcoming.map((item) => (
                <li key={item.id} className={`is-${item.type}`}>
                  <span className="crm-calendar-ds__upcoming-icon" aria-hidden="true">
                    <IhIcon name={CALENDAR_EVENT_TYPE_ICONS[item.type]} size={13} />
                  </span>
                  <div>
                    <strong title={item.title ?? t(`events.${item.titleKey}`)}>
                      {item.title ?? t(`events.${item.titleKey}`)}
                    </strong>
                    <span>
                      {item.timeLabel} · {t(`rail.when.${item.when}`)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-calendar-ds__rail-card">
            <h3>{t('rail.quickCreate')}</h3>
            <ul className="crm-calendar-ds__quick">
              {CALENDAR_QUICK_CREATE.map((action) => (
                <li key={action.key}>
                  <button
                    type="button"
                    className="crm-calendar-ds__quick-btn"
                    title={t(`rail.quick.${action.key}`)}
                  >
                    <span className="crm-calendar-ds__quick-icon" aria-hidden="true">
                      <IhIcon name={action.icon} size={14} />
                    </span>
                    {t(`rail.quick.${action.key}`)}
                  </button>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-calendar-ds__rail-card crm-calendar-ds__rail-card--ai">
            <h3>{t('rail.aiSuggestions')}</h3>
            <ul className="crm-calendar-ds__recs">
              {preview.aiSuggestions.map((item) => (
                <li key={item.id}>{t(`rail.suggestions.${item.bodyKey}`)}</li>
              ))}
            </ul>
          </section>

          <section className="crm-calendar-ds__rail-card">
            <h3>{t('rail.sync')}</h3>
            <ul className="crm-calendar-ds__sync">
              {preview.sync.map((item) => (
                <li key={item.id}>
                  <div>
                    <strong>{t(`rail.providers.${item.providerKey}`)}</strong>
                    <span
                      className={`crm-calendar-ds__sync-status is-${item.status}`}
                    >
                      <i aria-hidden="true" />
                      {t(`rail.syncStatus.${item.status}`)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
