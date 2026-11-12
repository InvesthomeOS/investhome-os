'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocale } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, ErrorState, Input, LoadingState, Select, TextArea } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers, hasPermission } from '@/lib/api/auth';
import { fetchInventoryAssets } from '@/lib/api/inventory';
import { fetchProjectPhases } from '@/lib/api/project-phases';
import { fetchProjects } from '@/lib/api/projects';
import { canUpdateCrm } from '@/lib/crm/crm-permissions';
import { useDebouncedQueryParam, useListQueryPatch } from '@/lib/crm/list-query';
import { confirmDiscardUnsaved, saveFailedMessage } from '@/lib/crm/unsaved-form';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { EmailSendComposer } from '@/workspaces/crm/contact-card/email-send-composer';
import { WhatsAppSendComposer } from '@/workspaces/crm/contact-card/whatsapp-send-composer';
import { fetchMembershipProjects } from '@/workspaces/crm/api/contacts';
import { phaseFieldVisible, unitIdentifier } from '@/workspaces/crm/project-phase-unit.mjs';
import { lockPageScroll } from '@/lib/ui/scroll-lock.mjs';
import { formatOsDateTime } from '@/lib/datetime/os-datetime.mjs';
import { OsOverflowMenu } from '@/components/shell/os-overflow-menu';
import { createNote } from '@/workspaces/crm/api/activities';
import {
  CRM_LEAD_JUNK_REASONS,
  CRM_LEAD_STAGES,
  archiveCrmLead,
  convertCrmLead,
  createCrmLead,
  CrmLeadConflictError,
  crmLeadDisplayName,
  crmLeadJunkReasonLabel,
  crmLeadStageLabel,
  emptyCrmLeadStageBuckets,
  fetchCrmLead,
  fetchCrmLeadBoard,
  fetchCrmLeadBoardCards,
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
import { CrmContactPicker } from '@/workspaces/crm/crm-person-fields';
import { CRM_SOURCE_OPTIONS, crmSourceChoices, crmSourceLabel } from '@/workspaces/crm/crm-source-options';

type ViewMode = 'kanban' | 'list';
type DrawerMode = 'create' | 'detail' | 'edit' | 'convert';
type DetailTab = 'general' | 'tasks' | 'notes' | 'history';
type LeadView = CrmLeadItem & { metadata?: Record<string, unknown> | null };

const STAGES = CRM_LEAD_STAGES;
const CREATE_SOURCES = CRM_SOURCE_OPTIONS.map((item) => item.value);

const COPY = {
  tr: {
    title: 'Pipeline',
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
    sourceField: 'Geliş Kaynağı',
    unassigned: 'Atanmamış',
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
    junkView: 'Junk / Lost',
    messages: 'Mesajlar',
    matches: 'Eşleşmeler',
    agreements: 'Anlaşmalar',
    viewsAria: 'Görünüm',
    emptyTitle: 'Henüz lead yok',
    emptyBody: 'Mevcut tablo boş. Demo kayıt eklenmez. Yeni lead ile başlayın.',
    previous: 'Önceki',
    next: 'Sonraki',
    more: 'Daha fazla',
    loadErrorTitle: 'Leadler yüklenemedi',
    loadError: 'Kayıtlar alınamadı. Yeniden deneyin.',
    retry: 'Yeniden dene',
    emptyColumn: 'Bu aşamada lead bulunmuyor.',
    lead: 'Lead',
    name: 'Ad Soyad',
    phone: 'Telefon',
    email: 'E-posta',
    contact: 'Telefon / E-posta',
    comments: 'Yorumlar',
    notesField: 'Notlar',
    referrer: 'Yönlendiren',
    lastActivity: 'Son Aktivite',
    nextTask: 'Sonraki Görev',
    created: 'Oluşturulma',
    history: 'İletişim geçmişi',
    generalTab: 'Genel Bilgiler',
    tasksTab: 'Görevler',
    commentsTab: 'Notlar',
    notesTab: 'Notlar',
    addNote: 'Not ekle',
    notePlaceholder: 'Not',
    noteSaved: 'Not eklendi',
    historyTab: 'İletişim Geçmişi',
    emailAction: 'E-posta',
    whatsappAction: 'WhatsApp',
    reusePerson: 'Mevcut kişiyle devam et',
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
    purchaseBudget: 'Alım Bütçesi',
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
    taskReminder: 'Hatırlatma',
    taskReminder10: '10 dakika önce',
    taskReminderNone: 'Hatırlatma yok',
  },
  en: {
    title: 'Pipeline',
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
    sourceField: 'Source',
    unassigned: 'Unassigned',
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
    junkView: 'Junk / Lost',
    messages: 'Messages',
    matches: 'Matches',
    agreements: 'Agreements',
    viewsAria: 'View',
    emptyTitle: 'No leads yet',
    emptyBody: 'The board is empty. Demo rows are not seeded. Start with a new lead.',
    previous: 'Previous',
    next: 'Next',
    more: 'Load more',
    loadErrorTitle: 'Leads could not be loaded',
    loadError: 'The records could not be loaded. Try again.',
    retry: 'Retry',
    emptyColumn: 'No leads in this stage.',
    lead: 'Lead',
    name: 'Full name',
    phone: 'Phone',
    email: 'Email',
    contact: 'Phone / Email',
    comments: 'Comments',
    notesField: 'Notes',
    referrer: 'Referred by',
    lastActivity: 'Last activity',
    nextTask: 'Next task',
    created: 'Created',
    history: 'Communication history',
    generalTab: 'General',
    tasksTab: 'Tasks',
    commentsTab: 'Notes',
    notesTab: 'Notes',
    addNote: 'Add note',
    notePlaceholder: 'Note',
    noteSaved: 'Note added',
    historyTab: 'Communication history',
    emailAction: 'Email',
    whatsappAction: 'WhatsApp',
    reusePerson: 'Continue with existing person',
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
    purchaseBudget: 'Purchase budget',
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
    taskReminder: 'Reminder',
    taskReminder10: '10 minutes before',
    taskReminderNone: 'No reminder',
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
  referral: { tr: 'Acente', en: 'Agency' },
  agency: { tr: 'Acente', en: 'Agency' },
  agent: { tr: 'Acente', en: 'Agency' },
  acenta: { tr: 'Acente', en: 'Agency' },
  acente: { tr: 'Acente', en: 'Agency' },
  google: { tr: 'Google Ads', en: 'Google Ads' },
  other: { tr: 'Diğer', en: 'Other' },
};

const EMPTY_TASK_FORM = { title: '', date: '', time: '', reminder: '10' };
const TASK_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const TASK_TIME_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

const EMPTY_FORM: CrmLeadWrite = {
  full_name: '',
  first_name: '',
  last_name: '',
  phone: '',
  email: '',
  contact_id: '',
  address_line1: '',
  city: '',
  state_province: '',
  country: '',
  language: '',
  organization_name: '',
  job_title: '',
  next_follow_up_at: '',
  source: 'manual',
  campaign: '',
  project: '',
  project_id: '',
  phase_id: '',
  inventory_asset_id: '',
  owner_user_id: '',
  notes: '',
  stage: 'yeni',
  investment_budget_amount: '',
  investment_budget_currency: 'USD',
};

function formatWhen(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  return formatOsDateTime(value, locale);
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
  return value.trim().replace(/Acenta/g, 'Acente').replace(/acenta/g, 'acente');
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
    'crm.leads.facebook_messenger.sent': {
      tr: 'Facebook Messenger yanıtı',
      en: 'Facebook Messenger reply',
    },
    'crm.leads.instagram_dm.received': {
      tr: 'Instagram mesajı',
      en: 'Instagram message',
    },
    'crm.leads.instagram_dm.sent': {
      tr: 'Instagram yanıtı',
      en: 'Instagram reply',
    },
  };
  return map[key]?.[locale] ?? key;
}

export function CrmLeadsLiveWorkspace() {
  const locale = useLocale() === 'tr' ? 'tr' : 'en';
  const t = COPY[locale];
  const { canRead, canCreate, authLoading, user, canManageTasks, has } = useCrmAccess();
  const canSendEmail = has('send_communications');
  const canUpdate = canUpdateCrm(user);
  const canArchive = Boolean(user && hasPermission(user, 'leads', 'archive'));
  const canAddTask = canManageTasks;
  const queryClient = useQueryClient();
  const archiveMutation = useMutation({
    mutationFn: (id: string) => archiveCrmLead(id),
    onSuccess: async () => {
      setSelectedId(null);
      setDrawer(null);
      await queryClient.invalidateQueries({ queryKey: ['crm-leads'] });
      setToast(locale === 'tr' ? 'Pipeline kaydı kaldırıldı.' : 'Pipeline record removed.');
    },
    onError: () => {
      setFormError(locale === 'tr' ? 'Pipeline kaydı kaldırılamadı.' : 'Pipeline record could not be removed.');
    },
  });

  const { openContact } = useContactCard();

  const searchParams = useSearchParams();
  const patchQuery = useListQueryPatch();
  const [searchDraft, setSearchDraft, search] = useDebouncedQueryParam('q');
  const [view, setView] = useState<ViewMode>('kanban');
  const [emailComposeOpen, setEmailComposeOpen] = useState(false);
  const [whatsappComposeOpen, setWhatsappComposeOpen] = useState(false);
  const stage = searchParams.get('stage') ?? '';
  const source = searchParams.get('source') ?? '';
  const project = searchParams.get('project') ?? '';
  const phaseFilter = searchParams.get('phase') ?? '';
  const ownerId = searchParams.get('owner') ?? '';
  const dateFrom = searchParams.get('from') ?? '';
  const dateTo = searchParams.get('to') ?? '';
  const ingestStatus = searchParams.get('ingest') ?? '';
  const junkReason = searchParams.get('junk') ?? '';
  const page = Math.max(1, Number(searchParams.get('page') || '1') || 1);
  const setSource = (value: string) => patchQuery({ source: value, page: null });
  const setProject = (value: string) => patchQuery({ project: value, phase: null, page: null });
  const setPhaseFilter = (value: string) => patchQuery({ phase: value, page: null });
  const setOwnerId = (value: string) => patchQuery({ owner: value, page: null });
  const setDateFrom = (value: string) => patchQuery({ from: value, page: null });
  const setDateTo = (value: string) => patchQuery({ to: value, page: null });
  const setIngestStatus = (value: string) => patchQuery({ ingest: value, page: null });
  const setJunkReason = (value: string) => patchQuery({ junk: value, page: null });
  const [junkPending, setJunkPending] = useState<LeadView | null>(null);
  const [drawer, setDrawer] = useState<DrawerMode | null>(null);
  const [detailTab, setDetailTab] = useState<DetailTab>('general');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<CrmLeadWrite>(EMPTY_FORM);
  const [projectSearch, setProjectSearch] = useState('');
  const leadFormOpen = drawer === 'create' || drawer === 'edit';
  const activeUsersQuery = useQuery({
    queryKey: ['crm', 'active-users'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: leadFormOpen,
  });
  const projectsQuery = useQuery({
    queryKey: ['crm-lead-projects', projectSearch],
    queryFn: () => fetchProjects({
      search: projectSearch.trim() || undefined,
      page: 1,
      page_size: 100,
      sort_by: 'project_name',
      sort_order: 'asc',
    }),
    enabled: leadFormOpen,
  });
  const leadPhasesQuery = useQuery({
    queryKey: ['crm-lead-form-phases', form.project_id],
    queryFn: () => fetchProjectPhases(form.project_id || ''),
    enabled: leadFormOpen && Boolean(form.project_id),
  });
  const selectedLeadProject = (projectsQuery.data?.items ?? []).find((item) => item.id === form.project_id);
  const leadUsesPhases = Boolean(selectedLeadProject?.uses_phases);
  const leadPhaseReady = leadUsesPhases && phaseFieldVisible(leadPhasesQuery.data);
  const leadUnitsQuery = useQuery({
    queryKey: ['crm-lead-form-units', form.project_id, form.phase_id, leadUsesPhases, leadPhasesQuery.data?.length],
    queryFn: () =>
      fetchInventoryAssets({
        project_id: form.project_id || undefined,
        phase_id: leadUsesPhases ? form.phase_id || undefined : undefined,
        page: 1,
        page_size: 100,
      }),
    enabled:
      leadFormOpen &&
      Boolean(form.project_id) &&
      (!leadUsesPhases || Boolean(form.phase_id)),
  });
  const membershipProjectsQuery = useQuery({
    queryKey: ['crm-membership-projects'],
    queryFn: fetchMembershipProjects,
    enabled: canRead && !authLoading,
  });
  const membershipProjects = useMemo(() => {
    const seen = new Set<string>();
    return (membershipProjectsQuery.data ?? []).filter((item) => {
      if (!item.project_id || seen.has(item.project_id)) return false;
      seen.add(item.project_id);
      return true;
    });
  }, [membershipProjectsQuery.data]);
  const selectedMembership = membershipProjects.find((item) => item.project_id === project);
  const filterPhases = (selectedMembership?.phases ?? []).filter((item) => item.active);
  const [formBaseline, setFormBaseline] = useState<CrmLeadWrite>(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<CrmLeadConflictError | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [taskFormOpen, setTaskFormOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState('');
  const [taskForm, setTaskForm] = useState(EMPTY_TASK_FORM);
  const [taskFormError, setTaskFormError] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      search: search || undefined,
      stage: stage || undefined,
      source: source || undefined,
      project: project || undefined,
      phase_id: phaseFilter || undefined,
      owner_id: ownerId || undefined,
      date_from: dateFrom ? `${dateFrom}T00:00:00Z` : undefined,
      date_to: dateTo ? `${dateTo}T23:59:59Z` : undefined,
      ingest_status: ingestStatus || undefined,
      junk_reason: junkReason || undefined,
      surface: 'pipeline' as const,
    }),
    [search, stage, source, project, phaseFilter, ownerId, dateFrom, dateTo, ingestStatus, junkReason],
  );

  const listQuery = useQuery({
    queryKey: ['crm-leads', 'list', filters, page],
    queryFn: () => fetchCrmLeads({ ...filters, page, pageSize: 25 }),
    enabled: canRead && !authLoading && view === 'list',
    placeholderData: keepPreviousData,
  });
  const boardQuery = useQuery({
    queryKey: ['crm-leads', 'board', filters],
    queryFn: () => fetchCrmLeadBoard({ ...filters, pageSize: 25 }),
    enabled: canRead && !authLoading && view === 'kanban',
    placeholderData: keepPreviousData,
  });
  const [extraCards, setExtraCards] = useState<Partial<Record<CrmLeadStage, LeadView[]>>>({});
  const filterKey = JSON.stringify(filters);
  const seenFilter = useRef(filterKey);
  if (seenFilter.current !== filterKey) {
    seenFilter.current = filterKey;
    setExtraCards({});
  }
  const searchPage = useRef(search);
  useEffect(() => {
    if (searchPage.current === search) return;
    searchPage.current = search;
    patchQuery({ page: null });
  }, [patchQuery, search]);

  useEffect(() => {
    if (!drawer) return undefined;
    return lockPageScroll();
  }, [drawer]);

  useEffect(() => {
    setDetailTab('general');
  }, [selectedId]);

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
      setFormError(null);
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
      const message = error instanceof Error ? error.message : '';
      setFormError(message && !message.startsWith('Request failed') ? message : saveFailedMessage(locale === 'tr'));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: CrmLeadWrite }) => updateCrmLead(id, payload),
    onSuccess: async () => {
      setFormError(null);
      setDrawer('detail');
      await invalidate();
      showToast(t.updatedOk);
    },
    onError: (error) => {
      const message = error instanceof Error ? error.message : '';
      setFormError(message && !message.startsWith('Request failed') ? message : saveFailedMessage(locale === 'tr'));
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
      showToast(saveFailedMessage(locale === 'tr'));
    },
  });

  const data = view === 'list' ? listQuery.data : boardQuery.data;
  const listItems = useMemo(() => (listQuery.data?.items ?? []) as LeadView[], [listQuery.data?.items]);
  const boardColumns = useMemo(() => boardQuery.data?.columns ?? [], [boardQuery.data?.columns]);
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
  const grouped = useMemo(() => {
    const buckets = emptyCrmLeadStageBuckets<LeadView>();
    for (const column of boardColumns) {
      const extra = extraCards[column.stage] ?? [];
      buckets[column.stage] = [...(column.items as LeadView[]), ...extra];
    }
    return buckets;
  }, [boardColumns, extraCards]);
  const items = view === 'list' ? listItems : STAGES.flatMap((column) => grouped[column]);
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
        ...(taskForm.reminder === 'none' ? { reminders: [] } : {}),
      });
    },
    onSuccess: async () => {
      setTaskForm(EMPTY_TASK_FORM);
      setTaskFormError(null);
      setTaskFormOpen(false);
      await invalidate();
      showToast(t.taskCreated);
    },
    onError: () => {
      setTaskFormError(saveFailedMessage(locale === 'tr'));
    },
  });

  const noteMutation = useMutation({
    mutationFn: async () => {
      const body = noteDraft.trim();
      const contactId = selected?.contact_id || selected?.converted_contact_id;
      if (!body || !contactId) throw new Error(t.save);
      return createNote({
        contact_id: contactId,
        entity_type: 'contact',
        entity_id: contactId,
        description: body,
        title: body.split('\n')[0]?.slice(0, 120),
      });
    },
    onSuccess: async () => {
      setNoteDraft('');
      await invalidate();
      showToast(t.noteSaved);
    },
    onError: () => {
      showToast(saveFailedMessage(locale === 'tr'));
    },
  });

  const sourceOptions = useMemo(() => {
    const live = (data?.sources ?? []).filter(Boolean);
    return live.length ? live : [...CREATE_SOURCES];
  }, [data?.sources]);

  const clearFilters = () => {
    setSearchDraft('');
    patchQuery({
      q: null,
      stage: null,
      page: null,
      source: null,
      project: null,
      owner: null,
      from: null,
      to: null,
      ingest: null,
      junk: null,
    });
  };

  const openCreate = (nextStage?: CrmLeadStage) => {
    const next = { ...EMPTY_FORM, stage: nextStage || 'yeni', owner_user_id: user?.id || '' };
    setForm(next);
    setFormBaseline(next);
    setProjectSearch('');
    setFormError(null);
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
    const nameParts = (item.full_name || '').trim().split(/\s+/);
    const nextForm: CrmLeadWrite = {
      full_name: item.full_name,
      first_name: nameParts[0] || '',
      last_name: nameParts.slice(1).join(' '),
      phone: item.phone ?? '',
      email: item.email ?? '',
      contact_id: item.contact_id ?? '',
      source: item.source ?? 'manual',
      campaign: item.campaign ?? '',
      project: item.project ?? '',
      project_id: item.project_id ?? '',
      phase_id: item.phase_id ?? '',
      inventory_asset_id: item.inventory_asset_id ?? '',
      owner_user_id: item.owner_user_id ?? '',
      notes: item.notes ?? '',
      stage: item.stage,
      investment_budget_amount: item.investment_budget_amount ?? '',
      investment_budget_currency: item.investment_budget_currency ?? 'USD',
    };
    setForm(nextForm);
    setFormBaseline(nextForm);
    setProjectSearch(item.project ?? '');
    setFormError(null);
    setDrawer('edit');
  };

  const submitForm = (confirm = false) => {
    setFormError(null);
    if (form.stage === 'unqualified' && !form.junk_reason) {
      setFormError(t.junkReasonRequired);
      return;
    }
    if (form.stage === 'unqualified' && form.junk_reason === 'other' && !(form.junk_reason_detail || '').trim()) {
      setFormError(t.junkReasonDetailRequired);
      return;
    }
    const composedName = [form.first_name, form.last_name].map((part) => part?.trim()).filter(Boolean).join(' ');
    const payload: CrmLeadWrite = {
      full_name: composedName || form.full_name?.trim() || undefined,
      first_name: form.first_name?.trim() || undefined,
      last_name: form.last_name?.trim() || undefined,
      phone: form.phone?.trim() || undefined,
      email: form.email?.trim() || undefined,
      contact_id: form.contact_id || null,
      address_line1: form.address_line1?.trim() || undefined,
      city: form.city?.trim() || undefined,
      state_province: form.state_province?.trim() || undefined,
      country: form.country?.trim() || undefined,
      language: form.language?.trim() || undefined,
      organization_name: form.organization_name?.trim() || undefined,
      job_title: form.job_title?.trim() || undefined,
      next_follow_up_at: form.next_follow_up_at ? new Date(form.next_follow_up_at).toISOString() : null,
      source: form.source || 'manual',
      campaign: form.campaign?.trim() || undefined,
      project: form.project?.trim() || undefined,
      project_id: form.project_id || null,
      phase_id: form.phase_id || null,
      inventory_asset_id: form.inventory_asset_id || null,
      owner_user_id: form.owner_user_id || null,
      notes: form.notes?.trim() || undefined,
      stage: drawer === 'create' ? 'yeni' : form.stage,
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
      const personId = conflict?.matches.find((match) => match.kind === 'person')?.id;
      convertMutation.mutate({ id: item.id, personId });
      return;
    }
    if (next === 'unqualified') {
      setJunkPending(item);
      return;
    }
    stageMutation.mutate({ id: item.id, next });
  };

  const activeQuery = view === 'list' ? listQuery : boardQuery;
  if (authLoading || (activeQuery.isLoading && !activeQuery.data)) {
    return <LoadingState />;
  }
  if (!canRead) {
    return <ErrorState title={t.title} message="No access" />;
  }
  if (activeQuery.isError) {
    return (
      <ErrorState
        title={t.loadErrorTitle}
        message={t.loadError}
        action={
          <Button type="button" size="sm" onClick={() => void listQuery.refetch()}>
            {t.retry}
          </Button>
        }
      />
    );
  }

  const unmatchedCount = kpis.unmatched + kpis.failed;
  const saving = createMutation.isPending || updateMutation.isPending || convertMutation.isPending;
  const leadFormDirty =
    (drawer === 'create' || drawer === 'edit') && JSON.stringify(form) !== JSON.stringify(formBaseline);
  const taskDraftDirty = taskFormOpen && Boolean(taskForm.title.trim() || taskForm.date || taskForm.time);
  const requestCloseDrawer = () => {
    if ((leadFormDirty || taskDraftDirty) && !confirmDiscardUnsaved(locale === 'tr')) return;
    setFormError(null);
    setDrawer(null);
  };
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
          <Link href={'/workspaces/crm/junk' as Route}>{t.junkView}</Link>
          <Link href={'/workspaces/crm/communication' as Route}>{t.messages}</Link>
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
            onClick={() => patchQuery({ stage: item.value, junk: null, page: null })}
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
          placeholder={t.searchPh}
        />
        <Select
          label={t.stage}
          value={stage}
          onChange={(event) => {
            const next = event.target.value;
            patchQuery(next === 'unqualified' ? { stage: next } : { stage: next, junk: null });
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
        <Select label={t.project} value={project} onChange={(event) => setProject(event.target.value)} data-testid="crm-leads-project-filter">
          <option value="">{t.any}</option>
          {membershipProjects.map((item) => (
            <option key={item.project_id || item.label} value={item.project_id || ''}>
              {item.label}
            </option>
          ))}
        </Select>
        {filterPhases.length > 0 ? (
          <Select label={locale === 'tr' ? 'Faz' : 'Phase'} value={phaseFilter} onChange={(event) => setPhaseFilter(event.target.value)} data-testid="crm-leads-phase-filter">
            <option value="">{locale === 'tr' ? 'Tümü' : 'All'}</option>
            {filterPhases.map((phase) => (
              <option key={phase.id} value={phase.id}>{phase.name}</option>
            ))}
          </Select>
        ) : null}
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
          {canCreate ? (
            <Button type="button" size="sm" data-testid="crm-leads-create" onClick={() => openCreate()}>
              {t.create}
            </Button>
          ) : null}
        </div>
      </section>

      {view === 'kanban' ? (
        <div className="crm-ops-kanban" data-testid="crm-leads-kanban">
          <div className="crm-ops-kanban__inner">
            <div className="crm-ops-kanban__header-row">
              {STAGES.map((column) => (
                <div key={column} className={`crm-ops-kanban__header-cell is-${column}`}>
                  <h3>
                    <span className="crm-ops-kanban__dot" aria-hidden />
                    {stageLabel(column, locale)}
                  </h3>
                  <span className="crm-ops-kanban__count">
                    {boardColumns.find((entry) => entry.stage === column)?.total ?? 0}
                  </span>
                </div>
              ))}
            </div>

            <div className="crm-ops-kanban__columns">
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
<div className="crm-ops-kanban__body">
                {(boardColumns.find((entry) => entry.stage === column)?.total ?? 0) === 0 ? (
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
                      canDrag={canUpdate && item.stage !== 'converted'}
                      onDragStart={() => setDraggingId(item.id)}
                      onDragEnd={() => setDraggingId(null)}
                      onOpen={() => openDetail(item)}
                    />
                  ))
                )}
                {grouped[column].length < (boardColumns.find((entry) => entry.stage === column)?.total ?? 0) ? (
                  <button
                    type="button"
                    className="crm-ops-col-add"
                    data-testid="crm-leads-column-more"
                    onClick={() => {
                      const loaded = grouped[column].length;
                      const nextPage = Math.floor(loaded / 25) + 1;
                      void fetchCrmLeadBoardCards({ ...filters, stage: column, page: nextPage, pageSize: 25 }).then((result) => {
                        setExtraCards((current) => {
                          const seen = new Set(grouped[column].map((row) => row.id));
                          const fresh = result.items.filter((row) => !seen.has(row.id)) as LeadView[];
                          return { ...current, [column]: [...(current[column] ?? []), ...fresh] };
                        });
                      });
                    }}
                  >
                    {t.more}
                  </button>
                ) : null}
              </div>
              {canCreate ? (
                <button type="button" className="crm-ops-col-add" data-testid="crm-leads-add-column" onClick={() => openCreate(column)}>
                  {t.addLead}
                </button>
              ) : null}
                </section>
              ))}
            </div>
          </div>
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
                        <td>{item.interest_label || item.project || t.none}</td>
                        <td>
                          {formatCrmInvestmentBudget(
                            item.investment_budget_amount,
                            item.investment_budget_currency,
                            locale,
                          )}
                        </td>
                        <td>{displayOwner(item.owner_name) || t.none}</td>
                        <td>{lastActivityLabel(item, locale, t.none)}</td>
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
          {(listQuery.data?.total ?? 0) > 0 ? (
            <div className="crm-ops-filtercard__actions" data-testid="crm-leads-pager">
              <Button type="button" variant="secondary" size="sm" disabled={page <= 1} onClick={() => patchQuery({ page: String(page - 1) })}>
                {t.previous}
              </Button>
              <span>
                {page} / {listQuery.data?.pages ?? 1}
              </span>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={page >= (listQuery.data?.pages ?? 1)}
                onClick={() => patchQuery({ page: String(page + 1) })}
              >
                {t.next}
              </Button>
            </div>
          ) : null}
        </div>
      )}

      {view === 'kanban' && (boardQuery.data?.total ?? 0) === 0 ? (
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
          <button type="button" className="crm-ops-drawer-backdrop" aria-label={t.close} onClick={requestCloseDrawer} />
          <aside className="crm-ops-drawer" role="dialog" data-testid="crm-leads-drawer">
            <div className="crm-ops-drawer__head">
              <div className="crm-ops-drawer__identity">
                <div className="crm-ops-drawer__title-row">
                  <h3>
                    {drawer === 'create'
                      ? t.create
                      : drawer === 'edit'
                        ? t.edit
                        : (selected ? crmLeadDisplayName(selected) : t.title)}
                  </h3>
                  {selected && drawer !== 'create' && drawer !== 'edit' ? (
                    <OsOverflowMenu
                      label={t.actions}
                      items={[
                        selected.converted_contact_id || selected.contact_id
                          ? {
                              id: 'open-person',
                              label: t.openPerson,
                              testId: 'crm-lead-menu-open-person',
                              onSelect: () =>
                                openContact((selected.converted_contact_id || selected.contact_id) as string),
                            }
                          : { id: 'open-person', hidden: true },
                        canUpdate && selected.stage !== 'converted'
                          ? {
                              id: 'edit',
                              label: t.edit,
                              testId: 'crm-leads-edit',
                              onSelect: () => openEdit(selected),
                            }
                          : { id: 'edit', hidden: true },
                        {
                          id: 'matches',
                          label: t.matches,
                          href: `/workspaces/crm/matches?q=${encodeURIComponent(crmLeadDisplayName(selected))}` as Route,
                        },
                        {
                          id: 'agreements',
                          label: t.agreements,
                          href: `/workspaces/crm/agreements?q=${encodeURIComponent(crmLeadDisplayName(selected))}` as Route,
                        },
                        { id: 'divider', divider: true },
                        canArchive
                          ? {
                              id: 'remove',
                              label: locale === 'tr' ? 'Pipeline’dan Kaldır' : 'Remove from Pipeline',
                              destructive: true,
                              testId: 'crm-lead-menu-remove',
                              onSelect: () => {
                                const confirmed = window.confirm(
                                  locale === 'tr'
                                    ? 'Bu kaydı Pipeline’dan kaldırmak istediğinize emin misiniz?'
                                    : 'Are you sure you want to remove this record from the Pipeline?',
                                );
                                if (confirmed) archiveMutation.mutate(selected.id);
                              },
                            }
                          : { id: 'remove', hidden: true },
                      ]}
                    />
                  ) : null}
                </div>
                {selected && drawer !== 'create' && drawer !== 'edit' ? (
                  <p className="crm-ops-drawer__meta">
                    {[
                      sourceLabel(selected.source, locale),
                      selected.interest_label || selected.project,
                      selected.phase_name,
                      selected.unit_number,
                      displayOwner(selected.owner_name),
                      stageLabel(selected.stage, locale),
                    ].filter(Boolean).join(' · ')}
                  </p>
                ) : null}
              </div>
              <button type="button" className="crm-ops-link" onClick={requestCloseDrawer}>
                {t.close}
              </button>
            </div>
            {selected && drawer !== 'create' && drawer !== 'edit' ? (
              <div className="crm-lead-stage" data-testid="crm-lead-stage-control">
                <span className={`crm-ops-badge is-${selected.stage} is-current`}>{stageLabel(selected.stage, locale)}</span>
                {canUpdate && selected.stage !== 'converted' ? (
                  <>
                    <div className="crm-lead-stage__strip" role="listbox" aria-label={t.stage}>
                      {STAGES.map((stage) => (
                        <button
                          key={stage}
                          type="button"
                          role="option"
                          aria-selected={stage === selected.stage}
                          className={stage === selected.stage ? 'is-current' : ''}
                          disabled={convertMutation.isPending || stageMutation.isPending}
                          onClick={() => handleStageMove(selected, stage)}
                        >
                          {stageLabel(stage, locale)}
                        </button>
                      ))}
                    </div>
                    <div className="crm-lead-stage__menu">
                      <Select
                        label={t.stage}
                        value={selected.stage}
                        disabled={convertMutation.isPending || stageMutation.isPending}
                        onChange={(event) => handleStageMove(selected, event.target.value as CrmLeadStage)}
                      >
                        {STAGES.map((stage) => (
                          <option key={stage} value={stage}>
                            {stageLabel(stage, locale)}
                          </option>
                        ))}
                      </Select>
                    </div>
                  </>
                ) : null}
              </div>
            ) : null}
            <div className="crm-ops-drawer__body">
              {drawer === 'create' || drawer === 'edit' ? (
                <form
                  className="crm-ops-form"
                  onSubmit={(event) => {
                    event.preventDefault();
                    submitForm(false);
                  }}
                >
                  {drawer === 'create' ? (
                    <CrmContactPicker
                      selectedId={form.contact_id || ''}
                      selectedName={form.full_name || ''}
                      onSelect={(contact) => {
                        if (!contact) {
                          setForm((current) => ({ ...current, contact_id: '' }));
                          return;
                        }
                        const parts = contact.name.trim().split(/\s+/);
                        setForm((current) => ({
                          ...current,
                          contact_id: contact.id,
                          full_name: contact.name,
                          first_name: parts[0] || '',
                          last_name: parts.slice(1).join(' '),
                          phone: contact.phone || current.phone,
                          email: contact.email || current.email,
                        }));
                      }}
                    />
                  ) : null}
                  <Input label="Ad" value={form.first_name ?? ''} onChange={(event) => setForm((current) => ({ ...current, first_name: event.target.value }))} />
                  <Input label="Soyad" value={form.last_name ?? ''} onChange={(event) => setForm((current) => ({ ...current, last_name: event.target.value }))} />
                  <Input label={t.phone} value={form.phone ?? ''} onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))} />
                  <Input label={t.email} value={form.email ?? ''} onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))} />
                  <Input label="Adres" value={form.address_line1 ?? ''} onChange={(event) => setForm((current) => ({ ...current, address_line1: event.target.value }))} />
                  <Input label="Şehir" value={form.city ?? ''} onChange={(event) => setForm((current) => ({ ...current, city: event.target.value }))} />
                  <Input label="Bölge / Eyalet" value={form.state_province ?? ''} onChange={(event) => setForm((current) => ({ ...current, state_province: event.target.value }))} />
                  <Input label="Ülke" value={form.country ?? ''} onChange={(event) => setForm((current) => ({ ...current, country: event.target.value }))} />
                  <Select label="Dil" value={form.language ?? ''} onChange={(event) => setForm((current) => ({ ...current, language: event.target.value }))}>
                    <option value="">Seçin</option>
                    <option value="tr">Türkçe</option>
                    <option value="en">English</option>
                  </Select>
                  <Input label="Şirket" value={form.organization_name ?? ''} onChange={(event) => setForm((current) => ({ ...current, organization_name: event.target.value }))} />
                  <Input label="Pozisyon" value={form.job_title ?? ''} onChange={(event) => setForm((current) => ({ ...current, job_title: event.target.value }))} />
                  <Select
                    label={t.sourceField}
                    value={form.source ?? 'manual'}
                    onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
                  >
                    {crmSourceChoices(form.source).map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label || crmSourceLabel(item.value)}
                      </option>
                    ))}
                  </Select>
                  <Input label="Sonraki Takip" type="datetime-local" value={form.next_follow_up_at ?? ''} onChange={(event) => setForm((current) => ({ ...current, next_follow_up_at: event.target.value }))} />
                  <Input
                    label={locale === 'tr' ? 'Proje ara' : 'Search projects'}
                    value={projectSearch}
                    onChange={(event) => setProjectSearch(event.target.value)}
                    placeholder={locale === 'tr' ? 'Proje adı' : 'Project name'}
                  />
                  <Select
                    label={t.interestedProject}
                    value={form.project_id || ''}
                    onChange={(event) => {
                      const projectId = event.target.value;
                      const match = (projectsQuery.data?.items ?? []).find((item) => item.id === projectId);
                      setForm((current) => ({
                        ...current,
                        project_id: projectId,
                        project: match?.project_name || (projectId ? current.project : ''),
                        phase_id: '',
                        inventory_asset_id: '',
                      }));
                      if (match) setProjectSearch(match.project_name);
                    }}
                  >
                    <option value="">{form.project && !form.project_id ? form.project : locale === 'tr' ? 'Seçin' : 'Select'}</option>
                    {(projectsQuery.data?.items ?? []).map((item) => (
                      <option key={item.id} value={item.id}>{item.project_name}</option>
                    ))}
                  </Select>
                  {leadUsesPhases && !phaseFieldVisible(leadPhasesQuery.data) ? (
                    <p data-testid="phased-project-empty">Bu proje fazlı olarak tanımlı. Önce Projeler &gt; Fazlar bölümünden faz oluşturun.</p>
                  ) : null}
                  {leadPhaseReady ? (
                    <Select
                      label={locale === 'tr' ? 'Faz' : 'Phase'}
                      value={form.phase_id || ''}
                      onChange={(event) =>
                        setForm((current) => ({
                          ...current,
                          phase_id: event.target.value,
                          inventory_asset_id: '',
                        }))
                      }
                    >
                      <option value="">{locale === 'tr' ? 'Seçin' : 'Select'}</option>
                      {(leadPhasesQuery.data ?? []).map((phase) => (
                        <option key={phase.id} value={phase.id}>{phase.name}</option>
                      ))}
                    </Select>
                  ) : null}
                  {form.project_id && (!leadUsesPhases || (leadPhaseReady && form.phase_id)) ? (
                    <>
                      <Select
                        label={locale === 'tr' ? 'Ünite' : 'Unit'}
                        value={form.inventory_asset_id || ''}
                        onChange={(event) => {
                          const asset = (leadUnitsQuery.data?.items ?? []).find((item) => item.id === event.target.value);
                          setForm((current) => ({
                            ...current,
                            inventory_asset_id: event.target.value,
                            phase_id: asset?.phase_id || current.phase_id,
                          }));
                        }}
                      >
                        <option value="">{locale === 'tr' ? 'Seçin' : 'Select'}</option>
                        {(leadUnitsQuery.data?.items ?? []).filter((item) => !leadUsesPhases || item.phase_id === form.phase_id).map((item) => {
                          const selectedPhaseName = (leadPhasesQuery.data ?? []).find((phase) => phase.id === form.phase_id)?.name || '';
                          const identifier = unitIdentifier(item.display_id);
                          return (
                            <option key={item.id} value={item.id}>
                              {selectedPhaseName ? `${selectedPhaseName} · ${identifier}` : identifier}
                            </option>
                          );
                        })}
                      </Select>
                      {leadPhaseReady && form.phase_id && (leadUnitsQuery.data?.items ?? []).filter((item) => item.phase_id === form.phase_id).length === 0 ? (
                        <p data-testid="phase-units-empty">{locale === 'tr' ? 'Bu faza henüz ünite atanmadı.' : 'No units are assigned to this phase yet.'}</p>
                      ) : null}
                    </>
                  ) : null}
                  <Select
                    label={t.owner}
                    value={form.owner_user_id ?? ''}
                    onChange={(event) => setForm((current) => ({ ...current, owner_user_id: event.target.value }))}
                  >
                    <option value="">{t.unassigned}</option>
                    {form.owner_user_id && !(activeUsersQuery.data?.items ?? []).some((item) => item.id === form.owner_user_id) ? (
                      <option value={form.owner_user_id}>
                        {(form.owner_user_id === user?.id ? displayOwner(user.full_name) : displayOwner(selected?.owner_name)) || form.owner_user_id}
                      </option>
                    ) : null}
                    {(activeUsersQuery.data?.items ?? []).map((item) => (
                      <option key={item.id} value={item.id}>
                        {displayOwner(item.full_name) || item.full_name}
                      </option>
                    ))}
                  </Select>
                  {drawer === 'edit' ? (
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
                    label={t.purchaseBudget}
                    value={form.investment_budget_amount ?? ''}
                    onChange={(event) =>
                      setForm((current) => ({ ...current, investment_budget_amount: event.target.value }))
                    }
                    placeholder={t.budgetPh}
                  />
                  <TextArea
                    label={t.notesField}
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
                  {formError ? (
                    <p className="crm-ops-form__error" role="alert" data-testid="crm-leads-form-error">
                      {formError}
                    </p>
                  ) : null}
                  <Button type="submit" size="sm" disabled={saving}>
                    {saving ? t.saving : t.save}
                  </Button>
                </form>
              ) : selected ? (
                <>
                  <div className="crm-lead-tabs" role="tablist">
                    {([
                      ['general', t.generalTab],
                      ['tasks', t.tasksTab],
                      ['notes', t.notesTab],
                      ['history', t.historyTab],
                    ] as const).map(([id, label]) => (
                      <button
                        key={id}
                        type="button"
                        role="tab"
                        aria-selected={detailTab === id}
                        className={detailTab === id ? 'is-current' : ''}
                        onClick={() => setDetailTab(id)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                  {detailTab === 'tasks' && taskFormOpen ? (
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
                      <Select
                        label={t.taskReminder}
                        value={taskForm.reminder}
                        onChange={(event) => setTaskForm((current) => ({ ...current, reminder: event.target.value }))}
                      >
                        <option value="10">{t.taskReminder10}</option>
                        <option value="none">{t.taskReminderNone}</option>
                      </Select>
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
                    tab={detailTab}
                  />
                  {detailTab === 'notes' && canCreate && (selected.contact_id || selected.converted_contact_id) ? (
                    <form
                      className="crm-ops-taskform"
                      data-testid="crm-lead-note-form"
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (!noteDraft.trim() || noteMutation.isPending) return;
                        noteMutation.mutate();
                      }}
                    >
                      <TextArea
                        label={t.notePlaceholder}
                        value={noteDraft}
                        rows={3}
                        onChange={(event) => setNoteDraft(event.target.value)}
                      />
                      <Button type="submit" size="sm" disabled={!noteDraft.trim() || noteMutation.isPending}>
                        {t.addNote}
                      </Button>
                    </form>
                  ) : null}
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
                  {selected ? (
                    <Button
                      type="button"
                      size="sm"
                      disabled={convertMutation.isPending}
                      onClick={() => {
                        const personId = conflict.matches.find((item) => item.kind === 'person')?.id;
                        convertMutation.mutate({ id: selected.id, personId });
                      }}
                    >
                      {convertMutation.isPending ? t.converting : t.reusePerson}
                    </Button>
                  ) : null}
                </div>
              ) : null}
              {emailComposeOpen && selected?.email && drawer !== 'create' ? (
                <EmailSendComposer
                  mode="new"
                  contactId={selected.contact_id || selected.converted_contact_id}
                  leadId={selected.id}
                  defaultTo={selected.email}
                  defaultSubject=""
                  onSent={() => setEmailComposeOpen(false)}
                />
              ) : null}
              {whatsappComposeOpen && selected?.phone && drawer !== 'create' ? (
                <WhatsAppSendComposer
                  mode="new"
                  contactId={selected.contact_id || selected.converted_contact_id}
                  leadId={selected.id}
                  phones={[selected.phone]}
                  onSent={() => setWhatsappComposeOpen(false)}
                />
              ) : null}
            </div>
            {selected && drawer !== 'create' && drawer !== 'edit' ? (
              <div className="crm-ops-drawer__actions crm-ops-drawer__quick" data-testid="crm-lead-actions">
                {canSendEmail && selected.email ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setEmailComposeOpen((open) => !open);
                      setWhatsappComposeOpen(false);
                    }}
                  >
                    <IhIcon name="mail" size={14} /> {t.emailAction}
                  </Button>
                ) : null}
                {canSendEmail && selected.phone ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setWhatsappComposeOpen((open) => !open);
                      setEmailComposeOpen(false);
                    }}
                  >
                    <IhIcon name="phone" size={14} /> {t.whatsappAction}
                  </Button>
                ) : null}
                {canAddTask ? (
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => {
                      setDetailTab('tasks');
                      setTaskFormOpen(true);
                      setTaskFormError(null);
                    }}
                  >
                    <IhIcon name="plus" size={14} /> {t.addTask}
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
      {item.interest_label || item.project ? <small>{item.interest_label || item.project}</small> : null}
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
  tab,
}: {
  item: LeadView;
  locale: 'tr' | 'en';
  t: (typeof COPY)['tr'];
  tab: DetailTab;
}) {
  const referrer = referrerLabel(item);
  const reason = unqualifiedReason(item, locale);
  const activity = item.activity ?? [];
  if (tab === 'tasks') {
    return (
      <>
        <h4>{t.tasks}</h4>
        <p className="crm-ops-muted">{t.taskReminder10}</p>
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
      </>
    );
  }
  if (tab === 'notes') {
    const entries = item.note_entries?.length
      ? item.note_entries
      : item.notes
        ? [{ id: item.id, body: item.notes, author_name: item.owner_name, created_at: item.created_at }]
        : [];
    return (
      <>
        <h4>{t.notesTab}</h4>
        {entries.length === 0 ? <p className="crm-ops-muted">{t.none}</p> : null}
        <ul className="crm-ops-history" data-testid="crm-lead-notes">
          {entries.map((entry) => (
            <li key={entry.id}>
              {entry.body}
              <small>
                {entry.author_name || t.none} · {formatWhen(entry.created_at, locale)}
              </small>
            </li>
          ))}
        </ul>
      </>
    );
  }
  if (tab === 'history') {
    return (
      <>
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
      </>
    );
  }
  return (
    <>
      <dl className="crm-ops-kv">
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
        <dd>{item.interest_label || item.project || t.none}</dd>
        {item.phase_name ? (
          <>
            <dt>{locale === 'tr' ? 'Faz' : 'Phase'}</dt>
            <dd>{item.phase_name}</dd>
          </>
        ) : null}
        {item.unit_number ? (
          <>
            <dt>{locale === 'tr' ? 'Ünite' : 'Unit'}</dt>
            <dd>{item.unit_number}</dd>
          </>
        ) : null}
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
