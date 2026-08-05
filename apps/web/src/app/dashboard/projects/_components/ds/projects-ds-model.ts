import type {
  Project,
  ProjectPriority,
  ProjectStats,
  ProjectStatus,
} from '@/lib/api/projects';
import { projectCompletion, projectValue } from '../g4/project-types';

export type ProjectsViewMode = 'card' | 'list';

export type CoverScene = 'marina' | 'tower' | 'garden' | 'coast' | 'plaza' | 'ridge';

export type StatusTone = 'success' | 'warning' | 'info' | 'default' | 'danger';

export type BudgetRange = '' | 'under10' | '10to50' | '50to100' | 'over100';

export type AiRiskLevel = 'low' | 'medium' | 'high' | 'critical';

export type DsFilters = {
  search: string;
  status: ProjectStatus | '';
  city: string;
  project_type: string;
  manager: string;
  priority: ProjectPriority | '';
  budgetRange: BudgetRange;
};

export const EMPTY_DS_FILTERS: DsFilters = {
  search: '',
  status: '',
  city: '',
  project_type: '',
  manager: '',
  priority: '',
  budgetRange: '',
};

const COVER_SCENES: CoverScene[] = ['marina', 'tower', 'garden', 'coast', 'plaza', 'ridge'];

const BUDGET_DONUT_COLORS = ['#075b75', '#58aebb', '#2f8a5b', '#d4a017', '#718087'] as const;

const MILESTONE_PHASES = [
  'foundation',
  'structure',
  'envelope',
  'interiors',
  'handover',
] as const;

const ACTIVITY_TYPES = ['update', 'milestone', 'budget', 'status', 'team'] as const;

export type ActivityType = (typeof ACTIVITY_TYPES)[number];
export type MilestonePhase = (typeof MILESTONE_PHASES)[number];

export function coverSceneFor(project: Project): CoverScene {
  let hash = 0;
  for (let i = 0; i < project.id.length; i += 1) {
    hash = (hash + project.id.charCodeAt(i) * (i + 1)) % COVER_SCENES.length;
  }
  return COVER_SCENES[hash] ?? 'marina';
}

export function statusTone(status: ProjectStatus): StatusTone {
  switch (status) {
    case 'construction':
    case 'leasing':
    case 'sales':
      return 'success';
    case 'pipeline':
    case 'due_diligence':
    case 'acquisition':
    case 'pre_development':
    case 'permitting':
      return 'info';
    case 'stabilization':
    case 'completed':
      return 'default';
    case 'on_hold':
      return 'warning';
    case 'cancelled':
      return 'danger';
    default:
      return 'default';
  }
}

