'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, Input, LoadingState, Select, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { fetchUsers, hasPermission, type UserRecord } from '@/lib/api/auth';
import { fetchDocumentsByEntity, linkDocument, type Document } from '@/lib/api/documents';
import { DocumentGallery, dedupeGalleryDocuments } from '@/workspaces/crm/contact-card/document-gallery';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { completeTask, createActivity, createFollowUp, createMeeting, createTask, updateActivity } from '@/workspaces/crm/api/activities';
import {
  assignContactOwner,
  fetchContactTimeline,
  fetchJunkReasons,
  updateContact,
  type ContactTimelineEntry,
} from '@/workspaces/crm/api/contacts';
import {
  assignContactTag,
  fetchCrmTags,
  removeContactTag,
} from '@/workspaces/crm/api/crm';
import { notifyContactUpdated, useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { PilotHistoryStream, type PilotHistoryFilter } from '@/workspaces/crm/contact-card/history-stream';
import { taskStatusLabel } from '@/workspaces/crm/contact-card/history-html';
import { UnitHistoryInline } from '@/workspaces/crm/contact-card/unit-history';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';
import { CRM_CONTACT_TYPES, type CrmContactType, type CrmPurchaseSummary } from '@/workspaces/crm/types';

import '@/app/workspaces/crm/contacts/_components/ds/contacts-ds.css';
import './contact-card.css';

const NOTE_TYPES = [
  { value: 'note', label: 'Yorum' },
  { value: 'phone_call', label: 'Arama' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'E-posta' },
  { value: 'meeting', label: 'Toplantı' },
] as const;

const TASK_KINDS = [
  { value: 'phone_call', label: 'Arama' },
  { value: 'email', label: 'E-posta' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'meeting', label: 'Toplantı' },
  { value: 'proposal', label: 'Teklif takibi' },
  { value: 'task', label: 'Genel takip' },
] as const;

const TASK_STATUSES = [
  { value: 'not_started', label: 'Başlamadı' },
  { value: 'in_progress', label: 'Devam ediyor' },
  { value: 'waiting', label: 'Beklemede' },
  { value: 'completed', label: 'Tamamlandı' },
] as const;

const ROLE_LABELS: Record<string, string> = {
  investor: 'Yatırımcı',
  prospect: 'Aday',
  buyer: 'Alıcı',
  broker: 'Acenta',
  realtor: 'Emlakçı',
  partner: 'Partner',
  vendor: 'Tedarikçi',
  contractor: 'Yüklenici',
  attorney: 'Avukat',
  lender: 'Finans',
  property_manager: 'Yönetici',
  architect: 'Mimar',
  consultant: 'Danışman',
  media_contact: 'Medya',
  government_contact: 'Kamu',
  internal_team: 'İç ekip',
};

const SOURCE_RULES: Array<{ match: RegExp; label: string }> = [
  { match: /instagram/i, label: 'Instagram Lead' },
  { match: /facebook|meta/i, label: 'Facebook Lead' },
  { match: /whatsapp|\bwa\b/i, label: 'WhatsApp' },
  { match: /rc[_\s-]?generator|acenta|agent|broker|referral|referans/i, label: 'Acenta' },
  { match: /web\s*form|website|web\s*site|crm form|webform|^web$|genel form/i, label: 'Web Sitesi' },
  { match: /manuel|manual|^os$/i, label: 'Manuel' },
];

type Panel = 'edit' | 'note' | 'task' | 'assign' | 'more' | null;

const PERSON_TABS = [
  { id: 'overview', label: 'Genel' },
  { id: 'purchases', label: 'Satın Almalar' },
  { id: 'history', label: 'İletişim' },
  { id: 'documents', label: 'Belgeler' },
  { id: 'tasks', label: 'Görevler' },
] as const;

type PersonTab = (typeof PERSON_TABS)[number]['id'];

function formatLeadSource(raw?: string | null): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  const mapped = SOURCE_RULES.find((rule) => rule.match.test(value))?.label;
  if (mapped) return mapped;
  if (/^[A-Z0-9_]+$/.test(value)) return null;
  return value;
}

function roleLabel(type: string) {
  return ROLE_LABELS[type] || type;
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  return ((parts[0][0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] || '' : '')).toUpperCase();
}

function phoneDigits(value?: string | null) {
  return (value || '').replace(/\D/g, '');
}

function formatShortDate(iso: string | null | undefined, locale: string) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10);
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' });
}

function formatDateTime(iso: string | null | undefined, locale: string) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString(locale, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function relativeLabel(iso: string | null | undefined, locale: string) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const diff = Date.now() - date.getTime();
  const minutes = Math.round(diff / 60000);
  if (Math.abs(minutes) < 1) return 'Az önce';
  if (Math.abs(minutes) < 60) return `${Math.abs(minutes)} dk ${minutes > 0 ? 'önce' : 'sonra'}`;
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return `${Math.abs(hours)} saat ${hours > 0 ? 'önce' : 'sonra'}`;
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 45) return `${Math.abs(days)} gün ${days > 0 ? 'önce' : 'sonra'}`;
  return formatShortDate(iso, locale);
}

function commLabel(type: string | null | undefined) {
  if (type === 'email') return 'E-posta';
  if (type === 'whatsapp') return 'WhatsApp';
  if (type === 'phone_call') return 'Arama';
  if (type === 'meeting' || type === 'zoom_meeting' || type === 'teams_meeting') return 'Toplantı';
  if (type === 'sms') return 'Mesaj';
  return null;
}

function taskKindLabel(type: string, meta?: Record<string, unknown> | null) {
  const kind = String(meta?.follow_up_kind || type || '');
  return TASK_KINDS.find((item) => item.value === kind)?.label
    || commLabel(kind)
    || (kind === 'follow_up' || kind === 'reminder' ? 'Genel takip' : kind || 'Genel takip');
}

function crmStatusLabel(raw?: string | null): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  if (/deal\s*won|^won$|^kazan[ıi]ld[ıi]$/i.test(value)) return 'Satın Alındı';
  if (/^completed$|^tamamland[ıi]$/i.test(value)) return 'Tamamlandı';
  if (/^active$|^aktif$/i.test(value)) return 'Aktif';
  if (/^cancelled$|^canceled$|^iptal$/i.test(value)) return 'İptal';
  if (/^lost$|^kaybedildi$/i.test(value)) return 'Kaybedildi';
  if (/^[A-Z0-9_:]+$/.test(value)) return null;
  return value;
}

