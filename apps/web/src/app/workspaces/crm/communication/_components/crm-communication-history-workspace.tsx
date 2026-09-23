'use client';

import { useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, LoadingState, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { activityQueries } from '@/workspaces/crm/hooks/use-activities';
import type { ActivityListParams, CrmActivityType } from '@/workspaces/crm/types/activities';

import './ds/communication-ds.css';

const PAGE_SIZE = 25;

const COMM_TYPES: CrmActivityType[] = [
  'phone_call',
  'whatsapp',
  'email',
  'sms',
  'meeting',
  'zoom_meeting',
  'teams_meeting',
  'site_visit',
  'property_tour',
  'investor_meeting',
  'construction_meeting',
  'note',
  'comment',
  'other',
  'follow_up',
  'internal_discussion',
];

const TYPE_FILTERS: Record<string, CrmActivityType[]> = {
  all: COMM_TYPES,
  phone: ['phone_call'],
  whatsapp: ['whatsapp'],
  email: ['email'],
  meeting: [
    'meeting',
    'zoom_meeting',
    'teams_meeting',
    'site_visit',
    'property_tour',
    'investor_meeting',
    'construction_meeting',
  ],
  note: ['note', 'comment', 'other', 'internal_discussion', 'follow_up', 'sms'],
};

const COPY = {
  tr: {
    title: 'İletişim',
    subtitle: 'Mevcut CRM aktivite geçmişi — gönderim kanalı uydurulmaz.',
    search: 'Başlık, özet veya kişi ara',
    type: 'Tür',
    contact: 'Kişi',
    responsible: 'Sorumlu',
    date: 'Tarih',
    all: 'Tümü',
    phone: 'Telefon',
    whatsapp: 'WhatsApp',
    email: 'E-posta',
    meeting: 'Toplantı',
    note: 'Genel Not',
    name: 'Kişi / Kayıt',
    summary: 'Özet',
    followUp: 'Takip',
    related: 'İlgili proje',
    empty: 'Bu filtrelerle eşleşen iletişim kaydı yok.',
    previous: 'Önceki',
    next: 'Sonraki',
    today: 'Bugün',
    d7: '7 gün',
    d30: '30 gün',
    d90: '90 gün',
  },
  en: {
    title: 'Communication',
    subtitle: 'Existing CRM activity history — send channels are not invented.',
    search: 'Search title, summary or contact',
    type: 'Type',
    contact: 'Person',
    responsible: 'Owner',
    date: 'Date',
    all: 'All',
    phone: 'Phone',
    whatsapp: 'WhatsApp',
    email: 'Email',
    meeting: 'Meeting',
    note: 'Note',
    name: 'Person / record',
    summary: 'Summary',
    followUp: 'Follow-up',
    related: 'Related project',
    empty: 'No communication history matches these filters.',
    previous: 'Previous',
    next: 'Next',
    today: 'Today',
    d7: '7 days',
    d30: '30 days',
    d90: '90 days',
  },
} as const;

function dateRange(value: string): { date_from?: string; date_to?: string } {
  if (!value) return {};
  const now = new Date();
  const end = now.toISOString();
  if (value === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return { date_from: start.toISOString(), date_to: end };
  }
  const days = value === '7d' ? 7 : value === '30d' ? 30 : value === '90d' ? 90 : 0;
  if (!days) return {};
  return { date_from: new Date(now.getTime() - days * 86_400_000).toISOString(), date_to: end };
}

function typeLabel(copy: (typeof COPY)['tr'], type: string): string {
  if (type === 'phone_call') return copy.phone;
  if (type === 'whatsapp') return copy.whatsapp;
  if (type === 'email') return copy.email;
  if (
    type === 'meeting' ||
    type === 'zoom_meeting' ||
    type === 'teams_meeting' ||
    type === 'site_visit' ||
    type === 'property_tour' ||
    type === 'investor_meeting' ||
    type === 'construction_meeting'
  ) {
    return copy.meeting;
  }
  return copy.note;
}

export function CrmCommunicationHistoryWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const { openContact } = useContactCard();
  const [search, setSearch] = useState('');
  const [type, setType] = useState('all');
  const [contactId, setContactId] = useState('');
  const [responsibleId, setResponsibleId] = useState('');
  const [date, setDate] = useState('');
  const [page, setPage] = useState(1);

  const listParams = useMemo<ActivityListParams>(
    () => ({
      page,
      page_size: PAGE_SIZE,
      sort_by: 'created_at',
      sort_dir: 'desc',
      search: search.trim() || undefined,
      activity_types: TYPE_FILTERS[type] ?? COMM_TYPES,
      entity_type: contactId ? 'contact' : undefined,
      entity_id: contactId || undefined,
      responsible_user_id: responsibleId || undefined,
      ...dateRange(date),
    }),
    [page, search, type, contactId, responsibleId, date],
  );

  const listQuery = useQuery(activityQueries.list(listParams));
  const contactsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'communication-filter'],
    queryFn: () => fetchContacts({ page: 1, page_size: 100, sort_by: 'last_contact_at', sort_dir: 'desc' }),
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'communication-filter'],
    queryFn: () => fetchUsers({ status: 'active' }),
  });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  if (listQuery.isLoading) {
    return <LoadingState label={copy.title} />;
  }

  return (
    <div className="comm-ds" data-testid="crm-communication-history">
      <header className="comm-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <span className="comm-ds__panel-head-meta">{total}</span>
      </header>

      <section className="comm-ds__toolbar comm-ds__toolbar--history" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder={copy.search}
        />
        <Select
          label={copy.type}
          value={type}
          onChange={(e) => {
            setType(e.target.value);
            setPage(1);
          }}
        >
          <option value="all">{copy.all}</option>
          <option value="phone">{copy.phone}</option>
          <option value="whatsapp">{copy.whatsapp}</option>
          <option value="email">{copy.email}</option>
          <option value="meeting">{copy.meeting}</option>
          <option value="note">{copy.note}</option>
        </Select>
        <Select
          label={copy.contact}
          value={contactId}
          onChange={(e) => {
            setContactId(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{copy.all}</option>
          {(contactsQuery.data?.items ?? []).map((contact) => (
            <option key={contact.id} value={contact.id}>
              {contact.display_name}
            </option>
          ))}
        </Select>
        <Select
          label={copy.responsible}
          value={responsibleId}
          onChange={(e) => {
            setResponsibleId(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{copy.all}</option>
          {(usersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
        <Select
          label={copy.date}
          value={date}
          onChange={(e) => {
            setDate(e.target.value);
            setPage(1);
          }}
        >
          <option value="">{copy.all}</option>
          <option value="today">{copy.today}</option>
          <option value="7d">{copy.d7}</option>
          <option value="30d">{copy.d30}</option>
          <option value="90d">{copy.d90}</option>
        </Select>
      </section>

      {items.length === 0 ? (
        <div className="comm-ds__empty">{copy.empty}</div>
      ) : (
        <div className="comm-ds__table-wrap">
          <table className="comm-ds__table">
            <thead>
              <tr>
                <th>{copy.name}</th>
                <th>{copy.type}</th>
                <th>{copy.date}</th>
                <th>{copy.responsible}</th>
                <th>{copy.summary}</th>
                <th>{copy.followUp}</th>
                <th>{copy.related}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    {row.entity_type === 'contact' ? (
                      <button
                        type="button"
                        className="comm-ds__card-link"
                        onClick={() => openContact(row.entity_id)}
                      >
                        {row.entity_name || row.title}
                      </button>
                    ) : (
                      row.entity_name || row.title
                    )}
                  </td>
                  <td>
                    <StatusChip tone="info">{typeLabel(copy, row.activity_type)}</StatusChip>
                  </td>
                  <td>{new Date(row.created_at).toLocaleString(locale)}</td>
                  <td>{row.owner_name || row.assigned_user_name || row.created_by_name || '—'}</td>
                  <td>{row.summary || row.title}</td>
                  <td>{row.due_date ? new Date(row.due_date).toLocaleString(locale) : '—'}</td>
                  <td>{row.related_entity_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="comm-ds__pagination">
        <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
          {copy.previous}
        </Button>
        <span>
          {page} / {pages}
        </span>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= pages}
          onClick={() => setPage((p) => p + 1)}
        >
          {copy.next}
        </Button>
      </div>
    </div>
  );
}
