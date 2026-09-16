'use client';

import type { Route } from 'next';
import { Suspense, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import {
  Button,
  ErrorState,
  Input,
  SegmentedControl,
  Select,
  StatusChip,
} from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { crmLabel } from '@/lib/crm/crm-labels';
import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { useContactCard } from '@/workspaces/crm/contact-card/contact-card-context';
import {
  relationshipMutations,
  relationshipQueries,
} from '@/workspaces/crm/hooks/use-relationships';
import type { CrmRelationshipSummary } from '@/workspaces/crm/api/relationships';

import './relationships-ds.css';

type RelationshipQuickFilter = 'all' | 'active' | 'stale' | 'atRisk' | 'confidential';
type RelationshipViewMode = 'list' | 'network' | 'intelligence';
type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';
type ScoreBand = 'green' | 'yellow' | 'orange' | 'red';

type DraftFilters = {
  search: string;
  status: string;
  category: string;
  relationship_type: string;
};

type AppliedFilters = DraftFilters & {
  page: number;
  page_size: number;
  sort_by: string;
  sort_dir: 'asc' | 'desc';
};

const PAGE_SIZE = 25;

const EMPTY_DRAFT: DraftFilters = {
  search: '',
  status: '',
  category: '',
  relationship_type: '',
};

const EMPTY_APPLIED: AppliedFilters = {
  ...EMPTY_DRAFT,
  page: 1,
  page_size: PAGE_SIZE,
  sort_by: 'updated_at',
  sort_dir: 'desc',
};

const QUICK_FILTERS: RelationshipQuickFilter[] = [
  'all',
  'active',
  'stale',
  'atRisk',
  'confidential',
];

const STATUS_OPTIONS = ['active', 'inactive', 'pending', 'archived'] as const;
const CATEGORY_OPTIONS = [
  'organizational',
  'commercial',
  'personal',
  'referral',
  'investment',
  'operational',
] as const;
const TYPE_OPTIONS = [
  'contact_company',
  'investor',
  'parent',
  'subsidiary',
  'partner',
  'client',
  'vendor',
  'referred_by',
  'colleague',
  'employed_by',
] as const;

function scoreBand(score: number): ScoreBand {
  if (score >= 75) return 'green';
  if (score >= 55) return 'yellow';
  if (score >= 35) return 'orange';
  return 'red';
}

function statusTone(status: string): StatusTone {
  switch (status) {
    case 'active':
      return 'success';
    case 'pending':
      return 'info';
    case 'inactive':
      return 'default';
    case 'archived':
      return 'warning';
    default:
      return 'default';
  }
}

function strengthTone(strength: string): StatusTone {
  switch (strength) {
    case 'strategic':
      return 'success';
    case 'strong':
      return 'info';
    case 'moderate':
      return 'warning';
    case 'weak':
      return 'default';
    default:
      return 'default';
  }
}

function matchesQuick(row: CrmRelationshipSummary, quick: RelationshipQuickFilter): boolean {
  switch (quick) {
    case 'all':
      return true;
    case 'active':
      return row.status === 'active';
    case 'stale':
      return row.engagement_score < 40;
    case 'atRisk':
      return row.risk_score > 60;
    case 'confidential':
      return row.is_confidential;
    default:
      return true;
  }
}

function ScoreBadge({ score, tooltip }: { score: number; tooltip: string }) {
  return (
    <span className={`rel-ds__score is-${scoreBand(score)}`} title={tooltip}>
      {score}
    </span>
  );
}

function TableSkeleton() {
  return (
    <div className="rel-ds__skeleton" aria-hidden="true">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="rel-ds__skeleton-row" />
      ))}
    </div>
  );
}

