import {
  activateCampaign,
  approveCampaign,
  archiveCampaign,
  bulkCampaignAction,
  createCampaign,
  createCampaignSavedView,
  duplicateCampaign,
  fetchCampaign,
  fetchCampaignBrief,
  fetchCampaignBudget,
  fetchCampaignLeads,
  fetchCampaignMilestones,
  fetchCampaignOverview,
  fetchCampaignReadiness,
  fetchCampaignSavedViews,
  fetchCampaigns,
  fetchCampaignSummary,
  fetchCampaignTracking,
  pauseCampaign,
  restoreCampaign,
  submitCampaignApproval,
  updateCampaign,
  updateCampaignBrief,
  updateCampaignTracking,
  validateCampaignTracking,
  type CampaignInput,
  type CampaignListParams,
} from '@/workspaces/marketing/api/campaigns';

export const campaignQueryKeys = {
  all: ['marketing', 'campaigns'] as const,
  list: (params: CampaignListParams) => ['marketing', 'campaigns', 'list', params] as const,
  summary: (myCampaigns?: boolean) => ['marketing', 'campaigns', 'summary', myCampaigns] as const,
  detail: (id: string) => ['marketing', 'campaigns', 'detail', id] as const,
  overview: (id: string) => ['marketing', 'campaigns', 'overview', id] as const,
  readiness: (id: string) => ['marketing', 'campaigns', 'readiness', id] as const,
  brief: (id: string) => ['marketing', 'campaigns', 'brief', id] as const,
  milestones: (id: string) => ['marketing', 'campaigns', 'milestones', id] as const,
  budget: (id: string) => ['marketing', 'campaigns', 'budget', id] as const,
  tracking: (id: string) => ['marketing', 'campaigns', 'tracking', id] as const,
  leads: (id: string) => ['marketing', 'campaigns', 'leads', id] as const,
  savedViews: ['marketing', 'campaigns', 'saved-views'] as const,
};

export const campaignQueries = {
  list: (params: CampaignListParams) => ({
    queryKey: campaignQueryKeys.list(params),
    queryFn: () => fetchCampaigns(params),
  }),
  summary: (myCampaigns = false) => ({
    queryKey: campaignQueryKeys.summary(myCampaigns),
    queryFn: () => fetchCampaignSummary(myCampaigns),
  }),
  detail: (id: string) => ({
    queryKey: campaignQueryKeys.detail(id),
    queryFn: () => fetchCampaign(id),
    enabled: Boolean(id),
  }),
  overview: (id: string) => ({
    queryKey: campaignQueryKeys.overview(id),
    queryFn: () => fetchCampaignOverview(id),
    enabled: Boolean(id),
  }),
  readiness: (id: string) => ({
    queryKey: campaignQueryKeys.readiness(id),
    queryFn: () => fetchCampaignReadiness(id),
    enabled: Boolean(id),
  }),
  brief: (id: string) => ({
    queryKey: campaignQueryKeys.brief(id),
    queryFn: () => fetchCampaignBrief(id),
    enabled: Boolean(id),
  }),
  milestones: (id: string) => ({
    queryKey: campaignQueryKeys.milestones(id),
    queryFn: () => fetchCampaignMilestones(id),
    enabled: Boolean(id),
  }),
  budget: (id: string) => ({
    queryKey: campaignQueryKeys.budget(id),
    queryFn: () => fetchCampaignBudget(id),
    enabled: Boolean(id),
  }),
  tracking: (id: string) => ({
    queryKey: campaignQueryKeys.tracking(id),
    queryFn: () => fetchCampaignTracking(id),
    enabled: Boolean(id),
  }),
  leads: (id: string) => ({
    queryKey: campaignQueryKeys.leads(id),
    queryFn: () => fetchCampaignLeads(id),
    enabled: Boolean(id),
  }),
  savedViews: () => ({
    queryKey: campaignQueryKeys.savedViews,
    queryFn: () => fetchCampaignSavedViews(),
  }),
};

export const campaignMutations = {
  create: createCampaign,
  update: updateCampaign,
  duplicate: duplicateCampaign,
  archive: archiveCampaign,
  restore: restoreCampaign,
  activate: activateCampaign,
  pause: pauseCampaign,
  submitApproval: submitCampaignApproval,
  approve: approveCampaign,
  bulk: bulkCampaignAction,
  updateBrief: updateCampaignBrief,
  updateTracking: updateCampaignTracking,
  validateTracking: validateCampaignTracking,
  createSavedView: createCampaignSavedView,
};

export type { CampaignInput, CampaignListParams };
