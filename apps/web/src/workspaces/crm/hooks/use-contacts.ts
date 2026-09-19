import {
  archiveContact,
  bulkUpdateContacts,
  checkDuplicates,
  createContact,
  deleteContact,
  fetchContact,
  fetchContacts,
  fetchSavedViews,
  importContacts,
  mergeContacts,
  restoreContact,
  updateContact,
  type ContactInput,
  type ContactListParams,
} from '@/workspaces/crm/api/contacts';

export const contactQueryKeys = {
  all: ['crm', 'contacts'] as const,
  list: (params: ContactListParams) => ['crm', 'contacts', 'list', params] as const,
  detail: (id: string) => ['crm', 'contacts', 'detail', id] as const,
  savedViews: ['crm', 'contacts', 'saved-views'] as const,
};

export const contactQueries = {
  list: (params: ContactListParams) => ({
    queryKey: contactQueryKeys.list(params),
    queryFn: () => fetchContacts(params),
  }),
  detail: (id: string) => ({
    queryKey: contactQueryKeys.detail(id),
    queryFn: () => fetchContact(id),
    enabled: Boolean(id),
  }),
  savedViews: () => ({
    queryKey: contactQueryKeys.savedViews,
    queryFn: () => fetchSavedViews(),
  }),
};

export const contactMutations = {
  create: createContact,
  update: updateContact,
  archive: archiveContact,
  restore: restoreContact,
  delete: deleteContact,
  checkDuplicates,
  merge: mergeContacts,
  bulkUpdate: bulkUpdateContacts,
  import: importContacts,
};

export type { ContactInput, ContactListParams };
