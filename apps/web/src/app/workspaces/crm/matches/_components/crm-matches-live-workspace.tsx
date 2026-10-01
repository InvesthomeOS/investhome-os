'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  decideCrmMatch,
  fetchCrmMatch,
  fetchCrmMatches,
  type CrmMatchAction,
  type CrmMatchDetail,
  type CrmMatchItem,
  type CrmMatchPerson,
  type CrmMatchPurchase,
  type CrmMatchStatus,
} from '@/workspaces/crm/api/crm-matches';

const PAGE_SIZES = [10, 25, 50] as const;
const REASONS = ['phone', 'email', 'secondary_email', 'bitrix', 'name_review'] as const;
const STATUSES: CrmMatchStatus[] = ['pending', 'in_review', 'same_person', 'different'];

const PROJECT_LABELS: Record<string, string> = {
  '1307_k_st': '1307 K St',
  '1313_penn': '1313 Penn',
  '1812_h_pl': '1812 H Pl',
  '2319_ontario': '2319 Ontario',
  reit: 'REIT',
  the_temple: 'The Temple',
  uniloft: 'Uniloft',
};

const COPY = {
  tr: {
    title: 'Eşleşmeler',
    subtitle: 'Olası müşteri / ilişkili kimlik incelemesi. Canlı CRM verisi, otomatik birleştirme yok.',
    kpis: 'Eşleşme özeti',
    pending: 'İnceleme Bekleyen',
    strong: 'Güçlü Eşleşme',
    possible: 'Olası Eşleşme',
    rejected: 'Reddedilen',
    search: 'Ara',
    searchPh: 'Ad, telefon, e-posta ara...',
    matchType: 'Eşleşme Türü',
    status: 'Durum',
    source: 'Kaynak',
    any: 'Tümü',
    clear: 'Filtreleri Temizle',
    empty: 'Eşleşme bulunamadı',
    person1: 'Kişi 1',
    person2: 'Kişi 2',
    reason: 'Eşleşme Nedeni',
    sharedPhone: 'Ortak Telefon',
    sharedEmail: 'Ortak E-posta',
    action: 'İşlem',
    open: 'Aç',
    close: 'Kapat',
    more: 'Diğer',
    goPerson1: 'Kişi 1’e Git',
    goPerson2: 'Kişi 2’ye Git',
    approve: 'Onayla',
    reject: 'Reddet',
    hold: 'İncelemede Tut',
    notes: 'İnceleme notu',
    evidence: 'Eşleşme kanıtı',
    conflicts: 'Çelişen alanlar',
    purchases: 'Satın Almalar',
    sourceIds: 'Kaynak ID',
    reviewNotes: 'Mevcut inceleme notları',
    protected: 'Korumalı kayıt',
    none: '—',
    filters: 'Eşleşme filtreleri',
    table: 'Eşleşme listesi',
    phone: 'Telefon',
    email: 'E-posta',
    name: 'Ad Soyad',
    historical: 'geçmiş birim',
    mergeBlocked: 'Kayıtlar birleştirilmedi.',
    nameReviewHint: 'Benzer ad yalnızca inceleme ipucudur; birleştirme kanıtı değildir.',
    countLabel: '{count} eşleşme',
    totalFooter: 'Toplam {count} eşleşme',
    pageSize: 'Sayfa başına',
    previous: 'Önceki',
    next: 'Sonraki',
    waiting: 'Bekliyor',
    approved: 'Onaylandı',
    declined: 'Reddedildi',
    inReview: 'İncelemede',
    compare: 'Kayıt karşılaştırması',
    review: 'İnceleme',
  },
  en: {
    title: 'Matches',
    subtitle: 'Possible customer / related identity review. Live CRM data, no automatic merge.',
    kpis: 'Match summary',
    pending: 'Awaiting review',
    strong: 'Strong match',
    possible: 'Possible match',
    rejected: 'Rejected',
    search: 'Search',
    searchPh: 'Search name, phone, email...',
    matchType: 'Match type',
    status: 'Status',
    source: 'Source',
    any: 'All',
    clear: 'Clear filters',
    empty: 'No matches found',
    person1: 'Person 1',
    person2: 'Person 2',
    reason: 'Match reason',
    sharedPhone: 'Shared phone',
    sharedEmail: 'Shared email',
    action: 'Action',
    open: 'Open',
    close: 'Close',
    more: 'More',
    goPerson1: 'Go to person 1',
    goPerson2: 'Go to person 2',
    approve: 'Approve',
    reject: 'Reject',
    hold: 'Keep in review',
    notes: 'Review note',
    evidence: 'Match evidence',
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
    name: 'Full name',
    historical: 'historical unit',
    mergeBlocked: 'Records were not merged.',
    nameReviewHint: 'Similar name is a review clue only, never merge evidence.',
    countLabel: '{count} matches',
    totalFooter: 'Total {count} matches',
    pageSize: 'Per page',
    previous: 'Previous',
    next: 'Next',
    waiting: 'Pending',
    approved: 'Approved',
    declined: 'Rejected',
    inReview: 'In review',
    compare: 'Record comparison',
    review: 'Review',
  },
} as const;

