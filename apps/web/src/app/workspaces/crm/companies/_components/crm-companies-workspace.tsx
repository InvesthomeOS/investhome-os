'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useMemo, useState, type KeyboardEvent, type MouseEvent } from 'react';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, KpiCard, LoadingState, Select, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { crmCompaniesQueries } from '@/lib/query/crm-companies-queries';
import { buildCompaniesPreview } from '@/workspaces/crm/lib/map-live-workspace';
import {
  COMPANY_AI_ACTIONS,
  COMPANY_CATEGORY_ORDER,
  COMPANY_COUNTRY_FLAG,
  COMPANY_HEALTH_SCORE_COLOR,
  COMPANY_KPI_ICONS,
  COMPANY_RELATION_ORDER,
  COMPANY_STATUS_ORDER,
  type CompanyCategoryKey,
  type CompanyHealthKey,
  type CompanyRow,
  type CompanyWorkspacePreview,
} from '../companies-model';

type FilterKey =
  | 'search'
  | 'category'
  | 'country'
  | 'status'
  | 'relation'
  | 'owner'
  | 'tag';

const CATEGORY_TONE: Record<
  CompanyCategoryKey,
  'success' | 'warning' | 'info' | 'default' | 'danger'
> = {
  investor: 'info',
  developer: 'success',
  architecture: 'default',
  legal: 'warning',
  title: 'info',
  broker: 'default',
  bank: 'info',
  partner: 'success',
};

function CompanyLogo({
  initials,
  tone,
  size = 'md',
}: {
  initials: string;
  tone: CompanyRow['logoTone'];
  size?: 'sm' | 'md';
}) {
  return (
    <span className={`crm-companies__logo is-${tone} is-${size}`} aria-hidden="true">
      {initials}
    </span>
  );
}

function HealthScore({ score, health }: { score: number; health: CompanyHealthKey }) {
  const t = useTranslations('crm.companies');
  const color = COMPANY_HEALTH_SCORE_COLOR[health];
  const pct = Math.max(0, Math.min(100, score));

  return (
    <div className={`crm-companies__health is-${health}`}>
      <div
        className="crm-companies__health-ring"
        style={{
          background: `conic-gradient(${color} ${pct}%, #e6eef1 0)`,
        }}
        aria-hidden="true"
      >
        <span>{score}</span>
      </div>
      <small>{t(`health.${health}`)}</small>
    </div>
  );
}

