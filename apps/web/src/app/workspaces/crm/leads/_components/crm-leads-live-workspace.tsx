'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  CRM_LEAD_JUNK_REASONS,
  CRM_LEAD_STAGES,
  convertCrmLead,
  createCrmLead,
  CrmLeadConflictError,
  crmLeadDisplayName,
  crmLeadJunkReasonLabel,
  crmLeadStageLabel,
  emptyCrmLeadStageBuckets,
  fetchCrmLead,
  fetchCrmLeads,
  formatCrmInvestmentBudget,
  moveCrmLeadStage,
  updateCrmLead,
  type CrmLeadItem,
  type CrmLeadMatch,
  type CrmLeadStage,
  type CrmLeadTaskItem,
  type CrmLeadWrite,
} from '@/workspaces/crm/api/crm-leads';
import { createTask } from '@/workspaces/crm/api/activities';
import { CrmJunkReasonDialog } from '@/workspaces/crm/junk-reason-dialog';

type ViewMode = 'kanban' | 'list';
type DrawerMode = 'create' | 'detail' | 'edit' | 'convert';
type LeadView = CrmLeadItem & { metadata?: Record<string, unknown> | null };

const STAGES = CRM_LEAD_STAGES;
const CREATE_SOURCES = ['instagram', 'facebook', 'website', 'whatsapp', 'referral', 'manual', 'other'] as const;

const COPY = {
  tr: {
    title: 'Leadler',
    subtitle: 'Operasyonel lead çalışma alanı. Canlı CRM verisi, demo kayıt yok.',
    kpis: 'Lead özeti',
    total: 'Toplam Lead',
    yeni: 'Yeni Müşteri Adayı',
    following: 'Proje Ortaklığı',
    qualified: 'Potansiyel',
    converted: 'Satış Kapama',
    search: 'Ara',
    searchPh: 'Ad, telefon, e-posta ara...',
    stage: 'Aşama',
    source: 'Kaynak',
    project: 'Proje',
    interestedProject: 'İlgilendiği Proje',
    owner: 'Sorumlu',
    dateFrom: 'Başlangıç',
    dateTo: 'Bitiş',
    any: 'Tümü',
    clear: 'Filtreleri Temizle',
    create: 'Yeni Lead',
    addLead: '+ Lead Ekle',
    kanban: 'Kanban',
    list: 'Liste',
    viewsAria: 'Görünüm',
    emptyTitle: 'Henüz lead yok',
    emptyBody: 'Mevcut tablo boş. Demo kayıt eklenmez. Yeni lead ile başlayın.',
    emptyColumn: 'Bu aşamada lead bulunmuyor.',
    lead: 'Lead',
    name: 'Ad Soyad',
    phone: 'Telefon',
    email: 'E-posta',
    contact: 'Telefon / E-posta',
    comments: 'Yorumlar',
    referrer: 'Yönlendiren',
    lastActivity: 'Son Aktivite',
    nextTask: 'Sonraki Görev',
    created: 'Oluşturulma',
    history: 'İletişim geçmişi',
    actions: 'İşlem',
    open: 'Aç',
    convert: 'Satışa Döndü',
    converting: 'Dönüştürülüyor…',
    save: 'Kaydet',
    saving: 'Kaydediliyor…',
    edit: 'Düzenle',
    close: 'Kapat',
    openPerson: 'Kişiyi aç',
    warning: 'Mevcut kişi bulundu. Yeni kişi sessizce oluşturulmaz.',
    confirmCreate: 'Lead olarak devam et',
    unmatched: 'Eşleşmeyen kaynak leadleri',
    unmatchedHint: 'Kaynak kayıtları silinmez; eşleşme bekleyen satırlar burada durur.',
    showUnmatched: 'Eşleşmeyenleri göster',
    convertHint: 'Satış Kapama yalnızca dönüşüm gerçekleşince işaretlenir. Satın alma otomatik açılmaz.',
    personCreated: 'Kişi oluşturuldu',
    personReused: 'Mevcut kişi kullanıldı',
    stageMoved: 'Aşama güncellendi',
    createdOk: 'Lead oluşturuldu',
    updatedOk: 'Lead güncellendi',
    none: '—',
    filters: 'Lead filtreleri',
    table: 'Lead listesi',
    reason: 'Junk Sebebi',
    junkReason: 'Junk Sebebi',
    junkReasonDetail: 'Açıklama',
    junkReasonRequired: 'Junk sebebi gerekli',
    junkReasonDetailRequired: 'Diğer için kısa açıklama gerekli',
    ingestUnmatched: 'Eşleşmeyen kaynak',
    ingestFailed: 'Kaynak kaydı başarısız',
    budget: 'Yatırım Bütçesi',
    budgetPh: '500,000',
    addTask: 'Görev Ekle',
    taskName: 'Görev Adı',
    taskDate: 'Tarih',
    taskTime: 'Saat',
    taskCancel: 'İptal',
    taskCreate: 'Görevi Oluştur',
    taskCreating: 'Oluşturuluyor…',
    tasks: 'Görevler',
    taskStatus: 'Durum',
    taskCreated: 'Görev oluşturuldu',
    taskNameRequired: 'Görev adı gerekli',
    taskDateRequired: 'Tarih gerekli',
    taskTimeRequired: 'Saat gerekli',
  },
  en: {
    title: 'Leads',
    subtitle: 'Operational lead workspace. Live CRM data only, no demo rows.',
    kpis: 'Lead summary',
    total: 'Total leads',
    yeni: 'New Lead',
    following: 'Project Partnership',
    qualified: 'Potential',
    converted: 'Sales Closing',
    search: 'Search',
    searchPh: 'Search name, phone, email...',
    stage: 'Stage',
    source: 'Source',
    project: 'Project',
    interestedProject: 'Interested project',
    owner: 'Owner',
    dateFrom: 'Start',
    dateTo: 'End',
    any: 'All',
    clear: 'Clear filters',
    create: 'New lead',
    addLead: '+ Add lead',
    kanban: 'Kanban',
    list: 'List',
    viewsAria: 'View',
    emptyTitle: 'No leads yet',
    emptyBody: 'The board is empty. Demo rows are not seeded. Start with a new lead.',
    emptyColumn: 'No leads in this stage.',
    lead: 'Lead',
    name: 'Full name',
    phone: 'Phone',
    email: 'Email',
    contact: 'Phone / Email',
    comments: 'Comments',
    referrer: 'Referred by',
    lastActivity: 'Last activity',
    nextTask: 'Next task',
    created: 'Created',
    history: 'Communication history',
    actions: 'Action',
    open: 'Open',
    convert: 'Converted',
    converting: 'Converting…',
    save: 'Save',
    saving: 'Saving…',
    edit: 'Edit',
    close: 'Close',
    openPerson: 'Open person',
    warning: 'An existing person matched. A duplicate person will not be created silently.',
    confirmCreate: 'Continue as lead',
    unmatched: 'Unmatched source leads',
    unmatchedHint: 'Source rows are kept; unmatched intake stays here.',
    showUnmatched: 'Show unmatched',
    convertHint: 'Sales Closing is marked only after conversion. A purchase is not created automatically.',
    personCreated: 'Person created',
    personReused: 'Existing person reused',
    stageMoved: 'Stage updated',
    createdOk: 'Lead created',
    updatedOk: 'Lead updated',
    none: '—',
    filters: 'Lead filters',
    table: 'Lead list',
    reason: 'Junk Reason',
    junkReason: 'Junk Reason',
    junkReasonDetail: 'Explanation',
    junkReasonRequired: 'Junk reason is required',
    junkReasonDetailRequired: 'A short explanation is required for Other',
    ingestUnmatched: 'Unmatched source',
    ingestFailed: 'Source intake failed',
    budget: 'Investment Budget',
    budgetPh: '500,000',
    addTask: 'Add Task',
    taskName: 'Task Name',
    taskDate: 'Date',
    taskTime: 'Time',
    taskCancel: 'Cancel',
    taskCreate: 'Create Task',
    taskCreating: 'Creating…',
    tasks: 'Tasks',
    taskStatus: 'Status',
    taskCreated: 'Task created',
    taskNameRequired: 'Task name is required',
    taskDateRequired: 'Date is required',
    taskTimeRequired: 'Time is required',
  },
};

