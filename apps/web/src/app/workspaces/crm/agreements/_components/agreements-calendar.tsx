'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Select } from '@investhome/ui';

import {
  fetchAgreementCalendar,
  type CrmAgreementSummary,
} from '@/workspaces/crm/api/agreements';

const WEEKDAYS = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

function isoDate(day: Date) {
  const year = day.getFullYear();
  const month = String(day.getMonth() + 1).padStart(2, '0');
  const date = String(day.getDate()).padStart(2, '0');
  return `${year}-${month}-${date}`;
}

function monthBounds(year: number, month: number) {
  const start = new Date(year, month, 1);
  const end = new Date(year, month + 1, 0);
  return {
    start: isoDate(start),
    end: isoDate(end),
    startDate: start,
    endDate: end,
  };
}

function latestCursor(items: CrmAgreementSummary[]) {
  const dates = items
    .flatMap((row) => [row.close_date, row.begin_date, row.agreement_date])
    .map((value) => (value ? new Date(value) : null))
    .filter((value): value is Date => Boolean(value && !Number.isNaN(value.getTime())));
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

export function AgreementsCalendar({
  projectGroup,
  items,
  onOpenAgreement,
}: {
  projectGroup: string;
  items: CrmAgreementSummary[];
  onOpenAgreement: (agreementId: string, contactId: string) => void;
}) {
  const t = useTranslations('crm.agreements');
  const [cursor, setCursor] = useState(() => latestCursor(items));
  const [personId, setPersonId] = useState('');
  const bounds = monthBounds(cursor.year, cursor.month);

  const people = useMemo(() => {
    const map = new Map<string, string>();
    for (const row of items) {
      for (const owner of row.participants || []) map.set(owner.contact_id, owner.display_name);
      if (row.contact_id && row.contact_name) map.set(row.contact_id, row.contact_name);
    }
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1], 'tr'));
  }, [items]);

  const query = useQuery({
    queryKey: ['crm', 'agreements', 'calendar', projectGroup, personId, bounds.start, bounds.end],
    queryFn: () =>
      fetchAgreementCalendar({
        start: bounds.start,
        end: bounds.end,
        project_group: projectGroup || undefined,
        contact_id: personId || undefined,
      }),
  });

  const byDay = useMemo(() => {
    const map = new Map<string, NonNullable<typeof query.data>['items']>();
    for (const item of query.data?.items ?? []) {
      const list = map.get(item.date) ?? [];
      list.push(item);
      map.set(item.date, list);
    }
    return map;
  }, [query.data]);

  const title = new Date(cursor.year, cursor.month, 1).toLocaleDateString('tr-TR', {
    month: 'long',
    year: 'numeric',
  });

  return (
    <section className="crm-agreements-calendar" data-testid="agreements-calendar">
      <div className="crm-agreements-calendar__nav">
        <Button type="button" variant="secondary" size="sm" onClick={() => setCursor((value) => {
          const date = new Date(value.year, value.month - 1, 1);
          return { year: date.getFullYear(), month: date.getMonth() };
        })}>
          ←
        </Button>
        <h2>{title}</h2>
        <Button type="button" variant="secondary" size="sm" onClick={() => setCursor((value) => {
          const date = new Date(value.year, value.month + 1, 1);
          return { year: date.getFullYear(), month: date.getMonth() };
        })}>
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
      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}
      {!query.isLoading && !(query.data?.items.length) ? <p>{t('emptyCalendar')}</p> : null}
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
              {events.map((item) => {
                const contactId = items.find((row) => row.id === item.agreement_id)?.contact_id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    title={item.title}
                    onClick={() => {
                      if (item.agreement_id && contactId) onOpenAgreement(item.agreement_id, contactId);
                    }}
                  >
                    {item.title}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
    </section>
  );
}
