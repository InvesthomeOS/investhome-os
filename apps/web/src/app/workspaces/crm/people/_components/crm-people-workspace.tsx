'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useMemo, useState, type KeyboardEvent, type MouseEvent } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Input, KpiCard, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import {
  PEOPLE_AI_ACTIONS,
  PEOPLE_DEPARTMENT_ORDER,
  PEOPLE_KPI_ICONS,
  PEOPLE_RELATION_SCORE_COLOR,
  PEOPLE_ROLE_ORDER,
  PEOPLE_SOURCE_COLOR,
  type PeopleAvatarTone,
  type PeopleRelationKey,
  type PeopleRoleKey,
  type PeopleRow,
  type PeopleWorkspacePreview,
} from '../people-model';

type FilterKey =
  | 'search'
  | 'company'
  | 'role'
  | 'department'
  | 'country'
  | 'owner'
  | 'tag';

const ROLE_TONE: Record<
  PeopleRoleKey,
  'success' | 'warning' | 'info' | 'default' | 'danger'
> = {
  ceo: 'info',
  decisionMaker: 'info',
  broker: 'default',
  partner: 'success',
  architect: 'default',
  lawyer: 'warning',
  finance: 'info',
  operations: 'default',
  investor: 'success',
  influencer: 'info',
};

function PersonAvatar({
  initials,
  tone,
  size = 'md',
}: {
  initials: string;
  tone: PeopleAvatarTone;
  size?: 'sm' | 'md';
}) {
  return (
    <span className={`crm-people__avatar is-${tone} is-${size}`} aria-hidden="true">
      {initials}
    </span>
  );
}

function CompanyMark({
  initials,
  tone,
}: {
  initials: string;
  tone: PeopleAvatarTone;
}) {
  return (
    <span className={`crm-people__company-mark is-${tone}`} aria-hidden="true">
      {initials}
    </span>
  );
}

function RelationScore({ score, relation }: { score: number; relation: PeopleRelationKey }) {
  const t = useTranslations('crm.people');
  const color = PEOPLE_RELATION_SCORE_COLOR[relation];
  const pct = Math.max(0, Math.min(100, score));

  return (
    <div className={`crm-people__relation is-${relation}`}>
      <div
        className="crm-people__relation-ring"
        style={{
          background: `conic-gradient(${color} ${pct}%, #e6eef1 0)`,
        }}
        aria-hidden="true"
      >
        <span>{score}</span>
      </div>
      <small>{t(`relation.${relation}`)}</small>
    </div>
  );
}

function AiNoteCell({ noteKey, note }: { noteKey: string; note?: string }) {
  const t = useTranslations('crm.people');
  const [expanded, setExpanded] = useState(false);
  const text = note || t(`aiNotes.${noteKey}`);
  const needsToggle = text.length > 48;

  return (
    <div className="crm-people__ai-summary">
      <p
        className={
          expanded
            ? 'crm-people__ai-note is-expanded'
            : 'crm-people__ai-note crm-people__clamp-fade'
        }
        title={text}
      >
        {text}
      </p>
      {needsToggle ? (
        <button
          type="button"
          className="crm-people__ai-more"
          aria-expanded={expanded}
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
        >
          {expanded ? t('actions.collapse') : t('actions.expand')}
          <IhIcon name="chevronDown" size={11} />
        </button>
      ) : null}
    </div>
  );
}

function ContactChannelIcons({ row }: { row: PeopleRow }) {
  const t = useTranslations('crm.people');

  return (
    <div className="crm-people__channels">
      {row.hasEmail ? (
        <button
          type="button"
          className="crm-people__channel"
          aria-label={t('channels.email')}
          title={t('channels.email')}
        >
          <IhIcon name="inbox" size={13} />
        </button>
      ) : null}
      {row.hasPhone ? (
        <button
          type="button"
          className="crm-people__channel"
          aria-label={t('channels.phone')}
          title={t('channels.phone')}
        >
          <IhIcon name="meeting" size={13} />
        </button>
      ) : null}
      {row.hasLinkedIn ? (
        <button
          type="button"
          className="crm-people__channel"
          aria-label={t('channels.linkedin')}
          title={t('channels.linkedin')}
        >
          <IhIcon name="crm" size={13} />
        </button>
      ) : null}
      {row.hasWhatsApp ? (
        <button
          type="button"
          className="crm-people__channel"
          aria-label={t('channels.whatsapp')}
          title={t('channels.whatsapp')}
        >
          <IhIcon name="check" size={13} />
        </button>
      ) : null}
    </div>
  );
}

