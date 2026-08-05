import type { CurrentUser } from '@/lib/api/auth';
import { hasPermission } from '@/lib/api/auth';
import {
  CLOSED_OPPORTUNITY_STAGES,
  OPPORTUNITY_STAGES,
  type OpportunityPriority,
  type OpportunityStage,
  type SalesOpportunity,
} from '@/lib/api/sales';

export const OPPORTUNITY_STAGE_ORDER: readonly OpportunityStage[] = OPPORTUNITY_STAGES;

/** Canonical display order for pipeline currency KPIs — do not mix or invent extras. */
export const OPPORTUNITY_CURRENCY_ORDER = ['USD', 'EUR', 'AED', 'GBP', 'TRY'] as const;

export type OpportunityViewMode = 'board' | 'list';

export type OpportunityCardContext = {
  customerName: string | null;
  projectName: string | null;
};

export type OpportunityWorkspaceFilters = {
  view: OpportunityViewMode;
  search: string;
  stage: OpportunityStage | '';
  assignee: string;
  priority: OpportunityPriority | '';
  archived: boolean;
  sort: string;
  direction: 'asc' | 'desc';
  page: number;
};

export type OpportunityPermissions = {
  canView: boolean;
  canViewBoard: boolean;
  canCreate: boolean;
  canUpdate: boolean;
  canChangeStage: boolean;
  canChangeProbability: boolean;
  canArchive: boolean;
  canRestore: boolean;
  canViewSensitiveValues: boolean;
  canViewProposals: boolean;
  canViewReservations: boolean;
};

export type CurrencyAggregate = {
  currency: string;
  total: number;
  weighted: number;
};

export type OpportunitySummary = {
  openCount: number;
  missingNextAction: number;
  overdueNextAction: number;
  currencies: CurrencyAggregate[];
};

export const DEFAULT_OPPORTUNITY_FILTERS: OpportunityWorkspaceFilters = {
  view: 'board',
  search: '',
  stage: '',
  assignee: '',
  priority: '',
  archived: false,
  sort: 'updated_at',
  direction: 'desc',
  page: 1,
};

export function getOpportunityPermissions(user: CurrentUser | null): OpportunityPermissions {
  return {
    canView: hasPermission(user, 'sales', 'view'),
    canViewBoard: hasPermission(user, 'sales', 'view_pipeline'),
    canCreate: hasPermission(user, 'sales', 'create'),
    canUpdate: hasPermission(user, 'sales', 'update'),
    canChangeStage: hasPermission(user, 'sales', 'change_stage'),
    canChangeProbability: hasPermission(user, 'sales', 'change_probability'),
    canArchive: hasPermission(user, 'sales', 'archive'),
    canRestore: hasPermission(user, 'sales', 'restore'),
    // This action is not present in the current configured role matrix. Keeping the
    // explicit check is intentionally fail-closed until the contract is formalized.
    canViewSensitiveValues: hasPermission(user, 'sales', 'view_sensitive_value'),
    canViewProposals: hasPermission(user, 'sales', 'view_proposal'),
    canViewReservations: hasPermission(user, 'sales', 'view_reservations'),
  };
}

export function isOpportunityOverdue(opportunity: SalesOpportunity, now = new Date()): boolean {
  if (!opportunity.next_action_date) return false;
  const due = new Date(`${opportunity.next_action_date}T23:59:59`);
  return !Number.isNaN(due.getTime()) && due.getTime() < now.getTime();
}

export function opportunityWeightedValue(opportunity: SalesOpportunity): number | null {
  if (!opportunity.expected_revenue) return null;
  const value = Number(opportunity.expected_revenue);
  if (!Number.isFinite(value)) return null;
  return value * (opportunity.probability / 100);
}

