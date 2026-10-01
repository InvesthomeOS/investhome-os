import {
  archiveCrmCompany,
  createCrmCompany,
  deleteCrmCompany,
  fetchCrmCompanies,
  fetchCrmCompany,
  fetchCrmCompanyCounts,
  importCrmCompanies,
  restoreCrmCompany,
  updateCrmCompany,
} from '@/workspaces/crm/api/companies';
import type { FetchCrmCompaniesParams } from '@/workspaces/crm/api/companies';

export const crmCompaniesQueryKeys = {
  all: ['crm', 'companies'] as const,
  counts: () => ['crm', 'companies', 'counts'] as const,
  list: (params: FetchCrmCompaniesParams) => ['crm', 'companies', 'list', params] as const,
  detail: (id: string) => ['crm', 'companies', 'detail', id] as const,
  hierarchy: () => ['crm', 'companies', 'hierarchy'] as const,
  savedViews: () => ['crm', 'companies', 'saved-views'] as const,
  timeline: (id: string) => ['crm', 'companies', 'timeline', id] as const,
};

export const crmCompaniesQueries = {
  counts: () => ({
    queryKey: crmCompaniesQueryKeys.counts(),
    queryFn: fetchCrmCompanyCounts,
  }),
  list: (params: FetchCrmCompaniesParams = {}) => ({
    queryKey: crmCompaniesQueryKeys.list(params),
    queryFn: () => fetchCrmCompanies(params),
  }),
  detail: (id: string) => ({
    queryKey: crmCompaniesQueryKeys.detail(id),
    queryFn: () => fetchCrmCompany(id),
    enabled: Boolean(id),
  }),
};

export const crmCompaniesMutations = {
  create: () => ({
    mutationFn: createCrmCompany,
  }),
  update: (id: string) => ({
    mutationFn: (payload: Record<string, unknown>) => updateCrmCompany(id, payload),
  }),
  archive: () => ({
    mutationFn: archiveCrmCompany,
  }),
  restore: () => ({
    mutationFn: restoreCrmCompany,
  }),
  delete: () => ({
    mutationFn: deleteCrmCompany,
  }),
  import: () => ({
    mutationFn: importCrmCompanies,
  }),
};
