'use client';

import type { Route } from 'next';
import { Suspense, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import {
  Button,
  Input,
  KpiCard,
  SegmentedControl,
  Select,
  StatusChip,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  aiScoreBand,
  CONTACT_QUICK_FILTERS,
  CONTACT_ROLE_ORDER,
  CONTACT_STATUS_ORDER,
  CONTACTS_KPI_ICONS,
  deriveContactsKpis,
  EMPTY_CONTACTS_FILTERS,
  filterContacts,
  formatDisplayDate,
  makeContactsFixture,
  statusTone,
  type ContactPriorityKey,
  type ContactQuickFilter,
  type ContactRoleKey,
  type ContactRow,
  type ContactsDsFilters,
  type ContactsViewMode,
  type ContactStatusKey,
  type ContactSortKey,
} from './contacts-ds-model';

import './contacts-ds.css';

const PAGE_SIZE = 10;

function ContactAvatar({
  initials,
  tone,
  size = 'sm',
}: {
  initials: string;
  tone: ContactRow['avatarTone'];
  size?: 'sm' | 'lg';
}) {
  return (
    <span
      className={`ctc-ds__avatar is-${tone}${size === 'lg' ? ' is-lg' : ''}`}
      aria-hidden="true"
    >
      {initials}
    </span>
  );
}

function AiScoreBadge({ score, tooltip }: { score: number; tooltip: string }) {
  const band = aiScoreBand(score);
  return (
    <span className={`ctc-ds__score is-${band}`} title={tooltip}>
      {score}
    </span>
  );
}

function PriorityDot({
  priority,
  label,
}: {
  priority: ContactPriorityKey;
  label: string;
}) {
  return (
    <span
      className={`ctc-ds__prio is-${priority}`}
      title={label}
      aria-label={label}
    />
  );
}

function RowActions({
  contact,
  onOpen,
  onCall,
  onEmail,
  onWhatsApp,
  onTask,
}: {
  contact: ContactRow;
  onOpen: () => void;
  onCall: () => void;
  onEmail: () => void;
  onWhatsApp: () => void;
  onTask: () => void;
}) {
  const t = useTranslations('crm.contacts.ds');

  return (
    <div className="ctc-ds__actions" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        className="ctc-ds__icon-btn"
        aria-label={t('actions.call')}
        title={t('actions.call')}
        onClick={onCall}
        disabled={!contact.phone}
      >
        <IhIcon name="meeting" size={13} />
      </button>
      <button
        type="button"
        className="ctc-ds__icon-btn"
        aria-label={t('actions.email')}
        title={t('actions.email')}
        onClick={onEmail}
        disabled={!contact.email}
      >
        <IhIcon name="inbox" size={13} />
      </button>
      <button
        type="button"
        className="ctc-ds__icon-btn"
        aria-label={t('actions.whatsapp')}
        title={t('actions.whatsapp')}
        onClick={onWhatsApp}
        disabled={!contact.phone}
      >
        <IhIcon name="check" size={13} />
      </button>
      <button
        type="button"
        className="ctc-ds__icon-btn"
        aria-label={t('actions.createTask')}
        title={t('actions.createTask')}
        onClick={onTask}
      >
        <IhIcon name="plus" size={13} />
      </button>
      <button
        type="button"
        className="ctc-ds__icon-btn"
        aria-label={t('actions.openDetail')}
        title={t('actions.openDetail')}
        onClick={onOpen}
      >
        <IhIcon name="arrowRight" size={13} />
      </button>
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="ctc-ds__skeleton" aria-hidden="true">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="ctc-ds__skeleton-row" />
      ))}
    </div>
  );
}

