'use client';

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
};

export function bitrixHistory(entry: WhatsAppEntry): BitrixHistoryMeta | null {
  const history = entry.metadata?.bitrix_history;
  if (!history || typeof history !== 'object') return null;
  return history as BitrixHistoryMeta;
}

export function isWhatsappEntry(entry: WhatsAppEntry): boolean {
  if (entry.activity_type === 'whatsapp') return true;
  const history = bitrixHistory(entry);
  const kind = String(history?.kind || '');
  if (kind === 'whatsapp_message' || kind === 'whatsapp_session') return true;
  return Boolean(history?.open_channel_summary);
}

export function whatsappSender(entry: WhatsAppEntry): string {
  const history = bitrixHistory(entry);
  if (history?.author_name) return String(history.author_name);
  if (entry.actor_name) return entry.actor_name;
  const direction = String(history?.direction || '');
  if (direction === 'outgoing') return 'WhatsApp';
  if (direction === 'system') return 'Sistem';
  if (history?.person_name) return String(history.person_name);
  return 'WhatsApp';
}

export function whatsappDirection(entry: WhatsAppEntry): 'incoming' | 'outgoing' | 'system' {
  const direction = String(bitrixHistory(entry)?.direction || '');
  if (direction === 'outgoing' || direction === 'system') return direction;
  return 'incoming';
}

export function sortWhatsappConversation(entries: WhatsAppEntry[]): WhatsAppEntry[] {
  return [...entries].filter(isWhatsappEntry).sort((a, b) => a.created_at.localeCompare(b.created_at));
}

export function WhatsAppThread({
  messages,
  locale,
  testId = 'whatsapp-thread',
}: {
  messages: WhatsAppEntry[];
  locale?: string;
  testId?: string;
}) {
  return (
    <div className="crm-contact-card__wa-tab" data-testid={testId}>
      {messages.map((message) => {
        const history = bitrixHistory(message);
        const direction = whatsappDirection(message);
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
            <p>{message.summary || message.title}</p>
            {Number(history?.attachment_count || 0) > 0 ? (
              <em>Ek var (Bitrix dosyası indirilemedi)</em>
            ) : null}
            {history?.open_channel_summary && !history.full_messages_recovered ? (
              <em>Open Channel özeti</em>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
