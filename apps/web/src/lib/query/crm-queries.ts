import { fetchCrmDashboard } from '@/workspaces/crm/api/crm';
import { fetchContacts } from '@/workspaces/crm/api/contacts';
import type { ContactListParams } from '@/workspaces/crm/api/contacts';

export type FetchCrmContactsParams = ContactListParams & {
  pageSize?: number;
  contactType?: string;
  includeArchived?: boolean;
};

export const crmContactQueryKeys = {
  all: ['crm', 'contacts'] as const,
  list: (params: FetchCrmContactsParams) => ['crm', 'contacts', params] as const,
};

export const crmContactQueries = {
  list: (params: FetchCrmContactsParams = {}) => ({
    queryKey: crmContactQueryKeys.list(params),
    queryFn: () =>
      fetchContacts({
        ...params,
        page_size: params.pageSize ?? params.page_size,
        contact_type: (params.contactType as ContactListParams['contact_type']) ?? params.contact_type,
        include_archived: params.includeArchived ?? params.include_archived,
      }),
  }),
};

export const crmQueries = {
  dashboard: () => ({
    queryKey: ['crm', 'dashboard'] as const,
    queryFn: () => fetchCrmDashboard(),
  }),
  contacts: (params: FetchCrmContactsParams = {}) => crmContactQueries.list(params),
};

export { fetchContacts as fetchCrmContacts };
