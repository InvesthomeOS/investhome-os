import type { Project, ProjectPriority, ProjectStatus } from '@/lib/api/projects';
import {
  formatCompactCurrency,
  priorityTone,
  statusTone,
  type AiRiskLevel,
  type CoverScene,
  type MilestonePhase,
  type StatusTone,
} from './projects-ds-model';

export const PROJECT_DETAIL_DS_TABS = [
  'overview',
  'construction',
  'units',
  'financial',
  'investors',
  'documents',
  'tasks',
  'timeline',
  'reports',
  'ai-insights',
] as const;

export type ProjectDetailDsTab = (typeof PROJECT_DETAIL_DS_TABS)[number];

/** Legacy route segments → DS tabs (presentation migration). */
export const PROJECT_DETAIL_TAB_ALIASES: Record<string, ProjectDetailDsTab> = {
  financials: 'financial',
  schedule: 'timeline',
  activity: 'timeline',
  team: 'overview',
  sales: 'units',
  leasing: 'units',
};

export function isProjectDetailDsTab(value: string): value is ProjectDetailDsTab {
  return (PROJECT_DETAIL_DS_TABS as readonly string[]).includes(value);
}

export function resolveProjectDetailDsTab(value: string): ProjectDetailDsTab | null {
  if (isProjectDetailDsTab(value)) return value;
  return PROJECT_DETAIL_TAB_ALIASES[value] ?? null;
}

export function projectDetailDsHref(
  projectId: string,
  tab: ProjectDetailDsTab = 'overview',
): string {
  return `/dashboard/projects/${projectId}/${tab}`;
}

export type UnitStatus = 'available' | 'reserved' | 'sold' | 'rented' | 'blocked';
export type TaskStatus = 'todo' | 'in_progress' | 'blocked' | 'done';
export type DocCategory =
  | 'contracts'
  | 'permits'
  | 'invoices'
  | 'drawings'
  | 'videos'
  | 'photos'
  | 'certificates'
  | 'specifications';
export type TimelineDomain =
  | 'construction'
  | 'permits'
  | 'deliveries'
  | 'sales'
  | 'marketing'
  | 'legal'
  | 'finance';
export type PermitStatus = 'approved' | 'pending' | 'in_review' | 'expiring';
export type InvestmentStatus = 'fundraising' | 'funded' | 'partial' | 'exiting';

export type DetailKpiKey =
  | 'totalBudget'
  | 'spent'
  | 'remaining'
  | 'expectedRoi'
  | 'units'
  | 'investors'
  | 'completion'
  | 'targetDelivery';

export type DetailUnit = {
  id: string;
  code: string;
  floor: number;
  bedrooms: number;
  areaSqm: number;
  price: number;
  status: UnitStatus;
  investor: string | null;
  rentalMonthly: number | null;
};

export type DetailInvestor = {
  id: string;
  name: string;
  initials: string;
  investment: number;
  ownershipPct: number;
  expectedReturn: number;
  status: 'active' | 'committed' | 'pending' | 'exited';
  documents: number;
  lastContact: string;
};

export type DetailDocument = {
  id: string;
  name: string;
  category: DocCategory;
  size: string;
  updatedAt: string;
  owner: string;
};

export type DetailTask = {
  id: string;
  title: string;
  priority: ProjectPriority;
  owner: string;
  status: TaskStatus;
  dueDate: string;
  progress: number;
  milestone: MilestonePhase;
};

export type DetailTimelineItem = {
  id: string;
  title: string;
  domain: TimelineDomain;
  date: string;
  status: 'completed' | 'current' | 'upcoming';
  note: string;
};

export type DetailMilestone = {
  id: string;
  phase: MilestonePhase;
  labelKey: MilestonePhase;
  pct: number;
  done: boolean;
  date: string;
};

export type DetailAiInsight = {
  id: string;
  key:
    | 'delayPrediction'
    | 'budgetRisk'
    | 'cashFlowRisk'
    | 'salesForecast'
    | 'investmentRecommendation'
    | 'completionConfidence'
    | 'materialCostTrend'
    | 'suggestedActions';
  score: number;
  tone: StatusTone;
  trend: 'up' | 'down' | 'neutral';
  delta: string;
};

export type DetailReportCard = {
  id: string;
  key: 'executive' | 'construction' | 'financial' | 'sales' | 'risk' | 'investor';
  updatedAt: string;
  pages: number;
};

