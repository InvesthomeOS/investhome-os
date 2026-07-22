import {
  activateAutomation,
  archiveAutomation,
  createAutomation,
  deleteAutomation,
  duplicateAutomation,
  fetchAutomation,
  fetchAutomationExecutions,
  fetchAutomationLogs,
  fetchAutomationMetrics,
  fetchAutomations,
  pauseAutomation,
  updateAutomation,
  type AutomationListParams,
} from '@/workspaces/marketing/api/automations';

export const automationQueryKeys = {
  all: ['marketing', 'automation'] as const,
  list: (params: AutomationListParams = {}) => ['marketing', 'automation', 'list', params] as const,
  detail: (id: string) => ['marketing', 'automation', 'detail', id] as const,
  executions: (id: string, page = 1) => ['marketing', 'automation', 'executions', id, page] as const,
  logs: (id: string, page = 1) => ['marketing', 'automation', 'logs', id, page] as const,
  metrics: (id: string) => ['marketing', 'automation', 'metrics', id] as const,
};

export const automationQueries = {
  list: (params: AutomationListParams = {}) => ({
    queryKey: automationQueryKeys.list(params),
    queryFn: () => fetchAutomations(params),
  }),
  detail: (id: string) => ({
    queryKey: automationQueryKeys.detail(id),
    queryFn: () => fetchAutomation(id),
  }),
  executions: (id: string, page = 1) => ({
    queryKey: automationQueryKeys.executions(id, page),
    queryFn: () => fetchAutomationExecutions(id, page),
  }),
  logs: (id: string, page = 1) => ({
    queryKey: automationQueryKeys.logs(id, page),
    queryFn: () => fetchAutomationLogs(id, page),
  }),
  metrics: (id: string) => ({
    queryKey: automationQueryKeys.metrics(id),
    queryFn: () => fetchAutomationMetrics(id),
  }),
};

export {
  activateAutomation,
  archiveAutomation,
  createAutomation,
  deleteAutomation,
  duplicateAutomation,
  pauseAutomation,
  updateAutomation,
};