const SOURCE_LABEL: Record<string, { tr: string; en: string }> = {
  manual: { tr: 'Manuel', en: 'Manual' },
  website: { tr: 'Web Sitesi', en: 'Website' },
  web: { tr: 'Web Sitesi', en: 'Website' },
  meta: { tr: 'Facebook Lead', en: 'Facebook Lead' },
  facebook: { tr: 'Facebook Lead', en: 'Facebook Lead' },
  instagram: { tr: 'Instagram Lead', en: 'Instagram Lead' },
  whatsapp: { tr: 'WhatsApp', en: 'WhatsApp' },
  wa: { tr: 'WhatsApp', en: 'WhatsApp' },
  referral: { tr: 'Acenta', en: 'Agency' },
  agency: { tr: 'Acenta', en: 'Agency' },
  agent: { tr: 'Acenta', en: 'Agency' },
  acenta: { tr: 'Acenta', en: 'Agency' },
  acente: { tr: 'Acenta', en: 'Agency' },
  google: { tr: 'Google Ads', en: 'Google Ads' },
  other: { tr: 'Diğer', en: 'Other' },
};

const EMPTY_TASK_FORM = { title: '', date: '', time: '' };
const TASK_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TASK_TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

const EMPTY_FORM: CrmLeadWrite = {
  full_name: '',
  phone: '',
  email: '',
  source: 'manual',
  campaign: '',
  project: '',
  owner_user_id: '',
  notes: '',
  stage: 'yeni',
  investment_budget_amount: '',
  investment_budget_currency: 'USD',
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

function toIstanbulDuePayload(date: string, time: string): string {
  return `${date}T${time}:00+03:00`;
}

function taskFormValid(form: typeof EMPTY_TASK_FORM): boolean {
  return Boolean(form.title.trim() && TASK_DATE_RE.test(form.date) && TASK_TIME_RE.test(form.time));
}

function formatTaskDuePart(value: string | null | undefined, locale: 'tr' | 'en', part: 'date' | 'time'): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  if (part === 'date') {
    return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
      timeZone: 'Europe/Istanbul',
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(date);
  }
  return new Intl.DateTimeFormat(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    timeZone: 'Europe/Istanbul',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date);
}

