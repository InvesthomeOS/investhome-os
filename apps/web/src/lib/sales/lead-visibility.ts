/** Sales workspace lead vs opportunity visibility and KPI rules. */

export const NEW_LEAD_STATUS = 'New';
export const QUALIFIED_LEAD_STATUS = 'Qualified';

export type SalesLeadStatusLike = { status: string };
export type SalesOpportunityLike = { lead_id?: string | null; party_id?: string | null };

export function isNewLeadStatus(status: string | null | undefined): boolean {
  return status === NEW_LEAD_STATUS;
}

export function isQualifiedLeadStatus(status: string | null | undefined): boolean {
  return status === QUALIFIED_LEAD_STATUS;
}

export function canConvertLeadToOpportunity(status: string | null | undefined): boolean {
  return isQualifiedLeadStatus(status);
}

export function leadMatchesSalesLeadList(
  lead: SalesLeadStatusLike,
  statusFilter: string | null | undefined,
): boolean {
  if (!statusFilter) return true;
  return lead.status === statusFilter;
}

export function countSalesLeadKpis(leads: SalesLeadStatusLike[]): {
  new_leads: number;
  qualified_leads: number;
} {
  let new_leads = 0;
  let qualified_leads = 0;
  for (const lead of leads) {
    if (isNewLeadStatus(lead.status)) {
      new_leads += 1;
      continue;
    }
    if (isQualifiedLeadStatus(lead.status)) {
      qualified_leads += 1;
    }
  }
  return { new_leads, qualified_leads };
}

export function newLeadHasOpportunity(
  leadId: string,
  opportunities: SalesOpportunityLike[],
): boolean {
  return opportunities.some(
    (item) => item.lead_id === leadId || item.party_id === leadId,
  );
}

export function salesPipelinePresentation(
  loading: boolean,
  opportunityCount: number,
): 'skeleton' | 'empty' | 'content' {
  if (loading && opportunityCount === 0) return 'skeleton';
  if (opportunityCount === 0) return 'empty';
  return 'content';
}

export function salesEmptyOpportunitiesCopyKey(leadCount: number): 'emptyOpportunitiesWithLeads' | 'emptyOpportunitiesHint' {
  return leadCount > 0 ? 'emptyOpportunitiesWithLeads' : 'emptyOpportunitiesHint';
}

export function visibleSalesLeadCount(kpis: {
  new_leads: number;
  qualified_leads: number;
} | null): number {
  if (!kpis) return 0;
  return kpis.new_leads + kpis.qualified_leads;
}
