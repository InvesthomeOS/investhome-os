'use client';

import { useMemo, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { Button, Input, Select } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';
import { fetchAgreements, type CrmAgreementSummary } from '@/workspaces/crm/api/agreements';
import { salesDetailUrl } from '@/workspaces/crm/contact-card/pilot-people';

import { AgreementsActivities } from './agreements-activities';
import { AgreementsCalendar } from './agreements-calendar';
import { AgreementsKanban } from './agreements-kanban';
import { AgreementsList } from './agreements-list';
import {
  PROJECT_SELECTOR,
  kanbanColumns,
  matchesQuery,
  normalizeStage,
  stageBucket,
  type StageBucket,
} from './agreements-stage';

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
  const [projectGroup, setProjectGroup] = useState(searchParams.get('project') || '');
  const [view, setView] = useState<ViewId>('kanban');
  const [queryText, setQueryText] = useState('');
  const [stage, setStage] = useState('');
  const [status, setStatus] = useState('');
  const [responsible, setResponsible] = useState('');
  const [bucket, setBucket] = useState<StageBucket>('all');

  const query = useQuery({
    queryKey: ['crm', 'agreements', projectGroup],
    queryFn: () =>
      fetchAgreements({
        project_group: projectGroup || undefined,
        page: 1,
        page_size: 200,
      }),
  });

  const items = query.data?.items ?? [];
  const groups = useMemo(() => {
    const api = query.data?.project_groups ?? [];
    return PROJECT_SELECTOR.map((item) => ({
      id: item.id,
      label: item.label,
      apiLabel: api.find((group) => group.id === item.id)?.label || item.label,
    }));
  }, [query.data?.project_groups]);

  const stages = useMemo(() => {
    return kanbanColumns(items);
  }, [items]);

  const responsibles = useMemo(() => {
    return [...new Set(items.map((item) => item.responsible_name).filter(Boolean) as string[])].sort((a, b) =>
      a.localeCompare(b, 'tr'),
    );
  }, [items]);

  const baseItems = useMemo(() => {
    return items.filter((row) => {
      if (!matchesQuery(row, queryText)) return false;
      if (status && row.status !== status) return false;
      if (responsible && row.responsible_name !== responsible) return false;
      if (stage && normalizeStage(row.stage_label) !== stage) return false;
      return true;
    });
  }, [items, queryText, responsible, stage, status]);

  const kpis = useMemo(() => {
    return {
      total: baseItems.length,
      won: baseItems.filter((row) => stageBucket(row.stage_label) === 'won').length,
      progress: baseItems.filter((row) => stageBucket(row.stage_label) === 'progress').length,
      capital: baseItems.filter((row) => stageBucket(row.stage_label) === 'capital').length,
      unstaged: baseItems.filter((row) => stageBucket(row.stage_label) === 'unstaged').length,
    };
  }, [baseItems]);

  const visibleItems = useMemo(() => {
    if (bucket === 'all') return baseItems;
    return baseItems.filter((row) => stageBucket(row.stage_label) === bucket);
  }, [baseItems, bucket]);

  const hasFilters = Boolean(queryText || projectGroup || stage || status || responsible || bucket !== 'all');

  const resetFilters = () => {
    setQueryText('');
    setProjectGroup('');
    setStage('');
    setStatus('');
    setResponsible('');
    setBucket('all');
  };

  const openPurchase = (row: CrmAgreementSummary) => {
    router.push(salesDetailUrl(row.contact_id, row.id));
  };

  const openAgreement = (agreementId: string, contactId: string) => {
    router.push(salesDetailUrl(contactId, agreementId));
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
          value={queryText}
          placeholder={t('searchPlaceholder')}
          onChange={(event) => setQueryText(event.target.value)}
        />
        <Select
          label={t('projectFilter')}
          value={projectGroup}
          data-testid="agreements-project-filter"
          onChange={(event) => setProjectGroup(event.target.value)}
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
        <Select label={t('statusFilter')} value={status} onChange={(event) => setStatus(event.target.value)}>
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
            {query.data ? t('count', { count: visibleItems.length }) : t('loading')}
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

      {query.isLoading ? <p>{t('loading')}</p> : null}
      {query.isError ? <p>{t('loadError')}</p> : null}

      {!query.isLoading && !query.isError && visibleItems.length === 0 && (view === 'kanban' || view === 'list') ? (
        <div className="ctc-ds__empty" data-testid="crm-agreements-empty">
          <strong>{t('emptyTitle')}</strong>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : null}

      {!query.isLoading && !query.isError && visibleItems.length > 0 && view === 'kanban' ? (
        <AgreementsKanban items={visibleItems} onOpen={openPurchase} />
      ) : null}
      {!query.isLoading && !query.isError && visibleItems.length > 0 && view === 'list' ? (
        <AgreementsList items={visibleItems} onOpen={openPurchase} />
      ) : null}
      {!query.isLoading && !query.isError && view === 'activities' ? (
        <AgreementsActivities projectGroup={projectGroup} items={items} onOpenAgreement={openAgreement} />
      ) : null}
      {!query.isLoading && !query.isError && view === 'calendar' ? (
        <AgreementsCalendar projectGroup={projectGroup} items={items} onOpenAgreement={openAgreement} />
      ) : null}
    </div>
  );
}
