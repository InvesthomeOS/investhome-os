'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, type ReactNode } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';
import type { CrmDashboardCount, CrmDashboardFeedItem } from '@/workspaces/crm/types';

import { CountBarChart, PetrolDonut } from '../../reports/_components/reports-charts';

const COPY = {
  tr: {
    title: 'Pano',
    subtitle: 'Canlı CRM operasyon özeti. Tahmin, demo metrik veya sahte dönüşüm oranı yok.',
    kpis: 'Operasyon özeti',
    currentPurchases: 'Güncel Satın Alma',
    investors: 'Toplam Yatırımcı',
    activeTasks: 'Aktif Görev',
    openLeads: 'Açık Lead',
    docsReview: 'İnceleme Gereken Belge',
    matchesPending: 'Eşleşme Bekleyen',
    scope: 'Satın alma kapsamı',
    current: 'Güncel',
    historical: 'Geçmiş birim değişimi',
    totalRows: 'Toplam satır',
    scopeHint: 'Geçmiş birim değişimleri güncel grafiklere dahil edilmez.',
    charts: 'Operasyon grafikleri',
    byProject: 'Projeye Göre Güncel Satın Alma',
    byMonth: 'Aylık Satın Alma',
    taskStatus: 'Görev Durumu',
    channels: 'İletişim Kanalları',
    leadPipeline: 'Lead Pipeline',
    docStatus: 'Belge Durumu',
    panels: 'Operasyon listeleri',
    recentActivities: 'Son Aktiviteler',
    upcomingTasks: 'Yaklaşan Görevler',
    recentDocs: 'Son Eklenen Belgeler',
    reviewQueue: 'İnceleme Gerekenler',
    recentLeads: 'Son Leadler',
    viewAll: 'Tümü',
    empty: 'Canlı kayıt yok.',
    loadFailed: 'Pano yüklenemedi.',
    accessDenied: 'Bu çalışma alanını görüntüleme yetkiniz yok.',
  },
  en: {
    title: 'Dashboard',
    subtitle: 'Live CRM operations summary. No forecasts, demo metrics, or invented conversion rates.',
    kpis: 'Operations summary',
    currentPurchases: 'Current purchases',
    investors: 'Investors',
    activeTasks: 'Active tasks',
    openLeads: 'Open leads',
    docsReview: 'Documents needing review',
    matchesPending: 'Matches pending',
    scope: 'Purchase scope',
    current: 'Current',
    historical: 'Historical unit change',
    totalRows: 'Total rows',
    scopeHint: 'Historical unit changes are excluded from current charts.',
    charts: 'Operations charts',
    byProject: 'Current purchases by project',
    byMonth: 'Monthly purchases',
    taskStatus: 'Task status',
    channels: 'Communication channels',
    leadPipeline: 'Lead pipeline',
    docStatus: 'Document status',
    panels: 'Operations lists',
    recentActivities: 'Recent activities',
    upcomingTasks: 'Upcoming tasks',
    recentDocs: 'Recent documents',
    reviewQueue: 'Needs review',
    recentLeads: 'Recent leads',
    viewAll: 'View all',
    empty: 'No live records.',
    loadFailed: 'Dashboard failed to load.',
    accessDenied: 'You do not have access to this workspace.',
  },
};

const KPI_ITEMS = [
  { key: 'current_purchases', href: '/workspaces/crm/agreements', labelKey: 'currentPurchases' },
  { key: 'investors', href: '/workspaces/crm/investors', labelKey: 'investors' },
  { key: 'active_tasks', href: '/workspaces/crm/tasks', labelKey: 'activeTasks' },
  { key: 'open_leads', href: '/workspaces/crm/leads', labelKey: 'openLeads' },
  { key: 'documents_review', href: '/workspaces/crm/documents?scope=unresolved', labelKey: 'docsReview' },
  { key: 'matches_pending', href: '/workspaces/crm/matches', labelKey: 'matchesPending' },
] as const;

const STAGE_LABEL: Record<string, { tr: string; en: string }> = {
  yeni: { tr: 'Yeni', en: 'New' },
  contacted: { tr: 'İletişim', en: 'Contacted' },
  following: { tr: 'Takipte', en: 'Following' },
  qualified: { tr: 'Nitelikli', en: 'Qualified' },
  converted: { tr: 'Satışa döndü', en: 'Converted' },
  unqualified: { tr: 'Niteliksiz', en: 'Unqualified' },
};

