import { fetchAudiences } from '@/workspaces/marketing/api/audiences';
import { fetchSegments } from '@/workspaces/marketing/api/segments';
import { fetchMarketingLeads } from '@/workspaces/marketing/api/marketing-leads';
import { fetchLeadSources } from '@/workspaces/marketing/api/lead-sources';
import {
  activateCampaign,
  archiveCampaign,
  createCampaign,
  fetchCampaign,
  fetchCampaigns,
  fetchContentAssets,
  fetchMarketingAlerts,
  fetchMarketingApprovals,
  fetchMarketingBudgets,
  fetchMarketingChannels,
  fetchMarketingDashboard,
  fetchMarketingEvents,
  fetchMarketingNavigation,
  fetchMarketingProviderStatuses,
  fetchMarketingQuickActions,
  fetchMarketingRecommendations,
  pauseCampaign,
  updateCampaign,
  type CampaignListParams,
} from '@/workspaces/marketing/api/marketing';
import {
  fetchAttributionHealth,
  fetchDashboardSavedViews,
  fetchDashboardWidgets,
  fetchDataHealth,
  fetchExecutiveDashboard,
  fetchMarketingFunnel,
  fetchMarketingHealth,
  fetchMarketingKPIs,
  fetchTrackingHealth,
  type AnalyticsQueryParams,
} from '@/workspaces/marketing/api/analytics';
import {
  fetchAIDashboard,
  fetchAIAnomalies,
  fetchAIBriefing,
  fetchAIInsights,
  fetchAIPredictions,
  fetchAIRecommendations,
  fetchAISettings,
} from '@/workspaces/marketing/api/ai';

