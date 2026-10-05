/** Pure helpers for Sales opportunities loading. Keep fetch effects stable. */

export type SalesOpportunitiesFilterSnapshot = {
  search: string;
  stage: string;
  assigned_sales_user_id: string;
  party_id: string;
  lead_id: string;
  priority: string;
  include_archived: boolean;
  sort_by: string;
  sort_dir: string;
  page: number;
  page_size: number;
  view: string;
};

export function salesOpportunitiesRequestKey(filters: SalesOpportunitiesFilterSnapshot): string {
  return [
    filters.view,
    filters.search.trim(),
    filters.stage,
    filters.assigned_sales_user_id,
    filters.party_id,
    filters.lead_id,
    filters.priority,
    filters.include_archived ? '1' : '0',
    filters.sort_by,
    filters.sort_dir,
    String(filters.page),
    String(filters.page_size),
  ].join('|');
}

export function shouldShowSalesSkeleton(loading: boolean, itemCount: number): boolean {
  return loading && itemCount === 0;
}

export function mergePartyNames(
  current: Record<string, string>,
  incoming: Record<string, string>,
): { next: Record<string, string>; changed: boolean } {
  let changed = false;
  const next = { ...current };
  for (const [id, name] of Object.entries(incoming)) {
    if (!id || !name || next[id] === name) continue;
    next[id] = name;
    changed = true;
  }
  return { next, changed };
}
