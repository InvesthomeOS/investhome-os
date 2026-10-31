'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import type { Route } from 'next';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { LIST_SEARCH_DEBOUNCE_MS, useDebouncedQueryParam, useListQueryPatch } from '@/lib/crm/list-query';
import {
  fetchAgreementBoard,
  fetchAgreementBoardCards,
  fetchAgreements,
  type CrmAgreementStatus,
  type CrmAgreementSummary,
} from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';

import { AgreementsActivities } from './agreements-activities';
import { AgreementsCalendar } from './agreements-calendar';
import { AgreementsKanban } from './agreements-kanban';
import { AgreementsList } from './agreements-list';
import { PROJECT_SELECTOR, stageBucket, type StageBucket } from './agreements-stage';

import '../../contacts/_components/ds/contacts-ds.css';
import '@/workspaces/crm/contact-card/contact-card.css';
import './agreements-workspace.css';

const VIEWS = [
  { id: 'kanban', labelKey: 'views.kanban' },
  { id: 'list', labelKey: 'views.list' },
  { id: 'activities', labelKey: 'views.activities' },
  { id: 'calendar', labelKey: 'views.calendar' },
] as const;

type ViewId = (typeof VIEWS)[number]['id'];

const AGREEMENT_LIST_DEFAULTS = { page: '1', size: '10', sort: 'agreement_date', dir: 'desc' };
const AGREEMENT_PAGE_SIZES = [10, 25, 50] as const;

const STATUS_OPTIONS = [
  { id: '', labelKey: 'statusOptions.allStatus' },
  { id: 'active', labelKey: 'statusOptions.statusActive' },
  { id: 'completed', labelKey: 'statusOptions.statusCompleted' },
  { id: 'cancelled', labelKey: 'statusOptions.statusCancelled' },
] as const;

