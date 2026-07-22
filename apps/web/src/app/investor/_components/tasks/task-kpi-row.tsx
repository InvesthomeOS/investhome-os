'use client';

import { InvestorKpiCard } from '../kpi-card';
import type { TasksSummaryKpis } from '../../_data/messaging-types';

interface TaskKpiRowProps {
  summary: TasksSummaryKpis;
}

export function TaskKpiRow({ summary }: TaskKpiRowProps) {
  return (
    <section className="inv-task-kpi-row" aria-label="Task summary">
      <InvestorKpiCard label="Open Tasks" value={summary.open} />
      <InvestorKpiCard label="Due Today" value={summary.dueToday} />
      <InvestorKpiCard label="Due This Week" value={summary.dueThisWeek} />
      <InvestorKpiCard label="Completed" value={summary.completed} />
      <InvestorKpiCard label="Overdue" value={summary.overdue} />
      <InvestorKpiCard label="High Priority" value={summary.highPriority} />
      <InvestorKpiCard label="Pending Documents" value={summary.pendingDocuments} />
    </section>
  );
}
