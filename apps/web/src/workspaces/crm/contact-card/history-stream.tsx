'use client';

import { FormEvent, useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';

import { Button, Input, Select, TextArea } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchActivity, updateActivity } from '@/workspaces/crm/api/activities';
import type { ContactTimelineEntry } from '@/workspaces/crm/api/contacts';
import {
  DocumentPreviewDialog,
  type GalleryDocument,
} from '@/workspaces/crm/contact-card/document-gallery';
import { EmailCard, EmailDetail } from '@/workspaces/crm/contact-card/crm-email-view';
import {
  parseWhatsappMedia,
  stripHtml,
  looksLikePayloadDump,
  noteFingerprint,
  taskStatusLabel,
} from '@/workspaces/crm/contact-card/history-html';
import {
  bitrixHistory,
  sortWhatsappConversation,
  timelineSourceKey,
  WhatsAppThread,
  whatsappDirection,
  whatsappSender,
} from '@/workspaces/crm/contact-card/whatsapp-thread';

export const PILOT_HISTORY_FILTERS = [
  { id: 'all', label: 'Tümü' },
  { id: 'comment', label: 'Yorumlar' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'email', label: 'E-posta' },
  { id: 'task', label: 'Görevler' },
  { id: 'document', label: 'Belgeler' },
] as const;

export type PilotHistoryFilter = (typeof PILOT_HISTORY_FILTERS)[number]['id'];

type StreamEntry = ContactTimelineEntry & {
  document?: GalleryDocument;
};

const TYPE_ICONS: Record<string, IhIconName> = {
  email: 'mail',
  whatsapp: 'inbox',
  comment: 'activity',
  task: 'check',
  document: 'documents',
};