export type ProjectDetailDsModel = {
  id: string;
  name: string;
  code: string;
  location: string;
  city: string;
  developmentType: string;
  projectType: string;
  status: ProjectStatus;
  stage: string | null;
  priority: ProjectPriority;
  risk: AiRiskLevel | null;
  coverScene: CoverScene | null;
  completion: number | null;
  healthScore: number | null;
  aiConfidence: number | null;
  investmentStatus: InvestmentStatus | null;
  lastUpdated: string | null;
  description: string | null;
  notes: string | null;
  nextMilestone: MilestonePhase | null;
  currentPhase: MilestonePhase | null;
  manager: string | null;
  contractor: string | null;
  architect: string | null;
  constructionCompany: string | null;
  permitStatus: PermitStatus | null;
  upcomingInspection: string | null;
  completionPrediction: string | null;
  weather: { tempC: number; condition: 'clear' | 'cloudy' | 'rain' | 'wind' } | null;
  kpis: Record<DetailKpiKey, { value: string | null }>;
  financial: {
    budget: number | null;
    spent: number | null;
    remaining: number | null;
    forecast: number | null;
    loan: number | null;
    cashFlow: number | null;
    roi: number | null;
    profit: number | null;
    revenue: number | null;
    expenses: number | null;
    series: number[];
  };
  scheduleDates: Array<{ id: string; labelKey: string; date: string }>;
  milestones: DetailMilestone[];
  units: DetailUnit[];
  investors: DetailInvestor[];
  documents: DetailDocument[];
  docCategoryCounts: Record<DocCategory, number>;
  tasks: DetailTask[];
  timeline: DetailTimelineItem[];
  reports: DetailReportCard[];
  aiInsights: DetailAiInsight[];
  upcomingTasks: DetailTask[];
  recentActivity: Array<{ id: string; title: string; time: string; tone: StatusTone }>;
  alerts: {
    ai: Array<{ id: string; textKey: string; tone: StatusTone }>;
    budget: Array<{ id: string; textKey: string; tone: StatusTone }>;
    construction: Array<{ id: string; textKey: string; tone: StatusTone }>;
  };
};

function finiteNumber(value: string | number | null | undefined): number | null {
  if (value == null || value === '') return null;
  const amount = Number(value);
  return Number.isFinite(amount) ? amount : null;
}

function storedMoney(value: string | number | null | undefined, locale: string): string | null {
  const amount = finiteNumber(value);
  if (amount == null) return null;
  return formatCompactCurrency(amount, locale);
}

function investmentStatusFor(project: Project): InvestmentStatus | null {
  const required = finiteNumber(project.equity_required);
  const raised = finiteNumber(project.equity_raised);
  if (required == null && raised == null) return null;
  if (
    project.project_status === 'stabilization' ||
    project.project_status === 'completed'
  ) {
    return 'exiting';
  }
  if (required != null && raised != null && required > 0 && raised >= required * 0.95) {
    return 'funded';
  }
  if (raised != null && raised > 0 && (required == null || raised < required)) return 'partial';
  if (required != null && raised === 0) return 'fundraising';
  return null;
}

function teamName(project: Project, role: Project['team_summary'][number]['role']): string | null {
  const member = project.team_summary?.find((item) => item.role === role && item.status !== 'ended');
  return member?.user?.full_name?.trim() || null;
}

function completionFor(project: Project): number | null {
  const amount = finiteNumber(project.completion_percentage);
  if (amount == null) return null;
  return Math.min(100, Math.max(0, amount));
}

function emptyFinancial(): ProjectDetailDsModel['financial'] {
  return {
    budget: null,
    spent: null,
    remaining: null,
    forecast: null,
    loan: null,
    cashFlow: null,
    roi: null,
    profit: null,
    revenue: null,
    expenses: null,
    series: [],
  };
}

function emptyKpis(): ProjectDetailDsModel['kpis'] {
  return {
    totalBudget: { value: null },
    spent: { value: null },
    remaining: { value: null },
    expectedRoi: { value: null },
    units: { value: null },
    investors: { value: null },
    completion: { value: null },
    targetDelivery: { value: null },
  };
}

