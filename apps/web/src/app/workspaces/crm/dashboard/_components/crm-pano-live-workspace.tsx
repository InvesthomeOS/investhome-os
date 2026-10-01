'use client';

import type { Route } from 'next';
import Link from 'next/link';
import { useMemo, type ReactNode, type SVGProps } from 'react';
import { useLocale } from 'next-intl';
import { useQuery } from '@tanstack/react-query';

import { ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';
import { crmQueries } from '@/lib/query/crm-queries';
import type { CrmDashboardCount, CrmDashboardFeedItem, CrmDashboardKpis } from '@/workspaces/crm/types';

import { CompactHorizontalBars, CompactVerticalBars, PanoDonut } from './pano-charts';

const COPY = {
  tr: {
    title: 'Pano',
    subtitle: 'CRM genel görünüm',
    kpis: 'Operasyon özeti',
    currentPurchases: 'Güncel Satın Alma',
    investors: 'Toplam Yatırımcı',
    activeTasks: 'Aktif Görev',
    openLeads: 'Açık Lead',
    docsReview: 'İnceleme Gereken Belge',
    matchesPending: 'Eşleşme Bekleyen',
    scope: 'Satın alma kapsamı',
    current: 'Güncel',
    historical: 'Geçmiş',
    totalRows: 'Toplam',
    charts: 'Operasyon grafikleri',
    byProject: 'Projeye Göre Güncel Satın Alma',
    byMonth: 'Aylık Satın Alma',
    docStatus: 'Belge Durumu',
    totalDocuments: 'Toplam belge',
    activeProjects: 'Aktif Projeler',
    ops: 'Günlük operasyon',
    daySummary: 'Günün Özeti',
    taskSummary: 'Görev Özeti',
    criticalReviews: 'Kritik İncelemeler',
    todayMeetings: 'Bugünkü toplantı',
    todayTasks: 'Bugünkü görev',
    recentActivities: 'Son aktiviteler',
    taskActive: 'Aktif',
    taskOverdue: 'Geciken',
    taskToday: 'Bugün',
    docsUnresolved: 'İnceleme gereken belge',
    matchesOpen: 'Eşleşme bekleyen',
    unmatchedComms: 'Eşleşmeyen iletişim',
    openUnmatched: 'Aç',
    viewAll: 'Tümünü görüntüle',
    empty: 'Canlı kayıt yok.',
    loadFailed: 'Pano yüklenemedi.',
    accessDenied: 'Bu çalışma alanını görüntüleme yetkiniz yok.',
  },
  en: {
    title: 'Dashboard',
    subtitle: 'CRM overview',
    kpis: 'Operations summary',
    currentPurchases: 'Current purchases',
    investors: 'Investors',
    activeTasks: 'Active tasks',
    openLeads: 'Open leads',
    docsReview: 'Documents needing review',
    matchesPending: 'Matches pending',
    scope: 'Purchase scope',
    current: 'Current',
    historical: 'Historical',
    totalRows: 'Total',
    charts: 'Operations charts',
    byProject: 'Current purchases by project',
    byMonth: 'Monthly purchases',
    docStatus: 'Document status',
    totalDocuments: 'Total documents',
    activeProjects: 'Active projects',
    ops: 'Daily operations',
    daySummary: "Today's summary",
    taskSummary: 'Task summary',
    criticalReviews: 'Critical reviews',
    todayMeetings: "Today's meetings",
    todayTasks: "Today's tasks",
    recentActivities: 'Recent activities',
    taskActive: 'Active',
    taskOverdue: 'Overdue',
    taskToday: 'Today',
    docsUnresolved: 'Documents needing review',
    matchesOpen: 'Matches pending',
    unmatchedComms: 'Unmatched communications',
    openUnmatched: 'Open',
    viewAll: 'View all',
    empty: 'No live records.',
    loadFailed: 'Dashboard failed to load.',
    accessDenied: 'You do not have access to this workspace.',
  },
};

type Copy = (typeof COPY)['tr'];

const KPI_ITEMS: Array<{
  key: keyof CrmDashboardKpis;
  href: string;
  labelKey: keyof Copy;
  icon: 'cart' | 'people' | 'check' | 'user' | 'doc' | 'link';
}> = [
  { key: 'current_purchases', href: '/workspaces/crm/agreements', labelKey: 'currentPurchases', icon: 'cart' },
  { key: 'investors', href: '/workspaces/crm/investors', labelKey: 'investors', icon: 'people' },
  { key: 'active_tasks', href: '/workspaces/crm/tasks', labelKey: 'activeTasks', icon: 'check' },
  { key: 'open_leads', href: '/workspaces/crm/leads', labelKey: 'openLeads', icon: 'user' },
  { key: 'documents_review', href: '/workspaces/crm/documents?scope=unresolved', labelKey: 'docsReview', icon: 'doc' },
  { key: 'matches_pending', href: '/workspaces/crm/matches', labelKey: 'matchesPending', icon: 'link' },
];

const DOC_LABEL: Record<string, { tr: string; en: string }> = {
  person: { tr: 'Kişi', en: 'Person' },
  purchase: { tr: 'Satın alma', en: 'Purchase' },
  hidden: { tr: 'Gizli', en: 'Hidden' },
  unresolved: { tr: 'İnceleme', en: 'Review' },
};

function localize(rows: CrmDashboardCount[], map: Record<string, { tr: string; en: string }>, locale: string) {
  const lang = locale.startsWith('tr') ? 'tr' : 'en';
  return rows.map((row) => ({
    ...row,
    label: map[row.key]?.[lang] ?? row.label,
  }));
}

function formatContextDate(locale: string) {
  return new Intl.DateTimeFormat(locale.startsWith('tr') ? 'tr-TR' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date());
}

function isSameLocalDay(value: string | null | undefined, now: Date) {
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}

function countByKey(rows: CrmDashboardCount[], key: string) {
  return rows.find((row) => row.key === key)?.count ?? 0;
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

function KpiGlyph({ name }: { name: (typeof KPI_ITEMS)[number]['icon'] }) {
  const props: SVGProps<SVGSVGElement> = {
    width: 18,
    height: 18,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.75,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  };
  if (name === 'cart') {
    return (
      <svg {...props}>
        <circle cx="9" cy="20" r="1.2" fill="currentColor" stroke="none" />
        <circle cx="18" cy="20" r="1.2" fill="currentColor" stroke="none" />
        <path d="M3 4h2l2.2 11.2a1.5 1.5 0 0 0 1.5 1.2h9.4a1.5 1.5 0 0 0 1.5-1.2L21 8H7" />
      </svg>
    );
  }
  if (name === 'people') {
    return (
      <svg {...props}>
        <circle cx="9" cy="8" r="3" />
        <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />
        <circle cx="17" cy="8.5" r="2.4" />
        <path d="M16.2 13.2a4.6 4.6 0 0 1 4.3 5.8" />
      </svg>
    );
  }
  if (name === 'check') {
    return (
      <svg {...props}>
        <rect x="4" y="4" width="16" height="16" rx="3" />
        <path d="m8 12 2.8 2.8L16.5 9" />
      </svg>
    );
  }
  if (name === 'user') {
    return (
      <svg {...props}>
        <circle cx="12" cy="8" r="3.2" />
        <path d="M5 19a7 7 0 0 1 14 0" />
      </svg>
    );
  }
  if (name === 'doc') {
    return (
      <svg {...props}>
        <path d="M7 4h7l5 5v11a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z" />
        <path d="M14 4v5h5M9 13h6M9 17h4" />
      </svg>
    );
  }
  return (
    <svg {...props}>
      <path d="M9.5 14.5 14.5 9.5" />
      <path d="M10.2 6.4 12 4.6a3.2 3.2 0 0 1 4.5 4.5l-1.8 1.8" />
      <path d="M13.8 17.6 12 19.4a3.2 3.2 0 1 1-4.5-4.5l1.8-1.8" />
    </svg>
  );
}

function StatRow({
  label,
  value,
  href,
}: {
  label: string;
  value: ReactNode;
  href: string;
}) {
  return (
    <Link href={href as Route} className="crm-pano__stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </Link>
  );
}

function FeedPreview({ items, empty }: { items: CrmDashboardFeedItem[]; empty: string }) {
  if (items.length === 0) {
    return <p className="crm-pano__empty">{empty}</p>;
  }
  return (
    <ul className="crm-pano__list">
      {items.slice(0, 4).map((item) => (
        <li key={`${item.kind}-${item.id}`}>
          <Link href={item.href as Route} className="crm-pano__row">
            <strong>{item.title}</strong>
            <span>{item.meta || '—'}</span>
          </Link>
        </li>
      ))}
    </ul>
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
  const now = useMemo(() => new Date(), []);

  const projectChart = charts?.purchases_by_project ?? [];
  const monthChart = charts?.purchases_by_month ?? [];
  const taskChart = charts?.task_status ?? [];
  const docChart = useMemo(
    () => localize(charts?.document_status ?? [], DOC_LABEL, locale),
    [charts?.document_status, locale],
  );

  const todayMeetingCount = data?.todays_meetings.length ?? 0;
  const todayTaskCount = (data?.upcoming_tasks ?? []).filter((task) => isSameLocalDay(task.due_at, now)).length;
  const overdueCount = countByKey(taskChart, 'overdue');

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
        <div className="crm-pano__context">
          <span>{formatContextDate(locale)}</span>
          <p className="crm-pano__scope" data-testid="crm-pano-purchase-scope">
            <strong>{copy.scope}:</strong> {copy.current}{' '}
            <span data-testid="crm-pano-scope-current">{scope.current}</span> · {copy.historical}{' '}
            <span data-testid="crm-pano-scope-historical">{scope.historical}</span> · {copy.totalRows}{' '}
            <span data-testid="crm-pano-scope-total">{scope.total}</span>
          </p>
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
            <span className="crm-pano__kpi-icon" data-icon={item.icon}>
              <KpiGlyph name={item.icon} />
            </span>
            <span className="crm-pano__kpi-copy">
              <span>{copy[item.labelKey]}</span>
              <strong>{kpis[item.key]}</strong>
            </span>
          </Link>
        ))}
      </section>

      <section className="crm-pano__row-charts" aria-label={copy.charts}>
        <ChartCard
          title={copy.byProject}
          href="/workspaces/crm/agreements"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={projectChart.some((row) => row.count > 0)}
        >
          <CompactVerticalBars data={projectChart} ariaLabel={copy.byProject} />
        </ChartCard>
        <ChartCard
          title={copy.docStatus}
          href="/workspaces/crm/documents"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={docChart.some((row) => row.count > 0)}
        >
          <PanoDonut data={docChart} ariaLabel={copy.docStatus} totalLabel={copy.totalDocuments} />
        </ChartCard>
      </section>

      <section className="crm-pano__row-charts" aria-label={copy.activeProjects}>
        <ChartCard
          title={copy.byMonth}
          href="/workspaces/crm/agreements"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={monthChart.some((row) => row.count > 0)}
        >
          <CompactVerticalBars data={monthChart} ariaLabel={copy.byMonth} />
        </ChartCard>
        <ChartCard
          title={copy.activeProjects}
          href="/workspaces/crm/agreements"
          viewAll={copy.viewAll}
          empty={copy.empty}
          hasData={projectChart.some((row) => row.count > 0)}
        >
          <CompactHorizontalBars data={projectChart} ariaLabel={copy.activeProjects} />
        </ChartCard>
      </section>

      <section className="crm-pano__ops" aria-label={copy.ops}>
        <article className="crm-pano__card">
          <header className="crm-pano__card-head">
            <h2>{copy.daySummary}</h2>
            <Link href={'/workspaces/crm/activities' as Route} className="crm-pano__view-all">
              {copy.viewAll}
            </Link>
          </header>
          <div className="crm-pano__stats">
            <StatRow label={copy.todayMeetings} value={todayMeetingCount} href="/workspaces/crm/calendar" />
            <StatRow label={copy.todayTasks} value={todayTaskCount} href="/workspaces/crm/tasks" />
          </div>
          <h3 className="crm-pano__subhead">{copy.recentActivities}</h3>
          <FeedPreview items={panels.recent_activities} empty={copy.empty} />
        </article>

        <article className="crm-pano__card">
          <header className="crm-pano__card-head">
            <h2>{copy.taskSummary}</h2>
            <Link href={'/workspaces/crm/tasks' as Route} className="crm-pano__view-all">
              {copy.viewAll}
            </Link>
          </header>
          <div className="crm-pano__stats">
            <StatRow label={copy.taskActive} value={kpis.active_tasks} href="/workspaces/crm/tasks" />
            <StatRow label={copy.taskOverdue} value={overdueCount} href="/workspaces/crm/tasks" />
            <StatRow label={copy.taskToday} value={todayTaskCount} href="/workspaces/crm/tasks" />
          </div>
          {panels.upcoming_tasks.length > 0 ? <FeedPreview items={panels.upcoming_tasks} empty={copy.empty} /> : null}
        </article>

        <article className="crm-pano__card">
          <header className="crm-pano__card-head">
            <h2>{copy.criticalReviews}</h2>
            <Link href={'/workspaces/crm/documents?scope=unresolved' as Route} className="crm-pano__view-all">
              {copy.viewAll}
            </Link>
          </header>
          <div className="crm-pano__stats">
            <StatRow
              label={copy.docsUnresolved}
              value={kpis.documents_review}
              href="/workspaces/crm/documents?scope=unresolved"
            />
            <StatRow label={copy.matchesOpen} value={kpis.matches_pending} href="/workspaces/crm/matches" />
            <StatRow label={copy.unmatchedComms} value={copy.openUnmatched} href="/workspaces/crm/communication/unmatched" />
          </div>
          <FeedPreview items={panels.review_queue} empty={copy.empty} />
        </article>
      </section>
    </div>
  );
}