function taskStatusLabel(status: string | null | undefined, locale: 'tr' | 'en'): string {
  const key = (status || 'open').toLowerCase();
  const labels: Record<string, { tr: string; en: string }> = {
    open: { tr: 'Açık', en: 'Open' },
    not_started: { tr: 'Açık', en: 'Open' },
    in_progress: { tr: 'Devam ediyor', en: 'In progress' },
    completed: { tr: 'Tamamlandı', en: 'Completed' },
    cancelled: { tr: 'İptal', en: 'Cancelled' },
  };
  return labels[key]?.[locale] ?? status ?? '—';
}

function sourceKey(value: string | null | undefined): string {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');
}

function sourceLocaleLabel(key: string, locale: 'tr' | 'en'): string {
  return SOURCE_LABEL[key]?.[locale] ?? SOURCE_LABEL.other?.[locale] ?? key;
}

function sourceLabel(value: string | null | undefined, locale: 'tr' | 'en'): string {
  if (!value?.trim()) return '—';
  const key = sourceKey(value);
  if (SOURCE_LABEL[key]) return sourceLocaleLabel(key, locale);
  if (/instagram/.test(key)) return sourceLocaleLabel('instagram', locale);
  if (/facebook|meta/.test(key)) return sourceLocaleLabel('facebook', locale);
  if (/whatsapp|^wa$/.test(key)) return sourceLocaleLabel('whatsapp', locale);
  if (/website|web_site|^web$/.test(key)) return sourceLocaleLabel('website', locale);
  if (/acenta|acente|agency|agent|referral/.test(key)) return sourceLocaleLabel('referral', locale);
  if (/manual|manuel/.test(key)) return sourceLocaleLabel('manual', locale);
  if (/^[a-z0-9_]+$/.test(key)) return sourceLocaleLabel('other', locale);
  return value.trim();
}

function sourceTone(value: string | null | undefined): string {
  const key = sourceKey(value);
  if (/instagram/.test(key)) return 'instagram';
  if (/facebook|meta/.test(key)) return 'facebook';
  if (/whatsapp|^wa$/.test(key)) return 'whatsapp';
  if (/website|web_site|^web$/.test(key)) return 'website';
  if (/acenta|acente|agency|agent|referral/.test(key)) return 'agency';
  return 'other';
}

function isAgencySource(value: string | null | undefined): boolean {
  return sourceTone(value) === 'agency';
}

function stageLabel(stage: CrmLeadStage, locale: 'tr' | 'en'): string {
  return crmLeadStageLabel(stage, locale);
}

function displayOwner(name: string | null | undefined): string {
  return String(name || '')
    .replace(/\s*\((?:Demo|demo)\)\s*$/g, '')
    .trim();
}

