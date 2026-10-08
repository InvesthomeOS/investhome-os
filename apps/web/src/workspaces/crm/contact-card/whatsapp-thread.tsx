'use client';

import { useMemo } from 'react';

import { documentPreviewUrl } from '@/lib/api/documents';
import type { GalleryDocument } from '@/workspaces/crm/contact-card/document-gallery';
import { isDecorativeMediaUrl, parseWhatsappMedia } from '@/workspaces/crm/contact-card/history-html';

export type WhatsAppEntry = {
  id: string;
  activity_type?: string;
  title: string;
  summary?: string | null;
  actor_name?: string | null;
  created_at: string;
  metadata?: Record<string, unknown> | null;
};

type BitrixHistoryMeta = {
  kind?: string;
  author_name?: string;
  person_name?: string;
  chat_id?: string;
  direction?: string;
  attachment_count?: number;
  open_channel_summary?: boolean;
  full_messages_recovered?: boolean | null;
  source?: string;
  bitrix_record_id?: string | number;
  message_id?: string | number;
  import_key?: string;
};

export function bitrixHistory(entry: WhatsAppEntry): BitrixHistoryMeta | null {
  const history = entry.metadata?.bitrix_history;
  if (history && typeof history === 'object') return history as BitrixHistoryMeta;
  const live = entry.metadata?.live_thread;
  if (live && typeof live === 'object') return live as BitrixHistoryMeta;
  return null;
}

export function isWhatsappEntry(entry: WhatsAppEntry): boolean {
  if (entry.activity_type === 'whatsapp') return true;
  const history = bitrixHistory(entry);
  const kind = String(history?.kind || '');
  if (kind === 'whatsapp_message' || kind === 'whatsapp_session') return true;
  return Boolean(history?.open_channel_summary);
}

function threadKind(entry: WhatsAppEntry): string {
  const type = String(entry.activity_type || '').toLowerCase();
  if (type) return type;
  return String(bitrixHistory(entry)?.kind || '').toLowerCase();
}

function isChannelEntry(entry: WhatsAppEntry, channels: string[]): boolean {
  const allowed = new Set(channels);
  const kind = threadKind(entry);
  if (allowed.has(kind)) return true;
  if (allowed.has('whatsapp') && isWhatsappEntry(entry)) return true;
  return false;
}

function channelSenderLabel(entry: WhatsAppEntry): string {
  const kind = threadKind(entry);
  if (kind.includes('facebook')) return 'Facebook';
  if (kind.includes('instagram')) return 'Instagram';
  return 'WhatsApp';
}

export function whatsappSender(entry: WhatsAppEntry): string {
  const history = bitrixHistory(entry);
  if (history?.author_name) return String(history.author_name);
  if (entry.actor_name) return entry.actor_name;
  const direction = String(history?.direction || '');
  if (direction === 'outgoing' || direction === 'outbound') return channelSenderLabel(entry);
  if (direction === 'system') return 'Sistem';
  if (history?.person_name) return String(history.person_name);
  return channelSenderLabel(entry);
}

export function whatsappDirection(entry: WhatsAppEntry): 'incoming' | 'outgoing' | 'system' {
  const direction = String(bitrixHistory(entry)?.direction || '');
  if (direction === 'outgoing' || direction === 'outbound') return 'outgoing';
  if (direction === 'system') return 'system';
  return 'incoming';
}

export function timelineSourceKey(entry: WhatsAppEntry): string {
  const history = bitrixHistory(entry);
  const kind = String(history?.kind || entry.activity_type || 'activity').toLowerCase();
  const recordId = String(history?.bitrix_record_id || history?.message_id || '').trim();
  const chatId = String(history?.chat_id || '').trim();
  if (recordId) {
    if (kind.includes('whatsapp')) {
      return chatId ? `whatsapp:${chatId}:${recordId}` : `whatsapp:${recordId}`;
    }
    return `${kind}:${recordId}`;
  }
  const importKey = String(history?.import_key || '').trim();
  if (importKey) {
    const parts = importKey.split(':');
    const tail = parts[parts.length - 1] || importKey;
    const family = parts[1] || kind;
    return `${family}:${tail}`;
  }
  return `id:${entry.id}`;
}

