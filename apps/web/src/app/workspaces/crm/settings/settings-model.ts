import type { IhIconName } from '@/components/icons/ih-icons';

export type SettingsCategoryId =
  | 'general'
  | 'crm'
  | 'ai'
  | 'users'
  | 'notifications'
  | 'integrations'
  | 'security'
  | 'system'
  | 'billing';

export type SettingsNotificationChannel = 'email' | 'whatsapp' | 'sms' | 'push';

export type SettingsIntegrationId =
  | 'googleCalendar'
  | 'outlook'
  | 'gmail'
  | 'slack'
  | 'quickbooks'
  | 'zapier'
  | 'microsoft365';

export type SettingsCrmEntityId =
  | 'pipelineStages'
  | 'opportunityStages'
  | 'activityTypes'
  | 'taskTypes'
  | 'tags';

export type SettingsHealthServiceId = 'api' | 'web' | 'database' | 'queue' | 'storage';

export type SettingsSecurityItemId =
  | 'mfa'
  | 'apiKeys'
  | 'sessionTimeout'
  | 'passwordPolicy'
  | 'loginHistory';

export type SettingsSystemItemId =
  | 'queue'
  | 'workers'
  | 'cache'
  | 'storage'
  | 'backgroundJobs'
  | 'logSize';

export type SettingsCategory = {
  id: SettingsCategoryId;
  icon: IhIconName;
};

export type SettingsGeneralInfo = {
  companyName: string;
  logoInitials: string;
  language: string;
  timezone: string;
  companyId: string;
  lastUpdatedKey: string;
};

export type SettingsAiConfig = {
  provider: string;
  model: string;
  temperature: string;
  defaultLanguage: string;
  promptPolicyKey: string;
  totalUsageKey: string;
};

export type SettingsCrmEntity = {
  id: SettingsCrmEntityId;
  count: number;
  icon: IhIconName;
};

export type SettingsNotification = {
  id: SettingsNotificationChannel;
  enabled: boolean;
  icon: IhIconName;
};

export type SettingsIntegration = {
  id: SettingsIntegrationId;
  connected: boolean;
  mark: string;
  tone: 'blue' | 'cyan' | 'rose' | 'violet' | 'amber' | 'green' | 'slate';
  lastSyncKey: string;
};

export type SettingsStatusTone = 'ok' | 'warn' | 'muted';

export type SettingsSecurityItem = {
  id: SettingsSecurityItemId;
  icon: IhIconName;
  valueKey: string;
  tone: SettingsStatusTone;
};

export type SettingsSystemItem = {
  id: SettingsSystemItemId;
  icon: IhIconName;
  valueKey: string;
  tone: SettingsStatusTone;
};

export type SettingsHealthService = {
  id: SettingsHealthServiceId;
  status: 'healthy';
};

export type SettingsLicense = {
  planKey: 'enterprise';
  userLimit: number;
  userLimitMax: number;
  activeUsers: number;
};

export type SettingsUsageMeter = {
  pct: number;
};

export type SettingsWorkspacePreview = {
  categories: SettingsCategory[];
  general: SettingsGeneralInfo;
  ai: SettingsAiConfig;
  crmEntities: SettingsCrmEntity[];
  notifications: SettingsNotification[];
  integrations: SettingsIntegration[];
  security: SettingsSecurityItem[];
  system: SettingsSystemItem[];
  health: SettingsHealthService[];
  license: SettingsLicense;
  aiRequests: SettingsUsageMeter;
  aiTokens: SettingsUsageMeter;
  storage: SettingsUsageMeter;
  lastUpdatedKey: string;
};
