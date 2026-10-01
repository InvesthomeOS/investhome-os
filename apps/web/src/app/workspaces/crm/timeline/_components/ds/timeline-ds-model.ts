import type { IhIconName } from '@/components/icons/ih-icons';
import type { CrmTimelineEntry } from '@/workspaces/crm/types/activities';

export type TimelineAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';
export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';

export type TimelineEntityKind =
  | 'people'
  | 'companies'
  | 'investors'
  | 'projects'
  | 'leads'
  | 'favorites';

export type TimelineEventCategory =
  | 'whatsapp'
  | 'email'
  | 'call'
  | 'meeting'
  | 'task'
  | 'note'
  | 'document'
  | 'lead'
  | 'investor'
  | 'project'
  | 'status'
  | 'construction'
  | 'payment'
  | 'contract'
  | 'inspection'
  | 'activity';

export type TimelineEventStatus =
  | 'completed'
  | 'planned'
  | 'scheduled'
  | 'in_progress'
  | 'cancelled'
  | 'missed'
  | 'deferred';

export type TimelineEntity = {
  id: string;
  kind: TimelineEntityKind;
  name: string;
  initials: string;
  avatarTone: TimelineAvatarTone;
  status: string;
  statusTone: StatusTone;
  parent?: string;
  favorite?: boolean;
  href?: string;
};

export type TimelineAttachment = {
  id: string;
  name: string;
  sizeLabel: string;
  kind: 'pdf' | 'docx' | 'image' | 'other';
};

export type TimelineRelatedRecord = {
  id: string;
  label: string;
  href: string;
};

export type TimelineEvent = {
  id: string;
  occurredAt: string;
  title: string;
  description: string;
  category: TimelineEventCategory;
  status: TimelineEventStatus;
  channel?: string;
  owner: string;
  ownerInitials: string;
  ownerTitle?: string;
  entityId: string;
  entityName: string;
  entityKind: TimelineEntityKind;
  entityStatus?: string;
  entityStatusTone?: StatusTone;
  notes?: string;
  attachments?: TimelineAttachment[];
  relatedRecords?: TimelineRelatedRecord[];
  href?: string;
  contactHref?: string;
  companyHref?: string;
  leadHref?: string;
  projectHref?: string;
  purchaseHref?: string;
  isSystem?: boolean;
  source: 'live' | 'fixture';
  recordSource?: string;
  personName?: string | null;
  projectLabel?: string | null;
  unitNumber?: string | null;
  agreementId?: string | null;
  documentId?: string | null;
  documentName?: string | null;
  sourceBadge?: string;
  eventKind?: string;
  priorityTier?: 'high' | 'normal';
  fullDescription?: string;
};

export type TimelineEntitySummary = {
  total: number;
  active: number;
  favorites: number;
};

export type TimelineDayGroup = {
  key: string;
  labelKey: 'today' | 'yesterday' | 'date';
  dateLabel: string;
  events: TimelineEvent[];
};

export type TimelineDsFilters = {
  search: string;
  status: TimelineEventStatus | '';
  category: TimelineEventCategory | '';
  owner: string;
  entityType: TimelineEntityKind | '' | 'all';
  dateFrom: string;
  dateTo: string;
  entityId: string | null;
  entityKindTab: TimelineEntityKind | 'all';
};

export type TimelineOpsFilters = {
  search: string;
  person: string;
  personId: string | null;
  projectGroup: string;
  eventKind: string;
  dateFrom: string;
  dateTo: string;
};

export const EMPTY_OPS_FILTERS: TimelineOpsFilters = {
  search: '',
  person: '',
  personId: null,
  projectGroup: '',
  eventKind: '',
  dateFrom: '',
  dateTo: '',
};

export const EVENT_KIND_OPTIONS = [
  'whatsapp',
  'email',
  'call',
  'meeting',
  'document',
  'purchase',
  'payment',
  'note',
  'task',
  'system',
] as const;

