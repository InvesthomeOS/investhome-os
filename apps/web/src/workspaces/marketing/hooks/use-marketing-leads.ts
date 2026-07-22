import {
  fetchHandoffReadiness,
  fetchMarketingLeadDetail,
  fetchMarketingLeadSummary,
  fetchMarketingLeads,
  handoffMarketingLead,
} from '@/workspaces/marketing/api/marketing-leads';

export const marketingLeadsQueryKeys = {
  all: ['marketing', 'marketingLeads'] as const,
  list: (page = 1) => ['marketing', 'marketingLeads', 'list', page] as const,
  summary: () => ['marketing', 'marketingLeads', 'summary'] as const,
  detail: (id: string) => ['marketing', 'marketingLeads', 'detail', id] as const,
  handoff: (id: string) => ['marketing', 'marketingLeads', 'handoff', id] as const,
};

export const marketingLeadsQueries = {
  list: (page = 1) => ({
    queryKey: marketingLeadsQueryKeys.list(page),
    queryFn: () => fetchMarketingLeads(page),
  }),
  summary: () => ({
    queryKey: marketingLeadsQueryKeys.summary(),
    queryFn: () => fetchMarketingLeadSummary(),
  }),
  detail: (id: string) => ({
    queryKey: marketingLeadsQueryKeys.detail(id),
    queryFn: () => fetchMarketingLeadDetail(id),
  }),
  handoffReadiness: (id: string) => ({
    queryKey: marketingLeadsQueryKeys.handoff(id),
    queryFn: () => fetchHandoffReadiness(id),
  }),
};

export { handoffMarketingLead };
