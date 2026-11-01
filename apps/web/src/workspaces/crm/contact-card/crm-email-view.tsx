'use client';

import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';

import { Button } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { fetchActivity } from '@/workspaces/crm/api/activities';
import { fetchEmailReplyContext } from '@/workspaces/crm/api/communication';
import { EmailSendComposer } from '@/workspaces/crm/contact-card/email-send-composer';
import {
  escapeHtml,
  parseEmailContent,
  sanitizeHtml,
} from '@/workspaces/crm/contact-card/history-html';
import type { CrmActivityAttachment } from '@/workspaces/crm/types/activities';

export type EmailViewEntry = {
  id: string;
  title: string;
  summary?: string | null;
  actor_name?: string | null;
  created_at: string;
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

function isActivityId(id: string) {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id);
}

function attachmentHref(item: CrmActivityAttachment) {
  if (item.document_id) return `/workspaces/crm/documents/${item.document_id}`;
  return item.file_url || '';
}

export function EmailCard({
  entry,
  locale,
  onOpen,
}: {
  entry: EmailViewEntry;
  locale: string;
  onOpen: () => void;
}) {
  const tCard = useTranslations('crm.contactCard.ui');
  const parsed = parseEmailContent(entry.title, entry.summary);
  return (
    <article className="crm-stream-card" data-testid="stream-email-card" data-activity-type="email">
      <span className="crm-stream-card__icon crm-stream-card__icon--email">
        <IhIcon name="mail" size={16} />
      </span>
      <div className="crm-stream-card__body">
        <div className="crm-stream-card__top">
          <strong>{tCard('k6fe4c6c71e')}</strong>
          <time>{formatWhen(entry.created_at, locale)}</time>
        </div>
        <h3>{parsed.subject}</h3>
        <p>
          <span>{tCard('k27a531eaf9')}</span> {parsed.sender?.label || entry.actor_name || '—'}
        </p>
        <p>
          <span>{tCard('k210d38d342')}</span> {parsed.recipients.map((item) => item.label).join(', ') || '—'}
        </p>
        {parsed.preview ? <p className="crm-stream-card__preview">{parsed.preview}</p> : null}
        <div className="crm-stream-card__actions">
          <Button type="button" size="sm" onClick={onOpen}>{tCard('k019f2bd44b')}</Button>
        </div>
      </div>
    </article>
  );
}

export function EmailDetail({
  entry,
  locale,
  onClose,
  canSend = false,
  communicationId = null,
  activityId = null,
  contactId = null,
}: {
  entry: EmailViewEntry;
  locale: string;
  onClose: () => void;
  canSend?: boolean;
  communicationId?: string | null;
  activityId?: string | null;
  contactId?: string | null;
}) {
  const tCard = useTranslations('crm.contactCard.ui');
  const t = useTranslations('crm.communication.workspace');
  const [composeMode, setComposeMode] = useState<'reply' | 'reply_all' | null>(null);
  const canReply = canSend && Boolean(communicationId || activityId);
  const contextQuery = useQuery({
    queryKey: ['crm', 'communications', 'email-reply', communicationId || '', activityId || ''],
    queryFn: () =>
      fetchEmailReplyContext({
        communication_id: communicationId,
        activity_id: activityId,
      }),
    enabled: canReply,
  });
  const detailQuery = useQuery({
    queryKey: ['crm', 'activities', entry.id],
    queryFn: () => fetchActivity(entry.id),
    enabled: isActivityId(entry.id),
  });
  const body = detailQuery.data?.description || entry.summary;
  const parsed = useMemo(
    () => parseEmailContent(entry.title, body),
    [entry.title, body],
  );
  const attachments = detailQuery.data?.attachments || [];
  const html = sanitizeHtml(parsed.html || `<p>${escapeHtml(parsed.text).replace(/\n/g, '<br>')}</p>`);

  return (
    <div className="crm-email-detail" data-testid="email-detail-view" role="dialog">
      <div className="crm-email-detail__panel">
        <header>
          <div>
            <small>{tCard('k6fe4c6c71e')}</small>
            <h2>{parsed.subject}</h2>
          </div>
          <div className="crm-email-detail__actions">
            {canReply ? (
              <Button type="button" size="sm" onClick={() => setComposeMode('reply')} data-testid="crm-email-reply">
                {t('emailReply')}
              </Button>
            ) : null}
            {canReply && contextQuery.data?.can_reply_all ? (
              <Button
                type="button"
                size="sm"
                variant="secondary"
                onClick={() => setComposeMode('reply_all')}
                data-testid="crm-email-reply-all"
              >
                {t('emailReplyAll')}
              </Button>
            ) : null}
            <Button type="button" size="sm" variant="secondary" onClick={onClose}>
              Kapat
            </Button>
          </div>
        </header>
        <dl>
          <div>
            <dt>{tCard('k92a6eb36f4')}</dt>
            <dd>{parsed.subject}</dd>
          </div>
          <div>
            <dt>{tCard('k44cf7471cc')}</dt>
            <dd>{parsed.sender?.label || entry.actor_name || '—'}</dd>
          </div>
          <div>
            <dt>{tCard('k2f73c087e6')}</dt>
            <dd>{parsed.recipients.map((item) => item.label).join(', ') || '—'}</dd>
          </div>
          {parsed.cc.length ? (
            <div>
              <dt>CC</dt>
              <dd>{parsed.cc.map((item) => item.label).join(', ')}</dd>
            </div>
          ) : null}
          <div>
            <dt>{tCard('kd7be79c145')}</dt>
            <dd>{formatWhen(entry.created_at, locale)}</dd>
          </div>
        </dl>
        <div
          className="crm-email-detail__body"
          data-testid="email-sanitized-body"
          dangerouslySetInnerHTML={{ __html: html }}
        />
        {parsed.links.length ? (
          <div className="crm-email-detail__links">
            <strong>{tCard('k14155eeb2d')}</strong>
            {parsed.links.map((link) => (
              <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer nofollow">
                {link.label.replace(/^mailto:/i, '')}
              </a>
            ))}
          </div>
        ) : null}
        {attachments.length ? (
          <div className="crm-email-detail__attachments">
            <strong>{tCard('k5aa5396c53')}</strong>
            {attachments.map((item) => {
              const href = attachmentHref(item);
              return href ? (
                <a key={item.id} href={href} target="_blank" rel="noreferrer">
                  {item.file_name}
                </a>
              ) : (
                <span key={item.id}>{item.file_name}</span>
              );
            })}
          </div>
        ) : null}
        {composeMode ? (
          <EmailSendComposer
            mode={composeMode}
            contactId={contactId}
            communicationId={communicationId}
            activityId={activityId}
            onSent={() => setComposeMode(null)}
          />
        ) : null}
      </div>
    </div>
  );
}