function ContactsDsWorkspaceInner() {
  const t = useTranslations('crm.contacts.ds');
  const locale = useLocale();
  const router = useRouter();

  const [contacts] = useState<ContactRow[]>(() => makeContactsFixture());
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<ContactsDsFilters>(EMPTY_CONTACTS_FILTERS);
  const [searchDraft, setSearchDraft] = useState('');
  const [view, setView] = useState<ContactsViewMode>('table');
  const [page, setPage] = useState(1);
  const [forceEmpty, setForceEmpty] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setLoading(false), 420);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setFilters((prev) => ({ ...prev, search: searchDraft }));
      setPage(1);
    }, 220);
    return () => window.clearTimeout(timer);
  }, [searchDraft]);

  const owners = useMemo(() => {
    const set = new Set<string>();
    for (const row of contacts) set.add(row.owner);
    return [...set].sort((a, b) => a.localeCompare(b));
  }, [contacts]);

  const filtered = useMemo(
    () => (forceEmpty ? [] : filterContacts(contacts, filters)),
    [contacts, filters, forceEmpty],
  );

  const kpis = useMemo(() => deriveContactsKpis(contacts), [contacts]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageSafe = Math.min(page, pages);
  const pageItems = filtered.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE);

  const openContact = (contact: ContactRow) => {
    router.push(`/workspaces/crm/contacts/${contact.id}` as Route);
  };

  const goImport = () => {
    router.push('/workspaces/crm/contacts/import' as Route);
  };

  const goNew = () => {
    router.push('/workspaces/crm/contacts/new' as Route);
  };

  const handleExport = () => {
    const header = [
      'full_name',
      'company',
      'role',
      'status',
      'source',
      'last_activity',
      'next_follow_up',
      'owner',
      'priority',
      'ai_score',
    ].join(',');
    const rows = filtered.map((c) =>
      [
        JSON.stringify(c.fullName),
        JSON.stringify(c.company),
        c.role,
        c.status,
        c.source,
        c.lastActivity,
        c.nextFollowUp ?? '',
        JSON.stringify(c.owner),
        c.priority,
        c.aiScore,
      ].join(','),
    );
    const blob = new Blob([[header, ...rows].join('\n')], {
      type: 'text/csv;charset=utf-8',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'crm-contacts-export.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const patchFilters = (patch: Partial<ContactsDsFilters>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(1);
    setForceEmpty(false);
  };

  const emptyState = (
    <div className="ctc-ds__empty" data-testid="contacts-ds-empty">
      <strong>{t('empty.title')}</strong>
      <p>{t('empty.description')}</p>
      <div className="ctc-ds__empty-actions">
        <Button variant="secondary" size="sm" onClick={goImport}>
          <IhIcon name="inbox" size={13} />
          {t('empty.import')}
        </Button>
        <Button variant="primary" size="sm" onClick={goNew}>
          <IhIcon name="plus" size={13} />
          {t('empty.add')}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="ctc-ds" data-testid="contacts-ds-workspace">
      <header className="ctc-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="ctc-ds__header-actions">
          <div className="ctc-ds__header-search">
            <Input
              label={t('filters.search')}
              value={searchDraft}
              onChange={(e) => setSearchDraft(e.target.value)}
              placeholder={t('filters.searchPlaceholder')}
              data-testid="contacts-ds-header-search"
            />
          </div>
          <Button variant="secondary" size="sm" onClick={goImport}>
            <IhIcon name="inbox" size={13} />
            {t('actions.import')}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleExport}>
            <IhIcon name="documents" size={13} />
            {t('actions.export')}
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={goNew}
            data-testid="contacts-ds-add"
          >
            <IhIcon name="plus" size={13} />
            {t('actions.add')}
          </Button>
        </div>
      </header>

      <section className="ctc-ds__kpi-row" aria-label={t('kpis.aria')}>
        {kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="ctc-ds__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={loading ? '—' : kpi.value}
            hint={t(`kpis.hints.${kpi.key}`)}
            delta={kpi.delta ? `${kpi.delta} ${t('kpis.vsLastMonth')}` : undefined}
            {...(kpi.deltaTone ? { deltaTone: kpi.deltaTone } : {})}
            icon={<IhIcon name={CONTACTS_KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <section className="ctc-ds__toolbar" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={searchDraft}
          onChange={(e) => setSearchDraft(e.target.value)}
          placeholder={t('filters.searchPlaceholder')}
          data-testid="contacts-ds-search"
        />
        <Select
          label={t('filters.role')}
          value={filters.role}
          onChange={(e) =>
            patchFilters({ role: e.target.value as ContactRoleKey | '' })
          }
        >
          <option value="">{t('filters.any')}</option>
          {CONTACT_ROLE_ORDER.map((role) => (
            <option key={role} value={role}>
              {t(`roles.${role}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) =>
            patchFilters({ status: e.target.value as ContactStatusKey | '' })
          }
        >
          <option value="">{t('filters.any')}</option>
          {CONTACT_STATUS_ORDER.map((status) => (
            <option key={status} value={status}>
              {t(`statuses.${status}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={filters.owner}
          onChange={(e) => patchFilters({ owner: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {owners.map((owner) => (
            <option key={owner} value={owner}>
              {owner}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.sort')}
          value={filters.sort}
          onChange={(e) =>
            patchFilters({ sort: e.target.value as ContactSortKey })
          }
        >
          <option value="activity_desc">{t('sort.activity_desc')}</option>
          <option value="name_asc">{t('sort.name_asc')}</option>
          <option value="name_desc">{t('sort.name_desc')}</option>
          <option value="followup_asc">{t('sort.followup_asc')}</option>
          <option value="score_desc">{t('sort.score_desc')}</option>
          <option value="priority_desc">{t('sort.priority_desc')}</option>
        </Select>
        <div className="ctc-ds__view-toggle">
          <SegmentedControl
            ariaLabel={t('view.aria')}
            value={view}
            onChange={(next) => setView(next as ContactsViewMode)}
            options={[
              { value: 'table', label: t('view.table') },
              { value: 'cards', label: t('view.cards') },
            ]}
          />
        </div>
      </section>

      <section className="ctc-ds__quick" aria-label={t('quick.aria')}>
        <SegmentedControl
          ariaLabel={t('quick.aria')}
          value={filters.quick}
          onChange={(next) =>
            patchFilters({ quick: next as ContactQuickFilter })
          }
          options={CONTACT_QUICK_FILTERS.map((key) => ({
            value: key,
            label: t(`quick.${key}`),
          }))}
        />
      </section>

      {loading ? (
        <section className="ctc-ds__table-section" aria-label={t('loading')}>
          <TableSkeleton />
        </section>
      ) : null}

      {!loading && view === 'cards' ? (
        <section className="ctc-ds__grid" aria-label={t('grid.aria')}>
          {pageItems.length === 0
            ? emptyState
            : pageItems.map((contact) => (
                <article
                  key={contact.id}
                  className="ctc-ds__card"
                  data-testid={`contacts-ds-card-${contact.id}`}
                >
                  <div className="ctc-ds__card-top">
                    <div className="ctc-ds__card-identity">
                      <ContactAvatar
                        initials={contact.initials}
                        tone={contact.avatarTone}
                        size="lg"
                      />
                      <div>
                        <strong title={contact.fullName}>{contact.fullName}</strong>
                        <span title={contact.company}>{contact.company}</span>
                      </div>
                    </div>
                    <AiScoreBadge
                      score={contact.aiScore}
                      tooltip={t('aiScore.tooltip')}
                    />
                  </div>
                  <div className="ctc-ds__card-meta">
                    <StatusChip tone={statusTone(contact.status)}>
                      {t(`statuses.${contact.status}`)}
                    </StatusChip>
                    <span className="ctc-ds__meta-pill">{t(`roles.${contact.role}`)}</span>
                    <span className="ctc-ds__meta-pill">
                      {t(`sources.${contact.source}`)}
                    </span>
                  </div>
                  <div className="ctc-ds__card-metrics">
                    <div>
                      <span>{t('columns.lastActivity')}</span>
                      <strong>
                        {formatDisplayDate(contact.lastActivity, locale)}
                      </strong>
                    </div>
                    <div>
                      <span>{t('columns.nextFollowUp')}</span>
                      <strong>
                        {formatDisplayDate(contact.nextFollowUp, locale)}
                      </strong>
                    </div>
                  </div>
                  <div className="ctc-ds__card-footer">
                    <div className="ctc-ds__card-owner" title={contact.owner}>
                      <PriorityDot
                        priority={contact.priority}
                        label={t(`priorities.${contact.priority}`)}
                      />
                      <span>{contact.owner}</span>
                    </div>
                    <div className="ctc-ds__card-actions">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => openContact(contact)}
                      >
                        {t('actions.openDetail')}
                      </Button>
                    </div>
                  </div>
                </article>
              ))}
        </section>
      ) : null}

      {!loading && view === 'table' ? (
        <section className="ctc-ds__table-section" aria-label={t('table.aria')}>
          <div className="ctc-ds__main-toolbar">
            <h2>
              {t('table.title')}
              <span className="ctc-ds__count">{filtered.length}</span>
            </h2>
          </div>
          {pageItems.length === 0 ? (
            emptyState
          ) : (
            <div className="ctc-ds__table-wrap">
              <table className="ctc-ds__table">
                <colgroup>
                  <col className="col-avatar" />
                  <col className="col-name" />
                  <col className="col-company" />
                  <col className="col-role" />
                  <col className="col-status" />
                  <col className="col-source" />
                  <col className="col-activity" />
                  <col className="col-followup" />
                  <col className="col-owner" />
                  <col className="col-priority" />
                  <col className="col-score" />
                  <col className="col-actions" />
                </colgroup>
                <thead>
                  <tr>
                    <th scope="col" aria-label={t('columns.avatar')} />
                    <th scope="col">{t('columns.fullName')}</th>
                    <th scope="col">{t('columns.company')}</th>
                    <th scope="col">{t('columns.role')}</th>
                    <th scope="col">{t('columns.status')}</th>
                    <th scope="col">{t('columns.source')}</th>
                    <th scope="col">{t('columns.lastActivity')}</th>
                    <th scope="col">{t('columns.nextFollowUp')}</th>
                    <th scope="col">{t('columns.owner')}</th>
                    <th scope="col">{t('columns.priority')}</th>
                    <th scope="col">{t('columns.aiScore')}</th>
                    <th scope="col">{t('columns.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((contact) => (
                    <tr
                      key={contact.id}
                      className="ctc-ds__row"
                      data-testid={`contacts-ds-row-${contact.id}`}
                      onClick={() => openContact(contact)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          openContact(contact);
                        }
                      }}
                      tabIndex={0}
                    >
                      <td>
                        <ContactAvatar
                          initials={contact.initials}
                          tone={contact.avatarTone}
                        />
                      </td>
                      <td>
                        <strong title={contact.fullName}>{contact.fullName}</strong>
                      </td>
                      <td title={contact.company}>{contact.company}</td>
                      <td>{t(`roles.${contact.role}`)}</td>
                      <td>
                        <StatusChip tone={statusTone(contact.status)}>
                          {t(`statuses.${contact.status}`)}
                        </StatusChip>
                      </td>
                      <td>{t(`sources.${contact.source}`)}</td>
                      <td>{formatDisplayDate(contact.lastActivity, locale)}</td>
                      <td>{formatDisplayDate(contact.nextFollowUp, locale)}</td>
                      <td title={contact.owner}>{contact.owner}</td>
                      <td>
                        <PriorityDot
                          priority={contact.priority}
                          label={t(`priorities.${contact.priority}`)}
                        />
                      </td>
                      <td>
                        <AiScoreBadge
                          score={contact.aiScore}
                          tooltip={t('aiScore.tooltip')}
                        />
                      </td>
                      <td>
                        <RowActions
                          contact={contact}
                          onOpen={() => openContact(contact)}
                          onCall={() => {
                            if (contact.phone) {
                              window.location.href = `tel:${contact.phone}`;
                            }
                          }}
                          onEmail={() => {
                            if (contact.email) {
                              window.location.href = `mailto:${contact.email}`;
                            }
                          }}
                          onWhatsApp={() => {
                            if (contact.phone) {
                              const digits = contact.phone.replace(/\D/g, '');
                              window.open(
                                `https://wa.me/${digits}`,
                                '_blank',
                                'noopener,noreferrer',
                              );
                            }
                          }}
                          onTask={() => {
                            router.push(
                              `/workspaces/crm/tasks?contact=${contact.id}` as Route,
                            );
                          }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {!loading && filtered.length > 0 ? (
        <div className="ctc-ds__pagination">
          <span>
            {t('pagination', {
              page: pageSafe,
              pages,
              total: filtered.length,
            })}
          </span>
          <div>
            <Button
              variant="secondary"
              size="sm"
              disabled={pageSafe <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              {t('prevPage')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={pageSafe >= pages}
              onClick={() => setPage((p) => Math.min(pages, p + 1))}
            >
              {t('nextPage')}
            </Button>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        hidden
        data-testid="contacts-ds-force-empty"
        onClick={() => setForceEmpty(true)}
      />
    </div>
  );
}

export function ContactsDsWorkspace() {
  const t = useTranslations('common');
  return (
    <Suspense
      fallback={
        <div className="ctc-ds">
          <div className="ctc-ds__empty">{t('loading')}</div>
        </div>
      }
    >
      <ContactsDsWorkspaceInner />
    </Suspense>
  );
}
