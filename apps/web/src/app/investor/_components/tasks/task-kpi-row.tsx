'use client';

import { useTranslations } from 'next-intl';

import { InvestorKpiCard } from '../kpi-card';
import type { TasksSummaryKpis } from '../../_data/messaging-types';

interface TaskKpiRowProps {
  summary: TasksSummaryKpis;
}

export function TaskKpiRow({ summary }: TaskKpiRowProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-task-kpi-row" aria-label={tChrome('k62e57c9d81')}>
      <InvestorKpiCard label="Open Tasks" value={summary.open} />
      <InvestorKpiCard label={tChrome('ke2219e75f0')} value={summary.dueToday} />
      <InvestorKpiCard label="Due This Week" value={summary.dueThisWeek} />
      <InvestorKpiCard label={tChrome('k1798b3ba42')} value={summary.completed} />
      <InvestorKpiCard label={tChrome('k07217c7719')} value={summary.overdue} />
      <InvestorKpiCard label={tChrome('kc9ccd69274')} value={summary.highPriority} />
      <InvestorKpiCard label="Pending Documents" value={summary.pendingDocuments} />
    </section>
  );
}
