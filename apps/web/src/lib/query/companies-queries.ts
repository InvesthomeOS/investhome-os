import {
  archiveCompany,
  createCompany,
  deactivateCompany,
  deleteCompany,
  duplicateCompany,
  exportCompanies,
  fetchCompanies,
  fetchCompany,
  importCompanies,
  transferCompanyOwnership,
  updateCompany,
  type CompanyCreatePayload,
  type CompanyListParams,
  type CompanyUpdatePayload,
} from '@/lib/api/companies';

export const companiesQueryKeys = {
  all: ['companies'] as const,
  list: (params: CompanyListParams) => ['companies', 'list', params] as const,
  detail: (id: string) => ['companies', 'detail', id] as const,
};

export const companiesQueries = {
  list: (params: CompanyListParams = {}) => ({
    queryKey: companiesQueryKeys.list(params),
    queryFn: () => fetchCompanies(params),
  }),
  detail: (id: string) => ({
    queryKey: companiesQueryKeys.detail(id),
    queryFn: () => fetchCompany(id),
    enabled: Boolean(id),
  }),
};

export const companiesMutations = {
  create: () => ({
    mutationFn: (payload: CompanyCreatePayload) => createCompany(payload),
  }),
  update: (id: string) => ({
    mutationFn: (payload: CompanyUpdatePayload) => updateCompany(id, payload),
  }),
  delete: () => ({
    mutationFn: (id: string) => deleteCompany(id),
  }),
  archive: () => ({
    mutationFn: (id: string) => archiveCompany(id),
  }),
  deactivate: () => ({
    mutationFn: (id: string) => deactivateCompany(id),
  }),
  duplicate: () => ({
    mutationFn: (id: string) => duplicateCompany(id),
  }),
  transferOwnership: () => ({
    mutationFn: ({ id, ownerUserId }: { id: string; ownerUserId: string }) =>
      transferCompanyOwnership(id, ownerUserId),
  }),
  export: () => ({
    mutationFn: (includeArchived?: boolean) => exportCompanies(includeArchived),
  }),
  import: () => ({
    mutationFn: (file: File) => importCompanies(file),
  }),
};