const TASK_LABEL: Record<string, { tr: string; en: string }> = {
  active: { tr: 'Aktif', en: 'Active' },
  in_progress: { tr: 'Devam ediyor', en: 'In progress' },
  completed: { tr: 'Tamamlandı', en: 'Completed' },
  overdue: { tr: 'Geciken', en: 'Overdue' },
};

const CHANNEL_LABEL: Record<string, { tr: string; en: string }> = {
  email: { tr: 'E-posta', en: 'Email' },
  whatsapp: { tr: 'WhatsApp', en: 'WhatsApp' },
  call: { tr: 'Arama', en: 'Call' },
  meeting: { tr: 'Toplantı', en: 'Meeting' },
  task: { tr: 'Görev', en: 'Task' },
  note: { tr: 'Not', en: 'Note' },
};

const DOC_LABEL: Record<string, { tr: string; en: string }> = {
  person: { tr: 'Kişi', en: 'Person' },
  purchase: { tr: 'Satın alma', en: 'Purchase' },
  hidden: { tr: 'Gizli', en: 'Hidden' },
  unresolved: { tr: 'İnceleme', en: 'Review' },
};

const PANEL_LINKS = {
  recent_activities: '/workspaces/crm/activities',
  upcoming_tasks: '/workspaces/crm/tasks',
  recent_documents: '/workspaces/crm/documents',
  review_queue: '/workspaces/crm/documents?scope=unresolved',
  recent_leads: '/workspaces/crm/leads',
} as const;

function localize(rows: CrmDashboardCount[], map: Record<string, { tr: string; en: string }>, locale: string) {
  const lang = locale.startsWith('tr') ? 'tr' : 'en';
  return rows.map((row) => ({
    ...row,
    label: map[row.key]?.[lang] ?? row.label,
  }));
}

function ChartCard({
  title,
  href,
  viewAll,
  children,
  empty,
  hasData,
}: {
  title: string;
  href: string;
  viewAll: string;
  children: ReactNode;
  empty: string;
  hasData: boolean;
}) {
  return (
    <article className="crm-pano__card">
      <header className="crm-pano__card-head">
        <h2>{title}</h2>
        <Link href={href as Route} className="crm-pano__view-all">
          {viewAll}
        </Link>
      </header>
      {hasData ? children : <p className="crm-pano__empty">{empty}</p>}
    </article>
  );
}

