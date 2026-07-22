'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, EmptyState, LoadingState, StatusChip } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canTransitionStage,
  changeOpportunityStage,
  fetchOpportunities,
  formatMoney,
  formatShortDate,
  stageRequiresModal,
  type OpportunityStage,
  type SalesOpportunity,
} from '@/lib/api/sales';
import { useSalesLabels } from '@/lib/i18n/sales-labels';

import { CrmAnalyticsStrip } from './crm-analytics-strip';
import { CrmDrawerField, CrmRecordDrawer } from './crm-record-drawer';

type ViewMode = 'board' | 'list';

/** UI-only board columns inspired by brief stages — maps onto existing OpportunityStage values. */
const BOARD_COLUMNS: {
  id: string;
  dropStage: OpportunityStage;
  stages: OpportunityStage[];
  labelKey: string;
}[] = [
  { id: 'new', dropStage: 'new', stages: ['new'], labelKey: 'stages.newLead' },
  { id: 'qualified', dropStage: 'qualified', stages: ['qualified'], labelKey: 'stages.qualified' },
  {
    id: 'meeting',
    dropStage: 'meeting_scheduled',
    stages: ['meeting_scheduled', 'meeting_completed'],
    labelKey: 'stages.meeting',
  },
  {
    id: 'reservation',
    dropStage: 'reservation',
    stages: [
      'inventory_matching',
      'proposal_preparation',
      'proposal_sent',
      'negotiation',
      'soft_hold',
      'reservation',
      'deposit_pending',
    ],
    labelKey: 'stages.reservation',
  },
  { id: 'contract', dropStage: 'contract', stages: ['contract'], labelKey: 'stages.contract' },
  {
    id: 'closing',
    dropStage: 'closing_handoff',
    stages: ['closing_handoff'],
    labelKey: 'stages.closing',
  },
  { id: 'won', dropStage: 'won', stages: ['won'], labelKey: 'stages.won' },
  {
    id: 'lost',
    dropStage: 'lost',
    stages: ['lost', 'dormant', 'cancelled'],
    labelKey: 'stages.lost',
  },
];

function makeDemoOpps(): SalesOpportunity[] {
  const base = (
    partial: Pick<SalesOpportunity, 'id' | 'stage' | 'display_id' | 'expected_revenue' | 'probability' | 'notes'>,
  ): SalesOpportunity => ({
    id: partial.id,
    opportunity_code: partial.display_id ?? partial.id.toUpperCase(),
    display_id: partial.display_id,
    lead_id: null,
    party_id: 'demo-party',
    party_type: 'lead',
    assigned_sales_user_id: null,
    stage: partial.stage,
    probability: partial.probability,
    expected_close_date: '2026-08-15',
    expected_revenue: partial.expected_revenue,
    currency: 'TRY',
    priority: 'medium',
    source: 'Website',
    current_risks: null,
    next_action: null,
    next_action_date: null,
    last_contact_at: '2026-07-18T12:00:00Z',
    notes: partial.notes,
    loss_reason: null,
    loss_notes: null,
    dormant_review_date: null,
    cancelled_reason: null,
    reservation_id: null,
    is_demo: true,
    archived_at: null,
    created_by_id: null,
    created_at: '2026-06-01T10:00:00Z',
    updated_at: '2026-07-18T12:00:00Z',
  });

  return [
    base({
      id: 'demo-opp-1',
      stage: 'new',
      notes: 'Marina — yeni lead',
      expected_revenue: '420000',
      probability: 15,
      display_id: 'OPP-1001',
    }),
    base({
      id: 'demo-opp-2',
      stage: 'qualified',
      notes: 'Skyline — nitelikli',
      expected_revenue: '980000',
      probability: 35,
      display_id: 'OPP-1002',
    }),
    base({
      id: 'demo-opp-3',
      stage: 'meeting_scheduled',
      notes: 'Gulf — toplantı',
      expected_revenue: '1250000',
      probability: 45,
      display_id: 'OPP-1003',
    }),
    base({
      id: 'demo-opp-4',
      stage: 'reservation',
      notes: 'Carter — rezervasyon',
      expected_revenue: '2100000',
      probability: 70,
      display_id: 'OPP-1004',
    }),
    base({
      id: 'demo-opp-5',
      stage: 'contract',
      notes: 'Demir — sözleşme',
      expected_revenue: '1750000',
      probability: 85,
      display_id: 'OPP-1005',
    }),
    base({
      id: 'demo-opp-6',
      stage: 'won',
      notes: 'Kazanılan — villa',
      expected_revenue: '3200000',
      probability: 100,
      display_id: 'OPP-1006',
    }),
  ];
}

