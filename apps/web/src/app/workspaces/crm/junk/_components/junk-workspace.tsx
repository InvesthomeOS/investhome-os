'use client';

import { useEffect, useState } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select, StatusChip } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchJunkReasons, type ContactListParams } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';

import '../../contacts/_components/ds/contacts-ds.css';

const PAGE_SIZE = 25;

const COPY = {
  tr: {
    title: 'Junk',
    subtitle: 'Bitrix Junklar listesinden gelen mevcut arşiv CRM kişileri — yeni kişi tablosu değil',
    search: 'Ad, telefon veya e-posta ara',
    name: 'Ad Soyad',
    phone: 'Telefon',
    extraPhone: 'Ek telefon',
    email: 'E-posta',
    extraEmail: 'Ek e-posta',
    junkReason: 'Junk Sebebi',
    source: 'Kaynak',
    lastActivity: 'Son Aktivite / Son İletişim',
    owner: 'Sorumlu',
    allReasons: 'Tüm sebepler',
    empty: 'Bu filtrelerle eşleşen Junk kişi yok.',
    previous: 'Önceki',
    next: 'Sonraki',
    archived: 'Junk / Arşiv',
  },
  en: {
    title: 'Junk',
    subtitle: 'Current archived CRM contacts from the Bitrix Junklar list — not a second person table',
    search: 'Search name, phone or email',
    name: 'Name',
    phone: 'Phone',
    extraPhone: 'Additional phone',
    email: 'Email',
    extraEmail: 'Additional email',
    junkReason: 'Junk reason',
    source: 'Source',
    lastActivity: 'Last activity / last contact',
    owner: 'Owner',
    allReasons: 'All reasons',
    empty: 'No Junk contacts match these filters.',
    previous: 'Previous',
    next: 'Next',
    archived: 'Junk / Archived',
  },
} as const;

export function JunkWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const { openContact } = useContactCard();
  const { authLoading, canRead } = useCrmAccess();
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [junkReason, setJunkReason] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const params: ContactListParams = {
    search: search || undefined,
    bitrix_list: 'current_junk',
    junk_reason: junkReason || undefined,
    include_archived: true,
    sort_by: 'display_name',
    sort_dir: 'asc',
    page,
    page_size: PAGE_SIZE,
  };
  const query = useQuery({
    ...contactQueries.list(params),
    enabled: !authLoading && canRead,
  });
  const reasonsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'junk-reasons'],
    queryFn: fetchJunkReasons,
    enabled: !authLoading && canRead,
  });
  const rows = query.data?.items ?? [];
  const pages = Math.max(1, query.data?.pages ?? 1);

  return (
    <div className="ctc-ds" data-testid="crm-junk-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
      </header>

      <section className="ctc-ds__toolbar" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.search}
          data-testid="crm-junk-search"
        />
        <Select
          label={copy.junkReason}
          value={junkReason}
          onChange={(event) => {
            setJunkReason(event.target.value);
            setPage(1);
          }}
          data-testid="crm-junk-reason-filter"
        >
          <option value="">{copy.allReasons}</option>
          {(reasonsQuery.data?.items ?? []).map((item) => (
            <option key={item.reason} value={item.reason}>
              {item.reason} ({item.count})
            </option>
          ))}
        </Select>
      </section>

      <section className="ctc-ds__table-section" aria-label={copy.title}>
        {query.isLoading ? <div className="ctc-ds__skeleton">Loading…</div> : null}
        {query.isError ? <div className="ctc-ds__empty">{query.error.message}</div> : null}
        {!query.isLoading && !query.isError && rows.length === 0 ? (
          <div className="ctc-ds__empty" data-testid="crm-junk-empty">{copy.empty}</div>
        ) : null}
        {rows.length ? (
          <div className="ctc-ds__table-wrap">
            <table className="ctc-ds__table">
              <thead>
                <tr>
                  <th>{copy.name}</th>
                  <th>{copy.phone}</th>
                  <th>{copy.extraPhone}</th>
                  <th>{copy.email}</th>
                  <th>{copy.extraEmail}</th>
                  <th>{copy.junkReason}</th>
                  <th>{copy.source}</th>
                  <th>{copy.lastActivity}</th>
                  <th>{copy.owner}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((contact) => (
                  <tr
                    key={contact.id}
                    className="ctc-ds__row"
                    data-testid={`crm-junk-row-${contact.id}`}
                    onClick={() => openContact(contact.id)}
                  >
                    <td><strong>{contact.display_name}</strong></td>
                    <td>{contact.primary_phone ?? '—'}</td>
                    <td>
                      {(contact.secondary_phones ?? []).length
                        ? (contact.secondary_phones ?? []).join(', ')
                        : '—'}
                    </td>
                    <td>{contact.primary_email ?? '—'}</td>
                    <td>
                      {(contact.secondary_emails ?? []).length
                        ? (contact.secondary_emails ?? []).join(', ')
                        : '—'}
                    </td>
                    <td>{contact.junk_reason ?? '—'}</td>
                    <td>
                      <StatusChip tone="default">
                        {[contact.source, contact.bitrix_source_channel].filter(Boolean).join(' · ') || copy.archived}
                      </StatusChip>
                    </td>
                    <td>
                      {contact.last_contact_at
                        ? new Date(contact.last_contact_at).toLocaleString(locale)
                        : '—'}
                    </td>
                    <td>{contact.owner_name ?? contact.bitrix_responsible ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {query.data?.total ? (
        <div className="ctc-ds__pagination">
          <span>{page} / {pages} · {query.data.total.toLocaleString(locale)}</span>
          <div>
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
              {copy.previous}
            </Button>
            <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>
              {copy.next}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