function emptyModel(projectId: string): ProjectDetailDsModel {
  return {
    id: projectId,
    name: '',
    code: '',
    location: '',
    city: '',
    developmentType: '',
    projectType: 'residential',
    status: 'pipeline',
    stage: null,
    priority: 'medium',
    risk: null,
    coverScene: null,
    completion: null,
    healthScore: null,
    aiConfidence: null,
    investmentStatus: null,
    lastUpdated: null,
    description: null,
    notes: null,
    nextMilestone: null,
    currentPhase: null,
    manager: null,
    contractor: null,
    architect: null,
    constructionCompany: null,
    permitStatus: null,
    upcomingInspection: null,
    completionPrediction: null,
    weather: null,
    kpis: emptyKpis(),
    financial: emptyFinancial(),
    scheduleDates: [],
    milestones: [],
    units: [],
    investors: [],
    documents: [],
    docCategoryCounts: {
      contracts: 0,
      permits: 0,
      invoices: 0,
      drawings: 0,
      videos: 0,
      photos: 0,
      certificates: 0,
      specifications: 0,
    },
    tasks: [],
    timeline: [],
    reports: [],
    aiInsights: [],
    upcomingTasks: [],
    recentActivity: [],
    alerts: { ai: [], budget: [], construction: [] },
  };
}

export function buildProjectDetailDsModel(
  projectInput: Project | null | undefined,
  projectId: string,
  locale: string,
): ProjectDetailDsModel {
  if (!projectInput) return emptyModel(projectId);
  const project = projectInput;
  const completion = completionFor(project);
  const location = [project.address, project.city, project.state, project.country].filter(Boolean).join(', ');
  const budget = finiteNumber(project.total_development_cost ?? project.construction_budget);
  const roi = finiteNumber(project.projected_roi ?? project.projected_irr);
  const loan = finiteNumber(project.debt_amount);
  const revenue = finiteNumber(project.projected_revenue);
  const profit = finiteNumber(project.projected_profit);
  const unitsTotal = project.total_units ?? project.residential_units;
  const scheduleDates = (
    [
      ['acquisition', project.acquisition_date],
      ['start', project.start_date],
      ['actualStart', project.actual_start_date],
      ['targetCompletion', project.target_completion_date],
      ['actualCompletion', project.actual_completion_date],
      ['closing', project.estimated_closing_date],
    ] as const
  )
    .filter((entry): entry is [(typeof entry)[0], string] => Boolean(entry[1]))
    .map(([labelKey, date]) => ({
      id: `${project.id}-${labelKey}`,
      labelKey,
      date: date.slice(0, 10),
    }));

  return {
    id: project.id,
    name: project.project_name,
    code: project.project_code,
    location,
    city: project.city ?? '',
    developmentType: project.development_type,
    projectType: project.project_type,
    status: project.project_status,
    stage: project.development_stage,
    priority: project.priority,
    risk: null,
    coverScene: null,
    completion,
    healthScore: null,
    aiConfidence: null,
    investmentStatus: investmentStatusFor(project),
    lastUpdated: project.updated_at,
    description: project.description?.trim() || null,
    notes: project.notes?.trim() || null,
    nextMilestone: null,
    currentPhase: null,
    manager:
      project.project_manager?.full_name?.trim() ||
      project.assigned_project_manager?.trim() ||
      teamName(project, 'project_manager'),
    contractor: teamName(project, 'construction_manager'),
    architect: null,
    constructionCompany: null,
    permitStatus: null,
    upcomingInspection: null,
    completionPrediction: project.target_completion_date?.slice(0, 10) ?? null,
    weather: null,
    kpis: {
      totalBudget: { value: storedMoney(budget, locale) },
      spent: { value: null },
      remaining: { value: null },
      expectedRoi: { value: roi == null ? null : `${roi.toFixed(1)}%` },
      units: { value: unitsTotal == null ? null : String(unitsTotal) },
      investors: { value: null },
      completion: { value: completion == null ? null : `${completion}%` },
      targetDelivery: { value: project.target_completion_date?.slice(0, 10) ?? null },
    },
    financial: {
      ...emptyFinancial(),
      budget,
      loan,
      roi,
      profit,
      revenue,
    },
    scheduleDates,
    milestones: [],
    units: [],
    investors: [],
    documents: [],
    docCategoryCounts: {
      contracts: 0,
      permits: 0,
      invoices: 0,
      drawings: 0,
      videos: 0,
      photos: 0,
      certificates: 0,
      specifications: 0,
    },
    tasks: [],
    timeline: [],
    reports: [],
    aiInsights: [],
    upcomingTasks: [],
    recentActivity: [],
    alerts: { ai: [], budget: [], construction: [] },
  };
}


export { statusTone, priorityTone, formatCompactCurrency };
