export const DOCUMENT_CATEGORIES = [
  'subscription',
  'tax',
  'financial',
  'legal',
  'report',
  'insurance',
  'compliance',
  'correspondence',
  'signature',
] as const;

export type DocumentCategory = (typeof DOCUMENT_CATEGORIES)[number];

export const DOCUMENT_TYPES = [
  'subscription_agreement',
  'operating_agreement',
  'side_letter',
  'w9',
  'k1',
  '1099',
  'accreditation_letter',
  'investor_update',
  'quarterly_report',
  'annual_report',
  'capital_call_notice',
  'distribution_statement',
  'insurance_certificate',
  'title_report',
  'appraisal',
  'amendment',
  'consent_form',
  'nda',
  'wire_instructions',
  'other',
] as const;

export type DocumentType = (typeof DOCUMENT_TYPES)[number];

export const DOCUMENT_STATUSES = [
  'new',
  'viewed',
  'signed',
  'pending_signature',
  'archived',
  'expired',
] as const;

export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

export const DOCUMENT_ACCESS_LEVELS = ['standard', 'restricted', 'confidential'] as const;

export type DocumentAccessLevel = (typeof DOCUMENT_ACCESS_LEVELS)[number];

export const DOCUMENT_FILE_TYPES = ['pdf', 'docx', 'xlsx', 'png', 'jpg', 'csv', 'zip'] as const;

export type DocumentFileType = (typeof DOCUMENT_FILE_TYPES)[number];

export const DOCUMENT_TAGS = [
  'required',
  'tax_season',
  'signature_needed',
  'annual',
  'quarterly',
  'legal_hold',
] as const;

export type DocumentTag = (typeof DOCUMENT_TAGS)[number];

export const FOLDER_GROUP_MODES = ['investment', 'entity', 'category', 'year'] as const;

export type FolderGroupMode = (typeof FOLDER_GROUP_MODES)[number];

export const LIBRARY_VIEW_MODES = ['table', 'grid', 'folder'] as const;

export type LibraryViewMode = (typeof LIBRARY_VIEW_MODES)[number];

export interface DocumentVersion {
  id: string;
  versionNumber: number;
  uploadedAt: string;
  uploadedBy: string;
  fileSizeBytes: number;
  changeNotes: string | null;
  isCurrent: boolean;
}

export interface DocumentActivity {
  id: string;
  timestamp: string;
  actor: string;
  action: 'uploaded' | 'viewed' | 'downloaded' | 'signed' | 'shared' | 'archived' | 'commented';
  description: string;
}

export interface DocumentFolder {
  id: string;
  name: string;
  parentId: string | null;
  documentCount: number;
  groupMode: FolderGroupMode;
  groupKey: string;
}

export interface InvestorDocument {
  id: string;
  title: string;
  description: string;
  investmentId: string;
  investmentName: string;
  entityName: string;
  category: DocumentCategory;
  documentType: DocumentType;
  status: DocumentStatus;
  accessLevel: DocumentAccessLevel;
  fileType: DocumentFileType;
  fileName: string;
  fileSizeBytes: number;
  pageCount: number | null;
  uploadedAt: string;
  updatedAt: string;
  expiresAt: string | null;
  taxYear: number | null;
  isRead: boolean;
  isArchived: boolean;
  requiresSignature: boolean;
  signatureRequestId: string | null;
  distributionStatementId: string | null;
  distributionId: string | null;
  tags: DocumentTag[];
  versions: DocumentVersion[];
  activity: DocumentActivity[];
  relatedDocumentIds: string[];
}

export const SIGNATURE_REQUEST_STATUSES = [
  'draft',
  'sent',
  'action_required',
  'waiting_on_others',
  'completed',
  'declined',
  'expired',
  'voided',
] as const;

export type SignatureRequestStatus = (typeof SIGNATURE_REQUEST_STATUSES)[number];

export const SIGNATURE_RECIPIENT_STATUSES = [
  'pending',
  'sent',
  'viewed',
  'signed',
  'declined',
  'delegated',
] as const;

export type SignatureRecipientStatus = (typeof SIGNATURE_RECIPIENT_STATUSES)[number];

export const SIGNATURE_FIELD_TYPES = [
  'signature',
  'initials',
  'date',
  'text',
  'checkbox',
  'name',
] as const;

export type SignatureFieldType = (typeof SIGNATURE_FIELD_TYPES)[number];

export const SIGNATURE_METHODS = ['typed', 'drawn', 'uploaded'] as const;

export type SignatureMethod = (typeof SIGNATURE_METHODS)[number];