export function sortWhatsappConversation(entries: WhatsAppEntry[], channels: string[] = ['whatsapp']): WhatsAppEntry[] {
  const seen = new Set<string>();
  const unique: WhatsAppEntry[] = [];
  for (const entry of [...entries].filter((item) => isChannelEntry(item, channels)).sort((a, b) => a.created_at.localeCompare(b.created_at))) {
    const key = timelineSourceKey(entry);
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(entry);
  }
  return unique;
}

function matchDocument(entry: WhatsAppEntry, documents: GalleryDocument[]): GalleryDocument | null {
  const hay = `${entry.title} ${entry.summary || ''}`.toLowerCase();
  return (
    documents.find((doc) => {
      const name = (doc.original_file_name || doc.title || '').toLowerCase();
      return name && hay.includes(name);
    }) || null
  );
}

function WhatsAppMediaBlock({
  entry,
  documents,
}: {
  entry: WhatsAppEntry;
  documents: GalleryDocument[];
}) {
  const parsed = parseWhatsappMedia(entry.summary || entry.title);
  const linked = matchDocument(entry, documents);
  const remote = parsed.media.filter((item) => /^https?:/i.test(item.url) && !isDecorativeMediaUrl(item.url));
  if (!remote.length && !linked && Number(bitrixHistory(entry)?.attachment_count || 0) <= 0) return null;
  return (
    <div className="crm-contact-card__wa-media">
      {remote.map((item) => {
        if (item.kind === 'image') {
          return <img key={item.url} src={item.url} alt={item.caption || 'WhatsApp görseli'} />;
        }
        if (item.kind === 'pdf') {
          return (
            <a key={item.url} href={item.url} target="_blank" rel="noreferrer">
              {item.caption || 'PDF'}
            </a>
          );
        }
        return (
          <a key={item.url} href={item.url} target="_blank" rel="noreferrer">
            {item.caption || 'Dosya'}
          </a>
        );
      })}
      {linked ? (
        /\.(png|jpe?g|gif|webp)$/i.test(linked.original_file_name || linked.title) ? (
          <img src={documentPreviewUrl(linked.id)} alt={linked.original_file_name || linked.title} />
        ) : (
          <a href={documentPreviewUrl(linked.id)} target="_blank" rel="noreferrer">
            {linked.original_file_name || linked.title}
          </a>
        )
      ) : null}
      {!remote.length && !linked && Number(bitrixHistory(entry)?.attachment_count || 0) > 0 ? (
        <em>Ek kaydı var; dosya içeriği OS’ta yok</em>
      ) : null}
    </div>
  );
}

export function WhatsAppThread({
  messages,
  locale,
  testId = 'whatsapp-thread',
  documents = [],
  channels = ['whatsapp'],
}: {
  messages: WhatsAppEntry[];
  locale?: string;
  testId?: string;
  documents?: GalleryDocument[];
  channels?: string[];
}) {
  const ordered = useMemo(() => sortWhatsappConversation(messages, channels), [messages, channels]);
  return (
    <div className="crm-contact-card__wa-tab" data-testid={testId}>
      {ordered.map((message) => {
        const direction = whatsappDirection(message);
        const parsed = parseWhatsappMedia(message.summary || message.title);
        return (
          <div
            key={message.id}
            className={`crm-contact-card__wa-bubble crm-contact-card__wa-bubble--${direction}`}
            data-testid="whatsapp-message"
          >
            <small>
              {whatsappSender(message)}
              {' · '}
              {new Date(message.created_at).toLocaleString(locale)}
            </small>
            {parsed.text ? <p>{parsed.text}</p> : null}
            <WhatsAppMediaBlock entry={message} documents={documents} />
          </div>
        );
      })}
    </div>
  );
}
