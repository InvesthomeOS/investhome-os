'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmCompaniesQueries } from '@/lib/query/crm-companies-queries';
import type { FetchCrmCompaniesParams } from '@/workspaces/crm/api/companies';
import type { CrmCompanyListItem } from '@/workspaces/crm/types';

import '../../agreements/_components/agreements-workspace.css';
import '../../contacts/_components/people-workspace.css';
import './companies-workspace.css';

const PAGE_SIZE = 25;

const TYPE_LABELS: Record<string, string> = {
  investment_company: 'Yatırımcı',
  buyer_entity: 'Alıcı şirketi',
  brokerage: 'Broker / Acenta',
  law_firm: 'Hukuk',
  bank: 'Banka',
  lender: 'Finansör',
  property_management: 'Yönetim',
  construction: 'İnşaat',
  contractor: 'Yüklenici',
  architecture: 'Mimarlık',
  accounting: 'Muhasebe',
  consulting: 'Danışmanlık',
  insurance: 'Sigorta',
  media: 'Medya',
  government: 'Kamu',
  vendor: 'Tedarikçi',
  partner: 'Partner',
  internal_entity: 'İç şirket',
  other: 'Diğer',
};

const RELATION_LABELS: Record<string, string> = {
  unknown: '—',
  cold: 'Soğuk',
  warm: 'Ilık',
  hot: 'Sıcak',
  active: 'Aktif',
  at_risk: 'Riskli',
  lost: 'Kayıp',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Aktif',
  inactive: 'Pasif',
  prospect: 'Aday',
  archived: 'Arşiv',
};

const COPY = {
  tr: {
    title: 'Şirketler',
    subtitle: 'Operasyonel şirket listesi — doğrulanmış CRM kayıtları',
    search: 'Şirket, kişi, telefon veya e-posta ara',
    category: 'Kategori',
    status: 'Durum',
    country: 'Ülke',
    relation: 'İlişki Türü',
    owner: 'Sorumlu',
    all: 'Tümü',
    allOwners: 'Tüm sorumlular',
    allCountries: 'Tüm ülkeler',
    allRelations: 'Tüm ilişkiler',
    total: 'Toplam Şirket',
    brokerage: 'Broker / Acenta Şirketleri',
    partner: 'Partner Şirketler',
    investor: 'Yatırımcı Şirketleri',
    open: 'Açık İlişkiler / İş Birlikleri',
    company: 'Şirket',
    people: 'İlgili Kişiler',
    openWork: 'Açık Proje / İş',
    lastActivity: 'Son Etkinlik',
    warning: 'Uyarı',
    empty: 'Bu görünümde şirket yok.',
    loading: 'Şirketler yükleniyor…',
    previous: 'Önceki',
    next: 'Sonraki',
    tools: 'Araçlar',
    countLabel: '{count} şirket',
    location: 'Ülke / Şehir',
  },
  en: {
    title: 'Companies',
    subtitle: 'Operational company list — verified CRM records',
    search: 'Search company, person, phone or email',
    category: 'Category',
    status: 'Status',
    country: 'Country',
    relation: 'Relationship type',
    owner: 'Owner',
    all: 'All',
    allOwners: 'All owners',
    allCountries: 'All countries',
    allRelations: 'All relationships',
    total: 'Total companies',
    brokerage: 'Broker / agency companies',
    partner: 'Partner companies',
    investor: 'Investor companies',
    open: 'Open relationships',
    company: 'Company',
    people: 'Related people',
    openWork: 'Open work',
    lastActivity: 'Last activity',
    warning: 'Warning',
    empty: 'No companies match this view.',
    loading: 'Loading companies…',
    previous: 'Previous',
    next: 'Next',
    tools: 'Tools',
    countLabel: '{count} companies',
    location: 'Country / city',
  },
} as const;

type SummaryTab = 'all' | 'brokerage' | 'partner' | 'investor' | 'open';

const TABS: Array<{ id: SummaryTab; countKey: keyof ReturnType<typeof emptyCounts>; labelKey: keyof (typeof COPY)['tr'] }> = [
  { id: 'all', countKey: 'total', labelKey: 'total' },
  { id: 'brokerage', countKey: 'brokerage', labelKey: 'brokerage' },
  { id: 'partner', countKey: 'partner', labelKey: 'partner' },
  { id: 'investor', countKey: 'investor', labelKey: 'investor' },
  { id: 'open', countKey: 'open_relationships', labelKey: 'open' },
];

function emptyCounts() {
  return { total: 0, brokerage: 0, partner: 0, investor: 0, open_relationships: 0 };
}

function warningFlags(company: CrmCompanyListItem): string[] {
  const notes = company.notes || '';
  const flags: string[] = [];
  const incomplete =
    !company.primary_email && !company.primary_phone && !company.country && !company.city && !company.legal_name;
  if (/BILGI_EKSIK/i.test(notes) || incomplete) flags.push('BILGI_EKSIK');
  const ambiguous =
    /INCELEME_GEREKLI/i.test(notes) ||
    (!company.legal_name && (company.company_type === 'other' || /deterministic link/i.test(notes)));
  if (ambiguous) flags.push('INCELEME_GEREKLI');
  return flags;
}

function formatActivity(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  return new Date(value).toLocaleString(locale, { day: '2-digit', month: 'short', year: 'numeric' });
}

function locationLabel(company: CrmCompanyListItem): string {
  const parts = [company.country, company.city].filter(Boolean);
  return parts.length ? parts.join(' / ') : '—';
}