function RelationshipsDsWorkspaceInner() {
  const t = useTranslations('crm.relationships');
  const tTypes = useTranslations('crm.relationships.types');
  const tCategories = useTranslations('crm.relationships.categories');
  const tStrengths = useTranslations('crm.relationships.strengths');
  const tStatuses = useTranslations('crm.relationships.filters');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { openContact } = useContactCard();
  const { authLoading, canRead, canCreate } = useCrmAccess();

  const [draft, setDraft] = useState<DraftFilters>(EMPTY_DRAFT);
  const [applied, setApplied] = useState<AppliedFilters>(EMPTY_APPLIED);
  const [quick, setQuick] = useState<RelationshipQuickFilter>('all');
  const [exporting, setExporting] = useState(false);

  const needsClientQuick = quick === 'stale' || quick === 'atRisk' || quick === 'confidential';

  const listParams = useMemo(() => {
    const statusFromQuick = quick === 'active' ? 'active' : undefined;
    return {
      search: applied.search || undefined,
      status: statusFromQuick ?? (applied.status || undefined),
      category: applied.category || undefined,
      relationship_type: applied.relationship_type || undefined,
      page: needsClientQuick ? 1 : applied.page,
      page_size: needsClientQuick ? 100 : applied.page_size,
      sort_by: applied.sort_by,
      sort_dir: applied.sort_dir,
    };
  }, [applied, quick, needsClientQuick]);

  const listQuery = useQuery({
    ...relationshipQueries.list(listParams),
    enabled: !authLoading && canRead,
  });

  const rawItems = listQuery.data?.items ?? [];
  const displayItems = useMemo(() => {
    if (quick === 'all' || quick === 'active') return rawItems;
    return rawItems.filter((row) => matchesQuick(row, quick));
  }, [rawItems, quick]);

  const serverTotal = listQuery.data?.total ?? 0;
  const total = needsClientQuick ? displayItems.length : serverTotal;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const pageSafe = Math.min(applied.page, pages);
  const pageItems = needsClientQuick
    ? displayItems.slice((pageSafe - 1) * PAGE_SIZE, pageSafe * PAGE_SIZE)
    : displayItems;

  const patchDraft = (patch: Partial<DraftFilters>) => {
    setDraft((prev) => ({ ...prev, ...patch }));
  };

  const handleApply = () => {
    setApplied({
      ...EMPTY_APPLIED,
      ...draft,
      page: 1,
      page_size: PAGE_SIZE,
    });
  };

  const handleReset = () => {
    setDraft(EMPTY_DRAFT);
    setApplied(EMPTY_APPLIED);
    setQuick('all');
  };

  const handleQuick = (next: RelationshipQuickFilter) => {
    setQuick(next);
    setDraft(EMPTY_DRAFT);
    setApplied({
      ...EMPTY_APPLIED,
      status: next === 'active' ? 'active' : '',
    });
  };

  const handleViewChange = (next: string) => {
    const mode = next as RelationshipViewMode;
    if (mode === 'network') {
      router.push('/workspaces/crm/relationships/network' as Route);
      return;
    }
    if (mode === 'intelligence') {
      router.push('/workspaces/crm/relationships/intelligence' as Route);
      return;
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const csv = await relationshipMutations.exportCsv();
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'crm-relationships-export.csv';
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Keep UX quiet — export failure surfaces via empty download attempt only.
    } finally {
      setExporting(false);
    }
  };

  const goNew = () => {
    router.push('/workspaces/crm/relationships/new' as Route);
  };

  const openEntity = (type: string, id: string) => {
    if (type === 'contact') {
      openContact(id);
      return;
    }
    if (type === 'company') {
      router.push(`/workspaces/crm/companies/${id}` as Route);
      return;
    }
    if (type === 'project' || type === 'investment') {
      router.push('/workspaces/crm/projects' as Route);
      return;
    }
  };

  const openRow = (row: CrmRelationshipSummary) => {
    router.push(`/workspaces/crm/relationships/${row.id}` as Route);
  };

  if (authLoading) {
    return (
      <div className="rel-ds" data-testid="relationships-ds-workspace">
        <div className="rel-ds__empty">{tCommon('loading')}</div>
      </div>
    );
  }

  if (!canRead) {
    return <ErrorState title={t('accessDenied')} message={t('accessDenied')} />;
  }

  const emptyState = (
    <div className="rel-ds__empty" data-testid="relationships-ds-empty">
      <strong>{t('emptyTitle')}</strong>
      <p>{t('emptyDescription')}</p>
      {canCreate ? (
        <div className="rel-ds__empty-actions">
          <Button variant="primary" size="sm" onClick={goNew}>
            <IhIcon name="plus" size={13} />
            {t('create')}
          </Button>
        </div>
      ) : null}
    </div>
  );

  const showError = listQuery.isError;
  const showLoading = listQuery.isLoading;

  return (
    <div className="rel-ds" data-testid="relationships-ds-workspace">
      <header className="rel-ds__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('description')}</p>
        </div>
        <div className="rel-ds__header-actions">
          <div className="rel-ds__header-search">
            <Input
              label={t('filters.search')}
              value={draft.search}
              onChange={(e) => patchDraft({ search: e.target.value })}
              placeholder={t('filters.searchPlaceholder')}
              data-testid="relationships-ds-header-search"
            />
          </div>
          {canCreate ? (
            <Button
              variant="primary"
              size="sm"
              onClick={goNew}
              data-testid="relationships-ds-add"
            >
              <IhIcon name="plus" size={13} />
              {t('create')}
            </Button>
          ) : null}
        </div>
      </header>

      <section className="rel-ds__toolbar" aria-label={t('filters.aria')}>
        <Input
          label={t('filters.search')}
          value={draft.search}
          onChange={(e) => patchDraft({ search: e.target.value })}
          placeholder={t('filters.searchPlaceholder')}
          data-testid="relationships-ds-search"
        />
        <Select
          label={t('filters.status')}
          value={draft.status}
          onChange={(e) => patchDraft({ status: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {tStatuses(status)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.category')}
          value={draft.category}
          onChange={(e) => patchDraft({ category: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {CATEGORY_OPTIONS.map((category) => (
            <option key={category} value={category}>
              {crmLabel(tCategories, category)}
            </option>
          ))}
        </Select>
        <Select
          label={t('filters.type')}
          value={draft.relationship_type}
          onChange={(e) => patchDraft({ relationship_type: e.target.value })}
        >
          <option value="">{t('filters.any')}</option>
          {TYPE_OPTIONS.map((type) => (
            <option key={type} value={type}>
              {crmLabel(tTypes, type)}
            </option>
          ))}
        </Select>
        <div className="rel-ds__toolbar-actions">
          <Button variant="secondary" size="sm" onClick={handleApply}>
            {tCommon('apply')}
          </Button>
          <Button variant="secondary" size="sm" onClick={handleReset}>
            {tCommon('reset')}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => void handleExport()}
            disabled={exporting}
          >
            <IhIcon name="documents" size={13} />
            {t('actions.export')}
          </Button>
        </div>
        <div className="rel-ds__view-toggle">
          <SegmentedControl
            ariaLabel={t('view.aria')}
            value="list"
            onChange={handleViewChange}
            options={[
              { value: 'list', label: t('view.list') },
              { value: 'network', label: t('networkView') },
              { value: 'intelligence', label: t('intelligenceView') },
            ]}
          />
        </div>
      </section>

      <section className="rel-ds__quick" aria-label={t('quick.aria')}>
        <SegmentedControl
          ariaLabel={t('quick.aria')}
          value={quick}
          onChange={(next) => handleQuick(next as RelationshipQuickFilter)}
          options={QUICK_FILTERS.map((key) => ({
            value: key,
            label: t(`savedViews.${key}`),
          }))}
        />
      </section>

      {showError ? (
        <section className="rel-ds__table-section">
          <div className="rel-ds__empty">
            <strong>{t('loadFailed')}</strong>
            <p>{listQuery.error?.message ?? t('loadFailed')}</p>
            <div className="rel-ds__empty-actions">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void listQuery.refetch()}
              >
                {tCommon('retry')}
              </Button>
            </div>
          </div>
        </section>
      ) : null}

      {!showError && showLoading ? (
        <section className="rel-ds__table-section" aria-label={t('loading')}>
          <TableSkeleton />
        </section>
      ) : null}

      {!showError && !showLoading ? (
        <section className="rel-ds__table-section" aria-label={t('table.aria')}>
          <div className="rel-ds__main-toolbar">
            <h2>
              {t('table.title')}
              <span className="rel-ds__count">{total}</span>
            </h2>
          </div>
          {pageItems.length === 0 ? (
            emptyState
          ) : (
            <div className="rel-ds__table-wrap">
              <table className="rel-ds__table">
                <colgroup>
                  <col className="col-source" />
                  <col className="col-type" />
                  <col className="col-target" />
                  <col className="col-category" />
                  <col className="col-strength" />
                  <col className="col-score" />
                  <col className="col-status" />
                </colgroup>
                <thead>
                  <tr>
                    <th scope="col">{t('fields.source')}</th>
                    <th scope="col">{t('fields.type')}</th>
                    <th scope="col">{t('fields.target')}</th>
                    <th scope="col">{t('fields.category')}</th>
                    <th scope="col">{t('fields.strength')}</th>
                    <th scope="col">{t('fields.score')}</th>
                    <th scope="col">{t('fields.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {pageItems.map((row) => (
                    <tr
                      key={row.id}
                      className="rel-ds__row"
                      data-testid={`relationships-ds-row-${row.id}`}
                      onClick={() => openRow(row)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          openRow(row);
                        }
                      }}
                      tabIndex={0}
                    >
                      <td>
                        <button
                          type="button"
                          className="rel-ds__entity-link"
                          title={row.source_display_name ?? row.source_entity_id}
                          onClick={(e) => {
                            e.stopPropagation();
                            openEntity(row.source_entity_type, row.source_entity_id);
                          }}
                        >
                          {row.source_display_name ?? row.source_entity_id.slice(0, 8)}
                        </button>
                      </td>
                      <td>{crmLabel(tTypes, row.relationship_type)}</td>
                      <td>
                        <button
                          type="button"
                          className="rel-ds__entity-link"
                          title={row.target_display_name ?? row.target_entity_id}
                          onClick={(e) => {
                            e.stopPropagation();
                            openEntity(row.target_entity_type, row.target_entity_id);
                          }}
                        >
                          {row.target_display_name ?? row.target_entity_id.slice(0, 8)}
                        </button>
                      </td>
                      <td>{crmLabel(tCategories, row.category)}</td>
                      <td>
                        <StatusChip tone={strengthTone(row.strength)}>
                          {crmLabel(tStrengths, row.strength)}
                        </StatusChip>
                      </td>
                      <td>
                        <ScoreBadge
                          score={row.relationship_score}
                          tooltip={t('score.tooltip')}
                        />
                      </td>
                      <td>
                        <StatusChip tone={statusTone(row.status)}>
                          {crmLabel(tStatuses, row.status)}
                        </StatusChip>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ) : null}

      {!showError && !showLoading && total > 0 ? (
        <div className="rel-ds__pagination">
          <span>
            {t('pagination', {
              page: pageSafe,
              pages,
              total,
            })}
          </span>
          <div>
            <Button
              variant="secondary"
              size="sm"
              disabled={pageSafe <= 1}
              onClick={() =>
                setApplied((prev) => ({
                  ...prev,
                  page: Math.max(1, prev.page - 1),
                }))
              }
            >
              {t('prevPage')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={pageSafe >= pages}
              onClick={() =>
                setApplied((prev) => ({
                  ...prev,
                  page: Math.min(pages, prev.page + 1),
                }))
              }
            >
              {t('nextPage')}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export function RelationshipsDsWorkspace() {
  const t = useTranslations('common');
  return (
    <Suspense
      fallback={
        <div className="rel-ds">
          <div className="rel-ds__empty">{t('loading')}</div>
        </div>
      }
    >
      <RelationshipsDsWorkspaceInner />
    </Suspense>
  );
}
