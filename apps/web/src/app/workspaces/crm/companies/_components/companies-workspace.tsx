'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers } from '@/lib/api/auth';
import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmCompaniesQueries } from '@/lib/query/crm-companies-queries';
import type { FetchCrmCompaniesParams } from '@/workspaces/crm/api/companies';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import type { CrmCompanyListItem } from '@/workspaces/crm/types';

const PAGE_SIZES = [10, 25, 50] as const;

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
  broker: 'Broker',
  realtor: 'Acenta',
  agent: 'Acenta',
  acenta: 'Acenta',
  partner: 'Partner',
  investor: 'Yatırımcı',
  collaboration: 'İş Birliği',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Aktif',
  inactive: 'Pasif',
  prospect: 'Aday',
  archived: 'Arşiv',
};

const FLAG_LABELS: Record<string, { tr: string; en: string }> = {
  BILGI_EKSIK: { tr: 'Bilgi Eksik', en: 'Missing info' },
  INCELEME_GEREKLI: { tr: 'İnceleme Gerekli', en: 'Needs review' },
};

const COPY = {
  tr: {
    title: 'Şirketler',
    subtitle: 'Operasyonel şirket listesi — doğrulanmış CRM kayıtları.',
    search: 'Şirket, kişi, telefon veya e-posta ara',
    searchPh: 'Şirket, kişi, telefon veya e-posta ara...',
    category: 'Kategori',
    status: 'Durum',
    country: 'Ülke',
    relation: 'İlişki Türü',
    owner: 'Sorumlu',
    all: 'Tümü',
    allOwners: 'Tüm sorumlular',
    allCountries: 'Tüm ülkeler',
    allRelations: 'Tüm ilişkiler',
    clear: 'Filtreleri Temizle',
    create: 'Yeni Şirket',
    total: 'Toplam Şirket',
    brokerage: 'Broker / Acenta Şirketleri',
    partner: 'Partner Şirketler',
    investor: 'Yatırımcı Şirketleri',
    openRelations: 'Açık İlişkiler / İş Birlikleri',
    company: 'Şirket',
    people: 'İlgili Kişiler',
    openWork: 'Açık Proje / İş',
    lastActivity: 'Son Etkinlik',
    empty: 'Bu görünümde şirket yok.',
    loading: 'Şirketler yükleniyor…',
    previous: 'Önceki',
    next: 'Sonraki',
    tools: 'Araçlar',
    countLabel: '{count} şirket',
    location: 'Ülke / Şehir',
    actions: 'İşlem',
    open: 'Aç',
    edit: 'Düzenle',
    more: 'Diğer',
    none: '—',
    kpis: 'Şirket özeti',
    table: 'Şirket listesi',
    pageSize: 'Sayfa başına',
    totalFooter: 'Toplam {count} şirket',
  },
  en: {
    title: 'Companies',
    subtitle: 'Operational company list — verified CRM records.',
    search: 'Search company, person, phone or email',
    searchPh: 'Search company, person, phone or email...',
    category: 'Category',
    status: 'Status',
    country: 'Country',
    relation: 'Relationship type',
    owner: 'Owner',
    all: 'All',
    allOwners: 'All owners',
    allCountries: 'All countries',
    allRelations: 'All relationships',
    clear: 'Clear filters',
    create: 'New company',
    total: 'Total companies',
    brokerage: 'Broker / agency companies',
    partner: 'Partner companies',
    investor: 'Investor companies',
    openRelations: 'Open relationships',
    company: 'Company',
    people: 'Related people',
    openWork: 'Open work',
    lastActivity: 'Last activity',
    empty: 'No companies match this view.',
    loading: 'Loading companies…',
    previous: 'Previous',
    next: 'Next',
    tools: 'Tools',
    countLabel: '{count} companies',
    location: 'Country / city',
    actions: 'Action',
    open: 'Open',
    edit: 'Edit',
    more: 'More',
    none: '—',
    kpis: 'Company summary',
    table: 'Company list',
    pageSize: 'Per page',
    totalFooter: 'Total {count} companies',
  },
} as const;

type SummaryTab = 'all' | 'brokerage' | 'partner' | 'investor' | 'open';

const TABS: Array<{
  id: SummaryTab;
  countKey: keyof ReturnType<typeof emptyCounts>;
  labelKey: keyof (typeof COPY)['tr'];
  icon: IhIconName;
  tone: string;
}> = [
  { id: 'all', countKey: 'total', labelKey: 'total', icon: 'crm', tone: '' },
  { id: 'brokerage', countKey: 'brokerage', labelKey: 'brokerage', icon: 'users', tone: 'is-mint' },
  { id: 'partner', countKey: 'partner', labelKey: 'partner', icon: 'meeting', tone: 'is-purple' },
  { id: 'investor', countKey: 'investor', labelKey: 'investor', icon: 'investors', tone: 'is-gold' },
  { id: 'open', countKey: 'open_relationships', labelKey: 'openRelations', icon: 'sparkles', tone: '' },
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
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(locale, { day: '2-digit', month: 'short', year: 'numeric' });
}

