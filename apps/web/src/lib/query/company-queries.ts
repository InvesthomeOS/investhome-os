import {
  fetchCompanyDashboard,
  fetchCompanyRecentActivity,
  searchCompanyWorkspace,
} from '@/lib/api/company-workspace';

export const companyQueryKeys = {
  dashboard: ['company', 'dashboard'] as const,
  recentActivity: (limit: number) => ['company', 'recent-activity', limit] as const,
  search: (query: string, entityTypes?: string[]) =>
    ['company', 'search', query, entityTypes?.join(',') ?? 'all'] as const,
};

export const companyQueries = {
  dashboard: () => ({
    queryKey: companyQueryKeys.dashboard,
    queryFn: fetchCompanyDashboard,
  }),
  recentActivity: (limit = 20) => ({
    queryKey: companyQueryKeys.recentActivity(limit),
    queryFn: () => fetchCompanyRecentActivity(limit),
  }),
  search: (query: string, entityTypes?: string[]) => ({
    queryKey: companyQueryKeys.search(query, entityTypes),
    queryFn: () => searchCompanyWorkspace(query, entityTypes),
    enabled: query.trim().length > 0,
  }),
};
