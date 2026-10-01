'use client';

import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';

import { Button, ErrorState, Input, Select } from '@investhome/ui';

import { IhIcon, type IhIconName } from '@/components/icons/ih-icons';
import { fetchUsers } from '@/lib/api/auth';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { fetchActivity } from '@/workspaces/crm/api/activities';
import type { CommunicationFeedItem } from '@/workspaces/crm/api/communication';
import { EmailDetail } from '@/workspaces/crm/contact-card/crm-email-view';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  emailPreviewText,
  looksLikePayloadDump,
  parseEmailContent,
  stripHtml,
} from '@/workspaces/crm/contact-card/history-html';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';
import { WhatsAppThread } from '@/workspaces/crm/contact-card/whatsapp-thread';
import { communicationQueries } from '@/workspaces/crm/hooks/use-communication';

import '../../contacts/_components/ds/contacts-ds.css';
import { UnmatchedCommunicationsView } from './unmatched-communications-view';

const PROJECTS = [
  { value: '1307_k_st', label: '1307 K St' },
  { value: '1313_penn', label: '1313 Penn' },
  { value: '1812_h_pl', label: '1812 H Pl' },
  { value: '2319_ontario', label: '2319 Ontario' },
  { value: 'reit', label: 'REIT' },
  { value: 'the_temple', label: 'The Temple' },
  { value: 'uniloft', label: 'Uniloft' },
] as const;

type ChannelKey = 'email' | 'whatsapp' | 'call' | 'comment' | 'meeting' | 'sms' | 'other';
type SortKey = 'when' | 'channel' | 'person' | 'subject' | 'project' | 'direction' | 'owner';

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
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function channelKey(channel: string): ChannelKey {
  if (channel === 'whatsapp') return 'whatsapp';
  if (channel === 'call' || channel === 'phone') return 'call';
  if (channel === 'comment' || channel === 'note') return 'comment';
  if (channel === 'meeting') return 'meeting';
  if (channel === 'sms') return 'sms';
  if (channel === 'email') return 'email';
  return 'other';
}

function displayOwner(name: string | null | undefined): string {
  return String(name || '')
    .replace(/\s*\((?:Demo|demo)\)\s*$/g, '')
    .trim();
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '•';
  const first = parts[0][0] || '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] || '' : '';
  return `${first}${last}`.toLocaleUpperCase('tr-TR');
}

function readableText(value: string | null | undefined): string {
  const text = stripHtml(value);
  if (!text || looksLikePayloadDump(text)) return '';
  return text;
}

function rowCopy(item: CommunicationFeedItem): { subject: string; preview: string } {
  if (item.channel === 'email') {
    const parsed = parseEmailContent(item.subject || '', item.preview);
    const subject = parsed.subject || readableText(item.subject) || '—';
    const preview = parsed.preview && parsed.preview !== subject ? parsed.preview : '';
    return { subject, preview };
  }
  const subject = readableText(item.subject) || '—';
  const preview = emailPreviewText(item.preview, 180);
  return { subject, preview: preview && preview !== subject ? preview : '' };
}

function projectDisplay(item: CommunicationFeedItem): { title: string; subtitle: string | null } {
  const title = item.project_unit || [item.project_label, item.unit_number].filter(Boolean).join(' · ');
  if (!title) return { title: '', subtitle: null };
  const subtitle = item.project_label && !title.includes(item.project_label) ? item.project_label : null;
  return { title, subtitle };
}

function isActivityId(id: string | null | undefined): id is string {
  return Boolean(id && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id));
}

function visiblePages(page: number, pages: number): Array<number | 'ellipsis'> {
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const wanted = new Set([1, pages, page - 1, page, page + 1]);
  const nums = [...wanted].filter((value) => value >= 1 && value <= pages).sort((a, b) => a - b);
  const next: Array<number | 'ellipsis'> = [];
  for (const value of nums) {
    const last = next[next.length - 1];
    if (typeof last === 'number' && value - last > 1) next.push('ellipsis');
    next.push(value);
  }
  return next;
}

