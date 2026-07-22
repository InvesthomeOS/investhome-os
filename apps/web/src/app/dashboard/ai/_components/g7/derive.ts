import type { AttentionItem, AiInsightItem, SummaryCard } from '@/lib/api/executive';

import type { MorningBriefTheme } from './ai-views';

export function sparkFromBase(base: number, points = 8): number[] {
  const n = Math.max(Math.abs(base), 1);
  return Array.from({ length: points }, (_, i) => {
    const wave = Math.sin(i * 0.9) * 0.08 + (i / points) * 0.04;
    return Math.max(0, n * (0.86 + wave));
  });
}

export type CommandKpi = {
  id: string;
  labelKey: string;
  value: string;
  severity: 'ok' | 'warn' | 'critical' | 'info';
  spark: number[];
  href: string;
  kind: 'live' | 'partial';
};

export function buildCommandKpis(input: {
  summaryCards: SummaryCard[];
  attention: AttentionItem[];
  insights: { priorities: AiInsightItem[]; risks: AiInsightItem[]; opportunities: AiInsightItem[] } | null;
  locale: string;
}): CommandKpi[] {
  const critical = input.attention.filter((a) => a.severity === 'critical').length;
  const warnings = input.attention.filter((a) => a.severity === 'warning').length;
  const priorities = input.insights?.priorities.length ?? 0;
  const risks = input.insights?.risks.length ?? 0;
  const opportunities = input.insights?.opportunities.length ?? 0;

  const cardVal = (key: string) => {
    const card = input.summaryCards.find((c) => c.key === key);
    if (!card || card.value === null || card.value === undefined) return '—';
    return String(card.value);
  };

  return [
    {
      id: 'priorities',
      labelKey: 'kpiPriorities',
      value: String(priorities),
      severity: priorities > 3 ? 'warn' : 'info',
      spark: sparkFromBase(priorities || 1),
      href: '/dashboard/ai?view=morning_brief',
      kind: 'live',
    },
    {
      id: 'risks',
      labelKey: 'kpiRisks',
      value: String(risks),
      severity: risks > 0 ? 'critical' : 'ok',
      spark: sparkFromBase(risks || 1),
      href: '/dashboard/ai?view=risk_center',
      kind: 'live',
    },
    {
      id: 'critical',
      labelKey: 'kpiCritical',
      value: String(critical),
      severity: critical > 0 ? 'critical' : 'ok',
      spark: sparkFromBase(critical || 1),
      href: '/dashboard/ai?view=action_center',
      kind: 'live',
    },
    {
      id: 'warnings',
      labelKey: 'kpiWarnings',
      value: String(warnings),
      severity: warnings > 0 ? 'warn' : 'ok',
      spark: sparkFromBase(warnings || 1),
      href: '/dashboard/ai?view=action_center',
      kind: 'live',
    },
    {
      id: 'opportunities',
      labelKey: 'kpiOpportunities',
      value: String(opportunities),
      severity: 'info',
      spark: sparkFromBase(opportunities || 1),
      href: '/dashboard/ai?view=forecasts',
      kind: 'live',
    },
    {
      id: 'projects',
      labelKey: 'kpiProjects',
      value: cardVal('active_projects'),
      severity: 'info',
      spark: sparkFromBase(Number(cardVal('active_projects')) || 1),
      href: '/dashboard/projects',
      kind: 'live',
    },
    {
      id: 'investors',
      labelKey: 'kpiInvestors',
      value: cardVal('active_investors'),
      severity: 'info',
      spark: sparkFromBase(Number(cardVal('active_investors')) || 1),
      href: '/dashboard/investors',
      kind: 'live',
    },
    {
      id: 'pipeline',
      labelKey: 'kpiPipeline',
      value: cardVal('open_leads'),
      severity: 'info',
      spark: sparkFromBase(Number(cardVal('open_leads')) || 1),
      href: '/workspaces/crm',
      kind: 'partial',
    },
  ];
}