export const ENTITY_KIND_ORDER: Array<TimelineEntityKind | 'all'> = [
  'all',
  'people',
  'companies',
  'investors',
  'projects',
  'leads',
  'favorites',
];

export const TIMELINE_CATEGORIES: TimelineEventCategory[] = [
  'whatsapp',
  'email',
  'call',
  'meeting',
  'task',
  'note',
  'document',
  'lead',
  'investor',
  'project',
  'status',
  'construction',
  'payment',
  'contract',
  'inspection',
  'activity',
];

export const TIMELINE_STATUSES: TimelineEventStatus[] = [
  'completed',
  'planned',
  'scheduled',
  'in_progress',
  'cancelled',
  'missed',
  'deferred',
];

export const CATEGORY_ICON: Record<TimelineEventCategory, IhIconName> = {
  whatsapp: 'check',
  email: 'inbox',
  call: 'meeting',
  meeting: 'calendar',
  task: 'check',
  note: 'documents',
  document: 'documents',
  lead: 'target',
  investor: 'investors',
  project: 'projects',
  status: 'activity',
  construction: 'projects',
  payment: 'barChart',
  contract: 'documents',
  inspection: 'search',
  activity: 'activity',
};

export const CATEGORY_TONE: Record<TimelineEventCategory, StatusTone> = {
  whatsapp: 'success',
  email: 'info',
  call: 'info',
  meeting: 'warning',
  task: 'warning',
  note: 'default',
  document: 'default',
  lead: 'info',
  investor: 'success',
  project: 'info',
  status: 'default',
  construction: 'warning',
  payment: 'success',
  contract: 'info',
  inspection: 'warning',
  activity: 'default',
};

export const STATUS_TONE: Record<TimelineEventStatus, StatusTone> = {
  completed: 'success',
  planned: 'default',
  scheduled: 'info',
  in_progress: 'warning',
  cancelled: 'danger',
  missed: 'danger',
  deferred: 'warning',
};

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

export function avatarTone(seed: string): TimelineAvatarTone {
  const tones: TimelineAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i) * (i + 1)) % tones.length;
  }
  return tones[hash] ?? 'navy';
}

function mapApiCategory(type: string): TimelineEventCategory {
  const key = type.toLowerCase();
  if (key.includes('whatsapp')) return 'whatsapp';
  if (key.includes('email')) return 'email';
  if (key.includes('phone') || key.includes('call') || key === 'sms') return 'call';
  if (key.includes('meeting') || key.includes('zoom') || key.includes('teams') || key.includes('visit'))
    return 'meeting';
  if (key.includes('task') || key.includes('follow') || key.includes('reminder')) return 'task';
  if (key.includes('note') || key.includes('comment') || key.includes('discussion')) return 'note';
  if (key.includes('document') || key.includes('proposal')) return 'document';
  if (key.includes('payment') || key.includes('closing')) return 'payment';
  if (key.includes('contract') || key.includes('reservation')) return 'contract';
  if (key.includes('inspection')) return 'inspection';
  if (key.includes('construction')) return 'construction';
  if (key.includes('investor')) return 'investor';
  if (key.includes('lead')) return 'lead';
  if (key.includes('project') || key.includes('property')) return 'project';
  if (key.includes('system') || key.includes('automation') || key.includes('status')) return 'status';
  return 'activity';
}

function mapApiStatus(status: string | null): TimelineEventStatus {
  const key = (status ?? 'completed').toLowerCase();
  if (key === 'completed' || key === 'planned' || key === 'scheduled') return key;
  if (key === 'in_progress') return 'in_progress';
  if (key === 'cancelled') return 'cancelled';
  if (key === 'missed') return 'missed';
  if (key === 'deferred' || key === 'archived') return 'deferred';
  return 'completed';
}

function mapEntityKind(entityType: string | null): TimelineEntityKind {
  switch ((entityType ?? '').toLowerCase()) {
    case 'company':
      return 'companies';
    case 'investor':
      return 'investors';
    case 'project':
    case 'property':
      return 'projects';
    case 'opportunity':
      return 'leads';
    case 'contact':
    default:
      return 'people';
  }
}

