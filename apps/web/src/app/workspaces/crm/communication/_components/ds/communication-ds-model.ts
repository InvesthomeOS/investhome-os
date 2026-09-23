import type { IhIconName } from '@/components/icons/ih-icons';
import type { CrmCommChannel, CrmCommDirection, CrmCommThreadSummary } from '@/workspaces/crm/types';

export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';

/** Global workspace channel filters (exact order). */
export type CommStreamChannel =
  | 'all'
  | 'email'
  | 'whatsapp'
  | 'phone'
  | 'meeting'
  | 'task'
  | 'note';

export type CommSortKey = 'recent' | 'unread' | 'name_asc' | 'name_desc';

export type CommAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';

export type CommAttachmentKind = 'pdf' | 'docx' | 'image' | 'meeting_summary' | 'voice';

export type CommTimelineItemKind =
  | 'whatsapp'
  | 'email'
  | 'phone'
  | 'meeting'
  | 'note'
  | 'task'
  | 'system';

export type CommAttachment = {
  id: string;
  name: string;
  sizeLabel: string;
  kind: CommAttachmentKind;
};

export type CommTimelineItem = {
  id: string;
  kind: CommTimelineItemKind;
  direction: CrmCommDirection | 'system';
  body: string;
  timestamp: string;
  owner: string;
  relatedEntity?: string;
  attachments?: CommAttachment[];
  read?: boolean;
};

export type CommActivityPreview = {
  id: string;
  kind: CommTimelineItemKind;
  label: string;
  timeLabel: string;
};

export type CommTaskPreview = {
  id: string;
  title: string;
  dueLabel: string;
  owner: string;
  done?: boolean;
};

export type CommProjectPreview = {
  id: string;
  name: string;
  location: string;
  status: string;
  statusTone: StatusTone;
};

export type CommContactInfo = {
  name: string;
  initials: string;
  avatarTone: CommAvatarTone;
  company: string;
  email: string;
  phone: string;
  location: string;
  source: string;
  status: string;
  statusTone: StatusTone;
  score: number;
  createdLabel: string;
  tags: string[];
  detailHref?: string;
};

export type CommStreamRow = {
  id: string;
  contactName: string;
  initials: string;
  avatarTone: CommAvatarTone;
  preview: string;
  timestamp: string;
  channel: Exclude<CommStreamChannel, 'all'>;
  unread: number;
  starred: boolean;
  hasAttachment: boolean;
  subject: string;
  owner: string;
  company: string;
  /** Maps to API channel when present */
  apiChannel?: CrmCommChannel;
};

export type CommConversation = {
  threadId: string;
  channel: Exclude<CommStreamChannel, 'all'>;
  channelActive: boolean;
  contact: CommContactInfo;
  timeline: CommTimelineItem[];
  recentActivities: CommActivityPreview[];
  upcomingTasks: CommTaskPreview[];
  relatedProjects: CommProjectPreview[];
  crmNotes: string[];
  aiSuggestions: string[];
};

export type CommDsFilters = {
  channel: CommStreamChannel;
  search: string;
  sort: CommSortKey;
  unreadOnly: boolean;
  starredOnly: boolean;
};

export const EMPTY_COMM_FILTERS: CommDsFilters = {
  channel: 'all',
  search: '',
  sort: 'recent',
  unreadOnly: false,
  starredOnly: false,
};

export const COMM_STREAM_CHANNELS: CommStreamChannel[] = [
  'all',
  'email',
  'whatsapp',
  'phone',
  'meeting',
  'task',
  'note',
];

export const CHANNEL_ICON: Record<Exclude<CommStreamChannel, 'all'>, IhIconName> = {
  email: 'inbox',
  whatsapp: 'check',
  phone: 'meeting',
  meeting: 'calendar',
  task: 'target',
  note: 'documents',
};

export const CHANNEL_STATUS_TONE: Record<Exclude<CommStreamChannel, 'all'>, StatusTone> = {
  email: 'info',
  whatsapp: 'success',
  phone: 'default',
  meeting: 'warning',
  task: 'info',
  note: 'default',
};

