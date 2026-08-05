import type { IhIconName } from '@/components/icons/ih-icons';
import type {
  CrmActivityAttachment,
  CrmActivityChecklistItem,
  CrmActivityComment,
  CrmActivityDetail,
  CrmActivityEntityType,
  CrmActivityPriority,
  CrmActivityStatus,
  CrmActivitySummary,
  CrmActivityVisibility,
} from '@/workspaces/crm/types/activities';

export type NotesAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';
export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';

export type NotesExplorerTab = 'all' | 'important' | 'shared' | 'draft';

export type NotesCategoryKey =
  | 'meeting'
  | 'general'
  | 'follow_up'
  | 'research'
  | 'internal'
  | 'other';

export type NotesEntityKind =
  | 'contact'
  | 'company'
  | 'investor'
  | 'lead'
  | 'project'
  | 'activity'
  | 'meeting'
  | 'communication'
  | 'opportunity'
  | 'other';

export type NotesSortKey = 'newest' | 'oldest' | 'title_asc' | 'priority' | 'updated';

export type NotesViewMode = 'list' | 'compact';

export type NotesAttachmentKind = 'pdf' | 'docx' | 'xlsx' | 'image' | 'zip' | 'other';

export type NotesViewerTab = 'note' | 'details' | 'relations' | 'tags' | 'history';

export type NotesPerson = {
  id: string;
  name: string;
  initials: string;
  avatarTone: NotesAvatarTone;
  role?: string;
};

export type NotesRelatedEntity = {
  id: string;
  name: string;
  kind: NotesEntityKind;
  href?: string;
};

export type NotesActionItem = {
  id: string;
  title: string;
  done: boolean;
  assignee?: string;
  assigneeInitials?: string;
  dueLabel?: string;
};

export type NotesAttachment = {
  id: string;
  name: string;
  sizeLabel: string;
  kind: NotesAttachmentKind;
  dateLabel: string;
  url?: string | null;
};

export type NotesComment = {
  id: string;
  body: string;
  author: string;
  authorInitials: string;
  avatarTone: NotesAvatarTone;
  timestamp: string;
  parentId?: string | null;
};

export type NotesHistoryEntry = {
  id: string;
  label: string;
  actor: string;
  timestamp: string;
};

export type NoteRow = {
  id: string;
  title: string;
  preview: string;
  body: string;
  category: NotesCategoryKey;
  status: CrmActivityStatus;
  priority: CrmActivityPriority;
  visibility: CrmActivityVisibility;
  isFavorite: boolean;
  isPinned: boolean;
  isDraft: boolean;
  isShared: boolean;
  isImportant: boolean;
  owner: string;
  ownerInitials: string;
  ownerTone: NotesAvatarTone;
  createdBy: string;
  createdByInitials: string;
  createdAt: string;
  updatedBy: string;
  updatedByInitials: string;
  updatedAt: string;
  updatedLabel: string;
  dateLabel: string;
  relatedPerson?: string;
  relatedEntity?: NotesRelatedEntity;
  relatedPeople: NotesPerson[];
  tags: string[];
  actionItems: NotesActionItem[];
  attachments: NotesAttachment[];
  comments: NotesComment[];
  history: NotesHistoryEntry[];
  entityType: CrmActivityEntityType | NotesEntityKind;
  source: 'live' | 'fixture';
};

export type NotesDsFilters = {
  search: string;
  category: NotesCategoryKey | '';
  owner: string;
  entityType: NotesEntityKind | '';
  tag: string;
  dateFrom: string;
  dateTo: string;
  view: NotesViewMode;
  sort: NotesSortKey;
  tab: NotesExplorerTab;
};

export const EMPTY_NOTES_FILTERS: NotesDsFilters = {
  search: '',
  category: '',
  owner: '',
  entityType: '',
  tag: '',
  dateFrom: '',
  dateTo: '',
  view: 'list',
  sort: 'newest',
  tab: 'all',
};

export const NOTES_EXPLORER_TABS: NotesExplorerTab[] = ['all', 'important', 'shared', 'draft'];

export const NOTES_CATEGORIES: NotesCategoryKey[] = [
  'meeting',
  'general',
  'follow_up',
  'research',
  'internal',
  'other',
];

export const NOTES_ENTITY_KINDS: NotesEntityKind[] = [
  'contact',
  'company',
  'investor',
  'lead',
  'project',
  'activity',
  'meeting',
  'communication',
  'opportunity',
  'other',
];

export const NOTES_SORT_KEYS: NotesSortKey[] = ['newest', 'oldest', 'title_asc', 'priority', 'updated'];

export const CATEGORY_ICON: Record<NotesCategoryKey, IhIconName> = {
  meeting: 'calendar',
  general: 'documents',
  follow_up: 'clock',
  research: 'search',
  internal: 'users',
  other: 'activity',
};

