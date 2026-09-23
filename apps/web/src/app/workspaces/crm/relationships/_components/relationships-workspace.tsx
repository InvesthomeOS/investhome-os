'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import type { CrmRelationshipSummary, RelationshipListParams } from '@/workspaces/crm/api/relationships';
import { relationshipQueries } from '@/workspaces/crm/hooks/use-relationships';

import '../../agreements/_components/agreements-workspace.css';
import '../../contacts/_components/people-workspace.css';
import '../../contacts/_components/ds/contacts-ds.css';
import './relationships-workspace.css';

import { RelationshipNetworkView } from './relationship-network-view';

const PAGE_SIZE = 50;

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
  contact_company: 'Kişi ↔ Şirket',
  investor: 'Kişi ↔ Proje / Yatırım',
  colleague: 'Kişi ↔ Kişi',
  partner: 'Ortaklık / Co-owner',
  company_project: 'Şirket ↔ Proje',
  parent: 'Şirket hiyerarşisi',
  subsidiary: 'Şirket hiyerarşisi',
};

const CATEGORY_LABELS: Record<string, string> = {
  organizational: 'Organizasyonel',
  commercial: 'Ticari',
  personal: 'Kişisel',
  referral: 'Referans',
  investment: 'Yatırım',
  operational: 'Operasyonel',
  other: 'Diğer',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Aktif',
  inactive: 'Pasif',
  pending: 'Beklemede',
  archived: 'Arşiv',
};

const COPY = {
  tr: {
    title: 'İlişkiler',
    subtitle: 'CRM’deki gerçek ilişkiler — skor veya güç üretilmez',
    search: 'Kişi, şirket veya proje ara',
    type: 'İlişki türü',
    category: 'Kategori',
    project: 'Proje',
    status: 'Durum',
    owner: 'Sorumlu',
    all: 'Tümü',
    allTypes: 'Tüm türler',
    allCategories: 'Tüm kategoriler',
    allProjects: 'Tüm projeler',
    allOwners: 'Tüm sorumlular',
    total: 'Toplam İlişki',
    contactCompany: 'Kişi ↔ Şirket',
    contactProject: 'Kişi ↔ Proje / Yatırım',
    contactContact: 'Kişi ↔ Kişi',
    companyProject: 'Şirket ↔ Proje',
    source: 'Kaynak',
    relationType: 'İlişki Türü',
    target: 'Hedef',
    linked: 'Bağlı Proje / Yatırım',
    lastActivity: 'Son Etkinlik',
    note: 'Not',
    empty: 'Bu görünümde ilişki yok.',
    loading: 'İlişkiler yükleniyor…',
    previous: 'Önceki',
    next: 'Sonraki',
    tools: 'Araçlar',
    create: 'Yeni İlişki',
    list: 'Liste',
    network: 'Ağ Grafiği',
    countLabel: '{count} ilişki',
  },
  en: {
    title: 'Relationships',
    subtitle: 'Real CRM relationships — no generated scores or strength',
    search: 'Search person, company or project',
    type: 'Relationship type',
    category: 'Category',
    project: 'Project',
    status: 'Status',
    owner: 'Owner',
    all: 'All',
    allTypes: 'All types',
    allCategories: 'All categories',
    allProjects: 'All projects',
    allOwners: 'All owners',
    total: 'Total relationships',
    contactCompany: 'Person ↔ Company',
    contactProject: 'Person ↔ Project / Investment',
    contactContact: 'Person ↔ Person',
    companyProject: 'Company ↔ Project',
    source: 'Source',
    relationType: 'Type',
    target: 'Target',
    linked: 'Linked project / purchase',
    lastActivity: 'Last activity',
    note: 'Note',
    empty: 'No relationships match this view.',
    loading: 'Loading relationships…',
    previous: 'Previous',
    next: 'Next',
    tools: 'Tools',
    create: 'New relationship',
    list: 'List',
    network: 'Network graph',
    countLabel: '{count} relationships',
  },
} as const;

type SummaryTab = 'all' | 'contact_company' | 'contact_project' | 'contact_contact' | 'company_project';
type WorkspaceView = 'list' | 'network';

const TABS: Array<{ id: SummaryTab; countKey: keyof ReturnType<typeof emptyCounts>; labelKey: keyof (typeof COPY)['tr'] }> = [
  { id: 'all', countKey: 'total', labelKey: 'total' },
  { id: 'contact_company', countKey: 'contact_company', labelKey: 'contactCompany' },
  { id: 'contact_project', countKey: 'contact_project', labelKey: 'contactProject' },
  { id: 'contact_contact', countKey: 'contact_contact', labelKey: 'contactContact' },
  { id: 'company_project', countKey: 'company_project', labelKey: 'companyProject' },
];