export const TIMELINE_KIND_TONE: Record<CommTimelineItemKind, StatusTone> = {
  whatsapp: 'success',
  email: 'info',
  phone: 'default',
  meeting: 'warning',
  note: 'default',
  task: 'info',
  system: 'default',
};

const AVATAR_TONES: CommAvatarTone[] = ['navy', 'cyan', 'green', 'amber', 'violet', 'rose'];

export function initialsFromName(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

export function avatarToneFromName(name: string): CommAvatarTone {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash + name.charCodeAt(i) * (i + 1)) % 97;
  return AVATAR_TONES[hash % AVATAR_TONES.length]!;
}

export function mapApiChannelToStream(channel: CrmCommChannel | string): Exclude<CommStreamChannel, 'all'> {
  switch (channel) {
    case 'email':
      return 'email';
    case 'whatsapp':
      return 'whatsapp';
    case 'phone':
    case 'sms':
      return 'phone';
    case 'meeting':
    case 'zoom':
    case 'teams':
      return 'meeting';
    case 'note':
    case 'internal_message':
      return 'note';
    default:
      return 'email';
  }
}

export function streamChannelToApi(channel: CommStreamChannel): CrmCommChannel | undefined {
  switch (channel) {
    case 'email':
      return 'email';
    case 'whatsapp':
      return 'whatsapp';
    case 'phone':
      return 'phone';
    case 'meeting':
      return 'meeting';
    case 'note':
      return 'note';
    case 'task':
      return undefined;
    default:
      return undefined;
  }
}

export function formatRelativeTime(iso: string | null | undefined, locale: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) {
    return date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
  }
  if (diffDays === 1) {
    return locale.startsWith('tr') ? 'Dün' : 'Yesterday';
  }
  if (diffDays < 7) {
    return date.toLocaleDateString(locale, { weekday: 'short' });
  }
  return date.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
}

export function threadToStreamRow(
  thread: CrmCommThreadSummary,
  locale: string,
  contactName?: string,
): CommStreamRow {
  const name = contactName ?? thread.subject ?? '—';
  const channel = mapApiChannelToStream(thread.channel);
  return {
    id: thread.id,
    contactName: name,
    initials: initialsFromName(name),
    avatarTone: avatarToneFromName(name),
    preview: thread.preview ?? '',
    timestamp: formatRelativeTime(thread.last_communication_at, locale),
    channel,
    unread: thread.unread_count,
    starred: thread.is_pinned,
    hasAttachment: false,
    subject: thread.subject || '',
    owner: thread.assigned_user_id ?? thread.owner_id ?? '',
    company: '',
    apiChannel: thread.channel,
  };
}

export function filterStreamRows(rows: CommStreamRow[], filters: CommDsFilters): CommStreamRow[] {
  let next = rows;
  if (filters.channel !== 'all') {
    next = next.filter((r) => r.channel === filters.channel);
  }
  if (filters.unreadOnly) {
    next = next.filter((r) => r.unread > 0);
  }
  if (filters.starredOnly) {
    next = next.filter((r) => r.starred);
  }
  const q = filters.search.trim().toLowerCase();
  if (q) {
    next = next.filter(
      (r) =>
        r.contactName.toLowerCase().includes(q) ||
        r.preview.toLowerCase().includes(q) ||
        r.subject.toLowerCase().includes(q) ||
        r.company.toLowerCase().includes(q),
    );
  }
  const sorted = [...next];
  switch (filters.sort) {
    case 'unread':
      sorted.sort((a, b) => b.unread - a.unread || a.contactName.localeCompare(b.contactName));
      break;
    case 'name_asc':
      sorted.sort((a, b) => a.contactName.localeCompare(b.contactName));
      break;
    case 'name_desc':
      sorted.sort((a, b) => b.contactName.localeCompare(a.contactName));
      break;
    case 'recent':
    default:
      break;
  }
  return sorted;
}

export function countByChannel(rows: CommStreamRow[]): Record<CommStreamChannel, number> {
  const counts: Record<CommStreamChannel, number> = {
    all: rows.length,
    email: 0,
    whatsapp: 0,
    phone: 0,
    meeting: 0,
    task: 0,
    note: 0,
  };
  for (const row of rows) {
    counts[row.channel] += 1;
  }
  return counts;
}

