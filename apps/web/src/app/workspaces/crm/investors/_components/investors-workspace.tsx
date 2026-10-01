'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchInvestorCounts, type ContactListParams } from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactSummary } from '@/workspaces/crm/types';

const PAGE_SIZES = [10, 25, 50] as const;

const AGREEMENT_PROJECTS = [
  { value: '1307_k_st', label: '1307 K St' },
  { value: '1313_penn', label: '1313 Penn' },
  { value: '1812_h_pl', label: '1812 H Pl' },
  { value: '2319_ontario', label: '2319 Ontario' },
  { value: 'reit', label: 'REIT' },
  { value: 'the_temple', label: 'The Temple' },
  { value: 'uniloft', label: 'Uniloft' },
] as const;

const PROJECT_LABELS: Record<string, string> = Object.fromEntries(
  AGREEMENT_PROJECTS.map((item) => [item.value, item.label]),
);

const FLAG_LABELS: Record<string, { tr: string; en: string }> = {
  BILGI_EKSIK: { tr: 'Bilgi Eksik', en: 'Missing info' },
  INCELEME_GEREKLI: { tr: 'İnceleme Gerekli', en: 'Needs review' },
};

const COPY = {
  tr: {
    title: 'Yatırımcılar',
    subtitle: 'Satın alma kaydı olan kanonik kişiler — yatırımcılar ayrı tutulur.',
    search: 'Ad, telefon veya e-posta ara',
    searchPh: 'Ad, telefon veya e-posta ara...',
    project: 'Proje',
    status: 'Durum',
    owner: 'Sorumlu',
    investments: 'Yatırım',
    all: 'Tümü',
    active: 'Aktif',
    inactive: 'Pasif',
    archived: 'Arşiv',
    prospect: 'Aday',
    hasInvestments: 'Yatırımı Var',
    noInvestments: 'Yatırımı Yok',
    allOwners: 'Tüm sorumlular',
    allProjects: 'Tüm projeler',
    clear: 'Filtreleri Temizle',
    total: 'Toplam Yatırımcı',
    purchases: 'Toplam Yatırım / Satın Alma Kaydı',
    missing: 'Bilgi Eksik',
    review: 'İnceleme Gerekli',
    investor: 'Yatırımcı',
    projects: 'Projeler',
    purchaseCount: 'Yatırım / Satın Alma Sayısı',
    amount: 'Doğrulanmış Toplam Tutar',
    lastActivity: 'Son Etkinlik',
    warning: 'Uyarı',
    empty: 'Bu görünümde yatırımcı yok.',
    previous: 'Önceki',
    next: 'Sonraki',
    tools: 'Araçlar',
    countLabel: '{count} yatırımcı',
    totalFooter: 'Toplam {count} yatırımcı',
    actions: 'İşlem',
    open: 'Aç',
    more: 'Diğer',
    goPerson: 'Kişiye Git',
    none: '—',
    kpis: 'Yatırımcı özeti',
    table: 'Yatırımcı listesi',
    pageSize: 'Sayfa başına',
  },
  en: {
    title: 'Investors',
    subtitle: 'Canonical people with purchase records — investors are kept separate.',
    search: 'Search name, phone or email',
    searchPh: 'Search name, phone or email...',
    project: 'Project',
    status: 'Status',
    owner: 'Owner',
    investments: 'Investments',
    all: 'All',
    active: 'Active',
    inactive: 'Inactive',
    archived: 'Archived',
    prospect: 'Prospect',
    hasInvestments: 'Has investments',
    noInvestments: 'No investments',
    allOwners: 'All owners',
    allProjects: 'All projects',
    clear: 'Clear filters',
    total: 'Total investors',
    purchases: 'Total investments / purchases',
    missing: 'Missing info',
    review: 'Needs review',
    investor: 'Investor',
    projects: 'Projects',
    purchaseCount: 'Investments / purchases',
    amount: 'Verified total',
    lastActivity: 'Last activity',
    warning: 'Warning',
    empty: 'No investors match this view.',
    previous: 'Previous',
    next: 'Next',
    tools: 'Tools',
    countLabel: '{count} investors',
    totalFooter: 'Total {count} investors',
    actions: 'Action',
    open: 'Open',
    more: 'More',
    goPerson: 'Go to person',
    none: '—',
    kpis: 'Investor summary',
    table: 'Investor list',
    pageSize: 'Per page',
  },
} as const;

type InvestorTab = 'all' | 'active' | 'purchases' | 'missing' | 'review';