export const CATEGORY_TONE: Record<NotesCategoryKey, StatusTone> = {
  meeting: 'info',
  general: 'default',
  follow_up: 'warning',
  research: 'info',
  internal: 'default',
  other: 'default',
};

export const STATUS_TONE: Record<CrmActivityStatus, StatusTone> = {
  planned: 'default',
  scheduled: 'info',
  in_progress: 'warning',
  completed: 'success',
  cancelled: 'danger',
  missed: 'danger',
  deferred: 'warning',
  archived: 'default',
};

export const PRIORITY_TONE: Record<CrmActivityPriority, StatusTone> = {
  low: 'default',
  medium: 'info',
  high: 'warning',
  critical: 'danger',
};

const AVATAR_TONES: NotesAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];

export function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

export function avatarToneFromName(name: string): NotesAvatarTone {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash + name.charCodeAt(i) * (i + 1)) % 97;
  return AVATAR_TONES[hash % AVATAR_TONES.length]!;
}

export function mapEntityKind(type: string | null | undefined): NotesEntityKind {
  switch (type) {
    case 'contact':
      return 'contact';
    case 'company':
      return 'company';
    case 'investor':
      return 'investor';
    case 'opportunity':
      return 'lead';
    case 'project':
    case 'property':
      return 'project';
    case 'meeting':
      return 'meeting';
    case 'activity':
      return 'activity';
    case 'communication':
      return 'communication';
    default:
      return 'other';
  }
}

export function entityHref(kind: NotesEntityKind, id?: string): string | undefined {
  if (!id) return undefined;
  switch (kind) {
    case 'contact':
      return `/workspaces/crm/contacts/${id}`;
    case 'company':
      return `/workspaces/crm/companies/${id}`;
    case 'investor':
      return `/workspaces/crm/people/${id}`;
    case 'lead':
      return `/workspaces/crm/leads/${id}`;
    case 'project':
      return `/workspaces/crm/projects`;
    case 'meeting':
      return `/workspaces/crm/calendar`;
    case 'communication':
      return `/workspaces/crm/communication`;
    case 'activity':
      return `/workspaces/crm/activities`;
    case 'opportunity':
      return `/workspaces/crm/pipeline`;
    default:
      return undefined;
  }
}

function inferCategory(summary: CrmActivitySummary | CrmActivityDetail): NotesCategoryKey {
  const tags = (summary.tags ?? []).map((t) => t.toLowerCase());
  const blob = `${summary.title} ${summary.summary ?? ''} ${tags.join(' ')}`.toLowerCase();
  if (blob.includes('toplant') || blob.includes('meeting') || blob.includes('görüşme')) return 'meeting';
  if (blob.includes('takip') || blob.includes('follow')) return 'follow_up';
  if (blob.includes('araştır') || blob.includes('research') || blob.includes('analiz')) return 'research';
  if (summary.visibility === 'private' || blob.includes('internal') || blob.includes('dahili')) {
    return 'internal';
  }
  if (summary.activity_category === 'meeting') return 'meeting';
  if (summary.activity_category === 'follow_up') return 'follow_up';
  if (summary.activity_category === 'note') return 'general';
  return 'other';
}

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes || bytes <= 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function attachmentKind(name: string, mime?: string | null): NotesAttachmentKind {
  const lower = `${name} ${mime ?? ''}`.toLowerCase();
  if (lower.includes('pdf')) return 'pdf';
  if (lower.includes('doc')) return 'docx';
  if (lower.includes('xls') || lower.includes('sheet')) return 'xlsx';
  if (lower.includes('image') || /\.(png|jpe?g|gif|webp)$/.test(lower)) return 'image';
  if (lower.includes('zip') || lower.includes('rar')) return 'zip';
  return 'other';
}

function relativeLabel(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  const now = new Date();
  const startToday = new Date(now);
  startToday.setHours(0, 0, 0, 0);
  const startThat = new Date(date);
  startThat.setHours(0, 0, 0, 0);
  const dayDiff = Math.round((startToday.getTime() - startThat.getTime()) / 86400000);
  if (dayDiff === 0) {
    return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  }
  if (dayDiff === 1) return locale.startsWith('tr') ? 'Dün' : 'Yesterday';
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
}