export const marketingQueryKeys = {
  all: ['marketing'] as const,
  dashboard: () => ['marketing', 'dashboard'] as const,
  navigation: () => ['marketing', 'navigation'] as const,
  quickActions: () => ['marketing', 'quickActions'] as const,
  providerStatuses: () => ['marketing', 'providerStatuses'] as const,
  campaigns: {
    all: ['marketing', 'campaigns'] as const,
    list: (params: CampaignListParams) => ['marketing', 'campaigns', 'list', params] as const,
    detail: (id: string) => ['marketing', 'campaigns', 'detail', id] as const,
  },
  audiences: {
    all: ['marketing', 'audiences'] as const,
    list: (params: import('@/workspaces/marketing/api/audiences').AudienceListParams) =>
      ['marketing', 'audiences', 'list', params] as const,
    summary: () => ['marketing', 'audiences', 'summary'] as const,
    detail: (id: string) => ['marketing', 'audiences', 'detail', id] as const,
    members: (id: string, page = 1) => ['marketing', 'audiences', 'members', id, page] as const,
    readiness: (id: string) => ['marketing', 'audiences', 'readiness', id] as const,
    savedViews: () => ['marketing', 'audiences', 'savedViews'] as const,
  },
  segments: {
    all: ['marketing', 'segments'] as const,
    list: (page = 1) => ['marketing', 'segments', 'list', page] as const,
    summary: () => ['marketing', 'segments', 'summary'] as const,
    detail: (id: string) => ['marketing', 'segments', 'detail', id] as const,
    rules: (id: string) => ['marketing', 'segments', 'rules', id] as const,
    preview: (id: string) => ['marketing', 'segments', 'preview', id] as const,
    fieldRegistry: () => ['marketing', 'segments', 'fieldRegistry'] as const,
    savedViews: () => ['marketing', 'segments', 'savedViews'] as const,
  },
  marketingLeads: {
    all: ['marketing', 'marketingLeads'] as const,
    list: (page = 1) => ['marketing', 'marketingLeads', 'list', page] as const,
    summary: () => ['marketing', 'marketingLeads', 'summary'] as const,
    detail: (id: string) => ['marketing', 'marketingLeads', 'detail', id] as const,
    handoff: (id: string) => ['marketing', 'marketingLeads', 'handoff', id] as const,
  },
  leadSources: {
    all: ['marketing', 'leadSources'] as const,
    list: (page = 1) => ['marketing', 'leadSources', 'list', page] as const,
    summary: () => ['marketing', 'leadSources', 'summary'] as const,
    detail: (id: string) => ['marketing', 'leadSources', 'detail', id] as const,
    hierarchy: () => ['marketing', 'leadSources', 'hierarchy'] as const,
  },
  // Legacy flat keys (backward compat)
  audiencesLegacy: (page = 1) => ['marketing', 'audiences', page] as const,
  segmentsLegacy: (page = 1) => ['marketing', 'segments', page] as const,
  leadsLegacy: (page = 1) => ['marketing', 'leads', page] as const,
  sourcesLegacy: (page = 1) => ['marketing', 'sources', page] as const,
  landingPages: () => ['marketing', 'landingPages'] as const,
  forms: () => ['marketing', 'forms'] as const,
  assets: {
    all: ['marketing', 'assets'] as const,
    list: (page = 1) => ['marketing', 'assets', 'list', page] as const,
    detail: (id: string) => ['marketing', 'assets', 'detail', id] as const,
    rights: (id: string) => ['marketing', 'assets', 'rights', id] as const,
    usage: (id: string) => ['marketing', 'assets', 'usage', id] as const,
  },
  brand: {
    all: ['marketing', 'brand'] as const,
    overview: () => ['marketing', 'brand', 'overview'] as const,
    profile: (id: string) => ['marketing', 'brand', 'profile', id] as const,
    guidelines: (id: string) => ['marketing', 'brand', 'guidelines', id] as const,
    terminology: (id: string) => ['marketing', 'brand', 'terminology', id] as const,
  },
  templates: {
    all: ['marketing', 'templates'] as const,
    list: (page = 1) => ['marketing', 'templates', 'list', page] as const,
    detail: (id: string) => ['marketing', 'templates', 'detail', id] as const,
    placeholders: (id: string) => ['marketing', 'templates', 'placeholders', id] as const,
  },
  contentStudio: {
    all: ['marketing', 'content'] as const,
    dashboard: () => ['marketing', 'content', 'dashboard'] as const,
    calendar: () => ['marketing', 'content', 'calendar'] as const,
    list: (params: import('@/workspaces/marketing/api/content').ContentListParams) =>
      ['marketing', 'content', 'list', params] as const,
    detail: (id: string) => ['marketing', 'content', 'detail', id] as const,
    readiness: (id: string) => ['marketing', 'content', 'readiness', id] as const,
    brief: (id: string) => ['marketing', 'content', 'brief', id] as const,
    versions: (id: string) => ['marketing', 'content', 'versions', id] as const,
  },
  // Legacy flat keys (backward compat)
  content: (page = 1) => ['marketing', 'content', page] as const,
  social: {
    all: ['marketing', 'social'] as const,
    dashboard: () => ['marketing', 'social', 'dashboard'] as const,
    list: (page = 1) => ['marketing', 'social', 'list', page] as const,
    detail: (id: string) => ['marketing', 'social', 'detail', id] as const,
  },
  email: {
    all: ['marketing', 'email'] as const,
    dashboard: () => ['marketing', 'email', 'dashboard'] as const,
    list: (page = 1) => ['marketing', 'email', 'list', page] as const,
    detail: (id: string) => ['marketing', 'email', 'detail', id] as const,
  },
  whatsapp: {
    all: ['marketing', 'whatsapp'] as const,
    dashboard: () => ['marketing', 'whatsapp', 'dashboard'] as const,
    list: (page = 1) => ['marketing', 'whatsapp', 'list', page] as const,
    detail: (id: string) => ['marketing', 'whatsapp', 'detail', id] as const,
  },
  sms: {
    all: ['marketing', 'sms'] as const,
    dashboard: () => ['marketing', 'sms', 'dashboard'] as const,
    list: (page = 1) => ['marketing', 'sms', 'list', page] as const,
    detail: (id: string) => ['marketing', 'sms', 'detail', id] as const,
  },
  channelCampaigns: {
    all: ['marketing', 'channelCampaigns'] as const,
    calendar: () => ['marketing', 'channelCampaigns', 'calendar'] as const,
    providerStatuses: () => ['marketing', 'channelCampaigns', 'providerStatuses'] as const,
    eligibility: (audienceId: string, channel: string) =>
      ['marketing', 'channelCampaigns', 'eligibility', audienceId, channel] as const,
  },
  // Legacy flat keys (backward compat)
  socialLegacy: () => ['marketing', 'social'] as const,
  emailLegacy: () => ['marketing', 'email'] as const,
  whatsappLegacy: () => ['marketing', 'whatsapp'] as const,
  smsLegacy: () => ['marketing', 'sms'] as const,
  advertising: () => ['marketing', 'advertising'] as const,
  events: (page = 1) => ['marketing', 'events', page] as const,
  assetsLegacy: () => ['marketing', 'assets'] as const,
  brandLegacy: () => ['marketing', 'brand'] as const,
  templatesLegacy: () => ['marketing', 'templates'] as const,
  calendar: () => ['marketing', 'calendar'] as const,
  attribution: () => ['marketing', 'attribution'] as const,
  analytics: () => ['marketing', 'analytics'] as const,
  automations: () => ['marketing', 'automation'] as const,
  automationList: (params: Record<string, unknown> = {}) => ['marketing', 'automation', 'list', params] as const,
  automationDetail: (id: string) => ['marketing', 'automation', 'detail', id] as const,
  approvals: (page = 1) => ['marketing', 'approvals', page] as const,
  budgets: (page = 1) => ['marketing', 'budgets', page] as const,
  vendors: () => ['marketing', 'vendors'] as const,
  reports: () => ['marketing', 'reports'] as const,
  settings: () => ['marketing', 'settings'] as const,
  alerts: (page = 1) => ['marketing', 'alerts', page] as const,
  recommendations: (page = 1) => ['marketing', 'recommendations', page] as const,
  channels: () => ['marketing', 'channels'] as const,
  dashboardAnalytics: {
    executive: (params: AnalyticsQueryParams = {}) => ['marketing', 'dashboard', 'executive', params] as const,
    performance: (params: AnalyticsQueryParams = {}) => ['marketing', 'dashboard', 'performance', params] as const,
    health: () => ['marketing', 'dashboard', 'health'] as const,
    trackingHealth: () => ['marketing', 'dashboard', 'tracking', 'health'] as const,
    attributionHealth: () => ['marketing', 'dashboard', 'attribution', 'health'] as const,
    dataHealth: () => ['marketing', 'dashboard', 'data', 'health'] as const,
    widgets: (key = 'executive', params: AnalyticsQueryParams = {}) =>
      ['marketing', 'dashboard', 'widgets', key, params] as const,
    funnel: (params: AnalyticsQueryParams = {}) => ['marketing', 'dashboard', 'funnel', params] as const,
    kpis: (params: AnalyticsQueryParams = {}) => ['marketing', 'dashboard', 'kpis', params] as const,
    alerts: () => ['marketing', 'dashboard', 'alerts'] as const,
    recommendations: () => ['marketing', 'dashboard', 'recommendations'] as const,
    savedViews: (dashboardKey?: string) => ['marketing', 'dashboard', 'savedViews', dashboardKey] as const,
  },
  ai: {
    dashboard: () => ['marketing', 'ai', 'dashboard'] as const,
    insights: (category?: string) => ['marketing', 'ai', 'insights', category] as const,
    recommendations: (type?: string) => ['marketing', 'ai', 'recommendations', type] as const,
    predictions: () => ['marketing', 'ai', 'predictions'] as const,
    anomalies: () => ['marketing', 'ai', 'anomalies'] as const,
    briefing: (period = 'weekly') => ['marketing', 'ai', 'briefing', period] as const,
    settings: () => ['marketing', 'ai', 'settings'] as const,
  },
};