/** Fixture stream + conversations used when API returns empty / unavailable. */
export function makeCommunicationFixture(): {
  rows: CommStreamRow[];
  conversations: Record<string, CommConversation>;
} {
  const rows: CommStreamRow[] = [
    {
      id: 'thr-isabella',
      contactName: 'Isabella Romano',
      initials: 'IR',
      avatarTone: 'violet',
      preview: 'Merhaba, The Temple birim planlarını inceledim. 2+1 için müsaitlik var mı?',
      timestamp: '10:30',
      channel: 'whatsapp',
      unread: 2,
      starred: true,
      hasAttachment: false,
      subject: 'The Temple — birim sorusu',
      owner: 'Ayşe Demir',
      company: 'Romano Holdings',
    },
    {
      id: 'thr-ahmet',
      contactName: 'Ahmet Yılmaz',
      initials: 'AY',
      avatarTone: 'navy',
      preview: 'Marina Heights öneri paketi ektedir. Görüşme özetini de ekledim.',
      timestamp: '09:40',
      channel: 'email',
      unread: 0,
      starred: false,
      hasAttachment: true,
      subject: 'Marina Heights öneri paketi',
      owner: 'Can Özkan',
      company: 'Yılmaz Yatırım',
    },
    {
      id: 'thr-elif',
      contactName: 'Elif Kaya',
      initials: 'EK',
      avatarTone: 'cyan',
      preview: 'Outbound · 6 dk · Bağlandı — takip toplantısı planlandı.',
      timestamp: 'Dün',
      channel: 'phone',
      unread: 0,
      starred: true,
      hasAttachment: false,
      subject: 'Takip araması',
      owner: 'Ayşe Demir',
      company: 'Kaya Partners',
    },
    {
      id: 'thr-nova',
      contactName: 'Nova Capital',
      initials: 'NC',
      avatarTone: 'amber',
      preview: 'Yatırımcı brifing notları paylaşıldı. Katılımcılar: 4.',
      timestamp: 'Dün',
      channel: 'meeting',
      unread: 1,
      starred: false,
      hasAttachment: true,
      subject: 'Yatırımcı brifing',
      owner: 'Mehmet Kaya',
      company: 'Nova Capital',
    },
    {
      id: 'thr-zeynep',
      contactName: 'Zeynep Arslan',
      initials: 'ZA',
      avatarTone: 'green',
      preview: 'Showroom ziyareti için hatırlatma görevi oluşturuldu.',
      timestamp: '23 Tem',
      channel: 'task',
      unread: 0,
      starred: false,
      hasAttachment: false,
      subject: 'Showroom hatırlatma',
      owner: 'Can Özkan',
      company: 'Arslan Group',
    },
    {
      id: 'thr-horizon',
      contactName: 'Horizon Partners',
      initials: 'HP',
      avatarTone: 'rose',
      preview: 'Müşteri tercihleri: deniz manzarası, yüksek kat, peşinat esnekliği.',
      timestamp: '22 Tem',
      channel: 'note',
      unread: 0,
      starred: false,
      hasAttachment: false,
      subject: 'CRM notu',
      owner: 'Ayşe Demir',
      company: 'Horizon Partners',
    },
    {
      id: 'thr-can',
      contactName: 'Can Özkan',
      initials: 'CÖ',
      avatarTone: 'navy',
      preview: 'Teklif onayı bekleniyor — WhatsApp üzerinden son mesaj.',
      timestamp: '22 Tem',
      channel: 'whatsapp',
      unread: 0,
      starred: false,
      hasAttachment: false,
      subject: 'Teklif onayı',
      owner: 'Ayşe Demir',
      company: 'Özkan Gayrimenkul',
    },
    {
      id: 'thr-mehmet',
      contactName: 'Mehmet Kaya',
      initials: 'MK',
      avatarTone: 'cyan',
      preview: 'Ödeme planı PDF’i eklendi. İnceleme sonrası dönüş bekliyoruz.',
      timestamp: '21 Tem',
      channel: 'email',
      unread: 3,
      starred: true,
      hasAttachment: true,
      subject: 'Ödeme planı',
      owner: 'Can Özkan',
      company: 'Kaya İnşaat',
    },
    {
      id: 'thr-ayse',
      contactName: 'Ayşe Demir',
      initials: 'AD',
      avatarTone: 'green',
      preview: 'Gelen arama · Cevapsız — geri arama planlandı.',
      timestamp: '20 Tem',
      channel: 'phone',
      unread: 0,
      starred: false,
      hasAttachment: false,
      subject: 'Geri arama',
      owner: 'Mehmet Kaya',
      company: 'Demir Holding',
    },
    {
      id: 'thr-temple',
      contactName: 'The Temple Sales',
      initials: 'TS',
      avatarTone: 'amber',
      preview: 'Showroom turu tamamlandı. Özet not eklendi.',
      timestamp: '19 Tem',
      channel: 'meeting',
      unread: 0,
      starred: false,
      hasAttachment: true,
      subject: 'Showroom turu',
      owner: 'Ayşe Demir',
      company: 'The Temple',
    },
  ];

  const conversations: Record<string, CommConversation> = {
    'thr-isabella': {
      threadId: 'thr-isabella',
      channel: 'whatsapp',
      channelActive: true,
      contact: {
        name: 'Isabella Romano',
        initials: 'IR',
        avatarTone: 'violet',
        company: 'Romano Holdings',
        email: 'isabella@romano.holdings',
        phone: '+39 02 1234 5678',
        location: 'Milano, İtalya',
        source: 'Referral',
        status: 'Nitelikli Lead',
        statusTone: 'success',
        score: 78,
        createdLabel: '12 Haz 2026',
        tags: ['The Temple', 'Yurt Dışı Yatırımcı'],
        detailHref: '/workspaces/crm/leads',
      },
      timeline: [
        {
          id: 'msg-1',
          kind: 'system',
          direction: 'system',
          body: 'Konuşma WhatsApp üzerinden başlatıldı.',
          timestamp: '09:15',
          owner: 'Sistem',
        },
        {
          id: 'msg-2',
          kind: 'whatsapp',
          direction: 'inbound',
          body: 'Merhaba, The Temple birim planlarını inceledim. 2+1 için müsaitlik var mı?',
          timestamp: '09:42',
          owner: 'Isabella Romano',
          relatedEntity: 'The Temple',
          read: true,
        },
        {
          id: 'msg-3',
          kind: 'whatsapp',
          direction: 'outbound',
          body: 'Merhaba Isabella, evet — 18. ve 22. katlarda iki 2+1 seçenek mevcut. Plan PDF’ini paylaşıyorum.',
          timestamp: '09:55',
          owner: 'Ayşe Demir',
          attachments: [
            { id: 'att-1', name: 'The-Temple-2plus1-plan.pdf', sizeLabel: '2.4 MB', kind: 'pdf' },
          ],
          read: true,
        },
        {
          id: 'msg-4',
          kind: 'email',
          direction: 'outbound',
          body: 'Detaylı ödeme planı ve sözleşme özeti e-posta ile iletildi.',
          timestamp: '10:05',
          owner: 'Ayşe Demir',
          attachments: [
            { id: 'att-2', name: 'Odeme-Plani.docx', sizeLabel: '180 KB', kind: 'docx' },
          ],
          relatedEntity: 'Lead · Isabella Romano',
        },
        {
          id: 'msg-5',
          kind: 'whatsapp',
          direction: 'inbound',
          body: 'Teşekkürler! Yarın 14:00 showroom için uygun muyuz?',
          timestamp: '10:28',
          owner: 'Isabella Romano',
          read: false,
        },
        {
          id: 'msg-6',
          kind: 'note',
          direction: 'internal',
          body: 'Yurt dışı yatırımcı — peşinat esnekliği ve İngilizce sözleşme talep etti.',
          timestamp: '10:30',
          owner: 'Ayşe Demir',
        },
      ],
      recentActivities: [
        { id: 'act-1', kind: 'whatsapp', label: 'WhatsApp mesajı alındı', timeLabel: '10:28' },
        { id: 'act-2', kind: 'email', label: 'Ödeme planı gönderildi', timeLabel: '10:05' },
        { id: 'act-3', kind: 'phone', label: 'Tanışma araması', timeLabel: 'Dün' },
        { id: 'act-4', kind: 'meeting', label: 'Keşif toplantısı', timeLabel: '23 Tem' },
      ],
      upcomingTasks: [
        {
          id: 'task-1',
          title: 'Showroom ziyaretini onayla',
          dueLabel: 'Yarın · 14:00',
          owner: 'Ayşe Demir',
        },
        {
          id: 'task-2',
          title: 'İngilizce sözleşme taslağı hazırla',
          dueLabel: '29 Tem',
          owner: 'Can Özkan',
        },
      ],
      relatedProjects: [
        {
          id: 'proj-1',
          name: 'The Temple',
          location: 'Kadıköy, İstanbul',
          status: 'İnceleme Aşamasında',
          statusTone: 'info',
        },
      ],
      crmNotes: [
        'Deniz manzarası ve yüksek kat tercih ediyor. Yatırım amacı: uzun vadeli kira.',
      ],
      aiSuggestions: [
        'Showroom sonrası 24 saat içinde İngilizce takip e-postası gönderin.',
        'Benzer profildeki yatırımcılara The Temple 2+1 paketini önerin.',
      ],
    },
  };

  // Lightweight conversations for remaining threads
  for (const row of rows) {
    if (conversations[row.id]) continue;
    conversations[row.id] = {
      threadId: row.id,
      channel: row.channel,
      channelActive: row.channel === 'whatsapp' || row.channel === 'email',
      contact: {
        name: row.contactName,
        initials: row.initials,
        avatarTone: row.avatarTone,
        company: row.company,
        email: `${row.initials.toLowerCase()}@example.com`,
        phone: '+90 532 000 00 00',
        location: 'İstanbul, Türkiye',
        source: 'CRM',
        status: 'Aktif',
        statusTone: 'info',
        score: 62,
        createdLabel: '01 Tem 2026',
        tags: [row.company].filter(Boolean),
      },
      timeline: [
        {
          id: `${row.id}-t1`,
          kind: row.channel === 'phone' ? 'phone' : row.channel === 'meeting' ? 'meeting' : row.channel === 'task' ? 'task' : row.channel === 'note' ? 'note' : row.channel === 'whatsapp' ? 'whatsapp' : 'email',
          direction: 'inbound',
          body: row.preview,
          timestamp: row.timestamp,
          owner: row.contactName,
          relatedEntity: row.company,
          attachments: row.hasAttachment
            ? [{ id: `${row.id}-a1`, name: 'Ek-dosya.pdf', sizeLabel: '1.1 MB', kind: 'pdf' }]
            : undefined,
        },
        {
          id: `${row.id}-t2`,
          kind: 'note',
          direction: 'internal',
          body: 'CRM sistem notu: konuşma merkezi üzerinden takip ediliyor.',
          timestamp: row.timestamp,
          owner: row.owner || 'Sistem',
        },
      ],
      recentActivities: [
        {
          id: `${row.id}-a`,
          kind: row.channel === 'task' ? 'task' : row.channel === 'note' ? 'note' : row.channel === 'phone' ? 'phone' : row.channel === 'meeting' ? 'meeting' : row.channel === 'whatsapp' ? 'whatsapp' : 'email',
          label: row.subject || row.preview.slice(0, 40),
          timeLabel: row.timestamp,
        },
      ],
      upcomingTasks: [
        {
          id: `${row.id}-task`,
          title: 'Takip mesajı gönder',
          dueLabel: 'Bu hafta',
          owner: row.owner || '—',
        },
      ],
      relatedProjects: [
        {
          id: `${row.id}-proj`,
          name: 'Marina Heights',
          location: 'Beşiktaş, İstanbul',
          status: 'Aktif',
          statusTone: 'success',
        },
      ],
      crmNotes: ['Kısa CRM notu — kanal geçmişi birleştirildi.'],
      aiSuggestions: ['Son etkileşime göre 48 saat içinde takip önerilir.'],
    };
  }

  return { rows, conversations };
}