function RowActions({ href }: { href: string }) {
  const t = useTranslations('crm.people');

  return (
    <div className="crm-people__row-actions">
      <Link
        href={href as Route}
        className="crm-people__icon-action"
        aria-label={t('actions.detail')}
        title={t('actions.detail')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="search" size={14} />
      </Link>
      <button
        type="button"
        className="crm-people__icon-action"
        aria-label={t('actions.message')}
        title={t('actions.message')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="inbox" size={14} />
      </button>
      <button
        type="button"
        className="crm-people__icon-action"
        aria-label={t('actions.note')}
        title={t('actions.note')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="documents" size={14} />
      </button>
      <button
        type="button"
        className="crm-people__icon-action"
        aria-label={t('actions.more')}
        title={t('actions.more')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="chevronDown" size={14} />
      </button>
    </div>
  );
}

function SourceDonut({
  slices,
  label,
}: {
  slices: PeopleWorkspacePreview['sourceDistribution'];
  label: string;
}) {
  let cursor = 0;
  const stops = slices
    .map((slice) => {
      const start = cursor;
      cursor += slice.pct;
      return `${PEOPLE_SOURCE_COLOR[slice.key]} ${start}% ${cursor}%`;
    })
    .join(', ');

  return (
    <div
      className="crm-people__donut"
      style={{ background: `conic-gradient(${stops})` }}
      role="img"
      aria-label={label}
    >
      <span aria-hidden="true" />
    </div>
  );
}

export function CrmPeopleWorkspace({
  preview,
  onOpenAi,
  onOpenPerson,
  detailBasePath = '/workspaces/crm/people',
  newPersonHref = '/workspaces/crm/contacts/new',
  titleOverride,
  subtitleOverride,
  testId = 'crm-people-workspace',
}: {
  preview: PeopleWorkspacePreview;
  /** Opens Dashboard Freeze AI drawer when provided by the shell. */
  onOpenAi?: (prompt?: string) => void;
  onOpenPerson?: (id: string) => void;
  detailBasePath?: string;
  newPersonHref?: string;
  titleOverride?: string;
  subtitleOverride?: string;
  testId?: string;
}) {
  const t = useTranslations('crm.people');
  const router = useRouter();
  const [aiAction, setAiAction] = useState<string | null>('newPerson');
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    search: '',
    company: '',
    role: '',
    department: '',
    country: '',
    owner: '',
    tag: '',
  });
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const openPerson = (id: string) => {
    if (onOpenPerson) {
      onOpenPerson(id);
      return;
    }
    router.push(`${detailBasePath}/${id}` as Route);
  };

  const onRowActivate = (id: string, event: MouseEvent | KeyboardEvent) => {
    const target = event.target as HTMLElement | null;
    if (target?.closest('a,button,input,label,select,textarea')) return;
    openPerson(id);
  };

  const filteredPeople = useMemo(() => {
    return preview.people.filter((row) => {
      if (filters.company && row.company !== filters.company) return false;
      if (filters.role && row.role !== filters.role) return false;
      if (filters.department && row.department !== filters.department) return false;
      if (filters.country && row.country !== filters.country) return false;
      if (filters.owner && row.owner !== filters.owner) return false;
      if (filters.tag && !row.tags.includes(filters.tag)) return false;
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        if (
          !row.name.toLowerCase().includes(q) &&
          !row.company.toLowerCase().includes(q) &&
          !row.owner.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      if (aiAction === 'missingInfo') {
        return (
          row.relation === 'attention' ||
          row.relation === 'weak' ||
          !row.hasPhone ||
          !row.hasLinkedIn
        );
      }
      if (aiAction === 'similar') {
        return row.role === 'decisionMaker' || row.role === 'ceo' || row.role === 'investor';
      }
      return true;
    });
  }, [aiAction, filters, preview.people]);

  const totalPages = Math.max(1, preview.totalPages);
  const pageItems = filteredPeople.slice(0, Math.min(pageSize, filteredPeople.length));

  const clearFilters = () => {
    setFilters({
      search: '',
      company: '',
      role: '',
      department: '',
      country: '',
      owner: '',
      tag: '',
    });
    setPage(1);
  };

  const setRowChecked = (id: string, checked: boolean) => {
    setCheckedIds((prev) => ({ ...prev, [id]: checked }));
  };

  return (
    <div className="crm-people" data-testid={testId}>
      <header className="crm-people__header">
        <div>
          <h1>{titleOverride ?? t('title')}</h1>
          <p>{subtitleOverride ?? t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-people__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="crm-people__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`)}
            delta={`${kpi.delta} ${t('kpis.thisMonth')}`}
            deltaTone={kpi.deltaTone}
            icon={<IhIcon name={PEOPLE_KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-people__ai" aria-label={t('ai.aria')}>
        {PEOPLE_AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            type="button"
            className={
              action.key === 'newPerson'
                ? 'crm-people__ai-cta'
                : aiAction === action.key
                  ? 'is-featured'
                  : undefined
            }
            onClick={() => {
              if (action.key === 'newPerson') {
                setAiAction(action.key);
                router.push(newPersonHref as Route);
                return;
              }
              if (action.key === 'aiAnalysis') {
                onOpenAi?.(t('ai.openPrompt'));
                setAiAction(action.key);
                return;
              }
              setAiAction((prev) => (prev === action.key ? null : action.key));
            }}
          >
            <span className="crm-people__ai-icon" aria-hidden="true">
              <IhIcon name={action.icon} size={15} />
            </span>
            <span>{t(`ai.actions.${action.key}`)}</span>
          </button>
        ))}
        <button
          type="button"
          className="screenshot-dashboard__intro-ai-primary"
          onClick={() => onOpenAi?.(t('ai.openPrompt'))}
        >
          <IhIcon name="sparkles" size={15} />
          {t('ai.title')}
        </button>
      </nav>

      <section className="crm-people__filters" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={filters.search}
          onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Select
          label={t('filters.company')}
          value={filters.company}
          onChange={(e) => setFilters((prev) => ({ ...prev, company: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.companies.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.role')}
          value={filters.role}
          onChange={(e) => setFilters((prev) => ({ ...prev, role: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {PEOPLE_ROLE_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`role.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.department')}
          value={filters.department}
          onChange={(e) => setFilters((prev) => ({ ...prev, department: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {PEOPLE_DEPARTMENT_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`department.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.country')}
          value={filters.country}
          onChange={(e) => setFilters((prev) => ({ ...prev, country: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.countries.map((key) => (
            <option key={key} value={key}>
              {t(`country.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.owner')}
          value={filters.owner}
          onChange={(e) => setFilters((prev) => ({ ...prev, owner: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.owners.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.tag')}
          value={filters.tag}
          onChange={(e) => setFilters((prev) => ({ ...prev, tag: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {preview.tags.map((tag) => (
            <option key={tag} value={tag}>
              {t(`tags.${tag}`)}
            </option>
          ))}
        </Select>
        <Button variant="secondary" size="sm" onClick={clearFilters}>
          <IhIcon name="refresh" size={13} />
          {t('filters.clear')}
        </Button>
      </section>

      <div className="crm-people__layout">
        <div className="crm-people__main">
          <div className="crm-people__table-wrap" role="region" aria-label={t('table.aria')}>
            <table className="crm-people__table">
              <thead>
                <tr>
                  <th scope="col" className="crm-people__th-check">
                    <span className="sr-only">{t('table.select')}</span>
                  </th>
                  <th scope="col">{t('table.person')}</th>
                  <th scope="col">{t('table.company')}</th>
                  <th scope="col">{t('table.role')}</th>
                  <th scope="col">{t('table.department')}</th>
                  <th scope="col">{t('table.contact')}</th>
                  <th scope="col">{t('table.lastActivity')}</th>
                  <th scope="col">{t('table.relation')}</th>
                  <th scope="col">{t('table.aiNote')}</th>
                  <th scope="col">{t('table.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((row) => {
                  const detailHref = `${detailBasePath}/${row.id}`;
                  return (
                  <tr
                    key={row.id}
                    data-testid={`person-row-${row.id}`}
                    tabIndex={0}
                    role="link"
                    onClick={(e) => onRowActivate(row.id, e)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        onRowActivate(row.id, e);
                      }
                    }}
                  >
                    <td>
                      <label className="crm-people__checkbox">
                        <input
                          type="checkbox"
                          checked={Boolean(checkedIds[row.id])}
                          aria-label={t('actions.selectPerson', { name: row.name })}
                          onChange={(e) => setRowChecked(row.id, e.target.checked)}
                        />
                      </label>
                    </td>
                    <td>
                      <Link
                        href={detailHref as Route}
                        className="crm-people__person-cell"
                        onClick={(e) => {
                          if (!onOpenPerson) return;
                          e.preventDefault();
                          e.stopPropagation();
                          onOpenPerson(row.id);
                        }}
                      >
                        <PersonAvatar initials={row.initials} tone={row.avatarTone} />
                        <div className="crm-people__person-text">
                          <strong title={row.name}>{row.name}</strong>
                          <span title={row.title ?? t(`titles.${row.titleKey}`)}>
                            {row.title ?? t(`titles.${row.titleKey}`)}
                          </span>
                        </div>
                      </Link>
                    </td>
                    <td>
                      <div className="crm-people__company-cell">
                        <CompanyMark initials={row.companyInitials} tone={row.companyTone} />
                        <span title={row.company}>{row.company}</span>
                      </div>
                    </td>
                    <td>
                      <StatusChip
                        tone={ROLE_TONE[row.role]}
                        className={`crm-people__badge crm-people__role--${row.role}`}
                      >
                        {t(`role.${row.role}`)}
                      </StatusChip>
                    </td>
                    <td>
                      <span className="crm-people__dept">{t(`department.${row.department}`)}</span>
                    </td>
                    <td>
                      <ContactChannelIcons row={row} />
                    </td>
                    <td>
                      <div className="crm-people__activity">
                        <IhIcon name="activity" size={12} />
                        <div>
                          <strong>{row.lastActivityLabel ?? t(`lastActivity.${row.lastActivityKey}`)}</strong>
                          <time>{row.lastActivityDate}</time>
                        </div>
                      </div>
                    </td>
                    <td>
                      <RelationScore score={row.relationScore} relation={row.relation} />
                    </td>
                    <td>
                      <AiNoteCell noteKey={row.aiNoteKey} note={row.aiNote} />
                    </td>
                    <td>
                      <RowActions href={detailHref} />
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <footer className="crm-people__pagination" aria-label={t('pagination.aria')}>
            <p>{t('pagination.total', { count: preview.totalPeople })}</p>
            <div className="crm-people__page-numbers" role="navigation">
              {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((n) => (
                <button
                  key={n}
                  type="button"
                  className={page === n ? 'is-active' : undefined}
                  onClick={() => setPage(n)}
                  aria-current={page === n ? 'page' : undefined}
                >
                  {n}
                </button>
              ))}
              {totalPages > 6 ? <span className="crm-people__page-ellipsis">…</span> : null}
              {totalPages > 5 ? (
                <button
                  type="button"
                  className={page === totalPages ? 'is-active' : undefined}
                  onClick={() => setPage(totalPages)}
                  aria-current={page === totalPages ? 'page' : undefined}
                >
                  {totalPages}
                </button>
              ) : null}
            </div>
            <label className="ih-field crm-people__page-size">
              <span className="ih-field__label">{t('pagination.perPage')}</span>
              <select
                className="ih-select"
                value={String(pageSize)}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                aria-label={t('pagination.perPage')}
              >
                <option value="10">10 / {t('pagination.pageUnit')}</option>
                <option value="20">20 / {t('pagination.pageUnit')}</option>
                <option value="40">40 / {t('pagination.pageUnit')}</option>
              </select>
            </label>
          </footer>
        </div>

        <aside className="crm-people__rail" aria-label={t('rail.aria')}>
          <section className="crm-people__rail-card">
            <h3>{t('rail.recent')}</h3>
            <ul className="crm-people__recent">
              {preview.recentPeople.map((item) => (
                <li key={item.id}>
                  <PersonAvatar initials={item.initials} tone={item.avatarTone} size="sm" />
                  <div>
                    <strong title={item.name}>{item.name}</strong>
                    <span title={item.company}>{item.company}</span>
                    <span>{t(`rail.addedAt.${item.addedAtKey}`)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-people__rail-card">
            <h3>{t('rail.upcoming')}</h3>
            <ul className="crm-people__meetings">
              {preview.upcomingMeetings.map((item) => (
                <li key={item.id}>
                  <span className="crm-people__meeting-icon" aria-hidden="true">
                    <IhIcon name="calendar" size={13} />
                  </span>
                  <div>
                    <strong title={item.name}>{item.name}</strong>
                    <span title={item.company}>{item.company}</span>
                    <time>{t(`rail.meetingWhen.${item.whenKey}`)}</time>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-people__rail-card">
            <h3>{t('rail.sourceDistribution')}</h3>
            <div className="crm-people__distribution">
              <SourceDonut
                slices={preview.sourceDistribution}
                label={t('rail.sourceDistribution')}
              />
              <ul className="crm-people__legend">
                {preview.sourceDistribution.map((slice) => (
                  <li key={slice.key} className={`is-${slice.key}`}>
                    <span />
                    {t(`source.${slice.key}`)} · {slice.pct}%
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="crm-people__rail-card">
            <h3>{t('rail.activePeople')}</h3>
            <ol className="crm-people__active">
              {preview.activePeople.map((item, index) => (
                <li key={item.id}>
                  <span className="crm-people__rank" aria-hidden="true">
                    {index + 1}
                  </span>
                  <PersonAvatar initials={item.initials} tone={item.avatarTone} size="sm" />
                  <div>
                    <strong title={item.name}>{item.name}</strong>
                    <span>
                      {[
                        item.activityCount != null
                          ? t('rail.activityCount', { count: item.activityCount })
                          : null,
                        item.lastContactLabel ??
                          (item.lastContactKey ? t(`rail.lastContact.${item.lastContactKey}`) : null),
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
    </div>
  );
}