function AiSummaryCell({ noteKey, note }: { noteKey: string; note?: string }) {
  const t = useTranslations('crm.companies');
  const [expanded, setExpanded] = useState(false);
  const text = note || t(`aiSummaries.${noteKey}`);
  const needsToggle = text.length > 48;

  return (
    <div className="crm-companies__ai-summary">
      <p
        className={
          expanded
            ? 'crm-companies__ai-note is-expanded'
            : 'crm-companies__ai-note crm-companies__clamp-fade'
        }
        title={text}
      >
        {text}
      </p>
      {needsToggle ? (
        <button
          type="button"
          className="crm-companies__ai-more"
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

function RowActions({ href }: { href: string }) {
  const t = useTranslations('crm.companies');

  return (
    <div className="crm-companies__row-actions">
      <Link
        href={href as Route}
        className="crm-companies__icon-action"
        aria-label={t('actions.detail')}
        title={t('actions.detail')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="search" size={14} />
      </Link>
      <button
        type="button"
        className="crm-companies__icon-action"
        aria-label={t('actions.edit')}
        title={t('actions.edit')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="settings" size={14} />
      </button>
      <button
        type="button"
        className="crm-companies__icon-action"
        aria-label={t('actions.note')}
        title={t('actions.note')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="documents" size={14} />
      </button>
      <button
        type="button"
        className="crm-companies__icon-action"
        aria-label={t('actions.more')}
        title={t('actions.more')}
        onClick={(e) => e.stopPropagation()}
      >
        <IhIcon name="chevronDown" size={14} />
      </button>
    </div>
  );
}

function CategoryDonut({
  slices,
  label,
}: {
  slices: CompanyWorkspacePreview['categoryDistribution'];
  label: string;
}) {
  const colors: Record<string, string> = {
    investor: '#2f6fed',
    developer: '#2f8a5b',
    architecture: '#7b5ea7',
    legal: '#c77938',
    title: '#58aebb',
    other: '#9aa7af',
  };

  let cursor = 0;
  const stops = slices
    .map((slice) => {
      const start = cursor;
      cursor += slice.pct;
      return `${colors[slice.key] ?? colors.other} ${start}% ${cursor}%`;
    })
    .join(', ');

  return (
    <div
      className="crm-companies__donut"
      style={{ background: `conic-gradient(${stops})` }}
      role="img"
      aria-label={label}
    >
      <span aria-hidden="true" />
    </div>
  );
}

export function CrmCompaniesWorkspace({
  preview: previewProp,
  onOpenAi,
  detailBasePath = '/workspaces/crm/companies',
  newCompanyHref = '/workspaces/crm/companies/new',
}: {
  preview?: CompanyWorkspacePreview;
  /** Opens Dashboard Freeze AI drawer when provided by the shell. */
  onOpenAi?: (prompt?: string) => void;
  detailBasePath?: string;
  newCompanyHref?: string;
}) {
  const t = useTranslations('crm.companies');
  const router = useRouter();
  const [aiAction, setAiAction] = useState<string | null>('newCompany');
  const [filters, setFilters] = useState<Record<FilterKey, string>>({
    search: '',
    category: '',
    country: '',
    status: '',
    relation: '',
    owner: '',
    tag: '',
  });
  const [checkedIds, setCheckedIds] = useState<Record<string, boolean>>({});
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const liveQuery = useQuery({
    ...crmCompaniesQueries.list({
      page,
      pageSize,
      search: filters.search.trim() || undefined,
      status: filters.status || undefined,
    }),
    enabled: !previewProp,
  });
  const preview = previewProp ?? buildCompaniesPreview(liveQuery.data?.items ?? [], liveQuery.data?.total ?? 0, pageSize);

  const openCompany = (id: string) => {
    router.push(`${detailBasePath}/${id}` as Route);
  };

  const onRowActivate = (id: string, event: MouseEvent | KeyboardEvent) => {
    const target = event.target as HTMLElement | null;
    if (target?.closest('a,button,input,label,select,textarea')) return;
    openCompany(id);
  };

  const filteredCompanies = useMemo(() => {
    if (!previewProp) return preview.companies;
    return preview.companies.filter((row) => {
      if (filters.category && row.category !== filters.category) return false;
      if (filters.country && row.country !== filters.country) return false;
      if (filters.status && row.status !== filters.status) return false;
      if (filters.relation && row.relation !== filters.relation) return false;
      if (filters.owner && row.owner !== filters.owner) return false;
      if (filters.tag && !row.tags.includes(filters.tag)) return false;
      if (filters.search) {
        const q = filters.search.trim().toLowerCase();
        if (
          !row.name.toLowerCase().includes(q) &&
          !row.contactName.toLowerCase().includes(q) &&
          !row.owner.toLowerCase().includes(q)
        ) {
          return false;
        }
      }
      if (aiAction === 'missingInfo') {
        return row.health === 'attention' || row.health === 'risk' || row.openProjects === 0;
      }
      if (aiAction === 'similar') {
        return row.category === 'investor' || row.category === 'developer';
      }
      return true;
    });
  }, [aiAction, filters, preview.companies, previewProp]);

  const totalPages = Math.max(1, previewProp ? preview.totalPages : Math.ceil((preview.totalCompanies || 1) / pageSize));
  const pageItems = previewProp
    ? filteredCompanies.slice(0, Math.min(pageSize, filteredCompanies.length))
    : filteredCompanies;

  const clearFilters = () => {
    setFilters({
      search: '',
      category: '',
      country: '',
      status: '',
      relation: '',
      owner: '',
      tag: '',
    });
    setPage(1);
  };

  const setRowChecked = (id: string, checked: boolean) => {
    setCheckedIds((prev) => ({ ...prev, [id]: checked }));
  };

  if (!previewProp && liveQuery.isLoading) {
    return <LoadingState label={t('title')} />;
  }

  return (
    <div className="crm-companies" data-testid="crm-companies-workspace">
      <header className="crm-companies__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
      </header>

      <section className="crm-companies__kpi-row" aria-label={t('kpis.aria')}>
        {preview.kpis.map((kpi) => (
          <KpiCard
            key={kpi.key}
            className="crm-companies__kpi"
            label={t(`kpis.${kpi.key}`)}
            value={kpi.value}
            hint={t(`kpis.hints.${kpi.hintKey}`)}
            delta={`${kpi.delta} ${t('kpis.thisMonth')}`}
            deltaTone={kpi.deltaTone}
            icon={<IhIcon name={COMPANY_KPI_ICONS[kpi.key]} size={18} />}
          />
        ))}
      </section>

      <nav className="screenshot-dashboard__intro-ai crm-companies__ai" aria-label={t('ai.aria')}>
        {COMPANY_AI_ACTIONS.map((action) => (
          <button
            key={action.key}
            type="button"
            className={
              action.key === 'newCompany'
                ? 'crm-companies__ai-cta'
                : aiAction === action.key
                  ? 'is-featured'
                  : undefined
            }
            onClick={() => {
              if (action.key === 'newCompany') {
                setAiAction(action.key);
                router.push(newCompanyHref as Route);
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
            <span className="crm-companies__ai-icon" aria-hidden="true">
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

      <section className="crm-companies__filters" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={filters.search}
          onChange={(e) => {
            setFilters((prev) => ({ ...prev, search: e.target.value }));
            setPage(1);
          }}
          placeholder={t('filters.searchPlaceholder')}
        />
        <Select
          label={t('filters.category')}
          value={filters.category}
          onChange={(e) => setFilters((prev) => ({ ...prev, category: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {COMPANY_CATEGORY_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`category.${key}`)}
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
              {COMPANY_COUNTRY_FLAG[key]} {t(`country.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.status')}
          value={filters.status}
          onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {COMPANY_STATUS_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`status.${key}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.relation')}
          value={filters.relation}
          onChange={(e) => setFilters((prev) => ({ ...prev, relation: e.target.value }))}
        >
          <option value="">{t('filters.any')}</option>
          {COMPANY_RELATION_ORDER.map((key) => (
            <option key={key} value={key}>
              {t(`relation.${key}`)}
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

      <div className="crm-companies__layout">
        <div className="crm-companies__main">
          <div className="crm-companies__table-wrap" role="region" aria-label={t('table.aria')}>
            <table className="crm-companies__table">
              <thead>
                <tr>
                  <th scope="col" className="crm-companies__th-check">
                    <span className="sr-only">{t('table.select')}</span>
                  </th>
                  <th scope="col">{t('table.company')}</th>
                  <th scope="col">{t('table.category')}</th>
                  <th scope="col">{t('table.country')}</th>
                  <th scope="col">{t('table.contact')}</th>
                  <th scope="col">{t('table.openProjects')}</th>
                  <th scope="col">{t('table.lastActivity')}</th>
                  <th scope="col">{t('table.health')}</th>
                  <th scope="col">{t('table.aiSummary')}</th>
                  <th scope="col">{t('table.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {pageItems.map((row) => {
                  const detailHref = `${detailBasePath}/${row.id}`;
                  return (
                  <tr
                    key={row.id}
                    data-testid={`company-row-${row.id}`}
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
                      <label className="crm-companies__checkbox">
                        <input
                          type="checkbox"
                          checked={Boolean(checkedIds[row.id])}
                          aria-label={t('actions.selectCompany', { name: row.name })}
                          onChange={(e) => setRowChecked(row.id, e.target.checked)}
                        />
                      </label>
                    </td>
                    <td>
                      <Link
                        href={detailHref as Route}
                        className="crm-companies__company-cell"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <CompanyLogo initials={row.initials} tone={row.logoTone} />
                        <div className="crm-companies__company-text">
                          <strong title={row.name}>{row.name}</strong>
                          <span title={row.subtitle ?? t(`subtitles.${row.subtitleKey}`)}>
                            {row.subtitle ?? t(`subtitles.${row.subtitleKey}`)}
                          </span>
                        </div>
                      </Link>
                    </td>
                    <td>
                      <StatusChip
                        tone={CATEGORY_TONE[row.category]}
                        className={`crm-companies__badge crm-companies__cat--${row.category}`}
                      >
                        {t(`category.${row.category}`)}
                      </StatusChip>
                    </td>
                    <td>
                      <span className="crm-companies__country">
                        <span aria-hidden="true">{COMPANY_COUNTRY_FLAG[row.country]}</span>
                        <span>{t(`country.${row.country}`)}</span>
                      </span>
                    </td>
                    <td>
                      <div className="crm-companies__contact">
                        <span className="crm-companies__avatar" aria-hidden="true">
                          {row.contactInitials}
                        </span>
                        <div>
                          <strong title={row.contactName}>{row.contactName}</strong>
                          <span>{row.contactDetail ?? t(`roles.${row.contactRoleKey}`)}</span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="crm-companies__projects">{row.openProjects}</span>
                    </td>
                    <td>
                      <div className="crm-companies__activity">
                        <IhIcon name="activity" size={12} />
                        <div>
                          <strong>{row.lastActivityLabel ?? t(`lastActivity.${row.lastActivityKey}`)}</strong>
                          <time>{row.lastActivityDate}</time>
                        </div>
                      </div>
                    </td>
                    <td>
                      <HealthScore score={row.healthScore} health={row.health} />
                    </td>
                    <td>
                      <AiSummaryCell noteKey={row.aiSummaryKey} note={row.aiSummary} />
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

          <footer className="crm-companies__pagination" aria-label={t('pagination.aria')}>
            <p>{t('pagination.total', { count: preview.totalCompanies })}</p>
            <div className="crm-companies__page-numbers" role="navigation">
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
              {totalPages > 6 ? <span className="crm-companies__page-ellipsis">…</span> : null}
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
            <label className="ih-field crm-companies__page-size">
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

        <aside className="crm-companies__rail" aria-label={t('rail.aria')}>
          <section className="crm-companies__rail-card">
            <h3>{t('rail.recent')}</h3>
            <ul className="crm-companies__recent">
              {preview.recentCompanies.map((item) => (
                <li key={item.id}>
                  <CompanyLogo initials={item.initials} tone={item.logoTone} size="sm" />
                  <div>
                    <strong title={item.name}>{item.name}</strong>
                    <span>{t(`rail.addedAt.${item.addedAtKey}`)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <section className="crm-companies__rail-card">
            <h3>{t('rail.upcoming')}</h3>
            {preview.upcomingMeetings.length ? (
              <ul className="crm-companies__meetings">
                {preview.upcomingMeetings.map((item) => (
                  <li key={item.id}>
                    <span className="crm-companies__meeting-icon" aria-hidden="true">
                      <IhIcon name="calendar" size={13} />
                    </span>
                    <div>
                      <strong title={item.company}>{item.company}</strong>
                      <span>{t(`rail.meetingTypes.${item.typeKey}`)}</span>
                      <time>{t(`rail.meetingWhen.${item.whenKey}`)}</time>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p>—</p>
            )}
          </section>

          <section className="crm-companies__rail-card crm-companies__rail-card--ai">
            <h3>{t('rail.aiRecommendations')}</h3>
            {preview.recommendations.length ? (
              <ul className="crm-companies__recs">
                {preview.recommendations.map((item) => (
                  <li key={item.id}>{t(`rail.recommendations.${item.bodyKey}`)}</li>
                ))}
              </ul>
            ) : (
              <p>—</p>
            )}
          </section>

          <section className="crm-companies__rail-card">
            <h3>{t('rail.categoryDistribution')}</h3>
            <div className="crm-companies__distribution">
              <CategoryDonut
                slices={preview.categoryDistribution}
                label={t('rail.categoryDistribution')}
              />
              <ul className="crm-companies__legend">
                {preview.categoryDistribution.map((slice) => (
                  <li key={slice.key} className={`is-${slice.key}`}>
                    <span />
                    {slice.key === 'other'
                      ? t('rail.other')
                      : t(`category.${slice.key}`)}{' '}
                    · {slice.pct}%
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section className="crm-companies__rail-card">
            <h3>{t('rail.activePartners')}</h3>
            <ul className="crm-companies__partners">
              {preview.activePartners.map((item) => (
                <li key={item.id}>
                  <CompanyLogo initials={item.initials} tone={item.logoTone} size="sm" />
                  <div>
                    <strong title={item.name}>{item.name}</strong>
                    <span>
                      {t('rail.activityCount', { count: item.activityCount })} ·{' '}
                      {t(`rail.lastContact.${item.lastContactKey}`)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </aside>
      </div>
    </div>
  );
}
