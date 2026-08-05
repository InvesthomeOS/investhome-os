import type { IhIconName } from '@/components/icons/ih-icons';

export type SystemLogLevel = 'info' | 'warning' | 'error' | 'debug';

export type SystemLogRow = {
  id: string;
  timestamp: string;
  level: SystemLogLevel;
  service: string;
  message: string;
  actor: string;
};

export type SystemLogsPreview = {
  rows: SystemLogRow[];
};

export type AdminIntegrationStatus = 'connected' | 'degraded' | 'disconnected';

export type AdminIntegrationRow = {
  id: string;
  name: string;
  provider: string;
  status: AdminIntegrationStatus;
  lastSync: string;
  icon: IhIconName;
};

export type AdminIntegrationsPreview = {
  rows: AdminIntegrationRow[];
};