function metaText(item: LeadView, keys: string[]): string | null {
  const meta = item.metadata;
  if (!meta || typeof meta !== 'object') return null;
  for (const key of keys) {
    const value = meta[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

function referrerLabel(item: LeadView): string | null {
  if (!isAgencySource(item.source)) return null;
  return metaText(item, ['referrer_name', 'referrer', 'agency_name', 'agency', 'referred_by', 'yonlendiren']);
}

function unqualifiedReason(item: LeadView, locale: 'tr' | 'en'): string | null {
  if (item.stage !== 'unqualified') return null;
  if (item.junk_reason) return crmLeadJunkReasonLabel(item.junk_reason, locale);
  return metaText(item, ['lost_reason', 'unqualified_reason', 'reason']);
}

function lastActivityLabel(item: LeadView, locale: 'tr' | 'en', none: string): string {
  const latest = item.activity?.[0];
  if (latest) {
    return `${activityLabel(latest.description, locale)} · ${formatWhen(latest.created_at, locale)}`;
  }
  if (item.updated_at && item.updated_at !== item.created_at) {
    return formatWhen(item.updated_at, locale);
  }
  return none;
}

function ingestLabel(status: string, t: (typeof COPY)['tr']): string | null {
  if (status === 'unmatched') return t.ingestUnmatched;
  if (status === 'failed') return t.ingestFailed;
  return null;
}

function activityLabel(key: string, locale: 'tr' | 'en'): string {
  const map: Record<string, { tr: string; en: string }> = {
    'crm.leads.created': { tr: 'Lead oluşturuldu', en: 'Lead created' },
    'crm.leads.updated': { tr: 'Lead güncellendi', en: 'Lead updated' },
    'crm.leads.stage_changed': { tr: 'Aşama değişti', en: 'Stage changed' },
    'crm.leads.converted': { tr: 'Satışa döndü', en: 'Converted' },
    'crm.leads.ingest.ok': { tr: 'Kaynak lead alındı', en: 'Provider lead stored' },
    'crm.leads.ingest.unmatched': { tr: 'Eşleşmeyen kaynak lead saklandı', en: 'Unmatched provider lead kept' },
    'crm.leads.ingest.failed': { tr: 'Başarısız kaynak lead saklandı', en: 'Failed provider lead kept' },
    'crm.leads.facebook_messenger.received': {
      tr: 'Facebook Messenger mesajı',
      en: 'Facebook Messenger message',
    },
  };
  return map[key]?.[locale] ?? key;
}

export function CrmLeadsLiveWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const t = COPY[locale];
  const { canRead, canCreate, authLoading, user, canManageTasks } = useCrmAccess();
  const canWrite = canCreate || canUpdateCrm(user);
  const canAddTask = canManageTasks;
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
  const [junkReason, setJunkReason] = useState('');
  const [junkPending, setJunkPending] = useState<LeadView | null>(null);
  const [drawer, setDrawer] = useState<DrawerMode | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<CrmLeadWrite>(EMPTY_FORM);
  const [conflict, setConflict] = useState<CrmLeadConflictError | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [taskFormOpen, setTaskFormOpen] = useState(false);
  const [taskForm, setTaskForm] = useState(EMPTY_TASK_FORM);
  const [taskFormError, setTaskFormError] = useState<string | null>(null);

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
      junk_reason: junkReason || undefined,
    }),
    [search, stage, source, project, ownerId, dateFrom, dateTo, ingestStatus, junkReason],
  );

  const listQuery = useQuery({
    queryKey: ['crm-leads', filters],
    queryFn: () => fetchCrmLeads(filters),
    enabled: canRead && !authLoading,
    placeholderData: keepPreviousData,
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
    await queryClient.invalidateQueries({ queryKey: ['crm'] });
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
    mutationFn: ({
      id,
      next,
      junk_reason,
      junk_reason_detail,
    }: {
      id: string;
      next: CrmLeadStage;
      junk_reason?: string;
      junk_reason_detail?: string;
    }) => moveCrmLeadStage(id, next, { junk_reason, junk_reason_detail }),
    onSuccess: async () => {
      setJunkPending(null);
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
  const items = (data?.items ?? []) as LeadView[];
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
  const selected = (detailQuery.data ?? items.find((item) => item.id === selectedId) ?? null) as LeadView | null;

  const taskMutation = useMutation({
    mutationFn: async () => {
      const title = taskForm.title.trim();
      if (!title) throw new Error(t.taskNameRequired);
      if (!TASK_DATE_RE.test(taskForm.date)) throw new Error(t.taskDateRequired);
      if (!TASK_TIME_RE.test(taskForm.time)) throw new Error(t.taskTimeRequired);
      if (!selectedId) throw new Error(t.save);
      return createTask({
        title,
        lead_id: selectedId,
        contact_id: selected?.contact_id || selected?.converted_contact_id || undefined,
        due_on: taskForm.date,
        due_time: taskForm.time,
        due_date: toIstanbulDuePayload(taskForm.date, taskForm.time),
        timezone: 'Europe/Istanbul',
      });
    },
    onSuccess: async () => {
      setTaskForm(EMPTY_TASK_FORM);
      setTaskFormError(null);
      setTaskFormOpen(false);
      await invalidate();
      showToast(t.taskCreated);
    },
    onError: (error) => {
      setTaskFormError(error instanceof Error ? error.message : t.save);
    },
  });

  const grouped = useMemo(() => {
    const buckets = emptyCrmLeadStageBuckets<LeadView>();
    for (const item of items) {
      buckets[item.stage]?.push(item);
    }
    return buckets;
  }, [items]);

  const sourceOptions = useMemo(() => {
    const live = (data?.sources ?? []).filter(Boolean);
    return live.length ? live : [...CREATE_SOURCES];
  }, [data?.sources]);

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
    setJunkReason('');
  };

  const openCreate = (nextStage?: CrmLeadStage) => {
    setForm({ ...EMPTY_FORM, stage: nextStage || 'yeni' });
    setConflict(null);
    setSelectedId(null);
    setDrawer('create');
  };

  const openDetail = (item: LeadView) => {
    setSelectedId(item.id);
    setConflict(null);
    setTaskFormOpen(false);
    setTaskForm(EMPTY_TASK_FORM);
    setTaskFormError(null);
    setDrawer('detail');
  };

  const openEdit = (item: LeadView) => {
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
      stage: item.stage,
      investment_budget_amount: item.investment_budget_amount ?? '',
      investment_budget_currency: item.investment_budget_currency ?? 'USD',
    });
    setDrawer('edit');
  };

  const submitForm = (confirm = false) => {
    if (form.stage === 'unqualified' && !form.junk_reason) {
      showToast(t.junkReasonRequired);
      return;
    }
    if (form.stage === 'unqualified' && form.junk_reason === 'other' && !(form.junk_reason_detail || '').trim()) {
      showToast(t.junkReasonDetailRequired);
      return;
    }
    const payload: CrmLeadWrite = {
      full_name: form.full_name?.trim() || undefined,
      phone: form.phone?.trim() || undefined,
      email: form.email?.trim() || undefined,
      source: form.source || 'manual',
      campaign: form.campaign?.trim() || undefined,
      project: form.project?.trim() || undefined,
      owner_user_id: form.owner_user_id || null,
      notes: form.notes?.trim() || undefined,
      stage: form.stage,
      junk_reason: form.stage === 'unqualified' ? form.junk_reason : undefined,
      junk_reason_detail:
        form.stage === 'unqualified' && form.junk_reason === 'other' ? form.junk_reason_detail?.trim() : undefined,
      investment_budget_amount: form.investment_budget_amount?.trim() || null,
      investment_budget_currency: form.investment_budget_currency?.trim() || 'USD',
    };
    if (drawer === 'edit' && selectedId) {
      updateMutation.mutate({ id: selectedId, payload });
      return;
    }
    createMutation.mutate({ payload, confirm });
  };

  const handleStageMove = (item: LeadView, next: CrmLeadStage) => {
    if (next === item.stage) return;
    if (next === 'converted') {
      setSelectedId(item.id);
      setDrawer('convert');
      setConflict(null);
      return;
    }
    if (next === 'unqualified') {
      setJunkPending(item);
      return;
    }
    stageMutation.mutate({ id: item.id, next });
  };

  if (authLoading || (listQuery.isLoading && !data)) {
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
  const kpisLive = data?.kpis ?? kpis;

  return (
    <div className="crm-ops crm-ops--leads" data-testid="crm-leads-workspace">
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
        <div className="crm-ops-views" role="tablist" aria-label={t.viewsAria}>
          <button type="button" className={view === 'kanban' ? 'is-active' : ''} onClick={() => setView('kanban')}>
            {t.kanban}
          </button>
          <button type="button" className={view === 'list' ? 'is-active' : ''} onClick={() => setView('list')}>
            {t.list}
          </button>
        </div>
      </header>

      <section className="crm-ops-kpis" aria-label={t.kpis}>
        {(
          [
            { value: '', label: t.total, count: kpisLive.total, testId: 'crm-leads-kpi-total', icon: 'users' as IhIconName, tone: '' },
            { value: 'yeni', label: t.yeni, count: kpisLive.yeni, testId: 'crm-leads-kpi-yeni', icon: 'inbox' as IhIconName, tone: 'is-blue' },
            { value: 'following', label: t.following, count: kpisLive.following, testId: 'crm-leads-kpi-following', icon: 'clock' as IhIconName, tone: 'is-gold' },
            { value: 'qualified', label: t.qualified, count: kpisLive.qualified, testId: 'crm-leads-kpi-qualified', icon: 'sparkles' as IhIconName, tone: 'is-purple' },
            { value: 'converted', label: t.converted, count: kpisLive.converted, testId: 'crm-leads-kpi-converted', icon: 'check' as IhIconName, tone: 'is-mint' },
          ] as const
        ).map((item) => (
          <button
            key={item.testId}
            type="button"
            className={`${item.tone}${stage === item.value ? ' is-active' : ''}`}
            data-testid={item.testId}
            onClick={() => {
              setStage(item.value);
              setJunkReason('');
            }}
          >
            <span className="crm-ops-kpis__icon" aria-hidden>
              <IhIcon name={item.icon} size={16} />
            </span>
            <strong>{item.count.toLocaleString(locale)}</strong>
            <span>{item.label}</span>
          </button>
        ))}
      </section>

      {unmatchedCount > 0 ? (
        <div className="crm-ops-banner">
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

      <section className="crm-ops-filtercard" aria-label={t.filters}>
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
        <Select
          label={t.stage}
          value={stage}
          onChange={(event) => {
            const next = event.target.value;
            setStage(next);
            if (next !== 'unqualified') setJunkReason('');
          }}
        >
          <option value="">{t.any}</option>
          {STAGES.map((item) => (
            <option key={item} value={item}>
              {stageLabel(item, locale)}
            </option>
          ))}
        </Select>
        {stage === 'unqualified' ? (
          <Select label={t.junkReason} value={junkReason} onChange={(event) => setJunkReason(event.target.value)}>
            <option value="">{t.any}</option>
            {CRM_LEAD_JUNK_REASONS.map((item) => (
              <option key={item.code} value={item.code}>
                {item[locale]}
              </option>
            ))}
          </Select>
        ) : null}
        <Select label={t.source} value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="">{t.any}</option>
          {sourceOptions.map((item) => (
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
              {displayOwner(item.name) || item.name}
            </option>
          ))}
        </Select>
        <Input label={t.dateFrom} type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} />
        <Input label={t.dateTo} type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} />
        <div className="crm-ops-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t.clear}
          </Button>
          {canWrite ? (
            <Button type="button" size="sm" onClick={() => openCreate()}>
              {t.create}
            </Button>
          ) : null}
        </div>
      </section>

      {view === 'kanban' ? (
        <div className="crm-ops-kanban" data-testid="crm-leads-kanban">
          {STAGES.map((column) => (
            <section
              key={column}
              className={`crm-ops-kanban__col is-${column}${draggingId ? ' is-drop' : ''}`}
              onDragOver={(event) => event.preventDefault()}
              onDrop={() => {
                const item = items.find((row) => row.id === draggingId);
                setDraggingId(null);
                if (item) handleStageMove(item, column);
              }}
            >
              <div className="crm-ops-kanban__head">
                <h3>
                  <span className="crm-ops-kanban__dot" aria-hidden />
                  {stageLabel(column, locale)}
                </h3>
                <span className="crm-ops-kanban__count">{grouped[column].length}</span>
              </div>
              <div className="crm-ops-kanban__body">
                {grouped[column].length === 0 ? (
                  <div className="crm-ops-col-empty">
                    <strong>{t.emptyTitle}</strong>
                    <p>{t.emptyColumn}</p>
                  </div>
                ) : (
                  grouped[column].map((item) => (
                    <LeadCard
                      key={item.id}
                      item={item}
                      locale={locale}
                      t={t}
                      canDrag={canWrite && item.stage !== 'converted'}
                      onDragStart={() => setDraggingId(item.id)}
                      onDragEnd={() => setDraggingId(null)}
                      onOpen={() => openDetail(item)}
                    />
                  ))
                )}
              </div>
              {canWrite ? (
                <button type="button" className="crm-ops-col-add" onClick={() => openCreate(column)}>
                  {t.addLead}
                </button>
              ) : null}
            </section>
          ))}
        </div>
      ) : (
        <div className="crm-ops-tablecard" role="region" aria-label={t.table}>
          {items.length === 0 ? (
            <div className="crm-ops-empty" data-testid="crm-leads-empty">
              <span className="crm-ops-empty__icon" aria-hidden>
                <IhIcon name="empty" size={20} />
              </span>
              <strong>{t.emptyTitle}</strong>
              <p>{t.emptyBody}</p>
            </div>
          ) : (
            <div className="crm-ops-table-wrap">
              <table className="crm-ops-table" data-testid="crm-leads-table">
                <thead>
                  <tr>
                    <th>{t.lead}</th>
                    <th>{t.contact}</th>
                    <th>{t.source}</th>
                    <th>{t.stage}</th>
                    <th>{t.interestedProject}</th>
                    <th>{t.budget}</th>
                    <th>{t.owner}</th>
                    <th>{t.lastActivity}</th>
                    <th>{t.nextTask}</th>
                    <th>{t.created}</th>
                    <th>{t.actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const referrer = referrerLabel(item);
                    return (
                      <tr key={item.id} className="crm-ops-row" onClick={() => openDetail(item)}>
                        <td>
                          <button type="button" className="crm-ops-link" onClick={() => openDetail(item)}>
                            {crmLeadDisplayName(item)}
                          </button>
                        </td>
                        <td>
                          {item.phone || t.none}
                          <div>{item.email || t.none}</div>
                        </td>
                        <td>
                          <span className={`crm-ops-badge is-${sourceTone(item.source)}`}>
                            {sourceLabel(item.source, locale)}
                          </span>
                          {referrer ? (
                            <div>
                              {t.referrer}: {referrer}
                            </div>
                          ) : null}
                        </td>
                        <td>
                          <span className={`crm-ops-badge is-${item.stage}`}>{stageLabel(item.stage, locale)}</span>
                        </td>
                        <td>{item.project || t.none}</td>
                        <td>
                          {formatCrmInvestmentBudget(
                            item.investment_budget_amount,
                            item.investment_budget_currency,
                            locale,
                          )}
                        </td>
                        <td>{displayOwner(item.owner_name) || t.none}</td>
                        <td>{lastActivityLabel(item, locale, t.none)}</td>
                        <td>{t.none}</td>
                        <td>{formatWhen(item.created_at, locale)}</td>
                        <td>
                          <button
                            type="button"
                            className="crm-ops-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              openDetail(item);
                            }}
                          >
                            {t.open}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {view === 'kanban' && items.length === 0 ? (
        <div className="crm-ops-empty" data-testid="crm-leads-empty">
          <span className="crm-ops-empty__icon" aria-hidden>
            <IhIcon name="empty" size={20} />
          </span>
          <strong>{t.emptyTitle}</strong>
          <p>{t.emptyBody}</p>
        </div>
      ) : null}

      {drawer ? (
        <>
          <button type="button" className="crm-ops-drawer-backdrop" aria-label={t.close} onClick={() => setDrawer(null)} />
          <aside className="crm-ops-drawer" role="dialog" data-testid="crm-leads-drawer">
            <div className="crm-ops-drawer__head">
              <h3>
                {drawer === 'create'
                  ? t.create
                  : drawer === 'edit'
                    ? t.edit
                    : drawer === 'convert'
                      ? t.convert
                      : (selected ? crmLeadDisplayName(selected) : t.title)}
              </h3>
              <button type="button" className="crm-ops-link" onClick={() => setDrawer(null)}>
                {t.close}
              </button>
            </div>
            <div className="crm-ops-drawer__body">
              {drawer === 'create' || drawer === 'edit' ? (
                <form
                  className="crm-ops-form"
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
                    {CREATE_SOURCES.map((item) => (
                      <option key={item} value={item}>
                        {sourceLabel(item, locale)}
                      </option>
                    ))}
                  </Select>
                  <Input
                    label={t.interestedProject}
                    value={form.project ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, project: event.target.value }))}
                  />
                  <Select
                    label={t.owner}
                    value={form.owner_user_id ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, owner_user_id: event.target.value }))}
                  >
                    <option value="">{t.any}</option>
                    {(data?.owners ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {displayOwner(item.name) || item.name}
                      </option>
                    ))}
                  </Select>
                  {drawer === 'create' ? (
                    <Select
                      label={t.stage}
                      value={form.stage ?? 'yeni'}
                      onChange={(event) => {
                        const next = event.target.value as CrmLeadStage;
                        setForm((current) => ({
                          ...current,
                          stage: next,
                          junk_reason: next === 'unqualified' ? current.junk_reason : undefined,
                          junk_reason_detail: next === 'unqualified' ? current.junk_reason_detail : undefined,
                        }));
                      }}
                    >
                      {STAGES.filter((item) => item !== 'converted').map((item) => (
                        <option key={item} value={item}>
                          {stageLabel(item, locale)}
                        </option>
                      ))}
                    </Select>
                  ) : null}
                  {form.stage === 'unqualified' ? (
                    <>
                      <Select
                        label={t.junkReason}
                        value={form.junk_reason ?? ''}
                        onChange={(event) =>
                          setForm((current) => ({ ...current, junk_reason: event.target.value || undefined }))
                        }
                      >
                        <option value="">{t.any}</option>
                        {CRM_LEAD_JUNK_REASONS.map((item) => (
                          <option key={item.code} value={item.code}>
                            {item[locale]}
                          </option>
                        ))}
                      </Select>
                      {form.junk_reason === 'other' ? (
                        <TextArea
                          label={t.junkReasonDetail}
                          value={form.junk_reason_detail ?? ''}
                          rows={3}
                          onChange={(event) =>
                            setForm((current) => ({ ...current, junk_reason_detail: event.target.value }))
                          }
                        />
                      ) : null}
                    </>
                  ) : null}
                  <Input
                    label={t.budget}
                    value={form.investment_budget_amount ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, investment_budget_amount: event.target.value }))
                    }
                    placeholder={t.budgetPh}
                  />
                  <TextArea
                    label={t.comments}
                    value={form.notes ?? ''}
                    rows={4}
                    onChange={(event) => setForm((current) => ({ ...current, notes: event.target.value }))}
                  />
                  {conflict ? (
                    <div className="crm-ops-conflict">
                      <strong>{t.warning}</strong>
                      {conflict.matches.map((match) => (
                        <ConflictLink key={`${match.kind}-${match.id}`} match={match} onPerson={(id) => openContact(id)} />
                      ))}
                      {drawer === 'create' && conflict.code !== 'existing_lead' ? (
                        <Button type="button" size="sm" variant="secondary" onClick={() => submitForm(true)}>
                          {t.confirmCreate}
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                  <Button type="submit" size="sm" disabled={saving}>
                    {saving ? t.saving : t.save}
                  </Button>
                </form>
              ) : selected ? (
                <>
                  {taskFormOpen ? (
                    <form
                      className="crm-ops-taskform"
                      data-testid="crm-lead-task-form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (!taskFormValid(taskForm) || taskMutation.isPending) return;
                        taskMutation.mutate();
                      }}
                    >
                      <Input
                        label={t.taskName}
                        value={taskForm.title}
                        onChange={(event) => setTaskForm((current) => ({ ...current, title: event.target.value }))}
                        required
                      />
                      <Input
                        label={t.taskDate}
                        type="date"
                        value={taskForm.date}
                        onChange={(event) => setTaskForm((current) => ({ ...current, date: event.target.value }))}
                        required
                      />
                      <Input
                        label={t.taskTime}
                        type="time"
                        value={taskForm.time}
                        onChange={(event) => setTaskForm((current) => ({ ...current, time: event.target.value }))}
                        required
                      />
                      {taskFormError ? <p className="crm-ops-conflict">{taskFormError}</p> : null}
                      <div className="crm-ops-taskform__actions">
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            setTaskFormOpen(false);
                            setTaskFormError(null);
                            setTaskForm(EMPTY_TASK_FORM);
                          }}
                        >
                          {t.taskCancel}
                        </Button>
                        <Button type="submit" size="sm" disabled={!taskFormValid(taskForm) || taskMutation.isPending}>
                          {taskMutation.isPending ? t.taskCreating : t.taskCreate}
                        </Button>
                      </div>
                    </form>
                  ) : null}
                  <LeadDetail
                    item={selected}
                    locale={locale}
                    t={t}
                    canWrite={canWrite}
                    onStage={(next) => handleStageMove(selected, next)}
                    onPerson={openContact}
                  />
                </>
              ) : (
                <LoadingState />
              )}
              {conflict && drawer !== 'create' && drawer !== 'edit' ? (
                <div className="crm-ops-conflict">
                  <strong>{t.warning}</strong>
                  {conflict.matches.map((match) => (
                    <ConflictLink key={`${match.kind}-${match.id}`} match={match} onPerson={(id) => openContact(id)} />
                  ))}
                </div>
              ) : null}
            </div>
            {selected && drawer !== 'create' && drawer !== 'edit' ? (
              <div className="crm-ops-drawer__actions">
                {canWrite && drawer !== 'convert' && selected.stage !== 'converted' ? (
                  <Button type="button" size="sm" variant="secondary" onClick={() => openEdit(selected)}>
                    {t.edit}
                  </Button>
                ) : null}
                {canAddTask && drawer !== 'convert' ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setTaskFormOpen(true);
                      setTaskFormError(null);
                    }}
                  >
                    {t.addTask}
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
                {selected.converted_contact_id || selected.contact_id ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => openContact((selected.converted_contact_id || selected.contact_id) as string)}
                  >
                    {t.openPerson}
                  </Button>
                ) : null}
              </div>
            ) : null}
          </aside>
        </>
      ) : null}

      <CrmJunkReasonDialog
        open={Boolean(junkPending)}
        locale={locale}
        pending={stageMutation.isPending}
        onCancel={() => setJunkPending(null)}
        onConfirm={(payload) => {
          if (!junkPending) return;
          stageMutation.mutate({ id: junkPending.id, next: 'unqualified', ...payload });
        }}
      />
    </div>
  );
}

