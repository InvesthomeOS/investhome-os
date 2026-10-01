'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select } from '@investhome/ui';

import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  fetchCrmLead,
  fetchCrmLeads,
  moveCrmLeadStage,
  type CrmLeadItem,
  type CrmLeadStage,
} from '@/workspaces/crm/api/crm-leads';

const STAGES: CrmLeadStage[] = ['yeni', 'contacted', 'following', 'qualified', 'converted', 'unqualified'];
const ACTIVE_STAGES: CrmLeadStage[] = ['yeni', 'contacted', 'following', 'qualified'];
const CLOSED_STAGES: CrmLeadStage[] = ['converted', 'unqualified'];

const STAGE_LABEL: Record<CrmLeadStage, { tr: string; en: string }> = {
  yeni: { tr: 'Yeni', en: 'New' },
  contacted: { tr: 'İletişime Geçildi', en: 'Contacted' },
  following: { tr: 'Takipte', en: 'Following' },
  qualified: { tr: 'Nitelikli', en: 'Qualified' },
  converted: { tr: 'Satışa Döndü', en: 'Converted' },
  unqualified: { tr: 'Uygun Değil', en: 'Unsuitable' },
};

const SOURCE_LABEL: Record<string, { tr: string; en: string }> = {
  manual: { tr: 'Manuel', en: 'Manual' },
  website: { tr: 'Website', en: 'Website' },
  meta: { tr: 'Meta / Facebook', en: 'Meta / Facebook' },
  facebook: { tr: 'Meta / Facebook', en: 'Meta / Facebook' },
  instagram: { tr: 'Instagram', en: 'Instagram' },
  google: { tr: 'Google Ads', en: 'Google Ads' },
  referral: { tr: 'Referans', en: 'Referral' },
  other: { tr: 'Diğer', en: 'Other' },
};

const COPY = {
  tr: {
    title: 'Pipeline',
    subtitle: 'Operasyonel satış pipeline. Canlı lead kayıtları, demo kart yok.',
    kpis: 'Pipeline özeti',
    total: 'Aktif pipeline',
    yeni: 'Yeni',
    following: 'Takipte',
    qualified: 'Nitelikli',
    search: 'Ara',
    searchPh: 'Ad, telefon, e-posta',
    source: 'Kaynak',
    project: 'Proje',
    owner: 'Sorumlu',
    date: 'Tarih',
    dateFrom: 'Başlangıç',
    dateTo: 'Bitiş',
    any: 'Tümü',
    clear: 'Filtreleri Temizle',
    emptyTitle: 'Aktif pipeline boş',
    emptyBody: 'Satışa dönen ve uygun olmayan leadler aktif kart olarak görünmez. Demo kayıt eklenmez.',
    phone: 'Telefon',
    email: 'E-posta',
    campaign: 'Kampanya',
    notes: 'Not',
    created: 'Oluşturma',
    lastActivity: 'Son aktivite',
    stageAge: 'Aşama yaşı',
    history: 'Son iletişim / aktivite',
    close: 'Kapat',
    openPerson: 'Kişiyi aç',
    identity: 'Kimlik',
    stage: 'Aşama',
    convertedHint: 'Satışa döndü yalnızca dönüşümle işaretlenir. Bu kayıt tarihsel olarak izlenebilir.',
    closedHint: 'Uygun değil kayıtları tarihsel olarak saklanır, aktif pipeline sayılmaz.',
    stageMoved: 'Aşama güncellendi',
    convertBlocked: 'Satışa dönüş yalnızca Leadler dönüşümü ile yapılır.',
    none: '—',
    filters: 'Pipeline filtreleri',
    today: 'bugün',
    days: 'g',
  },
  en: {
    title: 'Pipeline',
    subtitle: 'Operational sales pipeline. Live lead records, no demo cards.',
    kpis: 'Pipeline summary',
    total: 'Active pipeline',
    yeni: 'New',
    following: 'Following',
    qualified: 'Qualified',
    search: 'Search',
    searchPh: 'Name, phone, email',
    source: 'Source',
    project: 'Project',
    owner: 'Owner',
    date: 'Date',
    dateFrom: 'From',
    dateTo: 'To',
    any: 'All',
    clear: 'Clear filters',
    emptyTitle: 'Active pipeline is empty',
    emptyBody: 'Converted and unsuitable leads stay historical. Demo cards are not added.',
    phone: 'Phone',
    email: 'Email',
    campaign: 'Campaign',
    notes: 'Notes',
    created: 'Created',
    lastActivity: 'Last activity',
    stageAge: 'Stage age',
    history: 'Latest communication / activity',
    close: 'Close',
    openPerson: 'Open person',
    identity: 'Identity',
    stage: 'Stage',
    convertedHint: 'Converted only after person conversion. The record stays historically traceable.',
    closedHint: 'Unsuitable leads are preserved historically and are not counted as active pipeline.',
    stageMoved: 'Stage updated',
    convertBlocked: 'Conversion is done from Leads, not by dropping onto Converted.',
    none: '—',
    filters: 'Pipeline filters',
    today: 'today',
    days: 'd',
  },
};