function oppLabel(opp: SalesOpportunity): string {
  return opp.notes?.trim() || opp.display_id || opp.opportunity_code;
}

export function CrmPipelineWorkspace() {
  const t = useTranslations('crm.g2.pipeline');
  const tDrawer = useTranslations('crm.g2.drawer');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { getStageLabel, getPriorityLabel } = useSalesLabels();
  const { user } = useAuth();

  const canView = user
    ? hasPermission(user, 'sales', 'view') ||
      hasPermission(user, 'sales', 'view_pipeline') ||
      hasPermission(user, 'leads', 'view')
    : false;
  const canChangeStage = user ? hasPermission(user, 'sales', 'change_stage') : false;

  const [items, setItems] = useState<SalesOpportunity[]>([]);
  const [usingDemo, setUsingDemo] = useState(false);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>('board');
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [overCol, setOverCol] = useState<string | null>(null);
  const [selected, setSelected] = useState<SalesOpportunity | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [quickEditId, setQuickEditId] = useState<string | null>(null);
  const [quickProb, setQuickProb] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchOpportunities({
        offset: 0,
        limit: 200,
        sort_by: 'updated_at',
        sort_dir: 'desc',
        include_archived: false,
      });
      if (!res.items.length) {
        setItems(makeDemoOpps());
        setUsingDemo(true);
      } else {
        setItems(res.items);
        setUsingDemo(false);
      }
    } catch {
      setItems(makeDemoOpps());
      setUsingDemo(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!canView) {
      setLoading(false);
      return;
    }
    void load();
  }, [canView, load]);

  const byColumn = useMemo(() => {
    const map: Record<string, SalesOpportunity[]> = {};
    for (const col of BOARD_COLUMNS) map[col.id] = [];
    for (const opp of items) {
      const col = BOARD_COLUMNS.find((c) => c.stages.includes(opp.stage));
      if (col) map[col.id]!.push(opp);
    }
    return map;
  }, [items]);

  const totals = useMemo(() => {
    const revenue = items.reduce((sum, o) => sum + (Number(o.expected_revenue) || 0), 0);
    const weighted = items.reduce(
      (sum, o) => sum + ((Number(o.expected_revenue) || 0) * (o.probability || 0)) / 100,
      0,
    );
    return { count: items.length, revenue, weighted };
  }, [items]);

  const moveTo = async (id: string, colId: string) => {
    const col = BOARD_COLUMNS.find((c) => c.id === colId);
    const opp = items.find((o) => o.id === id);
    if (!col || !opp || opp.stage === col.dropStage) return;

    // Local demo / optimistic preview when demo or modal-required stages
    if (usingDemo || id.startsWith('demo-') || stageRequiresModal(col.dropStage)) {
      setItems((prev) =>
        prev.map((o) => (o.id === id ? { ...o, stage: col.dropStage, probability: o.probability } : o)),
      );
      if (stageRequiresModal(col.dropStage) && !usingDemo) {
        setToast(t('stageNeedsConfirm'));
      }
      return;
    }

    if (!canChangeStage) {
      setToast(t('noStagePermission'));
      return;
    }

    if (!canTransitionStage(opp.stage, col.dropStage)) {
      setToast(t('invalidTransition'));
      return;
    }

    const prev = items;
    setItems((cur) => cur.map((o) => (o.id === id ? { ...o, stage: col.dropStage } : o)));
    try {
      const updated = await changeOpportunityStage(id, { stage: col.dropStage });
      setItems((cur) => cur.map((o) => (o.id === id ? updated : o)));
    } catch {
      setItems(prev);
      setToast(t('stageError'));
    }
  };

  const saveQuickProb = () => {
    if (!quickEditId) return;
    const n = Number(quickProb);
    if (Number.isFinite(n) && n >= 0 && n <= 100) {
      setItems((prev) => prev.map((o) => (o.id === quickEditId ? { ...o, probability: n } : o)));
    }
    setQuickEditId(null);
    setQuickProb('');
  };

  if (!user) return <LoadingState label={tCommon('loading')} />;
  if (!canView) return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  if (loading) return <LoadingState label={t('loading')} variant="skeleton" lines={6} />;

  return (
    <div className="crm-g2-pipeline" data-testid="crm-g2-pipeline">
      <header className="crm-g2-toolbar">
        <div>
          <p className="crm-g2-toolbar__eyebrow">{t('eyebrow')}</p>
          <h1 className="crm-g2-toolbar__title">{t('title')}</h1>
          <p className="crm-g2-toolbar__subtitle">
            {t('subtitle', {
              count: totals.count,
              revenue: formatMoney(String(totals.revenue), 'TRY', locale),
              weighted: formatMoney(String(Math.round(totals.weighted)), 'TRY', locale),
            })}
            {usingDemo ? ` · ${t('demoBadge')}` : ''}
          </p>
        </div>
        <div className="crm-g2-toolbar__actions">
          <div className="crm-g2-seg" role="group" aria-label={t('viewLabel')}>
            <button
              type="button"
              className={view === 'board' ? 'is-active' : undefined}
              onClick={() => setView('board')}
            >
              {t('board')}
            </button>
            <button
              type="button"
              className={view === 'list' ? 'is-active' : undefined}
              onClick={() => setView('list')}
            >
              {t('list')}
            </button>
          </div>
          <Link href={'/dashboard/sales' as Route} className="ih-btn ih-btn--secondary">
            {t('openSales')}
          </Link>
        </div>
      </header>

      <CrmAnalyticsStrip
        compact
        contactCount={totals.count}
        activityCount={byColumn.meeting?.length ?? 0}
        pipelineValue={formatMoney(String(totals.revenue), 'TRY', locale)}
        pipelineTrend={[2.1, 2.4, 2.8, 3.0, 2.9, 3.3, totals.revenue / 1_000_000 || 3.4]}
      />

      {toast ? (
        <div className="crm-g2-toast" role="status">
          {toast}
          <button type="button" onClick={() => setToast(null)} aria-label={tCommon('close')}>
            ×
          </button>
        </div>
      ) : null}

      {view === 'board' ? (
        <div className="crm-g2-board" role="list" data-testid="crm-g2-board">
          {BOARD_COLUMNS.map((col) => {
            const cards = byColumn[col.id] ?? [];
            const colTotal = cards.reduce((s, c) => s + (Number(c.expected_revenue) || 0), 0);
            return (
              <section
                key={col.id}
                className={`crm-g2-col${overCol === col.id ? ' crm-g2-col--over' : ''}`}
                role="listitem"
                onDragOver={(e) => {
                  e.preventDefault();
                  setOverCol(col.id);
                }}
                onDragLeave={() => setOverCol((cur) => (cur === col.id ? null : cur))}
                onDrop={(e) => {
                  e.preventDefault();
                  if (draggingId) void moveTo(draggingId, col.id);
                  setDraggingId(null);
                  setOverCol(null);
                }}
              >
                <header className="crm-g2-col__head">
                  <div className="crm-g2-col__head-row">
                    <span className="crm-g2-col__name">{t(col.labelKey as 'stages.newLead')}</span>
                    <span className="crm-g2-col__count">{cards.length}</span>
                  </div>
                  <span className="crm-g2-col__total">
                    {formatMoney(String(colTotal), 'TRY', locale)}
                  </span>
                </header>
                <div className="crm-g2-col__cards">
                  {cards.map((opp) => (
                    <article
                      key={opp.id}
                      className={`crm-g2-card${draggingId === opp.id ? ' crm-g2-card--dragging' : ''}`}
                      draggable
                      onDragStart={() => setDraggingId(opp.id)}
                      onDragEnd={() => {
                        setDraggingId(null);
                        setOverCol(null);
                      }}
                      onClick={() => setSelected(opp)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          setSelected(opp);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      data-testid={`crm-g2-opp-${opp.id}`}
                    >
                      <div className="crm-g2-card__top">
                        <h3 className="crm-g2-card__title">{oppLabel(opp)}</h3>
                        <StatusChip tone="default">{getPriorityLabel(opp.priority)}</StatusChip>
                      </div>
                      <p className="crm-g2-card__value">
                        {formatMoney(opp.expected_revenue, opp.currency || 'TRY', locale)}
                        <span> · {opp.probability}%</span>
                      </p>
                      <div className="crm-g2-card__bar" aria-hidden="true">
                        <span style={{ width: `${Math.min(100, opp.probability)}%` }} />
                      </div>
                      <p className="crm-g2-card__meta">
                        {opp.expected_close_date
                          ? formatShortDate(opp.expected_close_date, locale)
                          : '—'}
                        {' · '}
                        {getStageLabel(opp.stage)}
                      </p>
                      <div className="crm-g2-card__actions" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          className="crm-g2-link"
                          onClick={() => {
                            setQuickEditId(opp.id);
                            setQuickProb(String(opp.probability));
                          }}
                        >
                          {t('quickEdit')}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        <div className="crm-g2-table-wrap">
          <table className="crm-g2-table" data-testid="crm-g2-pipeline-list">
            <thead>
              <tr>
                <th>{t('listCols.opportunity')}</th>
                <th>{t('listCols.stage')}</th>
                <th>{t('listCols.revenue')}</th>
                <th>{t('listCols.probability')}</th>
                <th>{t('listCols.closeDate')}</th>
              </tr>
            </thead>
            <tbody>
              {items.map((opp) => (
                <tr key={opp.id} onClick={() => setSelected(opp)}>
                  <td>
                    <strong>{oppLabel(opp)}</strong>
                  </td>
                  <td>{getStageLabel(opp.stage)}</td>
                  <td>{formatMoney(opp.expected_revenue, opp.currency || 'TRY', locale)}</td>
                  <td>{opp.probability}%</td>
                  <td>
                    {opp.expected_close_date ? formatShortDate(opp.expected_close_date, locale) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {quickEditId ? (
        <div className="crm-g2-quickedit" role="dialog" aria-label={t('quickEdit')}>
          <label>
            {t('probability')}
            <input
              type="number"
              min={0}
              max={100}
              value={quickProb}
              onChange={(e) => setQuickProb(e.target.value)}
            />
          </label>
          <Button type="button" onClick={saveQuickProb}>
            {t('save')}
          </Button>
          <Button type="button" variant="ghost" onClick={() => setQuickEditId(null)}>
            {tCommon('cancel')}
          </Button>
        </div>
      ) : null}

      <CrmRecordDrawer
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title={selected ? oppLabel(selected) : ''}
        subtitle={selected ? getStageLabel(selected.stage) : undefined}
        badge={
          selected ? (
            <StatusChip tone="default">{getPriorityLabel(selected.priority)}</StatusChip>
          ) : null
        }
        summary={
          selected ? (
            <dl className="crm-g2-drawer__grid">
              <CrmDrawerField
                label={t('listCols.revenue')}
                value={formatMoney(selected.expected_revenue, selected.currency || 'TRY', locale)}
              />
              <CrmDrawerField label={t('listCols.probability')} value={`${selected.probability}%`} />
              <CrmDrawerField
                label={t('listCols.closeDate')}
                value={
                  selected.expected_close_date
                    ? formatShortDate(selected.expected_close_date, locale)
                    : '—'
                }
              />
              <CrmDrawerField label={t('listCols.stage')} value={getStageLabel(selected.stage)} />
            </dl>
          ) : null
        }
        sections={{
          timeline: <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
          activities: <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
          tasks: <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
          documents: <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
          ai: <p className="crm-g2-drawer__empty">{t('aiHint')}</p>,
          projects: <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
          investors: <p className="crm-g2-drawer__empty">{tDrawer('emptySection')}</p>,
        }}
        footer={
          selected && !selected.id.startsWith('demo-') ? (
            <Link href={`/dashboard/sales?opportunity=${selected.id}` as Route} className="ih-btn">
              {t('openFull')}
            </Link>
          ) : (
            <Button type="button" variant="secondary" onClick={() => setSelected(null)}>
              {tCommon('close')}
            </Button>
          )
        }
      />
    </div>
  );
}
