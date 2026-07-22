import type { Investor, InvestorStatus } from '@/lib/api/investors';

/** Full G3 investor lifecycle (Turkish product labels via i18n). */
export const INVESTOR_LIFECYCLE_STAGES = [
  'new_investor',
  'contacted',
  'qualified',
  'meeting_scheduled',
  'interested',
  'nda_signed',
  'project_presented',
  'reservation',
  'contract',
  'payment_pending',
  'wire_received',
  'construction',
  'closing',
  'rental',
  'portfolio',
  'lost',
] as const;

export type InvestorLifecycleStage = (typeof INVESTOR_LIFECYCLE_STAGES)[number];

export type StageTone = 'info' | 'warn' | 'success' | 'danger' | 'neutral';

export const LIFECYCLE_META: {
  id: InvestorLifecycleStage;
  tone: StageTone;
  defaultProbability: number;
}[] = [
  { id: 'new_investor', tone: 'neutral', defaultProbability: 10 },
  { id: 'contacted', tone: 'info', defaultProbability: 15 },
  { id: 'qualified', tone: 'info', defaultProbability: 25 },
  { id: 'meeting_scheduled', tone: 'warn', defaultProbability: 35 },
  { id: 'interested', tone: 'warn', defaultProbability: 45 },
  { id: 'nda_signed', tone: 'warn', defaultProbability: 55 },
  { id: 'project_presented', tone: 'warn', defaultProbability: 60 },
  { id: 'reservation', tone: 'success', defaultProbability: 70 },
  { id: 'contract', tone: 'success', defaultProbability: 80 },
  { id: 'payment_pending', tone: 'warn', defaultProbability: 85 },
  { id: 'wire_received', tone: 'success', defaultProbability: 90 },
  { id: 'construction', tone: 'info', defaultProbability: 92 },
  { id: 'closing', tone: 'info', defaultProbability: 95 },
  { id: 'rental', tone: 'success', defaultProbability: 98 },
  { id: 'portfolio', tone: 'success', defaultProbability: 100 },
  { id: 'lost', tone: 'danger', defaultProbability: 0 },
];

/** Map legacy InvestorStatus values onto board lifecycle columns. */
const LEGACY_TO_LIFECYCLE: Record<string, InvestorLifecycleStage> = {
  prospect: 'new_investor',
  contacted: 'contacted',
  qualified: 'qualified',
  meeting_scheduled: 'meeting_scheduled',
  interested: 'interested',
  nda_signed: 'nda_signed',
  project_presented: 'project_presented',
  reservation: 'reservation',
  contract: 'contract',
  payment_pending: 'payment_pending',
  wire_received: 'wire_received',
  construction: 'construction',
  closing: 'closing',
  rental: 'rental',
  portfolio: 'portfolio',
  lost: 'lost',
  active: 'interested',
  invested: 'portfolio',
  follow_up: 'contacted',
  dormant: 'lost',
  rejected: 'lost',
  new_investor: 'new_investor',
};

export function toLifecycleStage(status: string | null | undefined): InvestorLifecycleStage {
  if (!status) return 'new_investor';
  return LEGACY_TO_LIFECYCLE[status] ?? 'new_investor';
}

export function isLifecycleStage(value: string): value is InvestorLifecycleStage {
  return (INVESTOR_LIFECYCLE_STAGES as readonly string[]).includes(value);
}

export function stageProbability(stage: InvestorLifecycleStage): number {
  return LIFECYCLE_META.find((s) => s.id === stage)?.defaultProbability ?? 10;
}

export function stageTone(stage: InvestorLifecycleStage): StageTone {
  return LIFECYCLE_META.find((s) => s.id === stage)?.tone ?? 'neutral';
}

export function investorCapacity(investor: Investor): number {
  const raw = investor.investment_capacity ?? investor.maximum_ticket ?? investor.minimum_ticket;
  const n = Number(raw);
  return Number.isFinite(n) ? n : 0;
}

export function weightedValue(investor: Investor, probability: number): number {
  return (investorCapacity(investor) * probability) / 100;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ''}${parts[parts.length - 1]![0] ?? ''}`.toUpperCase();
}

export type InvestorViewId =
  | 'pipeline'
  | 'list'
  | 'opportunities'
  | 'reservations'
  | 'contracts'
  | 'payments'
  | 'closings'
  | 'portfolio'
  | 'activity'
  | 'analytics';

export const INVESTOR_VIEWS: InvestorViewId[] = [
  'pipeline',
  'list',
  'opportunities',
  'reservations',
  'contracts',
  'payments',
  'closings',
  'portfolio',
  'activity',
  'analytics',
];

export function parseView(value: string | null | undefined): InvestorViewId {
  if (value && (INVESTOR_VIEWS as string[]).includes(value)) {
    return value as InvestorViewId;
  }
  return 'pipeline';
}

/** Status values accepted by PATCH /investors — lifecycle + legacy. */
export const PERSISTABLE_STATUSES = [
  ...INVESTOR_LIFECYCLE_STAGES,
  'prospect',
  'active',
  'invested',
  'follow_up',
  'dormant',
  'rejected',
] as const;

export type PersistableStatus = (typeof PERSISTABLE_STATUSES)[number];

export function lifecycleAsStatus(stage: InvestorLifecycleStage): InvestorStatus {
  return stage as InvestorStatus;
}