function entityKindLabel(kind: TimelineEntityKind): string {
  switch (kind) {
    case 'companies':
      return 'Şirket';
    case 'investors':
      return 'Yatırımcı';
    case 'projects':
      return 'Proje';
    case 'leads':
      return 'Lead';
    case 'favorites':
      return 'Favori';
    case 'people':
    default:
      return 'Kişi';
  }
}

function extractEntityNameFromTitle(title: string): string | null {
  const dashed = title.split(/\s+[—–]\s+/);
  if (dashed.length >= 2) {
    const tail = dashed[dashed.length - 1]!.trim();
    if (tail.length >= 2) return tail;
  }
  const withMatch = title.match(/\b(?:with|ile)\s+(.+)$/i);
  if (withMatch?.[1]?.trim()) return withMatch[1]!.trim();
  const forMatch = title.match(/\b(?:for|için)\s+(.+)$/i);
  if (forMatch?.[1]?.trim()) return forMatch[1]!.trim();
  return null;
}

function metaString(meta: Record<string, unknown> | null | undefined, keys: string[]): string | null {
  if (!meta) return null;
  for (const key of keys) {
    const value = meta[key];
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
}

export function mapTimelineEntry(entry: CrmTimelineEntry): TimelineEvent {
  const meta = entry.metadata_json;
  const entityKind = mapEntityKind(entry.entity_type);
  const category = mapApiCategory(entry.activity_type);
  const entityId = entry.entity_id ?? entry.id.replace(/^(log|agreement|document)-/, '');
  const personName =
    (entry.person_name ?? '').trim() ||
    metaString(meta, ['entity_name', 'contact_name', 'person_name']) ||
    extractEntityNameFromTitle(entry.title);
  const safeName =
    personName &&
    !['contact', 'company', 'investor', 'project', 'lead', 'crm', 'unknown person', 'unknown'].includes(
      personName.toLowerCase(),
    )
      ? personName
      : null;
  const projectLabel = (entry.project_label ?? '').trim() || metaString(meta, ['project_label', 'project_name']);
  const unitNumber = (entry.unit_number ?? '').trim() || metaString(meta, ['unit_number', 'unit']);
  const actor =
    entry.actor_name?.trim() ||
    metaString(meta, ['actor_name', 'owner_name', 'assigned_user_name']) ||
    '';
  const eventKind = (entry.event_kind ?? mapKindFromCategory(category)).trim() || 'system';
  const sourceBadge = (entry.source_badge ?? '').trim() || sourceBadgeForKind(eventKind);
  const priorityTier = entry.priority_tier === 'high' ? 'high' : eventKind === 'purchase' || eventKind === 'payment' ? 'high' : 'normal';
  const summary = (entry.summary ?? entry.title ?? '').trim();
  const agreementId = entry.agreement_id ?? null;
  return {
    id: entry.id,
    occurredAt: entry.created_at,
    title: summary || entry.title,
    description: summary,
    category,
    status: mapApiStatus(entry.status),
    channel: eventKind === 'whatsapp' || eventKind === 'email' ? eventKind : undefined,
    owner: actor,
    ownerInitials: initials(actor || safeName || '?'),
    entityId,
    entityName: safeName ?? '',
    entityKind,
    href: entry.entity_id ? entityHref(entityKind, entry.entity_id) : '/workspaces/crm/timeline',
    contactHref: entityKind === 'people' && entry.entity_id ? `/workspaces/crm/contacts/${entry.entity_id}` : undefined,
    companyHref:
      entityKind === 'companies' && entry.entity_id ? `/workspaces/crm/companies/${entry.entity_id}` : undefined,
    purchaseHref:
      agreementId && entry.entity_id
        ? `/workspaces/crm/contacts/${entry.entity_id}/satin-alma/${agreementId}`
        : undefined,
    isSystem: entry.is_system_event,
    source: 'live',
    recordSource: entry.source,
    personName: safeName,
    projectLabel: projectLabel || null,
    unitNumber: unitNumber || null,
    agreementId,
    documentId: entry.document_id ?? null,
    documentName: entry.document_name ?? null,
    sourceBadge,
    eventKind,
    priorityTier,
    fullDescription: (entry.description ?? entry.summary ?? entry.title ?? '').trim(),
  };
}

function mapKindFromCategory(category: TimelineEventCategory): string {
  if (category === 'whatsapp' || category === 'email' || category === 'note' || category === 'task') return category;
  if (category === 'document' || category === 'payment') return category;
  if (category === 'contract') return 'purchase';
  return 'system';
}

function sourceBadgeForKind(kind: string): string {
  switch (kind) {
    case 'whatsapp':
      return 'WhatsApp';
    case 'email':
      return 'Email';
    case 'call':
      return 'Arama';
    case 'meeting':
      return 'Toplantı';
    case 'document':
      return 'Belge';
    case 'purchase':
      return 'Satın Alma';
    case 'payment':
      return 'Ödeme';
    case 'note':
      return 'Not';
    case 'task':
      return 'Görev';
    default:
      return 'Sistem';
  }
}

export type TimelineFeedRow =
  | { type: 'event'; event: TimelineEvent }
  | { type: 'cluster'; id: string; eventKind: string; sourceBadge: string; personName: string | null; events: TimelineEvent[] };

const CLUSTERABLE = new Set(['whatsapp', 'email']);

export function clusterCommunicationEvents(events: TimelineEvent[]): TimelineFeedRow[] {
  const rows: TimelineFeedRow[] = [];
  let index = 0;
  while (index < events.length) {
    const current = events[index]!;
    if (!CLUSTERABLE.has(current.eventKind)) {
      rows.push({ type: 'event', event: current });
      index += 1;
      continue;
    }
    const bucket: TimelineEvent[] = [current];
    let cursor = index + 1;
    while (cursor < events.length) {
      const next = events[cursor]!;
      if (
        next.eventKind === current.eventKind &&
        next.entityId === current.entityId &&
        CLUSTERABLE.has(next.eventKind)
      ) {
        bucket.push(next);
        cursor += 1;
        continue;
      }
      break;
    }
    if (bucket.length >= 3) {
      rows.push({
        type: 'cluster',
        id: `cluster-${current.eventKind}-${current.entityId}-${current.id}`,
        eventKind: current.eventKind,
        sourceBadge: current.sourceBadge,
        personName: current.personName,
        events: bucket,
      });
    } else {
      for (const event of bucket) rows.push({ type: 'event', event });
    }
    index = cursor;
  }
  return rows;
}

function entityHref(kind: TimelineEntityKind, id: string): string {
  switch (kind) {
    case 'people':
      return `/workspaces/crm/contacts/${id}`;
    case 'companies':
      return `/workspaces/crm/companies/${id}`;
    case 'leads':
      return '/workspaces/crm/leads';
    case 'projects':
      return '/workspaces/crm/projects';
    case 'investors':
      return '/workspaces/crm/relationships';
    default:
      return '/workspaces/crm/timeline';
  }
}

export function makeTimelineFixture(now = new Date()): {
  entities: TimelineEntity[];
  events: TimelineEvent[];
} {
  const day = (offset: number, hour: number, minute: number) => {
    const d = new Date(now);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + offset);
    d.setHours(hour, minute, 0, 0);
    return d.toISOString();
  };

  const entities: TimelineEntity[] = [
    {
      id: 'ent-isabella',
      kind: 'leads',
      name: 'Isabella Romano',
      initials: 'IR',
      avatarTone: 'violet',
      status: 'Nitelikli Lead',
      statusTone: 'success',
      parent: 'Romano Investments',
      favorite: true,
      href: '/workspaces/crm/leads',
    },
    {
      id: 'ent-harbor',
      kind: 'projects',
      name: 'Harbor Point',
      initials: 'HP',
      avatarTone: 'cyan',
      status: 'Aktif Proje',
      statusTone: 'info',
      parent: 'İnşaat',
      favorite: true,
      href: '/workspaces/crm/projects',
    },
    {
      id: 'ent-mehmet',
      kind: 'people',
      name: 'Mehmet Kaya',
      initials: 'MK',
      avatarTone: 'navy',
      status: 'Aktif Kişi',
      statusTone: 'info',
      parent: 'Kaya Holding',
      href: '/workspaces/crm/contacts',
    },
    {
      id: 'ent-temple',
      kind: 'projects',
      name: 'The Temple',
      initials: 'TT',
      avatarTone: 'amber',
      status: 'Satışta',
      statusTone: 'warning',
      parent: 'Kadıköy',
      href: '/workspaces/crm/projects',
    },
    {
      id: 'ent-ayse',
      kind: 'people',
      name: 'Ayşe Demir',
      initials: 'AD',
      avatarTone: 'green',
      status: 'Sahip',
      statusTone: 'default',
      parent: 'InvestHome',
      href: '/workspaces/crm/contacts',
    },
    {
      id: 'ent-romano',
      kind: 'companies',
      name: 'Romano Investments',
      initials: 'RI',
      avatarTone: 'rose',
      status: 'Aktif',
      statusTone: 'success',
      parent: 'Şirket',
      href: '/workspaces/crm/companies',
    },
    {
      id: 'ent-can',
      kind: 'investors',
      name: 'Can Özkan',
      initials: 'CÖ',
      avatarTone: 'amber',
      status: 'Yatırımcı',
      statusTone: 'info',
      parent: 'Bireysel',
      href: '/workspaces/crm/relationships',
    },
  ];

  const events: TimelineEvent[] = [
    {
      id: 'evt-wa-1',
      occurredAt: day(0, 10, 30),
      title: 'WhatsApp Mesajı',
      description: 'The Temple 2+1 plan PDF paylaşıldı; showroom uygunluğu soruldu.',
      category: 'whatsapp',
      status: 'completed',
      channel: 'WhatsApp',
      owner: 'Ayşe Demir',
      ownerInitials: 'AD',
      ownerTitle: 'Satış Danışmanı',
      entityId: 'ent-isabella',
      entityName: 'Isabella Romano',
      entityKind: 'leads',
      entityStatus: 'Nitelikli Lead',
      entityStatusTone: 'success',
      notes: 'Yurt dışı yatırımcı — peşinat esnekliği ve İngilizce sözleşme talep etti.',
      attachments: [
        { id: 'att-1', name: 'The_Temple_2plus1_plan.pdf', sizeLabel: '2.4 MB', kind: 'pdf' },
      ],
      relatedRecords: [
        { id: 'rel-1', label: 'The Temple', href: '/workspaces/crm/projects' },
        { id: 'rel-2', label: 'Lead · Isabella Romano', href: '/workspaces/crm/leads' },
      ],
      href: '/workspaces/crm/communication',
      contactHref: '/workspaces/crm/contacts',
      companyHref: '/workspaces/crm/companies',
      leadHref: '/workspaces/crm/leads',
      projectHref: '/workspaces/crm/projects',
      source: 'fixture',
    },
    {
      id: 'evt-email-1',
      occurredAt: day(0, 9, 45),
      title: 'Ödeme Planı E-postası',
      description: 'Detaylı ödeme planı ve sözleşme özeti iletildi.',
      category: 'email',
      status: 'completed',
      channel: 'E-posta',
      owner: 'Ayşe Demir',
      ownerInitials: 'AD',
      ownerTitle: 'Satış Danışmanı',
      entityId: 'ent-isabella',
      entityName: 'Isabella Romano',
      entityKind: 'leads',
      entityStatus: 'Nitelikli Lead',
      entityStatusTone: 'success',
      attachments: [
        { id: 'att-2', name: 'Odeme-Plani.docx', sizeLabel: '180 KB', kind: 'docx' },
      ],
      relatedRecords: [
        { id: 'rel-3', label: 'Lead · Isabella Romano', href: '/workspaces/crm/leads' },
      ],
      href: '/workspaces/crm/communication',
      leadHref: '/workspaces/crm/leads',
      source: 'fixture',
    },
    {
      id: 'evt-meeting-1',
      occurredAt: day(0, 14, 0),
      title: 'Showroom Toplantısı',
      description: 'The Temple showroom turu planlandı — 2+1 deniz manzaralı seçenekler.',
      category: 'meeting',
      status: 'scheduled',
      channel: 'Toplantı',
      owner: 'Mehmet Kaya',
      ownerInitials: 'MK',
      ownerTitle: 'Satış Müdürü',
      entityId: 'ent-temple',
      entityName: 'The Temple',
      entityKind: 'projects',
      entityStatus: 'Satışta',
      entityStatusTone: 'warning',
      relatedRecords: [
        { id: 'rel-4', label: 'The Temple', href: '/workspaces/crm/projects' },
      ],
      href: '/workspaces/crm/calendar',
      projectHref: '/workspaces/crm/projects',
      source: 'fixture',
    },
    {
      id: 'evt-task-1',
      occurredAt: day(-1, 16, 20),
      title: 'Takip Görevi',
      description: 'Showroom sonrası İngilizce takip e-postası hazırlanacak.',
      category: 'task',
      status: 'in_progress',
      owner: 'Can Özkan',
      ownerInitials: 'CÖ',
      ownerTitle: 'Operasyon',
      entityId: 'ent-isabella',
      entityName: 'Isabella Romano',
      entityKind: 'leads',
      entityStatus: 'Nitelikli Lead',
      entityStatusTone: 'success',
      notes: '24 saat içinde gönderilmeli.',
      href: '/workspaces/crm/tasks',
      leadHref: '/workspaces/crm/leads',
      source: 'fixture',
    },
    {
      id: 'evt-call-1',
      occurredAt: day(-1, 11, 10),
      title: 'Tanışma Araması',
      description: 'İlk keşif araması tamamlandı. Bütçe ve zaman çizelgesi netleşti.',
      category: 'call',
      status: 'completed',
      channel: 'Telefon',
      owner: 'Ayşe Demir',
      ownerInitials: 'AD',
      entityId: 'ent-mehmet',
      entityName: 'Mehmet Kaya',
      entityKind: 'people',
      entityStatus: 'Aktif Kişi',
      entityStatusTone: 'info',
      href: '/workspaces/crm/communication/calls',
      contactHref: '/workspaces/crm/contacts',
      source: 'fixture',
    },
    {
      id: 'evt-construction-1',
      occurredAt: day(-1, 8, 30),
      title: 'İnşaat Güncellemesi',
      description: 'Harbor Point blok A kaba inşaat %72 tamamlandı.',
      category: 'construction',
      status: 'completed',
      owner: 'Sistem',
      ownerInitials: 'SY',
      entityId: 'ent-harbor',
      entityName: 'Harbor Point',
      entityKind: 'projects',
      entityStatus: 'Aktif Proje',
      entityStatusTone: 'info',
      relatedRecords: [
        { id: 'rel-5', label: 'Harbor Point', href: '/workspaces/crm/projects' },
      ],
      href: '/workspaces/crm/projects',
      projectHref: '/workspaces/crm/projects',
      isSystem: true,
      source: 'fixture',
    },
    {
      id: 'evt-payment-1',
      occurredAt: day(-2, 15, 40),
      title: 'Peşinat Kaydı',
      description: 'Rezervasyon peşinatı muhasebe sistemine işlendi.',
      category: 'payment',
      status: 'completed',
      owner: 'Can Özkan',
      ownerInitials: 'CÖ',
      entityId: 'ent-can',
      entityName: 'Can Özkan',
      entityKind: 'investors',
      entityStatus: 'Yatırımcı',
      entityStatusTone: 'info',
      href: '/workspaces/crm/activities',
      source: 'fixture',
    },
    {
      id: 'evt-note-1',
      occurredAt: day(-2, 10, 5),
      title: 'İç Not',
      description: 'Romano Investments için İngilizce sözleşme taslağı isteniyor.',
      category: 'note',
      status: 'completed',
      owner: 'Ayşe Demir',
      ownerInitials: 'AD',
      entityId: 'ent-romano',
      entityName: 'Romano Investments',
      entityKind: 'companies',
      entityStatus: 'Aktif',
      entityStatusTone: 'success',
      href: '/workspaces/crm/notes',
      companyHref: '/workspaces/crm/companies',
      source: 'fixture',
    },
    {
      id: 'evt-doc-1',
      occurredAt: day(-3, 13, 15),
      title: 'Sözleşme Taslağı',
      description: 'İngilizce satış sözleşmesi taslağı yüklendi.',
      category: 'contract',
      status: 'planned',
      owner: 'Mehmet Kaya',
      ownerInitials: 'MK',
      entityId: 'ent-isabella',
      entityName: 'Isabella Romano',
      entityKind: 'leads',
      attachments: [
        { id: 'att-3', name: 'Sales_Agreement_EN_draft.pdf', sizeLabel: '890 KB', kind: 'pdf' },
      ],
      href: '/workspaces/crm/documents',
      leadHref: '/workspaces/crm/leads',
      source: 'fixture',
    },
    {
      id: 'evt-inspection-1',
      occurredAt: day(-3, 9, 0),
      title: 'Saha İncelemesi',
      description: 'Harbor Point ortak alan denetimi tamamlandı; eksikler raporlandı.',
      category: 'inspection',
      status: 'completed',
      owner: 'Sistem',
      ownerInitials: 'SY',
      entityId: 'ent-harbor',
      entityName: 'Harbor Point',
      entityKind: 'projects',
      isSystem: true,
      href: '/workspaces/crm/projects',
      projectHref: '/workspaces/crm/projects',
      source: 'fixture',
    },
  ];

  return { entities, events };
}

