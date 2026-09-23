import {
  fetchCrmDocumentFeed,
  setCrmDocumentHubVisibility,
  type CrmDocumentFeedParams,
} from '@/workspaces/crm/api/crm-documents';

export const crmDocumentQueryKeys = {
  all: ['crm', 'documents'] as const,
  feed: (params: CrmDocumentFeedParams) => ['crm', 'documents', 'feed', params] as const,
};

export const crmDocumentQueries = {
  feed: (params: CrmDocumentFeedParams = {}) => ({
    queryKey: crmDocumentQueryKeys.feed(params),
    queryFn: () => fetchCrmDocumentFeed(params),
  }),
};

export function hideCrmDocument(documentId: string, hidden: boolean) {
  return setCrmDocumentHubVisibility(documentId, hidden);
}