function emptyCounts() {
  return { total: 0, active: 0, purchases: 0, missing_info: 0, review_required: 0 };
}

const TABS: Array<{
  id: InvestorTab;
  countKey: keyof ReturnType<typeof emptyCounts>;
  labelKey: keyof (typeof COPY)['tr'];
  icon: IhIconName;
  tone: string;
  filter: boolean;
}> = [
  { id: 'all', countKey: 'total', labelKey: 'total', icon: 'users', tone: '', filter: true },
  { id: 'active', countKey: 'active', labelKey: 'active', icon: 'check', tone: 'is-mint', filter: true },
  { id: 'purchases', countKey: 'purchases', labelKey: 'purchases', icon: 'trendingUp', tone: 'is-gold', filter: false },
  { id: 'missing', countKey: 'missing_info', labelKey: 'missing', icon: 'documents', tone: 'is-purple', filter: true },
  { id: 'review', countKey: 'review_required', labelKey: 'review', icon: 'alert', tone: 'is-warn', filter: true },
];

function warningFlags(contact: CrmContactSummary): string[] {
  const notes = contact.notes || '';
  const flags: string[] = [];
  if (/BILGI_EKSIK/i.test(notes)) flags.push('BILGI_EKSIK');
  if (/INCELEME_GEREKLI/i.test(notes) || contact.review_required) flags.push('INCELEME_GEREKLI');
  return flags;
}

function formatActivity(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(locale, { day: '2-digit', month: 'short', year: 'numeric' });
}

function uniqueProjects(projects: string[] | undefined): string[] {
  const labels: string[] = [];
  for (const item of projects ?? []) {
    const label = PROJECT_LABELS[item] || item;
    if (label && !labels.includes(label)) labels.push(label);
  }
  return labels;
}

function amountLabel(contact: CrmContactSummary): string {
  const totals = contact.verified_amount_totals ?? [];
  if (!totals.length) return '—';
  return totals.map((item) => item.label).join(' · ');
}

function displayOwner(name: string | null | undefined): string {
  return String(name || '')
    .replace(/\s*\((?:Demo|demo)\)\s*$/g, '')
    .trim();
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  const first = parts[0][0] || '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] || '' : '';
  return `${first}${last}`.toLocaleUpperCase('tr-TR');
}

function statusLabel(status: string | null | undefined, copy: (typeof COPY)['tr']): string {
  if (status === 'active') return copy.active;
  if (status === 'inactive') return copy.inactive;
  if (status === 'archived') return copy.archived;
  if (status === 'prospect') return copy.prospect;
  return copy.none;
}

function statusTone(status: string | null | undefined): string {
  if (status === 'active') return 'active';
  if (status === 'inactive' || status === 'archived') return 'inactive';
  if (status === 'prospect') return 'prospect';
  return 'other';
}

function flagLabel(flag: string, locale: 'tr' | 'en'): string {
  return FLAG_LABELS[flag]?.[locale] ?? flag.replaceAll('_', ' ');
}