function formatWhen(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function stageAge(value: string | null | undefined, locale: 'tr' | 'en', t: (typeof COPY)['tr']): string {
  if (!value) return t.none;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return t.none;
  const days = Math.max(0, Math.floor((Date.now() - date.getTime()) / 86_400_000));
  if (days === 0) return t.today;
  return `${days}${t.days}`;
}

function sourceLabel(value: string | null | undefined, locale: 'tr' | 'en'): string {
  if (!value) return '—';
  return SOURCE_LABEL[value.toLowerCase()]?.[locale] ?? value;
}

function stageLabel(stage: CrmLeadStage, locale: 'tr' | 'en'): string {
  return STAGE_LABEL[stage][locale];
}

function activityLabel(key: string, locale: 'tr' | 'en'): string {
  const map: Record<string, { tr: string; en: string }> = {
    'crm.leads.created': { tr: 'Lead oluşturuldu', en: 'Lead created' },
    'crm.leads.updated': { tr: 'Lead güncellendi', en: 'Lead updated' },
    'crm.leads.stage_changed': { tr: 'Aşama değişti', en: 'Stage changed' },
    'crm.leads.converted': { tr: 'Kişiye dönüştürüldü', en: 'Converted to person' },
  };
  return map[key]?.[locale] ?? key;
}

export function CrmPipelineLiveWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const t = COPY[locale];
  const { canRead, authLoading, user } = useCrmAccess();
  const canWrite = canUpdateCrm(user);
  const queryClient = useQueryClient();
  const { openContact } = useContactCard();

  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [stage, setStage] = useState('');
  const [source, setSource] = useState('');
  const [project, setProject] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      stage: stage || undefined,
      source: source || undefined,
      project: project || undefined,
      owner_id: ownerId || undefined,
      date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
    }),
    [search, stage, source, project, ownerId, dateFrom, dateTo],
  );

  const listQuery = useQuery({
    queryKey: ['crm-leads', 'pipeline', filters],
    queryFn: () => fetchCrmLeads(filters),
    enabled: canRead && !authLoading,
  });

  const detailQuery = useQuery({
    queryKey: ['crm-lead', selectedId],
    queryFn: () => fetchCrmLead(selectedId as string),
    enabled: Boolean(selectedId),
  });

  const showToast = (message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2400);
  };

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['crm-leads'] });
    if (selectedId) {
      await queryClient.invalidateQueries({ queryKey: ['crm-lead', selectedId] });
    }
  };

  const stageMutation = useMutation({
    mutationFn: ({ id, next }: { id: string; next: CrmLeadStage }) => moveCrmLeadStage(id, next),
    onSuccess: async () => {
      await invalidate();
      showToast(t.stageMoved);
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : t.stageMoved);
    },
  });

  const data = listQuery.data;
  const kpis = data?.kpis ?? {
    total: 0,
    active: 0,
    yeni: 0,
    following: 0,
    qualified: 0,
    converted: 0,
    unqualified: 0,
    unmatched: 0,
    failed: 0,
  };
  const items = useMemo(() => {
    const rows = data?.items ?? [];
    if (stage && CLOSED_STAGES.includes(stage as CrmLeadStage)) {
      return rows.filter((item) => item.stage === stage);
    }
    if (stage) {
      return rows.filter((item) => item.stage === stage);
    }
    return rows.filter((item) => !CLOSED_STAGES.includes(item.stage));
  }, [data?.items, stage]);
  const selected = detailQuery.data ?? items.find((item) => item.id === selectedId) ?? null;

  const grouped = useMemo(() => {
    const buckets: Record<CrmLeadStage, CrmLeadItem[]> = {
      yeni: [],
      contacted: [],
      following: [],
      qualified: [],
      converted: [],
      unqualified: [],
    };
    for (const item of items) {
      buckets[item.stage]?.push(item);
    }
    return buckets;
  }, [items]);

  const columnCount = (column: CrmLeadStage) => {
    if (!stage && CLOSED_STAGES.includes(column)) {
      return column === 'converted' ? kpis.converted : kpis.unqualified;
    }
    return grouped[column].length;
  };

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setStage('');
    setSource('');
    setProject('');
    setOwnerId('');
    setDateFrom('');
    setDateTo('');
  };

  const openDetail = (item: CrmLeadItem) => {
    setSelectedId(item.id);
  };

  const handleStageMove = (item: CrmLeadItem, next: CrmLeadStage) => {
    if (next === item.stage) return;
    if (next === 'converted') {
      showToast(t.convertBlocked);
      return;
    }
    stageMutation.mutate({ id: item.id, next });
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

  const activeEmpty = !stage && items.length === 0;

  return (
    <div className="crm-tasks crm-tasks--ops crm-leads crm-pipeline" data-testid="crm-pipeline-workspace">
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

      <section className="crm-leads__kpi-row crm-pipeline__kpi-row" aria-label={t.kpis}>
        {(
          [
            ['', t.total, kpis.active, 'crm-pipeline-kpi-active'],
            ['yeni', t.yeni, kpis.yeni, 'crm-pipeline-kpi-yeni'],
            ['following', t.following, kpis.following, 'crm-pipeline-kpi-following'],
            ['qualified', t.qualified, kpis.qualified, 'crm-pipeline-kpi-qualified'],
          ] as const
        ).map(([value, label, count, testId]) => (
          <button
            key={label}
            type="button"
            className={`crm-leads__kpi${stage === value ? ' is-active' : ''}`}
            data-testid={testId}
            onClick={() => setStage(value)}
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
        <Select label={t.source} value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="">{t.any}</option>
          {(data?.sources ?? Object.keys(SOURCE_LABEL)).map((item) => (
            <option key={item} value={item}>
              {sourceLabel(item, locale)}
            </option>
          ))}
        </Select>
        <Select label={t.project} value={project} onChange={(event) => setProject(event.target.value)}>
          <option value="">{t.any}</option>
          {(data?.projects ?? []).map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </Select>
        <Select label={t.owner} value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
          <option value="">{t.any}</option>
          {(data?.owners ?? []).map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
        <Input label={t.dateFrom} type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        <Input label={t.dateTo} type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        <div className="crm-tasks__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t.clear}
          </Button>
        </div>
      </section>

      <div className="crm-leads__kanban" data-testid="crm-pipeline-kanban">
        {STAGES.map((column) => {
          const closedHidden = !stage && CLOSED_STAGES.includes(column);
          return (
            <section
              key={column}
              className={`crm-leads__column${stage === column ? ' is-selected' : ''}${closedHidden ? ' is-historical' : ''}`}
              data-testid={`crm-pipeline-column-${column}`}
              onDragOver={(event) => {
                if (column !== 'converted') event.preventDefault();
              }}
              onDrop={() => {
                const item = (data?.items ?? []).find((row) => row.id === draggingId);
                setDraggingId(null);
                if (item) handleStageMove(item, column);
              }}
            >
              <h3>
                <button
                  type="button"
                  className="crm-pipeline__column-btn"
                  onClick={() => setStage(stage === column ? '' : column)}
                >
                  {stageLabel(column, locale)}
                </button>
                <span>{columnCount(column)}</span>
              </h3>
              {closedHidden
                ? null
                : grouped[column].map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      className="crm-leads__card"
                      data-testid={`crm-pipeline-card-${item.id}`}
                      draggable={canWrite && item.stage !== 'converted'}
                      onDragStart={() => setDraggingId(item.id)}
                      onDragEnd={() => setDraggingId(null)}
                      onClick={() => openDetail(item)}
                    >
                      <strong>{item.full_name}</strong>
                      <small>{item.phone || item.email || t.none}</small>
                      <small>
                        {sourceLabel(item.source, locale)}
                        {item.project ? ` · ${item.project}` : ''}
                      </small>
                      <small>
                        {item.owner_name || t.none} · {t.lastActivity} {formatWhen(item.updated_at, locale)}
                      </small>
                      <small>
                        {t.created} {formatWhen(item.created_at, locale)} · {t.stageAge}{' '}
                        {stageAge(item.updated_at || item.created_at, locale, t)}
                      </small>
                    </button>
                  ))}
            </section>
          );
        })}
      </div>

      {activeEmpty ? (
        <div className="crm-tasks__empty" data-testid="crm-pipeline-empty">
          <strong>{t.emptyTitle}</strong>
          <p>{t.emptyBody}</p>
        </div>
      ) : null}

      {selectedId && selected ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={t.close} onClick={() => setSelectedId(null)} />
          <aside className="crm-tasks__drawer" role="dialog" data-testid="crm-pipeline-drawer">
            <div className="crm-tasks__drawer-head">
              <h3>{selected.full_name}</h3>
              <button type="button" className="crm-tasks__link-btn" onClick={() => setSelectedId(null)}>
                {t.close}
              </button>
            </div>
            <div className="crm-tasks__drawer-body">
              <h4>{t.identity}</h4>
              <p>
                {selected.full_name}
                <br />
                {t.phone}: {selected.phone || t.none}
                <br />
                {t.email}: {selected.email || t.none}
              </p>
              <h4>{t.stage}</h4>
              {canWrite && selected.stage !== 'converted' ? (
                <Select
                  label={t.stage}
                  value={selected.stage}
                  onChange={(event) => handleStageMove(selected, event.target.value as CrmLeadStage)}
                >
                  {[...ACTIVE_STAGES, 'unqualified' as const].map((item) => (
                    <option key={item} value={item}>
                      {stageLabel(item, locale)}
                    </option>
                  ))}
                </Select>
              ) : (
                <p>{stageLabel(selected.stage, locale)}</p>
              )}
              <p>
                {t.source}: {sourceLabel(selected.source, locale)}
                <br />
                {t.campaign}: {selected.campaign || t.none}
                <br />
                {t.project}: {selected.project || t.none}
                <br />
                {t.owner}: {selected.owner_name || t.none}
                <br />
                {t.created}: {formatWhen(selected.created_at, locale)}
                <br />
                {t.lastActivity}: {formatWhen(selected.updated_at, locale)}
              </p>
              {selected.notes ? (
                <>
                  <h4>{t.notes}</h4>
                  <p>{selected.notes}</p>
                </>
              ) : null}
              {selected.converted_contact_id ? (
                <p>
                  <Link href={`/workspaces/crm/contacts/${selected.converted_contact_id}` as Route}>
                    {t.openPerson}: {selected.converted_contact_name || selected.converted_contact_id}
                  </Link>
                </p>
              ) : null}
              <h4>{t.history}</h4>
              <ul className="crm-leads__history">
                {(selected.activity ?? []).length === 0 ? <li>{t.none}</li> : null}
                {(selected.activity ?? []).slice(0, 8).map((event) => (
                  <li key={event.id}>
                    {activityLabel(event.description, locale)}
                    <small>
                      {event.actor_name || t.none} · {formatWhen(event.created_at, locale)}
                    </small>
                  </li>
                ))}
              </ul>
              {selected.stage === 'converted' ? <p>{t.convertedHint}</p> : null}
              {selected.stage === 'unqualified' ? <p>{t.closedHint}</p> : null}
            </div>
            {selected.converted_contact_id ? (
              <div className="crm-tasks__drawer-actions">
                <Button type="button" size="sm" onClick={() => openContact(selected.converted_contact_id as string)}>
                  {t.openPerson}
                </Button>
              </div>
            ) : null}
          </aside>
        </>
      ) : selectedId ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={t.close} onClick={() => setSelectedId(null)} />
          <aside className="crm-tasks__drawer" role="dialog">
            <LoadingState />
          </aside>
        </>
      ) : null}
    </div>
  );
}