function LeadCard({
  item,
  locale,
  t,
  canDrag,
  onDragStart,
  onDragEnd,
  onOpen,
}: {
  item: LeadView;
  locale: 'tr' | 'en';
  t: (typeof COPY)['tr'];
  canDrag: boolean;
  onDragStart: () => void;
  onDragEnd: () => void;
  onOpen: () => void;
}) {
  const referrer = referrerLabel(item);
  const ingest = ingestLabel(item.ingest_status, t);
  return (
    <button
      type="button"
      className="crm-ops-leadcard"
      draggable={canDrag}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onClick={onOpen}
    >
      <strong>{crmLeadDisplayName(item)}</strong>
      {item.phone ? <small>{item.phone}</small> : null}
      {item.email ? <small>{item.email}</small> : null}
      <div className="crm-ops-leadcard__meta">
        <span className={`crm-ops-badge is-${sourceTone(item.source)}`}>{sourceLabel(item.source, locale)}</span>
        {ingest ? <span className="crm-ops-badge is-warn">{ingest}</span> : null}
      </div>
      {referrer ? (
        <small>
          {t.referrer}: {referrer}
        </small>
      ) : null}
      {item.project ? <small>{item.project}</small> : null}
      {item.investment_budget_amount ? (
        <small>
          {t.budget}: {formatCrmInvestmentBudget(item.investment_budget_amount, item.investment_budget_currency, locale)}
        </small>
      ) : null}
      {displayOwner(item.owner_name) ? <small>{displayOwner(item.owner_name)}</small> : null}
      <small>
        {t.lastActivity}: {lastActivityLabel(item, locale, t.none)}
      </small>
      <small>
        {t.created}: {formatWhen(item.created_at, locale)}
      </small>
    </button>
  );
}