const REASON_LABEL: Record<string, { tr: string; en: string }> = {
  phone: { tr: 'Aynı telefon', en: 'Same phone' },
  email: { tr: 'Aynı e-posta', en: 'Same email' },
  secondary_email: { tr: 'Aynı ikincil e-posta', en: 'Same secondary email' },
  bitrix: { tr: 'Aynı Bitrix kimliği', en: 'Same Bitrix identity' },
  name_review: { tr: 'Aynı ad + iletişim bilgisi', en: 'Same name + contact info' },
};

const SOURCE_LABEL: Record<string, { tr: string; en: string }> = {
  bitrix: { tr: 'Bitrix', en: 'Bitrix' },
  web: { tr: 'Web Sitesi', en: 'Website' },
  website: { tr: 'Web Sitesi', en: 'Website' },
  manual: { tr: 'Manuel', en: 'Manual' },
  instagram: { tr: 'Instagram', en: 'Instagram' },
  facebook: { tr: 'Facebook', en: 'Facebook' },
  whatsapp: { tr: 'WhatsApp', en: 'WhatsApp' },
};

type KpiId = 'pending' | 'strong' | 'possible' | 'rejected';

const KPIS: Array<{
  id: KpiId;
  countKey: 'pending' | 'strong' | 'possible' | 'rejected';
  labelKey: 'pending' | 'strong' | 'possible' | 'rejected';
  icon: IhIconName;
  tone: string;
}> = [
  { id: 'pending', countKey: 'pending', labelKey: 'pending', icon: 'documents', tone: 'is-sky' },
  { id: 'strong', countKey: 'strong', labelKey: 'strong', icon: 'users', tone: 'is-mint' },
  { id: 'possible', countKey: 'possible', labelKey: 'possible', icon: 'user', tone: 'is-purple' },
  { id: 'rejected', countKey: 'rejected', labelKey: 'rejected', icon: 'alert', tone: 'is-warn' },
];

function reasonLabel(value: string, locale: 'tr' | 'en'): string {
  return REASON_LABEL[value]?.[locale] ?? value.replaceAll('_', ' ');
}

function reasonsLabel(reasons: string[], locale: 'tr' | 'en'): string {
  const labels = reasons.map((item) => reasonLabel(item, locale)).filter(Boolean);
  return [...new Set(labels)].join(', ') || '—';
}

function statusLabel(value: CrmMatchStatus, copy: (typeof COPY)['tr']): string {
  if (value === 'pending') return copy.waiting;
  if (value === 'in_review') return copy.inReview;
  if (value === 'same_person') return copy.approved;
  if (value === 'different') return copy.declined;
  return copy.none;
}

function statusTone(value: CrmMatchStatus): string {
  if (value === 'pending' || value === 'in_review') return 'pending';
  if (value === 'same_person') return 'approved';
  if (value === 'different') return 'rejected';
  return 'other';
}

function sourceLabel(value: string | null | undefined, locale: 'tr' | 'en', none: string): string {
  const raw = String(value || '').trim();
  if (!raw) return none;
  const key = raw.toLowerCase();
  return SOURCE_LABEL[key]?.[locale] ?? raw.replaceAll('_', ' ');
}

