'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Select } from '@investhome/ui';

import type { CrmActivitySummary } from '@/workspaces/crm/types/activities';
import type { CrmContactSummary } from '@/workspaces/crm/types';

import { displayDate, responsibleOf } from './agents-stage';

const ACTIVITY_TYPES = [
  { id: '', label: 'Tümü' },
  { id: 'phone_call', label: 'Arama' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'email', label: 'E-posta' },
  { id: 'comment', label: 'Yorum' },
  { id: 'task', label: 'Görev' },
  { id: 'meeting', label: 'Toplantı' },
  { id: 'follow_up', label: 'Takip' },
];

const TYPE_LABELS: Record<string, string> = {
  phone_call: 'Arama',
  whatsapp: 'WhatsApp',
  email: 'E-posta',
  comment: 'Yorum',
  task: 'Görev',
  meeting: 'Toplantı',
  zoom_meeting: 'Toplantı',
  teams_meeting: 'Toplantı',
  follow_up: 'Takip',
};

const MEETING_TYPES = new Set(['meeting', 'zoom_meeting', 'teams_meeting']);

export function AgentsActivities({
  items,
  activities,
  onOpen,
}: {
  items: CrmContactSummary[];
  activities: CrmActivitySummary[];
  onOpen: (agentId: string) => void;
}) {
  const t = useTranslations('crm.agents');
  const [personId, setPersonId] = useState('');
  const [responsible, setResponsible] = useState('');
  const [activityType, setActivityType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const people = useMemo(
    () => items.map((item) => [item.id, item.display_name] as const).sort((a, b) => a[1].localeCompare(b[1], 'tr')),
    [items],
  );
  const responsibles = useMemo(
    () => [...new Set(items.map(responsibleOf).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'tr')),
    [items],
  );

  const filtered = useMemo(() => {
    const from = dateFrom ? Date.parse(dateFrom) : null;
    const to = dateTo ? Date.parse(`${dateTo}T23:59:59`) : null;
    return activities.filter((item) => {
      if (personId && item.entity_id !== personId) return false;
      if (activityType) {
        const matchesType =
          activityType === 'meeting' ? MEETING_TYPES.has(item.activity_type) : item.activity_type === activityType;
        if (!matchesType) return false;
      }
      if (responsible) {
        const agent = items.find((row) => row.id === item.entity_id);
        const name = item.assigned_user_name || item.owner_name || (agent ? responsibleOf(agent) : '');
        if (name !== responsible) return false;
      }
      const when = Date.parse(item.created_at || item.start_date || '');
      if (from && !Number.isNaN(when) && when < from) return false;
      if (to && !Number.isNaN(when) && when > to) return false;
      return true;
    });
  }, [activities, activityType, dateFrom, dateTo, items, personId, responsible]);

  return (
    <section className="crm-agreements-feed" data-testid="agents-activities">
      <div className="crm-agreements-filters" aria-label={t('filters')}>
        <Select label={t('personFilter')} value={personId} onChange={(event) => setPersonId(event.target.value)}>
          <option value="">{t('allPeople')}</option>
          {people.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </Select>
        <Select label={t('responsibleFilter')} value={responsible} onChange={(event) => setResponsible(event.target.value)}>
          <option value="">{t('allResponsible')}</option>
          {responsibles.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('activityTypeFilter')}
          value={activityType}
          onChange={(event) => setActivityType(event.target.value)}
        >
          {ACTIVITY_TYPES.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </Select>
        <label className="ih-field">
          <span className="ih-field__label">{t('dateFrom')}</span>
          <input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        </label>
        <label className="ih-field">
          <span className="ih-field__label">{t('dateTo')}</span>
          <input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        </label>
      </div>
      {!filtered.length ? <p>{t('emptyActivities')}</p> : null}
      {filtered.length ? (
        <p className="crm-agreements-count">
          {Math.min(filtered.length, 80)} / {filtered.length}
        </p>
      ) : null}
      {filtered.slice(0, 80).map((item) => {
        const agent = items.find((row) => row.id === item.entity_id);
        return (
          <article key={item.id} className="crm-agreements-event">
            <small>
              {displayDate(item.created_at)}
              {item.activity_type ? ` · ${TYPE_LABELS[item.activity_type] || item.activity_type}` : ''}
            </small>
            <button type="button" onClick={() => onOpen(item.entity_id)}>
              {item.title}
            </button>
            {item.summary ? <p>{item.summary}</p> : null}
            <small>
              {[agent?.display_name, item.assigned_user_name || item.owner_name || (agent ? responsibleOf(agent) : '')]
                .filter(Boolean)
                .join(' · ')}
            </small>
          </article>
        );
      })}
    </section>
  );
}
