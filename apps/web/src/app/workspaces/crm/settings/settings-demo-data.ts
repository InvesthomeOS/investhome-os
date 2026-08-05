import type { SettingsWorkspacePreview } from './settings-model';

/** Typed local fixtures for Settings UX review — no live API / settings services. */
export function makeSettingsPreview(): SettingsWorkspacePreview {
  return {
    categories: [
      { id: 'general', icon: 'settings' },
      { id: 'crm', icon: 'crm' },
      { id: 'ai', icon: 'sparkles' },
      { id: 'users', icon: 'users' },
      { id: 'notifications', icon: 'bell' },
      { id: 'integrations', icon: 'inbox' },
      { id: 'security', icon: 'permissions' },
      { id: 'system', icon: 'activity' },
      { id: 'billing', icon: 'documents' },
    ],
    general: {
      companyName: 'InvestHome Global',
      logoInitials: 'IH',
      language: 'tr',
      timezone: 'europeIstanbul',
      companyId: 'IH-ENT-0042',
      lastUpdatedKey: 'recent',
    },
    ai: {
      provider: 'openai',
      model: 'gpt4o',
      temperature: '0.7',
      defaultLanguage: 'tr',
      promptPolicyKey: 'enterprise',
      totalUsageKey: 'summary',
    },
    crmEntities: [
      { id: 'pipelineStages', count: 7, icon: 'barChart' },
      { id: 'opportunityStages', count: 6, icon: 'target' },
      { id: 'activityTypes', count: 12, icon: 'activity' },
      { id: 'taskTypes', count: 8, icon: 'check' },
      { id: 'tags', count: 24, icon: 'inventory' },
    ],
    notifications: [
      { id: 'email', enabled: true, icon: 'inbox' },
      { id: 'whatsapp', enabled: true, icon: 'activity' },
      { id: 'sms', enabled: false, icon: 'bell' },
      { id: 'push', enabled: true, icon: 'sparkles' },
    ],
    integrations: [
      { id: 'googleCalendar', connected: true, mark: 'G', tone: 'blue', lastSyncKey: 'minutesAgo' },
      { id: 'outlook', connected: true, mark: 'O', tone: 'cyan', lastSyncKey: 'hourAgo' },
      { id: 'gmail', connected: true, mark: 'M', tone: 'rose', lastSyncKey: 'minutesAgo' },
      { id: 'slack', connected: true, mark: 'S', tone: 'violet', lastSyncKey: 'live' },
      { id: 'quickbooks', connected: false, mark: 'Q', tone: 'green', lastSyncKey: 'never' },
      { id: 'zapier', connected: true, mark: 'Z', tone: 'amber', lastSyncKey: 'dayAgo' },
    ],
    security: [
      { id: 'mfa', icon: 'permissions', valueKey: 'enabled', tone: 'ok' },
      { id: 'apiKeys', icon: 'settings', valueKey: 'activeCount', tone: 'ok' },
      { id: 'sessionTimeout', icon: 'activity', valueKey: 'timeout', tone: 'muted' },
      { id: 'passwordPolicy', icon: 'permissions', valueKey: 'strong', tone: 'ok' },
      { id: 'loginHistory', icon: 'users', valueKey: 'recent', tone: 'muted' },
    ],
    system: [
      { id: 'queue', icon: 'inbox', valueKey: 'healthy', tone: 'ok' },
      { id: 'workers', icon: 'activity', valueKey: 'running', tone: 'ok' },
      { id: 'cache', icon: 'sparkles', valueKey: 'hitRate', tone: 'ok' },
      { id: 'storage', icon: 'documents', valueKey: 'used', tone: 'warn' },
      { id: 'backgroundJobs', icon: 'check', valueKey: 'active', tone: 'ok' },
      { id: 'logSize', icon: 'barChart', valueKey: 'size', tone: 'muted' },
    ],
    health: [
      { id: 'api', status: 'healthy' },
      { id: 'web', status: 'healthy' },
      { id: 'database', status: 'healthy' },
      { id: 'queue', status: 'healthy' },
      { id: 'storage', status: 'healthy' },
    ],
    license: {
      planKey: 'enterprise',
      userLimit: 50,
      userLimitMax: 100,
      activeUsers: 42,
    },
    aiRequests: { pct: 24.9 },
    aiTokens: { pct: 24 },
    storage: { pct: 24.5 },
    lastUpdatedKey: 'recent',
  };
}
