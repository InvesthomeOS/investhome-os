'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchCrmTag } from '@/workspaces/crm/api/crm';
import {
  fetchJunkReasons,
  fetchPeopleCounts,
  type ContactListParams,
} from '@/workspaces/crm/api/contacts';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { contactQueries } from '@/workspaces/crm/hooks/use-contacts';
import type { CrmContactSummary } from '@/workspaces/crm/types';

import '../../agreements/_components/agreements-workspace.css';
import './ds/contacts-ds.css';
import './people-workspace.css';

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

const TYPE_LABELS: Record<string, string> = {
  investor: 'Yatırımcı',
  prospect: 'Potansiyel',
  buyer: 'Alıcı',
  broker: 'Broker',
  realtor: 'Realtor',
  partner: 'Partner',
  vendor: 'Tedarikçi',
  contractor: 'Yüklenici',
  attorney: 'Avukat',
  lender: 'Finansör',
  property_manager: 'Yönetici',
  architect: 'Mimar',
  consultant: 'Danışman',
  media_contact: 'Medya',
  government_contact: 'Kamu',
  internal_team: 'İç ekip',
};

const COPY = {
  tr: {
    title: 'Kişiler',
    subtitle: 'Operasyonel kişi listesi — aynı kanonik kayıt kümesi',
    search: 'Ad, telefon veya e-posta ara',
    category: 'Kategori / Tür',
    owner: 'Sorumlu',
    source: 'Kaynak',
    junkReason: 'Junk Sebebi',
    agreementProject: 'Anlaşma Projesi',
    all: 'Tümü',
    active: 'Aktif',
    junk: 'Junk',
    review: 'İnceleme Gerekli',
    missing: 'Bilgi Eksik',
    bitrix: 'Bitrix',
    otherSource: 'Diğer',
    customer: 'Müşteri',
    agent: 'Acenta',
    agreement: 'Anlaşmalı',
    allOwners: 'Tüm sorumlular',
    allReasons: 'Tüm sebepler',
    allProjects: 'Tüm projeler',
    name: 'Ad Soyad',
    phone: 'Telefon',
    email: 'E-posta',
    type: 'Kategori / Tür',
    status: 'Durum',
    lastActivity: 'Son Etkinlik',
    warning: 'Uyarı',
    empty: 'Bu görünümde kişi yok.',
    loading: 'Kişiler yükleniyor…',
    previous: 'Önceki',
    next: 'Sonraki',
    tools: 'Doğrulama araçları',
    countLabel: '{count} kişi',
  },
  en: {
    title: 'People',
    subtitle: 'Operational people list — one canonical dataset',
    search: 'Search name, phone or email',
    category: 'Category / Type',
    owner: 'Owner',
    source: 'Source',
    junkReason: 'Junk reason',
    agreementProject: 'Agreement project',
    all: 'All',
    active: 'Active',
    junk: 'Junk',
    review: 'Review required',
    missing: 'Missing info',
    bitrix: 'Bitrix',
    otherSource: 'Other',
    customer: 'Customer',
    agent: 'Agent',
    agreement: 'Agreement',
    allOwners: 'All owners',
    allReasons: 'All reasons',
    allProjects: 'All projects',
    name: 'Name',
    phone: 'Phone',
    email: 'Email',
    type: 'Category / Type',
    status: 'Status',
    lastActivity: 'Last activity',
    warning: 'Warning',
    empty: 'No people match this view.',
    loading: 'Loading people…',
    previous: 'Previous',
    next: 'Next',
    tools: 'Verification tools',
    countLabel: '{count} people',
  },
} as const;

type PeopleTab = 'all' | 'active' | 'junk' | 'review' | 'missing';
type CategoryFilter = '' | 'customer' | 'agent' | 'agreement';

const TABS: Array<{ id: PeopleTab; countKey: keyof ReturnType<typeof emptyCounts> }> = [
  { id: 'all', countKey: 'total' },
  { id: 'active', countKey: 'active' },
  { id: 'junk', countKey: 'junk' },
  { id: 'review', countKey: 'review_required' },
  { id: 'missing', countKey: 'missing_info' },
];

function emptyCounts() {
  return { total: 0, active: 0, junk: 0, review_required: 0, missing_info: 0 };
}

