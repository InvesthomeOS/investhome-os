'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import type { Route } from 'next';
import { useParams, usePathname, useRouter } from 'next/navigation';
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
import { personCardCopy, type PersonCardCopy } from '@/workspaces/crm/contact-card/person-card-copy';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { PilotHistoryStream, type PilotHistoryFilter } from '@/workspaces/crm/contact-card/history-stream';
import { taskStatusLabel } from '@/workspaces/crm/contact-card/history-html';
import { UnitHistoryInline } from '@/workspaces/crm/contact-card/unit-history';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';
import { CRM_CONTACT_TYPES, type CrmContactType, type CrmPurchaseSummary } from '@/workspaces/crm/types';

import '@/app/workspaces/crm/contacts/_components/ds/contacts-ds.css';
import './contact-card.css';

const NOTE_TYPES = ['note', 'phone_call', 'whatsapp', 'email', 'meeting'] as const;
const TASK_KINDS = ['phone_call', 'email', 'whatsapp', 'meeting', 'proposal', 'task'] as const;
const TASK_STATUSES = ['not_started', 'in_progress', 'waiting', 'completed'] as const;

const SOURCE_RULES: Array<{ match: RegExp; key: keyof PersonCardCopy['sources'] }> = [
  { match: /instagram/i, key: 'instagram' },
  { match: /facebook|meta/i, key: 'facebook' },
  { match: /whatsapp|\bwa\b/i, key: 'whatsapp' },
  { match: /rc[_\s-]?generator|acenta|agent|broker|referral|referans/i, key: 'agency' },
  { match: /web\s*form|website|web\s*site|crm form|webform|^web$|genel form/i, key: 'website' },
  { match: /manuel|manual|^os$/i, key: 'manual' },
];

type Panel = 'edit' | 'note' | 'task' | 'assign' | 'more' | null;

const PERSON_TABS = ['overview', 'purchases', 'history', 'documents', 'tasks'] as const;

type PersonTab = (typeof PERSON_TABS)[number];

function formatLeadSource(raw: string | null | undefined, t: PersonCardCopy): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  const mapped = SOURCE_RULES.find((rule) => rule.match.test(value))?.key;
  if (mapped) return t.sources[mapped];
  if (/^[A-Z0-9_]+$/.test(value)) return null;
  return value;
}

function roleLabel(type: string, t: PersonCardCopy) {
  return t.roleLabels[type as keyof PersonCardCopy['roleLabels']] || type;
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const first = parts[0];
  if (!first) return '•';
  const last = parts.length > 1 ? parts[parts.length - 1] : undefined;
  return ((first[0] || '') + (last?.[0] || '')).toUpperCase();
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

function relativeLabel(iso: string | null | undefined, locale: string, t: PersonCardCopy) {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  const diff = Date.now() - date.getTime();
  const minutes = Math.round(diff / 60000);
  if (Math.abs(minutes) < 1) return t.justNow;
  if (Math.abs(minutes) < 60) {
    return `${Math.abs(minutes)} ${minutes > 0 ? t.minutesAgo : t.minutesLater}`;
  }
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) {
    return `${Math.abs(hours)} ${hours > 0 ? t.hoursAgo : t.hoursLater}`;
  }
  const days = Math.round(hours / 24);
  if (Math.abs(days) < 45) {
    return `${Math.abs(days)} ${days > 0 ? t.daysAgo : t.daysLater}`;
  }
  return formatShortDate(iso, locale);
}

function commLabel(type: string | null | undefined, t: PersonCardCopy) {
  if (type === 'email') return t.email;
  if (type === 'whatsapp') return t.whatsapp;
  if (type === 'phone_call') return t.callKind;
  if (type === 'meeting' || type === 'zoom_meeting' || type === 'teams_meeting') return t.meeting;
  if (type === 'sms') return t.message;
  return null;
}

function taskKindLabel(type: string, t: PersonCardCopy, meta?: Record<string, unknown> | null) {
  const kind = String(meta?.follow_up_kind || type || '');
  if (kind === 'proposal') return t.proposalKind;
  if (kind === 'task' || kind === 'follow_up' || kind === 'reminder') return t.followKind;
  return commLabel(kind, t) || kind || t.followKind;
}

function crmStatusLabel(raw: string | null | undefined, t: PersonCardCopy): string | null {
  const value = (raw || '').trim();
  if (!value) return null;
  if (/deal\s*won|^won$|^kazan[ıi]ld[ıi]$/i.test(value)) return t.purchased;
  if (/^completed$|^tamamland[ıi]$/i.test(value)) return t.completed;
  if (/^active$|^aktif$/i.test(value)) return t.active;
  if (/^cancelled$|^canceled$|^iptal$/i.test(value)) return t.cancelled;
  if (/^lost$|^kaybedildi$/i.test(value)) return t.lost;
  if (/^[A-Z0-9_:]+$/.test(value)) return null;
  return value;
}

