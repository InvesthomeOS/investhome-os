import type { Route } from 'next';

export type LoadState = 'idle' | 'loading' | 'error' | 'success';

export type MetricDisplayState =
  | 'ready'
  | 'empty'
  | 'unavailable'
  | 'loading'
  | 'error';

export type CompanyHealthTone = 'healthy' | 'attention' | 'critical' | 'unknown';

export interface ExecutiveMetric {
  key: string;
  label: string;
  value: string | null;
  state: MetricDisplayState;
  href?: Route;
  hint?: string;
}

export interface PriorityItemView {
  id: string;
  severity: 'critical' | 'warning' | 'information';
  title: string;
  description: string;
  href: Route;
  dueLabel?: string | null;
  category: string;
}

export interface AlertItemView {
  id: string;
  severity: 'critical' | 'warning' | 'information';
  title: string;
  description: string;
  href?: Route | null;
  source: string;
}

export interface MyWorkItem {
  id: string;
  title: string;
  meta: string;
  href: Route;
  kind: 'approval' | 'task' | 'meeting' | 'document' | 'activity';
}
