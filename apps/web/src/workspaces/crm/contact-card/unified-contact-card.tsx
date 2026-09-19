'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, Input, LoadingState, Select, StatusChip, TextArea } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { fetchUsers, hasPermission, type UserRecord } from '@/lib/api/auth';
import { fetchDocumentsByEntity, linkDocument, type Document } from '@/lib/api/documents';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { completeTask, createActivity, createFollowUp, createTask } from '@/workspaces/crm/api/activities';
import {
  assignContactOwner,
  changeContactStatus,
  fetchContactTimeline,
  fetchJunkReasons,
  updateContact,
  type ContactTimelineEntry,
} from '@/workspaces/crm/api/contacts';
import { notifyContactUpdated, useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';
import { CRM_CONTACT_TYPES, type CrmContactType, type CrmPurchaseSummary } from '@/workspaces/crm/types';
import {
  bitrixHistory,
  sortWhatsappConversation,
  WhatsAppThread,
} from '@/workspaces/crm/contact-card/whatsapp-thread';

import '@/app/workspaces/crm/contacts/_components/ds/contacts-ds.css';
import './contact-card.css';

const NOTE_TYPES = [
  { value: 'phone_call', label: 'Telefon Görüşmesi' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'email', label: 'E-posta' },
  { value: 'meeting', label: 'Toplantı' },
  { value: 'note', label: 'Genel Not' },
] as const;

const TASK_STATUSES = [
  { value: 'not_started', label: 'Başlamadı' },
  { value: 'in_progress', label: 'Devam ediyor' },
  { value: 'waiting', label: 'Beklemede' },
  { value: 'completed', label: 'Tamamlandı' },
] as const;

const ACTIVITY_TYPE_LABELS: Record<string, string> = {
  phone_call: 'Arama',
  whatsapp: 'WhatsApp',
  sms: 'SMS',
  email: 'E-posta',
  meeting: 'Toplantı',
  note: 'Not',
  comment: 'Yorum',
  task: 'Görev',
  follow_up: 'Takip',
  system_event: 'Durum/Aşama',
  automation_event: 'Durum/Aşama',
  contract_signed: 'Anlaşma',
  other: 'Diğer',
};

const HISTORY_FILTERS = [
  { id: 'all', label: 'Tümü' },
  { id: 'comment', label: 'Yorumlar' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'sms', label: 'SMS' },
  { id: 'task', label: 'Görevler' },
  { id: 'meeting', label: 'Toplantılar' },
  { id: 'email', label: 'E-posta' },
  { id: 'phone_call', label: 'Aramalar' },
] as const;

type HistoryFilter = (typeof HISTORY_FILTERS)[number]['id'];
type Panel = 'edit' | 'note' | 'task' | 'assign' | null;

const PERSON_TABS = [
  { id: 'overview', label: 'Özet' },
  { id: 'history', label: 'Geçmiş' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'purchases', label: 'Satın Aldıkları' },
  { id: 'documents', label: 'Belgeler' },
  { id: 'tasks', label: 'Görevler' },
] as const;

type PersonTab = (typeof PERSON_TABS)[number]['id'];

function investmentSectionTitle(purchases: CrmPurchaseSummary[]) {
  return purchases.some((item) => item.project_group === 'reit')
    ? 'YATIRIMLARI / SATIN ALDIKLARI'
    : 'SATIN ALDIKLARI';
}

function investmentRowTitle(purchase: CrmPurchaseSummary) {
  if (purchase.project_group === 'reit') {
    const amount = (purchase.amount_label || '').replace(/^\$/, '').trim() || purchase.amount || '';
    return amount ? `REIT · ${amount}` : 'REIT';
  }
  if (purchase.project_group === '1812_h_pl') {
    return purchase.unit_number ? `1812 H Place · ${purchase.unit_number}` : '1812 H Place';
  }
  return purchase.project_label;
}

function historyTypeLabel(entry: ContactTimelineEntry): string {
  if (entry.title.startsWith('Durum ') || entry.activity_type === 'system_event' || entry.activity_type === 'automation_event') {
    return 'Durum/Aşama';
  }
  if (entry.imported_historical_comment) return 'Yorum';
  return ACTIVITY_TYPE_LABELS[entry.activity_type] ?? entry.title;
}

function matchesHistoryFilter(entry: ContactTimelineEntry, filter: HistoryFilter): boolean {
  if (filter === 'all') return true;
  if (filter === 'comment') return entry.activity_type === 'comment' || Boolean(entry.imported_historical_comment);
  if (filter === 'meeting') {
    return ['meeting', 'zoom_meeting', 'teams_meeting', 'investor_meeting', 'construction_meeting'].includes(entry.activity_type);
  }
  return entry.activity_type === filter;
}

function conversationMessages(entries: ContactTimelineEntry[], focus: ContactTimelineEntry): ContactTimelineEntry[] {
  const history = bitrixHistory(focus);
  const chatId = history?.chat_id;
  const messages = entries.filter((entry) => {
    if (entry.activity_type !== 'whatsapp') return false;
    const meta = bitrixHistory(entry);
    if (meta?.kind !== 'whatsapp_message') return false;
    if (chatId) return String(meta.chat_id || '') === String(chatId);
    return true;
  });
  return [...messages].sort((a, b) => a.created_at.localeCompare(b.created_at));
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
  const documentsQuery = useQuery({
    queryKey: ['crm', 'contacts', 'documents', contactId],
    queryFn: async () => {
      const [crmDocs, contactDocs] = await Promise.all([
        fetchDocumentsByEntity('crm_contact', contactId).catch(() => ({ items: [] as Document[] })),
        fetchDocumentsByEntity('contact', contactId).catch(() => ({ items: [] as Document[] })),
      ]);
      const seen = new Set<string>();
      return [...crmDocs.items, ...contactDocs.items].filter((doc) => {
        if (seen.has(doc.id)) return false;
        seen.add(doc.id);
        return true;
      });
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
  const [company, setCompany] = useState('');
  const [position, setPosition] = useState('');
  const [statusValue, setStatusValue] = useState<'active' | 'archived'>('active');
  const [junkReason, setJunkReason] = useState('');
  const [roles, setRoles] = useState<CrmContactType[]>([]);
  const [ownerId, setOwnerId] = useState('');
  const [followUpAt, setFollowUpAt] = useState('');
  const [note, setNote] = useState('');
  const [noteType, setNoteType] = useState<(typeof NOTE_TYPES)[number]['value']>('phone_call');
  const [noteAt, setNoteAt] = useState(nowLocal);
  const [noteNeedsFollowUp, setNoteNeedsFollowUp] = useState(false);
  const [noteFollowUpAt, setNoteFollowUpAt] = useState('');
  const [taskTitle, setTaskTitle] = useState('');
  const [taskDescription, setTaskDescription] = useState('');
  const [taskAssignee, setTaskAssignee] = useState('');
  const [taskDue, setTaskDue] = useState('');
  const [taskStatus, setTaskStatus] = useState<(typeof TASK_STATUSES)[number]['value']>('not_started');
  const [linkDocumentId, setLinkDocumentId] = useState('');
  const [historyFilter, setHistoryFilter] = useState<HistoryFilter>('all');
  const [whatsappFocus, setWhatsappFocus] = useState<ContactTimelineEntry | null>(null);
  const [tab, setTab] = useState<PersonTab>('overview');
  const contact = query.data;

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const value = new URLSearchParams(window.location.search).get('tab');
    if (PERSON_TABS.some((item) => item.id === value)) {
      setTab(value as PersonTab);
    }
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
    setExtraEmails((contact.secondary_emails ?? []).join(', '));
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
  const filteredTimeline = useMemo(
    () => timeline.filter((entry) => matchesHistoryFilter(entry, historyFilter)),
    [timeline, historyFilter],
  );
  const timelineGroups = useMemo(() => {
    const groups: { label: string; items: ContactTimelineEntry[] }[] = [];
    for (const entry of filteredTimeline) {
      const label = new Date(entry.created_at).toLocaleDateString(locale, {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
      const last = groups[groups.length - 1];
      if (!last || last.label !== label) groups.push({ label, items: [entry] });
      else last.items.push(entry);
    }
    return groups;
  }, [filteredTimeline, locale]);
  const whatsappThread = useMemo(
    () => (whatsappFocus ? conversationMessages(timeline, whatsappFocus) : []),
    [timeline, whatsappFocus],
  );
  const whatsappMessages = useMemo(() => sortWhatsappConversation(timeline), [timeline]);
  const allOpenTasks = (contact?.crm_activities ?? []).filter(
    (activity) => activity.activity_type === 'task' && activity.status !== 'completed' && activity.task_status !== 'completed',
  );

  if (authLoading || query.isLoading) return <LoadingState label="Loading…" />;
  if (!canRead) return <EmptyState title="CRM" description="Access denied" />;
  if (query.isError || !contact) {
    return <ErrorState title="CRM" message={query.error?.message ?? 'Contact unavailable'} />;
  }

  const categories = [
    contact.is_agent ? 'Acenta' : 'Müşteri',
    ...(contact.has_agreements ? ['Anlaşmalı'] : []),
  ];
  const isJunk = contact.status === 'archived';
  const ownerName = contact.owner_name ?? contact.bitrix_responsible ?? '—';
  const purchases = contact.purchases ?? [];
  const documents = documentsQuery.data ?? [];
  const openTasks = allOpenTasks;
  const showHistory = tab === 'history';
  const showPurchasesOnOverview = purchases.length > 0;
  const showPurchases = tab === 'purchases' || (tab === 'overview' && showPurchasesOnOverview);
  const showDocuments = tab === 'documents';
  const showTasks = tab === 'tasks';

  const openPurchaseRow = (agreementId: string) => {
    openPurchase(agreementId);
  };

  const selectTab = (next: PersonTab) => {
    setTab(next);
    if (typeof window === 'undefined') return;
    const url = new URL(window.location.href);
    url.searchParams.set('tab', next);
    window.history.replaceState(null, '', `${url.pathname}${url.search}`);
  };

  const togglePanel = (next: Panel) => setPanel((current) => (current === next ? null : next));

  const submitEdit = (event: FormEvent) => {
    event.preventDefault();
    actionMutation.mutate(async () => {
      await updateContact(contactId, {
        display_name: displayName.trim() || contact.display_name,
        primary_phone: phone.trim() || null,
        secondary_phones: splitList(extraPhones),
        primary_email: email.trim() || null,
        secondary_emails: splitList(extraEmails),
        organization_name: company.trim() || null,
        job_title: position.trim() || null,
        status: statusValue,
        junk_reason: statusValue === 'archived' ? junkReason.trim() || null : contact.junk_reason,
        contact_type: roles[0] ?? contact.contact_type,
        contact_types: roles,
        owner_user_id: ownerId || undefined,
        next_follow_up_at: followUpAt ? toIso(followUpAt) : null,
      });
      setPanel(null);
    });
  };

  const submitNote = (event: FormEvent) => {
    event.preventDefault();
    if (!note.trim()) return;
    const typeLabel = NOTE_TYPES.find((item) => item.value === noteType)?.label ?? 'Not';
    actionMutation.mutate(async () => {
      await createActivity({
        entity_type: 'contact',
        entity_id: contactId,
        activity_type: noteType,
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
    actionMutation.mutate(async () => {
      await createTask({
        entity_type: 'contact',
        entity_id: contactId,
        activity_type: 'task',
        title: taskTitle.trim(),
        description: taskDescription.trim() || undefined,
        assigned_user_id: taskAssignee || user?.id,
        due_date: taskDue ? toIso(taskDue) : undefined,
        task_status: taskStatus,
        status: taskStatus === 'completed' ? 'completed' : 'planned',
      });
      setTaskTitle('');
      setTaskDescription('');
      setTaskDue('');
      setTaskStatus('not_started');
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

  return (
    <div
      className={`crm-verify-detail crm-contact-card crm-contact-card--${variant}`}
      data-testid="unified-contact-card"
    >
      {variant === 'page' ? (
        <Button className="crm-contact-card__back" variant="secondary" size="sm" onClick={() => window.history.back()}>
          <IhIcon name="chevronLeft" size={13} /> Kişilere dön
        </Button>
      ) : null}

      <header className="crm-verify-detail__hero crm-contact-card__hero">
        <div className="crm-contact-card__hero-top">
          <div>
            <h1>{contact.display_name}</h1>
            <p>
              {[contact.job_title, contact.organization_name, contact.bitrix_source_channel || contact.source || 'OS']
                .filter(Boolean)
                .join(' · ')}
            </p>
          </div>
          <StatusChip tone={isJunk ? 'default' : 'success'}>{isJunk ? 'Junk' : 'Aktif'}</StatusChip>
        </div>
        <p>
          {[contact.primary_phone, contact.primary_email].filter(Boolean).join(' · ') || '—'}
        </p>
        {canUpdate ? (
          <div className="crm-contact-card__actions">
            <Button type="button" size="sm" variant={panel === 'edit' ? 'primary' : 'secondary'} onClick={() => togglePanel('edit')}>Düzenle</Button>
            <Button type="button" size="sm" variant={panel === 'note' ? 'primary' : 'secondary'} onClick={() => togglePanel('note')}>Not Ekle</Button>
            <Button type="button" size="sm" variant={panel === 'task' ? 'primary' : 'secondary'} onClick={() => togglePanel('task')}>Görev Ekle</Button>
            <Button type="button" size="sm" variant={panel === 'assign' ? 'primary' : 'secondary'} onClick={() => togglePanel('assign')}>Sorumlu Ata</Button>
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
            {[contact.agent.brokerage_name || contact.organization_name, contact.primary_phone, contact.primary_email]
              .filter(Boolean)
              .join(' · ') || '—'}
            {' · '}
            {contact.agent.status === 'active' ? 'Aktif' : 'Pasif'}
          </div>
        </div>
      ) : null}

      {error ? <div className="crm-verify-detail__error">{error}</div> : null}

      <nav className="crm-contact-card__tabs" aria-label="Person card tabs" data-testid="person-card-tabs">
          {PERSON_TABS.filter((item) => item.id !== 'purchases' || purchases.length === 0).map((item) => (
            <button
              key={item.id}
              type="button"
              className={tab === item.id ? 'is-active' : undefined}
              data-testid={`contact-tab-${item.id}`}
              onClick={() => selectTab(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

      {tab === 'overview' ? (
        <section className="crm-verify-detail__section" data-testid="contact-overview">
          <h2>Özet</h2>
          <dl className="crm-contact-card__facts">
            <div><dt>Telefon</dt><dd>{contact.primary_phone || '—'}</dd></div>
            {contact.secondary_phones?.length ? (
              <div><dt>Diğer telefonlar</dt><dd>{contact.secondary_phones.join(', ')}</dd></div>
            ) : null}
            {contact.whatsapp ? <div><dt>WhatsApp</dt><dd>{contact.whatsapp}</dd></div> : null}
            <div><dt>E-posta</dt><dd>{contact.primary_email || '—'}</dd></div>
            {contact.secondary_emails?.length ? (
              <div><dt>Diğer e-postalar</dt><dd>{contact.secondary_emails.join(', ')}</dd></div>
            ) : null}
            {contact.organization_name ? <div><dt>Şirket</dt><dd>{contact.organization_name}</dd></div> : null}
            {contact.job_title ? <div><dt>Pozisyon</dt><dd>{contact.job_title}</dd></div> : null}
            <div><dt>Durum</dt><dd>{isJunk ? 'Junk' : 'Aktif'}</dd></div>
            <div><dt>Kategori / Roller</dt><dd>{[...categories, ...roles].join(' · ') || '—'}</dd></div>
            <div><dt>Kaynak</dt><dd>{contact.bitrix_source_channel || contact.source || 'OS'}</dd></div>
            <div><dt>Sorumlu</dt><dd>{ownerName}</dd></div>
            <div>
              <dt>Son aktivite</dt>
              <dd>{contact.last_contact_at ? new Date(contact.last_contact_at).toLocaleString(locale) : '—'}</dd>
            </div>
            <div>
              <dt>Sonraki takip</dt>
              <dd>{contact.next_follow_up_at ? new Date(contact.next_follow_up_at).toLocaleString(locale) : '—'}</dd>
            </div>
            {contact.address_line1 || contact.city || contact.country ? (
              <div>
                <dt>Adres</dt>
                <dd>
                  {[contact.address_line1, contact.address_line2, contact.city, contact.state_province, contact.postal_code, contact.country]
                    .filter(Boolean)
                    .join(', ')}
                </dd>
              </div>
            ) : null}
            {contact.notes ? (
              <div>
                <dt>Notlar</dt>
                <dd>{contact.notes}</dd>
              </div>
            ) : null}
            {(contact.profile_fields ?? [])
              .filter((item) => {
                const value = item.value.trim();
                if (!value) return false;
                if (item.label === 'Adres' && (contact.address_line1 || '').includes(value)) return false;
                if (item.label === 'Pozisyon' && contact.job_title === value) return false;
                return true;
              })
              .map((item) => (
                <div key={`${item.label}:${item.value}`}>
                  <dt>{item.label}</dt>
                  <dd>{item.value}</dd>
                </div>
              ))}
          </dl>
        </section>
      ) : null}

      {showPurchases && purchases.length ? (
        <section className="crm-verify-detail__section" data-testid="satin-aldiklari">
          <h2>{investmentSectionTitle(purchases)} <span>{purchases.length}</span></h2>
          <div className="crm-verify-detail__records crm-purchase-list">
            {purchases.map((purchase) => {
              const isReit = purchase.project_group === 'reit';
              return (
              <article
                key={purchase.agreement_id}
                className="crm-purchase-list__item crm-purchase-list__item--stack"
                data-testid={`purchase-row-${purchase.bitrix_deal_id || purchase.agreement_id}`}
                role="button"
                tabIndex={0}
                onClick={() => openPurchaseRow(purchase.agreement_id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    openPurchaseRow(purchase.agreement_id);
                  }
                }}
              >
                <strong>{investmentRowTitle(purchase)}</strong>
                {!isReit && purchase.unit_number && purchase.project_group !== '1812_h_pl' ? (
                  <span className="crm-purchase-list__unit">Daire {purchase.unit_number}</span>
                ) : null}
                {!isReit ? (
                  <span className="crm-purchase-list__amount">
                    {(purchase.amount_label || purchase.amount || '').replace(' USD', '')}
                  </span>
                ) : null}
                {purchase.stage ? <span className="crm-purchase-list__unit">Aşama: {purchase.stage}</span> : null}
                <small className="crm-purchase-list__owners">
                  {purchase.participants.length
                    ? purchase.participants
                        .map((item) => {
                          const share = item.ownership_pct?.replace(/\.00$/, '');
                          return `${item.display_name}${share ? ` ${share}%` : ''}`;
                        })
                        .join(' / ')
                    : purchase.owners_label || ''}
                </small>
              </article>
              );
            })}
          </div>
        </section>
      ) : null}

      {panel === 'edit' ? (
        <section className="crm-verify-detail__section" data-testid="contact-edit-panel">
          <h2>Kişiyi Düzenle</h2>
          <form onSubmit={submitEdit} className="crm-contact-card__panel">
            <div className="crm-contact-card__panel-grid">
              <Input label="Ad Soyad" value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
              <Input label="Telefon" value={phone} onChange={(event) => setPhone(event.target.value)} />
              <Input label="Ek telefonlar" value={extraPhones} onChange={(event) => setExtraPhones(event.target.value)} />
              <Input label="E-posta" value={email} onChange={(event) => setEmail(event.target.value)} />
              <Input label="Ek e-postalar" value={extraEmails} onChange={(event) => setExtraEmails(event.target.value)} />
              <Input label="Şirket" value={company} onChange={(event) => setCompany(event.target.value)} />
              <Input label="Pozisyon" value={position} onChange={(event) => setPosition(event.target.value)} />
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
                    {type}
                  </label>
                ))}
              </div>
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending}>Kaydet</Button>
          </form>
        </section>
      ) : null}

      {panel === 'note' ? (
        <section className="crm-verify-detail__section" data-testid="contact-note-panel">
          <h2>Not Ekle</h2>
          <form onSubmit={submitNote} className="crm-contact-card__panel">
            <TextArea label="Not / görüşme özeti" value={note} onChange={(event) => setNote(event.target.value)} />
            <div className="crm-contact-card__panel-grid">
              <Select label="Aktivite türü" value={noteType} onChange={(event) => setNoteType(event.target.value as typeof noteType)}>
                {NOTE_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>{item.label}</option>
                ))}
              </Select>
              <Input label="Tarih / saat" type="datetime-local" value={noteAt} onChange={(event) => setNoteAt(event.target.value)} />
              <Select label="Takip gerekli mi?" value={noteNeedsFollowUp ? 'yes' : 'no'} onChange={(event) => setNoteNeedsFollowUp(event.target.value === 'yes')}>
                <option value="no">Hayır</option>
                <option value="yes">Evet</option>
              </Select>
              {noteNeedsFollowUp ? (
                <Input label="Takip tarihi" type="datetime-local" value={noteFollowUpAt} onChange={(event) => setNoteFollowUpAt(event.target.value)} />
              ) : null}
            </div>
            <Button type="submit" size="sm" disabled={actionMutation.isPending || !note.trim()}>Notu kaydet</Button>
          </form>
        </section>
      ) : null}

      {panel === 'task' ? (
        <section className="crm-verify-detail__section" data-testid="contact-task-panel">
          <h2>Görev Ekle</h2>
          <form onSubmit={submitTask} className="crm-contact-card__panel">
            <Input label="Görev başlığı" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} />
            <TextArea label="Açıklama" value={taskDescription} onChange={(event) => setTaskDescription(event.target.value)} />
            <div className="crm-contact-card__panel-grid">
              <Select label="Atanan kullanıcı" value={taskAssignee} onChange={(event) => setTaskAssignee(event.target.value)}>
                <option value="">Seçin</option>
                {users.map((item) => (
                  <option key={item.id} value={item.id}>{item.full_name}</option>
                ))}
              </Select>
              <Input label="Son tarih" type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} />
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
          <p className="crm-contact-card__meta-line">Mevcut sorumlu: {ownerName}</p>
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

      {openTasks.length && showTasks ? (
        <section className="crm-verify-detail__section">
          <h2>Açık görevler <span>{openTasks.length}</span></h2>
          <div className="crm-verify-detail__records">
            {openTasks.map((task) => (
              <article key={task.id}>
                <strong>{task.title}</strong>
                <small>
                  {task.due_date ? new Date(task.due_date).toLocaleString(locale) : 'Tarihsiz'}
                  {task.task_status ? ` · ${task.task_status}` : ''}
                </small>
                {canUpdate ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={actionMutation.isPending}
                    onClick={() => actionMutation.mutate(async () => completeTask(task.id))}
                  >
                    Görevi tamamla
                  </Button>
                ) : null}
              </article>
            ))}
          </div>
        </section>
      ) : null}

      {tab === 'tasks' && !openTasks.length ? (
        <section className="crm-verify-detail__section" data-testid="contact-tasks">
          <h2>Görevler</h2>
          <p>Açık görev yok.</p>
        </section>
      ) : null}

      {tab === 'whatsapp' ? (
        <section className="crm-verify-detail__section" data-testid="contact-whatsapp">
          <h2>WhatsApp <span>{whatsappMessages.length}</span></h2>
          {whatsappMessages.length ? (
            <WhatsAppThread messages={whatsappMessages} locale={locale} testId="contact-whatsapp-thread" />
          ) : (
            <p>WhatsApp yazışması yok.</p>
          )}
        </section>
      ) : null}

      {showHistory ? (
      <section className="crm-verify-detail__section" data-testid="contact-timeline">
        <h2>Geçmiş & Notlar <span>{filteredTimeline.length}</span></h2>
        <div className="crm-contact-card__history-filters" data-testid="contact-timeline-filters">
          {HISTORY_FILTERS.map((filter) => (
            <button
              key={filter.id}
              type="button"
              className={historyFilter === filter.id ? 'is-active' : undefined}
              data-testid={`timeline-filter-${filter.id}`}
              onClick={() => setHistoryFilter(filter.id)}
            >
              {filter.label}
            </button>
          ))}
        </div>
        {timelineQuery.isLoading ? <p>Loading…</p> : null}
        {filteredTimeline.length ? (
          <div className="crm-verify-detail__records crm-verify-detail__timeline">
            {timelineGroups.map((group) => (
              <div key={group.label} className="crm-contact-card__timeline-day">
                <p className="crm-contact-card__date-sep">{group.label}</p>
                {group.items.map((entry) => {
                  const history = bitrixHistory(entry);
                  const typeLabel = historyTypeLabel(entry);
                  const isWhatsapp = entry.activity_type === 'whatsapp';
                  return (
                    <article
                      key={entry.id}
                      data-imported={entry.imported_historical_comment ? 'true' : 'false'}
                      data-activity-type={entry.activity_type}
                      className={isWhatsapp ? 'crm-contact-card__timeline-wa' : undefined}
                      onClick={isWhatsapp ? () => setWhatsappFocus(entry) : undefined}
                      onKeyDown={
                        isWhatsapp
                          ? (event) => {
                              if (event.key === 'Enter' || event.key === ' ') {
                                event.preventDefault();
                                setWhatsappFocus(entry);
                              }
                            }
                          : undefined
                      }
                      role={isWhatsapp ? 'button' : undefined}
                      tabIndex={isWhatsapp ? 0 : undefined}
                    >
                      <strong>
                        <span className={`crm-contact-card__type-chip crm-contact-card__type-chip--${entry.activity_type}`}>
                          {typeLabel}
                        </span>
                      </strong>
                      <small>
                        {new Date(entry.created_at).toLocaleString(locale)}
                        {entry.actor_name ? ` · ${entry.actor_name}` : history?.author_name ? ` · ${history.author_name}` : ''}
                        {history?.source ? ` · ${history.source}` : entry.imported_historical_comment ? ' · bitrix' : ''}
                      </small>
                      {entry.summary ? (
                        <p>{entry.summary}</p>
                      ) : entry.title && entry.title !== typeLabel && entry.title !== ACTIVITY_TYPE_LABELS[entry.activity_type] ? (
                        <p>{entry.title}</p>
                      ) : null}
                      {isWhatsapp && history?.open_channel_summary && !history.full_messages_recovered ? (
                        <p className="crm-contact-card__muted">Open Channel özeti — mesaj içeriği kurtarılamadı.</p>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            ))}
          </div>
        ) : <p>Kayıt yok</p>}
        {whatsappFocus ? (
          <div className="crm-contact-card__wa-drawer" data-testid="whatsapp-conversation">
            <div className="crm-contact-card__wa-panel">
              <div className="crm-contact-card__wa-head">
                <strong>WhatsApp konuşması</strong>
                <Button type="button" size="sm" variant="secondary" onClick={() => setWhatsappFocus(null)}>
                  Kapat
                </Button>
              </div>
              {whatsappThread.length ? (
                <div className="crm-contact-card__wa-thread">
                  {whatsappThread.map((message) => {
                    const meta = bitrixHistory(message);
                    const direction = String(meta?.direction || 'incoming');
                    return (
                      <div
                        key={message.id}
                        className={`crm-contact-card__wa-bubble crm-contact-card__wa-bubble--${direction}`}
                        data-testid="whatsapp-message"
                      >
                        <small>
                          {meta?.author_name || message.actor_name || (direction === 'outgoing' ? 'Giden' : direction === 'system' ? 'Sistem' : 'Gelen')}
                          {' · '}
                          {new Date(message.created_at).toLocaleString(locale)}
                        </small>
                        <p>{message.summary || message.title}</p>
                        {Number(meta?.attachment_count || 0) > 0 ? (
                          <em>Ek var (Bitrix dosyası indirilemedi)</em>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="crm-contact-card__muted">
                  {bitrixHistory(whatsappFocus)?.open_channel_summary
                    ? 'Bu Open Channel kaydı özet. Kurtarılmış mesaj içeriği yok.'
                    : 'Bu sohbet için kurtarılmış mesaj yok.'}
                </p>
              )}
            </div>
          </div>
        ) : null}
      </section>
      ) : null}

      {showPurchases && !purchases.length ? (
      <section className="crm-verify-detail__section" data-testid="contact-agreements">
        <h2>Anlaşmalar / Yatırımlar <span>{contact.crm_agreements.length}</span></h2>
        {contact.crm_agreements.length ? (
          <div className="crm-verify-detail__records">
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
                    {agreement.amount_and_currency_amount
                      ? ` · ${agreement.amount_and_currency_label || 'Tutar ve para birimi'}: ${agreement.amount_and_currency_amount}${agreement.amount_and_currency_currency ? ` ${agreement.amount_and_currency_currency}` : ''}`
                      : ''}
                  </small>
                </article>
              );
            })}
          </div>
        ) : <p>Kayıt yok</p>}
      </section>
      ) : null}

      {showDocuments ? (
      <section className="crm-verify-detail__section" data-testid="contact-documents">
        <h2>Belgeler <span>{documents.length}</span></h2>
        {!canViewDocuments ? (
          <p>Belge görüntüleme yetkisi yok.</p>
        ) : documentsQuery.isLoading ? (
          <p>Loading…</p>
        ) : documents.length ? (
          <ul className="crm-contact-card__docs" data-testid="nedim-general-documents">
            {documents.map((doc) => (
              <li key={doc.id}>
                <a href={`/workspaces/crm/documents/${doc.id}`}>{doc.title}</a>
                <small>{doc.document_type} · v{doc.version_number}</small>
              </li>
            ))}
          </ul>
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
