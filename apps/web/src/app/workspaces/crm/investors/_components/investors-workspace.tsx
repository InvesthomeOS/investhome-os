'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import {
  fetchInvestorCounts,
  type ContactListParams,
} from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactSummary } from '@/workspaces/crm/types';

import '../../agreements/_components/agreements-workspace.css';
import '../../contacts/_components/people-workspace.css';
import '../../contacts/_components/ds/contacts-ds.css';

const PAGE_SIZE = 25;

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

const COPY = {
  tr: {
    title: 'Yatırımcılar',
    subtitle: 'Satın alma kaydı olan kanonik kişiler — katılımcılar ayrı tutulur',
    search: 'Ad, telefon veya e-posta ara',
    project: 'Proje',
    status: 'Durum',
    owner: 'Sorumlu',
    investments: 'Yatırım',
    all: 'Tümü',
    active: 'Aktif',
    archived: 'Arşiv',
    hasInvestments: 'Yatırımı var',
    noInvestments: 'Yatırımı yok',
    allOwners: 'Tüm sorumlular',
    allProjects: 'Tüm projeler',
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
    loading: 'Yatırımcılar yükleniyor…',
    previous: 'Önceki',
    next: 'Sonraki',
    tools: 'Araçlar',
    countLabel: '{count} yatırımcı',
  },
  en: {
    title: 'Investors',
    subtitle: 'Canonical people with purchase records — participants stay on the purchase',
    search: 'Search name, phone or email',
    project: 'Project',
    status: 'Status',
    owner: 'Owner',
    investments: 'Investments',
    all: 'All',
    active: 'Active',
    archived: 'Archived',
    hasInvestments: 'Has investments',
    noInvestments: 'No investments',
    allOwners: 'All owners',
    allProjects: 'All projects',
    total: 'Total investors',
    purchases: 'Total investments / purchases',
    missing: 'Missing info',
    review: 'Review required',
    investor: 'Investor',
    projects: 'Projects',
    purchaseCount: 'Investments / purchases',
    amount: 'Verified total',
    lastActivity: 'Last activity',
    warning: 'Warning',
    empty: 'No investors match this view.',
    loading: 'Loading investors…',
    previous: 'Previous',
    next: 'Next',
    tools: 'Tools',
    countLabel: '{count} investors',
  },
} as const;

type InvestorTab = 'all' | 'active' | 'purchases' | 'missing' | 'review';

function emptyCounts() {
  return { total: 0, active: 0, purchases: 0, missing_info: 0, review_required: 0 };
}

const TABS: Array<{ id: InvestorTab; countKey: keyof ReturnType<typeof emptyCounts>; labelKey: keyof (typeof COPY)['tr'] }> = [
  { id: 'all', countKey: 'total', labelKey: 'total' },
  { id: 'active', countKey: 'active', labelKey: 'active' },
  { id: 'purchases', countKey: 'purchases', labelKey: 'purchases' },
  { id: 'missing', countKey: 'missing_info', labelKey: 'missing' },
  { id: 'review', countKey: 'review_required', labelKey: 'review' },
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
  return new Date(value).toLocaleString(locale, { day: '2-digit', month: 'short', year: 'numeric' });
}

function projectLabel(projects: string[] | undefined): string {
  if (!projects?.length) return '—';
  return projects.map((item) => PROJECT_LABELS[item] || item).join(', ');
}

function amountLabel(contact: CrmContactSummary): string {
  const totals = contact.verified_amount_totals ?? [];
  if (!totals.length) return '—';
  return totals.map((item) => item.label).join(' · ');
}