export function filterEntities(
  entities: TimelineEntity[],
  tab: TimelineEntityKind | 'all',
  search: string,
): TimelineEntity[] {
  const q = search.trim().toLowerCase();
  return entities.filter((entity) => {
    if (tab === 'favorites' && !entity.favorite) return false;
    if (tab !== 'all' && tab !== 'favorites' && entity.kind !== tab) return false;
    if (!q) return true;
    return (
      entity.name.toLowerCase().includes(q) ||
      (entity.parent ?? '').toLowerCase().includes(q) ||
      entity.status.toLowerCase().includes(q)
    );
  });
}

export function filterEvents(events: TimelineEvent[], filters: TimelineDsFilters): TimelineEvent[] {
  const q = filters.search.trim().toLowerCase();
  return events.filter((event) => {
    if (filters.entityId && event.entityId !== filters.entityId) return false;
    if (filters.status && event.status !== filters.status) return false;
    if (filters.category && event.category !== filters.category) return false;
    if (filters.owner && event.owner !== filters.owner) return false;
    if (
      filters.entityType &&
      filters.entityType !== 'all' &&
      event.entityKind !== filters.entityType
    ) {
      return false;
    }
    if (filters.dateFrom) {
      const from = new Date(`${filters.dateFrom}T00:00:00`);
      if (new Date(event.occurredAt) < from) return false;
    }
    if (filters.dateTo) {
      const to = new Date(`${filters.dateTo}T23:59:59.999`);
      if (new Date(event.occurredAt) > to) return false;
    }
    if (!q) return true;
    return (
      event.title.toLowerCase().includes(q) ||
      event.description.toLowerCase().includes(q) ||
      event.entityName.toLowerCase().includes(q) ||
      event.owner.toLowerCase().includes(q) ||
      event.category.toLowerCase().includes(q)
    );
  });
}