function typeLabel(contact: CrmContactSummary, copy: (typeof COPY)['tr']): string {
  const types = (contact.contact_types?.length ? contact.contact_types : [contact.contact_type]).filter(Boolean);
  const labels = types.map((item) => TYPE_LABELS[item] || item);
  if (contact.has_agreements && !labels.includes(copy.agreement)) labels.push(copy.agreement);
  if (!labels.length) return copy.customer;
  return labels.join(' · ');
}

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

export function PeopleWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const router = useRouter();
  const searchParams = useSearchParams();
  const tagId = searchParams.get('tag') || '';
  const { openContact } = useContactCard();
  const { authLoading, canRead } = useCrmAccess();
  const [tab, setTab] = useState<PeopleTab>('all');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<CategoryFilter>('');
  const [ownerId, setOwnerId] = useState('');
  const [source, setSource] = useState<'' | 'bitrix' | 'other'>('');
  const [agreementProject, setAgreementProject] = useState('');
  const [junkReason, setJunkReason] = useState('');
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
      category: category || undefined,
      owner_user_id: ownerId || undefined,
      source_group: source || undefined,
      agreement_project: agreementProject || undefined,
      junk_reason: tab === 'junk' ? junkReason || undefined : undefined,
      tag_id: tagId || undefined,
      include_archived: tab !== 'active',
      sort_by: 'updated_at',
      sort_dir: 'desc',
      page,
      page_size: PAGE_SIZE,
    };
    if (tab === 'active') next.status = 'active';
    if (tab === 'junk') next.status = 'archived';
    if (tab === 'review') next.flag = 'inceleme_gerekli';
    if (tab === 'missing') next.flag = 'bilgi_eksik';
    return next;
  }, [agreementProject, category, junkReason, ownerId, page, search, source, tab, tagId]);

  const contactsQuery = useQuery({
    ...contactQueries.list(params),
    enabled: !authLoading && canRead,
  });
  const countsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'people-counts'],
    queryFn: fetchPeopleCounts,
    enabled: !authLoading && canRead,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'people-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canRead,
  });
  const reasonsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'junk-reasons'],
    queryFn: fetchJunkReasons,
    enabled: !authLoading && canRead && tab === 'junk',
  });
  const tagQuery = useQuery({
    queryKey: ['crm', 'tags', 'detail', tagId],
    queryFn: () => fetchCrmTag(tagId),
    enabled: !authLoading && canRead && Boolean(tagId),
  });

  const rows = contactsQuery.data?.items ?? [];
  const pages = Math.max(1, contactsQuery.data?.pages ?? 1);
  const counts = countsQuery.data ?? emptyCounts();

  const selectTab = (next: PeopleTab) => {
    setTab(next);
    setPage(1);
    if (next !== 'junk') setJunkReason('');
  };

  return (
    <div className="ctc-ds crm-people-workspace" data-testid="crm-people-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <Link href="/workspaces/crm/contacts/tools" className="crm-people-tools" data-testid="crm-people-tools-link">
          {copy.tools}
        </Link>
      </header>

      <div className="crm-people-sticky">
      <section className="crm-people-summary" aria-label={copy.title}>
        {TABS.map((item) => {
          const label = copy[item.id];
          const value = counts[item.countKey];
          return (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'is-active' : undefined}
              data-testid={`crm-people-chip-${item.id}`}
              onClick={() => selectTab(item.id)}
            >
              <span>{label}</span>
              <strong
                data-testid={`crm-people-count-${item.id}`}
                data-count={countsQuery.data ? String(value) : ''}
              >
                {countsQuery.data ? value.toLocaleString(locale) : '—'}
              </strong>
            </button>
          );
        })}
      </section>

      <div className="crm-agreements-views crm-people-tabs" role="tablist" aria-label={copy.title}>
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={tab === item.id}
            className={tab === item.id ? 'is-active' : undefined}
            data-testid={`crm-people-tab-${item.id}`}
            onClick={() => selectTab(item.id)}
          >
            {copy[item.id]}
          </button>
        ))}
      </div>
      </div>

      <section className="ctc-ds__toolbar crm-people-filters" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.search}
          data-testid="crm-people-search"
        />
        <Select
          label={copy.category}
          value={category}
          onChange={(event) => {
            setCategory(event.target.value as CategoryFilter);
            setPage(1);
          }}
          data-testid="crm-people-filter-category"
        >
          <option value="">{copy.all}</option>
          <option value="customer">{copy.customer}</option>
          <option value="agent">{copy.agent}</option>
          <option value="agreement">{copy.agreement}</option>
        </Select>
        <Select
          label={copy.owner}
          value={ownerId}
          onChange={(event) => {
            setOwnerId(event.target.value);
            setPage(1);
          }}
          data-testid="crm-people-filter-owner"
        >
          <option value="">{copy.allOwners}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
        <Select
          label={copy.source}
          value={source}
          onChange={(event) => {
            setSource(event.target.value as typeof source);
            setPage(1);
          }}
          data-testid="crm-people-filter-source"
        >
          <option value="">{copy.all}</option>
          <option value="bitrix">{copy.bitrix}</option>
          <option value="other">{copy.otherSource}</option>
        </Select>
        <Select
          label={copy.agreementProject}
          value={agreementProject}
          onChange={(event) => {
            setAgreementProject(event.target.value);
            setPage(1);
          }}
          data-testid="crm-people-filter-project"
        >
          <option value="">{copy.allProjects}</option>
          {AGREEMENT_PROJECTS.map((project) => (
            <option key={project.value} value={project.value}>
              {project.label}
            </option>
          ))}
        </Select>
        {tab === 'junk' ? (
          <Select
            label={copy.junkReason}
            value={junkReason}
            onChange={(event) => {
              setJunkReason(event.target.value);
              setPage(1);
            }}
            data-testid="crm-people-filter-junk-reason"
          >
            <option value="">{copy.allReasons}</option>
            {(reasonsQuery.data?.items ?? []).map((item) => (
              <option key={item.reason} value={item.reason}>
                {item.reason} ({item.count})
              </option>
            ))}
          </Select>
        ) : null}
      </section>

      {tagId ? (
        <div className="crm-people-tag-filter" data-testid="crm-people-tag-filter">
          <span>Etiket: {tagQuery.data?.name || '…'}</span>
          <button
            type="button"
            onClick={() => {
              setPage(1);
              router.replace('/workspaces/crm/contacts');
            }}
          >
            Kaldır
          </button>
        </div>
      ) : null}

      <p className="crm-agreements-count" data-testid="crm-people-filtered-count">
        {copy.countLabel.replace('{count}', String((contactsQuery.data?.total ?? 0).toLocaleString(locale)))}
      </p>

      <section className="ctc-ds__table-section crm-people-table" aria-label={copy.title}>
        {contactsQuery.isLoading ? <div className="ctc-ds__skeleton">{copy.loading}</div> : null}
        {contactsQuery.isError ? <div className="ctc-ds__empty">{contactsQuery.error.message}</div> : null}
        {!contactsQuery.isLoading && !contactsQuery.isError && rows.length === 0 ? (
          <div className="ctc-ds__empty">{copy.empty}</div>
        ) : null}
        {rows.length ? (
          <div className="ctc-ds__table-wrap">
            <table className="ctc-ds__table">
              <thead>
                <tr>
                  <th>{copy.name}</th>
                  <th>{copy.phone}</th>
                  <th>{copy.email}</th>
                  <th>{copy.type}</th>
                  <th>{copy.status}</th>
                  <th>{copy.owner}</th>
                  <th>{copy.lastActivity}</th>
                  <th>{copy.warning}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((contact) => (
                  <tr
                    key={contact.id}
                    className="ctc-ds__row"
                    data-testid={`crm-people-row-${contact.id}`}
                    onClick={() => openContact(contact.id)}
                  >
                    <td>
                      <strong>{contact.display_name}</strong>
                    </td>
                    <td>{contact.primary_phone ?? '—'}</td>
                    <td>{contact.primary_email ?? '—'}</td>
                    <td>{typeLabel(contact, copy)}</td>
                    <td>
                      <StatusChip tone={contact.status === 'active' ? 'success' : 'default'}>
                        {contact.status === 'active' ? copy.active : copy.junk}
                      </StatusChip>
                    </td>
                    <td>{contact.owner_name ?? contact.bitrix_responsible ?? '—'}</td>
                    <td>{formatActivity(contact.last_contact_at, locale)}</td>
                    <td>
                      <span className="crm-people-flags">
                        {warningFlags(contact).map((flag) => (
                          <span key={flag} className={`crm-people-flag is-${flag.toLowerCase()}`}>
                            {flag}
                          </span>
                        ))}
                        {warningFlags(contact).length === 0 ? '—' : null}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {contactsQuery.data?.total ? (
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