function LeadDetail({
  item,
  locale,
  t,
  canWrite,
  onStage,
  onPerson,
}: {
  item: LeadView;
  locale: 'tr' | 'en';
  t: (typeof COPY)['tr'];
  canWrite: boolean;
  onStage: (next: CrmLeadStage) => void;
  onPerson: (id: string) => void;
}) {
  const referrer = referrerLabel(item);
  const reason = unqualifiedReason(item, locale);
  const activity = item.activity ?? [];
  return (
    <>
      <dl className="crm-ops-kv">
        <dt>{t.name}</dt>
        <dd>{crmLeadDisplayName(item)}</dd>
        <dt>{t.phone}</dt>
        <dd>{item.phone || t.none}</dd>
        <dt>{t.email}</dt>
        <dd>{item.email || t.none}</dd>
        <dt>{t.source}</dt>
        <dd>
          <span className={`crm-ops-badge is-${sourceTone(item.source)}`}>{sourceLabel(item.source, locale)}</span>
        </dd>
        {isAgencySource(item.source) ? (
          <>
            <dt>{t.referrer}</dt>
            <dd>{referrer || t.none}</dd>
          </>
        ) : null}
        <dt>{t.interestedProject}</dt>
        <dd>{item.project || t.none}</dd>
        <dt>{t.budget}</dt>
        <dd>{formatCrmInvestmentBudget(item.investment_budget_amount, item.investment_budget_currency, locale)}</dd>
        <dt>{t.stage}</dt>
        <dd>
          <span className={`crm-ops-badge is-${item.stage}`}>{stageLabel(item.stage, locale)}</span>
        </dd>
        {reason ? (
          <>
            <dt>{t.reason}</dt>
            <dd data-testid="crm-lead-junk-reason">
              {reason}
              {item.junk_reason === 'other' && item.junk_reason_detail ? ` — ${item.junk_reason_detail}` : ''}
            </dd>
          </>
        ) : null}
        <dt>{t.owner}</dt>
        <dd>{displayOwner(item.owner_name) || t.none}</dd>
        <dt>{t.created}</dt>
        <dd>{formatWhen(item.created_at, locale)}</dd>
      </dl>

      <h4>{t.comments}</h4>
      {item.notes ? <p className="crm-ops-note">{item.notes}</p> : <p className="crm-ops-muted">{t.none}</p>}

      {canWrite && item.stage !== 'converted' ? (
        <Select label={t.stage} value={item.stage} onChange={(event) => onStage(event.target.value as CrmLeadStage)}>
          {STAGES.filter((stage) => stage !== 'converted').map((stage) => (
            <option key={stage} value={stage}>
              {stageLabel(stage, locale)}
            </option>
          ))}
        </Select>
      ) : null}

      {item.converted_contact_id || item.contact_id || item.existing_person_id ? (
        <p>
          <button
            type="button"
            className="crm-ops-link"
            onClick={() =>
              onPerson(
                (item.converted_contact_id || item.contact_id || item.existing_person_id) as string,
              )
            }
          >
            {t.openPerson}:{' '}
            {item.converted_contact_name || item.contact_name || item.existing_person_name || item.contact_id}
          </button>
        </p>
      ) : null}

      <h4>{t.tasks}</h4>
      {(item.tasks ?? []).length === 0 ? (
        <p className="crm-ops-muted">{t.none}</p>
      ) : (
        <ul className="crm-ops-tasklist">
          {(item.tasks ?? []).map((task: CrmLeadTaskItem) => (
            <li key={task.id}>
              <strong>{task.title}</strong>
              <small>
                {formatTaskDuePart(task.due_date, locale, 'date')} · {formatTaskDuePart(task.due_date, locale, 'time')} ·{' '}
                {t.taskStatus}: {taskStatusLabel(task.status || task.task_status, locale)}
              </small>
            </li>
          ))}
        </ul>
      )}

      <h4>{t.history}</h4>
      <ul className="crm-ops-history">
        {activity.length === 0 ? <li>{t.none}</li> : null}
        {activity.map((event) => (
          <li key={event.id}>
            {activityLabel(event.description, locale)}
            {typeof event.metadata?.preview === 'string' && event.metadata.preview ? ` — ${event.metadata.preview}` : ''}
            <small>
              {event.actor_name || t.none} · {formatWhen(event.created_at, locale)}
            </small>
          </li>
        ))}
      </ul>
      <p className="crm-ops-muted">{t.convertHint}</p>
    </>
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
        <button type="button" className="crm-ops-link" onClick={() => onPerson(match.id)}>
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