export function CompaniesWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const router = useRouter();
  const { authLoading, canReadCompanies } = useCrmAccess();
  const [tab, setTab] = useState<SummaryTab>('all');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [country, setCountry] = useState('');
  const [relation, setRelation] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const params: FetchCrmCompaniesParams = useMemo(() => {
    const next: FetchCrmCompaniesParams = {
      search: search || undefined,
      status: status || undefined,
      country: country || undefined,
      relationshipStatus: relation || undefined,
      ownerUserId: ownerId || undefined,
      page,
      pageSize: PAGE_SIZE,
      sortBy: 'updated_at',
      sortOrder: 'desc',
    };
    if (tab === 'brokerage') next.companyType = 'brokerage';
    else if (tab === 'partner') next.companyType = 'partner';
    else if (tab === 'investor') next.companyType = 'investment_company';
    else if (category) next.companyType = category;
    if (tab === 'open') next.openRelationships = true;
    return next;
  }, [category, country, ownerId, page, relation, search, status, tab]);

  const listQuery = useQuery({
    ...crmCompaniesQueries.list(params),
    enabled: !authLoading && canReadCompanies,
  });
  const countsQuery = useQuery({
    ...crmCompaniesQueries.counts(),
    enabled: !authLoading && canReadCompanies,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'company-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canReadCompanies,
  });

  const rows = listQuery.data?.items ?? [];
  const pages = Math.max(1, listQuery.data?.pages ?? 1);
  const counts = countsQuery.data ?? emptyCounts();
  const countries = useMemo(
    () => Array.from(new Set(rows.map((row) => row.country).filter((value): value is string => Boolean(value)))),
    [rows],
  );

  const selectTab = (next: SummaryTab) => {
    setTab(next);
    setPage(1);
    if (next !== 'all') setCategory('');
  };

  return (
    <div className="ctc-ds crm-companies-ops" data-testid="crm-companies-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <Link href="/workspaces/crm/companies/tools" className="crm-people-tools" data-testid="crm-companies-tools-link">
          {copy.tools}
        </Link>
      </header>

      <div className="crm-people-sticky">
        <section className="crm-people-summary" aria-label={copy.title}>
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'is-active' : undefined}
              data-testid={`crm-companies-chip-${item.id}`}
              onClick={() => selectTab(item.id)}
            >
              <span>{copy[item.labelKey]}</span>
              <strong data-testid={`crm-companies-count-${item.id}`}>
                {countsQuery.data ? counts[item.countKey].toLocaleString(locale) : '—'}
              </strong>
            </button>
          ))}
        </section>
      </div>

      <section className="ctc-ds__toolbar crm-people-filters" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.search}
          data-testid="crm-companies-search"
        />
        {tab === 'all' ? (
          <Select
            label={copy.category}
            value={category}
            onChange={(event) => {
              setCategory(event.target.value);
              setPage(1);
            }}
            data-testid="crm-companies-filter-category"
          >
            <option value="">{copy.all}</option>
            {Object.entries(TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        ) : null}
        <Select
          label={copy.status}
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          data-testid="crm-companies-filter-status"
        >
          <option value="">{copy.all}</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          label={copy.country}
          value={country}
          onChange={(event) => {
            setCountry(event.target.value);
            setPage(1);
          }}
          data-testid="crm-companies-filter-country"
        >
          <option value="">{copy.allCountries}</option>
          {countries.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </Select>
        <Select
          label={copy.relation}
          value={relation}
          onChange={(event) => {
            setRelation(event.target.value);
            setPage(1);
          }}
          data-testid="crm-companies-filter-relation"
        >
          <option value="">{copy.allRelations}</option>
          {Object.entries(RELATION_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          label={copy.owner}
          value={ownerId}
          onChange={(event) => {
            setOwnerId(event.target.value);
            setPage(1);
          }}
          data-testid="crm-companies-filter-owner"
        >
          <option value="">{copy.allOwners}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
      </section>

      <p className="crm-agreements-count" data-testid="crm-companies-filtered-count">
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
                  <th>{copy.company}</th>
                  <th>{copy.category}</th>
                  <th>{copy.location}</th>
                  <th>{copy.people}</th>
                  <th>{copy.relation}</th>
                  <th>{copy.openWork}</th>
                  <th>{copy.owner}</th>
                  <th>{copy.lastActivity}</th>
                  <th>{copy.status}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((company) => {
                  const flags = warningFlags(company);
                  const people = (company.related_people ?? []).map((person) => person.display_name).filter(Boolean);
                  const openWork = company.related_agreement_count || company.open_relationship_count || 0;
                  return (
                    <tr
                      key={company.id}
                      className="ctc-ds__row"
                      data-testid={`company-row-${company.id}`}
                      onClick={() => router.push(`/workspaces/crm/companies/${company.id}`)}
                    >
                      <td>
                        <strong>{company.display_name}</strong>
                        {flags.length ? (
                          <span className="crm-people-flags">
                            {flags.map((flag) => (
                              <span key={flag} className={`crm-people-flag is-${flag.toLowerCase()}`}>
                                {flag}
                              </span>
                            ))}
                          </span>
                        ) : null}
                      </td>
                      <td>{TYPE_LABELS[company.company_type] || company.company_type}</td>
                      <td>{locationLabel(company)}</td>
                      <td>{people.length ? people.join(', ') : '—'}</td>
                      <td>{RELATION_LABELS[company.relationship_status] || company.relationship_status || '—'}</td>
                      <td>{openWork || '—'}</td>
                      <td>{company.owner_name ?? '—'}</td>
                      <td>{formatActivity(company.last_activity_at, locale)}</td>
                      <td>
                        <StatusChip tone={company.status === 'active' ? 'success' : 'default'}>
                          {STATUS_LABELS[company.status] || company.status}
                        </StatusChip>
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
