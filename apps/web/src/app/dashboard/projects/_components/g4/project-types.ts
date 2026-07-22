import type { Project, ProjectStatus } from '@/lib/api/projects';

/**
 * G4 product portfolio types (TR+EN). Mapped onto backend ProjectStatus values.
 * Spec types: Acquisition, Development, Construction, Renovation, Conversion,
 * Stabilization, Leasing, Closing, Completed, On Hold, Cancelled.
 */
export const PROJECT_PORTFOLIO_TYPES = [
  'acquisition',
  'development',
  'construction',
  'renovation',
  'conversion',
  'stabilization',
  'leasing',
  'closing',
  'completed',
  'on_hold',
  'cancelled',
] as const;

export type ProjectPortfolioType = (typeof PROJECT_PORTFOLIO_TYPES)[number];

export type StageTone = 'info' | 'warn' | 'success' | 'danger' | 'neutral';

export const PORTFOLIO_TYPE_META: {
  id: ProjectPortfolioType;
  tone: StageTone;
}[] = [
  { id: 'acquisition', tone: 'info' },
  { id: 'development', tone: 'info' },
  { id: 'construction', tone: 'warn' },
  { id: 'renovation', tone: 'warn' },
  { id: 'conversion', tone: 'warn' },
  { id: 'stabilization', tone: 'success' },
  { id: 'leasing', tone: 'success' },
  { id: 'closing', tone: 'info' },
  { id: 'completed', tone: 'success' },
  { id: 'on_hold', tone: 'neutral' },
  { id: 'cancelled', tone: 'danger' },
];

/** Map backend project_status (+ development_type hints) → G4 portfolio type. */
const STATUS_TO_PORTFOLIO: Record<string, ProjectPortfolioType> = {
  pipeline: 'acquisition',
  due_diligence: 'acquisition',
  acquisition: 'acquisition',
  pre_development: 'development',
  permitting: 'development',
  construction: 'construction',
  leasing: 'leasing',
  sales: 'closing',
  stabilization: 'stabilization',
  completed: 'completed',
  on_hold: 'on_hold',
  cancelled: 'cancelled',
};

const DEV_TYPE_OVERRIDE: Record<string, ProjectPortfolioType> = {
  renovation: 'renovation',
  conversion: 'conversion',
  fix_and_flip: 'renovation',
  value_add: 'renovation',
};

export function toPortfolioType(project: Project): ProjectPortfolioType {
  if (project.project_status === 'construction' || project.project_status === 'permitting') {
    const override = project.development_type
      ? DEV_TYPE_OVERRIDE[project.development_type]
      : undefined;
    if (override) return override;
  }
  if (project.development_type && DEV_TYPE_OVERRIDE[project.development_type]) {
    if (
      project.project_status === 'pre_development' ||
      project.project_status === 'construction' ||
      project.project_status === 'pipeline'
    ) {
      return DEV_TYPE_OVERRIDE[project.development_type]!;
    }
  }
  return STATUS_TO_PORTFOLIO[project.project_status] ?? 'development';
}

/** Prefer a persistable ProjectStatus when moving on the portfolio board. */
export function portfolioTypeAsStatus(type: ProjectPortfolioType): ProjectStatus {
  const map: Record<ProjectPortfolioType, ProjectStatus> = {
    acquisition: 'acquisition',
    development: 'pre_development',
    construction: 'construction',
    renovation: 'construction',
    conversion: 'construction',
    stabilization: 'stabilization',
    leasing: 'leasing',
    closing: 'sales',
    completed: 'completed',
    on_hold: 'on_hold',
    cancelled: 'cancelled',
  };
  return map[type];
}

export function projectValue(project: Project): number {
  const raw =
    project.current_project_value ??
    project.total_development_cost ??
    project.construction_budget ??
    project.projected_sale_value;
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

export function projectCompletion(project: Project): number {
  const n = Number(project.completion_percentage);
  if (!Number.isFinite(n)) return 0;
  return Math.min(100, Math.max(0, n));
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[parts.length - 1]![0] ?? ''}`.toUpperCase();
}

export type ProjectViewId =
  | 'portfolio'
  | 'board'
  | 'tasks'
  | 'timeline'
  | 'milestones'
  | 'budget'
  | 'contractors'
  | 'permits'
  | 'inspections'
  | 'issues'
  | 'documents'
  | 'change_orders'
  | 'analytics'
  | 'activity';

export const PROJECT_VIEWS: ProjectViewId[] = [
  'portfolio',
  'board',
  'tasks',
  'timeline',
  'milestones',
  'budget',
  'contractors',
  'permits',
  'inspections',
  'issues',
  'documents',
  'change_orders',
  'analytics',
  'activity',
];

export function parseView(value: string | null | undefined): ProjectViewId {
  if (value && (PROJECT_VIEWS as string[]).includes(value)) {
    return value as ProjectViewId;
  }
  return 'portfolio';
}

export type PortfolioLayout = 'grid' | 'list' | 'table';

export function parseLayout(value: string | null | undefined): PortfolioLayout {
  if (value === 'list' || value === 'table' || value === 'grid') return value;
  return 'grid';
}