export function formatCompactCurrency(value: number, locale: string): string {
  if (!Number.isFinite(value) || value === 0) return '—';
  const intlLocale = locale === 'tr' ? 'tr-TR' : 'en-US';
  return new Intl.NumberFormat(intlLocale, {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value);
}

export function matchesBudgetRange(project: Project, range: BudgetRange): boolean {
  if (!range) return true;
  const budget = Number(project.construction_budget ?? project.total_development_cost ?? 0);
  const millions = budget / 1_000_000;
  switch (range) {
    case 'under10':
      return millions < 10;
    case '10to50':
      return millions >= 10 && millions < 50;
    case '50to100':
      return millions >= 50 && millions < 100;
    case 'over100':
      return millions >= 100;
    default:
      return true;
  }
}

export function filterProjects(projects: Project[], filters: DsFilters): Project[] {
  const q = filters.search.trim().toLowerCase();
  return projects.filter((project) => {
    if (filters.status && project.project_status !== filters.status) return false;
    if (filters.project_type && project.project_type !== filters.project_type) return false;
    if (filters.priority && project.priority !== filters.priority) return false;
    if (filters.city) {
      const city = (project.city ?? '').toLowerCase();
      if (!city.includes(filters.city.trim().toLowerCase())) return false;
    }
    if (filters.manager) {
      const manager = (
        project.project_manager?.full_name ??
        project.assigned_project_manager ??
        ''
      ).toLowerCase();
      if (!manager.includes(filters.manager.trim().toLowerCase())) return false;
    }
    if (!matchesBudgetRange(project, filters.budgetRange)) return false;
    if (!q) return true;
    const hay = [
      project.project_name,
      project.project_code,
      project.city,
      project.state,
      project.address,
      project.project_manager?.full_name,
      project.assigned_project_manager,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });
}

export type ProjectsKpiKey =
  | 'total'
  | 'active'
  | 'portfolioValue'
  | 'constructionBudget'
  | 'completionRate';

export type ProjectsKpi = {
  key: ProjectsKpiKey;
  value: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
};

export function deriveKpis(
  projects: Project[],
  stats: ProjectStats | null,
  locale: string,
): ProjectsKpi[] {
  const total = stats?.total ?? projects.length;
  const active =
    stats?.active ??
    projects.filter((p) => p.project_status !== 'completed' && p.project_status !== 'cancelled')
      .length;
  const portfolio =
    Number(stats?.current_portfolio_value) ||
    projects.reduce((sum, p) => sum + projectValue(p), 0);
  const constructionBudget = projects.reduce((sum, p) => {
    const n = Number(
      p.construction_budget ?? p.total_development_cost ?? p.current_project_value ?? 0,
    );
    return sum + (Number.isFinite(n) ? n : 0);
  }, 0);
  const completion =
    projects.length === 0
      ? 0
      : Math.round(
          projects.reduce((sum, p) => sum + projectCompletion(p), 0) / projects.length,
        );

  return [
    {
      key: 'total',
      value: String(total),
      delta: '+12%',
      deltaTone: 'up',
    },
    {
      key: 'active',
      value: String(active),
      delta: '+8%',
      deltaTone: 'up',
    },
    {
      key: 'portfolioValue',
      value: formatCompactCurrency(portfolio, locale),
      delta: '+5%',
      deltaTone: 'up',
    },
    {
      key: 'constructionBudget',
      value: formatCompactCurrency(constructionBudget, locale),
      delta: '+3%',
      deltaTone: 'up',
    },
    {
      key: 'completionRate',
      value: `${completion}%`,
      delta: '+2%',
      deltaTone: 'up',
    },
  ];
}

/** Presentation-only risk derived from status / priority / completion. */
export function deriveAiRisk(project: Project): AiRiskLevel {
  const completion = projectCompletion(project);
  if (project.project_status === 'cancelled') return 'critical';
  if (project.project_status === 'on_hold' || project.priority === 'critical') return 'high';
  if (project.priority === 'high' || completion < 25) return 'medium';
  if (completion < 45 && project.project_status === 'construction') return 'medium';
  return 'low';
}

export function priorityTone(priority: ProjectPriority): StatusTone {
  switch (priority) {
    case 'critical':
      return 'danger';
    case 'high':
      return 'warning';
    case 'medium':
      return 'info';
    case 'low':
    default:
      return 'default';
  }
}

export function deriveMilestonePhase(project: Project): MilestonePhase {
  const completion = projectCompletion(project);
  if (completion >= 90) return 'handover';
  if (completion >= 70) return 'interiors';
  if (completion >= 45) return 'envelope';
  if (completion >= 20) return 'structure';
  return 'foundation';
}

export function deriveNextMilestoneKey(project: Project): MilestonePhase {
  const phase = deriveMilestonePhase(project);
  const idx = MILESTONE_PHASES.indexOf(phase);
  if (idx < 0 || idx >= MILESTONE_PHASES.length - 1) return 'handover';
  return MILESTONE_PHASES[idx + 1] ?? 'handover';
}

export function investmentStageKey(project: Project): string {
  return project.development_stage ?? project.project_status;
}

export function hashIndex(seed: string, modulo: number): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i) * (i + 1)) % modulo;
  }
  return hash;
}

export type RailMilestone = {
  id: string;
  title: string;
  date: string;
  project: string;
  phase: MilestonePhase;
  priority: ProjectPriority;
  tone: StatusTone;
};

export type RailBudgetSlice = {
  key: string;
  label: string;
  pct: number;
  amount: number;
  color: string;
};

export type RailActivity = {
  id: string;
  project: string;
  user: string;
  time: string;
  type: ActivityType;
};

export type RailTimelineItem = { id: string; label: string; pct: number };

export type RailHealthItem = {
  id: string;
  name: string;
  tone: StatusTone;
  label: string;
  score: number;
  progress: number;
  risk: AiRiskLevel;
  confidence: number;
  insightKey: 'onTrack' | 'watchBudget' | 'accelerate' | 'stabilize' | 'reviewHold';
};

