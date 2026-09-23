'use client';

import { useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select, StatusChip } from '@investhome/ui';

import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import type { CommunicationFeedItem } from '@/workspaces/crm/api/communication';
import { EmailDetail } from '@/workspaces/crm/contact-card/crm-email-view';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import { parseEmailContent } from '@/workspaces/crm/contact-card/history-html';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { WhatsAppThread } from '@/workspaces/crm/contact-card/whatsapp-thread';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';

import { UnmatchedCommunicationsView } from './unmatched-communications-view';

const PAGE_SIZE = 25;

const PROJECTS = [
  { value: '1307_k_st', label: '1307 K St' },
  { value: '1313_penn', label: '1313 Penn' },
  { value: '1812_h_pl', label: '1812 H Pl' },
  { value: '2319_ontario', label: '2319 Ontario' },
  { value: 'reit', label: 'REIT' },
  { value: 'the_temple', label: 'The Temple' },
  { value: 'uniloft', label: 'Uniloft' },
] as const;

function dateRange(value: string): { date_from?: string; date_to?: string } {
  if (!value) return {};
  const now = new Date();
  const end = now.toISOString();
  if (value === 'today') {
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return { date_from: start.toISOString(), date_to: end };
  }
  const days = value === '7d' ? 7 : value === '30d' ? 30 : value === '90d' ? 90 : 0;
  if (!days) return {};
  return { date_from: new Date(now.getTime() - days * 86_400_000).toISOString(), date_to: end };
}