export function InvestorsWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
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
      page_size: PAGE_SIZE,
    };
    if (hasInvestments === 'yes') next.has_investments = true;
    if (hasInvestments === 'no') next.has_investments = false;
    if (tab === 'active' || status === 'active') next.status = 'active';
    if (status === 'archived' || (tab !== 'active' && status === 'archived')) next.status = 'archived';
    if (tab === 'missing') next.flag = 'bilgi_eksik';
    if (tab === 'review') next.flag = 'inceleme_gerekli';
    return next;
  }, [hasInvestments, ownerId, page, project, search, status, tab]);

  const listQuery = useQuery({
    ...contactQueries.list(params),
    enabled: !authLoading && canRead,
  });
  const countsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'investor-counts'],
    queryFn: fetchInvestorCounts,
    enabled: !authLoading && canRead,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'investor-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canRead,
  });

  const rows = listQuery.data?.items ?? [];
  const pages = Math.max(1, listQuery.data?.pages ?? 1);
  const counts = countsQuery.data ?? emptyCounts();

  const selectTab = (next: InvestorTab) => {
    if (next === 'purchases') return;
    setTab(next);
    setPage(1);
    if (next === 'active') setStatus('active');
    if (next === 'all') setStatus('');
  };

  return (
    <div className="ctc-ds crm-people-workspace" data-testid="crm-investors-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <Link href="/workspaces/crm/investors/tools" className="crm-people-tools" data-testid="crm-investors-tools-link">
          {copy.tools}
        </Link>
      </header>

      <div className="crm-people-sticky">
        <section className="crm-people-summary" aria-label={copy.title}>
          {TABS.map((item) => {
            const value = counts[item.countKey];
            const isCountOnly = item.id === 'purchases';
            const Tag = isCountOnly ? 'div' : 'button';
            return (
              <Tag
                key={item.id}
                type={isCountOnly ? undefined : 'button'}
                className={!isCountOnly && tab === item.id ? 'is-active' : undefined}
                data-testid={`crm-investors-chip-${item.id}`}
                onClick={isCountOnly ? undefined : () => selectTab(item.id)}
              >
                <span>{copy[item.labelKey]}</span>
                <strong data-testid={`crm-investors-count-${item.id}`}>
                  {countsQuery.data ? value.toLocaleString(locale) : '—'}
                </strong>
              </Tag>
            );
          })}
        </section>
      </div>

      <section className="ctc-ds__toolbar crm-people-filters" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.search}
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
              {user.full_name}
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
          <option value="yes">{copy.hasInvestments}</option>
          <option value="no">{copy.noInvestments}</option>
        </Select>
      </section>

      <p className="crm-agreements-count" data-testid="crm-investors-filtered-count">
        {copy.countLabel.replace('{count}', String((listQuery.data?.total ?? 0).toLocaleString(locale)))}
      </p>

      <section className="ctc-ds__table-section crm-people-table" aria-label={copy.title}>
        {listQuery.isLoading ? <div className="ctc-ds__skeleton">{copy.loading}</div> : null}
        {listQuery.isError ? <div className="ctc-ds__empty">{listQuery.error.message}</div> : null}
        {!listQuery.isLoading && !listQuery.isError && rows.length === 0 ? (
          <div className="ctc-ds__empty">{copy.empty}</div>
        ) : null}
        {rows.length ? (
          <div className="ctc-ds__table-wrap">
            <table className="ctc-ds__table">
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
                </tr>
              </thead>
              <tbody>
                {rows.map((contact) => {
                  const flags = warningFlags(contact);
                  return (
                    <tr
                      key={contact.id}
                      className="ctc-ds__row"
                      data-testid={`investor-row-${contact.id}`}
                      onClick={() => openContact(contact.id)}
                    >
                      <td>
                        <strong>{contact.display_name}</strong>
                      </td>
                      <td>{projectLabel(contact.agreement_projects)}</td>
                      <td>{contact.agreement_count || '—'}</td>
                      <td>{amountLabel(contact)}</td>
                      <td>{contact.owner_name ?? contact.bitrix_responsible ?? '—'}</td>
                      <td>{formatActivity(contact.last_contact_at, locale)}</td>
                      <td>
                        <StatusChip tone={contact.status === 'active' ? 'success' : 'default'}>
                          {contact.status === 'active' ? copy.active : copy.archived}
                        </StatusChip>
                      </td>
                      <td>
                        <span className="crm-people-flags">
                          {flags.map((flag) => (
                            <span key={flag} className={`crm-people-flag is-${flag.toLowerCase()}`}>
                              {flag}
                            </span>
                          ))}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {listQuery.data?.total ? (
        <div className="ctc-ds__pagination">
          <span>
            {page} / {pages}
          </span>
          <div>
            <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
              {copy.previous}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={page >= pages}
              onClick={() => setPage((value) => value + 1)}
            >
              {copy.next}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
