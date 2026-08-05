import type { Project, ProjectPriority, ProjectStatus } from '@/lib/api/projects';
import { projectCompletion, projectValue } from '../g4/project-types';
import {
  coverSceneFor,
  deriveAiRisk,
  deriveMilestonePhase,
  deriveNextMilestoneKey,
  formatCompactCurrency,
  hashIndex,
  initials,
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
  risk: AiRiskLevel;
  coverScene: CoverScene;
  completion: number;
  healthScore: number;
  aiConfidence: number;
  investmentStatus: InvestmentStatus;
  lastUpdated: string;
  description: string;
  nextMilestone: MilestonePhase;
  currentPhase: MilestonePhase;
  manager: string;
  contractor: string;
  architect: string;
  constructionCompany: string;
  permitStatus: PermitStatus;
  upcomingInspection: string;
  completionPrediction: string;
  weather: { tempC: number; condition: 'clear' | 'cloudy' | 'rain' | 'wind' };
  kpis: Record<DetailKpiKey, { value: string; delta?: string; deltaTone?: 'up' | 'down' | 'neutral' }>;
  financial: {
    budget: number;
    spent: number;
    remaining: number;
    forecast: number;
    loan: number;
    cashFlow: number;
    roi: number;
    profit: number;
    revenue: number;
    expenses: number;
    series: number[];
  };
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

const CONTRACTORS = [
  'Marmara İnşaat A.Ş.',
  'Ankara Yapı Group',
  'Ege Construction Co.',
  'Bosphorus Builders',
  'Anadolu Teknik',
];

const ARCHITECTS = [
  'Studio Horizon',
  'Atölye Mimarlık',
  'Coastline Architects',
  'Form & Frame Studio',
  'Urban Layer Office',
];

const CONSTRUCTION_COS = [
  'İstanbul Construction Partners',
  'Black Sea Build Co.',
  'Aegean Development Works',
  'Capitol Contracting',
  'Nexus Construction TR',
];

const INVESTOR_NAMES = [
  'Elif Yılmaz',
  'Can Öztürk',
  'Maya Demir',
  'Kerim Arslan',
  'Selin Kaya',
  'Emre Aydın',
  'Zeynep Çelik',
  'Burak Şahin',
];

const DOC_NAMES: Record<DocCategory, string[]> = {
  contracts: ['EPC Agreement.pdf', 'Land Purchase Deed.pdf', 'JV Term Sheet.pdf'],
  permits: ['Building Permit.pdf', 'Fire Safety Approval.pdf', 'Zoning Certificate.pdf'],
  invoices: ['Steel Package Invoice.pdf', 'MEP Progress Invoice.pdf', 'Consultant Fee.pdf'],
  drawings: ['Architectural Set Rev.C.dwg', 'Structural Plans.pdf', 'Facade Details.pdf'],
  videos: ['Site Progress Week 24.mp4', 'Drone Flyover Q2.mp4'],
  photos: ['Tower Core Progress.jpg', 'Lobby Mockup.jpg', 'Facade Sample.jpg'],
  certificates: ['ISO Site Certificate.pdf', 'Occupancy Pre-Cert.pdf'],
  specifications: ['Technical Spec Book.pdf', 'Material Schedule.xlsx'],
};

function num(value: string | number | null | undefined, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function addDays(iso: string | null | undefined, days: number): string {
  const base = iso ? new Date(iso) : new Date();
  if (Number.isNaN(base.getTime())) {
    const d = new Date();
    d.setDate(d.getDate() + days);
    return d.toISOString().slice(0, 10);
  }
  base.setDate(base.getDate() + days);
  return base.toISOString().slice(0, 10);
}

function investmentStatusFor(project: Project): InvestmentStatus {
  const raised = num(project.equity_raised);
  const required = num(project.equity_required);
  if (project.project_status === 'stabilization' || project.project_status === 'completed') {
    return 'exiting';
  }
  if (required > 0 && raised >= required * 0.95) return 'funded';
  if (raised > 0) return 'partial';
  return 'fundraising';
}

function permitStatusFor(project: Project, risk: AiRiskLevel): PermitStatus {
  if (project.project_status === 'permitting') return 'in_review';
  if (risk === 'high' || risk === 'critical') return 'expiring';
  if (
    project.project_status === 'pipeline' ||
    project.project_status === 'due_diligence' ||
    project.project_status === 'pre_development'
  ) {
    return 'pending';
  }
  return 'approved';
}

function weatherFor(seed: string): ProjectDetailDsModel['weather'] {
  const conditions = ['clear', 'cloudy', 'rain', 'wind'] as const;
  return {
    tempC: 18 + hashIndex(seed, 14),
    condition: conditions[hashIndex(seed, conditions.length)]!,
  };
}

function buildSeries(seed: string, spentRatio: number): number[] {
  const start = Math.max(8, Math.round(spentRatio * 40));
  return Array.from({ length: 8 }, (_, i) => {
    const wobble = hashIndex(`${seed}-${i}`, 12) - 5;
    return Math.max(6, Math.min(96, start + i * 8 + wobble));
  });
}

function fallbackProject(projectId: string): Project {
  const idx = hashIndex(projectId, 6);
  const cities = ['İstanbul', 'Ankara', 'İzmir', 'Antalya', 'Bursa', 'Bodrum'];
  const names = [
    'Marina Residences',
    'Skyline Tower',
    'Garden Courts',
    'Coastal Vista',
    'Central Plaza',
    'Ridge Homes',
  ];
  const codes = ['MRN-01', 'SKY-12', 'GRD-04', 'CST-08', 'PLZ-03', 'RDG-07'];
  return {
    id: projectId,
    project_code: codes[idx]!,
    project_name: names[idx]!,
    slug: null,
    address: 'Demo Cadde 12',
    address_line2: null,
    city: cities[idx]!,
    state: null,
    postal_code: null,
    country: 'TR',
    latitude: null,
    longitude: null,
    timezone: 'Europe/Istanbul',
    project_type: 'residential',
    development_type: 'ground_up',
    project_status: 'construction',
    priority: 'high',
    development_stage: 'construction',
    ownership_entity: 'Investhome Demo SPV',
    company_id: null,
    total_units: 120,
    residential_units: 110,
    commercial_units: 10,
    gross_square_feet: null,
    net_sellable_square_feet: null,
    lot_size: null,
    acquisition_price: '8500000',
    land_cost: '6200000',
    construction_budget: '42000000',
    soft_cost_budget: '4800000',
    total_development_cost: '53000000',
    current_project_value: '61000000',
    projected_sale_value: '78000000',
    equity_required: '18000000',
    equity_raised: '14200000',
    debt_amount: '28000000',
    loan_to_cost: '52',
    projected_revenue: '76000000',
    projected_profit: '14000000',
    projected_roi: '18.4',
    projected_irr: '16.2',
    currency: 'USD',
    completion_percentage: String(35 + hashIndex(projectId, 45)),
    acquisition_date: null,
    start_date: addDays(null, -420),
    actual_start_date: addDays(null, -400),
    target_completion_date: addDays(null, 280 + hashIndex(projectId, 120)),
    actual_completion_date: null,
    estimated_closing_date: null,
    assigned_project_manager: 'Ayşe Kara',
    project_manager_user_id: null,
    project_manager: {
      id: 'demo-pm',
      full_name: 'Ayşe Kara',
      email: 'ayse.kara@investhome.demo',
    },
    team_summary: [],
    description:
      'Premium mixed residential development with marina-facing amenities, efficient unit mix, and institutional-grade construction governance.',
    notes: null,
    is_demo: true,
    archived_at: null,
    created_at: addDays(null, -500),
    updated_at: addDays(null, -2),
    created_by_user_id: null,
    updated_by_user_id: null,
  };
}

export function buildProjectDetailDsModel(
  projectInput: Project | null | undefined,
  projectId: string,
  locale: string,
): ProjectDetailDsModel {
  const project = projectInput ?? fallbackProject(projectId);
  const completion = projectCompletion(project);
  const risk = deriveAiRisk(project);
  const budget = num(
    project.construction_budget ?? project.total_development_cost ?? project.current_project_value,
    42_000_000,
  );
  const spentRatio = Math.min(0.92, Math.max(0.12, completion / 100 - 0.04 + hashIndex(project.id, 8) / 100));
  const spent = Math.round(budget * spentRatio);
  const remaining = Math.max(0, budget - spent);
  const roi = num(project.projected_roi ?? project.projected_irr, 16.5);
  const unitsTotal = project.total_units ?? project.residential_units ?? 96;
  const investorsCount = 4 + hashIndex(project.id, 5);
  const healthScore = Math.max(
    18,
    Math.min(98, completion + 16 - (risk === 'low' ? 0 : risk === 'medium' ? 8 : risk === 'high' ? 16 : 26)),
  );
  const aiConfidence = Math.max(
    44,
    Math.min(97, 55 + Math.round(completion * 0.3) - (risk === 'critical' ? 18 : risk === 'high' ? 10 : 0)),
  );
  const manager =
    project.project_manager?.full_name ?? project.assigned_project_manager ?? 'Ayşe Kara';
  const seed = project.id;
  const currentPhase = deriveMilestonePhase(project);
  const nextMilestone = deriveNextMilestoneKey(project);
  const location = [project.city, project.state, project.country].filter(Boolean).join(', ') || 'Türkiye';

  const phases: MilestonePhase[] = ['foundation', 'structure', 'envelope', 'interiors', 'handover'];
  const milestones: DetailMilestone[] = phases.map((phase, i) => {
    const target = (i + 1) * 20;
    const done = completion >= target - 2;
    return {
      id: `${seed}-ms-${phase}`,
      phase,
      labelKey: phase,
      pct: Math.min(100, Math.max(0, Math.round(completion - i * 18 + 20))),
      done,
      date: addDays(project.target_completion_date, -240 + i * 55),
    };
  });

  const unitStatuses: UnitStatus[] = ['available', 'reserved', 'sold', 'rented', 'blocked'];
  const units: DetailUnit[] = Array.from({ length: Math.min(12, Math.max(8, unitsTotal)) }, (_, i) => {
    const status = unitStatuses[(i + hashIndex(seed, unitStatuses.length)) % unitStatuses.length]!;
    const investor =
      status === 'sold' || status === 'reserved' || status === 'rented'
        ? INVESTOR_NAMES[(i + hashIndex(seed, INVESTOR_NAMES.length)) % INVESTOR_NAMES.length]!
        : null;
    return {
      id: `${seed}-unit-${i + 1}`,
      code: `${String.fromCharCode(65 + (i % 4))}-${String(100 + i * 3).padStart(3, '0')}`,
      floor: 2 + (i % 18),
      bedrooms: 1 + (i % 4),
      areaSqm: 68 + (i % 7) * 12,
      price: Math.round((budget / Math.max(unitsTotal, 1)) * (0.7 + (i % 5) * 0.08)),
      status,
      investor,
      rentalMonthly: status === 'rented' || status === 'available' ? 1800 + i * 120 : null,
    };
  });

  const investors: DetailInvestor[] = Array.from({ length: investorsCount }, (_, i) => {
    const name = INVESTOR_NAMES[(i + hashIndex(seed, INVESTOR_NAMES.length)) % INVESTOR_NAMES.length]!;
    const ownership = Math.round((100 / investorsCount) * (0.7 + (i % 3) * 0.15) * 10) / 10;
    return {
      id: `${seed}-inv-${i}`,
      name,
      initials: initials(name),
      investment: Math.round((num(project.equity_raised, budget * 0.3) / investorsCount) * (0.8 + (i % 4) * 0.1)),
      ownershipPct: ownership,
      expectedReturn: Math.round((roi + (i % 3) - 1) * 10) / 10,
      status: (['active', 'committed', 'pending', 'active'] as const)[i % 4]!,
      documents: 2 + (i % 4),
      lastContact: addDays(null, -3 - i * 4),
    };
  });

  const categories = Object.keys(DOC_NAMES) as DocCategory[];
  const documents: DetailDocument[] = categories.flatMap((category, ci) =>
    DOC_NAMES[category].slice(0, 2).map((name, ni) => ({
      id: `${seed}-doc-${category}-${ni}`,
      name,
      category,
      size: `${1.2 + ((ci + ni) % 5) * 0.7} MB`,
      updatedAt: addDays(null, -1 - ci - ni * 2),
      owner: manager,
    })),
  );

  const docCategoryCounts = categories.reduce(
    (acc, category) => {
      acc[category] = documents.filter((d) => d.category === category).length;
      return acc;
    },
    {} as Record<DocCategory, number>,
  );

  const tasks: DetailTask[] = [
    {
      id: `${seed}-task-1`,
      title: locale === 'tr' ? 'Cephe paneli teslimatını doğrula' : 'Validate facade panel delivery',
      priority: 'high',
      owner: manager,
      status: 'in_progress',
      dueDate: addDays(null, 5),
      progress: 62,
      milestone: currentPhase,
    },
    {
      id: `${seed}-task-2`,
      title: locale === 'tr' ? 'Ruhsat yenileme dosyasını tamamla' : 'Complete permit renewal pack',
      priority: 'critical',
      owner: 'Legal Ops',
      status: 'blocked',
      dueDate: addDays(null, 2),
      progress: 35,
      milestone: 'envelope',
    },
    {
      id: `${seed}-task-3`,
      title: locale === 'tr' ? 'Yatırımcı raporunu yayınla' : 'Publish investor report pack',
      priority: 'medium',
      owner: 'Finance',
      status: 'todo',
      dueDate: addDays(null, 9),
      progress: 12,
      milestone: nextMilestone,
    },
    {
      id: `${seed}-task-4`,
      title: locale === 'tr' ? 'Saha güvenliği denetimini kapat' : 'Close site safety inspection',
      priority: 'high',
      owner: CONTRACTORS[hashIndex(seed, CONTRACTORS.length)]!,
      status: 'in_progress',
      dueDate: addDays(null, 3),
      progress: 78,
      milestone: currentPhase,
    },
    {
      id: `${seed}-task-5`,
      title: locale === 'tr' ? 'Satış birim fiyatlarını güncelle' : 'Refresh unit pricing matrix',
      priority: 'medium',
      owner: 'Sales',
      status: 'done',
      dueDate: addDays(null, -4),
      progress: 100,
      milestone: 'interiors',
    },
    {
      id: `${seed}-task-6`,
      title: locale === 'tr' ? 'Nakit akışı tahminini revize et' : 'Revise cash-flow forecast',
      priority: 'high',
      owner: 'Finance',
      status: 'todo',
      dueDate: addDays(null, 7),
      progress: 20,
      milestone: nextMilestone,
    },
  ];

  const domains: TimelineDomain[] = [
    'construction',
    'permits',
    'deliveries',
    'sales',
    'marketing',
    'legal',
    'finance',
  ];
  const timeline: DetailTimelineItem[] = domains.map((domain, i) => {
    const status: DetailTimelineItem['status'] =
      i < 2 ? 'completed' : i === 2 ? 'current' : 'upcoming';
    return {
      id: `${seed}-tl-${domain}`,
      title: domain,
      domain,
      date: addDays(project.start_date, 40 + i * 35),
      status,
      note:
        locale === 'tr'
          ? `${domain} kilometre taşı güncellemesi`
          : `${domain} milestone update`,
    };
  });

  const reports: DetailReportCard[] = (
    ['executive', 'construction', 'financial', 'sales', 'risk', 'investor'] as const
  ).map((key, i) => ({
    id: `${seed}-rep-${key}`,
    key,
    updatedAt: addDays(null, -i * 3 - 1),
    pages: 4 + (i % 5),
  }));

  const aiInsights: DetailAiInsight[] = [
    {
      id: 'delayPrediction',
      key: 'delayPrediction',
      score: Math.max(12, 100 - healthScore + hashIndex(seed, 10)),
      tone: risk === 'low' ? 'success' : risk === 'medium' ? 'warning' : 'danger',
      trend: risk === 'low' ? 'down' : 'up',
      delta: risk === 'low' ? '-4d' : '+9d',
    },
    {
      id: 'budgetRisk',
      key: 'budgetRisk',
      score: Math.round(spentRatio * 100) - completion + 18,
      tone: spentRatio > completion / 100 + 0.08 ? 'warning' : 'success',
      trend: 'neutral',
      delta: `${Math.round((spentRatio - completion / 100) * 100)}%`,
    },
    {
      id: 'cashFlowRisk',
      key: 'cashFlowRisk',
      score: 28 + hashIndex(seed, 40),
      tone: 'info',
      trend: 'down',
      delta: '-2.1%',
    },
    {
      id: 'salesForecast',
      key: 'salesForecast',
      score: 55 + hashIndex(seed, 30),
      tone: 'success',
      trend: 'up',
      delta: '+6.4%',
    },
    {
      id: 'investmentRecommendation',
      key: 'investmentRecommendation',
      score: healthScore,
      tone: healthScore >= 70 ? 'success' : 'warning',
      trend: 'up',
      delta: '+hold',
    },
    {
      id: 'completionConfidence',
      key: 'completionConfidence',
      score: aiConfidence,
      tone: aiConfidence >= 70 ? 'success' : 'warning',
      trend: 'up',
      delta: `+${Math.round(aiConfidence / 20)}%`,
    },
    {
      id: 'materialCostTrend',
      key: 'materialCostTrend',
      score: 40 + hashIndex(seed, 35),
      tone: 'warning',
      trend: 'up',
      delta: '+3.8%',
    },
    {
      id: 'suggestedActions',
      key: 'suggestedActions',
      score: 4 + hashIndex(seed, 3),
      tone: 'info',
      trend: 'neutral',
      delta: '4',
    },
  ];

  const revenue = num(project.projected_revenue, projectValue(project) * 1.15);
  const profit = num(project.projected_profit, revenue * 0.18);
  const expenses = Math.round(spent * 0.92);
  const loan = num(project.debt_amount, budget * 0.48);
  const cashFlow = Math.round(num(project.equity_raised, budget * 0.28) - spent * 0.18);

  return {
    id: project.id,
    name: project.project_name,
    code: project.project_code,
    location,
    city: project.city ?? location,
    developmentType: project.development_type,
    projectType: project.project_type,
    status: project.project_status,
    stage: project.development_stage,
    priority: project.priority,
    risk,
    coverScene: coverSceneFor(project),
    completion,
    healthScore,
    aiConfidence,
    investmentStatus: investmentStatusFor(project),
    lastUpdated: project.updated_at,
    description:
      project.description?.trim() ||
      (locale === 'tr'
        ? 'Kurumsal yönetişim, şeffaf bütçe disiplini ve sahadan satışa entegre operasyon ile yürütülen premium geliştirme projesi.'
        : 'Premium development operated with institutional governance, transparent budget discipline, and integrated field-to-sales execution.'),
    nextMilestone,
    currentPhase,
    manager,
    contractor: CONTRACTORS[hashIndex(seed, CONTRACTORS.length)]!,
    architect: ARCHITECTS[hashIndex(seed, ARCHITECTS.length)]!,
    constructionCompany: CONSTRUCTION_COS[hashIndex(seed, CONSTRUCTION_COS.length)]!,
    permitStatus: permitStatusFor(project, risk),
    upcomingInspection: addDays(null, 6 + hashIndex(seed, 10)),
    completionPrediction: project.target_completion_date ?? addDays(null, 260),
    weather: weatherFor(seed),
    kpis: {
      totalBudget: {
        value: formatCompactCurrency(budget, locale),
        delta: '+1.2%',
        deltaTone: 'up',
      },
      spent: {
        value: formatCompactCurrency(spent, locale),
        delta: `${Math.round(spentRatio * 100)}%`,
        deltaTone: 'neutral',
      },
      remaining: {
        value: formatCompactCurrency(remaining, locale),
        delta: remaining / budget < 0.2 ? '-8%' : '+1%',
        deltaTone: remaining / budget < 0.2 ? 'down' : 'neutral',
      },
      expectedRoi: {
        value: `${roi.toFixed(1)}%`,
        delta: '+0.4%',
        deltaTone: 'up',
      },
      units: {
        value: String(unitsTotal),
        delta: `+${units.filter((u) => u.status === 'sold').length}`,
        deltaTone: 'up',
      },
      investors: {
        value: String(investorsCount),
        delta: '+1',
        deltaTone: 'up',
      },
      completion: {
        value: `${completion}%`,
        delta: '+2%',
        deltaTone: 'up',
      },
      targetDelivery: {
        value: (project.target_completion_date ?? addDays(null, 260)).slice(0, 10),
        delta: '0d',
        deltaTone: 'neutral',
      },
    },
    financial: {
      budget,
      spent,
      remaining,
      forecast: Math.round(budget * 1.04),
      loan,
      cashFlow,
      roi,
      profit,
      revenue,
      expenses,
      series: buildSeries(seed, spentRatio),
    },
    milestones,
    units,
    investors,
    documents,
    docCategoryCounts,
    tasks,
    timeline,
    reports,
    aiInsights,
    upcomingTasks: tasks.filter((t) => t.status !== 'done').slice(0, 4),
    recentActivity: [
      {
        id: `${seed}-act-1`,
        title: locale === 'tr' ? 'İnşaat ilerlemesi güncellendi' : 'Construction progress updated',
        time: addDays(null, -1),
        tone: 'success' as StatusTone,
      },
      {
        id: `${seed}-act-2`,
        title: locale === 'tr' ? 'Bütçe varyansı incelendi' : 'Budget variance reviewed',
        time: addDays(null, -2),
        tone: 'warning' as StatusTone,
      },
      {
        id: `${seed}-act-3`,
        title: locale === 'tr' ? 'Yeni birim rezervasyonu' : 'New unit reservation logged',
        time: addDays(null, -3),
        tone: 'info' as StatusTone,
      },
      {
        id: `${seed}-act-4`,
        title: locale === 'tr' ? 'Ruhsat belgesi yüklendi' : 'Permit document uploaded',
        time: addDays(null, -4),
        tone: 'default' as StatusTone,
      },
    ],
    alerts: {
      ai: [
        {
          id: 'ai-1',
          textKey: risk === 'low' ? 'stableDelivery' : 'watchSchedule',
          tone: risk === 'low' ? 'success' : 'warning',
        },
        {
          id: 'ai-2',
          textKey: 'materialWatch',
          tone: 'info',
        },
      ],
      budget: [
        {
          id: 'bud-1',
          textKey: spentRatio > 0.7 ? 'spendAcceleration' : 'spendOnPlan',
          tone: spentRatio > 0.7 ? 'warning' : 'success',
        },
      ],
      construction: [
        {
          id: 'con-1',
          textKey: 'inspectionDue',
          tone: 'info',
        },
        {
          id: 'con-2',
          textKey: risk === 'high' || risk === 'critical' ? 'crewBottleneck' : 'crewStable',
          tone: risk === 'high' || risk === 'critical' ? 'warning' : 'success',
        },
      ],
    },
  };
}

export { statusTone, priorityTone, formatCompactCurrency };
