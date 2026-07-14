export const APP_NAME = 'Investhome OS' as const;
export const APP_SLUG = 'investhome-os' as const;

export type ModuleName =
  | 'executive'
  | 'leads'
  | 'investors'
  | 'projects'
  | 'finance';

export const MODULE_NAMES: readonly ModuleName[] = [
  'executive',
  'leads',
  'investors',
  'projects',
  'finance',
] as const;

export interface HealthStatus {
  status: 'ok' | 'degraded' | 'down';
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}