function emptyCounts() {
  return {
    total: 0,
    contact_company: 0,
    contact_project: 0,
    contact_contact: 0,
    company_project: 0,
    company_company: 0,
  };
}

function formatActivity(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  return new Date(value).toLocaleString(locale, { day: '2-digit', month: 'short', year: 'numeric' });
}

function typeLabel(row: CrmRelationshipSummary): string {
  return TYPE_LABELS[row.relationship_type] || TYPE_LABELS[row.pair_kind] || row.relationship_type;
}

export function RelationshipsWorkspace() {
  const locale = useLocale();
  const copy = COPY[locale.startsWith('tr') ? 'tr' : 'en'];
  const router = useRouter();
  const { openContact, openPurchase } = useContactCard();
  const { authLoading, canRead, canCreate } = useCrmAccess();
  const [view, setView] = useState<WorkspaceView>('list');
  const [tab, setTab] = useState<SummaryTab>('all');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [relationshipType, setRelationshipType] = useState('');
  const [category, setCategory] = useState('');
  const [projectGroup, setProjectGroup] = useState('');
  const [status, setStatus] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [page, setPage] = useState(1);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const params: RelationshipListParams = useMemo(() => {
    const next: RelationshipListParams = {
      search: search || undefined,
      relationship_type: relationshipType || undefined,
      category: category || undefined,
      project_group: projectGroup || undefined,
      status: status || undefined,
      owner_user_id: ownerId || undefined,
      pair_kind: tab === 'all' ? undefined : tab,
      sort_by: 'updated_at',
      sort_order: 'desc',
      page,
      page_size: PAGE_SIZE,
    };
    return next;
  }, [category, ownerId, page, projectGroup, relationshipType, search, status, tab]);

  const listQuery = useQuery({
    ...relationshipQueries.list(params),
    enabled: !authLoading && canRead && view === 'list',
  });
  const countsQuery = useQuery({
    ...relationshipQueries.counts(),
    enabled: !authLoading && canRead,
  });
  const ownersQuery = useQuery({
    queryKey: ['crm', 'users', 'relationship-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canRead,
  });

  const rows = listQuery.data?.items ?? [];
  const pages = Math.max(1, Math.ceil((listQuery.data?.total ?? 0) / PAGE_SIZE));
  const counts = countsQuery.data ?? emptyCounts();

  const selectTab = (next: SummaryTab) => {
    setTab(next);
    setPage(1);
    if (next !== 'all') setRelationshipType('');
  };

  const openEntity = (
    entityType: string,
    entityId: string,
    agreementId?: string | null,
    event?: MouseEvent,
  ) => {
    event?.stopPropagation();
    if (entityType === 'contact') {
      openContact(entityId);
      return;
    }
    if (entityType === 'company') {
      router.push(`/workspaces/crm/companies/${entityId}`);
      return;
    }
    if (agreementId) {
      openPurchase(agreementId);
      return;
    }
    if (entityType === 'project') {
      router.push(`/dashboard/projects/${entityId}`);
    }
  };

  return (
    <div className="ctc-ds crm-people-workspace" data-testid="crm-relationships-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <div className="crm-rel-header-actions">
          {canCreate ? (
            <Link href="/workspaces/crm/relationships/new" className="crm-rel-create" data-testid="crm-relationships-new">
              {copy.create}
            </Link>
          ) : null}
          <Link href="/workspaces/crm/relationships/tools" className="crm-people-tools" data-testid="crm-relationships-tools-link">
            {copy.tools}
          </Link>
        </div>
      </header>

      <div className="crm-people-sticky">
        <section className="crm-people-summary" aria-label={copy.title}>
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'is-active' : undefined}
              data-testid={`crm-relationships-chip-${item.id}`}
              onClick={() => selectTab(item.id)}
            >
              <span>{copy[item.labelKey]}</span>
              <strong data-testid={`crm-relationships-count-${item.id}`}>
                {countsQuery.data ? counts[item.countKey].toLocaleString(locale) : '—'}
              </strong>
            </button>
          ))}
        </section>

        <div className="crm-agreements-views" role="tablist" aria-label={copy.title}>
          <button
            type="button"
            className={view === 'list' ? 'is-active' : undefined}
            data-testid="crm-relationships-view-list"
            onClick={() => setView('list')}
          >
            {copy.list}
          </button>
          <button
            type="button"
            className={view === 'network' ? 'is-active' : undefined}
            data-testid="crm-relationships-view-network"
            onClick={() => setView('network')}
          >
            {copy.network}
          </button>
        </div>
      </div>

      <section className="ctc-ds__toolbar crm-people-filters" aria-label={copy.search}>
        <Input
          label={copy.search}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={copy.search}
          data-testid="crm-relationships-search"
        />
        <Select
          label={copy.type}
          value={relationshipType}
          onChange={(event) => {
            setRelationshipType(event.target.value);
            setPage(1);
          }}
          data-testid="crm-relationships-filter-type"
        >
          <option value="">{copy.allTypes}</option>
          {Object.entries(TYPE_LABELS)
            .filter(([value], index, list) => list.findIndex((item) => item[1] === TYPE_LABELS[value]) === index)
            .map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
        </Select>
        <Select
          label={copy.category}
          value={category}
          onChange={(event) => {
            setCategory(event.target.value);
            setPage(1);
          }}
          data-testid="crm-relationships-filter-category"
        >
          <option value="">{copy.allCategories}</option>
          {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          label={copy.project}
          value={projectGroup}
          onChange={(event) => {
            setProjectGroup(event.target.value);
            setPage(1);
          }}
          data-testid="crm-relationships-filter-project"
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
            setPage(1);
          }}
          data-testid="crm-relationships-filter-status"
        >
          <option value="">{copy.all}</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
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
          data-testid="crm-relationships-filter-owner"
        >
          <option value="">{copy.allOwners}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
      </section>

      {view === 'network' ? (
        <RelationshipNetworkView
          embedded
          search={searchDraft}
          relationshipType={relationshipType}
          projectGroup={projectGroup}
          pairKind={tab === 'all' ? '' : tab}
        />
      ) : (
        <>
          <p className="crm-agreements-count" data-testid="crm-relationships-filtered-count">
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
                      <th>{copy.source}</th>
                      <th>{copy.relationType}</th>
                      <th>{copy.target}</th>
                      <th>{copy.category}</th>
                      <th>{copy.linked}</th>
                      <th>{copy.owner}</th>
                      <th>{copy.lastActivity}</th>
                      <th>{copy.status}</th>
                      <th>{copy.note}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr
                        key={row.id}
                        className="ctc-ds__row"
                        data-testid={`crm-relationships-row-${row.id}`}
                        onClick={() => router.push(`/workspaces/crm/relationships/${row.id}`)}
                      >
                        <td>
                          <button
                            type="button"
                            className="crm-rel-link"
                            onClick={(event) => openEntity(row.source_entity_type, row.source_entity_id, row.linked_agreement_id, event)}
                          >
                            {row.source_display_name || row.source_entity_id.slice(0, 8)}
                          </button>
                        </td>
                        <td>{typeLabel(row)}</td>
                        <td>
                          <button
                            type="button"
                            className="crm-rel-link"
                            onClick={(event) => openEntity(row.target_entity_type, row.target_entity_id, row.linked_agreement_id, event)}
                          >
                            {row.target_display_name || row.target_entity_id.slice(0, 8)}
                          </button>
                        </td>
                        <td>{CATEGORY_LABELS[row.category] || row.category}</td>
                        <td>
                          {row.linked_agreement_id ? (
                            <button
                              type="button"
                              className="crm-rel-link"
                              onClick={(event) => {
                                event.stopPropagation();
                                openPurchase(row.linked_agreement_id as string);
                              }}
                            >
                              {row.linked_project_label || row.linked_agreement_label}
                            </button>
                          ) : row.linked_project_id ? (
                            <button
                              type="button"
                              className="crm-rel-link"
                              onClick={(event) => openEntity('project', row.linked_project_id as string, null, event)}
                            >
                              {row.linked_project_label}
                            </button>
                          ) : (
                            '—'
                          )}
                        </td>
                        <td>{row.owner_name || '—'}</td>
                        <td>{formatActivity(row.last_interaction_at, locale)}</td>
                        <td>
                          <StatusChip tone={row.status === 'active' ? 'success' : 'default'}>
                            {STATUS_LABELS[row.status] || row.status}
                          </StatusChip>
                        </td>
                        <td>
                          <span className="crm-rel-note" title={row.notes || undefined}>
                            {row.notes || '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
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
        </>
      )}
    </div>
  );
}
