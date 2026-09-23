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
  convertCrmLead,
  createCrmLead,
  CrmLeadConflictError,
  fetchCrmLead,
  fetchCrmLeads,
  moveCrmLeadStage,
  updateCrmLead,
  type CrmLeadItem,
  type CrmLeadMatch,
  type CrmLeadStage,
  type CrmLeadWrite,
} from '@/workspaces/crm/api/crm-leads';

type ViewMode = 'kanban' | 'list';
type DrawerMode = 'create' | 'detail' | 'edit' | 'convert';

const STAGES: CrmLeadStage[] = ['yeni', 'contacted', 'following', 'qualified', 'converted', 'unqualified'];

const COPY = {
  tr: {
    title: 'Leadler',
    subtitle: 'Operasyonel lead çalışma alanı. Canlı CRM verisi, demo kayıt yok.',
    kpis: 'Lead özeti',
    total: 'Toplam Lead',
    yeni: 'Yeni',
    following: 'Takipte',
    qualified: 'Nitelikli',
    converted: 'Satışa Döndü',
    search: 'Ara',
    searchPh: 'Ad, telefon, e-posta',
    stage: 'Aşama',
    source: 'Kaynak',
    project: 'Proje',
    owner: 'Sorumlu',
    date: 'Tarih',
    dateFrom: 'Başlangıç',
    dateTo: 'Bitiş',
    any: 'Tümü',
    clear: 'Filtreleri Temizle',
    create: 'Yeni Lead',
    kanban: 'Kanban',
    list: 'Liste',
    emptyTitle: 'Henüz lead yok',
    emptyBody: 'Mevcut tablo boş. Demo kayıt eklenmez. Yeni lead ile başlayın.',
    name: 'Ad Soyad',
    phone: 'Telefon',
    email: 'E-posta',
    campaign: 'Kampanya',
    notes: 'Not',
    created: 'Oluşturma',
    history: 'Aktivite / geçmiş',
    convert: 'Kişiye dönüştür',
    converting: 'Dönüştürülüyor…',
    save: 'Kaydet',
    saving: 'Kaydediliyor…',
    edit: 'Düzenle',
    close: 'Kapat',
    openPerson: 'Kişiyi aç',
    warning: 'Mevcut kişi bulundu. Yeni kişi sessizce oluşturulmaz.',
    confirmCreate: 'Lead olarak devam et',
    unmatched: 'Eşleşmeyen / başarısız kaynak leadleri',
    unmatchedHint: 'Gelecek Meta, Instagram, Google ve website kayıtları silinmez.',
    showUnmatched: 'Eşleşmeyenleri göster',
    convertHint: 'Satışa döndü yalnızca dönüşüm gerçekleşince işaretlenir. Satın alma otomatik açılmaz.',
    personCreated: 'Kişi oluşturuldu',
    personReused: 'Mevcut kişi kullanıldı',
    stageMoved: 'Aşama güncellendi',
    createdOk: 'Lead oluşturuldu',
    updatedOk: 'Lead güncellendi',
    none: '—',
    filters: 'Lead filtreleri',
    table: 'Lead listesi',
    identity: 'Kimlik / iletişim',
    attribution: 'Kaynak ve kampanya',
    future: 'Gelecek kaynaklar: Meta / Facebook, Instagram, Google Ads, website formları. Bağlantı henüz yok.',
  },
  en: {
    title: 'Leads',
    subtitle: 'Operational lead workspace. Live CRM data only, no demo rows.',
    kpis: 'Lead summary',
    total: 'Total leads',
    yeni: 'New',
    following: 'Following',
    qualified: 'Qualified',
    converted: 'Converted',
    search: 'Search',
    searchPh: 'Name, phone, email',
    stage: 'Stage',
    source: 'Source',
    project: 'Project',
    owner: 'Owner',
    date: 'Date',
    dateFrom: 'From',
    dateTo: 'To',
    any: 'All',
    clear: 'Clear filters',
    create: 'New lead',
    kanban: 'Kanban',
    list: 'List',
    emptyTitle: 'No leads yet',
    emptyBody: 'The table is empty. Demo rows are not seeded. Create a lead to start.',
    name: 'Full name',
    phone: 'Phone',
    email: 'Email',
    campaign: 'Campaign',
    notes: 'Notes',
    created: 'Created',
    history: 'Activity / history',
    convert: 'Convert to person',
    converting: 'Converting…',
    save: 'Save',
    saving: 'Saving…',
    edit: 'Edit',
    close: 'Close',
    openPerson: 'Open person',
    warning: 'An existing person matched. A duplicate person will not be created silently.',
    confirmCreate: 'Continue as lead',
    unmatched: 'Unmatched / failed intake leads',
    unmatchedHint: 'Future Meta, Instagram, Google, and website rows are never discarded.',
    showUnmatched: 'Show unmatched',
    convertHint: 'Converted is marked only after conversion. A purchase is not created automatically.',
    personCreated: 'Person created',
    personReused: 'Existing person reused',
    stageMoved: 'Stage updated',
    createdOk: 'Lead created',
    updatedOk: 'Lead updated',
    none: '—',
    filters: 'Lead filters',
    table: 'Lead list',
    identity: 'Identity / contact',
    attribution: 'Source and campaign',
    future: 'Future sources: Meta / Facebook, Instagram, Google Ads, website forms. Not connected yet.',
  },
};