export interface SignatureField {
  id: string;
  type: SignatureFieldType;
  label: string;
  page: number;
  required: boolean;
  recipientId: string;
  value: string | null;
  completedAt: string | null;
}

export interface SignatureRecipient {
  id: string;
  name: string;
  email: string;
  role: 'investor' | 'sponsor' | 'witness' | 'co_investor' | 'legal';
  status: SignatureRecipientStatus;
  order: number;
  signedAt: string | null;
  isCurrentUser: boolean;
}

export interface SignatureEvent {
  id: string;
  timestamp: string;
  type: 'created' | 'sent' | 'viewed' | 'signed' | 'declined' | 'reminded' | 'expired' | 'voided';
  actor: string;
  description: string;
  ipAddressMasked: string;
}

export interface SignatureAuditEntry {
  id: string;
  timestamp: string;
  event: string;
  actor: string;
  details: string;
  ipAddressMasked: string;
  userAgent: string;
}

export interface SignatureRequest {
  id: string;
  documentId: string;
  documentTitle: string;
  investmentId: string;
  investmentName: string;
  entityName: string;
  status: SignatureRequestStatus;
  createdAt: string;
  sentAt: string | null;
  expiresAt: string;
  completedAt: string | null;
  declinedAt: string | null;
  voidedAt: string | null;
  message: string;
  recipients: SignatureRecipient[];
  fields: SignatureField[];
  events: SignatureEvent[];
  auditTrail: SignatureAuditEntry[];
  certificateId: string | null;
  isDemoOnly: true;
}

export const DOCUMENT_REQUIREMENT_STATUSES = [
  'missing',
  'pending_review',
  'submitted',
  'approved',
  'expired',
] as const;

export type DocumentRequirementStatus = (typeof DOCUMENT_REQUIREMENT_STATUSES)[number];

export interface DocumentRequirement {
  id: string;
  title: string;
  description: string;
  documentType: DocumentType;
  investmentId: string | null;
  investmentName: string | null;
  status: DocumentRequirementStatus;
  dueDate: string;
  priority: 'low' | 'medium' | 'high';
  category: DocumentCategory;
}

export const DOCUMENT_ALERT_SEVERITIES = ['info', 'warning', 'urgent'] as const;

export type DocumentAlertSeverity = (typeof DOCUMENT_ALERT_SEVERITIES)[number];

export interface DocumentAlert {
  id: string;
  title: string;
  message: string;
  severity: DocumentAlertSeverity;
  documentId: string | null;
  signatureRequestId: string | null;
  investmentId: string | null;
  actionLabel: string;
  actionHref: string;
  createdAt: string;
}

export interface DocumentFilterState {
  search: string;
  investmentId: string | 'all';
  category: DocumentCategory | 'all';
  documentType: DocumentType | 'all';
  status: DocumentStatus | 'all';
  fileType: DocumentFileType | 'all';
  taxYear: number | 'all';
  accessLevel: DocumentAccessLevel | 'all';
  requiresSignature: 'all' | 'yes' | 'no';
  isRead: 'all' | 'read' | 'unread';
  isArchived: 'all' | 'active' | 'archived';
  tags: DocumentTag[];
  dateFrom: string;
  dateTo: string;
}

export type DocumentSortField =
  | 'title'
  | 'uploadedAt'
  | 'updatedAt'
  | 'investmentName'
  | 'category'
  | 'fileSizeBytes'
  | 'status';

export interface DocumentSortState {
  field: DocumentSortField;
  direction: 'asc' | 'desc';
}

export interface DocumentSummaryKpis {
  totalDocuments: number;
  newDocuments: number;
  pendingSignatures: number;
  completedSignatures: number;
  taxDocuments: number;
  expiringSoon: number;
  missingDocuments: number;
  storageUsedBytes: number;
}

export interface SignatureFilterState {
  search: string;
  investmentId: string | 'all';
  status: SignatureRequestStatus | 'all';
  dateFrom: string;
  dateTo: string;
}

export type SignatureTab =
  | 'action_required'
  | 'waiting_on_others'
  | 'completed'
  | 'declined'
  | 'expired'
  | 'voided'
  | 'all';

export interface SignatureSummaryKpis {
  actionRequired: number;
  waitingOnOthers: number;
  completed: number;
  declined: number;
  expired: number;
  voided: number;
  total: number;
}

export interface SidebarDocumentBadges {
  unread: number;
  pendingSignatures: number;
  missing: number;
  total: number;
}

export const DOCUMENT_REFERENCE_DATE = '2025-07-16';

export const DEMO_VERIFICATION_CODE = '123456';

export const DEMONSTRATION_DISCLAIMER =
  'Demonstration Only — Not Legally Binding';