export function groupEventsByDay(
  events: TimelineEvent[],
  locale: string,
  now = new Date(),
): TimelineDayGroup[] {
  const startToday = new Date(now);
  startToday.setHours(0, 0, 0, 0);
  const startYesterday = new Date(startToday);
  startYesterday.setDate(startYesterday.getDate() - 1);

  const dateFmt = new Intl.DateTimeFormat(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  const sorted = [...events].sort(
    (a, b) => new Date(b.occurredAt).getTime() - new Date(a.occurredAt).getTime(),
  );

  const map = new Map<string, TimelineDayGroup>();
  for (const event of sorted) {
    const d = new Date(event.occurredAt);
    const dayStart = new Date(d);
    dayStart.setHours(0, 0, 0, 0);
    const key = dayStart.toISOString();
    let labelKey: TimelineDayGroup['labelKey'] = 'date';
    if (dayStart.getTime() === startToday.getTime()) labelKey = 'today';
    else if (dayStart.getTime() === startYesterday.getTime()) labelKey = 'yesterday';

    const existing = map.get(key);
    if (existing) {
      existing.events.push(event);
    } else {
      map.set(key, {
        key,
        labelKey,
        dateLabel: dateFmt.format(dayStart),
        events: [event],
      });
    }
  }

  return Array.from(map.values());
}

export function formatEventTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(
    new Date(iso),
  );
}