function fullDateLabel(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(locale, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function mapChecklist(items: CrmActivityChecklistItem[] | undefined): NotesActionItem[] {
  return (items ?? []).map((item) => ({
    id: item.id,
    title: item.title,
    done: item.is_completed,
    assignee: item.completed_by ?? undefined,
    assigneeInitials: item.completed_by ? initialsFromName(item.completed_by) : undefined,
    dueLabel: item.completed_at
      ? new Date(item.completed_at).toLocaleDateString()
      : undefined,
  }));
}

function mapAttachments(
  items: CrmActivityAttachment[] | undefined,
  locale: string,
): NotesAttachment[] {
  return (items ?? []).map((item) => ({
    id: item.id,
    name: item.file_name,
    sizeLabel: formatBytes(item.file_size_bytes),
    kind: attachmentKind(item.file_name, item.mime_type),
    dateLabel: relativeLabel(item.created_at, locale),
    url: item.file_url,
  }));
}

function mapComments(items: CrmActivityComment[] | undefined, locale: string): NotesComment[] {
  return (items ?? []).map((item) => {
    const author = item.created_by ?? '—';
    return {
      id: item.id,
      body: item.body,
      author,
      authorInitials: initialsFromName(author),
      avatarTone: avatarToneFromName(author),
      timestamp: relativeLabel(item.created_at, locale),
      parentId: item.parent_id,
    };
  });
}

function looksLikeUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value.trim(),
  );
}

function displayActorName(value: string | null | undefined, fallback = '—'): string {
  if (!value || !value.trim()) return fallback;
  if (looksLikeUuid(value)) return `CRM · ${value.slice(0, 8)}`;
  return value;
}

export function mapActivityToNoteRow(
  item: CrmActivitySummary | CrmActivityDetail,
  locale: string,
  detail?: CrmActivityDetail | null,
): NoteRow {
  const source = detail ?? item;
  const ownerRaw = source.assigned_user_id ?? source.owner_id ?? source.created_by ?? '—';
  const createdByRaw = source.created_by ?? ownerRaw;
  const updatedByRaw = source.owner_id ?? createdByRaw;
  const owner = displayActorName(ownerRaw);
  const createdBy = displayActorName(createdByRaw);
  const updatedBy = displayActorName(updatedByRaw);
  const category = inferCategory(source);
  const entityKind = mapEntityKind(source.entity_type);
  const titlePerson = (() => {
    const m = source.title.match(/[—–-]\s*(.+)$/);
    return m?.[1]?.trim() || undefined;
  })();
  const relatedName =
    (source.metadata_json?.entity_name as string | undefined) ??
    (source.metadata_json?.contact_name as string | undefined) ??
    (source.metadata_json?.company_name as string | undefined) ??
    (source.metadata_json?.project_name as string | undefined) ??
    titlePerson ??
    undefined;
  const personName =
    (source.metadata_json?.person_name as string | undefined) ??
    (source.metadata_json?.contact_name as string | undefined) ??
    (entityKind === 'contact' || entityKind === 'investor' || entityKind === 'lead'
      ? titlePerson
      : undefined);
  const isDraft = source.status === 'planned' || source.status === 'deferred';
  const isShared =
    source.visibility === 'team' ||
    source.visibility === 'organization' ||
    source.visibility === 'restricted';
  const isImportant =
    source.is_favorite || source.is_pinned || source.priority === 'high' || source.priority === 'critical';
  const body =
    ('description' in source && source.description) ||
    source.summary ||
    source.title;
  const detailChecklist = detail?.checklist_items;
  const detailAttachments = detail?.attachments;
  const detailComments = detail?.comments;

  return {
    id: source.id,
    title: source.title || '—',
    preview: (source.summary || body || '').slice(0, 120),
    body: body || '',
    category,
    status: source.status,
    priority: source.priority,
    visibility: source.visibility,
    isFavorite: source.is_favorite,
    isPinned: source.is_pinned,
    isDraft,
    isShared,
    isImportant,
    owner,
    ownerInitials: initialsFromName(owner),
    ownerTone: avatarToneFromName(owner),
    createdBy,
    createdByInitials: initialsFromName(createdBy),
    createdAt: source.created_at,
    updatedBy,
    updatedByInitials: initialsFromName(updatedBy),
    updatedAt: source.updated_at,
    updatedLabel: relativeLabel(source.updated_at || source.created_at, locale),
    dateLabel: fullDateLabel(source.updated_at || source.created_at, locale),
    relatedPerson: personName,
    relatedEntity: {
      id: source.entity_id,
      name: relatedName || '—',
      kind: entityKind,
      href: entityHref(entityKind, source.entity_id),
    },
    relatedPeople: personName
      ? [
          {
            id: `person-${source.id}`,
            name: personName,
            initials: initialsFromName(personName),
            avatarTone: avatarToneFromName(personName),
          },
        ]
      : [],
    tags: source.tags ?? [],
    actionItems: mapChecklist(detailChecklist),
    attachments: mapAttachments(detailAttachments, locale),
    comments: mapComments(detailComments, locale),
    history: [
      {
        id: `${source.id}-created`,
        label: 'created',
        actor: createdBy,
        timestamp: fullDateLabel(source.created_at, locale),
      },
      {
        id: `${source.id}-updated`,
        label: 'updated',
        actor: updatedBy,
        timestamp: fullDateLabel(source.updated_at || source.created_at, locale),
      },
    ],
    entityType: source.entity_type,
    source: 'live',
  };
}