export function InvestorsWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const copy = COPY[locale];
  const { openContact } = useContactCard();
  const { authLoading, canRead } = useCrmAccess();
  const [tab, setTab] = useState<InvestorTab>('all');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [project, setProject] = useState('');
  const [status, setStatus] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [hasInvestments, setHasInvestments] = useState<'yes' | 'no' | ''>('yes');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZES)[number]>(25);
  const [menuId, setMenuId] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const params: ContactListParams = useMemo(() => {
    const next: ContactListParams = {
      search: search || undefined,
      category: 'investor',
      agreement_project: project || undefined,
      owner_user_id: ownerId || undefined,
      include_archived: tab !== 'active' && status !== 'active',
      sort_by: 'updated_at',
      sort_dir: 'desc',
      page,
      page_size: pageSize,
    };
    if (hasInvestments === 'yes') next.has_investments = true;
    if (hasInvestments === 'no') next.has_investments = false;
    if (tab === 'active' || status === 'active') next.status = 'active';
    if (status === 'inactive') next.status = 'inactive';
    if (status === 'archived' || (tab !== 'active' && status === 'archived')) next.status = 'archived';
    if (tab === 'missing') next.flag = 'bilgi_eksik';
    if (tab === 'review') next.flag = 'inceleme_gerekli';
    return next;
  }, [hasInvestments, ownerId, page, pageSize, project, search, status, tab]);

  const listQuery = useQuery({
    ...contactQueries.list(params),
    enabled: !authLoading && canRead,
    placeholderData: keepPreviousData,
  });
  const countsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'investor-counts'],
    queryFn: fetchInvestorCounts,
    enabled: !authLoading && canRead,
    placeholderData: keepPreviousData,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'investor-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canRead,
  });

  const rows = listQuery.data?.items ?? [];
  const pages = Math.max(1, listQuery.data?.pages ?? 1);
  const total = listQuery.data?.total ?? 0;
  const counts = countsQuery.data ?? emptyCounts();

  const selectTab = (next: InvestorTab) => {
    if (next === 'purchases') return;
    setTab(next);
    setPage(1);
    if (next === 'active') setStatus('active');
    if (next === 'all') setStatus('');
  };

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setProject('');
    setStatus('');
    setOwnerId('');
    setHasInvestments('yes');
    setTab('all');
    setPage(1);
  };

  const openPerson = (id: string) => {
    setMenuId(null);
    openContact(id);
  };

  if (authLoading || (listQuery.isLoading && !listQuery.data)) {
    return <LoadingState />;
  }
  if (!canRead) {
    return <ErrorState title={copy.title} message="No access" />;
  }
  if (listQuery.isError) {
    return <ErrorState title={copy.title} message={listQuery.error.message} />;
  }

  return (
    <div className="crm-ops crm-ops--investors" data-testid="crm-investors-workspace">
      <header className="crm-ops__header">
        <div className="crm-ops__title">
          <span className="crm-ops__title-icon" aria-hidden>
            <IhIcon name="investors" size={18} />
          </span>
          <div>
            <h1>{copy.title}</h1>
            <p>{copy.subtitle}</p>
          </div>
        </div>
        <div className="crm-ops__header-tools">
          <Link href="/workspaces/crm/investors/tools" className="ih-btn ih-btn--secondary" data-testid="crm-investors-tools-link">
            {copy.tools}
          </Link>
        </div>
      </header>

      <section className="crm-ops-kpis" aria-label={copy.kpis}>
        {TABS.map((item) => {
          const value = counts[item.countKey];
          const className = `${item.tone}${!item.filter ? '' : tab === item.id ? ' is-active' : ''}`;
          const inner = (
            <>
              <span className="crm-ops-kpis__icon" aria-hidden>
                <IhIcon name={item.icon} size={16} />
              </span>
              <strong data-testid={`crm-investors-count-${item.id}`}>{value.toLocaleString(locale)}</strong>
              <span>{copy[item.labelKey]}</span>
            </>
          );
          if (!item.filter) {
            return (
              <div key={item.id} className={`crm-ops-kpi ${className}`} data-testid={`crm-investors-chip-${item.id}`}>
                {inner}
              </div>
            );
          }
          return (
            <button
              key={item.id}
              type="button"
              className={className}
              data-testid={`crm-investors-chip-${item.id}`}
              onClick={() => selectTab(item.id)}
            >
              {inner}
            </button>
          );
        })}
      </section>

      <section className="crm-ops-filtercard" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.searchPh}
          data-testid="crm-investors-search"
        />
        <Select
          label={copy.project}
          value={project}
          onChange={(event) => {
            setProject(event.target.value);
            setPage(1);
          }}
          data-testid="crm-investors-filter-project"
        >
          <option value="">{copy.allProjects}</option>
          {AGREEMENT_PROJECTS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
        <Select
          label={copy.status}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setTab(event.target.value === 'active' ? 'active' : 'all');
            setPage(1);
          }}
          data-testid="crm-investors-filter-status"
        >
          <option value="">{copy.all}</option>
          <option value="active">{copy.active}</option>
          <option value="inactive">{copy.inactive}</option>
          <option value="archived">{copy.archived}</option>
        </Select>
        <Select
          label={copy.owner}
          value={ownerId}
          onChange={(event) => {
            setOwnerId(event.target.value);
            setPage(1);
          }}
          data-testid="crm-investors-filter-owner"
        >
          <option value="">{copy.allOwners}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {displayOwner(user.full_name) || user.full_name}
            </option>
          ))}
        </Select>
        <Select
          label={copy.investments}
          value={hasInvestments}
          onChange={(event) => {
            setHasInvestments(event.target.value as 'yes' | 'no' | '');
            setPage(1);
          }}
          data-testid="crm-investors-filter-investments"
        >
          <option value="">{copy.all}</option>
          <option value="yes">{copy.hasInvestments}</option>
          <option value="no">{copy.noInvestments}</option>
        </Select>
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {copy.clear}
          </Button>
        </div>
      </section>

      <section className="crm-ops-tablecard" aria-label={copy.table}>
        <div className="crm-ops-tablecard__head">
          <strong data-testid="crm-investors-filtered-count">
            {copy.countLabel.replace('{count}', String(total.toLocaleString(locale)))}
          </strong>
        </div>
        {rows.length === 0 ? (
          <div className="crm-ops-empty">{copy.empty}</div>
        ) : (
          <div className="crm-ops-table-wrap">
            <table className="crm-ops-table">
              <thead>
                <tr>
                  <th>{copy.investor}</th>
                  <th>{copy.projects}</th>
                  <th>{copy.purchaseCount}</th>
                  <th>{copy.amount}</th>
                  <th>{copy.owner}</th>
                  <th>{copy.lastActivity}</th>
                  <th>{copy.status}</th>
                  <th>{copy.warning}</th>
                  <th>{copy.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((contact) => {
                  const flags = warningFlags(contact);
                  const projects = uniqueProjects(contact.agreement_projects);
                  const shownProjects = projects.slice(0, 3);
                  const extraProjects = projects.length - shownProjects.length;
                  const owner = displayOwner(contact.owner_name ?? contact.bitrix_responsible);
                  const company = contact.company_name || contact.organization_name;
                  return (
                    <tr
                      key={contact.id}
                      className="crm-ops-row"
                      data-testid={`investor-row-${contact.id}`}
                      onClick={() => openPerson(contact.id)}
                    >
                      <td>
                        <div className="crm-ops-company">
                          <span className="crm-ops-logo is-investor" aria-hidden>
                            {initials(contact.display_name)}
                          </span>
                          <div>
                            <button
                              type="button"
                              className="crm-ops-link"
                              onClick={(event) => {
                                event.stopPropagation();
                                openPerson(contact.id);
                              }}
                            >
                              {contact.display_name}
                            </button>
                            {company ? <div className="crm-ops-morecount">{company}</div> : null}
                          </div>
                        </div>
                      </td>
                      <td title={projects.join(', ')}>
                        {shownProjects.length ? shownProjects.join(', ') : copy.none}
                        {extraProjects > 0 ? <span className="crm-ops-morecount"> +{extraProjects}</span> : null}
                      </td>
                      <td>{contact.agreement_count || copy.none}</td>
                      <td>{amountLabel(contact)}</td>
                      <td>
                        {owner ? (
                          <div className="crm-ops-owner">
                            <span className="crm-ops-avatar" aria-hidden>
                              {initials(owner)}
                            </span>
                            <span>{owner}</span>
                          </div>
                        ) : (
                          copy.none
                        )}
                      </td>
                      <td>{formatActivity(contact.last_contact_at, locale)}</td>
                      <td>
                        <span className={`crm-ops-badge is-${statusTone(contact.status)}`}>
                          {statusLabel(contact.status, copy)}
                        </span>
                      </td>
                      <td>
                        {flags.length ? (
                          <div className="crm-ops-flags">
                            {flags.map((flag) => (
                              <span
                                key={flag}
                                className={`crm-ops-badge ${flag === 'BILGI_EKSIK' ? 'is-missing' : 'is-review'}`}
                              >
                                {flagLabel(flag, locale)}
                              </span>
                            ))}
                          </div>
                        ) : (
                          copy.none
                        )}
                      </td>
                      <td>
                        <div className="crm-ops-actions">
                          <button
                            type="button"
                            className="crm-ops-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              openPerson(contact.id);
                            }}
                          >
                            {copy.open}
                          </button>
                          <div className="crm-ops-more">
                            <button
                              type="button"
                              className="crm-ops-action"
                              aria-label={copy.more}
                              onClick={(event) => {
                                event.stopPropagation();
                                setMenuId((current) => (current === contact.id ? null : contact.id));
                              }}
                            >
                              ⋯
                            </button>
                            {menuId === contact.id ? (
                              <div className="crm-ops-more__panel">
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    openPerson(contact.id);
                                  }}
                                >
                                  {copy.goPerson}
                                </button>
                              </div>
                            ) : null}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="crm-ops-pager">
          <span>{copy.totalFooter.replace('{count}', String(total.toLocaleString(locale)))}</span>
          <div>
            <span>{copy.pageSize}</span>
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
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
              {copy.previous}
            </Button>
            <button type="button" className="is-active" disabled>
              {page}
            </button>
            <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => setPage((value) => value + 1)}>
              {copy.next}
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}
