'use client';

import { useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { formatDateTime } from '../../_lib/format';
import { getMessagesFor } from '../../_lib/permissions';
import { usePortalSession } from '../../_state/portal-session';
import { PageHeader } from '../page-header';

export function MessagesView() {
  const t = useTranslations('portalG9');
  const locale = useLocale();
  const { investorId } = usePortalSession();
  const messages = useMemo(
    () => (investorId ? getMessagesFor(investorId) : []),
    [investorId],
  );
  const [activeId, setActiveId] = useState<string | null>(messages[0]?.id ?? null);
  const active = messages.find((m) => m.id === activeId) ?? null;

  if (!investorId) return null;

  return (
    <div className="portal-page" data-testid="portal-messages">
      <PageHeader title={t('messages.title')} subtitle={t('messages.subtitle')} />
      <div className="portal-msg-layout">
        <aside className="portal-msg-list" aria-label={t('messages.inbox')}>
          {messages.map((m) => (
            <button
              key={m.id}
              type="button"
              aria-current={activeId === m.id ? 'true' : undefined}
              className={m.read ? undefined : 'unread'}
              onClick={() => setActiveId(m.id)}
              data-testid={`portal-msg-${m.id}`}
            >
              <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{m.from}</div>
              <strong style={{ display: 'block', fontSize: '0.86rem' }}>{m.subject}</strong>
              <div style={{ fontSize: '0.78rem', color: 'var(--muted)' }}>{m.preview}</div>
            </button>
          ))}
        </aside>
        <section className="portal-panel">
          {active ? (
            <>
              <h2 className="portal-panel__title">{active.subject}</h2>
              <p className="portal-panel__desc">
                {active.from} · {formatDateTime(active.at, locale)}
              </p>
              <div className="portal-msg-body">{active.body}</div>
            </>
          ) : (
            <div className="portal-empty">{t('messages.empty')}</div>
          )}
        </section>
      </div>
    </div>
  );
}
