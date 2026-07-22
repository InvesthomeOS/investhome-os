/**
 * Prototype-only demo data for Design System executive dashboard visual refinement (D1C).
 * NEVER import this module from production executive/home routes or API clients.
 */

export const PROTOTYPE_DEMO_BANNER = 'PROTOTYPE_DEMO_DATA_ONLY' as const;

export const demoKpis = [
  {
    id: 'exec.kpi_cash',
    value: '₺12,4M',
    trend: 'up' as const,
    trendLabel: '+3,2%',
    sparkline: [2.1, 2.4, 1.9, 2.8, 3.1, 2.7],
    href: '/dashboard/finance',
  },
  {
    id: 'exec.kpi_pipeline',
    value: '₺8,1M',
    trend: 'up' as const,
    trendLabel: '+1,1%',
    sparkline: [6.2, 6.8, 7.1, 7.4, 7.9, 8.1],
    href: '/dashboard/sales',
  },
  {
    id: 'exec.kpi_investors',
    value: '47',
    trend: 'neutral' as const,
    trendLabel: '0',
    sparkline: [45, 46, 46, 47, 47, 47],
    href: '/dashboard/investors',
  },
  {
    id: 'exec.kpi_open_deals',
    value: '23',
    trend: 'down' as const,
    trendLabel: '−2',
    sparkline: [28, 27, 26, 25, 24, 23],
    href: '/dashboard/sales',
  },
  {
    id: 'exec.kpi_projects',
    value: '6',
    trend: 'up' as const,
    trendLabel: '+1',
    sparkline: [4, 4, 5, 5, 5, 6],
    href: '/dashboard/projects',
  },
];

/** Net cash series for AreaChart (prototype demo). */
export const demoCashTrend = [
  { label: 'Oca', value: 2.1 },
  { label: 'Şub', value: 2.4 },
  { label: 'Mar', value: 1.9 },
  { label: 'Nis', value: 2.8 },
  { label: 'May', value: 3.1 },
  { label: 'Haz', value: 2.7 },
];

/** Liquidity / flow / capital summary — prototype demo only. */
export const demoFinancePulse = {
  liquidity: '₺12,4M',
  inflows: '₺4,8M',
  outflows: '₺3,1M',
  capital: '₺28,6M',
};

export const demoFunnel = [
  { label: 'Yeni', value: 120 },
  { label: 'Nitelikli', value: 74 },
  { label: 'Toplantı', value: 41 },
  { label: 'Teklif', value: 22 },
  { label: 'Kazanıldı', value: 9 },
];

export const demoInvestorMix = [
  { label: 'Aktif', value: 28 },
  { label: 'Takip', value: 12 },
  { label: 'Pasif', value: 7 },
];

export const demoInvestorPulse = {
  committed: '₺18,2M',
  capacity: '₺6,4M',
  followUps: 5,
};

export const demoAlerts = [
  {
    severity: 'critical' as const,
    titleKey: 'alertOverdue' as const,
    route: '/dashboard/finance',
  },
  {
    severity: 'warning' as const,
    titleKey: 'alertFunding' as const,
    route: '/dashboard/projects',
  },
  {
    severity: 'information' as const,
    titleKey: 'alertFollowUp' as const,
    route: '/dashboard/investors',
  },
];

export const demoAiItems = [
  {
    kind: 'priority' as const,
    titleKey: 'aiPriority' as const,
    reasonKey: 'aiPriorityReason' as const,
    impactKey: 'aiPriorityImpact' as const,
    actionKey: 'aiPriorityAction' as const,
    route: '/dashboard/finance',
  },
  {
    kind: 'risk' as const,
    titleKey: 'aiRisk' as const,
    reasonKey: 'aiRiskReason' as const,
    impactKey: 'aiRiskImpact' as const,
    actionKey: 'aiRiskAction' as const,
    route: '/dashboard/projects',
  },
  {
    kind: 'opportunity' as const,
    titleKey: 'aiOpportunity' as const,
    reasonKey: 'aiOpportunityReason' as const,
    impactKey: 'aiOpportunityImpact' as const,
    actionKey: 'aiOpportunityAction' as const,
    route: '/dashboard/sales',
  },
];

export const demoApprovals = [
  { titleKey: 'approvalExpense' as const, age: '2g', route: '/dashboard/finance' },
  { titleKey: 'approvalHold' as const, age: '5g', route: '/dashboard/sales' },
];

export const demoDeadlines = [
  {
    id: 'd1',
    titleKey: 'deadlineInspection' as const,
    when: '2026-07-22',
    route: '/dashboard/projects',
  },
  {
    id: 'd2',
    titleKey: 'deadlineClosing' as const,
    when: '2026-07-28',
    route: '/dashboard/sales',
  },
];

export const demoProjects = [
  {
    nameKey: 'projectAlpha' as const,
    progress: 72,
    health: 'on_track' as const,
    milestoneKey: 'milestoneAlpha' as const,
    route: '/dashboard/projects',
  },
  {
    nameKey: 'projectBeta' as const,
    progress: 48,
    health: 'attention' as const,
    milestoneKey: 'milestoneBeta' as const,
    route: '/dashboard/projects',
  },
  {
    nameKey: 'projectGamma' as const,
    progress: 31,
    health: 'at_risk' as const,
    milestoneKey: 'milestoneGamma' as const,
    route: '/dashboard/projects',
  },
];

export const demoMarketingMetrics = {
  leads: '184',
  handoffs: '42',
  conversion: '%12,4',
};

export const demoMarketingBars = [
  { label: 'Web', value: 64 },
  { label: 'Sosyal', value: 38 },
  { label: 'E-posta', value: 27 },
  { label: 'Etkinlik', value: 18 },
];

export const demoComms = [
  {
    titleKey: 'commUnread' as const,
    count: 3,
    route: '/dashboard',
  },
  {
    titleKey: 'commMention' as const,
    count: 1,
    route: '/dashboard',
  },
];

export const demoQuickActions = [
  { labelKey: 'qaFinance' as const, route: '/dashboard/finance' },
  { labelKey: 'qaSales' as const, route: '/dashboard/sales' },
  { labelKey: 'qaProjects' as const, route: '/dashboard/projects' },
  { labelKey: 'qaMarketing' as const, route: '/workspaces/marketing/dashboard' },
];