export const marketingQueries = {
  dashboard: () => ({
    queryKey: marketingQueryKeys.dashboard(),
    queryFn: () => fetchMarketingDashboard(),
  }),
  navigation: () => ({
    queryKey: marketingQueryKeys.navigation(),
    queryFn: () => fetchMarketingNavigation(),
  }),
  quickActions: () => ({
    queryKey: marketingQueryKeys.quickActions(),
    queryFn: () => fetchMarketingQuickActions(),
  }),
  providerStatuses: () => ({
    queryKey: marketingQueryKeys.providerStatuses(),
    queryFn: () => fetchMarketingProviderStatuses(),
  }),
  campaigns: (params: CampaignListParams = {}) => ({
    queryKey: marketingQueryKeys.campaigns.list(params),
    queryFn: () => fetchCampaigns(params),
  }),
  campaign: (id: string) => ({
    queryKey: marketingQueryKeys.campaigns.detail(id),
    queryFn: () => fetchCampaign(id),
  }),
  audiences: (page = 1) => ({
    queryKey: marketingQueryKeys.audiencesLegacy(page),
    queryFn: () => fetchAudiences({ page }),
  }),
  segments: (page = 1) => ({
    queryKey: marketingQueryKeys.segmentsLegacy(page),
    queryFn: () => fetchSegments(page),
  }),
  leads: (page = 1) => ({
    queryKey: marketingQueryKeys.leadsLegacy(page),
    queryFn: () => fetchMarketingLeads(page),
  }),
  sources: (page = 1) => ({
    queryKey: marketingQueryKeys.sourcesLegacy(page),
    queryFn: () => fetchLeadSources(page),
  }),
  content: (page = 1) => ({
    queryKey: marketingQueryKeys.content(page),
    queryFn: () => fetchContentAssets(page),
  }),
  events: (page = 1) => ({
    queryKey: marketingQueryKeys.events(page),
    queryFn: () => fetchMarketingEvents(page),
  }),
  budgets: (page = 1) => ({
    queryKey: marketingQueryKeys.budgets(page),
    queryFn: () => fetchMarketingBudgets(page),
  }),
  approvals: (page = 1) => ({
    queryKey: marketingQueryKeys.approvals(page),
    queryFn: () => fetchMarketingApprovals(page),
  }),
  alerts: (page = 1) => ({
    queryKey: marketingQueryKeys.alerts(page),
    queryFn: () => fetchMarketingAlerts(page),
  }),
  recommendations: (page = 1) => ({
    queryKey: marketingQueryKeys.recommendations(page),
    queryFn: () => fetchMarketingRecommendations(page),
  }),
  channels: () => ({
    queryKey: marketingQueryKeys.channels(),
    queryFn: () => fetchMarketingChannels(),
  }),
  dashboardExecutive: (params: AnalyticsQueryParams = {}) => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.executive(params),
    queryFn: () => fetchExecutiveDashboard(params),
  }),
  dashboardPerformance: (params: AnalyticsQueryParams = {}) => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.performance(params),
    queryFn: () => fetchExecutiveDashboard(params),
  }),
  dashboardHealth: () => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.health(),
    queryFn: () => fetchMarketingHealth(),
  }),
  dashboardTrackingHealth: () => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.trackingHealth(),
    queryFn: () => fetchTrackingHealth(),
  }),
  dashboardAttributionHealth: () => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.attributionHealth(),
    queryFn: () => fetchAttributionHealth(),
  }),
  dashboardDataHealth: () => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.dataHealth(),
    queryFn: () => fetchDataHealth(),
  }),
  dashboardWidgets: (key = 'executive', params: AnalyticsQueryParams = {}) => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.widgets(key, params),
    queryFn: () => fetchDashboardWidgets(key, params),
  }),
  dashboardFunnel: (params: AnalyticsQueryParams = {}) => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.funnel(params),
    queryFn: () => fetchMarketingFunnel(params),
  }),
  dashboardKPIs: (params: AnalyticsQueryParams = {}) => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.kpis(params),
    queryFn: () => fetchMarketingKPIs(params),
  }),
  dashboardSavedViews: (dashboardKey?: string) => ({
    queryKey: marketingQueryKeys.dashboardAnalytics.savedViews(dashboardKey),
    queryFn: () => fetchDashboardSavedViews(dashboardKey),
  }),
  aiDashboard: () => ({
    queryKey: marketingQueryKeys.ai.dashboard(),
    queryFn: () => fetchAIDashboard(),
  }),
  aiInsights: (category?: string) => ({
    queryKey: marketingQueryKeys.ai.insights(category),
    queryFn: () => fetchAIInsights(category),
  }),
  aiRecommendations: (type?: string) => ({
    queryKey: marketingQueryKeys.ai.recommendations(type),
    queryFn: () => fetchAIRecommendations(type),
  }),
  aiPredictions: () => ({
    queryKey: marketingQueryKeys.ai.predictions(),
    queryFn: () => fetchAIPredictions(),
  }),
  aiAnomalies: () => ({
    queryKey: marketingQueryKeys.ai.anomalies(),
    queryFn: () => fetchAIAnomalies(),
  }),
  aiBriefing: (period = 'weekly') => ({
    queryKey: marketingQueryKeys.ai.briefing(period),
    queryFn: () => fetchAIBriefing(period),
  }),
  aiSettings: () => ({
    queryKey: marketingQueryKeys.ai.settings(),
    queryFn: () => fetchAISettings(),
  }),
};

export const marketingMutations = {
  createCampaign,
  updateCampaign,
  activateCampaign,
  pauseCampaign,
  archiveCampaign,
};
