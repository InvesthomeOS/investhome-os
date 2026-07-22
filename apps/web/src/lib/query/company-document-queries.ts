import {
  fetchCompanyDocument,
  fetchCompanyDocuments,
  fetchDocumentFolders,
  fetchStorageSummary,
  type CompanyDocumentListParams,
} from '@/lib/api/company-documents';

export const companyDocumentQueryKeys = {
  all: ['company-documents'] as const,
  list: (params: CompanyDocumentListParams) => ['company-documents', 'list', params] as const,
  detail: (id: string) => ['company-documents', 'detail', id] as const,
  folders: (companyId: string) => ['company-documents', 'folders', companyId] as const,
  summary: (companyId?: string) => ['company-documents', 'summary', companyId] as const,
};

export const companyDocumentQueries = {
  list: (params: CompanyDocumentListParams) => ({
    queryKey: companyDocumentQueryKeys.list(params),
    queryFn: () => fetchCompanyDocuments(params),
  }),
  detail: (id: string) => ({
    queryKey: companyDocumentQueryKeys.detail(id),
    queryFn: () => fetchCompanyDocument(id),
    enabled: Boolean(id),
  }),
  folders: (companyId: string) => ({
    queryKey: companyDocumentQueryKeys.folders(companyId),
    queryFn: () => fetchDocumentFolders(companyId),
    enabled: Boolean(companyId),
  }),
  summary: (companyId?: string) => ({
    queryKey: companyDocumentQueryKeys.summary(companyId),
    queryFn: () => fetchStorageSummary(companyId),
  }),
};