export function formatEventDateTime(iso: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(iso));
}

export function uniqueOwners(events: TimelineEvent[]): string[] {
  return [...new Set(events.map((e) => e.owner).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  );
}

export function summarizeEntities(entities: TimelineEntity[]): TimelineEntitySummary {
  const active = entities.filter((entity) => {
    if (entity.statusTone === 'success' || entity.statusTone === 'info') return true;
    return /aktif|active|nitelikli|qualified/i.test(entity.status);
  }).length;
  return {
    total: entities.length,
    active,
    favorites: entities.filter((entity) => Boolean(entity.favorite)).length,
  };
}

export function entitiesFromEvents(
  events: TimelineEvent[],
  seed: TimelineEntity[],
): TimelineEntity[] {
  const byId = new Map<string, TimelineEntity>();
  for (const event of events) {
    const existing = byId.get(event.entityId);
    const candidateName = event.entityName;
    const isGeneric =
      !candidateName ||
      ['Contact', 'Company', 'Investor', 'Project', 'Lead', 'CRM', 'people', 'companies', 'Kişi', 'Şirket', 'Yatırımcı', 'Proje'].includes(
        candidateName,
      );
    if (!existing) {
      byId.set(event.entityId, {
        id: event.entityId,
        kind: event.entityKind,
        name: candidateName,
        initials: initials(candidateName),
        avatarTone: avatarTone(event.entityId),
        status: event.entityStatus ?? entityKindLabel(event.entityKind),
        statusTone: event.entityStatusTone ?? 'info',
        href: event.contactHref ?? event.leadHref ?? event.projectHref ?? event.href,
      });
      continue;
    }
    const existingGeneric = ['Contact', 'Company', 'Investor', 'Project', 'Lead', 'CRM', 'Kişi', 'Şirket', 'Yatırımcı', 'Proje'].includes(
      existing.name,
    );
    if (existingGeneric && !isGeneric) {
      byId.set(event.entityId, {
        ...existing,
        name: candidateName,
        initials: initials(candidateName),
      });
    }
  }
  for (const entity of seed) {
    if (!byId.has(entity.id)) byId.set(entity.id, entity);
  }
  return Array.from(byId.values());
}

export function mergeTimelineData(
  live: CrmTimelineEntry[] | undefined,
  fixture: { entities: TimelineEntity[]; events: TimelineEvent[] },
): { entities: TimelineEntity[]; events: TimelineEvent[]; usingFixture: boolean } {
  const liveEvents = (live ?? []).map(mapTimelineEntry);
  if (liveEvents.length === 0) {
    return { ...fixture, usingFixture: true };
  }
  return {
    entities: entitiesFromEvents(liveEvents, []),
    events: liveEvents,
    usingFixture: false,
  };
}
