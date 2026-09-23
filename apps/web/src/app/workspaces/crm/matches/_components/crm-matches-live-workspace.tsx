'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  decideCrmMatch,
  fetchCrmMatch,
  fetchCrmMatches,
  type CrmMatchAction,
  type CrmMatchItem,
  type CrmMatchPerson,
  type CrmMatchPurchase,
  type CrmMatchStatus,
} from '@/workspaces/crm/api/crm-matches';

const REASONS = ['phone', 'email', 'secondary_email', 'bitrix', 'name_review'] as const;
const STATUSES: CrmMatchStatus[] = ['pending', 'in_review', 'same_person', 'different'];

const COPY = {
  tr: {
    title: 'Matches',
    subtitle: 'Olası mükerrer / ilişkili kimlik incelemesi. Canlı CRM verisi, otomatik birleştirme yok.',
    kpis: 'Eşleşme özeti',
    pending: 'İnceleme Bekleyen',
    strong: 'Güçlü Eşleşme',
    possible: 'Olası Eşleşme',
    rejected: 'Reddedilen',
    search: 'Ara',
    searchPh: 'Ad, telefon, e-posta',
    matchType: 'Eşleşme Türü',
    status: 'Durum',
    source: 'Kaynak',
    any: 'Tümü',
    clear: 'Filtreleri Temizle',
    emptyTitle: 'İncelenecek eşleşme yok',
    emptyBody: 'Canlı kayıtlarda bekleyen kimlik eşleşmesi yok. Demo satır eklenmez.',
    person1: 'Kişi 1',
    person2: 'Kişi 2',
    reason: 'Eşleşme Nedeni',
    sharedPhone: 'Ortak Telefon',
    sharedEmail: 'Ortak E-posta',
    action: 'İşlem',
    open: 'Aç',
    close: 'Kapat',
    same: 'Aynı Kişi',
    different: 'Farklı Kişiler',
    hold: 'İncelemede Tut',
    notes: 'İnceleme notu',
    evidence: 'Kesin eşleşme kanıtı',
    conflicts: 'Çelişen alanlar',
    purchases: 'Satın almalar',
    sourceIds: 'Kaynak ID',
    reviewNotes: 'Mevcut inceleme notları',
    protected: 'Korumalı kayıt',
    none: '—',
    filters: 'Eşleşme filtreleri',
    table: 'Eşleşme listesi',
    phone: 'Telefon',
    email: 'E-posta',
    historical: 'geçmiş birim',
    mergeBlocked: 'Kayıtlar birleştirilmedi.',
    nameReviewHint: 'Benzer ad yalnızca inceleme ipucudur; birleştirme kanıtı değildir.',
  },
  en: {
    title: 'Matches',
    subtitle: 'Possible duplicate / related identity review. Live CRM data, no automatic merge.',
    kpis: 'Match summary',
    pending: 'Awaiting review',
    strong: 'Strong match',
    possible: 'Possible match',
    rejected: 'Rejected',
    search: 'Search',
    searchPh: 'Name, phone, email',
    matchType: 'Match type',
    status: 'Status',
    source: 'Source',
    any: 'All',
    clear: 'Clear filters',
    emptyTitle: 'No matches to review',
    emptyBody: 'No pending identity matches in live records. Demo rows are not added.',
    person1: 'Person 1',
    person2: 'Person 2',
    reason: 'Match reason',
    sharedPhone: 'Shared phone',
    sharedEmail: 'Shared email',
    action: 'Action',
    open: 'Open',
    close: 'Close',
    same: 'Same person',
    different: 'Different people',
    hold: 'Keep in review',
    notes: 'Review note',
    evidence: 'Exact matching evidence',
    conflicts: 'Conflicting fields',
    purchases: 'Purchases',
    sourceIds: 'Source IDs',
    reviewNotes: 'Existing review notes',
    protected: 'Protected record',
    none: '—',
    filters: 'Match filters',
    table: 'Match list',
    phone: 'Phone',
    email: 'Email',
    historical: 'historical unit',
    mergeBlocked: 'Records were not merged.',
    nameReviewHint: 'Similar name is a review clue only, never merge evidence.',
  },
};

