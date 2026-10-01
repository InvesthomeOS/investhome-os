'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Select } from '@investhome/ui';

import {
  fetchAgreementActivities,
  type CrmAgreementSummary,
} from '@/workspaces/crm/api/agreements';
import { emailPreviewText } from '@/workspaces/crm/contact-card/history-html';

import { displayDate } from './agreements-stage';

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

export function AgreementsActivities({
  projectGroup,
  items,
  onOpenAgreement,
}: {
  projectGroup: string;
  items: CrmAgreementSummary[];
  onOpenAgreement: (agreementId: string, contactId: string) => void;
}) {
  const t = useTranslations('crm.agreements');
  const [personId, setPersonId] = useState('');
  const [responsible, setResponsible] = useState('');
  const [activityType, setActivityType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const people = useMemo(() => {
    const map = new Map<string, string>();
    for (const row of items) {
      for (const owner of row.participants || []) {
        map.set(owner.contact_id, owner.display_name);
      }
      if (row.contact_id && row.contact_name) map.set(row.contact_id, row.contact_name);
    }
    return [...map.entries()].sort((a, b) => a[1].localeCompare(b[1], 'tr'));
  }, [items]);

  const responsibles = useMemo(() => {
    return [...new Set(items.map((item) => item.responsible_name).filter(Boolean) as string[])].sort((a, b) =>
      a.localeCompare(b, 'tr'),
    );
  }, [items]);

  const query = useQuery({
    queryKey: ['crm', 'agreements', 'activities', projectGroup, personId, responsible, activityType, dateFrom, dateTo],
    queryFn: () =>
      fetchAgreementActivities({
        project_group: projectGroup || undefined,
        contact_id: personId || undefined,
        activity_type: activityType || undefined,
        responsible: responsible || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page: 1,
        page_size: 100,
      }),
  });

  return (
    <section className="crm-agreements-feed" data-testid="agreements-activities">
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
        <Select label={t('activityTypeFilter')} value={activityType} onChange={(event) => setActivityType(event.target.value)}>
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

      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}
      {!query.isLoading && !query.data?.items.length ? <p>{t('emptyActivities')}</p> : null}

      {query.data?.items.map((item) => (
        <article key={item.id} className="crm-agreements-event">
          <small>
            {displayDate(item.created_at)}
            {item.activity_type ? ` · ${TYPE_LABELS[item.activity_type] || item.activity_type}` : ''}
            {item.project_label ? ` · ${item.project_label}` : ''}
          </small>
          {item.agreement_id && item.contact_id ? (
            <button type="button" onClick={() => onOpenAgreement(item.agreement_id as string, item.contact_id as string)}>
              {item.title}
            </button>
          ) : (
            <strong>{item.title}</strong>
          )}
          {item.summary ? <p>{emailPreviewText(item.summary)}</p> : null}
          <small>
            {[item.contact_name, item.responsible_name || item.actor_name].filter(Boolean).join(' · ')}
          </small>
        </article>
      ))}
    </section>
  );
}