function purchaseStatusLabel(purchase: CrmPurchaseSummary) {
  if (purchase.is_historical_unit_change) return 'Daire değişikliği';
  return crmStatusLabel(purchase.stage) || crmStatusLabel(purchase.status);
}

function investmentRowTitle(purchase: CrmPurchaseSummary) {
  if (purchase.project_group === 'reit') return purchase.project_label || 'REIT';
  return purchase.project_label;
}

function isFollowUpEntry(entry: ContactTimelineEntry) {
  const type = entry.activity_type;
  if (type === 'task' || type === 'follow_up' || type === 'reminder' || type === 'meeting') return true;
  if ((type === 'phone_call' || type === 'email' || type === 'whatsapp') && (entry.metadata?.due_date || entry.status === 'planned')) {
    return true;
  }
  return false;
}

function PurchaseHistoryRow({
  purchase,
  onOpen,
  identityTestId,
}: {
  purchase: CrmPurchaseSummary;
  onOpen: (agreementId: string) => void;
  identityTestId?: string;
}) {
  const isReit = purchase.project_group === 'reit';
  const historical = Boolean(purchase.is_historical_unit_change);
  const status = purchaseStatusLabel(purchase);
  const amount = purchase.amount_label || purchase.amount || null;
  const unit = isReit
    ? null
    : historical
      ? [purchase.unit_number || purchase.original_unit, purchase.final_unit ? `→ ${purchase.final_unit}` : null]
          .filter(Boolean)
          .join(' ')
      : purchase.unit_number;
  return (
    <tr
      className={historical ? 'is-historical' : 'is-current-purchase'}
      data-testid={`purchase-row-${purchase.bitrix_deal_id || purchase.agreement_id}`}
      role="button"
      tabIndex={0}
      onClick={() => onOpen(purchase.agreement_id)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          onOpen(purchase.agreement_id);
        }
      }}
    >
      <td>
        <strong data-testid={identityTestId}>{investmentRowTitle(purchase)}</strong>
        {!historical && purchase.unit_history && purchase.unit_history.length > 1 ? (
          <UnitHistoryInline steps={purchase.unit_history} />
        ) : null}
        {purchase.hemen_kira ? <span className="crm-purchase-list__unit">Hemen Kira</span> : null}
      </td>
      <td>{unit || '—'}</td>
      <td>{amount || '—'}</td>
      <td>{status || '—'}</td>
    </tr>
  );
}

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  if (!value?.trim()) return null;
  return (
    <div className="crm-person-info__row">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function toIso(local: string): string {
  return new Date(local).toISOString();
}

function nowLocal(): string {
  return toLocalInput(new Date().toISOString());
}

function friendlyError(message: string): string {
  if (message.includes('invalid_phone')) return 'Telefon numarası geçersiz.';
  if (message.includes('invalid_email')) return 'E-posta adresi geçersiz.';
  return message;
}

function splitList(value: string): string[] {
  return value
    .split(/[,;\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function requestedPersonTab(): PersonTab {
  if (typeof window === 'undefined') return 'overview';
  const value = new URLSearchParams(window.location.search).get('tab');
  if (value === 'whatsapp') return 'history';
  return PERSON_TABS.some((item) => item.id === value) ? (value as PersonTab) : 'overview';
}

function requestedHistoryFilter(): PilotHistoryFilter {
  if (typeof window === 'undefined') return 'all';
  return new URLSearchParams(window.location.search).get('tab') === 'whatsapp' ? 'whatsapp' : 'all';
}

export function UnifiedContactCard({
  contactId,
  variant = 'page',
}: {
  contactId: string;
  variant?: 'page' | 'drawer';
}) {
  const locale = useLocale();
  const queryClient = useQueryClient();
  const router = useRouter();
  const { openPurchase } = useContactCard();
  const { authLoading, canRead, has, user } = useCrmAccess();
  const canUpdate = has('update');
  const canViewDocuments = Boolean(user && hasPermission(user, 'documents', 'view'));
  const canLinkDocuments = Boolean(user && hasPermission(user, 'documents', 'update'));
  const query = useQuery({
    ...contactQueries.detail(contactId),
    enabled: !authLoading && canRead,
  });
  const timelineQuery = useQuery({
    queryKey: ['crm', 'contacts', 'timeline', contactId],
    queryFn: () => fetchContactTimeline(contactId),
    enabled: !authLoading && canRead,
  });
  const reasonsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'junk-reasons'],
    queryFn: fetchJunkReasons,
    enabled: !authLoading && canRead,
  });
  const usersQuery = useQuery({
    queryKey: ['users', 'crm-assign'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canUpdate,
  });
  const tagsQuery = useQuery({
    queryKey: ['crm', 'tags', { status: 'active' }],
    queryFn: () => fetchCrmTags({ status: 'active' }),
    enabled: !authLoading && canRead,
  });
  const documentsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'documents', contactId],
    queryFn: async () => {
      const [crmDocs, contactDocs] = await Promise.all([
        fetchDocumentsByEntity('crm_contact', contactId, { includeHidden: true, pageSize: 100 }).catch(() => ({
          items: [] as Document[],
        })),
        fetchDocumentsByEntity('contact', contactId, { includeHidden: true, pageSize: 100 }).catch(() => ({
          items: [] as Document[],
        })),
      ]);
      return dedupeGalleryDocuments([...crmDocs.items, ...contactDocs.items]);
    },
    enabled: !authLoading && canRead && canViewDocuments,
  });

  const [panel, setPanel] = useState<Panel>(null);
  const [error, setError] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [phone, setPhone] = useState('');
  const [extraPhones, setExtraPhones] = useState('');
  const [email, setEmail] = useState('');
  const [extraEmails, setExtraEmails] = useState('');
  const [secondEmail, setSecondEmail] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [region, setRegion] = useState('');
  const [source, setSource] = useState('');
  const [notes, setNotes] = useState('');
  const [company, setCompany] = useState('');
  const [position, setPosition] = useState('');
  const [statusValue, setStatusValue] = useState<'active' | 'archived'>('active');
  const [junkReason, setJunkReason] = useState('');
  const [roles, setRoles] = useState<CrmContactType[]>([]);
  const [ownerId, setOwnerId] = useState('');
  const [followUpAt, setFollowUpAt] = useState('');
  const [note, setNote] = useState('');
  const [noteType, setNoteType] = useState<(typeof NOTE_TYPES)[number]['value']>('note');
  const [noteAt, setNoteAt] = useState(nowLocal);
  const [noteNeedsFollowUp, setNoteNeedsFollowUp] = useState(false);
  const [noteFollowUpAt, setNoteFollowUpAt] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskAssignee, setTaskAssignee] = useState('');
  const [taskDue, setTaskDue] = useState('');
  const [taskStatus, setTaskStatus] = useState<(typeof TASK_STATUSES)[number]['value']>('not_started');
  const [taskKind, setTaskKind] = useState<(typeof TASK_KINDS)[number]['value']>('task');
  const [linkDocumentId, setLinkDocumentId] = useState('');
  const [tab, setTab] = useState<PersonTab>('overview');
  const [historyFilter, setHistoryFilter] = useState<PilotHistoryFilter>('all');
  const [rescheduleId, setRescheduleId] = useState<string | null>(null);
  const [rescheduleAt, setRescheduleAt] = useState('');
  const contact = query.data;
  const referrerQuery = useQuery({
    ...contactQueries.detail(contact?.referred_by_contact_id || ''),
    enabled: !authLoading && canRead && Boolean(contact?.referred_by_contact_id),
  });

  useEffect(() => {
    setTab(requestedPersonTab());
    setHistoryFilter(requestedHistoryFilter());
  }, [contactId]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const purchase = new URLSearchParams(window.location.search).get('purchase');
    if (purchase) {
      router.replace(salesDetailUrl(contactId, purchase));
    }
  }, [contactId, router]);

  useEffect(() => {
    if (!contact) return;
    setDisplayName(contact.display_name);
    setPhone(contact.primary_phone ?? '');
    setExtraPhones((contact.secondary_phones ?? []).join(', '));
    setEmail(contact.primary_email ?? '');
    setSecondEmail((contact.secondary_emails ?? [])[0] ?? '');
    setExtraEmails((contact.secondary_emails ?? []).slice(1).join(', '));
    setAddress(contact.address_line1 ?? '');
    setCity(contact.city ?? '');
    setRegion(contact.state_province ?? '');
    setSource(contact.source ?? contact.bitrix_source_channel ?? '');
    setNotes(contact.notes ?? '');
    setCompany(contact.organization_name ?? '');
    setPosition(contact.job_title ?? '');
    setStatusValue(contact.status === 'archived' ? 'archived' : 'active');
    setJunkReason(contact.junk_reason ?? '');
    setRoles(contact.contact_types.length ? contact.contact_types : [contact.contact_type]);
    setOwnerId(contact.owner_user_id ?? '');
    setFollowUpAt(toLocalInput(contact.next_follow_up_at));
    setTaskAssignee(contact.owner_user_id ?? user?.id ?? '');
  }, [contact, user?.id]);

  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: contactQueryKeys.detail(contactId) }),
      queryClient.invalidateQueries({ queryKey: ['crm', 'contacts', 'timeline', contactId] }),
      queryClient.invalidateQueries({ queryKey: contactQueryKeys.all }),
      queryClient.invalidateQueries({ queryKey: ['crm', 'contacts', 'documents', contactId] }),
      queryClient.invalidateQueries({ queryKey: ['crm', 'activities'] }),
      queryClient.invalidateQueries({ queryKey: ['crm', 'tasks'] }),
      queryClient.invalidateQueries({ queryKey: ['crm', 'calendar'] }),
      queryClient.invalidateQueries({ queryKey: ['crm', 'tags'] }),
    ]);
    notifyContactUpdated(contactId);
  };

  const actionMutation = useMutation({
    mutationFn: async (work: () => Promise<unknown>) => work(),
    onSuccess: () => {
      setError(null);
      void refresh();
    },
    onError: (err: Error) => setError(friendlyError(err.message)),
  });

  const users: UserRecord[] = usersQuery.data?.items ?? [];
  const timeline = useMemo(
    () => [...(timelineQuery.data?.items ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at)),
    [timelineQuery.data?.items],
  );
  const followUpEntries = useMemo(() => timeline.filter(isFollowUpEntry), [timeline]);
  const commEntries = useMemo(
    () => timeline.filter((entry) => ['email', 'whatsapp', 'phone_call', 'meeting', 'sms', 'comment', 'note'].includes(entry.activity_type)),
    [timeline],
  );

  if (authLoading || query.isLoading) return <LoadingState label="Loading…" />;
  if (!canRead) return <EmptyState title="CRM" description="Access denied" />;
  if (query.isError || !contact) {
    return <ErrorState title="CRM" message={query.error?.message ?? 'Kişi yüklenemedi'} />;
  }

  const isJunk = contact.status === 'archived';
  const ownerName = contact.owner_name ?? contact.bitrix_responsible ?? null;
  const purchases = contact.purchases ?? [];
  const currentPurchases = purchases.filter((item) => !item.is_historical_unit_change);
  const documents = documentsQuery.data ?? [];
  const visibleDocuments = documents.filter((doc) => !doc.hidden_from_view);
  const sourceRaw = contact.bitrix_source_channel || contact.source;
  const sourceLabel = formatLeadSource(sourceRaw);
  const referrerName = referrerQuery.data?.display_name?.trim() || null;
  const waNumber = phoneDigits(contact.whatsapp || contact.primary_phone);
  const lastComm = commEntries[0];
  const lastCommChannel = commLabel(lastComm?.activity_type) || commLabel(timeline[0]?.activity_type);
  const projectCount = new Set(currentPurchases.map((item) => item.project_label).filter(Boolean)).size;
  const tags = contact.tag_items ?? [];

  const selectTab = (next: PersonTab, filter: PilotHistoryFilter = 'all') => {
    setTab(next);
    if (next === 'history') setHistoryFilter(filter);
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    url.searchParams.set('tab', next === 'history' && filter === 'whatsapp' ? 'whatsapp' : next);
    window.history.replaceState(null, '', `${url.pathname}${url.search}`);
  };

  const togglePanel = (next: Panel) => setPanel((current) => (current === next ? null : next));

  const submitEdit = (event: FormEvent) => {
    event.preventDefault();
    const secondaryEmails = [secondEmail, ...splitList(extraEmails)].map((item) => item.trim()).filter(Boolean);
    actionMutation.mutate(async () => {
      const payload: Parameters<typeof updateContact>[1] = {};
      if (displayName.trim() && displayName.trim() !== contact.display_name) payload.display_name = displayName.trim();
      if (phone.trim() !== (contact.primary_phone ?? '')) payload.primary_phone = phone.trim() || undefined;
      if (email.trim() !== (contact.primary_email ?? '')) payload.primary_email = email.trim() || undefined;
      if (secondaryEmails.join('|') !== (contact.secondary_emails ?? []).join('|')) {
        payload.secondary_emails = secondaryEmails;
      }
      if (extraPhones !== (contact.secondary_phones ?? []).join(', ')) {
        payload.secondary_phones = splitList(extraPhones);
      }
      if (company.trim() !== (contact.organization_name ?? '')) payload.organization_name = company.trim() || undefined;
      if (position.trim() !== (contact.job_title ?? '')) payload.job_title = position.trim() || undefined;
      if (address.trim() !== (contact.address_line1 ?? '')) payload.address_line1 = address.trim() || undefined;
      if (city.trim() !== (contact.city ?? '')) payload.city = city.trim() || undefined;
      if (region.trim() !== (contact.state_province ?? '')) payload.state_province = region.trim() || undefined;
      if (source.trim() !== (contact.source ?? contact.bitrix_source_channel ?? '')) {
        payload.source = source.trim() || undefined;
      }
      if (notes !== (contact.notes ?? '')) payload.notes = notes;
      if (statusValue !== (contact.status === 'archived' ? 'archived' : 'active')) payload.status = statusValue;
      if (ownerId && ownerId !== (contact.owner_user_id ?? '')) payload.owner_user_id = ownerId;
      if (followUpAt !== toLocalInput(contact.next_follow_up_at)) {
        payload.next_follow_up_at = followUpAt ? toIso(followUpAt) : null;
      }
      const currentRoles = (contact.contact_types.length ? contact.contact_types : [contact.contact_type]).join('|');
      if (roles.join('|') !== currentRoles) {
        payload.contact_type = roles[0] ?? contact.contact_type;
        payload.contact_types = roles;
      }
      if (statusValue === 'archived') payload.junk_reason = junkReason.trim() || null;
      await updateContact(contactId, payload);
      setPanel(null);
    });
  };

  const submitNote = (event: FormEvent) => {
    event.preventDefault();
    if (!note.trim()) return;
    const typeLabel = NOTE_TYPES.find((item) => item.value === noteType)?.label ?? 'Yorum';
    actionMutation.mutate(async () => {
      await createActivity({
        entity_type: 'contact',
        entity_id: contactId,
        activity_type: noteType === 'note' ? 'comment' : noteType,
        title: typeLabel,
        description: note.trim(),
        start_date: noteAt ? toIso(noteAt) : new Date().toISOString(),
        status: 'completed',
      });
      if (noteNeedsFollowUp && noteFollowUpAt) {
        await createFollowUp({
          entity_type: 'contact',
          entity_id: contactId,
          reason: 'relationship_review',
          title: 'Takip',
          due_date: toIso(noteFollowUpAt),
          notes: note.trim(),
        });
      }
      setNote('');
      setNoteNeedsFollowUp(false);
      setNoteFollowUpAt('');
      setNoteAt(nowLocal());
      setPanel(null);
    });
  };

  const submitTask = (event: FormEvent) => {
    event.preventDefault();
    if (!taskTitle.trim()) return;
    const kindLabel = TASK_KINDS.find((item) => item.value === taskKind)?.label ?? 'Görev';
    actionMutation.mutate(async () => {
      if (taskKind === 'meeting') {
        await createMeeting({
          entity_type: 'contact',
          entity_id: contactId,
          activity_type: 'meeting',
          title: taskTitle.trim(),
          description: taskDescription.trim() || undefined,
          assigned_user_id: taskAssignee || user?.id,
          start_date: taskDue ? toIso(taskDue) : undefined,
          due_date: taskDue ? toIso(taskDue) : undefined,
          status: taskStatus === 'completed' ? 'completed' : 'planned',
        });
      } else if (taskKind === 'phone_call' || taskKind === 'email' || taskKind === 'whatsapp') {
        await createActivity({
          entity_type: 'contact',
          entity_id: contactId,
          activity_type: taskKind,
          title: taskTitle.trim() || kindLabel,
          description: taskDescription.trim() || undefined,
          assigned_user_id: taskAssignee || user?.id,
          due_date: taskDue ? toIso(taskDue) : undefined,
          task_status: taskStatus,
          status: taskStatus === 'completed' ? 'completed' : 'planned',
        });
      } else {
        await createTask({
          entity_type: 'contact',
          entity_id: contactId,
          title: taskTitle.trim(),
          description: taskDescription.trim() || undefined,
          assigned_user_id: taskAssignee || user?.id,
          due_date: taskDue ? toIso(taskDue) : undefined,
          task_status: taskStatus,
          metadata_json: { follow_up_kind: taskKind },
        });
      }
      setTaskTitle('');
      setTaskDescription('');
      setTaskDue('');
      setTaskStatus('not_started');
      setTaskKind('task');
      setPanel(null);
    });
  };

  const submitOwner = (event: FormEvent) => {
    event.preventDefault();
    if (!ownerId) return;
    actionMutation.mutate(async () => {
      try {
        await assignContactOwner(contactId, ownerId);
      } catch {
        await updateContact(contactId, { owner_user_id: ownerId });
      }
      setPanel(null);
    });
  };

  const submitLinkDocument = (event: FormEvent) => {
    event.preventDefault();
    if (!linkDocumentId.trim()) return;
    actionMutation.mutate(async () => {
      await linkDocument(linkDocumentId.trim(), 'crm_contact', contactId);
      setLinkDocumentId('');
    });
  };

  const completeFollowUpRow = (entry: ContactTimelineEntry) => {
    actionMutation.mutate(async () => {
      if (entry.activity_type === 'task') {
        await completeTask(entry.id);
      } else {
        await updateActivity(entry.id, { status: 'completed', task_status: 'completed' });
      }
    });
  };

  const saveReschedule = (entryId: string) => {
    if (!rescheduleAt) return;
    actionMutation.mutate(async () => {
      await updateActivity(entryId, { due_date: toIso(rescheduleAt) });
      setRescheduleId(null);
      setRescheduleAt('');
    });
  };

  const flags = [
    /BILGI_EKSIK/i.test(contact.notes || '') || (!contact.primary_phone && !contact.primary_email) ? 'BILGI_EKSIK' : null,
    /INCELEME_GEREKLI/i.test(contact.notes || '') || contact.review_required || contact.bitrix_history?.review_required
      ? 'INCELEME_GEREKLI'
      : null,
  ].filter(Boolean) as string[];

  const renderPurchaseTable = (items: CrmPurchaseSummary[], testId: string, heading: string) =>
    items.length ? (
      <div className="crm-purchase-history-group" data-testid={testId}>
        {heading ? <h3>{heading}</h3> : null}
        <table className="crm-person-table">
          <thead>
            <tr>
              <th>Proje / mülk</th>
              <th>Daire</th>
              <th>Tutar</th>
              <th>Durum</th>
            </tr>
          </thead>
          <tbody>
            {items.map((purchase, index) => (
              <PurchaseHistoryRow
                key={purchase.agreement_id}
                purchase={purchase}
                onOpen={openPurchase}
                identityTestId={testId === 'current-purchases' && index === 0 ? 'semrin-pilot-identity' : undefined}
              />
            ))}
          </tbody>
        </table>
      </div>
    ) : null;

  const renderTaskRows = (items: ContactTimelineEntry[], compact = false) => (
    <table className="crm-person-table crm-person-table--tasks">
      <thead>
        <tr>
          <th>Tarih</th>
          <th>Görev</th>
          <th>Tip</th>
          <th>Durum</th>
          {!compact ? <th>Açıklama</th> : null}
          <th>Sorumlu</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {(compact ? items.slice(0, 4) : items).map((entry) => {
          const due = typeof entry.metadata?.due_date === 'string' ? entry.metadata.due_date : null;
          const done = String(entry.metadata?.task_status || entry.status || '') === 'completed';
          return (
            <tr key={entry.id}>
              <td>{formatDateTime(due || entry.created_at, locale) || '—'}</td>
              <td>{entry.title.replace(/^(Görev|Takip):\s*/i, '')}</td>
              <td>{taskKindLabel(entry.activity_type, entry.metadata)}</td>
              <td>{taskStatusLabel(String(entry.metadata?.task_status || entry.status || ''))}</td>
              {!compact ? <td>{entry.summary || '—'}</td> : null}
              <td>{String(entry.metadata?.assigned_user_name || entry.actor_name || ownerName || '—')}</td>
              <td>
                {canUpdate && !done ? (
                  <div className="crm-person-table__actions">
                    <button type="button" onClick={() => completeFollowUpRow(entry)}>
                      Tamamla
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setRescheduleId(entry.id);
                        setRescheduleAt(toLocalInput(due || entry.created_at));
                      }}
                    >
                      Ertele
                    </button>
                  </div>
                ) : null}
                {rescheduleId === entry.id ? (
                  <div className="crm-person-reschedule">
                    <input type="datetime-local" value={rescheduleAt} onChange={(event) => setRescheduleAt(event.target.value)} />
                    <button type="button" onClick={() => saveReschedule(entry.id)}>
                      Kaydet
                    </button>
                  </div>
                ) : null}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );

  return (
    <div
      className={`crm-verify-detail crm-contact-card crm-person-card crm-contact-card--${variant}`}
      data-testid="unified-contact-card"
    >
      {variant === 'page' ? (
        <Button className="crm-contact-card__back" variant="secondary" size="sm" onClick={() => window.history.back()}>
          <IhIcon name="chevronLeft" size={13} /> Kişilere dön
        </Button>
      ) : null}

      <header className="crm-person-hero">
        <div className="crm-person-hero__main">
          <div className="crm-person-avatar" aria-hidden="true">
            {initials(contact.display_name)}
          </div>
          <div className="crm-person-hero__identity">
            <div className="crm-person-hero__name-row">
              <h1>{contact.display_name}</h1>
              {(contact.contact_types.length ? contact.contact_types : [contact.contact_type]).map((type) => (
                <span key={type} className="crm-person-chip">
                  {roleLabel(type)}
                </span>
              ))}
              {contact.is_agent ? <span className="crm-person-chip">Acenta</span> : null}
              <StatusChip tone={isJunk ? 'default' : 'success'}>{isJunk ? 'Junk' : 'Aktif'}</StatusChip>
            </div>
            <div className="crm-contact-card__tags" data-testid="contact-tags">
              {tags.map((tag) => (
                <span key={tag.id} className="crm-contact-card__tag">
                  <button type="button" onClick={() => router.push(`/workspaces/crm/contacts?tag=${tag.id}`)}>
                    {tag.name}
                  </button>
                  {canUpdate ? (
                    <button
                      type="button"
                      className="crm-contact-card__tag-remove"
                      aria-label={`${tag.name} kaldır`}
                      onClick={() => {
                        void removeContactTag(contactId, tag.id)
                          .then(() => refresh())
                          .catch((err: Error) => setError(err.message));
                      }}
                    >
                      ×
                    </button>
                  ) : null}
                </span>
              ))}
              {canUpdate ? (
                <select
                  className="crm-contact-card__tag-add"
                  value=""
                  aria-label="Etiket ekle"
                  onChange={(event) => {
                    const tagId = event.target.value;
                    if (!tagId) return;
                    void assignContactTag(contactId, tagId)
                      .then(() => refresh())
                      .catch((err: Error) => setError(err.message));
                  }}
                >
                  <option value="">+</option>
                  {(tagsQuery.data?.items ?? [])
                    .filter((tag) => !tags.some((item) => item.id === tag.id))
                    .map((tag) => (
                      <option key={tag.id} value={tag.id}>
                        {tag.name}
                      </option>
                    ))}
                </select>
              ) : null}
            </div>
          </div>
          <div className="crm-person-hero__meta">
            {sourceLabel ? (
              <div className="crm-person-source" data-testid="contact-lead-source">
                <dt>Geliş Kaynağı</dt>
                <dd>{sourceLabel}</dd>
              </div>
            ) : null}
            {referrerName ? (
              <div className="crm-person-source" data-testid="contact-referrer">
                <dt>Yönlendiren / Acenta</dt>
                <dd>{referrerName}</dd>
              </div>
            ) : null}
            {contact.created_at ? (
              <div className="crm-person-source">
                <dt>Oluşturulma Tarihi</dt>
                <dd>{formatShortDate(contact.created_at, locale)}</dd>
              </div>
            ) : null}
          </div>
        </div>
        {flags.length ? (
          <div className="crm-contact-card__flags" data-testid="contact-flags">
            {flags.map((flag) => (
              <span key={flag}>{flag}</span>
            ))}
          </div>
        ) : null}
        <div className="crm-person-actions">
          {contact.primary_email ? (
            <a className="crm-person-action" href={`mailto:${contact.primary_email}`}>
              <IhIcon name="mail" size={14} /> E-posta
            </a>
          ) : (
            <button type="button" className="crm-person-action" disabled>
              <IhIcon name="mail" size={14} /> E-posta
            </button>
          )}
          {waNumber ? (
            <a className="crm-person-action" href={`https://wa.me/${waNumber}`} target="_blank" rel="noreferrer">
              <IhIcon name="inbox" size={14} /> WhatsApp
            </a>
          ) : (
            <button type="button" className="crm-person-action" disabled>
              <IhIcon name="inbox" size={14} /> WhatsApp
            </button>
          )}
          <button
            type="button"
            className={`crm-person-action${panel === 'note' ? ' is-active' : ''}`}
            onClick={() => {
              setNoteType('note');
              togglePanel('note');
            }}
          >
            <IhIcon name="activity" size={14} /> Mesaj
          </button>
          {canUpdate ? (
            <button
              type="button"
              className={`crm-person-action${panel === 'task' && taskKind === 'meeting' ? ' is-active' : ''}`}
              onClick={() => {
                setTaskKind('meeting');
                togglePanel('task');
              }}
            >
              <IhIcon name="meeting" size={14} /> Toplantı
            </button>
          ) : null}
          {canUpdate ? (
            <button
              type="button"
              className={`crm-person-action${panel === 'more' || panel === 'assign' ? ' is-active' : ''}`}
              onClick={() => togglePanel(panel === 'more' || panel === 'assign' ? null : 'more')}
            >
              Diğer
            </button>
          ) : null}
          {canUpdate ? (
            <Button type="button" size="sm" data-testid="contact-edit-open" onClick={() => togglePanel('edit')}>
              Düzenle
            </Button>
          ) : null}
        </div>
        {panel === 'more' ? (
          <div className="crm-person-more">
            <button type="button" onClick={() => togglePanel('assign')}>
              Sorumlu Ata
            </button>
            <button
              type="button"
              onClick={() => {
                setTaskKind('task');
                togglePanel('task');
              }}
            >
              Görev Oluştur
            </button>
            <button
              type="button"
              onClick={() => {
                setStatusValue('archived');
                togglePanel('edit');
              }}
            >
              Junk&apos;a taşı
            </button>
          </div>
        ) : null}
      </header>

      {isJunk ? (
        <div className="crm-contact-card__banner crm-contact-card__banner--junk" data-testid="contact-junk-banner">
          <strong>Durum: Junk</strong>
          <div>Junk Sebebi: {contact.junk_reason || contact.bitrix_history?.junk_reason || '—'}</div>
        </div>
      ) : null}

      {contact.agent?.is_agent ? (
        <div className="crm-contact-card__banner" data-testid="contact-agent-banner">
          <strong>Acenta</strong>
          <div>
            {[contact.agent.brokerage_name || contact.organization_name, contact.agent.status === 'active' ? 'Aktif' : 'Pasif']
              .filter(Boolean)
              .join(' · ')}
          </div>
        </div>
      ) : null}

      {error ? <div className="crm-verify-detail__error">{error}</div> : null}

      {panel === 'edit' ? (
        <section className="crm-verify-detail__section" data-testid="contact-edit-panel">
          <h2>Kişiyi Düzenle</h2>
          <form onSubmit={submitEdit} className="crm-contact-card__panel">
            <div className="crm-contact-card__panel-grid">
              <Input label="Ad Soyad" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              <Input label="Telefon" value={phone} onChange={(event) => setPhone(event.target.value)} />
              <Input label="Ek telefonlar" value={extraPhones} onChange={(event) => setExtraPhones(event.target.value)} />
              <Input label="E-posta" value={email} onChange={(event) => setEmail(event.target.value)} />
              <Input label="İkinci E-posta" value={secondEmail} onChange={(event) => setSecondEmail(event.target.value)} />
              <Input label="Ek e-postalar" value={extraEmails} onChange={(event) => setExtraEmails(event.target.value)} />
              <Input label="Adres" value={address} onChange={(event) => setAddress(event.target.value)} />
              <Input label="Şehir" value={city} onChange={(event) => setCity(event.target.value)} />
              <Input label="Bölge" value={region} onChange={(event) => setRegion(event.target.value)} />
              <Input label="Şirket" value={company} onChange={(event) => setCompany(event.target.value)} />
              <Input label="Pozisyon" value={position} onChange={(event) => setPosition(event.target.value)} />
              <Input label="Kaynak" value={source} onChange={(event) => setSource(event.target.value)} />
              <Select label="Durum" value={statusValue} onChange={(event) => setStatusValue(event.target.value as 'active' | 'archived')}>
                <option value="active">Aktif</option>
                <option value="archived">Junk</option>
              </Select>
              {statusValue === 'archived' ? (
                <>
                  <Select label="Junk sebebi" value={junkReason} onChange={(event) => setJunkReason(event.target.value)}>
                    <option value="">Seçin veya yazın</option>
                    {(reasonsQuery.data?.items ?? []).map((item) => (
                      <option key={item.reason} value={item.reason}>{item.reason}</option>
                    ))}
                  </Select>
                  <Input label="Junk sebebi (serbest)" value={junkReason} onChange={(event) => setJunkReason(event.target.value)} />
                </>
              ) : null}
              <Select label="Sorumlu" value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
                <option value="">Seçin</option>
                {users.map((item) => (
                  <option key={item.id} value={item.id}>{item.full_name}</option>
                ))}
              </Select>
              <Input label="Sonraki takip" type="datetime-local" value={followUpAt} onChange={(event) => setFollowUpAt(event.target.value)} />
            </div>
            <TextArea label="Notlar" value={notes} onChange={(event) => setNotes(event.target.value)} />
            <div>
              <div className="crm-contact-card__meta-line">Tür / roller</div>
              <div className="crm-contact-card__roles">
                {CRM_CONTACT_TYPES.map((type) => (
                  <label key={type}>
                    <input
                      type="checkbox"
                      checked={roles.includes(type)}
                      onChange={() => {
                        setRoles((current) =>
                          current.includes(type) ? current.filter((item) => item !== type) : [...current, type],
                        );
                      }}
                    />
                    {roleLabel(type)}
                  </label>
                ))}
              </div>
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending} data-testid="contact-edit-save">
              Kaydet
            </Button>
          </form>
        </section>
      ) : null}

      {panel === 'note' ? (
        <section className="crm-verify-detail__section" data-testid="contact-note-panel">
          <h2>Yorum Ekle</h2>
          <form onSubmit={submitNote} className="crm-contact-card__panel">
            <TextArea label="Yorum" value={note} onChange={(event) => setNote(event.target.value)} />
            <div className="crm-contact-card__panel-grid">
              <Select label="Tür" value={noteType} onChange={(event) => setNoteType(event.target.value as typeof noteType)}>
                {NOTE_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </Select>
              <Input label="Tarih / saat" type="datetime-local" value={noteAt} onChange={(event) => setNoteAt(event.target.value)} />
              <Select label="Takip görevi oluştur" value={noteNeedsFollowUp ? 'yes' : 'no'} onChange={(event) => setNoteNeedsFollowUp(event.target.value === 'yes')}>
                <option value="no">Hayır</option>
                <option value="yes">Evet</option>
              </Select>
              {noteNeedsFollowUp ? (
                <Input label="Takip tarihi" type="datetime-local" value={noteFollowUpAt} onChange={(event) => setNoteFollowUpAt(event.target.value)} />
              ) : null}
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !note.trim()}>Yorumu kaydet</Button>
          </form>
        </section>
      ) : null}

      {panel === 'task' ? (
        <section className="crm-verify-detail__section" data-testid="contact-task-panel">
          <h2>Görev Oluştur</h2>
          <form onSubmit={submitTask} className="crm-contact-card__panel">
            <Input label="Görev" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder="24 Eyl 14:00 müşteriyi ara" />
            <TextArea label="Açıklama" value={taskDescription} onChange={(event) => setTaskDescription(event.target.value)} />
            <div className="crm-contact-card__panel-grid">
              <Select label="Tip" value={taskKind} onChange={(event) => setTaskKind(event.target.value as typeof taskKind)}>
                {TASK_KINDS.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </Select>
              <Select label="Sorumlu" value={taskAssignee} onChange={(event) => setTaskAssignee(event.target.value)}>
                <option value="">Seçin</option>
                {users.map((item) => (
                  <option key={item.id} value={item.id}>{item.full_name}</option>
                ))}
              </Select>
              <Input label="Tarih" type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} />
              <Select label="Durum" value={taskStatus} onChange={(event) => setTaskStatus(event.target.value as typeof taskStatus)}>
                {TASK_STATUSES.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </Select>
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !taskTitle.trim()}>Görevi kaydet</Button>
          </form>
        </section>
      ) : null}

      {panel === 'assign' ? (
        <section className="crm-verify-detail__section" data-testid="contact-assign-panel">
          <h2>Sorumlu Ata</h2>
          <p className="crm-contact-card__meta-line">Mevcut sorumlu: {ownerName || '—'}</p>
          <form onSubmit={submitOwner} className="crm-contact-card__panel">
            <Select label="Yeni sorumlu" value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
              <option value="">Kullanıcı seç</option>
              {users.map((item) => (
                <option key={item.id} value={item.id}>{item.full_name}</option>
              ))}
            </Select>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !ownerId}>Atamayı kaydet</Button>
          </form>
        </section>
      ) : null}

      <nav className="crm-contact-card__tabs crm-person-tabs" aria-label="Person card tabs" data-testid="person-card-tabs">
        {PERSON_TABS.map((item) => {
          const count =
            item.id === 'purchases' ? currentPurchases.length
            : item.id === 'history' ? commEntries.length
            : item.id === 'documents' ? visibleDocuments.length
            : item.id === 'tasks' ? followUpEntries.length
            : null;
          return (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'is-active' : undefined}
              data-testid={`contact-tab-${item.id}`}
              onClick={() => selectTab(item.id)}
            >
              {item.label}
              {count != null ? ` (${count})` : ''}
            </button>
          );
        })}
      </nav>

      {tab === 'overview' ? (
        <>
          <section className="crm-person-kpis" data-testid="contact-summary-cards">
            <button type="button" className="crm-person-kpi" onClick={() => selectTab('purchases')}>
              <span>Toplam Satın Alma</span>
              <strong>{currentPurchases.length}</strong>
              {projectCount ? <small>{projectCount} aktif projede</small> : null}
            </button>
            <button type="button" className="crm-person-kpi" onClick={() => selectTab('history')}>
              <span>İletişim</span>
              <strong>{commEntries.length}</strong>
              {lastCommChannel ? <small>{lastCommChannel}</small> : null}
            </button>
            <button type="button" className="crm-person-kpi" onClick={() => selectTab('history')}>
              <span>Son İletişim</span>
              <strong>{relativeLabel(contact.last_contact_at || lastComm?.created_at, locale) || '—'}</strong>
              {lastCommChannel ? <small>{lastCommChannel}</small> : null}
            </button>
            <div className="crm-person-kpi">
              <span>Durum</span>
              <strong className={isJunk ? '' : 'is-live'}>{isJunk ? 'Junk' : 'Aktif'}</strong>
              {contact.updated_at ? <small>Son güncelleme: {formatShortDate(contact.updated_at, locale)}</small> : null}
            </div>
            <div className="crm-person-kpi" data-testid="contact-summary-tags">
              <span>Etiketler</span>
              <div className="crm-person-kpi__tags">
                {tags.length ? tags.map((tag) => <em key={tag.id}>{tag.name}</em>) : <strong>—</strong>}
              </div>
            </div>
          </section>

          <section className="crm-person-workspace" data-testid="contact-overview">
            <article className="crm-person-panel">
              <div className="crm-person-panel__head">
                <h2>Genel Bilgiler</h2>
                {canUpdate ? (
                  <button type="button" onClick={() => togglePanel('edit')}>Düzenle</button>
                ) : null}
              </div>
              <dl className="crm-person-info">
                <InfoRow label="Ad Soyad" value={contact.display_name} />
                <InfoRow label="Telefon" value={contact.primary_phone} />
                <InfoRow label="Ek telefon" value={(contact.secondary_phones ?? []).join(', ')} />
                <InfoRow label="WhatsApp" value={contact.whatsapp && contact.whatsapp !== contact.primary_phone ? contact.whatsapp : null} />
                <InfoRow label="E-posta" value={contact.primary_email} />
                <InfoRow label="İkinci e-posta" value={(contact.secondary_emails ?? []).join(', ')} />
                <InfoRow label="Adres" value={[contact.address_line1, contact.address_line2].filter(Boolean).join(', ')} />
                <InfoRow label="Şehir" value={contact.city} />
                <InfoRow label="Bölge" value={contact.state_province} />
                <InfoRow label="Ülke" value={contact.country} />
                <InfoRow label="Şirket" value={contact.organization_name || contact.company_name} />
                <InfoRow
                  label="Rol"
                  value={(contact.contact_types.length ? contact.contact_types : [contact.contact_type]).map(roleLabel).join(', ')}
                />
                <InfoRow label="Geliş Kaynağı" value={sourceLabel} />
                <InfoRow label="Yönlendiren / Acenta" value={referrerName} />
                <InfoRow label="Sorumlu kullanıcı" value={ownerName} />
                <InfoRow label="Oluşturulma tarihi" value={formatShortDate(contact.created_at, locale)} />
                <InfoRow label="Son güncelleme" value={formatShortDate(contact.updated_at, locale)} />
                {(contact.profile_fields ?? [])
                  .filter((item) => {
                    const value = item.value.trim();
                    if (!value) return false;
                    if (/adres/i.test(item.label) && (contact.address_line1 || '').includes(value)) return false;
                    if (/pozisyon|rol/i.test(item.label) && contact.job_title === value) return false;
                    if (/telefon|e-posta|email|şirket|kaynak/i.test(item.label)) return false;
                    return true;
                  })
                  .map((item) => (
                    <InfoRow key={`${item.label}:${item.value}`} label={item.label} value={item.value} />
                  ))}
              </dl>
            </article>

            <div className="crm-person-workspace__side">
              <article className="crm-person-panel">
                <div className="crm-person-panel__head">
                  <h2>Satın Almalar</h2>
                  <button type="button" onClick={() => selectTab('purchases')}>Tümünü Gör</button>
                </div>
                {currentPurchases.length ? renderPurchaseTable(currentPurchases.slice(0, 3), 'current-purchases', '') : <p>Satın alma kaydı yok.</p>}
              </article>
              <article className="crm-person-panel" data-testid="contact-tasks-preview">
                <div className="crm-person-panel__head">
                  <h2>Görevler</h2>
                  <button type="button" onClick={() => { setTaskKind('task'); togglePanel('task'); }}>Görev Oluştur</button>
                </div>
                {followUpEntries.length ? renderTaskRows(followUpEntries, true) : <p>Bu kişi için görev kaydı yok.</p>}
              </article>
              <article className="crm-person-panel">
                <div className="crm-person-panel__head">
                  <h2>Belgeler</h2>
                  <button type="button" onClick={() => selectTab('documents')}>Tümünü Gör</button>
                </div>
                {visibleDocuments.length ? (
                  <ul className="crm-contact-card__docs">
                    {visibleDocuments.slice(0, 4).map((doc) => (
                      <li key={doc.id}>
                        <a href={`/workspaces/crm/documents/${doc.id}`}>{doc.original_file_name || doc.title}</a>
                        <small>
                          {[doc.document_type, doc.created_at ? relativeLabel(doc.created_at, locale) : null]
                            .filter(Boolean)
                            .join(' · ')}
                        </small>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Bu kişiye bağlı belge yok.</p>
                )}
              </article>
            </div>
          </section>
        </>
      ) : null}

      {tab === 'purchases' ? (
        <section className="crm-verify-detail__section" data-testid="satin-aldiklari">
          <h2>Satın Almalar <span>{currentPurchases.length}</span></h2>
          {currentPurchases.length ? (
            renderPurchaseTable(currentPurchases, 'current-purchases', '')
          ) : contact.crm_agreements.length ? (
            <div className="crm-verify-detail__records" data-testid="contact-agreements">
              {contact.crm_agreements.map((agreement) => {
                const isReit = agreement.project_group === 'reit';
                return (
                  <article key={agreement.id}>
                    <strong>{agreement.project_label}</strong>
                    <small>
                      Durum: {agreement.status}
                      {agreement.agreement_date ? ` · Anlaşma tarihi: ${agreement.agreement_date}` : ''}
                      {isReit
                        ? ` · Yatırım Tutarı: ${agreement.investment_amount || '—'}`
                        : ` · Daire No: ${agreement.unit_number || '—'}`}
                      {!isReit && agreement.purchase_price ? ` · Satış / anlaşma fiyatı: ${agreement.purchase_price}` : ''}
                      {!isReit && agreement.payment_amount ? ` · Ödeme: ${agreement.payment_amount}` : ''}
                      {!isReit && agreement.deposit ? ` · Kapora: ${agreement.deposit}` : ''}
                    </small>
                  </article>
                );
              })}
            </div>
          ) : (
            <p>Satın alma kaydı yok.</p>
          )}
        </section>
      ) : null}

      {tab === 'tasks' ? (
        <section className="crm-verify-detail__section" data-testid="contact-tasks">
          <div className="crm-person-panel__head">
            <h2>Görevler / Takip Planı <span>{followUpEntries.length}</span></h2>
            {canUpdate ? (
              <Button type="button" size="sm" onClick={() => { setTaskKind('task'); togglePanel('task'); }}>
                Görev Oluştur
              </Button>
            ) : null}
          </div>
          {followUpEntries.length ? renderTaskRows(followUpEntries) : <p>Bu kişi için görev kaydı yok.</p>}
        </section>
      ) : null}

      {tab === 'history' ? (
        <PilotHistoryStream
          entries={timeline}
          documents={documents}
          locale={locale}
          loading={timelineQuery.isLoading}
          initialFilter={historyFilter}
          includeDocuments={false}
          heading="Yorumlar / İletişim Akışı"
        />
      ) : null}

      {tab === 'documents' ? (
        <section className="crm-verify-detail__section" data-testid="contact-documents">
          <h2>Belgeler <span>{visibleDocuments.length}</span></h2>
          {!canViewDocuments ? (
            <p>Belge görüntüleme yetkisi yok.</p>
          ) : documentsQuery.isLoading ? (
            <p>Loading…</p>
          ) : documents.length ? (
            <div data-testid="nedim-general-documents">
              <DocumentGallery
                documents={documents}
                entityType="crm_contact"
                entityId={contactId}
                onChanged={() => {
                  void queryClient.invalidateQueries({ queryKey: ['crm', 'contacts', 'documents', contactId] });
                }}
              />
            </div>
          ) : (
            <p>Bu kişiye bağlı belge yok.</p>
          )}
          {canLinkDocuments ? (
            <form onSubmit={submitLinkDocument} className="crm-contact-card__panel">
              <Input
                label="Mevcut belge ID ile bağla"
                value={linkDocumentId}
                onChange={(event) => setLinkDocumentId(event.target.value)}
              />
              <Button type="submit" size="sm" variant="secondary" disabled={actionMutation.isPending || !linkDocumentId.trim()}>
                Belgeyi bağla
              </Button>
            </form>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