const REASON_LABEL: Record<string, { tr: string; en: string }> = {
  phone: { tr: 'Aynı telefon', en: 'Same phone' },
  email: { tr: 'Aynı e-posta', en: 'Same email' },
  secondary_email: { tr: 'Aynı ikincil e-posta', en: 'Same secondary email' },
  bitrix: { tr: 'Aynı Bitrix kimliği', en: 'Same Bitrix identity' },
  name_review: { tr: 'Benzer ad (ipucu)', en: 'Similar name (clue)' },
};

const STATUS_LABEL: Record<CrmMatchStatus, { tr: string; en: string }> = {
  pending: { tr: 'Bekliyor', en: 'Pending' },
  in_review: { tr: 'İncelemede', en: 'In review' },
  same_person: { tr: 'Aynı kişi', en: 'Same person' },
  different: { tr: 'Farklı kişiler', en: 'Different' },
};

function reasonLabel(value: string, locale: 'tr' | 'en'): string {
  return REASON_LABEL[value]?.[locale] ?? value;
}

function statusLabel(value: CrmMatchStatus, locale: 'tr' | 'en'): string {
  return STATUS_LABEL[value][locale];
}

function purchaseLine(row: CrmMatchPurchase, historical: string): string {
  const bits = [row.project, row.unit].filter(Boolean);
  if (row.historical) bits.push(historical);
  return bits.join(' · ') || '—';
}

function PersonPane({
  title,
  person,
  t,
}: {
  title: string;
  person: CrmMatchPerson;
  t: (typeof COPY)['tr'];
}) {
  return (
    <div className="crm-matches-live__pane">
      <h4>{title}</h4>
      <p>
        <Link href={person.href as Route}>{person.name}</Link>
        {person.review_required ? <span className="crm-matches-live__flag">{t.protected}</span> : null}
      </p>
      <p>
        {t.phone}: {person.phone || t.none}
        <br />
        {t.email}: {person.email || t.none}
        <br />
        {t.source}: {person.source || t.none}
      </p>
      <p>
        {t.sourceIds}: {person.source_ids.join(', ') || t.none}
      </p>
      <p>
        {t.purchases}:{' '}
        {person.purchases.length
          ? person.purchases.map((row) => purchaseLine(row, t.historical)).join('; ')
          : t.none}
      </p>
    </div>
  );
}