function locationLabel(company: CrmCompanyListItem): string {
  const parts = [company.country, company.city].filter(Boolean);
  return parts.length ? parts.join(' / ') : '—';
}

function categoryLabel(value: string | null | undefined): string {
  if (!value) return 'Diğer';
  return TYPE_LABELS[value] || 'Diğer';
}

function categoryTone(value: string | null | undefined): string {
  if (value === 'brokerage') return 'brokerage';
  if (value === 'partner') return 'partner';
  if (value === 'investment_company') return 'investor';
  return 'other';
}

function statusLabel(value: string | null | undefined): string {
  if (!value) return '—';
  return STATUS_LABELS[value] || value;
}

function statusTone(value: string | null | undefined): string {
  if (value === 'active') return 'active';
  if (value === 'inactive' || value === 'archived') return 'inactive';
  if (value === 'prospect') return 'prospect';
  return 'other';
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

function relationDisplay(company: CrmCompanyListItem): string {
  const fromPeople = Array.from(
    new Set(
      (company.related_people ?? [])
        .flatMap((person) => {
          const labels: string[] = [];
          if (person.contact_type) {
            const mapped = RELATION_LABELS[person.contact_type.toLowerCase()];
            if (mapped && mapped !== '—') labels.push(mapped);
          }
          if (person.is_broker && !labels.length) labels.push('Broker');
          return labels;
        })
        .filter(Boolean),
    ),
  );
  if (fromPeople.length) return fromPeople.join(', ');
  const status = (company.relationship_status || '').toLowerCase();
  if (!status || status === 'unknown') return '—';
  return RELATION_LABELS[status] || '—';
}

function openWorkLabel(company: CrmCompanyListItem): string {
  if (company.related_agreement_count && company.related_agreement_count > 0) {
    return String(company.related_agreement_count);
  }
  if (company.open_relationship_count && company.open_relationship_count > 0) {
    return String(company.open_relationship_count);
  }
  return '—';
}

function flagLabel(flag: string, locale: 'tr' | 'en'): string {
  return FLAG_LABELS[flag]?.[locale] ?? flag.replaceAll('_', ' ');
}

function companyHref(id: string): Route {
  return `/workspaces/crm/companies/${id}` as Route;
}

export function CompaniesWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const copy = COPY[locale];
  const router = useRouter();
  const { openContact } = useContactCard();
  const { authLoading, canReadCompanies, canCreate, user } = useCrmAccess();
  const canEdit = canUpdateCrm(user);
  const [tab, setTab] = useState<SummaryTab>('all');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [status, setStatus] = useState('');
  const [country, setCountry] = useState('');
  const [relation, setRelation] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<(typeof PAGE_SIZES)[number]>(10);
  const [menuId, setMenuId] = useState<string | null>(null);

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
      pageSize,
      sortBy: 'updated_at',
      sortOrder: 'desc',
    };
    if (tab === 'brokerage') next.companyType = 'brokerage';
    else if (tab === 'partner') next.companyType = 'partner';
    else if (tab === 'investor') next.companyType = 'investment_company';
    else if (category) next.companyType = category;
    if (tab === 'open') next.openRelationships = true;
    return next;
  }, [category, country, ownerId, page, pageSize, relation, search, status, tab]);

  const listQuery = useQuery({
    ...crmCompaniesQueries.list(params),
    enabled: !authLoading && canReadCompanies,
    placeholderData: keepPreviousData,
  });
  const countsQuery = useQuery({
    ...crmCompaniesQueries.counts(),
    enabled: !authLoading && canReadCompanies,
    placeholderData: keepPreviousData,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'company-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canReadCompanies,
  });

  const rows = listQuery.data?.items ?? [];
  const pages = Math.max(1, listQuery.data?.pages ?? 1);
  const total = listQuery.data?.total ?? 0;
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

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setCategory('');
    setStatus('');
    setCountry('');
    setRelation('');
    setOwnerId('');
    setPage(1);
  };

  const openCompany = (id: string) => {
    setMenuId(null);
    router.push(companyHref(id));
  };

  if (authLoading || (listQuery.isLoading && !listQuery.data)) {
    return <LoadingState />;
  }
  if (!canReadCompanies) {
    return <ErrorState title={copy.title} message="No access" />;
  }
  if (listQuery.isError) {
    return <ErrorState title={copy.title} message={listQuery.error.message} />;
  }

  return (
    <div className="crm-ops crm-ops--companies" data-testid="crm-companies-workspace">
      <header className="crm-ops__header">
        <div className="crm-ops__title">
          <span className="crm-ops__title-icon" aria-hidden>
            <IhIcon name="crm" size={18} />
          </span>
          <div>
            <h1>{copy.title}</h1>
            <p>{copy.subtitle}</p>
          </div>
        </div>
        <div className="crm-ops__header-tools">
          <Link href="/workspaces/crm/companies/tools" className="ih-btn ih-btn--secondary" data-testid="crm-companies-tools-link">
            {copy.tools}
          </Link>
          {canCreate ? (
            <Link href="/workspaces/crm/companies/new" className="ih-btn ih-btn--primary">
              {copy.create}
            </Link>
          ) : null}
        </div>
      </header>

      <section className="crm-ops-kpis" aria-label={copy.kpis}>
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${item.tone}${tab === item.id ? ' is-active' : ''}`}
            data-testid={`crm-companies-chip-${item.id}`}
            onClick={() => selectTab(item.id)}
          >
            <span className="crm-ops-kpis__icon" aria-hidden>
              <IhIcon name={item.icon} size={16} />
            </span>
            <strong data-testid={`crm-companies-count-${item.id}`}>{counts[item.countKey].toLocaleString(locale)}</strong>
            <span>{copy[item.labelKey]}</span>
          </button>
        ))}
      </section>

      <section className="crm-ops-filtercard" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.searchPh}
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
          {Object.entries(RELATION_LABELS)
            .filter(([value]) => !['broker', 'realtor', 'agent', 'acenta', 'partner', 'investor', 'collaboration'].includes(value))
            .map(([value, label]) => (
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
          {(ownersQuery.data?.items ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {displayOwner(item.full_name) || item.full_name}
            </option>
          ))}
        </Select>
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {copy.clear}
          </Button>
        </div>
      </section>

      <section className="crm-ops-tablecard" aria-label={copy.table}>
        <div className="crm-ops-tablecard__head">
          <strong data-testid="crm-companies-filtered-count">
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
                  <th>{copy.company}</th>
                  <th>{copy.category}</th>
                  <th>{copy.location}</th>
                  <th>{copy.people}</th>
                  <th>{copy.relation}</th>
                  <th>{copy.openWork}</th>
                  <th>{copy.owner}</th>
                  <th>{copy.lastActivity}</th>
                  <th>{copy.status}</th>
                  <th>{copy.actions}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((company) => {
                  const flags = warningFlags(company);
                  const people = (company.related_people ?? []).filter((person) => person.display_name);
                  const visiblePeople = people.slice(0, 2);
                  const extraPeople = people.length - visiblePeople.length;
                  const owner = displayOwner(company.owner_name);
                  return (
                    <tr
                      key={company.id}
                      className="crm-ops-row"
                      data-testid={`company-row-${company.id}`}
                      onClick={() => openCompany(company.id)}
                    >
                      <td>
                        <div className="crm-ops-company">
                          <span className={`crm-ops-logo is-${categoryTone(company.company_type)}`} aria-hidden>
                            {initials(company.display_name)}
                          </span>
                          <div>
                            <strong title={company.display_name}>{company.display_name}</strong>
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
                            ) : null}
                          </div>
                        </div>
                      </td>
                      <td>
                        <span className={`crm-ops-badge is-${categoryTone(company.company_type)}`}>
                          {categoryLabel(company.company_type)}
                        </span>
                      </td>
                      <td>{locationLabel(company)}</td>
                      <td>
                        {visiblePeople.length ? (
                          <div className="crm-ops-people">
                            {visiblePeople.map((person) => (
                              <button
                                key={person.id}
                                type="button"
                                className="crm-ops-link"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  openContact(person.id);
                                }}
                              >
                                {person.display_name}
                              </button>
                            ))}
                            {extraPeople > 0 ? (
                              <span className="crm-ops-morecount" title={people.slice(2).map((item) => item.display_name).join(', ')}>
                                +{extraPeople}
                              </span>
                            ) : null}
                          </div>
                        ) : (
                          copy.none
                        )}
                      </td>
                      <td>{relationDisplay(company)}</td>
                      <td>{openWorkLabel(company)}</td>
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
                      <td>{formatActivity(company.last_activity_at, locale)}</td>
                      <td>
                        <span className={`crm-ops-badge is-${statusTone(company.status)}`}>{statusLabel(company.status)}</span>
                      </td>
                      <td>
                        <div className="crm-ops-actions">
                          <button
                            type="button"
                            className="crm-ops-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              openCompany(company.id);
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
                                setMenuId((current) => (current === company.id ? null : company.id));
                              }}
                            >
                              ⋯
                            </button>
                            {menuId === company.id ? (
                              <div className="crm-ops-more__panel">
                                <Link href={companyHref(company.id)} onClick={(event) => event.stopPropagation()}>
                                  {copy.open}
                                </Link>
                                {canEdit ? (
                                  <Link href={companyHref(company.id)} onClick={(event) => event.stopPropagation()}>
                                    {copy.edit}
                                  </Link>
                                ) : null}
                                {people[0] ? (
                                  <button
                                    type="button"
                                    onClick={(event) => {
                                      event.stopPropagation();
                                      setMenuId(null);
                                      openContact(people[0].id);
                                    }}
                                  >
                                    {copy.people}
                                  </button>
                                ) : null}
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
