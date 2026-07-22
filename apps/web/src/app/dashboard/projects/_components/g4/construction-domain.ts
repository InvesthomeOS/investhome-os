export const CONSTRUCTION_STAGES = [
  'planned',
  'ready',
  'in_progress',
  'blocked',
  'review',
  'inspection',
  'completed',
] as const;

export type ConstructionStage = (typeof CONSTRUCTION_STAGES)[number];

export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';

export type TaskType =
  | 'task'
  | 'issue'
  | 'inspection'
  | 'permit'
  | 'change_order'
  | 'risk';

export interface ConstructionTask {
  id: string;
  key: string;
  projectId: string;
  projectName: string;
  title: string;
  description: string;
  stage: ConstructionStage;
  priority: TaskPriority;
  type: TaskType;
  assignee: string;
  dueDate: string | null;
  labels: string[];
  blockers: number;
  estimatedHours: number | null;
  actualHours: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface PermitRecord {
  id: string;
  projectId: string;
  projectName: string;
  name: string;
  authority: string;
  status: 'draft' | 'submitted' | 'under_review' | 'approved' | 'rejected' | 'expired';
  submittedAt: string | null;
  expiresAt: string | null;
  notes: string;
}

export interface InspectionRecord {
  id: string;
  projectId: string;
  projectName: string;
  name: string;
  inspector: string;
  status: 'scheduled' | 'passed' | 'failed' | 'conditional' | 'cancelled';
  scheduledAt: string | null;
  resultNotes: string;
}

export interface RiskRecord {
  id: string;
  projectId: string;
  projectName: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'open' | 'mitigating' | 'accepted' | 'closed';
  owner: string;
  dueDate: string | null;
  mitigation: string;
}

export interface ChangeOrderLocal {
  id: string;
  projectId: string;
  projectName: string;
  number: string;
  title: string;
  status: 'draft' | 'submitted' | 'approved' | 'rejected' | 'cancelled';
  amount: number;
  currency: string;
  vendor: string;
  createdAt: string;
}

export type MilestoneStatus =
  | 'not_started'
  | 'in_progress'
  | 'at_risk'
  | 'completed'
  | 'skipped';

export interface MilestoneRecord {
  id: string;
  projectId: string;
  key: string;
  title: string;
  status: MilestoneStatus;
  targetDate: string | null;
  actualDate: string | null;
  isDefault: boolean;
  order: number;
  notes: string;
}

/** 20 default construction milestones (product default set). */
export const DEFAULT_MILESTONES: { key: string; order: number }[] = [
  { key: 'site_survey', order: 1 },
  { key: 'design_freeze', order: 2 },
  { key: 'permit_application', order: 3 },
  { key: 'permit_approval', order: 4 },
  { key: 'groundbreaking', order: 5 },
  { key: 'foundation', order: 6 },
  { key: 'structure', order: 7 },
  { key: 'envelope', order: 8 },
  { key: 'mep_rough_in', order: 9 },
  { key: 'insulation', order: 10 },
  { key: 'drywall', order: 11 },
  { key: 'finishes', order: 12 },
  { key: 'mep_final', order: 13 },
  { key: 'landscaping', order: 14 },
  { key: 'punch_list', order: 15 },
  { key: 'final_inspection', order: 16 },
  { key: 'certificate_occupancy', order: 17 },
  { key: 'handover', order: 18 },
  { key: 'warranty_start', order: 19 },
  { key: 'stabilization', order: 20 },
];

export const STAGE_META: { id: ConstructionStage; tone: string }[] = [
  { id: 'planned', tone: 'neutral' },
  { id: 'ready', tone: 'info' },
  { id: 'in_progress', tone: 'warn' },
  { id: 'blocked', tone: 'danger' },
  { id: 'review', tone: 'info' },
  { id: 'inspection', tone: 'warn' },
  { id: 'completed', tone: 'success' },
];
