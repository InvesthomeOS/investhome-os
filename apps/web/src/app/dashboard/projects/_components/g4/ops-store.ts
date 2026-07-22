import type { Project } from '@/lib/api/projects';

import {
  DEFAULT_MILESTONES,
  type ChangeOrderLocal,
  type ConstructionStage,
  type ConstructionTask,
  type InspectionRecord,
  type MilestoneRecord,
  type PermitRecord,
  type RiskRecord,
  type TaskPriority,
} from './construction-domain';

const TASKS_KEY = 'investhome.projects.g4.tasks.v1';
const PERMITS_KEY = 'investhome.projects.g4.permits.v1';
const INSPECTIONS_KEY = 'investhome.projects.g4.inspections.v1';
const RISKS_KEY = 'investhome.projects.g4.risks.v1';
const COS_KEY = 'investhome.projects.g4.change-orders.v1';
const MILESTONES_KEY = 'investhome.projects.g4.milestones.v1';

function read<T>(key: string): T[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as T[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write<T>(key: string, items: T[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, JSON.stringify(items));
}

function uid(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function seedTasks(projects: Project[]): ConstructionTask[] {
  const stages: ConstructionStage[] = [
    'planned',
    'ready',
    'in_progress',
    'blocked',
    'review',
    'inspection',
    'completed',
  ];
  const priorities: TaskPriority[] = ['low', 'medium', 'high', 'urgent'];
  const titles = [
    'Foundation pour — zone A',
    'MEP rough-in Level 2',
    'Facade panel install',
    'Permit follow-up — municipality',
    'Safety inspection prep',
    'Punch list walkthrough',
    'Concrete curing check',
    'Window delivery coordination',
  ];
  const now = new Date().toISOString();
  const tasks: ConstructionTask[] = [];
  const pool = projects.slice(0, 6);
  if (pool.length === 0) return tasks;

  titles.forEach((title, idx) => {
    const project = pool[idx % pool.length]!;
    const due = new Date();
    due.setDate(due.getDate() + ((idx % 14) - 3));
    tasks.push({
      id: uid('task'),
      key: `${project.project_code}-${String(idx + 1).padStart(3, '0')}`,
      projectId: project.id,
      projectName: project.project_name,
      title,
      description: 'Operational construction work item (workspace store — no native task API yet).',
      stage: stages[idx % stages.length]!,
      priority: priorities[idx % priorities.length]!,
      type: idx % 5 === 0 ? 'inspection' : idx % 4 === 0 ? 'permit' : 'task',
      assignee: project.project_manager?.full_name ?? project.assigned_project_manager ?? 'Unassigned',
      dueDate: due.toISOString().slice(0, 10),
      labels: idx % 2 === 0 ? ['structure'] : ['mep'],
      blockers: idx % 3 === 0 ? 1 : 0,
      estimatedHours: 8 + (idx % 5) * 4,
      actualHours: idx % 2 === 0 ? 6 : null,
      createdAt: now,
      updatedAt: now,
    });
  });
  return tasks;
}

export function listTasks(projects?: Project[]): ConstructionTask[] {
  let items = read<ConstructionTask>(TASKS_KEY);
  if (items.length === 0 && projects && projects.length > 0) {
    items = seedTasks(projects);
    write(TASKS_KEY, items);
  }
  return items;
}

export function saveTasks(items: ConstructionTask[]) {
  write(TASKS_KEY, items);
}

export function updateTaskStage(id: string, stage: ConstructionStage): ConstructionTask | null {
  const items = listTasks();
  const idx = items.findIndex((t) => t.id === id);
  if (idx < 0) return null;
  const next = { ...items[idx]!, stage, updatedAt: new Date().toISOString() };
  items[idx] = next;
  saveTasks(items);
  return next;
}

export function upsertTask(task: ConstructionTask) {
  const items = listTasks();
  const idx = items.findIndex((t) => t.id === task.id);
  if (idx >= 0) items[idx] = task;
  else items.unshift(task);
  saveTasks(items);
}

export function createTask(input: Omit<ConstructionTask, 'id' | 'createdAt' | 'updatedAt' | 'key'> & { key?: string }): ConstructionTask {
  const now = new Date().toISOString();
  const task: ConstructionTask = {
    ...input,
    id: uid('task'),
    key: input.key ?? `TASK-${Date.now().toString().slice(-5)}`,
    createdAt: now,
    updatedAt: now,
  };
  upsertTask(task);
  return task;
}

function seedPermits(projects: Project[]): PermitRecord[] {
  return projects.slice(0, 4).map((p, i) => ({
    id: uid('permit'),
    projectId: p.id,
    projectName: p.project_name,
    name: i % 2 === 0 ? 'Building permit' : 'Occupancy permit',
    authority: 'Municipality',
    status: (['submitted', 'under_review', 'approved', 'draft'] as const)[i % 4]!,
    submittedAt: new Date().toISOString().slice(0, 10),
    expiresAt: null,
    notes: 'Local workspace record — permits API not available.',
  }));
}

export function listPermits(projects?: Project[]): PermitRecord[] {
  let items = read<PermitRecord>(PERMITS_KEY);
  if (items.length === 0 && projects && projects.length > 0) {
    items = seedPermits(projects);
    write(PERMITS_KEY, items);
  }
  return items;
}

function seedInspections(projects: Project[]): InspectionRecord[] {
  return projects.slice(0, 4).map((p, i) => ({
    id: uid('insp'),
    projectId: p.id,
    projectName: p.project_name,
    name: i % 2 === 0 ? 'Structural inspection' : 'Fire safety inspection',
    inspector: 'City inspector',
    status: (['scheduled', 'passed', 'failed', 'conditional'] as const)[i % 4]!,
    scheduledAt: new Date().toISOString().slice(0, 10),
    resultNotes: 'Local workspace record — inspections API not available.',
  }));
}

export function listInspections(projects?: Project[]): InspectionRecord[] {
  let items = read<InspectionRecord>(INSPECTIONS_KEY);
  if (items.length === 0 && projects && projects.length > 0) {
    items = seedInspections(projects);
    write(INSPECTIONS_KEY, items);
  }
  return items;
}

function seedRisks(projects: Project[]): RiskRecord[] {
  return projects.slice(0, 3).map((p, i) => ({
    id: uid('risk'),
    projectId: p.id,
    projectName: p.project_name,
    title: i === 0 ? 'Weather delay on concrete' : i === 1 ? 'Material lead-time risk' : 'Permit timeline slip',
    severity: (['medium', 'high', 'critical'] as const)[i % 3]!,
    status: (['open', 'mitigating', 'open'] as const)[i % 3]!,
    owner: p.project_manager?.full_name ?? 'PM',
    dueDate: new Date().toISOString().slice(0, 10),
    mitigation: 'Tracked in workspace store; backend risk register pending.',
  }));
}

export function listRisks(projects?: Project[]): RiskRecord[] {
  let items = read<RiskRecord>(RISKS_KEY);
  if (items.length === 0 && projects && projects.length > 0) {
    items = seedRisks(projects);
    write(RISKS_KEY, items);
  }
  return items;
}

export function listLocalChangeOrders(projects?: Project[]): ChangeOrderLocal[] {
  let items = read<ChangeOrderLocal>(COS_KEY);
  if (items.length === 0 && projects && projects.length > 0) {
    items = projects.slice(0, 3).map((p, i) => ({
      id: uid('co'),
      projectId: p.id,
      projectName: p.project_name,
      number: `CO-${String(i + 1).padStart(3, '0')}`,
      title: i === 0 ? 'Extra excavation' : i === 1 ? 'Facade revision' : 'MEP upgrade',
      status: (['draft', 'submitted', 'approved'] as const)[i % 3]!,
      amount: 25000 + i * 12000,
      currency: p.currency || 'USD',
      vendor: 'General contractor',
      createdAt: new Date().toISOString(),
    }));
    write(COS_KEY, items);
  }
  return items;
}

export function listMilestonesForProject(projectId: string, projectName?: string): MilestoneRecord[] {
  void projectName;
  const all = read<MilestoneRecord>(MILESTONES_KEY);
  let items = all.filter((m) => m.projectId === projectId);
  if (items.length === 0) {
    items = DEFAULT_MILESTONES.map((d) => ({
      id: uid('ms'),
      projectId,
      key: d.key,
      title: d.key,
      status: d.order <= 3 ? 'completed' : d.order === 4 ? 'in_progress' : d.order === 5 ? 'at_risk' : 'not_started',
      targetDate: null,
      actualDate: d.order <= 3 ? new Date().toISOString().slice(0, 10) : null,
      isDefault: true,
      order: d.order,
      notes: '',
    }));
    write(MILESTONES_KEY, [...all, ...items]);
  }
  return items.sort((a, b) => a.order - b.order);
}

export function updateMilestoneStatus(id: string, status: MilestoneRecord['status']) {
  const all = read<MilestoneRecord>(MILESTONES_KEY);
  const idx = all.findIndex((m) => m.id === id);
  if (idx < 0) return;
  all[idx] = {
    ...all[idx]!,
    status,
    actualDate: status === 'completed' ? new Date().toISOString().slice(0, 10) : all[idx]!.actualDate,
  };
  write(MILESTONES_KEY, all);
}

export function addCustomMilestone(projectId: string, title: string): MilestoneRecord {
  const all = read<MilestoneRecord>(MILESTONES_KEY);
  const existing = all.filter((m) => m.projectId === projectId);
  const ms: MilestoneRecord = {
    id: uid('ms'),
    projectId,
    key: `custom_${Date.now()}`,
    title,
    status: 'not_started',
    targetDate: null,
    actualDate: null,
    isDefault: false,
    order: existing.length + 1,
    notes: '',
  };
  write(MILESTONES_KEY, [...all, ms]);
  return ms;
}