function ChannelIcon({ channel }: { channel: ChannelKey }) {
  if (channel === 'whatsapp') {
    return (
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M20.5 12a8.5 8.5 0 0 1-12.7 7.4L4 20l.7-3.7A8.5 8.5 0 1 1 20.5 12Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path d="M9.2 9.6c.2-.5.4-.5.7-.5h.6c.2 0 .4.1.5.4l.5 1.2c.1.2 0 .5-.2.6l-.5.4c.5.9 1.3 1.7 2.2 2.2l.4-.5c.2-.2.4-.3.6-.2l1.2.5c.3.1.4.3.4.5v.6c0 .3 0 .5-.5.7A5.2 5.2 0 0 1 9.2 9.6Z" fill="currentColor" />
      </svg>
    );
  }
  const name: IhIconName = channel === 'email' ? 'mail' : channel === 'call' ? 'phone' : channel === 'meeting' ? 'meeting' : channel === 'comment' ? 'activity' : 'inbox';
  return <IhIcon name={name} size={13} />;
}

function sortValue(item: CommunicationFeedItem, key: SortKey): string {
  if (key === 'when') return item.occurred_at || '';
  if (key === 'channel') return channelKey(item.channel);
  if (key === 'person') return item.contact_name || '';
  if (key === 'subject') return rowCopy(item).subject;
  if (key === 'project') return projectDisplay(item).title;
  if (key === 'direction') return item.direction || '';
  return displayOwner(item.owner_name);
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
  const [pageSize, setPageSize] = useState(10);
  const [sortKey, setSortKey] = useState<SortKey>('when');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [unmatchedOpen, setUnmatchedOpen] = useState(false);
  const [selected, setSelected] = useState<CommunicationFeedItem | null>(null);
  const [emailOpen, setEmailOpen] = useState<CommunicationFeedItem | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchDraft.trim());
      setPerson(personDraft.trim());
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft, personDraft]);

  useEffect(() => {
    const close = () => setMenuId(null);
    window.addEventListener('click', close);
    return () => window.removeEventListener('click', close);
  }, []);

  const listParams = useMemo(
    () => ({
      search: search || undefined,
      channel: channel || undefined,
      person: person || undefined,
      project_group: projectGroup || undefined,
      owner_id: ownerId || undefined,
      direction: direction || undefined,
      page,
      page_size: pageSize,
      ...dateRange(date),
    }),
    [search, channel, person, projectGroup, ownerId, direction, date, page, pageSize],
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
  const detailQuery = useQuery({
    queryKey: ['crm', 'activities', selected?.activity_id],
    queryFn: () => fetchActivity(selected!.activity_id!),
    enabled: Boolean(
      selected
      && selected.channel !== 'whatsapp'
      && selected.channel !== 'email'
      && isActivityId(selected.activity_id),
    ),
  });

  const stats = feedQuery.data?.stats ?? { total: 0, email: 0, whatsapp: 0, unmatched: 0 };
  const total = feedQuery.data?.total ?? 0;
  const pages = feedQuery.data?.pages ?? 1;
  const from = total ? (page - 1) * pageSize + 1 : 0;
  const to = Math.min(page * pageSize, total);
  const items = useMemo(() => {
    const rows = [...(feedQuery.data?.items ?? [])];
    const directionFactor = sortDir === 'asc' ? 1 : -1;
    rows.sort((left, right) => {
      const a = sortValue(left, sortKey);
      const b = sortValue(right, sortKey);
      if (sortKey === 'when') return (a.localeCompare(b) || left.id.localeCompare(right.id)) * directionFactor;
      return (a.localeCompare(b, locale === 'tr' ? 'tr' : 'en', { sensitivity: 'base' }) || left.id.localeCompare(right.id)) * directionFactor;
    });
    return rows;
  }, [feedQuery.data?.items, sortDir, sortKey, locale]);

  const hasFilters = Boolean(searchDraft || personDraft || channel || projectGroup || ownerId || direction || date);

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

  const selectKpi = (nextChannel: string) => {
    setUnmatchedOpen(false);
    setChannel(nextChannel);
    setPage(1);
  };

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((value) => (value === 'asc' ? 'desc' : 'asc'));
      return;
    }
    setSortKey(key);
    setSortDir(key === 'when' ? 'desc' : 'asc');
  };

  const openRow = (item: CommunicationFeedItem) => {
    setMenuId(null);
    if (item.channel === 'email') {
      setEmailOpen(item);
      setSelected(null);
      return;
    }
    setEmailOpen(null);
    setSelected(item);
  };

  const drawerBody = selected
    ? readableText(detailQuery.data?.description || detailQuery.data?.summary || selected.preview)
    : '';

  const shell = (content: ReactNode) => (
    <div className="ctc-ds crm-comm" data-testid="crm-communication-workspace">
      {content}
    </div>
  );

  if (authLoading || (feedQuery.isLoading && !unmatchedOpen)) {
    return shell(
      <div className="crm-comm-skeleton" aria-hidden="true">
        {Array.from({ length: 6 }).map((_, index) => (
          <div key={index} />
        ))}
      </div>,
    );
  }

  if (!canViewCommunications) {
    return <ErrorState title={t('title')} message={tCommon('retry')} />;
  }

  const dateSelect = (id: string) => (
    <Select
      id={id}
      label={t('filters.date')}
      value={date}
      onChange={(event) => {
        setDate(event.target.value);
        setPage(1);
      }}
    >
      <option value="">{t('filters.anyDate')}</option>
      <option value="today">{t('filters.today')}</option>
      <option value="7d">{t('filters.d7')}</option>
      <option value="30d">{t('filters.d30')}</option>
      <option value="90d">{t('filters.d90')}</option>
    </Select>
  );

  return shell(
    <>
      <header className="crm-comm__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-comm__header-tools">{dateSelect('crm-comm-header-date')}</div>
      </header>

      <section className="crm-comm-kpis" aria-label={t('kpis.aria')}>
        {(
          [
            { id: 'total', value: stats.total, label: t('kpis.total'), icon: 'inbox' as const, testId: 'crm-comm-total', active: !unmatchedOpen && !channel, warn: false, onClick: () => selectKpi('') },
            { id: 'email', value: stats.email, label: t('kpis.email'), icon: 'mail' as const, testId: 'crm-comm-email', active: !unmatchedOpen && channel === 'email', warn: false, onClick: () => selectKpi('email') },
            { id: 'whatsapp', value: stats.whatsapp, label: t('kpis.whatsapp'), icon: 'inbox' as const, testId: 'crm-comm-whatsapp', active: !unmatchedOpen && channel === 'whatsapp', warn: false, onClick: () => selectKpi('whatsapp') },
            { id: 'unmatched', value: stats.unmatched, label: t('kpis.unmatched'), icon: 'alert' as const, testId: 'crm-comm-unmatched', active: unmatchedOpen, warn: true, onClick: () => setUnmatchedOpen(true) },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            className={`${item.active ? 'is-active' : ''}${item.warn ? ' is-warn' : ''}`}
            onClick={item.onClick}
          >
            <span className="crm-comm-kpis__icon" aria-hidden>
              {item.id === 'whatsapp' ? <ChannelIcon channel="whatsapp" /> : <IhIcon name={item.icon} size={16} />}
            </span>
            <strong data-testid={item.testId}>{item.value.toLocaleString(locale)}</strong>
            <span>{item.label}</span>
          </button>
        ))}
      </section>

      <section className="crm-comm-filtercard" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Select
          label={t('filters.channel')}
          value={channel}
          onChange={(event) => {
            setChannel(event.target.value);
            setUnmatchedOpen(false);
            setPage(1);
          }}
        >
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
        <Select
          label={t('filters.project')}
          value={projectGroup}
          onChange={(event) => {
            setProjectGroup(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anyProject')}</option>
          {PROJECTS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={ownerId}
          onChange={(event) => {
            setOwnerId(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anyOwner')}</option>
          {(ownersQuery.data?.items ?? []).map((user) => (
            <option key={user.id} value={user.id}>
              {displayOwner(user.full_name) || user.full_name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.direction')}
          value={direction}
          onChange={(event) => {
            setDirection(event.target.value);
            setPage(1);
          }}
        >
          <option value="">{t('filters.anyDirection')}</option>
          <option value="inbound">{t('filters.inbound')}</option>
          <option value="outbound">{t('filters.outbound')}</option>
        </Select>
        {dateSelect('crm-comm-filter-date')}
        <div className="crm-comm-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={clearFilters} disabled={!hasFilters}>
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
        <section className="crm-comm-tablecard" aria-label={t('unmatchedTab')}>
          <UnmatchedCommunicationsView />
        </section>
      ) : feedQuery.isError ? (
        <ErrorState title={t('title')} message={feedQuery.error.message} />
      ) : items.length === 0 ? (
        <div className="crm-comm-empty">{t('empty')}</div>
      ) : (
        <section className="crm-comm-tablecard" aria-label={t('tableAria')}>
          <div className="crm-comm-table-wrap">
            <table className="crm-comm-table">
              <thead>
                <tr>
                  {(
                    [
                      ['when', 'is-when'],
                      ['channel', 'is-channel'],
                      ['person', 'is-person'],
                      ['subject', 'is-subject'],
                      ['project', 'is-project'],
                      ['direction', 'is-direction'],
                      ['owner', 'is-owner'],
                    ] as const
                  ).map(([key, className]) => (
                    <th key={key} className={className}>
                      <button type="button" className="crm-comm-link" onClick={() => toggleSort(key)}>
                        {t(`columns.${key}`)}
                        {sortKey === key ? (sortDir === 'asc' ? ' ↑' : ' ↓') : ''}
                      </button>
                    </th>
                  ))}
                  <th className="is-actions">{t('columns.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const kind = channelKey(item.channel);
                  const copy = rowCopy(item);
                  const project = projectDisplay(item);
                  const owner = displayOwner(item.owner_name);
                  const inbound = item.direction !== 'outbound';
                  const rowKey = item.source_key || item.id;
                  return (
                    <tr
                      key={rowKey}
                      className={`crm-comm-row${selected?.id === item.id ? ' is-selected' : ''}`}
                      onClick={() => openRow(item)}
                      data-testid={`comm-row-${item.id}`}
                    >
                      <td className="is-when">
                        <span className="crm-comm-when">{formatWhen(item.occurred_at, locale)}</span>
                      </td>
                      <td className="is-channel">
                        <span className={`crm-comm-channel is-${kind}`}>
                          <ChannelIcon channel={kind} />
                          {t(`channels.${kind}`)}
                        </span>
                      </td>
                      <td className="is-person">
                        {item.contact_id ? (
                          <div className="crm-comm-person">
                            <span className="crm-comm-avatar" aria-hidden>
                              {initials(item.contact_name || t('openPerson'))}
                            </span>
                            <button
                              type="button"
                              className="crm-comm-link"
                              title={item.contact_name || undefined}
                              onClick={(event) => {
                                event.stopPropagation();
                                openContact(item.contact_id!);
                              }}
                            >
                              {item.contact_name || t('openPerson')}
                            </button>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="is-subject">
                        <div className="crm-comm-subject" title={[copy.subject, copy.preview].filter(Boolean).join('\n')}>
                          <strong>{copy.subject}</strong>
                          {copy.preview ? <small>{copy.preview}</small> : null}
                        </div>
                      </td>
                      <td className="is-project">
                        {project.title ? (
                          <div className="crm-comm-project" title={[project.title, project.subtitle].filter(Boolean).join(' · ')}>
                            {item.agreement_id && item.contact_id ? (
                              <a
                                href={salesDetailUrl(item.contact_id, item.agreement_id)}
                                className="crm-comm-link"
                                onClick={(event) => event.stopPropagation()}
                              >
                                <strong>{project.title}</strong>
                                {project.subtitle ? <span>{project.subtitle}</span> : null}
                              </a>
                            ) : (
                              <>
                                <strong>{project.title}</strong>
                                {project.subtitle ? <span>{project.subtitle}</span> : null}
                              </>
                            )}
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="is-direction">
                        <span className={`crm-comm-dir ${inbound ? 'is-inbound' : 'is-outbound'}`}>
                          {inbound ? '↓' : '↑'} {inbound ? t('filters.inbound') : t('filters.outbound')}
                        </span>
                      </td>
                      <td className="is-owner">
                        {owner ? (
                          <div className="crm-comm-owner" title={owner}>
                            <span className="crm-comm-avatar" aria-hidden>
                              {initials(owner)}
                            </span>
                            <span>{owner}</span>
                          </div>
                        ) : (
                          '—'
                        )}
                      </td>
                      <td className="is-actions">
                        <div className="crm-comm-actions">
                          <button
                            type="button"
                            className="crm-comm-action"
                            onClick={(event) => {
                              event.stopPropagation();
                              openRow(item);
                            }}
                          >
                            {t('open')}
                          </button>
                          {item.contact_id || (item.agreement_id && item.contact_id) ? (
                            <div className="crm-comm-more">
                              <button
                                type="button"
                                className="crm-comm-action is-more"
                                aria-label={t('more')}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  setMenuId((current) => (current === rowKey ? null : rowKey));
                                }}
                              >
                                …
                              </button>
                              {menuId === rowKey ? (
                                <div className="crm-comm-more__panel">
                                  {item.contact_id ? (
                                    <button
                                      type="button"
                                      onClick={(event) => {
                                        event.stopPropagation();
                                        setMenuId(null);
                                        openContact(item.contact_id!);
                                      }}
                                    >
                                      {t('openPerson')}
                                    </button>
                                  ) : null}
                                  {item.agreement_id && item.contact_id ? (
                                    <a
                                      href={salesDetailUrl(item.contact_id, item.agreement_id)}
                                      onClick={(event) => event.stopPropagation()}
                                    >
                                      {t('openPurchase')}
                                    </a>
                                  ) : null}
                                </div>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <footer className="crm-comm-pager">
            <p>{t('pager', { total, from, to })}</p>
            <div>
              <button type="button" disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>
                ‹
              </button>
              {visiblePages(page, pages).map((item, index) =>
                item === 'ellipsis' ? (
                  <span key={`e${index}`}>…</span>
                ) : (
                  <button
                    key={item}
                    type="button"
                    className={item === page ? 'is-active' : undefined}
                    onClick={() => setPage(item)}
                  >
                    {item}
                  </button>
                ),
              )}
              <button type="button" disabled={page >= pages} onClick={() => setPage((value) => Math.min(pages, value + 1))}>
                ›
              </button>
            </div>
            <label>
              {t('pageSize')}
              <select
                value={pageSize}
                onChange={(event) => {
                  setPageSize(Number(event.target.value));
                  setPage(1);
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
              </select>
            </label>
          </footer>
        </section>
      )}

      {selected ? (
        <>
          <button type="button" className="crm-comm-drawer-backdrop" aria-label={tCommon('close')} onClick={() => setSelected(null)} />
          <aside
            className={`crm-comm-drawer${selected.channel === 'whatsapp' ? ' is-wide' : ''}`}
            role="dialog"
            aria-label={t('drawerTitle')}
            data-testid="crm-comm-drawer"
          >
            <div className="crm-comm-drawer__head">
              <h3>
                {selected.channel === 'whatsapp'
                  ? t('conversationTitle')
                  : selected.channel === 'meeting'
                    ? t('meetingTitle')
                    : selected.channel === 'comment' || selected.channel === 'note'
                      ? t('commentTitle')
                      : t('drawerTitle')}
              </h3>
              <button type="button" className="crm-comm-link" onClick={() => setSelected(null)}>
                {tCommon('close')}
              </button>
            </div>
            <div className="crm-comm-drawer__body">
              <dl className="crm-comm-kv">
                <dt>{t('columns.channel')}</dt>
                <dd>{t(`channels.${channelKey(selected.channel)}`)}</dd>
                <dt>{t('columns.when')}</dt>
                <dd>{formatWhen(selected.occurred_at, locale)}</dd>
                <dt>{t('columns.person')}</dt>
                <dd>{selected.contact_name || '—'}</dd>
                <dt>{t('columns.project')}</dt>
                <dd>{projectDisplay(selected).title || '—'}</dd>
                <dt>{t('columns.direction')}</dt>
                <dd>{selected.direction === 'outbound' ? t('filters.outbound') : t('filters.inbound')}</dd>
                <dt>{t('columns.owner')}</dt>
                <dd>{displayOwner(selected.owner_name) || '—'}</dd>
              </dl>
              <div className="crm-comm-drawer__actions">
                {selected.contact_id ? (
                  <Button type="button" size="sm" onClick={() => openContact(selected.contact_id!)}>
                    {t('openPerson')}
                  </Button>
                ) : null}
                {selected.agreement_id && selected.contact_id ? (
                  <a className="crm-comm-link" href={salesDetailUrl(selected.contact_id, selected.agreement_id)}>
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
                  <div className="crm-comm-note">{drawerBody || rowCopy(selected).preview || rowCopy(selected).subject}</div>
                )
              ) : (
                <div className="crm-comm-note">{drawerBody || rowCopy(selected).preview || rowCopy(selected).subject}</div>
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
    </>,
  );
}
