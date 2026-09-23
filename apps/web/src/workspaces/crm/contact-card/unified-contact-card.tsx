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
import { createActivity, createFollowUp, createTask } from '@/workspaces/crm/api/activities';
import {
  assignContactOwner,
  changeContactStatus,
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
import { PilotHistoryStream } from '@/workspaces/crm/contact-card/history-stream';
import { taskStatusLabel } from '@/workspaces/crm/contact-card/history-html';
import { UnitHistoryInline } from '@/workspaces/crm/contact-card/unit-history';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';
import { CRM_CONTACT_TYPES, type CrmContactType, type CrmPurchaseSummary } from '@/workspaces/crm/types';
import {
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

type Panel = 'edit' | 'note' | 'task' | 'assign' | null;

const PERSON_TABS = [
  { id: 'overview', label: 'Özet' },
  { id: 'history', label: 'Geçmiş' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'purchases', label: 'Yatırımları / Satın Aldıkları' },
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

function PurchaseHistoryRow({
  purchase,
  onOpen,
}: {
  purchase: CrmPurchaseSummary;
  onOpen: (agreementId: string) => void;
}) {
  const isReit = purchase.project_group === 'reit';
  const historical = Boolean(purchase.is_historical_unit_change);
  return (
    <article
      className={`crm-purchase-list__item crm-purchase-list__item--stack${historical ? ' is-historical' : ' is-current-purchase'}`}
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
      <strong>{investmentRowTitle(purchase)}</strong>
      {purchase.unit_change_status ? (
        <span className="crm-agreements-tag">{purchase.unit_change_status}</span>
      ) : null}
      {!historical && purchase.unit_history && purchase.unit_history.length > 1 ? (
        <UnitHistoryInline steps={purchase.unit_history} />
      ) : null}
      {historical ? (
        <span className="crm-purchase-list__unit">
          {purchase.unit_number || purchase.original_unit}
          {purchase.final_unit ? ` → ${purchase.final_unit}` : ''}
        </span>
      ) : null}
      {!isReit && purchase.unit_number && purchase.project_group !== '1812_h_pl' && !historical ? (
        <span className="crm-purchase-list__unit">Daire {purchase.unit_number}</span>
      ) : null}
      {!isReit && !historical ? (
        <span className="crm-purchase-list__amount">
          {(purchase.amount_label || purchase.amount || '').replace(' USD', '') || '—'}
        </span>
      ) : null}
      {purchase.stage && !historical ? <span className="crm-purchase-list__unit">Aşama: {purchase.stage}</span> : null}
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
      {purchase.hemen_kira ? (
        <span className="crm-purchase-list__unit">Hemen Kira</span>
      ) : null}
    </article>
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
  const whatsappMessages = useMemo(() => sortWhatsappConversation(timeline), [timeline]);

  if (authLoading || query.isLoading) return <LoadingState label="Loading…" />;
  if (!canRead) return <EmptyState title="CRM" description="Access denied" />;
  if (query.isError || !contact) {
    return <ErrorState title="CRM" message={query.error?.message ?? 'Kişi yüklenemedi'} />;
  }

  const categories = [
    contact.is_agent ? 'Acenta' : 'Müşteri',
    ...(contact.has_agreements ? ['Anlaşmalı'] : []),
  ];
  const isJunk = contact.status === 'archived';
  const ownerName = contact.owner_name ?? contact.bitrix_responsible ?? '—';
  const purchases = contact.purchases ?? [];
  const currentPurchases = purchases.filter((item) => !item.is_historical_unit_change);
  const previousPurchases = purchases.filter((item) => item.is_historical_unit_change);
  const documents = documentsQuery.data ?? [];
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
            {currentPurchases[0] ? (
              <p className="crm-contact-card__pilot-identity" data-testid="semrin-pilot-identity">
                {[
                  currentPurchases[0].project_group === '1812_h_pl' ? '1812 H Place' : currentPurchases[0].project_label,
                  currentPurchases[0].unit_number ? `Unit ${currentPurchases[0].unit_number}` : null,
                ]
                  .filter(Boolean)
                  .join(' · ')}
                {currentPurchases[0].participants
                  .filter((item) => item.contact_id !== contactId)
                  .filter(
                    (item, index, list) => list.findIndex((row) => row.display_name === item.display_name) === index,
                  )
                  .map((item) => ` · ilgili sahip: ${item.display_name}`)
                  .join('')}
              </p>
            ) : null}
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
        <div className="crm-contact-card__tags" data-testid="contact-tags">
          {(contact.tag_items ?? []).map((tag) => (
            <span key={tag.id} className="crm-contact-card__tag">
              <button
                type="button"
                onClick={() => router.push(`/workspaces/crm/contacts?tag=${tag.id}`)}
              >
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
              <option value="">Etiket ekle</option>
              {(tagsQuery.data?.items ?? [])
                .filter((tag) => !(contact.tag_items ?? []).some((item) => item.id === tag.id))
                .map((tag) => (
                  <option key={tag.id} value={tag.id}>
                    {tag.name}
                  </option>
                ))}
            </select>
          ) : null}
        </div>
        {(() => {
          const flags = [
            /BILGI_EKSIK/i.test(contact.notes || '') || (!contact.primary_phone && !contact.primary_email)
              ? 'BILGI_EKSIK'
              : null,
            /INCELEME_GEREKLI/i.test(contact.notes || '') || contact.review_required || contact.bitrix_history?.review_required
              ? 'INCELEME_GEREKLI'
              : null,
          ].filter(Boolean) as string[];
          return flags.length ? (
            <div className="crm-contact-card__flags" data-testid="contact-flags">
              {flags.map((flag) => (
                <span key={flag}>{flag}</span>
              ))}
            </div>
          ) : null;
        })()}
        {canUpdate ? (
          <div className="crm-contact-card__actions">
            <Button type="button" size="sm" variant={panel === 'edit' ? 'primary' : 'secondary'} data-testid="contact-edit-open" onClick={() => togglePanel('edit')}>Düzenle</Button>
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
          {PERSON_TABS.map((item) => (
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

      {showPurchases && purchases.length ? (
        <section className="crm-verify-detail__section" data-testid="satin-aldiklari">
          <h2>
            {investmentSectionTitle(currentPurchases)} <span>{currentPurchases.length}</span>
          </h2>
          {currentPurchases.length ? (
            <div className="crm-purchase-history-group" data-testid="current-purchases">
              <h3>Güncel Satın Alma</h3>
              <div className="crm-verify-detail__records crm-purchase-list">
                {currentPurchases.map((purchase) => (
                  <PurchaseHistoryRow key={purchase.agreement_id} purchase={purchase} onOpen={openPurchaseRow} />
                ))}
              </div>
            </div>
          ) : null}
          {previousPurchases.length ? (
            <div className="crm-purchase-history-group" data-testid="previous-units">
              <h3>Önceki Daireler</h3>
              <div className="crm-verify-detail__records crm-purchase-list">
                {previousPurchases.map((purchase) => (
                  <PurchaseHistoryRow key={purchase.agreement_id} purchase={purchase} onOpen={openPurchaseRow} />
                ))}
              </div>
            </div>
          ) : null}
        </section>
      ) : null}

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
                    {type}
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

      {showTasks ? (
        <section className="crm-verify-detail__section" data-testid="contact-tasks">
          <h2>
            Görevler <span>{timeline.filter((entry) => entry.activity_type === 'task').length}</span>
          </h2>
          {timeline.filter((entry) => entry.activity_type === 'task').length ? (
            <div className="crm-stream">
              {timeline
                .filter((entry) => entry.activity_type === 'task')
                .map((entry) => (
                  <article key={entry.id} className="crm-stream-card" data-testid="stream-task-card">
                    <div className="crm-stream-card__body">
                      <div className="crm-stream-card__top">
                        <strong>Görev</strong>
                        <time>{new Date(entry.created_at).toLocaleString(locale)}</time>
                      </div>
                      <p className="crm-stream-card__meta">
                        {taskStatusLabel(String(entry.metadata?.task_status || entry.status || ''))}
                      </p>
                      <h3>{entry.title}</h3>
                      <p>
                        Son tarih:{' '}
                        {typeof entry.metadata?.due_date === 'string'
                          ? new Date(entry.metadata.due_date).toLocaleString(locale)
                          : '—'}
                      </p>
                      <p>Sorumlu: {String(entry.metadata?.assigned_user_name || entry.actor_name || '—')}</p>
                      <div className="crm-stream-card__actions">
                        <Button type="button" size="sm" onClick={() => selectTab('history')}>
                          Aç
                        </Button>
                      </div>
                    </div>
                  </article>
                ))}
            </div>
          ) : (
            <p>Bu kişi için görev kaydı yok.</p>
          )}
        </section>
      ) : null}

      {tab === 'whatsapp' ? (
        <section className="crm-verify-detail__section" data-testid="contact-whatsapp">
          <h2>WhatsApp <span>{whatsappMessages.length}</span></h2>
          {whatsappMessages.length ? (
            <WhatsAppThread
              messages={whatsappMessages}
              locale={locale}
              documents={documents}
              testId="contact-whatsapp-thread"
            />
          ) : (
            <p>WhatsApp yazışması yok.</p>
          )}
        </section>
      ) : null}

      {showHistory ? (
        <PilotHistoryStream
          entries={timeline}
          documents={documents}
          locale={locale}
          loading={timelineQuery.isLoading}
        />
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
        <h2>Belgeler <span>{documents.filter((doc) => !doc.hidden_from_view).length}</span></h2>
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
