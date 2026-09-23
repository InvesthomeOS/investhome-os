export type DocumentViewMode = 'card' | 'table';

export type DocumentAiActionKey =
  | 'summarize'
  | 'missing'
  | 'awaitingSignature'
  | 'recent';

export type DocumentFileType = 'pdf' | 'docx' | 'xlsx';

export type DocumentStatusKey = 'signed' | 'awaitingSignature' | 'shared' | 'draft' | 'rejected';

export type DocumentKpiKey =
  | 'total'
  | 'awaitingSignature'
  | 'addedLast7Days'
  | 'shared';

export type DocumentCard = {
  id: string;
  name: string;
  fileType: DocumentFileType;
  owner: string;
  project: string;
  status: DocumentStatusKey;
  size: string;
  version: string;
  date: string;
};

export type DocumentKpi = {
  key: DocumentKpiKey;
  value: number;
  hintKey: string;
  delta: string;
  deltaTone: 'up' | 'down' | 'neutral';
};

export type DocumentRecentOpened = {
  id: string;
  name: string;
  fileType: DocumentFileType;
  openedAtKey: 'minutesAgo10' | 'hoursAgo1' | 'yesterday';
};

export type DocumentSignatureDistribution = {
  signed: number;
  awaiting: number;
  rejected: number;
};

export type DocumentMissingItem = {
  id: string;
  labelKey: string;
};

export type DocumentActivity = {
  id: string;
  titleKey: string;
  timeKey: string;
};

export type DocumentAiSummary = {
  title: string;
  bodyKey: string;
  /** Presentation fixture date — locale-neutral DD.MM.YYYY */
  lastUpdated: string;
};

export type DocumentWorkspacePreview = {
  totalDocuments: number;
  kpis: DocumentKpi[];
  documents: DocumentCard[];
  aiSummary: DocumentAiSummary;
  recentlyOpened: DocumentRecentOpened[];
  signatureDistribution: DocumentSignatureDistribution;
  missingCount: number;
  missingItems: DocumentMissingItem[];
  activities: DocumentActivity[];
  customers: string[];
  projects: string[];
  documentTypes: DocumentFileType[];
};