function parsePersonLabel(name: string): { sourceId: string; display: string } {
  const trimmed = name.trim();
  const match = trimmed.match(/^(#?\d+)\s+(.+)$/);
  if (!match) return { sourceId: '', display: trimmed };
  const id = match[1].startsWith('#') ? match[1] : `#${match[1]}`;
  return { sourceId: id, display: match[2] };
}

function initials(name: string): string {
  const display = parsePersonLabel(name).display;
  const parts = display.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  const first = parts[0][0] || '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] || '' : '';
  return `${first}${last}`.toLocaleUpperCase('tr-TR');
}

function purchaseLine(row: CrmMatchPurchase, historical: string): string {
  const project = PROJECT_LABELS[row.project || ''] || row.project;
  const bits = [project, row.unit].filter(Boolean);
  if (row.historical) bits.push(historical);
  return bits.join(' · ') || '—';
}

function formatSourceIds(ids: string[], none: string): string {
  if (!ids.length) return none;
  const cleaned = ids.map((id) => {
    const digits = id.match(/(\d+)\s*$/);
    if (digits && (id.includes(':') || /^\d+$/.test(id))) return `#${digits[1]}`;
    return id;
  });
  return [...new Set(cleaned)].join(', ');
}

function equalText(left?: string | null, right?: string | null): boolean {
  const a = String(left || '').trim().toLowerCase();
  const b = String(right || '').trim().toLowerCase();
  return Boolean(a && b && a === b);
}

function PersonCell({
  name,
  sourceId,
  tone,
  onOpen,
}: {
  name: string;
  sourceId?: string;
  tone: 'is-person-a' | 'is-person-b';
  onOpen: () => void;
}) {
  const parsed = parsePersonLabel(name);
  const shownId = sourceId || parsed.sourceId;
  return (
    <div className="crm-ops-company">
      <span className={`crm-ops-logo ${tone}`} aria-hidden>
        {initials(parsed.display)}
      </span>
      <div>
        <button
          type="button"
          className="crm-ops-link"
          onClick={(event) => {
            event.stopPropagation();
            onOpen();
          }}
        >
          {parsed.display}
        </button>
        {shownId ? <div className="crm-ops-morecount">{shownId}</div> : null}
      </div>
    </div>
  );
}

function FieldRow({
  label,
  value,
  same,
  diff,
}: {
  label: string;
  value: string;
  same?: boolean;
  diff?: boolean;
}) {
  return (
    <div className={`crm-ops-compare-row${same ? ' is-same' : ''}${diff ? ' is-diff' : ''}`}>
      <dt>{label}</dt>
      <dd>{value}</dd>
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
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZES)[number]>(25);
  const [selectedId, setSelectedId] = useState<string | null>(initialId ?? null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [note, setNote] = useState('');
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      match_type: matchType || undefined,
      status: status || undefined,
      source: source || undefined,
    }),
    [search, matchType, source, status],
  );

  const listQuery = useQuery({
    queryKey: ['crm-matches', filters],
    queryFn: () => fetchCrmMatches(filters),
    enabled: canRead && !authLoading,
    placeholderData: keepPreviousData,
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
  const total = data?.total ?? items.length;
  const pages = Math.max(1, Math.ceil(items.length / pageSize));
  const currentPage = Math.min(page, pages);
  const pageItems = items.slice((currentPage - 1) * pageSize, currentPage * pageSize);
  const selected = detailQuery.data ?? null;
  const kpiActive: KpiId | null =
    matchType === 'strong' && status === 'pending'
      ? 'strong'
      : matchType === 'possible' && status === 'pending'
        ? 'possible'
        : !matchType && status === 'pending'
          ? 'pending'
          : !matchType && status === 'different'
            ? 'rejected'
            : null;

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setMatchType('');
    setStatus('');
    setSource('');
    setPage(1);
  };

  const selectKpi = (id: KpiId) => {
    setPage(1);
    if (id === 'strong' || id === 'possible') {
      setMatchType(matchType === id && status === 'pending' ? '' : id);
      setStatus('pending');
      return;
    }
    setMatchType('');
    setStatus(status === id ? '' : id);
  };

  const openRow = (item: CrmMatchItem) => {
    setMenuId(null);
    setSelectedId(item.id);
    setNote('');
  };

  const openPerson = (id: string) => {
    setMenuId(null);
    openContact(id);
  };

  if (authLoading || (listQuery.isLoading && !listQuery.data)) {
    return <LoadingState />;
  }
  if (!canRead) {
    return <ErrorState title={t.title} message="No access" />;
  }
  if (listQuery.isError) {
    return <ErrorState title={t.title} message={t.empty} />;
  }

  return (
    <div className="crm-ops crm-ops--matches" data-testid="crm-matches-workspace">
      {toast ? (
        <div className="crm-ops-toast" role="status">
          {toast}
        </div>
      ) : null}

      <header className="crm-ops__header">
        <div className="crm-ops__title">
          <span className="crm-ops__title-icon" aria-hidden>
            <IhIcon name="users" size={18} />
          </span>
          <div>
            <h1>{t.title}</h1>
            <p>{t.subtitle}</p>
          </div>
        </div>
      </header>

      <section className="crm-ops-kpis" aria-label={t.kpis}>
        {KPIS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${item.tone}${kpiActive === item.id ? ' is-active' : ''}`}
            data-testid={`crm-matches-kpi-${item.id}`}
            onClick={() => selectKpi(item.id)}
          >
            <span className="crm-ops-kpis__icon" aria-hidden>
              <IhIcon name={item.icon} size={16} />
            </span>
            <strong>{kpis[item.countKey].toLocaleString(locale)}</strong>
            <span>{t[item.labelKey]}</span>
          </button>
        ))}
      </section>

      <section className="crm-ops-filtercard" aria-label={t.filters}>
        <Input
          label={t.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={t.searchPh}
          data-testid="crm-matches-search"
        />
        <Select
          label={t.matchType}
          value={matchType}
          onChange={(event) => {
            setMatchType(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t.any}</option>
          <option value="strong">{t.strong}</option>
          <option value="possible">{t.possible}</option>
          {REASONS.map((item) => (
            <option key={item} value={item}>
              {reasonLabel(item, locale)}
            </option>
          ))}
        </Select>
        <Select
          label={t.status}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t.any}</option>
          {STATUSES.map((item) => (
            <option key={item} value={item}>
              {statusLabel(item, t)}
            </option>
          ))}
        </Select>
        <Select
          label={t.source}
          value={source}
          onChange={(event) => {
            setSource(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t.any}</option>
          {(data?.sources ?? []).map((item) => (
            <option key={item} value={item}>
              {sourceLabel(item, locale, item)}
            </option>
          ))}
        </Select>
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t.clear}
          </Button>
        </div>
      </section>

      <section className="crm-ops-tablecard" aria-label={t.table}>
        <div className="crm-ops-tablecard__head">
          <strong data-testid="crm-matches-filtered-count">
            {t.countLabel.replace('{count}', String(total.toLocaleString(locale)))}
          </strong>
        </div>
        {items.length === 0 ? (
          <div className="crm-ops-empty" data-testid="crm-matches-empty">
            <strong>{t.empty}</strong>
          </div>
        ) : (
          <div className="crm-ops-table-wrap">
            <table className="crm-ops-table" data-testid="crm-matches-table">
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
                {pageItems.map((item) => (
                  <tr
                    key={item.id}
                    className="crm-ops-row"
                    data-testid={`crm-match-row-${item.id}`}
                    onClick={() => openRow(item)}
                  >
                    <td>
                      <PersonCell
                        name={item.person_a_name}
                        tone="is-person-a"
                        onOpen={() => {
                          openPerson(item.person_a_id);
                        }}
                      />
                      {item.protected ? <div className="crm-ops-flag">{t.protected}</div> : null}
                    </td>
                    <td>
                      <PersonCell
                        name={item.person_b_name}
                        tone="is-person-b"
                        onOpen={() => {
                          openPerson(item.person_b_id);
                        }}
                      />
                    </td>
                    <td>{reasonsLabel(item.reasons, locale)}</td>
                    <td>{item.shared_phone || t.none}</td>
                    <td>{item.shared_email || t.none}</td>
                    <td>{sourceLabel(item.source, locale, t.none)}</td>
                    <td>
                      <span className={`crm-ops-badge is-${statusTone(item.status)}`}>
                        {statusLabel(item.status, t)}
                      </span>
                    </td>
                    <td>
                      <div className="crm-ops-actions">
                        <button
                          type="button"
                          className="crm-ops-action"
                          onClick={(event) => {
                            event.stopPropagation();
                            openRow(item);
                          }}
                        >
                          {t.open}
                        </button>
                        <div className="crm-ops-more">
                          <button
                            type="button"
                            className="crm-ops-action"
                            aria-label={t.more}
                            onClick={(event) => {
                              event.stopPropagation();
                              setMenuId((current) => (current === item.id ? null : item.id));
                            }}
                          >
                            ⋯
                          </button>
                          {menuId === item.id ? (
                            <div className="crm-ops-more__panel">
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  openPerson(item.person_a_id);
                                }}
                              >
                                {t.goPerson1}
                              </button>
                              <button
                                type="button"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  openPerson(item.person_b_id);
                                }}
                              >
                                {t.goPerson2}
                              </button>
                              {canWrite && (item.status === 'pending' || item.status === 'in_review') ? (
                                <>
                                  <button
                                    type="button"
                                    disabled={decisionMutation.isPending}
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setMenuId(null);
                                      decisionMutation.mutate({ id: item.id, action: 'same_person' });
                                    }}
                                  >
                                    {t.approve}
                                  </button>
                                  <button
                                    type="button"
                                    disabled={decisionMutation.isPending}
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setMenuId(null);
                                      decisionMutation.mutate({ id: item.id, action: 'different' });
                                    }}
                                  >
                                    {t.reject}
                                  </button>
                                </>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="crm-ops-pager">
          <span>{t.totalFooter.replace('{count}', String(total.toLocaleString(locale)))}</span>
          <div>
            <span>{t.pageSize}</span>
            {PAGE_SIZES.map((size) => (
              <button
                key={size}
                type="button"
                className={pageSize === size ? 'is-active' : undefined}
                onClick={() => {
                  setPageSize(size);
                  setPage(1);
                }}
              >
                {size}
              </button>
            ))}
            <Button variant="secondary" size="sm" disabled={currentPage <= 1} onClick={() => setPage((value) => value - 1)}>
              {t.previous}
            </Button>
            {Array.from({ length: pages }, (_, index) => index + 1).map((number) => (
              <button
                key={number}
                type="button"
                className={currentPage === number ? 'is-active' : undefined}
                onClick={() => setPage(number)}
              >
                {number}
              </button>
            ))}
            <Button variant="secondary" size="sm" disabled={currentPage >= pages} onClick={() => setPage((value) => value + 1)}>
              {t.next}
            </Button>
          </div>
        </div>
      </section>

      {selectedId ? (
        <>
          <button type="button" className="crm-ops-drawer-backdrop" aria-label={t.close} onClick={() => setSelectedId(null)} />
          <aside className="crm-ops-drawer" role="dialog" data-testid="crm-matches-drawer">
            <div className="crm-ops-drawer__head">
              <div>
                <h2>{t.review}</h2>
                <p>
                  {selected ? `${selected.person_a_name} · ${selected.person_b_name}` : t.compare}
                </p>
              </div>
              <Button type="button" variant="secondary" size="sm" onClick={() => setSelectedId(null)}>
                {t.close}
              </Button>
            </div>
            <div className="crm-ops-drawer__body">
              {selected ? (
                <MatchCompare
                  selected={selected}
                  t={t}
                  locale={locale}
                  note={note}
                  onNoteChange={setNote}
                  canWrite={canWrite}
                />
              ) : (
                <LoadingState />
              )}
            </div>
            {selected && canWrite ? (
              <div className="crm-ops-drawer__actions">
                <Button type="button" size="sm" variant="secondary" onClick={() => openPerson(selected.person_a_id)}>
                  {t.goPerson1}
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => openPerson(selected.person_b_id)}>
                  {t.goPerson2}
                </Button>
                {selected.status === 'pending' || selected.status === 'in_review' ? (
                  <>
                    <Button
                      type="button"
                      size="sm"
                      disabled={decisionMutation.isPending}
                      onClick={() => decisionMutation.mutate({ id: selected.id, action: 'same_person' })}
                    >
                      {t.approve}
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={decisionMutation.isPending}
                      onClick={() => decisionMutation.mutate({ id: selected.id, action: 'different' })}
                    >
                      {t.reject}
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
            ) : selected ? (
              <div className="crm-ops-drawer__actions">
                <Button type="button" size="sm" variant="secondary" onClick={() => openPerson(selected.person_a_id)}>
                  {t.goPerson1}
                </Button>
                <Button type="button" size="sm" variant="secondary" onClick={() => openPerson(selected.person_b_id)}>
                  {t.goPerson2}
                </Button>
              </div>
            ) : null}
          </aside>
        </>
      ) : null}
    </div>
  );
}

function MatchCompare({
  selected,
  t,
  locale,
  note,
  onNoteChange,
  canWrite,
}: {
  selected: CrmMatchDetail;
  t: (typeof COPY)['tr'];
  locale: 'tr' | 'en';
  note: string;
  onNoteChange: (value: string) => void;
  canWrite: boolean;
}) {
  const left = selected.person_a;
  const right = selected.person_b;
  const nameSame = equalText(left.name, right.name);
  const phoneSame = equalText(left.phone, right.phone);
  const emailSame = equalText(left.email, right.email);
  const sourceSame = equalText(left.source, right.source);
  const showNotes = canWrite && (selected.status === 'pending' || selected.status === 'in_review');

  return (
    <>
      {selected.protected ? <p className="crm-ops-warn">{t.protected}</p> : null}
      {selected.merge_message ? <p className="crm-ops-warn">{selected.merge_message}</p> : null}
      <div className="crm-ops-compare" aria-label={t.compare}>
        <PersonPane
          title={t.person1}
          person={left}
          t={t}
          locale={locale}
          tone="is-person-a"
          same={{ name: nameSame, phone: phoneSame, email: emailSame, source: sourceSame }}
        />
        <PersonPane
          title={t.person2}
          person={right}
          t={t}
          locale={locale}
          tone="is-person-b"
          same={{ name: nameSame, phone: phoneSame, email: emailSame, source: sourceSame }}
        />
      </div>
      <section className="crm-ops-section">
        <h2>{t.evidence}</h2>
        <ul className="crm-ops-list">
          {selected.evidence.length === 0 ? <li>{t.none}</li> : null}
          {selected.evidence.map((item) => (
            <li key={`${item.reason}-${item.value}`}>
              <strong>{reasonLabel(item.reason, locale)}</strong>
              <span>{item.value || t.none}</span>
            </li>
          ))}
        </ul>
        {selected.reasons.includes('name_review') ? <p className="crm-ops-muted">{t.nameReviewHint}</p> : null}
      </section>
      <section className="crm-ops-section">
        <h2>{t.conflicts}</h2>
        <p className="crm-ops-muted">
          {selected.conflicts.length
            ? selected.conflicts
                .map((item) => (item === 'name' ? t.name : item === 'phone' ? t.phone : item === 'email' ? t.email : item === 'source' ? t.source : item))
                .join(', ')
            : t.none}
        </p>
      </section>
      {selected.review_notes ? (
        <section className="crm-ops-section">
          <h2>{t.reviewNotes}</h2>
          <p className="crm-ops-note">{selected.review_notes}</p>
        </section>
      ) : null}
      {showNotes ? (
        <TextArea label={t.notes} value={note} rows={3} onChange={(event) => onNoteChange(event.target.value)} />
      ) : null}
    </>
  );
}

function PersonPane({
  title,
  person,
  t,
  locale,
  tone,
  same,
}: {
  title: string;
  person: CrmMatchPerson;
  t: (typeof COPY)['tr'];
  locale: 'tr' | 'en';
  tone: 'is-person-a' | 'is-person-b';
  same: { name: boolean; phone: boolean; email: boolean; source: boolean };
}) {
  const parsed = parsePersonLabel(person.name);
  const sourceId = person.source_ids[0] ? `#${person.source_ids[0]}` : parsed.sourceId;
  return (
    <div className="crm-ops-pane">
      <h3>{title}</h3>
      <div className="crm-ops-company">
        <span className={`crm-ops-logo ${tone}`} aria-hidden>
          {initials(parsed.display)}
        </span>
        <div>
          <strong>{parsed.display}</strong>
          {sourceId ? <div className="crm-ops-morecount">{sourceId}</div> : null}
          {person.review_required ? <span className="crm-ops-flag">{t.protected}</span> : null}
        </div>
      </div>
      <FieldRow label={t.name} value={parsed.display || t.none} same={same.name} diff={!same.name} />
      <FieldRow label={t.phone} value={person.phone || t.none} same={same.phone} diff={!same.phone && Boolean(person.phone)} />
      <FieldRow label={t.email} value={person.email || t.none} same={same.email} diff={!same.email && Boolean(person.email)} />
      <FieldRow label={t.source} value={sourceLabel(person.source, locale, t.none)} same={same.source} />
      <FieldRow label={t.sourceIds} value={formatSourceIds(person.source_ids, t.none)} />
      <FieldRow
        label={t.purchases}
        value={person.purchases.length ? person.purchases.map((row) => purchaseLine(row, t.historical)).join('; ') : t.none}
      />
    </div>
  );
}
