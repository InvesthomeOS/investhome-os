/**
 * Training simulation isolation.
 * Blocks real side-effects while simulation mode is active.
 */

export type BlockedAction =
  | 'payment'
  | 'email'
  | 'campaign_publish'
  | 'contract_execute'
  | 'financial_post'
  | 'investor_notify'
  | 'automation_trigger'
  | 'production_report';

const BLOCKED: Record<BlockedAction, string> = {
  payment: 'Real payments are blocked in training mode.',
  email: 'Real emails are blocked in training mode.',
  campaign_publish: 'Campaign publish is blocked in training mode.',
  contract_execute: 'Contract execution is blocked in training mode.',
  financial_post: 'Financial posting is blocked in training mode.',
  investor_notify: 'Investor notifications are blocked in training mode.',
  automation_trigger: 'Live automations are blocked in training mode.',
  production_report: 'Training data is excluded from production reports.',
};

export function assertSimulationSafe(simulationMode: boolean, action: BlockedAction): {
  allowed: boolean;
  reason?: string;
} {
  if (!simulationMode) return { allowed: true };
  return { allowed: false, reason: BLOCKED[action] };
}

export const TRAINING_LABELS = [
  'TRAINING DATA',
  'DEMO USER',
  'TEST INVESTOR',
  'TEST PAYMENT',
  'TEST PROJECT',
] as const;