export type BriefSection = {
  theme: MorningBriefTheme;
  evidenceHref: string;
  evidenceLabel: string;
  count: number;
  severity: 'ok' | 'warn' | 'critical' | 'info';
  live: boolean;
};

export function buildMorningBrief(input: {
  attention: AttentionItem[];
  insights: { priorities: AiInsightItem[]; risks: AiInsightItem[]; opportunities: AiInsightItem[] } | null;
  approvalsCount: number;
  overdueCount: number;
}): BriefSection[] {
  const critical = input.attention.filter((a) => a.severity === 'critical').length;
  const warnings = input.attention.filter((a) => a.severity === 'warning').length;
  const risks = input.insights?.risks.length ?? 0;
  const priorities = input.insights?.priorities.length ?? 0;

  return [
    {
      theme: 'changed',
      evidenceHref: '/dashboard/executive',
      evidenceLabel: 'executive',
      count: input.attention.length,
      severity: 'info',
      live: true,
    },
    {
      theme: 'decisions',
      evidenceHref: '/dashboard/ai?view=action_center',
      evidenceLabel: 'actions',
      count: input.approvalsCount + critical,
      severity: critical > 0 ? 'critical' : 'warn',
      live: true,
    },
    {
      theme: 'overdue',
      evidenceHref: '/dashboard/executive',
      evidenceLabel: 'attention',
      count: input.overdueCount,
      severity: input.overdueCount > 0 ? 'critical' : 'ok',
      live: true,
    },
    {
      theme: 'atRisk',
      evidenceHref: '/dashboard/ai?view=risk_center',
      evidenceLabel: 'risks',
      count: risks + warnings,
      severity: risks > 0 ? 'critical' : warnings > 0 ? 'warn' : 'ok',
      live: true,
    },
    {
      theme: 'moneyIn',
      evidenceHref: '/dashboard/finance?view=ar',
      evidenceLabel: 'finance',
      count: 0,
      severity: 'info',
      live: false,
    },
    {
      theme: 'moneyOut',
      evidenceHref: '/dashboard/finance?view=ap',
      evidenceLabel: 'finance',
      count: 0,
      severity: 'info',
      live: false,
    },
    {
      theme: 'investorFollowup',
      evidenceHref: '/dashboard/investors',
      evidenceLabel: 'investors',
      count: input.attention.filter((a) => a.link_module.includes('investor')).length,
      severity: 'warn',
      live: true,
    },
    {
      theme: 'projectDelay',
      evidenceHref: '/dashboard/projects?view=issues',
      evidenceLabel: 'projects',
      count: input.attention.filter((a) => a.link_module.includes('project')).length,
      severity: 'warn',
      live: true,
    },
    {
      theme: 'campaigns',
      evidenceHref: '/workspaces/marketing',
      evidenceLabel: 'marketing',
      count: 0,
      severity: 'info',
      live: false,
    },
    {
      theme: 'documents',
      evidenceHref: '/dashboard/knowledge?view=review',
      evidenceLabel: 'documents',
      count: 0,
      severity: 'info',
      live: false,
    },
    {
      theme: 'meetings',
      evidenceHref: '/dashboard/ai?view=meeting_intel',
      evidenceLabel: 'meetings',
      count: 0,
      severity: 'info',
      live: false,
    },
    {
      theme: 'priorities',
      evidenceHref: '/dashboard/ai?view=action_center',
      evidenceLabel: 'actions',
      count: priorities,
      severity: priorities > 0 ? 'warn' : 'ok',
      live: true,
    },
  ];
}

export type ForecastPoint = {
  label: string;
  low: number;
  mid: number;
  high: number;
};

export function buildForecastBands(base: number, locale: string): ForecastPoint[] {
  const n = Math.max(base, 10);
  const labels =
    locale === 'tr'
      ? ['30g', '60g', '90g', '120g']
      : ['30d', '60d', '90d', '120d'];
  return labels.map((label, i) => {
    const factor = 1 + i * 0.08;
    const mid = n * factor;
    return {
      label,
      low: mid * 0.82,
      mid,
      high: mid * 1.18,
    };
  });
}