export function AgreementsWorkspace() {
  const t = useTranslations('crm.agreements');
  const router = useRouter();
  const searchParams = useSearchParams();
  const patch = useListQueryPatch(AGREEMENT_LIST_DEFAULTS);
  const projectGroup = searchParams.get('project') ?? '';
  const statusParam = searchParams.get('status') ?? '';
  const status: '' | CrmAgreementStatus =
    statusParam === 'active' || statusParam === 'completed' || statusParam === 'cancelled' ? statusParam : '';
  const [queryDraft, setQueryDraft] = useDebouncedQueryParam('q', LIST_SEARCH_DEBOUNCE_MS, { resetPage: true });
  const queryText = searchParams.get('q') ?? '';
  const listPage = Math.max(1, Number(searchParams.get('page') || '1') || 1);
  const sizeParam = Number(searchParams.get('size'));
  const listPageSize = AGREEMENT_PAGE_SIZES.includes(sizeParam as (typeof AGREEMENT_PAGE_SIZES)[number])
    ? sizeParam
    : 10;
  const listSort = searchParams.get('sort') === 'hemen_kira' ? 'hemen_kira' : 'agreement_date';
  const listDir = searchParams.get('dir') === 'asc' ? 'asc' : 'desc';
  const [view, setView] = useState<ViewId>('kanban');
  const [stage, setStage] = useState('');
  const [responsible, setResponsible] = useState('');
  const [bucket, setBucket] = useState<StageBucket>('all');

  const boardQuery = useQuery({
    queryKey: ['crm', 'agreements', 'board', projectGroup, status, queryText, stage, responsible],
    queryFn: () =>
      fetchAgreementBoard({
        project_group: projectGroup || undefined,
        status: status || undefined,
        q: queryText.trim() || undefined,
        stage: stage || undefined,
        responsible: responsible || undefined,
      }),
  });
  const [extraCards, setExtraCards] = useState<Record<string, CrmAgreementSummary[]>>({});
  const [loadingStage, setLoadingStage] = useState<string | null>(null);
  const boardFilterKey = `${projectGroup}|${status}|${queryText}|${stage}|${responsible}`;
  const boardFilterRef = useRef(boardFilterKey);
  boardFilterRef.current = boardFilterKey;
  useEffect(() => {
    setExtraCards({});
  }, [boardFilterKey]);

  const listQuery = useQuery({
    queryKey: ['crm', 'agreements', 'list', projectGroup, status, queryText, listPage, listPageSize, listSort, listDir],
    queryFn: () =>
      fetchAgreements({
        project_group: projectGroup || undefined,
        status: status || undefined,
        q: queryText.trim() || undefined,
        page: listPage,
        page_size: listPageSize,
        sort_by: listSort,
        sort_dir: listDir,
      }),
    enabled: view === 'list',
  });

  const groups = useMemo(() => {
    const api = boardQuery.data?.project_groups ?? [];
    return PROJECT_SELECTOR.map((item) => ({
      id: item.id,
      label: item.label,
      apiLabel: api.find((group) => group.id === item.id)?.label || item.label,
    }));
  }, [boardQuery.data?.project_groups]);

  const stages = boardQuery.data?.stages ?? [];
  const responsibles = boardQuery.data?.responsibles ?? [];
  const kpis = boardQuery.data?.kpis ?? { total: 0, won: 0, progress: 0, capital: 0, unstaged: 0 };
  const visibleColumns = useMemo(() => {
    return (boardQuery.data?.columns ?? [])
      .filter((column) => bucket === 'all' || stageBucket(column.stage) === bucket)
      .map((column) => {
        const seen = new Set(column.items.map((item) => item.id));
        const items = [
          ...column.items,
          ...(extraCards[column.stage] ?? []).filter((item) => !seen.has(item.id)),
        ];
        return {
          stage: column.stage,
          total: column.total,
          pageSize: column.page_size,
          items,
          hasMore: items.length < column.total,
          loadingMore: loadingStage === column.stage,
        };
      });
  }, [boardQuery.data?.columns, bucket, extraCards, loadingStage]);
  const visibleTotal = visibleColumns.reduce((sum, column) => sum + column.total, 0);

  const hasFilters = Boolean(
    queryDraft || queryText || projectGroup || stage || status || responsible || bucket !== 'all',
  );

  const resetFilters = () => {
    setQueryDraft('');
    setStage('');
    setResponsible('');
    setBucket('all');
    patch({ q: null, project: null, status: null, page: null, sort: null, dir: null, size: null });
  };

  const sortList = (column: 'tarih' | 'hemenKira') => {
    const api = column === 'hemenKira' ? 'hemen_kira' : 'agreement_date';
    const nextDir = listSort === api ? (listDir === 'asc' ? 'desc' : 'asc') : api === 'agreement_date' ? 'desc' : 'asc';
    patch({ sort: api, dir: nextDir, page: null });
  };

  const openPurchase = (row: CrmAgreementSummary) => {
    router.push(salesDetailUrl(row.contact_id, row.id) as Route);
  };

  const openAgreement = (agreementId: string, contactId: string) => {
    router.push(salesDetailUrl(contactId, agreementId) as Route);
  };

  const loadMore = async (columnStage: string) => {
    const column = visibleColumns.find((item) => item.stage === columnStage);
    if (!column || !column.hasMore || loadingStage) return;
    const nextPage = Math.floor(column.items.length / column.pageSize) + 1;
    const requestedKey = boardFilterKey;
    setLoadingStage(columnStage);
    try {
      const data = await fetchAgreementBoardCards({
        project_group: projectGroup || undefined,
        status: status || undefined,
        q: queryText.trim() || undefined,
        stage: columnStage,
        responsible: responsible || undefined,
        page: nextPage,
        page_size: column.pageSize,
      });
      setExtraCards((current) => {
        if (boardFilterRef.current !== requestedKey) return current;
        const previous = current[columnStage] ?? [];
        const seen = new Set(column.items.map((item) => item.id));
        const added = data.items.filter((item) => !seen.has(item.id));
        return { ...current, [columnStage]: [...previous, ...added] };
      });
    } finally {
      setLoadingStage(null);
    }
  };

  return (
    <div className="ctc-ds crm-agreements" data-testid="crm-agreements-workspace">
      <header className="crm-agreements__header">
        <div>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        <div className="crm-agreements-views" role="tablist" aria-label={t('viewsLabel')}>
          {VIEWS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={view === item.id}
              className={view === item.id ? 'is-active' : undefined}
              data-testid={`agreements-view-${item.id}`}
              onClick={() => setView(item.id)}
            >
              {t(item.labelKey)}
            </button>
          ))}
        </div>
      </header>

      <section className="crm-agreements-filtercard" aria-label={t('filtersTitle')}>
        <Input
          label={t('searchLabel')}
          value={queryDraft}
          placeholder={t('searchPlaceholder')}
          onChange={(event) => setQueryDraft(event.target.value)}
        />
        <Select
          label={t('projectFilter')}
          value={projectGroup}
          data-testid="agreements-project-filter"
          onChange={(event) => patch({ project: event.target.value, page: null })}
        >
          <option value="">{t('allProjects')}</option>
          {groups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.label}
            </option>
          ))}
        </Select>
        <Select label={t('stageFilter')} value={stage} onChange={(event) => setStage(event.target.value)}>
          <option value="">{t('allStages')}</option>
          {stages.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </Select>
        <Select
          label={t('statusFilter')}
          value={status}
          onChange={(event) => patch({ status: event.target.value, page: null })}
        >
          {STATUS_OPTIONS.map((item) => (
            <option key={item.id} value={item.id}>
              {t(item.labelKey)}
            </option>
          ))}
        </Select>
        <Select
          label={t('responsibleFilter')}
          value={responsible}
          onChange={(event) => setResponsible(event.target.value)}
        >
          <option value="">{t('allResponsible')}</option>
          {responsibles.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </Select>
        <div className="crm-agreements-filtercard__actions">
          <Button type="button" variant="secondary" size="sm" onClick={resetFilters} disabled={!hasFilters}>
            {t('resetFilters')}
          </Button>
          <p className="crm-agreements-count" data-testid="agreements-count">
            {view === 'list'
              ? listQuery.data
                ? t('count', { count: listQuery.data.total })
                : t('loading')
              : boardQuery.data
                ? t('count', { count: visibleTotal })
                : t('loading')}
          </p>
        </div>
      </section>

      <section className="crm-agreements-kpis" aria-label={t('kpis.aria')}>
        {(
          [
            { id: 'all', value: kpis.total, label: t('kpis.total'), icon: 'documents' as const },
            { id: 'won', value: kpis.won, label: t('kpis.won'), icon: 'check' as const },
            { id: 'progress', value: kpis.progress, label: t('kpis.progress'), icon: 'clock' as const },
            { id: 'capital', value: kpis.capital, label: t('kpis.capital'), icon: 'trendingUp' as const },
            { id: 'unstaged', value: kpis.unstaged, label: t('kpis.unstaged'), icon: 'alert' as const },
          ] as const
        ).map((item) => (
          <button
            key={item.id}
            type="button"
            className={bucket === item.id ? 'is-active' : undefined}
            onClick={() => setBucket(item.id)}
          >
            <span className="crm-agreements-kpis__icon" aria-hidden>
              <IhIcon name={item.icon} size={16} />
            </span>
            <strong>{item.value}</strong>
            <span>{item.label}</span>
          </button>
        ))}
      </section>

      {view === 'list' && listQuery.isLoading ? <p>{t('loading')}</p> : null}
      {view !== 'list' && boardQuery.isLoading ? <p>{t('loading')}</p> : null}
      {view === 'list' && listQuery.isError ? <p>{t('loadError')}</p> : null}
      {view !== 'list' && boardQuery.isError ? <p>{t('loadError')}</p> : null}

      {view === 'list' && !listQuery.isLoading && !listQuery.isError && (listQuery.data?.items.length ?? 0) === 0 ? (
        <div className="ctc-ds__empty" data-testid="crm-agreements-empty">
          <strong>{t('emptyTitle')}</strong>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : null}
      {view === 'kanban' && !boardQuery.isLoading && !boardQuery.isError && visibleTotal === 0 ? (
        <div className="ctc-ds__empty" data-testid="crm-agreements-empty">
          <strong>{t('emptyTitle')}</strong>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : null}

      {!boardQuery.isLoading && !boardQuery.isError && visibleTotal > 0 && view === 'kanban' ? (
        <AgreementsKanban columns={visibleColumns} onOpen={openPurchase} onLoadMore={loadMore} />
      ) : null}
      {view === 'list' && !listQuery.isLoading && !listQuery.isError && (listQuery.data?.items.length ?? 0) > 0 ? (
        <AgreementsList
          items={listQuery.data?.items ?? []}
          onOpen={openPurchase}
          sortKey={listSort}
          sortDir={listDir}
          onSort={sortList}
          page={listPage}
          pages={listQuery.data?.pages ?? 1}
          total={listQuery.data?.total ?? 0}
          pageSize={listPageSize}
          onPage={(next) => patch({ page: String(next) })}
          onPageSize={(next) => patch({ size: String(next), page: null })}
        />
      ) : null}
      {!boardQuery.isLoading && !boardQuery.isError && view === 'activities' ? (
        <AgreementsActivities
          projectGroup={projectGroup}
          contacts={boardQuery.data?.contacts ?? []}
          responsibles={responsibles}
          onOpenAgreement={openAgreement}
        />
      ) : null}
      {!boardQuery.isLoading && !boardQuery.isError && view === 'calendar' ? (
        <AgreementsCalendar
          projectGroup={projectGroup}
          contacts={boardQuery.data?.contacts ?? []}
          latestAgreementDate={boardQuery.data?.latest_agreement_date ?? null}
          onOpenAgreement={openAgreement}
        />
      ) : null}
    </div>
  );
}
