'use client';

import type { Route } from 'next';
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import {
  Button,
  EmptyState,
  ErrorState,
  Input,
  SegmentedControl,
  Select,
  StatusChip,
  TextArea,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { canCreateCommunications } from '@/lib/crm/crm-permissions';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';

import { CommunicationComposer } from '../communication-composer';

import {
  CHANNEL_ICON,
  CHANNEL_STATUS_TONE,
  COMM_STREAM_CHANNELS,
  countByChannel,
  filterStreamRows,
  makeCommunicationFixture,
  mapApiChannelToStream,
  threadToStreamRow,
  TIMELINE_KIND_TONE,
  type CommAttachment,
  type CommConversation,
  type CommDsFilters,
  type CommSortKey,
  type CommStreamChannel,
  type CommStreamRow,
  type CommTimelineItem,
  type CommTimelineItemKind,
  EMPTY_COMM_FILTERS,
} from './communication-ds-model';

import './communication-ds.css';

const PAGE_SIZE = 10;

function channelIconForKind(kind: CommTimelineItemKind): (typeof CHANNEL_ICON)[Exclude<CommStreamChannel, 'all'>] {
  if (kind === 'system') return CHANNEL_ICON.note;
  return CHANNEL_ICON[kind];
}

function StreamAvatar({
  initials,
  tone,
  size = 'sm',
}: {
  initials: string;
  tone: CommStreamRow['avatarTone'];
  size?: 'sm' | 'lg';
}) {
  return (
    <span className={`comm-ds__avatar is-${tone}${size === 'lg' ? ' is-lg' : ''}`} aria-hidden="true">
      {initials}
    </span>
  );
}

function AttachmentCard({ attachment }: { attachment: CommAttachment }) {
  const t = useTranslations('crm.communication.ds');
  return (
    <div className="comm-ds__attachment">
      <span className="comm-ds__attachment-icon" aria-hidden="true">
        <IhIcon name="documents" size={13} />
      </span>
      <div className="comm-ds__list-item-main">
        <span className="comm-ds__attachment-name">{attachment.name}</span>
        <span className="comm-ds__attachment-size">
          {t(`attachments.${attachment.kind}`)} · {attachment.sizeLabel}
        </span>
      </div>
      <Button type="button" variant="secondary" size="sm">
        {t('attachments.download')}
      </Button>
    </div>
  );
}

function TimelineBubble({ item }: { item: CommTimelineItem }) {
  const t = useTranslations('crm.communication.ds');
  const kind = item.kind;
  const alignment =
    item.direction === 'outbound'
      ? 'is-outbound'
      : item.direction === 'system' || item.direction === 'internal'
        ? item.direction === 'system'
          ? 'is-system'
          : 'is-internal'
        : '';

  return (
    <article className={`comm-ds__bubble is-${kind} ${alignment}`.trim()}>
      <div className="comm-ds__bubble-head">
        <StatusChip tone={TIMELINE_KIND_TONE[kind]}>{t(`channels.${kind === 'system' ? 'note' : kind}`)}</StatusChip>
        <span className="comm-ds__bubble-meta">
          <span>{item.owner}</span>
          <time>{item.timestamp}</time>
        </span>
      </div>
      <p className="comm-ds__bubble-body">{item.body}</p>
      {item.relatedEntity ? (
        <div className="comm-ds__bubble-meta">
          <span>{item.relatedEntity}</span>
        </div>
      ) : null}
      {item.attachments?.length ? (
        <div className="comm-ds__attachments">
          {item.attachments.map((att) => (
            <AttachmentCard key={att.id} attachment={att} />
          ))}
        </div>
      ) : null}
    </article>
  );
}

function InfoPanel({
  conversation,
  onClose,
}: {
  conversation: CommConversation | null;
  onClose?: () => void;
}) {
  const t = useTranslations('crm.communication.ds');
  const router = useRouter();

  if (!conversation) {
    return (
      <div className="comm-ds__info">
        <div className="comm-ds__empty">
          <IhIcon name="user" size={22} />
          <strong>{t('info.emptyTitle')}</strong>
          <p>{t('info.emptyDescription')}</p>
        </div>
      </div>
    );
  }

  const { contact } = conversation;

  return (
    <div className="comm-ds__info">
      {onClose ? (
        <div className="comm-ds__card-head">
          <h3>{t('info.title')}</h3>
          <button type="button" className="comm-ds__card-link" onClick={onClose}>
            {t('info.close')}
          </button>
        </div>
      ) : null}

      <section className="comm-ds__card" aria-label={t('info.contact')}>
        <div className="comm-ds__card-head">
          <h3>{t('info.contact')}</h3>
          <button type="button" className="comm-ds__card-link">
            {t('info.edit')}
          </button>
        </div>
        <div className="comm-ds__contact-hero">
          <StreamAvatar initials={contact.initials} tone={contact.avatarTone} size="lg" />
          <div className="comm-ds__conv-identity">
            <div className="comm-ds__conv-name-row">
              <strong className="comm-ds__conv-name">{contact.name}</strong>
              <StatusChip tone={contact.statusTone}>{contact.status}</StatusChip>
            </div>
            <div className="comm-ds__conv-meta">
              <span>{contact.company}</span>
            </div>
          </div>
          <span className="comm-ds__score" title={t('info.score')}>
            {contact.score}
          </span>
        </div>
        <dl className="comm-ds__dl">
          <div className="comm-ds__dl-row">
            <dt>{t('info.fields.company')}</dt>
            <dd>{contact.company}</dd>
          </div>
          <div className="comm-ds__dl-row">
            <dt>{t('info.fields.email')}</dt>
            <dd>{contact.email}</dd>
          </div>
          <div className="comm-ds__dl-row">
            <dt>{t('info.fields.phone')}</dt>
            <dd>{contact.phone}</dd>
          </div>
          <div className="comm-ds__dl-row">
            <dt>{t('info.fields.location')}</dt>
            <dd>{contact.location}</dd>
          </div>
          <div className="comm-ds__dl-row">
            <dt>{t('info.fields.source')}</dt>
            <dd>{contact.source}</dd>
          </div>
          <div className="comm-ds__dl-row">
            <dt>{t('info.fields.created')}</dt>
            <dd>{contact.createdLabel}</dd>
          </div>
        </dl>
        {contact.tags.length ? (
          <div className="comm-ds__tags">
            {contact.tags.map((tag) => (
              <span key={tag} className="comm-ds__tag">
                {tag}
              </span>
            ))}
          </div>
        ) : null}
        {contact.detailHref ? (
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => router.push(contact.detailHref as Route)}
          >
            {t('info.viewDetail')}
            <IhIcon name="arrowRight" size={12} />
          </Button>
        ) : null}
      </section>

      <section className="comm-ds__card" aria-label={t('info.activities')}>
        <div className="comm-ds__card-head">
          <h3>{t('info.activities')}</h3>
          <button type="button" className="comm-ds__card-link">
            {t('info.seeAll')}
          </button>
        </div>
        <ul className="comm-ds__list">
          {conversation.recentActivities.map((act) => (
            <li key={act.id} className="comm-ds__list-item">
              <span className="comm-ds__act-dot" aria-hidden="true">
                <IhIcon name={channelIconForKind(act.kind)} size={11} />
              </span>
              <div className="comm-ds__list-item-main">
                <span className="comm-ds__list-title">{act.label}</span>
                <StatusChip tone={TIMELINE_KIND_TONE[act.kind]}>{t(`channels.${act.kind === 'system' ? 'note' : act.kind}`)}</StatusChip>
              </div>
              <span className="comm-ds__list-meta">{act.timeLabel}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="comm-ds__card" aria-label={t('info.tasks')}>
        <div className="comm-ds__card-head">
          <h3>{t('info.tasks')}</h3>
        </div>
        <ul className="comm-ds__list">
          {conversation.upcomingTasks.length === 0 ? (
            <li className="comm-ds__list-meta">{t('info.noTasks')}</li>
          ) : (
            conversation.upcomingTasks.map((task) => (
              <li key={task.id} className="comm-ds__list-item">
                <span className="comm-ds__task-check" aria-hidden="true" />
                <div className="comm-ds__list-item-main">
                  <span className="comm-ds__list-title">{task.title}</span>
                  <span className="comm-ds__list-meta">
                    {task.dueLabel} · {task.owner}
                  </span>
                </div>
              </li>
            ))
          )}
        </ul>
      </section>

      <section className="comm-ds__card" aria-label={t('info.projects')}>
        <div className="comm-ds__card-head">
          <h3>{t('info.projects')}</h3>
        </div>
        <ul className="comm-ds__list">
          {conversation.relatedProjects.map((proj) => (
            <li key={proj.id} className="comm-ds__project">
              <span className="comm-ds__project-name">{proj.name}</span>
              <span className="comm-ds__list-meta">{proj.location}</span>
              <StatusChip tone={proj.statusTone}>{proj.status}</StatusChip>
            </li>
          ))}
        </ul>
      </section>

      <section className="comm-ds__card" aria-label={t('info.notes')}>
        <div className="comm-ds__card-head">
          <h3>{t('info.notes')}</h3>
        </div>
        {conversation.crmNotes.map((note, idx) => (
          <p key={idx} className="comm-ds__note-box">
            {note}
          </p>
        ))}
      </section>

      <section className="comm-ds__card" aria-label={t('info.ai')}>
        <div className="comm-ds__card-head">
          <h3>{t('info.ai')}</h3>
          <IhIcon name="sparkles" size={13} />
        </div>
        {conversation.aiSuggestions.map((tip, idx) => (
          <p key={idx} className="comm-ds__ai-item">
            {tip}
          </p>
        ))}
      </section>
    </div>
  );
}

function CommunicationDsWorkspaceInner() {
  const t = useTranslations('crm.communication.ds');
  const locale = useLocale();
  const router = useRouter();
  const { authLoading, user, canViewCommunications } = useCrmAccess();

  const fixture = useMemo(() => makeCommunicationFixture(), []);
  const [filters, setFilters] = useState<CommDsFilters>(EMPTY_COMM_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(fixture.rows[0]?.id ?? null);
  const [composerOpen, setComposerOpen] = useState(false);
  const [composerChannel, setComposerChannel] = useState<Exclude<CommStreamChannel, 'all'>>('whatsapp');
  const [draftMessage, setDraftMessage] = useState('');
  const [infoOpen, setInfoOpen] = useState(false);
  const [starredIds, setStarredIds] = useState<Set<string>>(
    () => new Set(fixture.rows.filter((r) => r.starred).map((r) => r.id)),
  );

  // Channel is a global workspace filter applied client-side so tab counts stay stable.
  const threadsQuery = useQuery({
    ...communicationQueries.threads({
      search: filters.search || undefined,
      page: 1,
      page_size: 50,
      sort_by: 'last_communication_at',
      sort_dir: 'desc',
    }),
    enabled: !authLoading && canViewCommunications,
    retry: false,
  });

  const selectedThreadQuery = useQuery({
    ...communicationQueries.threadDetail(selectedId),
    enabled: !authLoading && canViewCommunications && Boolean(selectedId) && !selectedId?.startsWith('thr-'),
    retry: false,
  });

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const apiRows: CommStreamRow[] = useMemo(() => {
    const items = threadsQuery.data?.items ?? [];
    if (items.length === 0) return [];
    return items.map((thread) => threadToStreamRow(thread, locale, thread.subject || undefined));
  }, [threadsQuery.data, locale]);

  const usingFixture = apiRows.length === 0;
  const baseRows = usingFixture ? fixture.rows : apiRows;

  const rowsWithStars = useMemo(
    () =>
      baseRows.map((row) => ({
        ...row,
        starred: starredIds.has(row.id) || row.starred,
      })),
    [baseRows, starredIds],
  );

  const filtered = useMemo(() => filterStreamRows(rowsWithStars, filters), [rowsWithStars, filters]);
  const channelCounts = useMemo(() => countByChannel(rowsWithStars), [rowsWithStars]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, pages);
  const pageItems = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);

  useEffect(() => {
    if (!selectedId) {
      if (pageItems[0]) setSelectedId(pageItems[0].id);
      return;
    }
    if (filtered.every((r) => r.id !== selectedId)) {
      setSelectedId(pageItems[0]?.id ?? null);
    }
  }, [selectedId, filtered, pageItems]);

  const selectedRow = rowsWithStars.find((r) => r.id === selectedId) ?? null;

  const conversation: CommConversation | null = useMemo(() => {
    if (!selectedRow) return null;
    if (usingFixture) {
      return fixture.conversations[selectedRow.id] ?? null;
    }
    const apiThread = selectedThreadQuery.data;
    if (!apiThread) {
      return {
        threadId: selectedRow.id,
        channel: selectedRow.channel,
        channelActive: true,
        contact: {
          name: selectedRow.contactName,
          initials: selectedRow.initials,
          avatarTone: selectedRow.avatarTone,
          company: selectedRow.company || '—',
          email: '—',
          phone: '—',
          location: '—',
          source: 'CRM',
          status: selectedRow.subject || 'Aktif',
          statusTone: 'info',
          score: 0,
          createdLabel: '—',
          tags: [],
        },
        timeline: [],
        recentActivities: [],
        upcomingTasks: [],
        relatedProjects: [],
        crmNotes: [],
        aiSuggestions: [],
      };
    }
    const timeline: CommTimelineItem[] = apiThread.communications.map((msg) => ({
      id: msg.id,
      kind: mapApiChannelToStream(msg.channel) as CommTimelineItemKind,
      direction: msg.direction,
      body: msg.preview ?? msg.subject ?? '—',
      timestamp: new Date(msg.created_at).toLocaleString(locale, {
        hour: '2-digit',
        minute: '2-digit',
        day: 'numeric',
        month: 'short',
      }),
      owner: msg.assigned_user_id ?? msg.owner_id ?? '—',
      relatedEntity: msg.recipient_entity_type ?? undefined,
      attachments: msg.has_attachments
        ? [{ id: `${msg.id}-att`, name: 'attachment', sizeLabel: '—', kind: 'pdf' as const }]
        : undefined,
    }));
    return {
      threadId: apiThread.id,
      channel: mapApiChannelToStream(apiThread.channel),
      channelActive: apiThread.status === 'open' || apiThread.status === 'pending',
      contact: {
        name: selectedRow.contactName,
        initials: selectedRow.initials,
        avatarTone: selectedRow.avatarTone,
        company: selectedRow.company || '—',
        email: '—',
        phone: '—',
        location: '—',
        source: 'CRM',
        status: apiThread.status,
        statusTone: 'info',
        score: 0,
        createdLabel: new Date(apiThread.created_at).toLocaleDateString(locale),
        tags: apiThread.tags ?? [],
      },
      timeline,
      recentActivities: timeline.slice(0, 4).map((item) => ({
        id: item.id,
        kind: item.kind,
        label: item.body.slice(0, 48),
        timeLabel: item.timestamp,
      })),
      upcomingTasks: [],
      relatedProjects: [],
      crmNotes: [],
      aiSuggestions: [],
    };
  }, [selectedRow, usingFixture, fixture.conversations, selectedThreadQuery.data, locale]);

  const patchFilters = useCallback((patch: Partial<CommDsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
  }, []);

  const toggleStar = (id: string) => {
    setStarredIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (authLoading) {
    return (
      <div className="comm-ds" data-testid="communication-ds-workspace">
        <div className="comm-ds__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="comm-ds__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canViewCommunications) {
    return (
      <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
    );
  }

  const loadingList = threadsQuery.isLoading && !usingFixture;

  return (
    <div className="comm-ds" data-testid="communication-ds-workspace">
      <header className="comm-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="comm-ds__header-actions">
          {canCreateCommunications(user) ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={() => setComposerOpen(true)}
              data-testid="communication-ds-compose"
            >
              <IhIcon name="plus" size={13} />
              {t('actions.compose')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="comm-ds__channels" aria-label={t('channels.aria')}>
        <SegmentedControl
          ariaLabel={t('channels.aria')}
          value={filters.channel}
          onChange={(next) => patchFilters({ channel: next as CommStreamChannel })}
          options={COMM_STREAM_CHANNELS.map((key) => ({
            value: key,
            label: (
              <>
                <span className="comm-ds__channel-label">{t(`channels.${key}`)}</span>
                <StatusChip tone="info" className="comm-ds__channel-count">
                  {channelCounts[key]}
                </StatusChip>
              </>
            ),
          }))}
        />
      </section>

      <div className="comm-ds__workspace">
        {/* LEFT — Stream */}
        <section className="comm-ds__panel comm-ds__panel--stream" aria-label={t('stream.title')}>
          <div className="comm-ds__panel-head">
            <h2>
              <IhIcon name="activity" size={14} />
              {t('stream.title')}
            </h2>
            <span className="comm-ds__panel-head-meta">
              {t('stream.count', { count: filtered.length })}
            </span>
          </div>

          <div className="comm-ds__toolbar" aria-label={t('toolbar.aria')}>
            <Input
              label={t('toolbar.search')}
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              placeholder={t('toolbar.searchPlaceholder')}
              data-testid="communication-ds-search"
            />
            <button
              type="button"
              className={`comm-ds__icon-btn${filters.unreadOnly ? ' is-active' : ''}`}
              aria-label={t('toolbar.filterUnread')}
              title={t('toolbar.filterUnread')}
              onClick={() => patchFilters({ unreadOnly: !filters.unreadOnly })}
            >
              <IhIcon name="inbox" size={13} />
            </button>
            <div className="comm-ds__sort">
              <Select
                label={t('toolbar.sort')}
                value={filters.sort}
                onChange={(e) => patchFilters({ sort: e.target.value as CommSortKey })}
              >
                <option value="recent">{t('sort.recent')}</option>
                <option value="unread">{t('sort.unread')}</option>
                <option value="name_asc">{t('sort.name_asc')}</option>
                <option value="name_desc">{t('sort.name_desc')}</option>
              </Select>
            </div>
          </div>

          <div className="comm-ds__stream">
            {loadingList ? (
              <div className="comm-ds__skeleton" aria-hidden="true">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="comm-ds__skeleton-row" />
                ))}
              </div>
            ) : pageItems.length === 0 ? (
              <div className="comm-ds__empty">
                <IhIcon name="empty" size={22} />
                <strong>{t('stream.emptyTitle')}</strong>
                <p>{t('stream.emptyDescription')}</p>
              </div>
            ) : (
              pageItems.map((row) => {
                const selected = row.id === selectedId;
                return (
                  <button
                    key={row.id}
                    type="button"
                    className={`comm-ds__row${selected ? ' is-selected' : ''}`}
                    onClick={() => {
                      setSelectedId(row.id);
                      setComposerChannel(row.channel);
                    }}
                    data-testid={`communication-ds-row-${row.id}`}
                  >
                    <StreamAvatar initials={row.initials} tone={row.avatarTone} />
                    <div className="comm-ds__row-main">
                      <div className="comm-ds__row-top">
                        <span className="comm-ds__row-name">{row.contactName}</span>
                        <StatusChip tone={CHANNEL_STATUS_TONE[row.channel]}>
                          {t(`channels.${row.channel}`)}
                        </StatusChip>
                      </div>
                      <p className="comm-ds__row-preview">{row.preview}</p>
                    </div>
                    <div className="comm-ds__row-side">
                      <span className="comm-ds__row-time">{row.timestamp}</span>
                      <div className="comm-ds__row-flags">
                        {row.hasAttachment ? <IhIcon name="documents" size={11} /> : null}
                        <span
                          className="comm-ds__star"
                          role="presentation"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleStar(row.id);
                          }}
                        >
                          {starredIds.has(row.id) || row.starred ? '★' : '☆'}
                        </span>
                        {row.unread > 0 ? <span className="comm-ds__unread">{row.unread}</span> : null}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="comm-ds__pagination">
            <span className="comm-ds__pagination-meta">
              {t('pagination.range', {
                from: filtered.length === 0 ? 0 : (pageSafe - 1) * PAGE_SIZE + 1,
                to: Math.min(pageSafe * PAGE_SIZE, filtered.length),
                total: filtered.length,
              })}
            </span>
            <div className="comm-ds__pagination-controls">
              <button
                type="button"
                className="comm-ds__page-btn"
                disabled={pageSafe <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                aria-label={t('pagination.prev')}
              >
                <IhIcon name="chevronLeft" size={12} />
              </button>
              {Array.from({ length: Math.min(pages, 5) }).map((_, i) => {
                const n = i + 1;
                return (
                  <button
                    key={n}
                    type="button"
                    className={`comm-ds__page-btn${pageSafe === n ? ' is-active' : ''}`}
                    onClick={() => setPage(n)}
                  >
                    {n}
                  </button>
                );
              })}
              <button
                type="button"
                className="comm-ds__page-btn"
                disabled={pageSafe >= pages}
                onClick={() => setPage((p) => Math.min(pages, p + 1))}
                aria-label={t('pagination.next')}
              >
                <IhIcon name="chevronRight" size={12} />
              </button>
            </div>
          </div>
        </section>

        {/* CENTER — Conversation */}
        <section
          className="comm-ds__panel comm-ds__panel--conversation"
          aria-label={
            conversation
              ? t(`conversation.types.${conversation.channel}`)
              : t('conversation.title')
          }
        >
          <div className="comm-ds__panel-head">
            <h2>
              {conversation
                ? t(`conversation.types.${conversation.channel}`)
                : t('conversation.title')}
            </h2>
            <button
              type="button"
              className="comm-ds__icon-btn comm-ds__info-toggle"
              aria-label={t('info.open')}
              onClick={() => setInfoOpen(true)}
            >
              <IhIcon name="user" size={13} />
            </button>
          </div>

          {!conversation || !selectedRow ? (
            <div className="comm-ds__conversation">
              <div className="comm-ds__empty">
                <IhIcon name="inbox" size={22} />
                <strong>{t('conversation.emptyTitle')}</strong>
                <p>{t('conversation.emptyDescription')}</p>
                {canCreateCommunications(user) ? (
                  <Button type="button" size="sm" onClick={() => setComposerOpen(true)}>
                    {t('actions.compose')}
                  </Button>
                ) : null}
              </div>
            </div>
          ) : (
            <div className="comm-ds__conversation">
              <div className="comm-ds__channel-pill">
                <IhIcon name={CHANNEL_ICON[conversation.channel]} size={12} />
                {t(`channels.${conversation.channel}`)}
                {conversation.channelActive ? (
                  <StatusChip tone="success">{t('conversation.active')}</StatusChip>
                ) : null}
              </div>

              <div className="comm-ds__conv-contact">
                <StreamAvatar
                  initials={conversation.contact.initials}
                  tone={conversation.contact.avatarTone}
                  size="lg"
                />
                <div className="comm-ds__conv-identity">
                  <div className="comm-ds__conv-name-row">
                    <h3 className="comm-ds__conv-name">{conversation.contact.name}</h3>
                    <StatusChip tone={conversation.contact.statusTone}>
                      {conversation.contact.status}
                    </StatusChip>
                  </div>
                  <div className="comm-ds__conv-meta">
                    <span>{conversation.contact.company}</span>
                    <span>{conversation.contact.location}</span>
                  </div>
                </div>
                <div className="comm-ds__conv-actions">
                  <button
                    type="button"
                    className="comm-ds__icon-btn"
                    aria-label={t('conversation.star')}
                    onClick={() => toggleStar(selectedRow.id)}
                  >
                    {starredIds.has(selectedRow.id) ? '★' : '☆'}
                  </button>
                  {conversation.contact.detailHref ? (
                    <Button
                      type="button"
                      variant="secondary"
                      size="sm"
                      onClick={() => router.push(conversation.contact.detailHref as Route)}
                    >
                      {t('conversation.viewLead')}
                    </Button>
                  ) : null}
                </div>
              </div>

              <div className="comm-ds__timeline">
                <div className="comm-ds__day-sep">{t('conversation.today')}</div>
                {conversation.timeline.length === 0 ? (
                  <EmptyState title={t('conversation.noMessages')} description={t('conversation.noMessagesHint')} />
                ) : (
                  conversation.timeline.map((item) => <TimelineBubble key={item.id} item={item} />)
                )}
              </div>

              <div className="comm-ds__composer">
                <div className="comm-ds__composer-tabs" role="tablist" aria-label={t('composer.channelsAria')}>
                  {(['whatsapp', 'email', 'phone', 'meeting', 'note'] as const).map((ch) => (
                    <button
                      key={ch}
                      type="button"
                      role="tab"
                      aria-selected={composerChannel === ch}
                      className={`comm-ds__composer-tab${composerChannel === ch ? ' is-active' : ''}`}
                      onClick={() => setComposerChannel(ch)}
                    >
                      <IhIcon name={CHANNEL_ICON[ch]} size={11} />
                      {t(`composer.tabs.${ch}`)}
                    </button>
                  ))}
                </div>
                <TextArea
                  value={draftMessage}
                  onChange={(e) => setDraftMessage(e.target.value)}
                  placeholder={t('composer.placeholder')}
                  aria-label={t('composer.placeholder')}
                  rows={3}
                />
                <div className="comm-ds__composer-bar">
                  <div className="comm-ds__composer-tools">
                    <button type="button" className="comm-ds__icon-btn" aria-label={t('composer.attach')} title={t('composer.attach')}>
                      <IhIcon name="documents" size={13} />
                    </button>
                    <button type="button" className="comm-ds__icon-btn" aria-label={t('composer.emoji')} title={t('composer.emoji')}>
                      <IhIcon name="sparkles" size={13} />
                    </button>
                    <button type="button" className="comm-ds__icon-btn" aria-label={t('composer.schedule')} title={t('composer.schedule')}>
                      <IhIcon name="calendar" size={13} />
                    </button>
                    <button type="button" className="comm-ds__icon-btn" aria-label={t('composer.template')} title={t('composer.template')}>
                      <IhIcon name="inbox" size={13} />
                    </button>
                    <button type="button" className="comm-ds__icon-btn" aria-label={t('composer.ai')} title={t('composer.ai')}>
                      <IhIcon name="sparkles" size={13} />
                    </button>
                  </div>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={() => {
                      setComposerOpen(true);
                      setDraftMessage('');
                    }}
                    disabled={!canCreateCommunications(user)}
                  >
                    {t('composer.send')}
                    <IhIcon name="arrowRight" size={12} />
                  </Button>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* RIGHT — Info (drawer on narrow) */}
        <div className={`comm-ds__drawer${infoOpen ? ' is-open' : ''}`}>
          <button
            type="button"
            className="comm-ds__drawer-backdrop"
            aria-label={t('info.close')}
            onClick={() => setInfoOpen(false)}
          />
          <aside className="comm-ds__panel comm-ds__panel--info" aria-label={t('info.title')}>
            <div className="comm-ds__panel-head">
              <h2>{t('info.title')}</h2>
            </div>
            <InfoPanel conversation={conversation} onClose={infoOpen ? () => setInfoOpen(false) : undefined} />
          </aside>
        </div>
      </div>

      <CommunicationComposer open={composerOpen} onClose={() => setComposerOpen(false)} />
    </div>
  );
}

export function CommunicationDsWorkspace() {
  return (
    <Suspense
      fallback={
        <div className="comm-ds" data-testid="communication-ds-workspace">
          <div className="comm-ds__skeleton" aria-hidden="true">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="comm-ds__skeleton-row" />
            ))}
          </div>
        </div>
      }
    >
      <CommunicationDsWorkspaceInner />
    </Suspense>
  );
}
