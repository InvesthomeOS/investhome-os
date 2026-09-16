export type TaskStatusKey = 'open' | 'inProgress' | 'completed' | 'waiting' | 'cancelled';

export type TaskPriorityKey = 'low' | 'medium' | 'high' | 'critical';

export type TaskKanbanColumnKey = 'todo' | 'inProgress' | 'review' | 'completed';

export type TaskViewMode = 'list' | 'card' | 'kanban';

export type TaskKpiKey = 'open' | 'dueToday' | 'overdue' | 'completed';

export type TaskAiActionKey =
  | 'sortByPriority'
  | 'dueToday'
  | 'showOverdue'
  | 'createPlan';

export type TaskRow = {
  id: string;
  titleKey: string;
  title?: string;
  descriptionKey: string;
  description?: string;
  customer: string;
  customerId?: string;
  project: string;
  dueLabelKey: string;
  dueLabel?: string;
  dueTone: 'today' | 'soon' | 'overdue' | 'done' | 'neutral';
  priority: TaskPriorityKey;
  status: TaskStatusKey;
  kanbanColumn: TaskKanbanColumnKey;
  assignee: string;
  assigneeId?: string;
  assigneeInitials: string;
  tag: string;
  aiNoteKey: string;
  aiNote?: string;
  checked?: boolean;
};

export type TaskKpi = {
  key: TaskKpiKey;
  value: number;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
  hintKey: string;
};

export type TaskDaySummary = {
  open: number;
  dueToday: number;
  overdue: number;
  assessmentKey: string;
};

export type TaskPriorityItem = {
  id: string;
  titleKey: string;
  title?: string;
  dueLabelKey: string;
  dueLabel?: string;
};

export type TaskDeadlineItem = {
  id: string;
  titleKey: string;
  dueLabelKey: string;
};

export type TaskAiRecommendation = {
  id: string;
  bodyKey: string;
};

export type TaskTeamPerformance = {
  id: string;
  name: string;
  completed: number;
  total: number;
};

export type TaskWorkspacePreview = {
  totalTasks: number;
  kpis: TaskKpi[];
  daySummary: TaskDaySummary;
  tasks: TaskRow[];
  customers: string[];
  assignees: string[];
  projects: string[];
  tags: string[];
  todayPriorities: TaskPriorityItem[];
  upcomingDeadlines: TaskDeadlineItem[];
  aiRecommendations: TaskAiRecommendation[];
  teamPerformance: TaskTeamPerformance[];
};

export const TASK_STATUS_ORDER: TaskStatusKey[] = [
  'open',
  'inProgress',
  'waiting',
  'completed',
  'cancelled',
];

export const TASK_PRIORITY_ORDER: TaskPriorityKey[] = [
  'low',
  'medium',
  'high',
  'critical',
];

export const TASK_KANBAN_COLUMNS: TaskKanbanColumnKey[] = [
  'todo',
  'inProgress',
  'review',
  'completed',
];

export const TASK_PRIORITY_WEIGHT: Record<TaskPriorityKey, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};