function formatWhen(value: string, locale: string) {
  return new Date(value).toLocaleString(locale, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function isComment(entry: StreamEntry) {
  return (
    entry.activity_type === 'comment' ||
    entry.activity_type === 'note' ||
    entry.activity_type === 'internal_discussion' ||
    Boolean(entry.imported_historical_comment)
  );
}

function commentContentSha(entry: StreamEntry): string | null {
  const meta = entry.metadata || {};
  const comment = meta.bitrix_historical_comment;
  if (comment && typeof comment === 'object' && 'content_sha256' in comment) {
    const sha = String((comment as { content_sha256?: string }).content_sha256 || '').trim();
    return sha || null;
  }
  return null;
}

function isWhatsapp(entry: StreamEntry) {
  return entry.activity_type === 'whatsapp' || String(bitrixHistory(entry)?.kind || '').startsWith('whatsapp');
}

export function documentToStreamEntry(doc: GalleryDocument): StreamEntry {
  return {
    id: `document-${doc.id}`,
    source: 'document',
    activity_type: 'document',
    title: doc.original_file_name || doc.title,
    summary: doc.document_type || doc.source || null,
    status: null,
    actor_name: null,
    created_at: doc.created_at || new Date().toISOString(),
    is_system_event: false,
    document: doc,
  };
}

function matchesFilter(entry: StreamEntry, filter: PilotHistoryFilter) {
  if (filter === 'all') return true;
  if (filter === 'comment') return isComment(entry);
  if (filter === 'whatsapp') return isWhatsapp(entry);
  if (filter === 'document') return entry.activity_type === 'document';
  return entry.activity_type === filter;
}

function uniqueBySource(entries: StreamEntry[]): StreamEntry[] {
  const seen = new Set<string>();
  const unique: StreamEntry[] = [];
  for (const entry of entries) {
    if (isComment(entry) && looksLikePayloadDump(entry.summary || entry.title)) continue;
    const keys = entry.document
      ? [
          entry.document.bitrix_file_id ? `file:${entry.document.bitrix_file_id}` : '',
          entry.document.checksum ? `sum:${entry.document.checksum}` : '',
          `doc:${entry.document.id}`,
        ].filter(Boolean)
      : [timelineSourceKey(entry)];
    if (isComment(entry)) {
      keys.push(
        noteFingerprint({
          id: entry.id,
          entityId: typeof entry.metadata?.source_contact_id === 'string' ? entry.metadata.source_contact_id : undefined,
          createdAt: entry.created_at,
          text: stripHtml(entry.summary || entry.title || ''),
          sha256: commentContentSha(entry),
        }),
      );
    }
    if (keys.some((key) => seen.has(key))) continue;
    for (const key of keys) seen.add(key);
    unique.push(entry);
  }
  return unique;
}

function groupWhatsapp(entries: StreamEntry[]): StreamEntry[] {
  const used = new Set<string>();
  const result: StreamEntry[] = [];
  for (const entry of entries) {
    if (!isWhatsapp(entry) || used.has(entry.id)) {
      if (!isWhatsapp(entry)) result.push(entry);
      continue;
    }
    const chatId = String(bitrixHistory(entry)?.chat_id || '');
    const day = entry.created_at.slice(0, 10);
    const group: StreamEntry[] = [];
    const sourceSeen = new Set<string>();
    for (const item of entries) {
      if (!isWhatsapp(item) || used.has(item.id)) continue;
      const itemChat = String(bitrixHistory(item)?.chat_id || '');
      if (item.created_at.slice(0, 10) !== day || itemChat !== chatId) continue;
      used.add(item.id);
      const key = timelineSourceKey(item);
      if (sourceSeen.has(key)) continue;
      sourceSeen.add(key);
      group.push(item);
    }
    const latest = [...group].sort((a, b) => b.created_at.localeCompare(a.created_at))[0] || entry;
    result.push({
      ...latest,
      metadata: {
        ...(latest.metadata || {}),
        grouped_message_count: group.length,
        grouped_ids: group.map((item) => item.id),
      },
    });
  }
  return result;
}

function StreamIcon({ type }: { type: string }) {
  const name = TYPE_ICONS[type] || 'activity';
  return (
    <span className={`crm-stream-card__icon crm-stream-card__icon--${type}`}>
      <IhIcon name={name} size={16} />
    </span>
  );
}

function WhatsAppCard({
  entry,
  locale,
  onOpen,
}: {
  entry: StreamEntry;
  locale: string;
  onOpen: () => void;
}) {
  const parsed = parseWhatsappMedia(entry.summary || entry.title);
  const count = Number(entry.metadata?.grouped_message_count || 1);
  const direction = whatsappDirection(entry);
  return (
    <article className="crm-stream-card" data-testid="stream-whatsapp-card" data-activity-type="whatsapp">
      <StreamIcon type="whatsapp" />
      <div className="crm-stream-card__body">
        <div className="crm-stream-card__top">
          <strong>WhatsApp</strong>
          <time>{formatWhen(entry.created_at, locale)}</time>
        </div>
        <p>
          {direction === 'outgoing' ? 'Giden' : direction === 'system' ? 'Sistem' : 'Gelen'}
          {' · '}
          {whatsappSender(entry)}
        </p>
        <p className="crm-stream-card__preview">{parsed.text || entry.title.replace(/^WhatsApp:\s*/i, '') || '—'}</p>
        {count > 1 ? <p className="crm-stream-card__meta">{count} mesaj</p> : null}
        <div className="crm-stream-card__actions">
          <Button type="button" size="sm" onClick={onOpen}>
            Aç
          </Button>
        </div>
      </div>
    </article>
  );
}

function CommentCard({ entry, locale }: { entry: StreamEntry; locale: string }) {
  const text = stripHtml(entry.summary || entry.title.replace(/^Yorum:\s*/i, ''));
  if (!text || looksLikePayloadDump(text)) return null;
  const label = entry.activity_type === 'note' || entry.activity_type === 'internal_discussion' ? 'Not' : 'Yorum';
  return (
    <article className="crm-stream-card" data-testid="stream-comment-card" data-activity-type={entry.activity_type || 'comment'}>
      <StreamIcon type="comment" />
      <div className="crm-stream-card__body">
        <div className="crm-stream-card__top">
          <strong>{label}</strong>
          <time>{formatWhen(entry.created_at, locale)}</time>
        </div>
        <p>{entry.actor_name || bitrixHistory(entry)?.author_name || '—'}</p>
        <p className="crm-stream-card__preview">{text}</p>
      </div>
    </article>
  );
}

function TaskCard({
  entry,
  locale,
  onOpen,
}: {
  entry: StreamEntry;
  locale: string;
  onOpen: () => void;
}) {
  const due = typeof entry.metadata?.due_date === 'string' ? entry.metadata.due_date : null;
  const status = String(entry.metadata?.task_status || entry.status || '');
  const owner = String(entry.metadata?.assigned_user_name || entry.actor_name || '—');
  return (
    <article className="crm-stream-card" data-testid="stream-task-card" data-activity-type="task">
      <StreamIcon type="task" />
      <div className="crm-stream-card__body">
        <div className="crm-stream-card__top">
          <strong>Görev</strong>
          <time>{formatWhen(entry.created_at, locale)}</time>
        </div>
        <p className="crm-stream-card__meta">{taskStatusLabel(status)}</p>
        <h3>{entry.title.replace(/^Görev:\s*/i, '')}</h3>
        <p>Son tarih: {due ? formatWhen(due, locale) : '—'}</p>
        <p>Sorumlu: {owner}</p>
        <div className="crm-stream-card__actions">
          <Button type="button" size="sm" onClick={onOpen}>
            Aç
          </Button>
        </div>
      </div>
    </article>
  );
}

function DocumentCard({
  entry,
  locale,
  onOpen,
}: {
  entry: StreamEntry;
  locale: string;
  onOpen: () => void;
}) {
  const doc = entry.document;
  return (
    <article className="crm-stream-card" data-testid="stream-document-card" data-activity-type="document">
      <StreamIcon type="document" />
      <div className="crm-stream-card__body">
        <div className="crm-stream-card__top">
          <strong>Belge</strong>
          <time>{formatWhen(entry.created_at, locale)}</time>
        </div>
        <h3>{doc?.original_file_name || entry.title}</h3>
        <p>{doc?.category || doc?.document_type || entry.summary || '—'}</p>
        <div className="crm-stream-card__actions">
          <Button type="button" size="sm" onClick={onOpen}>
            Aç / Önizle
          </Button>
        </div>
      </div>
    </article>
  );
}

function TaskDetailDrawer({
  activityId,
  onClose,
}: {
  activityId: string;
  onClose: () => void;
}) {
  const query = useQuery({
    queryKey: ['crm', 'activities', activityId],
    queryFn: () => fetchActivity(activityId),
  });
  const [mode, setMode] = useState<'detail' | 'edit'>('detail');
  const item = query.data;
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [taskStatus, setTaskStatus] = useState('not_started');
  const save = useMutation({
    mutationFn: async () => {
      await updateActivity(activityId, {
        title: title.trim() || item?.title,
        description: description.trim() || undefined,
        task_status: taskStatus,
        status: taskStatus === 'completed' ? 'completed' : 'planned',
      });
    },
    onSuccess: () => {
      void query.refetch();
      setMode('detail');
    },
  });

  const startEdit = () => {
    if (!item) return;
    setTitle(item.title);
    setDescription(item.description || '');
    setTaskStatus(item.task_status || 'not_started');
    setMode('edit');
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    save.mutate();
  };

  return (
    <div className="crm-contact-card__wa-drawer" data-testid="crm-tasks-drawer" role="dialog">
      <div className="crm-contact-card__wa-panel crm-task-drawer">
        <div className="crm-contact-card__wa-head">
          <strong>{mode === 'edit' ? 'Görevi düzenle' : 'Görev'}</strong>
          <Button type="button" size="sm" variant="secondary" onClick={onClose}>
            Kapat
          </Button>
        </div>
        <div className="crm-task-drawer__body">
          {query.isLoading ? <p>Yükleniyor…</p> : null}
          {query.isError ? <p>Görev açılamadı.</p> : null}
          {item && mode === 'detail' ? (
            <>
              <h3>{item.title}</h3>
              <dl className="crm-task-drawer__kv">
                <dt>Durum</dt>
                <dd>{taskStatusLabel(item.task_status || item.status)}</dd>
                <dt>Sorumlu</dt>
                <dd>{item.assigned_user_name || item.owner_name || '—'}</dd>
                <dt>Son tarih</dt>
                <dd>{item.due_date ? new Date(item.due_date).toLocaleString() : '—'}</dd>
              </dl>
              {item.description ? <p className="crm-stream-card__preview">{stripHtml(item.description)}</p> : null}
              <Button type="button" size="sm" onClick={startEdit}>
                Düzenle
              </Button>
            </>
          ) : null}
          {item && mode === 'edit' ? (
            <form onSubmit={submit} className="crm-contact-card__panel">
              <Input label="Başlık" value={title} onChange={(event) => setTitle(event.target.value)} />
              <TextArea label="Açıklama" value={description} onChange={(event) => setDescription(event.target.value)} />
              <Select label="Durum" value={taskStatus} onChange={(event) => setTaskStatus(event.target.value)}>
                <option value="not_started">Başlamadı</option>
                <option value="in_progress">Devam ediyor</option>
                <option value="waiting">Beklemede</option>
                <option value="completed">Tamamlandı</option>
              </Select>
              <Button type="submit" size="sm" disabled={save.isPending}>
                Kaydet
              </Button>
            </form>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function PilotHistoryStream({
  entries,
  documents,
  locale,
  loading,
}: {
  entries: ContactTimelineEntry[];
  documents: GalleryDocument[];
  locale: string;
  loading?: boolean;
}) {
  const [filter, setFilter] = useState<PilotHistoryFilter>('all');
  const [emailFocus, setEmailFocus] = useState<StreamEntry | null>(null);
  const [whatsappFocus, setWhatsappFocus] = useState<StreamEntry | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [preview, setPreview] = useState<GalleryDocument | null>(null);

  const merged = useMemo(() => {
    const visibleDocs = documents.filter((item) => !item.hidden_from_view);
    return uniqueBySource(
      [...entries, ...visibleDocs.map(documentToStreamEntry)].sort((a, b) =>
        b.created_at.localeCompare(a.created_at),
      ),
    );
  }, [documents, entries]);

  const filtered = useMemo(() => {
    const items = merged.filter((entry) => matchesFilter(entry, filter));
    return groupWhatsapp(items);
  }, [filter, merged]);

  const groups = useMemo(() => {
    const map = new Map<string, StreamEntry[]>();
    for (const entry of filtered) {
      const label = new Date(entry.created_at).toLocaleDateString(locale, {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
      const list = map.get(label) ?? [];
      list.push(entry);
      map.set(label, list);
    }
    return Array.from(map, ([label, items]) => ({ label, items }));
  }, [filtered, locale]);

  const conversation = useMemo(() => {
    if (!whatsappFocus) return [];
    const chatId = String(bitrixHistory(whatsappFocus)?.chat_id || '');
    const pool = entries.filter((entry) => {
      if (!isWhatsapp(entry)) return false;
      if (!chatId) return true;
      return String(bitrixHistory(entry)?.chat_id || '') === chatId;
    });
    return sortWhatsappConversation(pool);
  }, [entries, whatsappFocus]);

  return (
    <section className="crm-verify-detail__section" data-testid="contact-timeline">
      <h2>
        Geçmiş / İletişim <span>{filtered.length}</span>
      </h2>
      <div className="crm-contact-card__history-filters" data-testid="contact-timeline-filters">
        {PILOT_HISTORY_FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={filter === item.id ? 'is-active' : undefined}
            data-testid={`timeline-filter-${item.id}`}
            onClick={() => setFilter(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {loading ? <p>Loading…</p> : null}
      {groups.length ? (
        <div className="crm-verify-detail__timeline crm-stream">
          {groups.map((group) => (
            <div key={group.label} className="crm-contact-card__timeline-day">
              <p className="crm-contact-card__date-sep">{group.label}</p>
              {group.items.map((entry) => {
                if (entry.activity_type === 'email') {
                  return <EmailCard key={entry.id} entry={entry} locale={locale} onOpen={() => setEmailFocus(entry)} />;
                }
                if (isWhatsapp(entry)) {
                  return (
                    <WhatsAppCard key={entry.id} entry={entry} locale={locale} onOpen={() => setWhatsappFocus(entry)} />
                  );
                }
                if (isComment(entry)) {
                  return <CommentCard key={entry.id} entry={entry} locale={locale} />;
                }
                if (entry.activity_type === 'task') {
                  return <TaskCard key={entry.id} entry={entry} locale={locale} onOpen={() => setTaskId(entry.id)} />;
                }
                if (entry.activity_type === 'document' && entry.document) {
                  return (
                    <DocumentCard
                      key={entry.id}
                      entry={entry}
                      locale={locale}
                      onOpen={() => setPreview(entry.document || null)}
                    />
                  );
                }
                return (
                  <article key={entry.id} className="crm-stream-card">
                    <StreamIcon type={entry.activity_type} />
                    <div className="crm-stream-card__body">
                      <div className="crm-stream-card__top">
                        <strong>{entry.title}</strong>
                        <time>{formatWhen(entry.created_at, locale)}</time>
                      </div>
                      {entry.summary ? <p className="crm-stream-card__preview">{stripHtml(entry.summary)}</p> : null}
                    </div>
                  </article>
                );
              })}
            </div>
          ))}
        </div>
      ) : (
        <p>Kayıt yok</p>
      )}
      {emailFocus ? <EmailDetail entry={emailFocus} locale={locale} onClose={() => setEmailFocus(null)} /> : null}
      {whatsappFocus ? (
        <div className="crm-contact-card__wa-drawer" data-testid="whatsapp-conversation">
          <div className="crm-contact-card__wa-panel">
            <div className="crm-contact-card__wa-head">
              <strong>WhatsApp konuşması</strong>
              <Button type="button" size="sm" variant="secondary" onClick={() => setWhatsappFocus(null)}>
                Kapat
              </Button>
            </div>
            <WhatsAppThread messages={conversation} locale={locale} documents={documents} testId="whatsapp-pilot-thread" />
          </div>
        </div>
      ) : null}
      {taskId ? <TaskDetailDrawer activityId={taskId} onClose={() => setTaskId(null)} /> : null}
      {preview ? <DocumentPreviewDialog doc={preview} onClose={() => setPreview(null)} /> : null}
    </section>
  );
}