function sortCurrencyAggregates(entries: CurrencyAggregate[]): CurrencyAggregate[] {
  return [...entries].sort((a, b) => {
    const ai = OPPORTUNITY_CURRENCY_ORDER.indexOf(
      a.currency as (typeof OPPORTUNITY_CURRENCY_ORDER)[number],
    );
    const bi = OPPORTUNITY_CURRENCY_ORDER.indexOf(
      b.currency as (typeof OPPORTUNITY_CURRENCY_ORDER)[number],
    );
    const ar = ai === -1 ? 999 : ai;
    const br = bi === -1 ? 999 : bi;
    if (ar !== br) return ar - br;
    return a.currency.localeCompare(b.currency);
  });
}

function withCanonicalCurrencyRows(entries: CurrencyAggregate[]): CurrencyAggregate[] {
  const byCurrency = new Map(entries.map((entry) => [entry.currency, entry]));
  return OPPORTUNITY_CURRENCY_ORDER.map(
    (currency) => byCurrency.get(currency) ?? { currency, total: 0, weighted: 0 },
  );
}

export function aggregateOpportunitySummary(items: SalesOpportunity[]): OpportunitySummary {
  const openItems = items.filter(
    (item) => !item.archived_at && !CLOSED_OPPORTUNITY_STAGES.includes(item.stage),
  );
  const byCurrency = new Map<string, CurrencyAggregate>();

  for (const item of openItems) {
    if (!item.expected_revenue) continue;
    const value = Number(item.expected_revenue);
    if (!Number.isFinite(value)) continue;
    const currency = item.currency || 'USD';
    const current = byCurrency.get(currency) ?? { currency, total: 0, weighted: 0 };
    current.total += value;
    current.weighted += value * (item.probability / 100);
    byCurrency.set(currency, current);
  }

  return {
    openCount: openItems.length,
    missingNextAction: openItems.filter((item) => !item.next_action || !item.next_action_date).length,
    overdueNextAction: openItems.filter((item) => isOpportunityOverdue(item)).length,
    currencies: withCanonicalCurrencyRows(sortCurrencyAggregates(Array.from(byCurrency.values()))),
  };
}

export function stageCurrencyTotals(
  items: SalesOpportunity[],
  stage: OpportunityStage,
): CurrencyAggregate[] {
  const byCurrency = new Map<string, CurrencyAggregate>();
  for (const item of items) {
    if (item.stage !== stage || !item.expected_revenue) continue;
    const value = Number(item.expected_revenue);
    if (!Number.isFinite(value)) continue;
    const currency = item.currency || 'USD';
    const current = byCurrency.get(currency) ?? { currency, total: 0, weighted: 0 };
    current.total += value;
    current.weighted += value * (item.probability / 100);
    byCurrency.set(currency, current);
  }
  return sortCurrencyAggregates(Array.from(byCurrency.values()));
}

export function getOpportunityCardContext(
  opportunity: SalesOpportunity,
  enrichment?: Record<string, OpportunityCardContext>,
): OpportunityCardContext {
  return (
    enrichment?.[opportunity.id] ?? {
      customerName: null,
      projectName: null,
    }
  );
}

export function filterOpportunities(
  items: SalesOpportunity[],
  filters: OpportunityWorkspaceFilters,
): SalesOpportunity[] {
  const needle = filters.search.trim().toLocaleLowerCase();
  return items.filter((item) => {
    if (filters.stage && item.stage !== filters.stage) return false;
    if (filters.assignee && item.assigned_sales_user_id !== filters.assignee) return false;
    if (filters.priority && item.priority !== filters.priority) return false;
    if (!filters.archived && item.archived_at) return false;
    if (
      needle &&
      ![item.display_id, item.opportunity_code, item.source]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase().includes(needle))
    ) {
      return false;
    }
    return true;
  });
}

export function isOpportunityStage(value: string | null): value is OpportunityStage {
  return Boolean(value && OPPORTUNITY_STAGES.includes(value as OpportunityStage));
}

export function isOpportunityPriority(value: string | null): value is OpportunityPriority {
  return value === 'low' || value === 'medium' || value === 'high' || value === 'urgent';
}
