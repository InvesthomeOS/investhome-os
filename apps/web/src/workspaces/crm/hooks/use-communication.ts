import {
  archiveCommunication,
  archiveThread,
  createCommunication,
  createSequence,
  createSignature,
  createTemplate,
  fetchCallLogs,
  fetchCommunication,
  fetchCommunicationAnalytics,
  fetchCommunications,
  fetchCommunicationThread,
  fetchCommunicationThreads,
  fetchMeetings,
  fetchProviderStatuses,
  fetchSequences,
  fetchSignatures,
  fetchTemplates,
  fetchUnmatchedCommunications,
  fetchCommunicationAccounts,
  fetchCommunicationFeed,
  fetchWhatsappConversation,
  markThreadRead,
  type CommunicationListParams,
  type ThreadListParams,
} from '@/workspaces/crm/api/communication';

export const communicationQueryKeys = {
  all: ['crm', 'communications'] as const,
  threads: (params: ThreadListParams) => ['crm', 'communications', 'threads', params] as const,
  threadDetail: (id: string) => ['crm', 'communications', 'thread', id] as const,
  list: (params: CommunicationListParams) => ['crm', 'communications', 'list', params] as const,
  detail: (id: string) => ['crm', 'communications', 'detail', id] as const,
  calls: (params: CommunicationListParams) => ['crm', 'communications', 'calls', params] as const,
  meetings: (params: CommunicationListParams) => ['crm', 'communications', 'meetings', params] as const,
  templates: (params: { search?: string; page?: number }) => ['crm', 'communications', 'templates', params] as const,
  sequences: (params: { page?: number }) => ['crm', 'communications', 'sequences', params] as const,
  signatures: ['crm', 'communications', 'signatures'] as const,
  analytics: ['crm', 'communications', 'analytics'] as const,
  providers: ['crm', 'communications', 'providers'] as const,
  accounts: ['crm', 'communications', 'accounts'] as const,
  unmatched: (params: { page?: number } = {}) => ['crm', 'communications', 'unmatched', params] as const,
  feed: (params: object) => ['crm', 'communications', 'feed', params] as const,
  conversation: (params: object) => ['crm', 'communications', 'conversation', params] as const,
};

export const communicationQueries = {
  threads: (params: ThreadListParams) => ({
    queryKey: communicationQueryKeys.threads(params),
    queryFn: () => fetchCommunicationThreads(params),
  }),
  threadDetail: (id: string | null) => ({
    queryKey: communicationQueryKeys.threadDetail(id ?? ''),
    queryFn: () => fetchCommunicationThread(id!),
    enabled: Boolean(id),
  }),
  list: (params: CommunicationListParams) => ({
    queryKey: communicationQueryKeys.list(params),
    queryFn: () => fetchCommunications(params),
  }),
  detail: (id: string | null) => ({
    queryKey: communicationQueryKeys.detail(id ?? ''),
    queryFn: () => fetchCommunication(id!),
    enabled: Boolean(id),
  }),
  calls: (params: CommunicationListParams = {}) => ({
    queryKey: communicationQueryKeys.calls(params),
    queryFn: () => fetchCallLogs(params),
  }),
  meetings: (params: CommunicationListParams = {}) => ({
    queryKey: communicationQueryKeys.meetings(params),
    queryFn: () => fetchMeetings(params),
  }),
  templates: (params: { search?: string; page?: number } = {}) => ({
    queryKey: communicationQueryKeys.templates(params),
    queryFn: () => fetchTemplates(params),
  }),
  sequences: (params: { page?: number } = {}) => ({
    queryKey: communicationQueryKeys.sequences(params),
    queryFn: () => fetchSequences(params),
  }),
  signatures: () => ({
    queryKey: communicationQueryKeys.signatures,
    queryFn: () => fetchSignatures(),
  }),
  analytics: () => ({
    queryKey: communicationQueryKeys.analytics,
    queryFn: () => fetchCommunicationAnalytics(),
  }),
  providers: () => ({
    queryKey: communicationQueryKeys.providers,
    queryFn: () => fetchProviderStatuses(),
  }),
  accounts: () => ({
    queryKey: communicationQueryKeys.accounts,
    queryFn: () => fetchCommunicationAccounts(),
  }),
  unmatched: (params: { page?: number } = {}) => ({
    queryKey: communicationQueryKeys.unmatched(params),
    queryFn: () => fetchUnmatchedCommunications(params),
  }),
  feed: (params: Parameters<typeof fetchCommunicationFeed>[0] = {}) => ({
    queryKey: communicationQueryKeys.feed(params),
    queryFn: () => fetchCommunicationFeed(params),
  }),
  conversation: (params: Parameters<typeof fetchWhatsappConversation>[0]) => ({
    queryKey: communicationQueryKeys.conversation(params),
    queryFn: () => fetchWhatsappConversation(params),
  }),
};

export const communicationMutations = {
  createCommunication,
  archiveCommunication,
  markThreadRead,
  archiveThread,
  createTemplate,
  createSignature,
  createSequence,
};