const STAGE_LABEL: Record<CrmLeadStage, { tr: string; en: string }> = {
  yeni: { tr: 'Yeni', en: 'New' },
  contacted: { tr: 'İletişime Geçildi', en: 'Contacted' },
  following: { tr: 'Takipte', en: 'Following' },
  qualified: { tr: 'Nitelikli', en: 'Qualified' },
  converted: { tr: 'Satışa Döndü', en: 'Converted' },
  unqualified: { tr: 'Uygun Değil', en: 'Unqualified' },
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

const EMPTY_FORM: CrmLeadWrite = {
  full_name: '',
  phone: '',
  email: '',
  source: 'manual',
  campaign: '',
  project: '',
  owner_user_id: '',
  notes: '',
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
    'crm.leads.ingest.ok': { tr: 'Kaynak lead alındı', en: 'Provider lead stored' },
    'crm.leads.ingest.unmatched': { tr: 'Eşleşmeyen kaynak lead saklandı', en: 'Unmatched provider lead kept' },
    'crm.leads.ingest.failed': { tr: 'Başarısız kaynak lead saklandı', en: 'Failed provider lead kept' },
  };
  return map[key]?.[locale] ?? key;
}

export function CrmLeadsLiveWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const t = COPY[locale];
  const { canRead, canCreate, authLoading, user } = useCrmAccess();
  const canWrite = canCreate || canUpdateCrm(user);
  const queryClient = useQueryClient();
  const { openContact } = useContactCard();

  const [view, setView] = useState<ViewMode>('kanban');
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [stage, setStage] = useState('');
  const [source, setSource] = useState('');
  const [project, setProject] = useState('');
  const [ownerId, setOwnerId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [ingestStatus, setIngestStatus] = useState('');
  const [drawer, setDrawer] = useState<DrawerMode | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<CrmLeadWrite>(EMPTY_FORM);
  const [conflict, setConflict] = useState<CrmLeadConflictError | null>(null);
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
      ingest_status: ingestStatus || undefined,
    }),
    [search, stage, source, project, ownerId, dateFrom, dateTo, ingestStatus],
  );

  const listQuery = useQuery({
    queryKey: ['crm-leads', filters],
    queryFn: () => fetchCrmLeads(filters),
    enabled: canRead && !authLoading,
  });

  const detailQuery = useQuery({
    queryKey: ['crm-lead', selectedId],
    queryFn: () => fetchCrmLead(selectedId as string),
    enabled: Boolean(selectedId) && drawer !== 'create',
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

  const createMutation = useMutation({
    mutationFn: ({ payload, confirm }: { payload: CrmLeadWrite; confirm?: boolean }) =>
      createCrmLead(payload, confirm),
    onSuccess: async (lead) => {
      setConflict(null);
      setSelectedId(lead.id);
      setDrawer('detail');
      await invalidate();
      showToast(t.createdOk);
    },
    onError: (error) => {
      if (error instanceof CrmLeadConflictError) {
        setConflict(error);
        return;
      }
      showToast(error instanceof Error ? error.message : t.save);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CrmLeadWrite }) => updateCrmLead(id, payload),
    onSuccess: async () => {
      setDrawer('detail');
      await invalidate();
      showToast(t.updatedOk);
    },
  });

  const stageMutation = useMutation({
    mutationFn: ({ id, next }: { id: string; next: CrmLeadStage }) => moveCrmLeadStage(id, next),
    onSuccess: async () => {
      await invalidate();
      showToast(t.stageMoved);
    },
  });

  const convertMutation = useMutation({
    mutationFn: ({ id, personId }: { id: string; personId?: string }) => convertCrmLead(id, personId),
    onSuccess: async (result) => {
      setConflict(null);
      setDrawer('detail');
      await invalidate();
      showToast(result.reused_existing ? t.personReused : t.personCreated);
    },
    onError: (error) => {
      if (error instanceof CrmLeadConflictError) {
        setConflict(error);
        setDrawer('convert');
        return;
      }
      showToast(error instanceof Error ? error.message : t.convert);
    },
  });

  const data = listQuery.data;
  const items = data?.items ?? [];
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

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setStage('');
    setSource('');
    setProject('');
    setOwnerId('');
    setDateFrom('');
    setDateTo('');
    setIngestStatus('');
  };

  const openCreate = () => {
    setForm(EMPTY_FORM);
    setConflict(null);
    setSelectedId(null);
    setDrawer('create');
  };

  const openDetail = (item: CrmLeadItem) => {
    setSelectedId(item.id);
    setConflict(null);
    setDrawer('detail');
  };

  const openEdit = (item: CrmLeadItem) => {
    setSelectedId(item.id);
    setForm({
      full_name: item.full_name,
      phone: item.phone ?? '',
      email: item.email ?? '',
      source: item.source ?? 'manual',
      campaign: item.campaign ?? '',
      project: item.project ?? '',
      owner_user_id: item.owner_user_id ?? '',
      notes: item.notes ?? '',
    });
    setDrawer('edit');
  };

  const submitForm = (confirm = false) => {
    const payload: CrmLeadWrite = {
      full_name: form.full_name?.trim() || undefined,
      phone: form.phone?.trim() || undefined,
      email: form.email?.trim() || undefined,
      source: form.source || 'manual',
      campaign: form.campaign?.trim() || undefined,
      project: form.project?.trim() || undefined,
      owner_user_id: form.owner_user_id || null,
      notes: form.notes?.trim() || undefined,
    };
    if (drawer === 'edit' && selectedId) {
      updateMutation.mutate({ id: selectedId, payload });
      return;
    }
    createMutation.mutate({ payload, confirm });
  };

  const handleStageMove = (item: CrmLeadItem, next: CrmLeadStage) => {
    if (next === item.stage) return;
    if (next === 'converted') {
      setSelectedId(item.id);
      setDrawer('convert');
      setConflict(null);
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

  const unmatchedCount = kpis.unmatched + kpis.failed;
  const saving = createMutation.isPending || updateMutation.isPending || convertMutation.isPending;

  return (
    <div className="crm-tasks crm-tasks--ops crm-leads" data-testid="crm-leads-workspace">
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
        <div className="crm-leads__views" role="tablist" aria-label={t.kanban}>
          <button type="button" className={view === 'kanban' ? 'is-active' : ''} onClick={() => setView('kanban')}>
            {t.kanban}
          </button>
          <button type="button" className={view === 'list' ? 'is-active' : ''} onClick={() => setView('list')}>
            {t.list}
          </button>
        </div>
      </header>

      <section className="crm-leads__kpi-row" aria-label={t.kpis}>
        {(
          [
            ['', t.total, kpis.total, 'crm-leads-kpi-total'],
            ['yeni', t.yeni, kpis.yeni, 'crm-leads-kpi-yeni'],
            ['following', t.following, kpis.following, 'crm-leads-kpi-following'],
            ['qualified', t.qualified, kpis.qualified, 'crm-leads-kpi-qualified'],
            ['converted', t.converted, kpis.converted, 'crm-leads-kpi-converted'],
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

      {unmatchedCount > 0 ? (
        <div className="crm-leads__banner">
          <div>
            <strong>{t.unmatched}</strong>
            <div>
              {unmatchedCount} · {t.unmatchedHint}
            </div>
          </div>
          <Button type="button" size="sm" variant="secondary" onClick={() => setIngestStatus(ingestStatus ? '' : 'attention')}>
            {t.showUnmatched}
          </Button>
        </div>
      ) : null}

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
        <Select label={t.stage} value={stage} onChange={(event) => setStage(event.target.value)}>
          <option value="">{t.any}</option>
          {STAGES.map((item) => (
            <option key={item} value={item}>
              {stageLabel(item, locale)}
            </option>
          ))}
        </Select>
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
          {canWrite ? (
            <Button type="button" size="sm" onClick={openCreate}>
              {t.create}
            </Button>
          ) : null}
        </div>
      </section>

      {view === 'kanban' ? (
        <div className="crm-leads__kanban" data-testid="crm-leads-kanban">
          {STAGES.map((column) => (
            <section
              key={column}
              className={`crm-leads__column${draggingId ? ' is-drop' : ''}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => {
                const item = items.find((row) => row.id === draggingId);
                setDraggingId(null);
                if (item) handleStageMove(item, column);
              }}
            >
              <h3>
                {stageLabel(column, locale)}
                <span>{grouped[column].length}</span>
              </h3>
              {grouped[column].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="crm-leads__card"
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
                  {item.ingest_status !== 'ok' ? (
                    <span className={`crm-leads__ingest is-${item.ingest_status}`}>{item.ingest_status}</span>
                  ) : null}
                </button>
              ))}
            </section>
          ))}
        </div>
      ) : (
        <div className="crm-tasks__table-wrap" role="region" aria-label={t.table}>
          {items.length === 0 ? (
            <div className="crm-tasks__empty" data-testid="crm-leads-empty">
              <strong>{t.emptyTitle}</strong>
              <p>{t.emptyBody}</p>
            </div>
          ) : (
            <table className="crm-tasks__table crm-tasks__table--ops" data-testid="crm-leads-table">
              <thead>
                <tr>
                  <th>{t.name}</th>
                  <th>{t.phone}</th>
                  <th>{t.email}</th>
                  <th>{t.source}</th>
                  <th>{t.project}</th>
                  <th>{t.campaign}</th>
                  <th>{t.owner}</th>
                  <th>{t.stage}</th>
                  <th>{t.date}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} onClick={() => openDetail(item)}>
                    <td>{item.full_name}</td>
                    <td>{item.phone || t.none}</td>
                    <td>{item.email || t.none}</td>
                    <td>{sourceLabel(item.source, locale)}</td>
                    <td>{item.project || t.none}</td>
                    <td>{item.campaign || t.none}</td>
                    <td>{item.owner_name || t.none}</td>
                    <td>{stageLabel(item.stage, locale)}</td>
                    <td>{formatWhen(item.created_at, locale)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {view === 'kanban' && items.length === 0 ? (
        <div className="crm-tasks__empty" data-testid="crm-leads-empty">
          <strong>{t.emptyTitle}</strong>
          <p>{t.emptyBody}</p>
        </div>
      ) : null}

      {drawer ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={t.close} onClick={() => setDrawer(null)} />
          <aside className="crm-tasks__drawer" role="dialog" data-testid="crm-leads-drawer">
            <div className="crm-tasks__drawer-head">
              <h3>
                {drawer === 'create'
                  ? t.create
                  : drawer === 'edit'
                    ? t.edit
                    : drawer === 'convert'
                      ? t.convert
                      : selected?.full_name || t.title}
              </h3>
              <button type="button" className="crm-tasks__link-btn" onClick={() => setDrawer(null)}>
                {t.close}
              </button>
            </div>
            <div className="crm-tasks__drawer-body">
              {drawer === 'create' || drawer === 'edit' ? (
                <form
                  className="crm-tasks__form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    submitForm(false);
                  }}
                >
                  <Input
                    label={t.name}
                    value={form.full_name ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
                  />
                  <Input
                    label={t.phone}
                    value={form.phone ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
                  />
                  <Input
                    label={t.email}
                    value={form.email ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
                  />
                  <Select
                    label={t.source}
                    value={form.source ?? 'manual'}
                    onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
                  >
                    {Object.keys(SOURCE_LABEL).map((item) => (
                      <option key={item} value={item}>
                        {sourceLabel(item, locale)}
                      </option>
                    ))}
                  </Select>
                  <Input
                    label={t.project}
                    value={form.project ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, project: event.target.value }))}
                  />
                  <Input
                    label={t.campaign}
                    value={form.campaign ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, campaign: event.target.value }))}
                  />
                  <Select
                    label={t.owner}
                    value={form.owner_user_id ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, owner_user_id: event.target.value }))}
                  >
                    <option value="">{t.any}</option>
                    {(data?.owners ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </Select>
                  <TextArea
                    label={t.notes}
                    value={form.notes ?? ''}
                    rows={4}
                    onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                  />
                  {conflict ? (
                    <div className="crm-leads__conflict">
                      <strong>{t.warning}</strong>
                      {conflict.matches.map((match) => (
                        <ConflictLink key={`${match.kind}-${match.id}`} match={match} onPerson={(id) => openContact(id)} />
                      ))}
                      {drawer === 'create' ? (
                        <Button type="button" size="sm" variant="secondary" onClick={() => submitForm(true)}>
                          {t.confirmCreate}
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                  <Button type="submit" size="sm" disabled={saving}>
                    {saving ? t.saving : t.save}
                  </Button>
                  <p>
                    <small>{t.future}</small>
                  </p>
                </form>
              ) : selected ? (
                <>
                  <h4>{t.identity}</h4>
                  <p>
                    {selected.full_name}
                    <br />
                    {selected.phone || t.none} · {selected.email || t.none}
                  </p>
                  <h4>{t.attribution}</h4>
                  <p>
                    {t.source}: {sourceLabel(selected.source, locale)}
                    <br />
                    {t.campaign}: {selected.campaign || t.none}
                    {selected.ad_id ? (
                      <>
                        <br />
                        Ad: {selected.ad_id}
                      </>
                    ) : null}
                    {selected.form_id ? (
                      <>
                        <br />
                        Form: {selected.form_id}
                      </>
                    ) : null}
                    <br />
                    {t.project}: {selected.project || t.none}
                    <br />
                    {t.owner}: {selected.owner_name || t.none}
                    <br />
                    {t.stage}: {stageLabel(selected.stage, locale)}
                    <br />
                    {t.created}: {formatWhen(selected.created_at, locale)}
                  </p>
                  {selected.notes ? (
                    <>
                      <h4>{t.notes}</h4>
                      <p>{selected.notes}</p>
                    </>
                  ) : null}
                  {canWrite && selected.stage !== 'converted' ? (
                    <Select
                      label={t.stage}
                      value={selected.stage}
                      onChange={(event) => handleStageMove(selected, event.target.value as CrmLeadStage)}
                    >
                      {STAGES.filter((item) => item !== 'converted').map((item) => (
                        <option key={item} value={item}>
                          {stageLabel(item, locale)}
                        </option>
                      ))}
                    </Select>
                  ) : null}
                  {selected.converted_contact_id ? (
                    <p>
                      <Link href={`/workspaces/crm/contacts/${selected.converted_contact_id}` as Route}>
                        {t.openPerson}: {selected.converted_contact_name || selected.converted_contact_id}
                      </Link>
                    </p>
                  ) : selected.existing_person_id ? (
                    <div className="crm-leads__conflict">
                      <strong>{t.warning}</strong>
                      <ConflictLink
                        match={{
                          kind: 'person',
                          id: selected.existing_person_id,
                          name: selected.existing_person_name || selected.existing_person_id,
                          reason: 'email',
                          href: `/workspaces/crm/contacts/${selected.existing_person_id}`,
                        }}
                        onPerson={openContact}
                      />
                    </div>
                  ) : null}
                  <h4>{t.history}</h4>
                  <ul className="crm-leads__history">
                    {(selected.activity ?? []).length === 0 ? <li>{t.none}</li> : null}
                    {(selected.activity ?? []).map((event) => (
                      <li key={event.id}>
                        {activityLabel(event.description, locale)}
                        <small>
                          {event.actor_name || t.none} · {formatWhen(event.created_at, locale)}
                        </small>
                      </li>
                    ))}
                  </ul>
                  {conflict ? (
                    <div className="crm-leads__conflict">
                      <strong>{t.warning}</strong>
                      {conflict.matches.map((match) => (
                        <ConflictLink key={`${match.kind}-${match.id}`} match={match} onPerson={(id) => openContact(id)} />
                      ))}
                    </div>
                  ) : null}
                  <p>
                    <small>{t.convertHint}</small>
                  </p>
                </>
              ) : (
                <LoadingState />
              )}
            </div>
            {selected && drawer !== 'create' && drawer !== 'edit' ? (
              <div className="crm-tasks__drawer-actions">
                {canWrite && drawer !== 'convert' && selected.stage !== 'converted' ? (
                  <Button type="button" size="sm" variant="secondary" onClick={() => openEdit(selected)}>
                    {t.edit}
                  </Button>
                ) : null}
                {canWrite && selected.stage !== 'converted' ? (
                  <Button
                    type="button"
                    size="sm"
                    disabled={convertMutation.isPending}
                    onClick={() => {
                      const personId = conflict?.matches.find((item) => item.kind === 'person')?.id;
                      convertMutation.mutate({ id: selected.id, personId });
                    }}
                  >
                    {convertMutation.isPending ? t.converting : t.convert}
                  </Button>
                ) : null}
                {selected.converted_contact_id ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => openContact(selected.converted_contact_id as string)}
                  >
                    {t.openPerson}
                  </Button>
                ) : null}
              </div>
            ) : null}
          </aside>
        </>
      ) : null}
    </div>
  );
}

function ConflictLink({
  match,
  onPerson,
}: {
  match: CrmLeadMatch;
  onPerson: (contactId: string) => void;
}) {
  if (match.kind === 'person') {
    return (
      <div>
        <button type="button" className="crm-tasks__link-btn" onClick={() => onPerson(match.id)}>
          {match.name}
        </button>
        <div>
          <Link href={`/workspaces/crm/contacts/${match.id}` as Route}>{match.name}</Link>
        </div>
      </div>
    );
  }
  return <div>{match.name}</div>;
}