export function CrmMatchesLiveWorkspace({ initialId }: { initialId?: string }) {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const t = COPY[locale];
  const { canRead, authLoading, user } = useCrmAccess();
  const canWrite = canUpdateCrm(user);
  const queryClient = useQueryClient();
  const { openContact } = useContactCard();

  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [matchType, setMatchType] = useState('');
  const [status, setStatus] = useState('');
  const [source, setSource] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(initialId ?? null);
  const [note, setNote] = useState('');
  const [toast, setToast] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      match_type: matchType || undefined,
      status: status || undefined,
      source: source || undefined,
    }),
    [search, matchType, status, source],
  );

  const listQuery = useQuery({
    queryKey: ['crm-matches', filters],
    queryFn: () => fetchCrmMatches(filters),
    enabled: canRead && !authLoading,
  });

  const detailQuery = useQuery({
    queryKey: ['crm-match', selectedId],
    queryFn: () => fetchCrmMatch(selectedId as string),
    enabled: Boolean(selectedId),
  });

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2800);
  };

  const decisionMutation = useMutation({
    mutationFn: ({ id, action }: { id: string; action: CrmMatchAction }) => decideCrmMatch(id, action, note),
    onSuccess: async (detail) => {
      setNote('');
      await queryClient.invalidateQueries({ queryKey: ['crm-matches'] });
      await queryClient.invalidateQueries({ queryKey: ['crm-match', detail.id] });
      showToast(detail.merge_message || t.mergeBlocked);
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : t.mergeBlocked);
    },
  });

  const data = listQuery.data;
  const kpis = data?.kpis ?? { pending: 0, strong: 0, possible: 0, rejected: 0, same_person: 0 };
  const items = data?.items ?? [];
  const selected = detailQuery.data ?? null;

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setMatchType('');
    setStatus('');
    setSource('');
  };

  const openRow = (item: CrmMatchItem) => {
    setSelectedId(item.id);
    setNote('');
  };

  if (authLoading || listQuery.isLoading) {
    return <LoadingState />;
  }
  if (!canRead) {
    return <ErrorState title={t.title} message="No access" />;
  }
  if (listQuery.isError) {
    return <ErrorState title={t.title} message={t.emptyBody} />;
  }

  return (
    <div className="crm-tasks crm-tasks--ops crm-leads crm-matches-live" data-testid="crm-matches-workspace">
      {toast ? (
        <div className="crm-leads__toast" role="status">
          {toast}
        </div>
      ) : null}

      <header className="crm-tasks__header">
        <div>
          <h1>{t.title}</h1>
          <p>{t.subtitle}</p>
        </div>
      </header>

      <section className="crm-leads__kpi-row crm-matches-live__kpi-row" aria-label={t.kpis}>
        {(
          [
            ['pending', t.pending, kpis.pending, 'crm-matches-kpi-pending'],
            ['strong', t.strong, kpis.strong, 'crm-matches-kpi-strong'],
            ['possible', t.possible, kpis.possible, 'crm-matches-kpi-possible'],
            ['different', t.rejected, kpis.rejected, 'crm-matches-kpi-rejected'],
          ] as const
        ).map(([value, label, count, testId]) => (
          <button
            key={value}
            type="button"
            className={`crm-leads__kpi${(value === 'strong' || value === 'possible' ? matchType : status) === value ? ' is-active' : ''}${value === 'pending' && status === 'pending' ? ' is-active' : ''}`}
            data-testid={testId}
            onClick={() => {
              if (value === 'strong' || value === 'possible') {
                setMatchType(matchType === value ? '' : value);
                setStatus('pending');
                return;
              }
              setMatchType('');
              setStatus(status === value ? '' : value);
            }}
          >
            <span>{label}</span>
            <strong>{count.toLocaleString(locale)}</strong>
          </button>
        ))}
      </section>

      <section className="crm-tasks__filters" aria-label={t.filters}>
        <div className="crm-tasks__search">
          <Input
            label={t.search}
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            onBlur={() => setSearch(searchDraft.trim())}
            onKeyDown={(event) => {
              if (event.key === 'Enter') setSearch(searchDraft.trim());
            }}
            placeholder={t.searchPh}
          />
        </div>
        <Select label={t.matchType} value={matchType} onChange={(event) => setMatchType(event.target.value)}>
          <option value="">{t.any}</option>
          {REASONS.map((item) => (
            <option key={item} value={item}>
              {reasonLabel(item, locale)}
            </option>
          ))}
        </Select>
        <Select label={t.status} value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">{t.any}</option>
          {STATUSES.map((item) => (
            <option key={item} value={item}>
              {statusLabel(item, locale)}
            </option>
          ))}
        </Select>
        <Select label={t.source} value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="">{t.any}</option>
          {(data?.sources ?? []).map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </Select>
        <div className="crm-tasks__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t.clear}
          </Button>
        </div>
      </section>

      <div className="crm-tasks__table-wrap" role="region" aria-label={t.table}>
        {items.length === 0 ? (
          <div className="crm-tasks__empty" data-testid="crm-matches-empty">
            <strong>{t.emptyTitle}</strong>
            <p>{t.emptyBody}</p>
          </div>
        ) : (
          <table className="crm-tasks__table crm-tasks__table--ops" data-testid="crm-matches-table">
            <thead>
              <tr>
                <th>{t.person1}</th>
                <th>{t.person2}</th>
                <th>{t.reason}</th>
                <th>{t.sharedPhone}</th>
                <th>{t.sharedEmail}</th>
                <th>{t.source}</th>
                <th>{t.status}</th>
                <th>{t.action}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} onClick={() => openRow(item)}>
                  <td>
                    {item.person_a_name}
                    {item.protected ? <div className="crm-matches-live__flag">{t.protected}</div> : null}
                  </td>
                  <td>{item.person_b_name}</td>
                  <td>{item.reasons.map((reason) => reasonLabel(reason, locale)).join(', ')}</td>
                  <td>{item.shared_phone || t.none}</td>
                  <td>{item.shared_email || t.none}</td>
                  <td>{item.source || t.none}</td>
                  <td>{statusLabel(item.status, locale)}</td>
                  <td>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      onClick={(event) => {
                        event.stopPropagation();
                        openRow(item);
                      }}
                    >
                      {t.open}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {selectedId ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={t.close} onClick={() => setSelectedId(null)} />
          <aside className="crm-tasks__drawer" role="dialog" data-testid="crm-matches-drawer">
            <div className="crm-tasks__drawer-head">
              <h3>
                {selected ? `${selected.person_a_name} · ${selected.person_b_name}` : t.title}
              </h3>
              <button type="button" className="crm-tasks__link-btn" onClick={() => setSelectedId(null)}>
                {t.close}
              </button>
            </div>
            <div className="crm-tasks__drawer-body">
              {selected ? (
                <>
                  <div className="crm-matches-live__compare">
                    <PersonPane title={t.person1} person={selected.person_a} t={t} />
                    <PersonPane title={t.person2} person={selected.person_b} t={t} />
                  </div>
                  <h4>{t.evidence}</h4>
                  <ul className="crm-leads__history">
                    {selected.evidence.length === 0 ? <li>{t.none}</li> : null}
                    {selected.evidence.map((item) => (
                      <li key={`${item.reason}-${item.value}`}>
                        {reasonLabel(item.reason, locale)}
                        <small>{item.value || t.none}</small>
                      </li>
                    ))}
                  </ul>
                  {selected.reasons.includes('name_review') ? <p>{t.nameReviewHint}</p> : null}
                  <h4>{t.conflicts}</h4>
                  <p>{selected.conflicts.map((item) => item).join(', ') || t.none}</p>
                  <h4>{t.purchases}</h4>
                  <p>
                    {selected.linked_purchases.length
                      ? selected.linked_purchases.map((row) => purchaseLine(row, t.historical)).join('; ')
                      : t.none}
                  </p>
                  <h4>{t.sourceIds}</h4>
                  <p>
                    {selected.person_a.source_ids.join(', ') || t.none} / {selected.person_b.source_ids.join(', ') || t.none}
                  </p>
                  <h4>{t.reviewNotes}</h4>
                  <p>{selected.review_notes || t.none}</p>
                  {selected.protected ? <p className="crm-matches-live__warn">{t.protected}</p> : null}
                  <p>{selected.merge_message}</p>
                  {canWrite && selected.status !== 'same_person' && selected.status !== 'different' ? (
                    <TextArea label={t.notes} value={note} rows={3} onChange={(event) => setNote(event.target.value)} />
                  ) : null}
                </>
              ) : (
                <LoadingState />
              )}
            </div>
            {selected && canWrite ? (
              <div className="crm-tasks__drawer-actions">
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => openContact(selected.person_a_id)}
                >
                  {t.person1}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="secondary"
                  onClick={() => openContact(selected.person_b_id)}
                >
                  {t.person2}
                </Button>
                {selected.status === 'pending' || selected.status === 'in_review' ? (
                  <>
                    <Button
                      type="button"
                      size="sm"
                      disabled={decisionMutation.isPending}
                      onClick={() => decisionMutation.mutate({ id: selected.id, action: 'same_person' })}
                    >
                      {t.same}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={decisionMutation.isPending}
                      onClick={() => decisionMutation.mutate({ id: selected.id, action: 'different' })}
                    >
                      {t.different}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={decisionMutation.isPending}
                      onClick={() => decisionMutation.mutate({ id: selected.id, action: 'in_review' })}
                    >
                      {t.hold}
                    </Button>
                  </>
                ) : null}
              </div>
            ) : null}
          </aside>
        </>
      ) : null}
    </div>
  );
}
