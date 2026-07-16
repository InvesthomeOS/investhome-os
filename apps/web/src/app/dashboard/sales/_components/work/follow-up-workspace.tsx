'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, ErrorState, LoadingState } from '@investhome/ui';

import { hasPermission } from '@/lib/api/auth';
import {
  completeWorkItem,
  createWorkItem,
  fetchCalendarEvents,
  fetchWorkDashboardKpis,
  fetchWorkItem,
  fetchWorkView,
  updateWorkItem,
  type WorkDashboardKpis,
  type WorkItem,
  type WorkItemInput,
  type WorkViewName,
  type CalendarEvent,
} from '@/lib/api/work-items';
import { useAuth } from '@/lib/auth/auth-context';
import { useWorkItemLabels } from '@/lib/i18n/work-item-labels';

import { CompleteWorkItemModal } from './complete-work-item-modal';
import { FollowUpCenterHome } from './follow-up-center-home';
import { InternalCalendarView } from './internal-calendar-view';
import { TeamWorkView } from './team-work-view';
import { WorkItemDetailDrawer } from './work-item-detail-drawer';
import { WorkItemFormModal } from './work-item-form-modal';
import { WorkItemList } from './work-item-list';

type LayoutMode = 'list' | 'calendar' | 'team';

export function FollowUpWorkspace() {
  const t = useTranslations('work');
  const { user } = useAuth();
  const { viewOptions, getViewLabel } = useWorkItemLabels();

  const [kpis, setKpis] = useState<WorkDashboardKpis | null>(null);
  const [items, setItems] = useState<WorkItem[]>([]);
  const [calendarEvents, setCalendarEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<WorkViewName>('today');
  const [layout, setLayout] = useState<LayoutMode>('list');
  const [selected, setSelected] = useState<WorkItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [completeOpen, setCompleteOpen] = useState(false);
  const [editItem, setEditItem] = useState<WorkItem | null>(null);

  const canView = user ? hasPermission(user, 'work', 'view') : false;
  const canCreate = user ? hasPermission(user, 'work', 'create') : false;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpiData, viewData, calData] = await Promise.all([
        fetchWorkDashboardKpis(),
        layout === 'team'
          ? fetchWorkView('team_work')
          : fetchWorkView(activeView),
        fetchCalendarEvents(),
      ]);
      setKpis(kpiData);
      setItems(viewData.items);
      setCalendarEvents(calData);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [activeView, layout, t]);

  useEffect(() => {
    if (canView) void loadData();
  }, [canView, loadData]);

  async function handleCreate(payload: WorkItemInput) {
    if (editItem) {
      await updateWorkItem(editItem.id, payload);
    } else {
      await createWorkItem(payload);
    }
    await loadData();
  }

  async function handleComplete(outcome: string, createNext: boolean) {
    if (!selected) return;
    await completeWorkItem(selected.id, {
      outcome,
      next_follow_up: createNext ? { title: `Follow-up: ${selected.title}` } : undefined,
    });
    setDrawerOpen(false);
    await loadData();
  }

  async function handleSelect(item: WorkItem) {
    const detail = await fetchWorkItem(item.id);
    setSelected(detail);
    setDrawerOpen(true);
  }

  if (!canView) {
    return <ErrorState title={t('title')} message={t('loadError')} />;
  }

  return (
    <div className="sales-work-page">
      <header className="sales-work-page__header">
        <div>
          <p className="sales-work-page__eyebrow">
            <Link href={'/dashboard/sales' as Route}>{t('nav')}</Link>
          </p>
          <h1>{t('title')}</h1>
          <p>{t('subtitle')}</p>
        </div>
        {canCreate && (
          <Button variant="primary" onClick={() => { setEditItem(null); setFormOpen(true); }}>
            {t('createButton')}
          </Button>
        )}
      </header>

      <FollowUpCenterHome
        kpis={kpis}
        loading={loading}
        activeView={activeView}
        onSelectView={(view) => { setLayout('list'); setActiveView(view as WorkViewName); }}
      />

      <div className="sales-work-page__toolbar">
        <div className="sales-work-page__views">
          {viewOptions.map((view) => (
            <button
              key={view}
              type="button"
              className={activeView === view && layout === 'list' ? 'sales-work-page__view--active' : undefined}
              onClick={() => { setLayout('list'); setActiveView(view); }}
            >
              {getViewLabel(view)}
            </button>
          ))}
        </div>
        <div className="sales-work-page__layouts">
          {(['list', 'calendar', 'team'] as LayoutMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={layout === mode ? 'sales-work-page__layout--active' : undefined}
              onClick={() => setLayout(mode)}
            >
              {t(`layout.${mode}` as never)}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <ErrorState
          title={t('title')}
          message={error}
          action={
            <button type="button" className="leads__button leads__button--secondary" onClick={() => void loadData()}>
              Retry
            </button>
          }
        />
      )}
      {!error && layout === 'list' && (
        <WorkItemList
          items={items}
          loading={loading}
          selectedId={selected?.id ?? null}
          onSelect={(item) => void handleSelect(item)}
        />
      )}
      {!error && layout === 'calendar' && (
        <InternalCalendarView
          events={calendarEvents}
          loading={loading}
          onSelectEvent={(event) => void fetchWorkItem(event.id).then((item) => { setSelected(item); setDrawerOpen(true); })}
        />
      )}
      {!error && layout === 'team' && <TeamWorkView items={items} loading={loading} />}

      <WorkItemDetailDrawer
        item={selected}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onComplete={() => setCompleteOpen(true)}
        onEdit={(item) => { setEditItem(item); setFormOpen(true); }}
      />
      <WorkItemFormModal
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditItem(null); }}
        onSubmit={handleCreate}
        initial={editItem}
      />
      <CompleteWorkItemModal
        item={selected}
        open={completeOpen}
        onClose={() => setCompleteOpen(false)}
        onSubmit={handleComplete}
      />
    </div>
  );
}
