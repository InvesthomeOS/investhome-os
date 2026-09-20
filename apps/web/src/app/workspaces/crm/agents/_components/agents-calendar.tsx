'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Select } from '@investhome/ui';

import type { CrmActivitySummary } from '@/workspaces/crm/types/activities';
import type { CrmContactSummary } from '@/workspaces/crm/types';

const WEEKDAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
const SCHEDULED = new Set([
  'meeting',
  'zoom_meeting',
  'teams_meeting',
  'task',
  'follow_up',
  'reminder',
  'site_visit',
  'property_tour',
]);

function isoDate(day: Date) {
  const year = day.getFullYear();
  const month = String(day.getMonth() + 1).padStart(2, '0');
  const date = String(day.getDate()).padStart(2, '0');
  return `${year}-${month}-${date}`;
}

function eventDate(item: CrmActivitySummary): string | null {
  const raw = item.start_date || item.due_date;
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return raw.slice(0, 10);
  return isoDate(date);
}

function latestCursor(items: CrmActivitySummary[]) {
  const dates = items
    .map(eventDate)
    .filter((value): value is string => Boolean(value))
    .map((value) => new Date(value));
  if (!dates.length) {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  }
  const latest = dates.reduce((max, item) => (item > max ? item : max));
  return { year: latest.getFullYear(), month: latest.getMonth() };
}

function gridDays(year: number, month: number) {
  const first = new Date(year, month, 1);
  const shift = (first.getDay() + 6) % 7;
  const days: Date[] = [];
  const cursor = new Date(year, month, 1 - shift);
  for (let index = 0; index < 42; index += 1) {
    days.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return days;
}

export function AgentsCalendar({
  items,
  activities,
  onOpen,
}: {
  items: CrmContactSummary[];
  activities: CrmActivitySummary[];
  onOpen: (agentId: string) => void;
}) {
  const t = useTranslations('crm.agents');
  const scheduled = useMemo(
    () => activities.filter((item) => SCHEDULED.has(item.activity_type) && eventDate(item)),
    [activities],
  );
  const [cursor, setCursor] = useState(() => latestCursor(scheduled));
  const [seeded, setSeeded] = useState(false);
  const [personId, setPersonId] = useState('');

  useEffect(() => {
    if (seeded || !scheduled.length) return;
    setCursor(latestCursor(scheduled));
    setSeeded(true);
  }, [scheduled, seeded]);

  const people = useMemo(
    () => items.map((item) => [item.id, item.display_name] as const).sort((a, b) => a[1].localeCompare(b[1], 'tr')),
    [items],
  );

  const visible = scheduled.filter((item) => !personId || item.entity_id === personId);
  const byDay = useMemo(() => {
    const map = new Map<string, CrmActivitySummary[]>();
    for (const item of visible) {
      const key = eventDate(item);
      if (!key) continue;
      const list = map.get(key) ?? [];
      list.push(item);
      map.set(key, list);
    }
    return map;
  }, [visible]);

  const title = new Date(cursor.year, cursor.month, 1).toLocaleDateString('tr-TR', {
    month: 'long',
    year: 'numeric',
  });
  const monthKeys = useMemo(() => {
    const start = isoDate(new Date(cursor.year, cursor.month, 1));
    const end = isoDate(new Date(cursor.year, cursor.month + 1, 0));
    return { start, end };
  }, [cursor]);
  const monthHasEvents = [...byDay.keys()].some((key) => key >= monthKeys.start && key <= monthKeys.end);

  return (
    <section className="crm-agreements-calendar" data-testid="agents-calendar">
      <div className="crm-agreements-calendar__nav">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() =>
            setCursor((value) => {
              const date = new Date(value.year, value.month - 1, 1);
              return { year: date.getFullYear(), month: date.getMonth() };
            })
          }
        >
          ←
        </Button>
        <h2>{title}</h2>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() =>
            setCursor((value) => {
              const date = new Date(value.year, value.month + 1, 1);
              return { year: date.getFullYear(), month: date.getMonth() };
            })
          }
        >
          →
        </Button>
      </div>
      <Select label={t('personFilter')} value={personId} onChange={(event) => setPersonId(event.target.value)}>
        <option value="">{t('allPeople')}</option>
        {people.map(([id, name]) => (
          <option key={id} value={id}>
            {name}
          </option>
        ))}
      </Select>
      {!monthHasEvents ? <p>{t('emptyCalendar')}</p> : null}
      <div className="crm-agreements-month">
        {WEEKDAYS.map((day) => (
          <div key={day} className="crm-agreements-month__dow">
            {day}
          </div>
        ))}
        {gridDays(cursor.year, cursor.month).map((day) => {
          const key = isoDate(day);
          const muted = day.getMonth() !== cursor.month;
          const events = byDay.get(key) ?? [];
          return (
            <div key={key} className={`crm-agreements-day${muted ? ' is-muted' : ''}`}>
              <strong>{day.getDate()}</strong>
              {events.map((item) => (
                <button key={item.id} type="button" title={item.title} onClick={() => onOpen(item.entity_id)}>
                  {item.title}
                </button>
              ))}
            </div>
          );
        })}
      </div>
    </section>
  );
}