function purchaseStatusLabel(purchase: CrmPurchaseSummary, t: PersonCardCopy) {
  if (purchase.is_historical_unit_change) return t.unitChange;
  return crmStatusLabel(purchase.stage, t) || crmStatusLabel(purchase.status, t);
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
  const t = personCardCopy(useLocale());
  const isReit = purchase.project_group === 'reit';
  const historical = Boolean(purchase.is_historical_unit_change);
  const status = purchaseStatusLabel(purchase, t);
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
        {purchase.hemen_kira ? <span className="crm-purchase-list__unit">{t.hemenKira}</span> : null}
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

function friendlyError(message: string, t: PersonCardCopy): string {
  if (message.includes('invalid_phone')) return t.invalidPhone;
  if (message.includes('invalid_email')) return t.invalidEmailMsg;
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
  return PERSON_TABS.some((item) => item === value) ? (value as PersonTab) : 'overview';
}

function requestedHistoryFilter(): PilotHistoryFilter {
  if (typeof window === 'undefined') return 'all';
  return new URLSearchParams(window.location.search).get('tab') === 'whatsapp' ? 'whatsapp' : 'all';
}

function personIdFromRoute(pathname: string | null, paramId: string | undefined): string {
  const fromPath = pathname?.match(/\/contacts\/([0-9a-fA-F-]{36})(?:\/|$)/)?.[1];
  if (fromPath) return fromPath;
  return typeof paramId === 'string' ? paramId : '';
}

export function UnifiedContactCard({
  contactId: contactIdProp,
  variant = 'page',
}: {
  contactId: string;
  variant?: 'page' | 'drawer';
}) {
  const params = useParams<{ contactId?: string }>();
  const pathname = usePathname();
  const routeContactId = personIdFromRoute(pathname, params.contactId);
  const contactId = variant === 'page' && routeContactId ? routeContactId : contactIdProp;
  const locale = useLocale();
  const t = personCardCopy(locale);
  const queryClient = useQueryClient();
  const router = useRouter();
  const { openPurchase } = useContactCard();
  const { authLoading, canRead, has, user, canViewFinancial } = useCrmAccess();
  const canUpdate = has('update');
  const canViewDocuments = Boolean(user && hasPermission(user, 'documents', 'view'));
  const canLinkDocuments = Boolean(user && hasPermission(user, 'documents', 'update'));
  const canUploadDocuments = canLinkDocuments;
  const canArchiveDocuments = Boolean(
    user && (hasPermission(user, 'documents', 'archive') || hasPermission(user, 'documents', 'delete')),
  );
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
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [extraPhones, setExtraPhones] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [email, setEmail] = useState('');
  const [extraEmails, setExtraEmails] = useState('');
  const [secondEmail, setSecondEmail] = useState('');
  const [address, setAddress] = useState('');
  const [city, setCity] = useState('');
  const [region, setRegion] = useState('');
  const [country, setCountry] = useState('');
  const [language, setLanguage] = useState('');
  const [budgetMin, setBudgetMin] = useState('');
  const [budgetMax, setBudgetMax] = useState('');
  const [source, setSource] = useState('');
  const [notes, setNotes] = useState('');
  const [company, setCompany] = useState('');
  const [position, setPosition] = useState('');
  const [saveOk, setSaveOk] = useState(false);
  const [statusValue, setStatusValue] = useState<'active' | 'archived'>('active');
  const [junkReason, setJunkReason] = useState('');
  const [roles, setRoles] = useState<CrmContactType[]>([]);
  const [ownerId, setOwnerId] = useState('');
  const [followUpAt, setFollowUpAt] = useState('');
  const [note, setNote] = useState('');
  const [noteType, setNoteType] = useState<(typeof NOTE_TYPES)[number]>('note');
  const [noteAt, setNoteAt] = useState(nowLocal);
  const [noteNeedsFollowUp, setNoteNeedsFollowUp] = useState(false);
  const [noteFollowUpAt, setNoteFollowUpAt] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskAssignee, setTaskAssignee] = useState('');
  const [taskDue, setTaskDue] = useState('');
  const [taskStatus, setTaskStatus] = useState<(typeof TASK_STATUSES)[number]>('not_started');
  const [taskKind, setTaskKind] = useState<(typeof TASK_KINDS)[number]>('task');
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
      router.replace(salesDetailUrl(contactId, purchase) as Route);
    }
  }, [contactId, router]);

  useEffect(() => {
    if (!contact) return;
    setDisplayName(contact.display_name);
    setFirstName(contact.first_name ?? '');
    setLastName(contact.last_name ?? '');
    setPhone(contact.primary_phone ?? '');
    setExtraPhones((contact.secondary_phones ?? []).join(', '));
    setWhatsapp(contact.whatsapp ?? '');
    setEmail(contact.primary_email ?? '');
    setSecondEmail((contact.secondary_emails ?? [])[0] ?? '');
    setExtraEmails((contact.secondary_emails ?? []).slice(1).join(', '));
    setAddress(contact.address_line1 ?? '');
    setCity(contact.city ?? '');
    setRegion(contact.state_province ?? '');
    setCountry(contact.country ?? '');
    const prefs = contact.communication_prefs ?? {};
    setLanguage(typeof prefs.language === 'string' ? prefs.language : '');
    const buyer = contact.buyer_profile ?? {};
    setBudgetMin(buyer.budget_min != null ? String(buyer.budget_min) : '');
    setBudgetMax(buyer.budget_max != null ? String(buyer.budget_max) : '');
    setSource(contact.source ?? contact.bitrix_source_channel ?? '');
    setNotes(contact.notes ?? '');
    setCompany(contact.organization_name ?? '');
    setPosition(contact.job_title ?? '');
    setSaveOk(false);
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
    onError: (err: Error) => {
      setSaveOk(false);
      setError(friendlyError(err.message, t));
    },
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

  if (authLoading || query.isLoading) return <LoadingState label={t.loading} />;
  if (!canRead) return <EmptyState title="CRM" description={t.accessDenied} />;
  if (query.isError || !contact) {
    return <ErrorState title="CRM" message={query.error?.message ?? t.loadError} />;
  }

  const isJunk = contact.status === 'archived';
  const ownerName = contact.owner_name ?? contact.bitrix_responsible ?? null;
  const purchases = contact.purchases ?? [];
  const currentPurchases = purchases.filter((item) => !item.is_historical_unit_change);
  const documents = documentsQuery.data ?? [];
  const visibleDocuments = documents.filter((doc) => !doc.hidden_from_view);
  const sourceRaw = contact.bitrix_source_channel || contact.source;
  const sourceLabel = formatLeadSource(sourceRaw, t);
  const referrerName = referrerQuery.data?.display_name?.trim() || null;
  const waNumber = phoneDigits(contact.whatsapp || contact.primary_phone);
  const lastComm = commEntries[0];
  const lastCommChannel = commLabel(lastComm?.activity_type, t) || commLabel(timeline[0]?.activity_type, t);
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
    const combinedName = `${firstName.trim()} ${lastName.trim()}`.trim();
    const nextDisplay = displayName.trim() || combinedName;
    if (!nextDisplay) {
      setError(t.nameRequired);
      return;
    }
    if (email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setError(t.invalidEmail);
      return;
    }
    const secondaryEmails = [secondEmail, ...splitList(extraEmails)].map((item) => item.trim()).filter(Boolean);
    setSaveOk(false);
    actionMutation.mutate(async () => {
      const payload: Parameters<typeof updateContact>[1] = {};
      if (nextDisplay !== contact.display_name) payload.display_name = nextDisplay;
      if (firstName.trim() !== (contact.first_name ?? '')) payload.first_name = firstName.trim() || undefined;
      if (lastName.trim() !== (contact.last_name ?? '')) payload.last_name = lastName.trim() || undefined;
      if (phone.trim() !== (contact.primary_phone ?? '')) payload.primary_phone = phone.trim() || undefined;
      if (whatsapp.trim() !== (contact.whatsapp ?? '')) payload.whatsapp = whatsapp.trim() || undefined;
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
      if (country.trim() !== (contact.country ?? '')) payload.country = country.trim() || undefined;
      const currentLanguage = typeof contact.communication_prefs?.language === 'string' ? contact.communication_prefs.language : '';
      if (language.trim() !== currentLanguage) {
        payload.communication_prefs = { language: language.trim() || null };
      }
      if (canViewFinancial) {
        const currentMin = contact.buyer_profile?.budget_min != null ? String(contact.buyer_profile.budget_min) : '';
        const currentMax = contact.buyer_profile?.budget_max != null ? String(contact.buyer_profile.budget_max) : '';
        if (budgetMin.trim() !== currentMin || budgetMax.trim() !== currentMax) {
          payload.buyer_profile = {
            ...(contact.buyer_profile ?? {}),
            budget_min: budgetMin.trim() ? Number(budgetMin.trim()) : null,
            budget_max: budgetMax.trim() ? Number(budgetMax.trim()) : null,
          };
        }
      }
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
      setSaveOk(true);
      setPanel(null);
    });
  };

  const cancelEdit = () => {
    if (!contact) return;
    setDisplayName(contact.display_name);
    setFirstName(contact.first_name ?? '');
    setLastName(contact.last_name ?? '');
    setPhone(contact.primary_phone ?? '');
    setExtraPhones((contact.secondary_phones ?? []).join(', '));
    setWhatsapp(contact.whatsapp ?? '');
    setEmail(contact.primary_email ?? '');
    setSecondEmail((contact.secondary_emails ?? [])[0] ?? '');
    setExtraEmails((contact.secondary_emails ?? []).slice(1).join(', '));
    setAddress(contact.address_line1 ?? '');
    setCity(contact.city ?? '');
    setRegion(contact.state_province ?? '');
    setCountry(contact.country ?? '');
    const prefs = contact.communication_prefs ?? {};
    setLanguage(typeof prefs.language === 'string' ? prefs.language : '');
    const buyer = contact.buyer_profile ?? {};
    setBudgetMin(buyer.budget_min != null ? String(buyer.budget_min) : '');
    setBudgetMax(buyer.budget_max != null ? String(buyer.budget_max) : '');
    setSource(contact.source ?? contact.bitrix_source_channel ?? '');
    setNotes(contact.notes ?? '');
    setCompany(contact.organization_name ?? '');
    setPosition(contact.job_title ?? '');
    setStatusValue(contact.status === 'archived' ? 'archived' : 'active');
    setJunkReason(contact.junk_reason ?? '');
    setRoles(contact.contact_types.length ? contact.contact_types : [contact.contact_type]);
    setOwnerId(contact.owner_user_id ?? '');
    setFollowUpAt(toLocalInput(contact.next_follow_up_at));
    setError(null);
    setPanel(null);
  };

  const submitNote = (event: FormEvent) => {
    event.preventDefault();
    if (!note.trim()) return;
    const typeLabel = noteType === 'note' ? t.noteKind : commLabel(noteType, t) || t.comment;
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
          title: t.followKind,
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
    const kindLabel = taskKindLabel(taskKind, t);
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
              <th>{t.purchases}</th>
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
          <th>{t.task}</th>
          <th>Tip</th>
          <th>Durum</th>
          {!compact ? <th>{t.description}</th> : null}
          <th>{t.assignee}</th>
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
              <td>{taskKindLabel(entry.activity_type, t, entry.metadata)}</td>
              <td>
                {entry.metadata?.task_status === 'not_started'
                  ? t.notStarted
                  : entry.metadata?.task_status === 'in_progress'
                    ? t.inProgress
                    : entry.metadata?.task_status === 'waiting'
                      ? t.waiting
                      : String(entry.metadata?.task_status || entry.status || '') === 'completed'
                        ? t.completed
                        : taskStatusLabel(String(entry.metadata?.task_status || entry.status || ''))}
              </td>
              {!compact ? <td>{entry.summary || '—'}</td> : null}
              <td>{String(entry.metadata?.assigned_user_name || entry.actor_name || ownerName || '—')}</td>
              <td>
                {canUpdate && !done ? (
                  <div className="crm-person-table__actions">
                    <button type="button" onClick={() => completeFollowUpRow(entry)}>
                      {t.complete}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setRescheduleId(entry.id);
                        setRescheduleAt(toLocalInput(due || entry.created_at));
                      }}
                    >
                      {t.postpone}
                    </button>
                  </div>
                ) : null}
                {rescheduleId === entry.id ? (
                  <div className="crm-person-reschedule">
                    <input type="datetime-local" value={rescheduleAt} onChange={(event) => setRescheduleAt(event.target.value)} />
                    <button type="button" onClick={() => saveReschedule(entry.id)}>
                      {t.save}
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
          <IhIcon name="chevronLeft" size={13} /> {t.back}
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
                  {roleLabel(type, t)}
                </span>
              ))}
              {contact.is_agent ? <span className="crm-person-chip">{t.agent}</span> : null}
              <StatusChip tone={isJunk ? 'default' : 'success'}>{isJunk ? t.junk : t.active}</StatusChip>
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
                      aria-label={`${tag.name} ${t.removeTag}`}
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
                  aria-label={t.addTag}
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
                <dt>{t.source}</dt>
                <dd>{sourceLabel}</dd>
              </div>
            ) : null}
            {referrerName ? (
              <div className="crm-person-source" data-testid="contact-referrer">
                <dt>{t.referrer}</dt>
                <dd>{referrerName}</dd>
              </div>
            ) : null}
            {contact.created_at ? (
              <div className="crm-person-source">
                <dt>{t.createdAt}</dt>
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
              <IhIcon name="mail" size={14} /> {t.email}
            </a>
          ) : (
            <button type="button" className="crm-person-action" disabled>
              <IhIcon name="mail" size={14} /> {t.email}
            </button>
          )}
          {waNumber ? (
            <a className="crm-person-action" href={`https://wa.me/${waNumber}`} target="_blank" rel="noreferrer">
              <IhIcon name="inbox" size={14} /> {t.whatsapp}
            </a>
          ) : (
            <button type="button" className="crm-person-action" disabled>
              <IhIcon name="inbox" size={14} /> {t.whatsapp}
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
            <IhIcon name="activity" size={14} /> {t.message}
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
              <IhIcon name="meeting" size={14} /> {t.meeting}
            </button>
          ) : null}
          {canUpdate ? (
            <button
              type="button"
              className={`crm-person-action${panel === 'more' || panel === 'assign' ? ' is-active' : ''}`}
              onClick={() => togglePanel(panel === 'more' || panel === 'assign' ? null : 'more')}
            >
              {t.more}
            </button>
          ) : null}
          {canUpdate ? (
            <Button type="button" size="sm" data-testid="contact-edit-open" onClick={() => togglePanel('edit')}>
              {t.edit}
            </Button>
          ) : null}
        </div>
        {panel === 'more' ? (
          <div className="crm-person-more">
            <button type="button" onClick={() => togglePanel('assign')}>
              {t.assignOwner}
            </button>
            <button
              type="button"
              onClick={() => {
                setTaskKind('task');
                togglePanel('task');
              }}
            >
              {t.createTask}
            </button>
            <button
              type="button"
              onClick={() => {
                setStatusValue('archived');
                togglePanel('edit');
              }}
            >
              {t.moveToJunk}
            </button>
          </div>
        ) : null}
      </header>

      {isJunk ? (
        <div className="crm-contact-card__banner crm-contact-card__banner--junk" data-testid="contact-junk-banner">
          <strong>{t.junkStatus}</strong>
          <div>{t.junkReason}: {contact.junk_reason || contact.bitrix_history?.junk_reason || '—'}</div>
        </div>
      ) : null}

      {contact.agent?.is_agent ? (
        <div className="crm-contact-card__banner" data-testid="contact-agent-banner">
          <strong>{t.agent}</strong>
          <div>
            {[contact.agent.brokerage_name || contact.organization_name, contact.agent.status === 'active' ? t.active : t.passive]
              .filter(Boolean)
              .join(' · ')}
          </div>
        </div>
      ) : null}

      {error ? <div className="crm-verify-detail__error">{error}</div> : null}
      {saveOk && !error ? (
        <div className="crm-verify-detail__success" data-testid="contact-edit-success">
          {t.saved}
        </div>
      ) : null}

      {panel === 'edit' ? (
        <section className="crm-verify-detail__section" data-testid="contact-edit-panel">
          <h2>{t.editPerson}</h2>
          <form onSubmit={submitEdit} className="crm-contact-card__panel">
            <div className="crm-contact-card__panel-grid">
              <Input label={t.displayName} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              <Input label={t.firstName} value={firstName} onChange={(event) => setFirstName(event.target.value)} />
              <Input label={t.lastName} value={lastName} onChange={(event) => setLastName(event.target.value)} />
              <Input label={t.phone} value={phone} onChange={(event) => setPhone(event.target.value)} />
              <Input label={t.whatsapp} value={whatsapp} onChange={(event) => setWhatsapp(event.target.value)} />
              <Input label={t.extraPhones} value={extraPhones} onChange={(event) => setExtraPhones(event.target.value)} />
              <Input label={t.email} value={email} onChange={(event) => setEmail(event.target.value)} />
              <Input label={t.secondEmail} value={secondEmail} onChange={(event) => setSecondEmail(event.target.value)} />
              <Input label={t.extraEmails} value={extraEmails} onChange={(event) => setExtraEmails(event.target.value)} />
              <Input label={t.address} value={address} onChange={(event) => setAddress(event.target.value)} />
              <Input label={t.city} value={city} onChange={(event) => setCity(event.target.value)} />
              <Input label={t.region} value={region} onChange={(event) => setRegion(event.target.value)} />
              <Input label={t.country} value={country} onChange={(event) => setCountry(event.target.value)} />
              <Select label={t.language} value={language} onChange={(event) => setLanguage(event.target.value)}>
                <option value="">{t.select}</option>
                <option value="tr">Türkçe</option>
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="ru">Русский</option>
                <option value="ar">العربية</option>
              </Select>
              {canViewFinancial ? (
                <>
                  <Input
                    label={t.budgetMin}
                    value={budgetMin}
                    onChange={(event) => setBudgetMin(event.target.value)}
                    inputMode="decimal"
                  />
                  <Input
                    label={t.budgetMax}
                    value={budgetMax}
                    onChange={(event) => setBudgetMax(event.target.value)}
                    inputMode="decimal"
                  />
                </>
              ) : null}
              <Input label={t.company} value={company} onChange={(event) => setCompany(event.target.value)} />
              <Input label={t.position} value={position} onChange={(event) => setPosition(event.target.value)} />
              <Input label={t.source} value={source} onChange={(event) => setSource(event.target.value)} />
              <Select label={t.status} value={statusValue} onChange={(event) => setStatusValue(event.target.value as 'active' | 'archived')}>
                <option value="active">{t.active}</option>
                <option value="archived">{t.junk}</option>
              </Select>
              {statusValue === 'archived' ? (
                <>
                  <Select label={t.junkReasonField} value={junkReason} onChange={(event) => setJunkReason(event.target.value)}>
                    <option value="">{t.selectOrType}</option>
                    {(reasonsQuery.data?.items ?? []).map((item) => (
                      <option key={item.reason} value={item.reason}>{item.reason}</option>
                    ))}
                  </Select>
                  <Input label={t.junkReasonFree} value={junkReason} onChange={(event) => setJunkReason(event.target.value)} />
                </>
              ) : null}
              <Select label={t.owner} value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
                <option value="">{t.select}</option>
                {users.map((item) => (
                  <option key={item.id} value={item.id}>{item.full_name}</option>
                ))}
              </Select>
              <Input label={t.nextFollowUp} type="datetime-local" value={followUpAt} onChange={(event) => setFollowUpAt(event.target.value)} />
            </div>
            <TextArea label={t.notes} value={notes} onChange={(event) => setNotes(event.target.value)} />
            <div>
              <div className="crm-contact-card__meta-line">{t.roles}</div>
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
                    {roleLabel(type, t)}
                  </label>
                ))}
              </div>
            </div>
            <div className="crm-contact-card__panel-actions">
              <Button type="submit" size="sm" disabled={actionMutation.isPending} data-testid="contact-edit-save">
                {actionMutation.isPending ? t.saving : t.save}
              </Button>
              <Button
                type="button"
                size="sm"
                variant="secondary"
                disabled={actionMutation.isPending}
                data-testid="contact-edit-cancel"
                onClick={cancelEdit}
              >
                {t.cancel}
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {panel === 'note' ? (
        <section className="crm-verify-detail__section" data-testid="contact-note-panel">
          <h2>{t.addComment}</h2>
          <form onSubmit={submitNote} className="crm-contact-card__panel">
            <TextArea label={t.comment} value={note} onChange={(event) => setNote(event.target.value)} />
            <div className="crm-contact-card__panel-grid">
              <Select label={t.type} value={noteType} onChange={(event) => setNoteType(event.target.value as typeof noteType)}>
                {NOTE_TYPES.map((item) => (
                  <option key={item} value={item}>
                    {item === 'note' ? t.noteKind : commLabel(item, t) || item}
                  </option>
                ))}
              </Select>
              <Input label={t.datetime} type="datetime-local" value={noteAt} onChange={(event) => setNoteAt(event.target.value)} />
              <Select label={t.createFollowUp} value={noteNeedsFollowUp ? 'yes' : 'no'} onChange={(event) => setNoteNeedsFollowUp(event.target.value === 'yes')}>
                <option value="no">{t.no}</option>
                <option value="yes">{t.yes}</option>
              </Select>
              {noteNeedsFollowUp ? (
                <Input label={t.followUpDate} type="datetime-local" value={noteFollowUpAt} onChange={(event) => setNoteFollowUpAt(event.target.value)} />
              ) : null}
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !note.trim()}>{t.saveComment}</Button>
          </form>
        </section>
      ) : null}

      {panel === 'task' ? (
        <section className="crm-verify-detail__section" data-testid="contact-task-panel">
          <h2>{t.createTask}</h2>
          <form onSubmit={submitTask} className="crm-contact-card__panel">
            <Input label={t.task} value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} placeholder={t.taskPlaceholder} />
            <TextArea label={t.description} value={taskDescription} onChange={(event) => setTaskDescription(event.target.value)} />
            <div className="crm-contact-card__panel-grid">
              <Select label={t.type} value={taskKind} onChange={(event) => setTaskKind(event.target.value as typeof taskKind)}>
                {TASK_KINDS.map((item) => (
                  <option key={item} value={item}>{taskKindLabel(item, t)}</option>
                ))}
              </Select>
              <Select label={t.owner} value={taskAssignee} onChange={(event) => setTaskAssignee(event.target.value)}>
                <option value="">{t.select}</option>
                {users.map((item) => (
                  <option key={item.id} value={item.id}>{item.full_name}</option>
                ))}
              </Select>
              <Input label={t.date} type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} />
              <Select label={t.status} value={taskStatus} onChange={(event) => setTaskStatus(event.target.value as typeof taskStatus)}>
                {TASK_STATUSES.map((item) => (
                  <option key={item} value={item}>
                    {item === 'not_started'
                      ? t.notStarted
                      : item === 'in_progress'
                        ? t.inProgress
                        : item === 'waiting'
                          ? t.waiting
                          : t.completed}
                  </option>
                ))}
              </Select>
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !taskTitle.trim()}>{t.saveTask}</Button>
          </form>
        </section>
      ) : null}

      {panel === 'assign' ? (
        <section className="crm-verify-detail__section" data-testid="contact-assign-panel">
          <h2>{t.assignOwner}</h2>
          <p className="crm-contact-card__meta-line">{t.currentOwner}: {ownerName || '—'}</p>
          <form onSubmit={submitOwner} className="crm-contact-card__panel">
            <Select label={t.newOwner} value={ownerId} onChange={(event) => setOwnerId(event.target.value)}>
              <option value="">{t.selectUser}</option>
              {users.map((item) => (
                <option key={item.id} value={item.id}>{item.full_name}</option>
              ))}
            </Select>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !ownerId}>{t.saveAssignment}</Button>
          </form>
        </section>
      ) : null}

      <nav className="crm-contact-card__tabs crm-person-tabs" aria-label="Person card tabs" data-testid="person-card-tabs">
        {PERSON_TABS.map((item) => {
          const count =
            item === 'purchases' ? currentPurchases.length
            : item === 'history' ? commEntries.length
            : item === 'documents' ? visibleDocuments.length
            : item === 'tasks' ? followUpEntries.length
            : null;
          return (
            <button
              key={item}
              type="button"
              className={tab === item ? 'is-active' : undefined}
              data-testid={`contact-tab-${item}`}
              onClick={() => selectTab(item)}
            >
              {t.tabs[item]}
              {count != null ? ` (${count})` : ''}
            </button>
          );
        })}
      </nav>

      {tab === 'overview' ? (
        <>
          <section className="crm-person-kpis" data-testid="contact-summary-cards">
            <button type="button" className="crm-person-kpi" onClick={() => selectTab('purchases')}>
              <span>{t.totalPurchases}</span>
              <strong>{currentPurchases.length}</strong>
              {projectCount ? <small>{projectCount} {t.inProjects}</small> : null}
            </button>
            <button type="button" className="crm-person-kpi" onClick={() => selectTab('history')}>
              <span>{t.communication}</span>
              <strong>{commEntries.length}</strong>
              {lastCommChannel ? <small>{lastCommChannel}</small> : null}
            </button>
            <button type="button" className="crm-person-kpi" onClick={() => selectTab('history')}>
              <span>{t.lastContact}</span>
              <strong>{relativeLabel(contact.last_contact_at || lastComm?.created_at, locale, t) || '—'}</strong>
              {lastCommChannel ? <small>{lastCommChannel}</small> : null}
            </button>
            <div className="crm-person-kpi">
              <span>{t.status}</span>
              <strong className={isJunk ? '' : 'is-live'}>{isJunk ? t.junk : t.active}</strong>
              {contact.updated_at ? <small>{t.lastUpdate}: {formatShortDate(contact.updated_at, locale)}</small> : null}
            </div>
            <div className="crm-person-kpi" data-testid="contact-summary-tags">
              <span>{t.tags}</span>
              <div className="crm-person-kpi__tags">
                {tags.length ? tags.map((tag) => <em key={tag.id}>{tag.name}</em>) : <strong>—</strong>}
              </div>
            </div>
          </section>

          <section className="crm-person-workspace" data-testid="contact-overview">
            <article className="crm-person-panel">
              <div className="crm-person-panel__head">
                <h2>{t.general}</h2>
                {canUpdate ? (
                  <button type="button" onClick={() => togglePanel('edit')}>{t.edit}</button>
                ) : null}
              </div>
              <dl className="crm-person-info">
                <InfoRow label={t.displayName} value={contact.display_name} />
                <InfoRow label={t.firstName} value={contact.first_name} />
                <InfoRow label={t.lastName} value={contact.last_name} />
                <InfoRow label={t.phone} value={contact.primary_phone} />
                <InfoRow label={t.extraPhone} value={(contact.secondary_phones ?? []).join(', ')} />
                <InfoRow label={t.whatsapp} value={contact.whatsapp && contact.whatsapp !== contact.primary_phone ? contact.whatsapp : null} />
                <InfoRow label={t.email} value={contact.primary_email} />
                <InfoRow label={t.secondEmail} value={(contact.secondary_emails ?? []).join(', ')} />
                <InfoRow label={t.address} value={[contact.address_line1, contact.address_line2].filter(Boolean).join(', ')} />
                <InfoRow label={t.city} value={contact.city} />
                <InfoRow label={t.region} value={contact.state_province} />
                <InfoRow label={t.country} value={contact.country} />
                <InfoRow
                  label={t.language}
                  value={typeof contact.communication_prefs?.language === 'string' ? contact.communication_prefs.language : null}
                />
                {canViewFinancial ? (
                  <InfoRow
                    label={t.buyerBudget}
                    value={
                      contact.buyer_profile?.budget_min != null || contact.buyer_profile?.budget_max != null
                        ? [contact.buyer_profile?.budget_min, contact.buyer_profile?.budget_max].filter((item) => item != null).join(' – ')
                        : null
                    }
                  />
                ) : null}
                <InfoRow label={t.company} value={contact.organization_name || contact.company_name} />
                <InfoRow
                  label={t.role}
                  value={(contact.contact_types.length ? contact.contact_types : [contact.contact_type])
                    .map((type) => roleLabel(type, t))
                    .join(', ')}
                />
                <InfoRow label={t.source} value={sourceLabel} />
                <InfoRow label={t.referrer} value={referrerName} />
                <InfoRow label={t.ownerUser} value={ownerName} />
                <InfoRow label={t.createdAt} value={formatShortDate(contact.created_at, locale)} />
                <InfoRow label={t.updatedAt} value={formatShortDate(contact.updated_at, locale)} />
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
                  <h2>{t.purchases}</h2>
                  <button type="button" onClick={() => selectTab('purchases')}>{t.viewAll}</button>
                </div>
                {currentPurchases.length ? renderPurchaseTable(currentPurchases.slice(0, 3), 'current-purchases', '') : <p>{t.noPurchases}</p>}
              </article>
              <article className="crm-person-panel" data-testid="contact-tasks-preview">
                <div className="crm-person-panel__head">
                  <h2>{t.tasksHeading}</h2>
                  <button type="button" onClick={() => { setTaskKind('task'); togglePanel('task'); }}>{t.createTask}</button>
                </div>
                {followUpEntries.length ? renderTaskRows(followUpEntries, true) : <p>{t.noTasks}</p>}
              </article>
              <article className="crm-person-panel">
                <div className="crm-person-panel__head">
                  <h2>{t.documents}</h2>
                  <button type="button" onClick={() => selectTab('documents')}>{t.viewAll}</button>
                </div>
                {visibleDocuments.length ? (
                  <ul className="crm-contact-card__docs">
                    {visibleDocuments.slice(0, 4).map((doc) => (
                      <li key={doc.id}>
                        <a href={`/workspaces/crm/documents/${doc.id}`}>{doc.original_file_name || doc.title}</a>
                        <small>
                          {[doc.document_type, doc.created_at ? relativeLabel(doc.created_at, locale, t) : null]
                            .filter(Boolean)
                            .join(' · ')}
                        </small>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>{t.noDocuments}</p>
                )}
              </article>
            </div>
          </section>
        </>
      ) : null}

      {tab === 'purchases' ? (
        <section className="crm-verify-detail__section" data-testid="satin-aldiklari">
          <h2>{t.purchases} <span>{currentPurchases.length}</span></h2>
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
                      {t.agreementStatus}: {agreement.status}
                      {agreement.agreement_date ? ` · ${t.agreementDate}: ${agreement.agreement_date}` : ''}
                      {isReit
                        ? ` · ${t.investmentAmount}: ${agreement.investment_amount || '—'}`
                        : ` · ${t.unitNumber}: ${agreement.unit_number || '—'}`}
                      {!isReit && agreement.purchase_price ? ` · ${t.salePrice}: ${agreement.purchase_price}` : ''}
                      {!isReit && agreement.payment_amount ? ` · ${t.payment}: ${agreement.payment_amount}` : ''}
                      {!isReit && agreement.deposit ? ` · ${t.deposit}: ${agreement.deposit}` : ''}
                    </small>
                  </article>
                );
              })}
            </div>
          ) : (
            <p>{t.noPurchases}</p>
          )}
        </section>
      ) : null}

      {tab === 'tasks' ? (
        <section className="crm-verify-detail__section" data-testid="contact-tasks">
          <div className="crm-person-panel__head">
            <h2>{t.tasksPlan} <span>{followUpEntries.length}</span></h2>
            {canUpdate ? (
              <Button type="button" size="sm" onClick={() => { setTaskKind('task'); togglePanel('task'); }}>
                {t.createTask}
              </Button>
            ) : null}
          </div>
          {followUpEntries.length ? renderTaskRows(followUpEntries) : <p>{t.noTasks}</p>}
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
          heading={t.historyHeading}
        />
      ) : null}

      {tab === 'documents' ? (
        <section className="crm-verify-detail__section" data-testid="contact-documents">
          <h2>{t.documents} <span>{visibleDocuments.length}</span></h2>
          {!canViewDocuments ? (
            <p>{t.noDocumentView}</p>
          ) : documentsQuery.isLoading ? (
            <p>{t.loading}</p>
          ) : documents.length ? (
            <div data-testid="nedim-general-documents">
              <DocumentGallery
                documents={documents}
                entityType="crm_contact"
                entityId={contactId}
                canUpload={canUploadDocuments}
                canEditMeta={canUploadDocuments}
                canUnlink={canUpdate}
                canArchive={canArchiveDocuments}
                onChanged={() => {
                  void queryClient.invalidateQueries({ queryKey: ['crm', 'contacts', 'documents', contactId] });
                }}
              />
            </div>
          ) : (
            <p>{t.noDocuments}</p>
          )}
          {canLinkDocuments ? (
            <form onSubmit={submitLinkDocument} className="crm-contact-card__panel">
              <Input
                label={t.linkDocument}
                value={linkDocumentId}
                onChange={(event) => setLinkDocumentId(event.target.value)}
              />
              <Button type="submit" size="sm" variant="secondary" disabled={actionMutation.isPending || !linkDocumentId.trim()}>
                {t.linkDocumentAction}
              </Button>
            </form>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