function formatWhen(value: string | null | undefined, locale: string): string {
  if (!value) return '—';
  return new Date(value).toLocaleString(locale === 'tr' ? 'tr-TR' : 'en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function channelTone(channel: string): 'default' | 'info' {
  return channel === 'email' || channel === 'whatsapp' ? 'info' : 'default';
}

function channelLabelKey(channel: string): 'channels.email' | 'channels.whatsapp' | 'channels.call' | 'channels.comment' | 'channels.meeting' | 'channels.sms' {
  if (channel === 'whatsapp') return 'channels.whatsapp';
  if (channel === 'call' || channel === 'phone') return 'channels.call';
  if (channel === 'comment' || channel === 'note') return 'channels.comment';
  if (channel === 'meeting') return 'channels.meeting';
  if (channel === 'sms') return 'channels.sms';
  return 'channels.email';
}

function rowPreview(item: CommunicationFeedItem): string {
  if (item.channel === 'email') {
    return parseEmailContent(item.subject || '', item.preview).preview || item.preview || item.subject || '';
  }
  return item.preview || item.subject || '';
}

export function CrmCommunicationLiveWorkspace() {
  const t = useTranslations('crm.communication.workspace');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { authLoading, canViewCommunications } = useCrmAccess();
  const { openContact } = useContactCard();
  const searchParams = useSearchParams();
  const [searchDraft, setSearchDraft] = useState('');
  const [search, setSearch] = useState('');
  const [personDraft, setPersonDraft] = useState('');
  const [person, setPerson] = useState('');
  const [channel, setChannel] = useState(searchParams.get('channel') || '');
  const [projectGroup, setProjectGroup] = useState(searchParams.get('project') || '');
  const [ownerId, setOwnerId] = useState(searchParams.get('owner') || '');
  const [direction, setDirection] = useState('');
  const [date, setDate] = useState('');
  const [page, setPage] = useState(1);
  const [unmatchedOpen, setUnmatchedOpen] = useState(false);
  const [selected, setSelected] = useState<CommunicationFeedItem | null>(null);
  const [emailOpen, setEmailOpen] = useState<CommunicationFeedItem | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPerson(personDraft.trim());
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft, personDraft]);

  const listParams = useMemo(
    () => ({
      search: search || undefined,
      channel: channel || undefined,
      person: person || undefined,
      project_group: projectGroup || undefined,
      owner_id: ownerId || undefined,
      direction: direction || undefined,
      page,
      page_size: PAGE_SIZE,
      ...dateRange(date),
    }),
    [search, channel, person, projectGroup, ownerId, direction, date, page],
  );

  const feedQuery = useQuery({
    ...communicationQueries.feed(listParams),
    enabled: !authLoading && canViewCommunications,
  });
  const ownersQuery = useQuery({
    queryKey: ['users', 'communication-owners'],
    queryFn: () => fetchUsers({ status: 'active' }),
    enabled: !authLoading && canViewCommunications,
  });
  const conversationQuery = useQuery({
    ...communicationQueries.conversation({
      activity_id: selected?.activity_id || selected?.id || undefined,
      contact_id: selected?.contact_id || undefined,
      chat_id: selected?.conversation_key || undefined,
    }),
    enabled: Boolean(
      selected
      && selected.channel === 'whatsapp'
      && (selected.activity_id || selected.contact_id || selected.conversation_key),
    ),
  });

  const stats = feedQuery.data?.stats ?? { total: 0, email: 0, whatsapp: 0, unmatched: 0 };
  const items = feedQuery.data?.items ?? [];
  const pages = feedQuery.data?.pages ?? 1;

  const clearFilters = () => {
    setSearchDraft('');
    setSearch('');
    setPersonDraft('');
    setPerson('');
    setChannel('');
    setProjectGroup('');
    setOwnerId('');
    setDirection('');
    setDate('');
    setPage(1);
  };

  const openRow = (item: CommunicationFeedItem) => {
    if (item.channel === 'email') {
      setEmailOpen(item);
      setSelected(null);
      return;
    }
    setSelected(item);
  };

  if (authLoading || (feedQuery.isLoading && !unmatchedOpen)) {
    return (
      <div className="crm-tasks crm-tasks--ops crm-comm-live" data-testid="crm-communication-workspace">
        <div className="crm-tasks__skeleton" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <div key={index} className="crm-tasks__skeleton-row" />
          ))}
        </div>
      </div>
    );
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('title')} message={tCommon('retry')} />;
  }

  return (
    <div className="crm-tasks crm-tasks--ops crm-comm-live" data-testid="crm-communication-workspace">
      <header className="crm-tasks__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-comm-live__kpi-row" aria-label={t('kpis.aria')}>
        <article className="crm-comm-live__kpi">
          <span>{t('kpis.total')}</span>
          <strong data-testid="crm-comm-total">{stats.total.toLocaleString(locale)}</strong>
        </article>
        <article className="crm-comm-live__kpi">
          <span>{t('kpis.email')}</span>
          <strong data-testid="crm-comm-email">{stats.email.toLocaleString(locale)}</strong>
        </article>
        <article className="crm-comm-live__kpi">
          <span>{t('kpis.whatsapp')}</span>
          <strong data-testid="crm-comm-whatsapp">{stats.whatsapp.toLocaleString(locale)}</strong>
        </article>
        <button
          type="button"
          className={`crm-comm-live__kpi crm-comm-live__kpi--btn${unmatchedOpen ? ' is-active' : ''}`}
          onClick={() => setUnmatchedOpen(true)}
        >
          <span>{t('kpis.unmatched')}</span>
          <strong data-testid="crm-comm-unmatched">{stats.unmatched.toLocaleString(locale)}</strong>
        </button>
      </section>

      <section className="crm-tasks__filters" aria-label={t('filters.aria')}>
        <div className="crm-tasks__search">
          <Input
            label={t('filters.search')}
            value={searchDraft}
            onChange={(event) => setSearchDraft(event.target.value)}
            placeholder={t('filters.searchPlaceholder')}
          />
        </div>
        <Select label={t('filters.channel')} value={channel} onChange={(event) => { setChannel(event.target.value); setPage(1); }}>
          <option value="">{t('filters.anyChannel')}</option>
          <option value="email">{t('channels.email')}</option>
          <option value="whatsapp">{t('channels.whatsapp')}</option>
          <option value="call">{t('channels.call')}</option>
          <option value="comment">{t('channels.comment')}</option>
          <option value="meeting">{t('channels.meeting')}</option>
        </Select>
        <Input
          label={t('filters.person')}
          value={personDraft}
          onChange={(event) => setPersonDraft(event.target.value)}
          placeholder={t('filters.personPlaceholder')}
        />
        <Select label={t('filters.project')} value={projectGroup} onChange={(event) => { setProjectGroup(event.target.value); setPage(1); }}>
          <option value="">{t('filters.anyProject')}</option>
          {PROJECTS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
        <Select label={t('filters.owner')} value={ownerId} onChange={(event) => { setOwnerId(event.target.value); setPage(1); }}>
          <option value="">{t('filters.anyOwner')}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {user.full_name}
            </option>
          ))}
        </Select>
        <Select label={t('filters.direction')} value={direction} onChange={(event) => { setDirection(event.target.value); setPage(1); }}>
          <option value="">{t('filters.anyDirection')}</option>
          <option value="inbound">{t('filters.inbound')}</option>
          <option value="outbound">{t('filters.outbound')}</option>
        </Select>
        <Select label={t('filters.date')} value={date} onChange={(event) => { setDate(event.target.value); setPage(1); }}>
          <option value="">{t('filters.anyDate')}</option>
          <option value="today">{t('filters.today')}</option>
          <option value="7d">{t('filters.d7')}</option>
          <option value="30d">{t('filters.d30')}</option>
          <option value="90d">{t('filters.d90')}</option>
        </Select>
        <div className="crm-tasks__filter-actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters}>
            {t('filters.clear')}
          </Button>
          <Button
            type="button"
            size="sm"
            variant={unmatchedOpen ? 'primary' : 'secondary'}
            onClick={() => setUnmatchedOpen((value) => !value)}
            data-testid="crm-comm-unmatched-tab"
          >
            {t('unmatchedTab')}
          </Button>
        </div>
      </section>

      {unmatchedOpen ? (
        <UnmatchedCommunicationsView />
      ) : feedQuery.isError ? (
        <ErrorState title={t('title')} message={feedQuery.error.message} />
      ) : items.length === 0 ? (
        <div className="crm-tasks__empty">{t('empty')}</div>
      ) : (
        <div className="crm-tasks__table-wrap" role="region" aria-label={t('tableAria')}>
          <table className="crm-tasks__table crm-tasks__table--ops">
            <thead>
              <tr>
                <th>{t('columns.when')}</th>
                <th>{t('columns.channel')}</th>
                <th>{t('columns.person')}</th>
                <th>{t('columns.subject')}</th>
                <th>{t('columns.project')}</th>
                <th>{t('columns.direction')}</th>
                <th>{t('columns.owner')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr
                  key={item.source_key}
                  className={`crm-tasks__row${selected?.id === item.id ? ' is-selected' : ''}`}
                  onClick={() => openRow(item)}
                  data-testid={`comm-row-${item.id}`}
                >
                  <td>{formatWhen(item.occurred_at, locale)}</td>
                  <td>
                    <StatusChip tone={channelTone(item.channel)}>
                      {t(channelLabelKey(item.channel))}
                    </StatusChip>
                  </td>
                  <td>
                    {item.contact_id ? (
                      <button
                        type="button"
                        className="crm-tasks__link-btn"
                        onClick={(event) => {
                          event.stopPropagation();
                          openContact(item.contact_id!);
                        }}
                      >
                        {item.contact_name || t('openPerson')}
                      </button>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    <strong>{item.subject || '—'}</strong>
                    {rowPreview(item) ? <div className="crm-comm-live__hint">{rowPreview(item)}</div> : null}
                  </td>
                  <td>
                    {item.agreement_id && item.contact_id ? (
                      <a
                        href={salesDetailUrl(item.contact_id, item.agreement_id)}
                        className="crm-tasks__link-btn"
                        onClick={(event) => event.stopPropagation()}
                      >
                        {item.project_unit || t('openPurchase')}
                      </a>
                    ) : (
                      item.project_unit || '—'
                    )}
                  </td>
                  <td>{item.direction === 'outbound' ? t('filters.outbound') : t('filters.inbound')}</td>
                  <td>{item.owner_name || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!unmatchedOpen ? (
        <div className="crm-tasks__pagination">
          <Button type="button" variant="secondary" size="sm" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
            {t('previous')}
          </Button>
          <span>
            {page} / {pages}
          </span>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((value) => value + 1)}
          >
            {t('next')}
          </Button>
        </div>
      ) : null}

      {selected ? (
        <>
          <button type="button" className="crm-tasks__drawer-backdrop" aria-label={tCommon('close')} onClick={() => setSelected(null)} />
          <aside className="crm-tasks__drawer" role="dialog" aria-label={t('drawerTitle')} data-testid="crm-comm-drawer">
            <div className="crm-tasks__drawer-head">
              <h3>{selected.channel === 'whatsapp' ? t('conversationTitle') : t('drawerTitle')}</h3>
              <button type="button" className="crm-tasks__link-btn" onClick={() => setSelected(null)}>
                {tCommon('close')}
              </button>
            </div>
            <div className="crm-tasks__drawer-body">
              <dl className="crm-tasks__kv">
                <dt>{t('columns.channel')}</dt>
                <dd>{t(channelLabelKey(selected.channel))}</dd>
                <dt>{t('columns.when')}</dt>
                <dd>{formatWhen(selected.occurred_at, locale)}</dd>
                <dt>{t('columns.person')}</dt>
                <dd>{selected.contact_name || '—'}</dd>
                <dt>{t('columns.project')}</dt>
                <dd>{selected.project_unit || '—'}</dd>
              </dl>
              <div className="crm-tasks__drawer-actions">
                {selected.contact_id ? (
                  <Button type="button" size="sm" onClick={() => openContact(selected.contact_id!)}>
                    {t('openPerson')}
                  </Button>
                ) : null}
                {selected.agreement_id && selected.contact_id ? (
                  <a className="crm-tasks__link-btn" href={salesDetailUrl(selected.contact_id, selected.agreement_id)}>
                    {t('openPurchase')}
                  </a>
                ) : null}
              </div>
              {selected.channel === 'whatsapp' ? (
                conversationQuery.data?.messages?.length ? (
                  <WhatsAppThread
                    messages={conversationQuery.data.messages.map((message) => ({
                      id: message.id,
                      activity_type: message.activity_type,
                      title: message.title,
                      summary: message.summary,
                      actor_name: message.actor_name,
                      created_at: message.created_at,
                      metadata: message.metadata,
                    }))}
                    locale={locale}
                  />
                ) : (
                  <p>{selected.preview}</p>
                )
              ) : (
                <p className="crm-comm-live__body">{selected.preview}</p>
              )}
            </div>
          </aside>
        </>
      ) : null}

      {emailOpen ? (
        <EmailDetail
          entry={{
            id: emailOpen.activity_id || emailOpen.id,
            title: emailOpen.subject || '',
            summary: emailOpen.preview,
            actor_name: emailOpen.owner_name,
            created_at: emailOpen.occurred_at || new Date().toISOString(),
          }}
          locale={locale}
          onClose={() => setEmailOpen(null)}
        />
      ) : null}
    </div>
  );
}