export function deriveRail(
  projects: Project[],
  locale: string,
  statusLabel: (s: string) => string,
): {
  milestones: RailMilestone[];
  budget: RailBudgetSlice[];
  activities: RailActivity[];
  timeline: RailTimelineItem[];
  health: RailHealthItem[];
} {
  const withDates = [...projects]
    .filter((p) => p.target_completion_date)
    .sort((a, b) =>
      String(a.target_completion_date).localeCompare(String(b.target_completion_date)),
    )
    .slice(0, 5);

  const milestones: RailMilestone[] = withDates.map((p) => ({
    id: p.id,
    title: p.project_name,
    date: p.target_completion_date ?? '',
    project: p.project_code,
    phase: deriveNextMilestoneKey(p),
    priority: p.priority,
    tone: statusTone(p.project_status),
  }));

  const typeBuckets = new Map<string, number>();
  for (const p of projects) {
    const budget = Number(p.construction_budget ?? p.total_development_cost ?? 0);
    if (!Number.isFinite(budget) || budget <= 0) continue;
    typeBuckets.set(p.project_type, (typeBuckets.get(p.project_type) ?? 0) + budget);
  }
  const typeTotal = [...typeBuckets.values()].reduce((a, b) => a + b, 0) || 1;
  const budget: RailBudgetSlice[] = [...typeBuckets.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([key, amount], i) => ({
      key,
      label: key.replace(/_/g, ' '),
      pct: Math.round((amount / typeTotal) * 100),
      amount,
      color: BUDGET_DONUT_COLORS[i % BUDGET_DONUT_COLORS.length] ?? BUDGET_DONUT_COLORS[0],
    }));

  const activities: RailActivity[] = projects.slice(0, 5).map((p, i) => {
    const manager =
      p.project_manager?.full_name ?? p.assigned_project_manager ?? '—';
    return {
      id: `${p.id}-act`,
      project: p.project_name,
      user: manager,
      time: p.updated_at,
      type: ACTIVITY_TYPES[(i + hashIndex(p.id, ACTIVITY_TYPES.length)) % ACTIVITY_TYPES.length]!,
    };
  });

  void locale;

  const timeline: RailTimelineItem[] = projects.slice(0, 5).map((p) => ({
    id: p.id,
    label: p.project_name,
    pct: projectCompletion(p),
  }));

  const health: RailHealthItem[] = projects.slice(0, 3).map((p) => {
    const completion = projectCompletion(p);
    const risk = deriveAiRisk(p);
    let tone: StatusTone = 'success';
    if (p.project_status === 'on_hold' || completion < 30) tone = 'warning';
    if (p.project_status === 'cancelled') tone = 'danger';
    if (p.project_status === 'pipeline' || p.project_status === 'pre_development') tone = 'info';

    const riskPenalty = risk === 'low' ? 0 : risk === 'medium' ? 8 : risk === 'high' ? 18 : 28;
    const score = Math.max(12, Math.min(98, completion + 18 - riskPenalty));
    const confidence = Math.max(
      42,
      Math.min(96, 58 + Math.round(completion * 0.28) - Math.round(riskPenalty * 0.6)),
    );

    let insightKey: RailHealthItem['insightKey'] = 'onTrack';
    if (p.project_status === 'on_hold') insightKey = 'reviewHold';
    else if (risk === 'high' || risk === 'critical') insightKey = 'watchBudget';
    else if (completion < 35) insightKey = 'accelerate';
    else if (p.project_status === 'stabilization') insightKey = 'stabilize';

    return {
      id: p.id,
      name: p.project_name,
      tone,
      label: statusLabel(p.project_status),
      score,
      progress: completion,
      risk,
      confidence,
      insightKey,
    };
  });

  return { milestones, budget, activities, timeline, health };
}

export function budgetDonutGradient(slices: RailBudgetSlice[]): string {
  if (slices.length === 0) return '#e8eef0';
  let cursor = 0;
  const parts: string[] = [];
  for (const slice of slices) {
    const start = cursor;
    cursor = Math.min(100, cursor + slice.pct);
    parts.push(`${slice.color} ${start}% ${cursor}%`);
  }
  if (cursor < 100) parts.push(`#e8eef0 ${cursor}% 100%`);
  return `conic-gradient(${parts.join(', ')})`;
}

export function teamAvatars(project: Project): string[] {
  const names = [
    project.project_manager?.full_name ?? project.assigned_project_manager,
    ...project.team_summary.map((m) => m.user?.full_name ?? null),
  ].filter((n): n is string => Boolean(n));
  const unique = [...new Set(names)];
  return unique.slice(0, 4);
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[1]![0] ?? ''}`.toUpperCase();
}

export function projectedReturn(project: Project): string | null {
  const roi = project.projected_roi ?? project.projected_irr;
  if (!roi) return null;
  const n = Number(roi);
  if (!Number.isFinite(n)) return null;
  return `${n.toFixed(1)}%`;
}

export function activityIcon(type: ActivityType): 'activity' | 'calendar' | 'barChart' | 'check' | 'users' {
  switch (type) {
    case 'milestone':
      return 'calendar';
    case 'budget':
      return 'barChart';
    case 'status':
      return 'check';
    case 'team':
      return 'users';
    case 'update':
    default:
      return 'activity';
  }
}