export function countByTab(rows: NoteRow[]): Record<NotesExplorerTab, number> {
  return {
    all: rows.length,
    important: rows.filter((r) => r.isImportant).length,
    shared: rows.filter((r) => r.isShared).length,
    draft: rows.filter((r) => r.isDraft).length,
  };
}

function matchesTab(row: NoteRow, tab: NotesExplorerTab): boolean {
  switch (tab) {
    case 'important':
      return row.isImportant;
    case 'shared':
      return row.isShared;
    case 'draft':
      return row.isDraft;
    case 'all':
    default:
      return true;
  }
}

function priorityRank(priority: CrmActivityPriority): number {
  switch (priority) {
    case 'critical':
      return 4;
    case 'high':
      return 3;
    case 'medium':
      return 2;
    case 'low':
    default:
      return 1;
  }
}

export function filterNoteRows(rows: NoteRow[], filters: NotesDsFilters): NoteRow[] {
  const q = filters.search.trim().toLowerCase();
  let next = rows.filter((row) => {
    if (!matchesTab(row, filters.tab)) return false;
    if (filters.category && row.category !== filters.category) return false;
    if (filters.owner && row.owner !== filters.owner && row.createdBy !== filters.owner) return false;
    if (filters.entityType && row.relatedEntity?.kind !== filters.entityType) return false;
    if (filters.tag && !(row.tags ?? []).includes(filters.tag)) return false;
    if (filters.dateFrom) {
      const from = new Date(filters.dateFrom).getTime();
      if (new Date(row.updatedAt || row.createdAt).getTime() < from) return false;
    }
    if (filters.dateTo) {
      const to = new Date(filters.dateTo);
      to.setHours(23, 59, 59, 999);
      if (new Date(row.updatedAt || row.createdAt).getTime() > to.getTime()) return false;
    }
    if (q) {
      const hay = [
        row.title,
        row.preview,
        row.body,
        row.owner,
        row.relatedPerson ?? '',
        row.relatedEntity?.name ?? '',
        ...(row.tags ?? []),
      ]
        .join(' ')
        .toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  next = [...next].sort((a, b) => {
    switch (filters.sort) {
      case 'oldest':
        return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      case 'title_asc':
        return a.title.localeCompare(b.title);
      case 'priority':
        return priorityRank(b.priority) - priorityRank(a.priority);
      case 'updated':
        return new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime();
      case 'newest':
      default:
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    }
  });

  return next;
}

export function uniqueOwners(rows: NoteRow[]): string[] {
  return Array.from(new Set(rows.map((r) => r.owner).filter((o) => o && o !== '—'))).sort();
}

export function uniqueTags(rows: NoteRow[]): string[] {
  return Array.from(new Set(rows.flatMap((r) => r.tags))).sort();
}

export function makeNotesFixture(now = new Date()): NoteRow[] {
  const day = (offset: number, hour: number, minute: number) => {
    const d = new Date(now);
    d.setHours(0, 0, 0, 0);
    d.setDate(d.getDate() + offset);
    d.setHours(hour, minute, 0, 0);
    return d.toISOString();
  };

  const locale = 'tr-TR';

  const rows: NoteRow[] = [
    {
      id: 'note-fixture-1',
      title: 'The Temple birim planları görüşmesi',
      preview:
        'Olivia Brook ile The Temple birim planları ve teslim takvimi üzerine görüşme özeti.',
      body: `## Görüşme özeti

Olivia Brook ile The Temple projesinin birim planları ve teslim takvimi üzerine görüşüldü. Müşteri, 2+1 dairelerin cephe tercihlerinde esneklik ve teslim öncesi ek inceleme talep etti.

### Konuşulan başlıklar
- Birim planlarının güncel hali ve opsiyonlar
- Teslim takvimi ve inceleme penceresi
- Finansman senaryosu ve peşinat esnekliği
- Sonraki adım: revize plan setinin paylaşımı

> "Önceliğimiz plan netliği; finansmanı ikinci turda netleştiririz." — Olivia Brook`,
      category: 'meeting',
      status: 'completed',
      priority: 'high',
      visibility: 'organization',
      isFavorite: true,
      isPinned: true,
      isDraft: false,
      isShared: true,
      isImportant: true,
      owner: 'Olivia Brook',
      ownerInitials: 'OB',
      ownerTone: 'violet',
      createdBy: 'Super Admin',
      createdByInitials: 'SA',
      createdAt: day(-6, 9, 20),
      updatedBy: 'Ayşe Demir',
      updatedByInitials: 'AD',
      updatedAt: day(0, 10, 35),
      updatedLabel: relativeLabel(day(0, 10, 35), locale),
      dateLabel: fullDateLabel(day(0, 10, 35), locale),
      relatedPerson: 'Olivia Brook',
      relatedEntity: {
        id: 'proj-temple',
        name: 'The Temple',
        kind: 'project',
        href: '/workspaces/crm/projects',
      },
      relatedPeople: [
        {
          id: 'p-ob',
          name: 'Olivia Brook',
          initials: 'OB',
          avatarTone: 'violet',
          role: 'Yatırımcı',
        },
        {
          id: 'p-ad',
          name: 'Ayşe Demir',
          initials: 'AD',
          avatarTone: 'cyan',
          role: 'Satış',
        },
      ],
      tags: ['Birim Planları', 'Görüşme'],
      actionItems: [
        {
          id: 'ai-1',
          title: 'Revize birim plan setini paylaş',
          done: false,
          assignee: 'Ayşe Demir',
          assigneeInitials: 'AD',
          dueLabel: '30 Tem',
        },
        {
          id: 'ai-2',
          title: 'Finansman senaryolarını hazırla',
          done: true,
          assignee: 'Super Admin',
          assigneeInitials: 'SA',
          dueLabel: '28 Tem',
        },
        {
          id: 'ai-3',
          title: 'Teslim öncesi inceleme randevusu öner',
          done: false,
          assignee: 'Olivia Brook',
          assigneeInitials: 'OB',
          dueLabel: '2 Ağu',
        },
      ],
      attachments: [
        {
          id: 'att-1',
          name: 'Temple_Birim_Planlari.pdf',
          sizeLabel: '2.4 MB',
          kind: 'pdf',
          dateLabel: relativeLabel(day(-1, 14, 10), locale),
        },
        {
          id: 'att-2',
          name: 'Gorusme_Ozeti.docx',
          sizeLabel: '186 KB',
          kind: 'docx',
          dateLabel: relativeLabel(day(0, 10, 20), locale),
        },
      ],
      comments: [
        {
          id: 'c-1',
          body: 'Plan seti v2 hazır; yarın paylaşabiliriz.',
          author: 'Ayşe Demir',
          authorInitials: 'AD',
          avatarTone: 'cyan',
          timestamp: relativeLabel(day(0, 11, 5), locale),
        },
        {
          id: 'c-2',
          body: 'Olivia peşinat esnekliğini özellikle vurguladı.',
          author: 'Super Admin',
          authorInitials: 'SA',
          avatarTone: 'navy',
          timestamp: relativeLabel(day(-1, 16, 40), locale),
        },
      ],
      history: [
        {
          id: 'h-1',
          label: 'created',
          actor: 'Super Admin',
          timestamp: fullDateLabel(day(-6, 9, 20), locale),
        },
        {
          id: 'h-2',
          label: 'updated',
          actor: 'Ayşe Demir',
          timestamp: fullDateLabel(day(0, 10, 35), locale),
        },
      ],
      entityType: 'project',
      source: 'fixture',
    },
    {
      id: 'note-fixture-2',
      title: 'Harbor Point yatırımcı brifingi',
      preview: 'Mehmet Kaya ile Harbor Point faz-2 brifing notları ve risk başlıkları.',
      body: `## Brifing notları

Harbor Point faz-2 için yatırımcı brifingi tamamlandı. İnşaat ilerleme oranı ve birim stok durumu paylaşıldı.

- Faz-2 teslim hedefi Q4
- Risk: cephe malzemesi tedarik gecikmesi
- Aksiyon: güncel stok listesini ilet`,
      category: 'research',
      status: 'completed',
      priority: 'medium',
      visibility: 'team',
      isFavorite: false,
      isPinned: false,
      isDraft: false,
      isShared: true,
      isImportant: false,
      owner: 'Mehmet Kaya',
      ownerInitials: 'MK',
      ownerTone: 'navy',
      createdBy: 'Mehmet Kaya',
      createdByInitials: 'MK',
      createdAt: day(-2, 11, 0),
      updatedBy: 'Mehmet Kaya',
      updatedByInitials: 'MK',
      updatedAt: day(-1, 9, 15),
      updatedLabel: relativeLabel(day(-1, 9, 15), locale),
      dateLabel: fullDateLabel(day(-1, 9, 15), locale),
      relatedPerson: 'Mehmet Kaya',
      relatedEntity: {
        id: 'proj-harbor',
        name: 'Harbor Point',
        kind: 'project',
        href: '/workspaces/crm/projects',
      },
      relatedPeople: [
        {
          id: 'p-mk',
          name: 'Mehmet Kaya',
          initials: 'MK',
          avatarTone: 'navy',
          role: 'Yatırımcı',
        },
      ],
      tags: ['Brifing', 'Faz-2'],
      actionItems: [
        {
          id: 'ai-h1',
          title: 'Güncel stok listesini gönder',
          done: false,
          assignee: 'Ayşe Demir',
          assigneeInitials: 'AD',
          dueLabel: '29 Tem',
        },
      ],
      attachments: [
        {
          id: 'att-h1',
          name: 'Harbor_Stok.xlsx',
          sizeLabel: '420 KB',
          kind: 'xlsx',
          dateLabel: relativeLabel(day(-1, 9, 0), locale),
        },
      ],
      comments: [],
      history: [
        {
          id: 'hh-1',
          label: 'created',
          actor: 'Mehmet Kaya',
          timestamp: fullDateLabel(day(-2, 11, 0), locale),
        },
      ],
      entityType: 'project',
      source: 'fixture',
    },
    {
      id: 'note-fixture-3',
      title: 'Isabella Romano takip notu',
      preview: 'Lead nitelendirme sonrası takip maddeleri — taslak.',
      body: `## Takip maddeleri

Isabella Romano ile nitelendirme görüşmesi sonrası taslak not.

- ROI senaryosu henüz onaylanmadı
- LinkedIn üzerinden ikinci tur planlanacak`,
      category: 'follow_up',
      status: 'planned',
      priority: 'high',
      visibility: 'private',
      isFavorite: true,
      isPinned: false,
      isDraft: true,
      isShared: false,
      isImportant: true,
      owner: 'Ayşe Demir',
      ownerInitials: 'AD',
      ownerTone: 'cyan',
      createdBy: 'Ayşe Demir',
      createdByInitials: 'AD',
      createdAt: day(-3, 15, 40),
      updatedBy: 'Ayşe Demir',
      updatedByInitials: 'AD',
      updatedAt: day(-3, 16, 10),
      updatedLabel: relativeLabel(day(-3, 16, 10), locale),
      dateLabel: fullDateLabel(day(-3, 16, 10), locale),
      relatedPerson: 'Isabella Romano',
      relatedEntity: {
        id: 'lead-isabella',
        name: 'Isabella Romano',
        kind: 'lead',
        href: '/workspaces/crm/leads',
      },
      relatedPeople: [
        {
          id: 'p-ir',
          name: 'Isabella Romano',
          initials: 'IR',
          avatarTone: 'rose',
          role: 'Lead',
        },
      ],
      tags: ['Lead', 'Takip'],
      actionItems: [],
      attachments: [],
      comments: [],
      history: [
        {
          id: 'hi-1',
          label: 'created',
          actor: 'Ayşe Demir',
          timestamp: fullDateLabel(day(-3, 15, 40), locale),
        },
      ],
      entityType: 'opportunity',
      source: 'fixture',
    },
    {
      id: 'note-fixture-4',
      title: 'Romano Investments şirket notu',
      preview: 'Kurumsal ilişki özeti ve ortaklık potansiyeli.',
      body: `## Şirket notu

Romano Investments ile kurumsal ilişki özeti. Ortaklık modeli değerlendiriliyor.`,
      category: 'general',
      status: 'in_progress',
      priority: 'medium',
      visibility: 'organization',
      isFavorite: false,
      isPinned: false,
      isDraft: false,
      isShared: true,
      isImportant: false,
      owner: 'Super Admin',
      ownerInitials: 'SA',
      ownerTone: 'navy',
      createdBy: 'Super Admin',
      createdByInitials: 'SA',
      createdAt: day(-8, 10, 0),
      updatedBy: 'Super Admin',
      updatedByInitials: 'SA',
      updatedAt: day(-4, 12, 30),
      updatedLabel: relativeLabel(day(-4, 12, 30), locale),
      dateLabel: fullDateLabel(day(-4, 12, 30), locale),
      relatedPerson: undefined,
      relatedEntity: {
        id: 'co-romano',
        name: 'Romano Investments',
        kind: 'company',
        href: '/workspaces/crm/companies',
      },
      relatedPeople: [],
      tags: ['Ortaklık'],
      actionItems: [],
      attachments: [
        {
          id: 'att-r1',
          name: 'Romano_Profil.zip',
          sizeLabel: '1.1 MB',
          kind: 'zip',
          dateLabel: relativeLabel(day(-5, 11, 0), locale),
        },
      ],
      comments: [
        {
          id: 'cr-1',
          body: 'Kurumsal sunum şablonu güncellendi.',
          author: 'Super Admin',
          authorInitials: 'SA',
          avatarTone: 'navy',
          timestamp: relativeLabel(day(-4, 12, 0), locale),
        },
      ],
      history: [
        {
          id: 'hr-1',
          label: 'created',
          actor: 'Super Admin',
          timestamp: fullDateLabel(day(-8, 10, 0), locale),
        },
      ],
      entityType: 'company',
      source: 'fixture',
    },
    {
      id: 'note-fixture-5',
      title: 'İç ekip: iletişim şablonları',
      preview: 'Dahili not — WhatsApp ve e-posta şablon revizyonları.',
      body: `## Dahili not

İletişim şablonlarının revizyon listesi. Dışarı paylaşılmayacak.`,
      category: 'internal',
      status: 'planned',
      priority: 'low',
      visibility: 'private',
      isFavorite: false,
      isPinned: false,
      isDraft: true,
      isShared: false,
      isImportant: false,
      owner: 'Ayşe Demir',
      ownerInitials: 'AD',
      ownerTone: 'cyan',
      createdBy: 'Ayşe Demir',
      createdByInitials: 'AD',
      createdAt: day(-1, 17, 20),
      updatedBy: 'Ayşe Demir',
      updatedByInitials: 'AD',
      updatedAt: day(-1, 17, 45),
      updatedLabel: relativeLabel(day(-1, 17, 45), locale),
      dateLabel: fullDateLabel(day(-1, 17, 45), locale),
      relatedPerson: undefined,
      relatedEntity: {
        id: 'act-templates',
        name: 'Communication',
        kind: 'communication',
        href: '/workspaces/crm/communication',
      },
      relatedPeople: [],
      tags: ['Şablon', 'Dahili'],
      actionItems: [
        {
          id: 'ai-t1',
          title: 'WhatsApp hoş geldin şablonunu güncelle',
          done: false,
          assignee: 'Ayşe Demir',
          assigneeInitials: 'AD',
          dueLabel: '31 Tem',
        },
      ],
      attachments: [],
      comments: [],
      history: [
        {
          id: 'ht-1',
          label: 'created',
          actor: 'Ayşe Demir',
          timestamp: fullDateLabel(day(-1, 17, 20), locale),
        },
      ],
      entityType: 'internal_user',
      source: 'fixture',
    },
    {
      id: 'note-fixture-6',
      title: 'Site ziyareti gözlemleri',
      preview: 'The Temple şantiye ziyareti — görsel ekler ile.',
      body: `## Site ziyareti

Şantiye gezisi sırasında toplanan gözlemler ve fotoğraf notları.`,
      category: 'meeting',
      status: 'completed',
      priority: 'medium',
      visibility: 'team',
      isFavorite: true,
      isPinned: false,
      isDraft: false,
      isShared: true,
      isImportant: true,
      owner: 'Super Admin',
      ownerInitials: 'SA',
      ownerTone: 'navy',
      createdBy: 'Super Admin',
      createdByInitials: 'SA',
      createdAt: day(-10, 13, 0),
      updatedBy: 'Olivia Brook',
      updatedByInitials: 'OB',
      updatedAt: day(-7, 18, 0),
      updatedLabel: relativeLabel(day(-7, 18, 0), locale),
      dateLabel: fullDateLabel(day(-7, 18, 0), locale),
      relatedPerson: 'Olivia Brook',
      relatedEntity: {
        id: 'proj-temple',
        name: 'The Temple',
        kind: 'project',
        href: '/workspaces/crm/projects',
      },
      relatedPeople: [
        {
          id: 'p-ob2',
          name: 'Olivia Brook',
          initials: 'OB',
          avatarTone: 'violet',
        },
      ],
      tags: ['Şantiye', 'Ziyaret'],
      actionItems: [],
      attachments: [
        {
          id: 'att-s1',
          name: 'site-photo-01.jpg',
          sizeLabel: '3.2 MB',
          kind: 'image',
          dateLabel: relativeLabel(day(-10, 14, 0), locale),
        },
      ],
      comments: [],
      history: [
        {
          id: 'hs-1',
          label: 'created',
          actor: 'Super Admin',
          timestamp: fullDateLabel(day(-10, 13, 0), locale),
        },
      ],
      entityType: 'project',
      source: 'fixture',
    },
  ];

  // Expand fixture volume for realistic explorer counts (~42 feel via repeats of variants)
  const extras: NoteRow[] = [];
  const seeds = [
    ['contact', 'Elif Yılmaz', 'contact'],
    ['company', 'Nova Holding', 'company'],
    ['investor', 'Can Öztürk', 'investor'],
    ['lead', 'Sofia Martins', 'lead'],
    ['project', 'Skyline Residences', 'project'],
    ['meeting', 'Haftalık pipeline', 'meeting'],
  ] as const;

  seeds.forEach(([kind, name, entity], idx) => {
    for (let i = 0; i < 6; i += 1) {
      const id = `note-fixture-x-${idx}-${i}`;
      const important = i % 3 === 0;
      const draft = i % 5 === 0;
      const shared = !draft && i % 2 === 0;
      const owner = i % 2 === 0 ? 'Ayşe Demir' : 'Super Admin';
      const created = day(-(idx * 2 + i + 1), 9 + (i % 6), 10 + i);
      extras.push({
        id,
        title: `${name} — not ${i + 1}`,
        preview: `${name} ile ilgili operasyonel not kaydı.`,
        body: `## ${name}\n\nOperasyonel not kaydı #${i + 1}.`,
        category: NOTES_CATEGORIES[i % NOTES_CATEGORIES.length]!,
        status: draft ? 'planned' : i % 4 === 0 ? 'in_progress' : 'completed',
        priority: important ? 'high' : 'medium',
        visibility: shared ? 'organization' : 'private',
        isFavorite: important,
        isPinned: false,
        isDraft: draft,
        isShared: shared,
        isImportant: important,
        owner,
        ownerInitials: initialsFromName(owner),
        ownerTone: avatarToneFromName(owner),
        createdBy: owner,
        createdByInitials: initialsFromName(owner),
        createdAt: created,
        updatedBy: owner,
        updatedByInitials: initialsFromName(owner),
        updatedAt: created,
        updatedLabel: relativeLabel(created, locale),
        dateLabel: fullDateLabel(created, locale),
        relatedPerson: kind === 'company' ? undefined : name,
        relatedEntity: {
          id: `ent-${idx}-${i}`,
          name,
          kind: kind as NotesEntityKind,
          href: entityHref(kind as NotesEntityKind, `ent-${idx}-${i}`),
        },
        relatedPeople:
          kind === 'company'
            ? []
            : [
                {
                  id: `rp-${idx}-${i}`,
                  name,
                  initials: initialsFromName(name),
                  avatarTone: avatarToneFromName(name),
                },
              ],
        tags: i % 2 === 0 ? ['CRM'] : ['Operasyon'],
        actionItems: [],
        attachments: [],
        comments: [],
        history: [
          {
            id: `${id}-h`,
            label: 'created',
            actor: owner,
            timestamp: fullDateLabel(created, locale),
          },
        ],
        entityType: entity as CrmActivityEntityType,
        source: 'fixture',
      });
    }
  });

  return [...rows, ...extras];
}

export function mergeNotesData(
  live: CrmActivitySummary[] | undefined,
  fixture: NoteRow[],
  locale: string,
): { rows: NoteRow[]; usingFixture: boolean } {
  const liveRows = (live ?? []).map((item) => mapActivityToNoteRow(item, locale));
  if (liveRows.length === 0) {
    return { rows: fixture, usingFixture: true };
  }
  return { rows: liveRows, usingFixture: false };
}

export function enrichNoteWithDetail(
  row: NoteRow,
  detail: CrmActivityDetail | null | undefined,
  locale: string,
): NoteRow {
  if (!detail) return row;
  const mapped = mapActivityToNoteRow(detail, locale, detail);
  return {
    ...mapped,
    // Preserve fixture enrichment when API detail is sparse
    relatedPerson: mapped.relatedPerson || row.relatedPerson,
    relatedPeople: mapped.relatedPeople.length ? mapped.relatedPeople : row.relatedPeople,
    actionItems: mapped.actionItems.length ? mapped.actionItems : row.actionItems,
    attachments: mapped.attachments.length ? mapped.attachments : row.attachments,
    comments: mapped.comments.length ? mapped.comments : row.comments,
    tags: mapped.tags.length ? mapped.tags : row.tags,
    body: mapped.body || row.body,
  };
}

/** Lightweight markdown → safe HTML for read-focused viewer */
export function renderNoteBodyHtml(body: string): string {
  const escaped = body
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const lines = escaped.split(/\r?\n/);
  const html: string[] = [];
  let inUl = false;
  let inQuote = false;

  const closeLists = () => {
    if (inUl) {
      html.push('</ul>');
      inUl = false;
    }
    if (inQuote) {
      html.push('</blockquote>');
      inQuote = false;
    }
  };

  for (const line of lines) {
    if (/^###\s+/.test(line)) {
      closeLists();
      html.push(`<h4>${line.replace(/^###\s+/, '')}</h4>`);
      continue;
    }
    if (/^##\s+/.test(line)) {
      closeLists();
      html.push(`<h3>${line.replace(/^##\s+/, '')}</h3>`);
      continue;
    }
    if (/^#\s+/.test(line)) {
      closeLists();
      html.push(`<h2>${line.replace(/^#\s+/, '')}</h2>`);
      continue;
    }
    if (/^[-*]\s+/.test(line)) {
      if (inQuote) {
        html.push('</blockquote>');
        inQuote = false;
      }
      if (!inUl) {
        html.push('<ul>');
        inUl = true;
      }
      html.push(`<li>${line.replace(/^[-*]\s+/, '')}</li>`);
      continue;
    }
    if (/^>\s?/.test(line)) {
      if (inUl) {
        html.push('</ul>');
        inUl = false;
      }
      if (!inQuote) {
        html.push('<blockquote>');
        inQuote = true;
      }
      html.push(`<p>${line.replace(/^>\s?/, '')}</p>`);
      continue;
    }
    if (!line.trim()) {
      closeLists();
      continue;
    }
    closeLists();
    const withInline = line
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/`(.+?)`/g, '<code>$1</code>');
    html.push(`<p>${withInline}</p>`);
  }
  closeLists();
  return html.join('\n');
}