function PanelCard({
  title,
  href,
  viewAll,
  empty,
  items,
}: {
  title: string;
  href: string;
  viewAll: string;
  empty: string;
  items: CrmDashboardFeedItem[];
}) {
  return (
    <article className="crm-pano__card">
      <header className="crm-pano__card-head">
        <h2>{title}</h2>
        <Link href={href as Route} className="crm-pano__view-all">
          {viewAll}
        </Link>
      </header>
      {items.length === 0 ? (
        <p className="crm-pano__empty">{empty}</p>
      ) : (
        <ul className="crm-pano__list">
          {items.map((item) => (
            <li key={`${item.kind}-${item.id}`}>
              <Link href={item.href as Route} className="crm-pano__row">
                <strong>{item.title}</strong>
                <span>{item.meta || '—'}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

export function CrmPanoLiveWorkspace() {
  const locale = useLocale();
  const copy = locale.startsWith('tr') ? COPY.tr : COPY.en;
  const { authLoading, canRead: canView } = useCrmAccess();
  const query = useQuery({
    ...crmQueries.dashboard(),
    enabled: !authLoading && canView,
  });

  const data = query.data;
  const kpis = data?.kpis;
  const scope = data?.purchase_scope;
  const charts = data?.charts;
  const panels = data?.panels;

  const projectChart = charts?.purchases_by_project ?? [];
  const monthChart = charts?.purchases_by_month ?? [];
  const taskChart = useMemo(
    () => localize(charts?.task_status ?? [], TASK_LABEL, locale),
    [charts?.task_status, locale],
  );
  const channelChart = useMemo(
    () => localize(charts?.communication_channels ?? [], CHANNEL_LABEL, locale),
    [charts?.communication_channels, locale],
  );
  const leadChart = useMemo(
    () => localize(charts?.lead_pipeline ?? [], STAGE_LABEL, locale),
    [charts?.lead_pipeline, locale],
  );
  const docChart = useMemo(
    () => localize(charts?.document_status ?? [], DOC_LABEL, locale),
    [charts?.document_status, locale],
  );

  if (authLoading || query.isLoading) {
    return (
      <div className="crm-pano" data-testid="crm-pano-live">
        <LoadingState label={locale.startsWith('tr') ? 'Yükleniyor' : 'Loading'} />
      </div>
    );
  }

  if (!canView) {
    return (
      <div className="crm-pano" data-testid="crm-pano-live">
        <ErrorState title={copy.accessDenied} message={copy.accessDenied} />
      </div>
    );
  }

  if (query.isError || !kpis || !charts || !panels || !scope) {
    return (
      <div className="crm-pano" data-testid="crm-pano-live">
        <ErrorState title={copy.loadFailed} message={copy.empty} />
      </div>
    );
  }

  return (
    <div className="crm-pano" data-testid="crm-pano-live">
      <header className="crm-pano__header">
        <div>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
      </header>

      <section className="crm-pano__kpi-row" aria-label={copy.kpis}>
        {KPI_ITEMS.map((item) => (
          <Link
            key={item.key}
            href={item.href as Route}
            className="crm-pano__kpi"
            data-testid={`crm-pano-kpi-${item.key}`}
          >
            <span>{copy[item.labelKey]}</span>
            <strong>{kpis[item.key]}</strong>
          </Link>
        ))}
      </section>

      <p className="crm-pano__scope" data-testid="crm-pano-purchase-scope">
        <strong>{copy.scope}:</strong> {copy.current} {scope.current} · {copy.historical} {scope.historical} ·{' '}
        {copy.totalRows} {scope.total}. {copy.scopeHint}
      </p>

      <section className="crm-pano__charts" aria-label={copy.charts}>
        <ChartCard
          title={copy.byProject}
          href="/workspaces/crm/agreements"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={projectChart.some((row) => row.count > 0)}
        >
          <CountBarChart
            data={projectChart.map((row) => ({ key: row.key, label: row.label, count: row.count }))}
            ariaLabel={copy.byProject}
          />
        </ChartCard>
        <ChartCard
          title={copy.byMonth}
          href="/workspaces/crm/agreements"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={monthChart.some((row) => row.count > 0)}
        >
          <CountBarChart
            data={monthChart.map((row) => ({ key: row.key, label: row.label, count: row.count }))}
            ariaLabel={copy.byMonth}
          />
        </ChartCard>
        <ChartCard
          title={copy.taskStatus}
          href="/workspaces/crm/tasks"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={taskChart.some((row) => row.count > 0)}
        >
          <PetrolDonut data={taskChart} ariaLabel={copy.taskStatus} />
        </ChartCard>
        <ChartCard
          title={copy.channels}
          href="/workspaces/crm/communication"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={channelChart.some((row) => row.count > 0)}
        >
          <PetrolDonut data={channelChart.filter((row) => row.count > 0)} ariaLabel={copy.channels} />
        </ChartCard>
        <ChartCard
          title={copy.leadPipeline}
          href="/workspaces/crm/pipeline"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={leadChart.some((row) => row.count > 0)}
        >
          <CountBarChart data={leadChart} ariaLabel={copy.leadPipeline} />
        </ChartCard>
        <ChartCard
          title={copy.docStatus}
          href="/workspaces/crm/documents"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={docChart.some((row) => row.count > 0)}
        >
          <PetrolDonut data={docChart.filter((row) => row.count > 0)} ariaLabel={copy.docStatus} />
        </ChartCard>
      </section>

      <section className="crm-pano__panels" aria-label={copy.panels}>
        <PanelCard
          title={copy.recentActivities}
          href={PANEL_LINKS.recent_activities}
          viewAll={copy.viewAll}
          empty={copy.empty}
          items={panels.recent_activities}
        />
        <PanelCard
          title={copy.upcomingTasks}
          href={PANEL_LINKS.upcoming_tasks}
          viewAll={copy.viewAll}
          empty={copy.empty}
          items={panels.upcoming_tasks}
        />
        <PanelCard
          title={copy.recentDocs}
          href={PANEL_LINKS.recent_documents}
          viewAll={copy.viewAll}
          empty={copy.empty}
          items={panels.recent_documents}
        />
        <PanelCard
          title={copy.reviewQueue}
          href={PANEL_LINKS.review_queue}
          viewAll={copy.viewAll}
          empty={copy.empty}
          items={panels.review_queue}
        />
        <PanelCard
          title={copy.recentLeads}
          href={PANEL_LINKS.recent_leads}
          viewAll={copy.viewAll}
          empty={copy.empty}
          items={panels.recent_leads}
        />
      </section>
    </div>
  );
}
