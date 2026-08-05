import type { IhIconName } from '@/components/icons/ih-icons';

export type AdminAiActionKey =
  | 'newUser'
  | 'createRole'
  | 'systemScan'
  | 'auditLog';

export type AdminKpiKey =
  | 'activeUsers'
  | 'onlineUsers'
  | 'uptime'
  | 'openAlerts'
  | 'apiRequests';

export type AdminTabKey =
  | 'users'
  | 'roles'
  | 'workspacePermissions'
  | 'auditLog'
  | 'services';

export type AdminRoleKey =
  | 'systemAdmin'
  | 'admin'
  | 'salesManager'
  | 'salesRep'
  | 'analyst'
  | 'support'
  | 'marketing';

export type AdminStatusKey = 'active' | 'inactive' | 'suspended';

export type AdminWorkspaceKey =
  | 'crm'
  | 'sales'
  | 'finance'
  | 'marketing'
  | 'operations'
  | 'platform';

export type AdminLastLoginKey =
  | 'now'
  | 'today'
  | 'yesterday'
  | 'week'
  | 'month'
  | 'never';

export type AdminAvatarTone = 'navy' | 'cyan' | 'green' | 'amber' | 'violet' | 'rose';

export type AdminServiceKey = 'api' | 'web' | 'database' | 'queue' | 'storage';

export type AdminQueueKey = 'mail' | 'notification' | 'import' | 'ai';

export type AdminUserRow = {
  id: string;
  name: string;
  email: string;
  initials: string;
  avatarTone: AdminAvatarTone;
  role: AdminRoleKey;
  workspace: AdminWorkspaceKey;
  lastLoginLabel: string;
  lastLoginOnline?: boolean;
  status: AdminStatusKey;
  mfaEnabled: boolean;
  aiUsed: number;
  aiLimit: number;
  aiUsedLabel: string;
  aiLimitLabel: string;
};

export type AdminRoleRow = {
  id: string;
  role: AdminRoleKey;
  users: number;
  descriptionKey: string;
};

export type AdminPermissionRow = {
  id: string;
  workspace: AdminWorkspaceKey;
  role: AdminRoleKey;
  accessKey: string;
};

export type AdminAuditRow = {
  id: string;
  eventKey: string;
  actor: string;
  timeLabel: string;
};

export type AdminServiceRow = {
  id: string;
  service: AdminServiceKey;
  statusKey: 'running' | 'degraded' | 'down';
  detail: string;
};

export type AdminHealthItem = {
  key: AdminServiceKey;
  statusKey: 'running' | 'degraded' | 'down';
};

export type AdminWorkerItem = {
  id: string;
  name: string;
  statusKey: 'running' | 'idle' | 'error';
  heartbeat: string;
};

export type AdminQueueItem = {
  key: AdminQueueKey;
  pending: number;
};

export type AdminKpi = {
  key: AdminKpiKey;
  value: string | number;
  hintKey: string;
  delta?: string;
  deltaTone?: 'up' | 'down' | 'neutral';
};

export type AdminWorkspacePreview = {
  totalUsers: number;
  totalPages: number;
  kpis: AdminKpi[];
  users: AdminUserRow[];
  roles: AdminRoleRow[];
  permissions: AdminPermissionRow[];
  auditRows: AdminAuditRow[];
  services: AdminServiceRow[];
  health: AdminHealthItem[];
  recentAudit: AdminAuditRow[];
  workers: AdminWorkerItem[];
  queues: AdminQueueItem[];
  apiPerformance: {
    points: number[];
    requestsLabel: string;
    avgResponse: string;
    errorRate: string;
  };
  workspaces: AdminWorkspaceKey[];
};

export const ADMIN_AI_ACTIONS: ReadonlyArray<{
  key: AdminAiActionKey;
  icon: IhIconName;
}> = [
  { key: 'newUser', icon: 'plus' },
  { key: 'createRole', icon: 'roles' },
  { key: 'systemScan', icon: 'search' },
  { key: 'auditLog', icon: 'activity' },
];

export const ADMIN_KPI_ICONS: Record<AdminKpiKey, IhIconName> = {
  activeUsers: 'users',
  onlineUsers: 'activity',
  uptime: 'check',
  openAlerts: 'alert',
  apiRequests: 'barChart',
};

export const ADMIN_TAB_ORDER: AdminTabKey[] = [
  'users',
  'roles',
  'workspacePermissions',
  'auditLog',
  'services',
];

export const ADMIN_ROLE_ORDER: AdminRoleKey[] = [
  'systemAdmin',
  'admin',
  'salesManager',
  'salesRep',
  'analyst',
  'support',
  'marketing',
];

export const ADMIN_STATUS_ORDER: AdminStatusKey[] = ['active', 'inactive', 'suspended'];

export const ADMIN_LAST_LOGIN_ORDER: AdminLastLoginKey[] = [
  'now',
  'today',
  'yesterday',
  'week',
  'month',
  'never',
];

export const ADMIN_WORKSPACE_ORDER: AdminWorkspaceKey[] = [
  'crm',
  'sales',
  'finance',
  'marketing',
  'operations',
  'platform',
];
