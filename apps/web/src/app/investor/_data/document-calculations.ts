import { getAllDocuments } from './documents';
import { getMissingRequirements } from './document-requirements';
import type {
  DocumentAlert,
  DocumentFilterState,
  DocumentFolder,
  DocumentSortState,
  DocumentSummaryKpis,
  FolderGroupMode,
  InvestorDocument,
  SidebarDocumentBadges,
  SignatureFilterState,
  SignatureRequest,
  SignatureSummaryKpis,
  SignatureTab,
} from './document-types';
import { DOCUMENT_REFERENCE_DATE } from './document-types';
import { getAllSignatureRequests } from './signature-requests';

function parseDate(dateStr: string): Date {
  return new Date(`${dateStr.includes('T') ? dateStr.split('T')[0] : dateStr}T12:00:00`);
}

export function formatDocumentBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function applyDocumentOverrides(
  documents: InvestorDocument[],
  overrides: Record<string, Partial<Pick<InvestorDocument, 'isRead' | 'isArchived' | 'status'>>>,
): InvestorDocument[] {
  return documents.map((doc) => {
    const patch = overrides[doc.id];
    return patch ? { ...doc, ...patch } : doc;
  });
}

export function applySignatureOverrides(
  requests: SignatureRequest[],
  overrides: Record<string, Partial<Pick<SignatureRequest, 'status'>>>,
): SignatureRequest[] {
  return requests.map((req) => {
    const patch = overrides[req.id];
    return patch ? { ...req, ...patch } : req;
  });
}

export function filterDocuments(
  documents: InvestorDocument[],
  filters: DocumentFilterState,
): InvestorDocument[] {
  return documents.filter((doc) => {
    if (filters.investmentId !== 'all' && doc.investmentId !== filters.investmentId) return false;
    if (filters.category !== 'all' && doc.category !== filters.category) return false;
    if (filters.documentType !== 'all' && doc.documentType !== filters.documentType) return false;
    if (filters.status !== 'all' && doc.status !== filters.status) return false;
    if (filters.fileType !== 'all' && doc.fileType !== filters.fileType) return false;
    if (filters.taxYear !== 'all' && doc.taxYear !== filters.taxYear) return false;
    if (filters.accessLevel !== 'all' && doc.accessLevel !== filters.accessLevel) return false;
    if (filters.requiresSignature === 'yes' && !doc.requiresSignature) return false;
    if (filters.requiresSignature === 'no' && doc.requiresSignature) return false;
    if (filters.isRead === 'read' && !doc.isRead) return false;
    if (filters.isRead === 'unread' && doc.isRead) return false;
    if (filters.isArchived === 'active' && doc.isArchived) return false;
    if (filters.isArchived === 'archived' && !doc.isArchived) return false;
    if (filters.tags.length > 0 && !filters.tags.some((t) => doc.tags.includes(t))) return false;
    if (filters.dateFrom && parseDate(doc.uploadedAt) < parseDate(filters.dateFrom)) return false;
    if (filters.dateTo && parseDate(doc.uploadedAt) > parseDate(filters.dateTo)) return false;
    if (filters.search.trim()) {
      const q = filters.search.toLowerCase();
      const haystack = [
        doc.title,
        doc.description,
        doc.investmentName,
        doc.entityName,
        doc.fileName,
        doc.category,
        doc.documentType,
      ]
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

export function sortDocuments(
  documents: InvestorDocument[],
  sort: DocumentSortState,
): InvestorDocument[] {
  const sorted = [...documents];
  const dir = sort.direction === 'asc' ? 1 : -1;
  sorted.sort((a, b) => {
    switch (sort.field) {
      case 'title':
        return dir * a.title.localeCompare(b.title);
      case 'uploadedAt':
        return dir * (parseDate(a.uploadedAt).getTime() - parseDate(b.uploadedAt).getTime());
      case 'updatedAt':
        return dir * (parseDate(a.updatedAt).getTime() - parseDate(b.updatedAt).getTime());
      case 'investmentName':
        return dir * a.investmentName.localeCompare(b.investmentName);
      case 'category':
        return dir * a.category.localeCompare(b.category);
      case 'fileSizeBytes':
        return dir * (a.fileSizeBytes - b.fileSizeBytes);
      case 'status':
        return dir * a.status.localeCompare(b.status);
      default:
        return 0;
    }
  });
  return sorted;
}

export function computeDocumentSummary(
  documents: InvestorDocument[],
  signatureRequests: SignatureRequest[],
): DocumentSummaryKpis {
  const ref = parseDate(DOCUMENT_REFERENCE_DATE);
  const expiringThreshold = new Date(ref);
  expiringThreshold.setDate(expiringThreshold.getDate() + 30);

  const activeDocs = documents.filter((d) => !d.isArchived);
  const actionRequiredSigs = signatureRequests.filter((s) => s.status === 'action_required');
  const completedSigs = signatureRequests.filter((s) => s.status === 'completed');

  return {
    totalDocuments: activeDocs.length,
    newDocuments: activeDocs.filter((d) => d.status === 'new' || !d.isRead).length,
    pendingSignatures: actionRequiredSigs.length,
    completedSignatures: completedSigs.length,
    taxDocuments: activeDocs.filter((d) => d.category === 'tax').length,
    expiringSoon: activeDocs.filter(
      (d) => d.expiresAt && parseDate(d.expiresAt) <= expiringThreshold && parseDate(d.expiresAt) >= ref,
    ).length,
    missingDocuments: getMissingRequirements().length,
    storageUsedBytes: activeDocs.reduce((sum, d) => sum + d.fileSizeBytes, 0),
  };
}

export function computeSignatureSummary(
  requests: SignatureRequest[],
): SignatureSummaryKpis {
  return {
    actionRequired: requests.filter((s) => s.status === 'action_required').length,
    waitingOnOthers: requests.filter((s) => s.status === 'waiting_on_others').length,
    completed: requests.filter((s) => s.status === 'completed').length,
    declined: requests.filter((s) => s.status === 'declined').length,
    expired: requests.filter((s) => s.status === 'expired').length,
    voided: requests.filter((s) => s.status === 'voided').length,
    total: requests.length,
  };
}

export function filterSignatureRequestsByTab(
  requests: SignatureRequest[],
  tab: SignatureTab,
): SignatureRequest[] {
  if (tab === 'all') return requests;
  const statusMap: Record<Exclude<SignatureTab, 'all'>, SignatureRequest['status']> = {
    action_required: 'action_required',
    waiting_on_others: 'waiting_on_others',
    completed: 'completed',
    declined: 'declined',
    expired: 'expired',
    voided: 'voided',
  };
  return requests.filter((s) => s.status === statusMap[tab]);
}

export function filterSignatureRequests(
  requests: SignatureRequest[],
  filters: SignatureFilterState,
): SignatureRequest[] {
  return requests.filter((req) => {
    if (filters.investmentId !== 'all' && req.investmentId !== filters.investmentId) return false;
    if (filters.status !== 'all' && req.status !== filters.status) return false;
    if (filters.dateFrom && parseDate(req.createdAt) < parseDate(filters.dateFrom)) return false;
    if (filters.dateTo && parseDate(req.createdAt) > parseDate(filters.dateTo)) return false;
    if (filters.search.trim()) {
      const q = filters.search.toLowerCase();
      const haystack = [req.documentTitle, req.investmentName, req.entityName, req.message]
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

export function computeDocumentAlerts(
  documents: InvestorDocument[],
  signatureRequests: SignatureRequest[],
): DocumentAlert[] {
  const ref = parseDate(DOCUMENT_REFERENCE_DATE);
  const alerts: DocumentAlert[] = [];

  signatureRequests
    .filter((s) => s.status === 'action_required')
    .forEach((s) => {
      const daysLeft = Math.ceil(
        (parseDate(s.expiresAt).getTime() - ref.getTime()) / (1000 * 60 * 60 * 24),
      );
      alerts.push({
        id: `alert-sig-${s.id}`,
        title: 'Signature Required',
        message: `"${s.documentTitle}" requires your signature${daysLeft > 0 ? ` — expires in ${daysLeft} days` : ' — expiring soon'}.`,
        severity: daysLeft <= 7 ? 'urgent' : 'warning',
        documentId: s.documentId,
        signatureRequestId: s.id,
        investmentId: s.investmentId,
        actionLabel: 'Review & Sign',
        actionHref: `/investor/signatures/${s.id}`,
        createdAt: s.sentAt ?? s.createdAt,
      });
    });

  documents
    .filter((d) => !d.isRead && !d.isArchived && d.status === 'new')
    .slice(0, 3)
    .forEach((d) => {
      alerts.push({
        id: `alert-doc-${d.id}`,
        title: 'New Document',
        message: `"${d.title}" is available for review.`,
        severity: 'info',
        documentId: d.id,
        signatureRequestId: null,
        investmentId: d.investmentId,
        actionLabel: 'View Document',
        actionHref: `/investor/documents/${d.id}`,
        createdAt: d.uploadedAt,
      });
    });

  getMissingRequirements().forEach((req) => {
    alerts.push({
      id: `alert-req-${req.id}`,
      title: 'Missing Document',
      message: req.description,
      severity: req.priority === 'high' ? 'urgent' : 'warning',
      documentId: null,
      signatureRequestId: null,
      investmentId: req.investmentId,
      actionLabel: 'View Requirements',
      actionHref: '/investor/documents#missing-documents',
      createdAt: req.dueDate,
    });
  });

  return alerts.sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function computeSidebarBadges(
  documents: InvestorDocument[],
  signatureRequests: SignatureRequest[],
): SidebarDocumentBadges {
  const activeDocs = documents.filter((d) => !d.isArchived);
  return {
    unread: activeDocs.filter((d) => !d.isRead).length,
    pendingSignatures: signatureRequests.filter((s) => s.status === 'action_required').length,
    missing: getMissingRequirements().length,
    total: activeDocs.filter((d) => !d.isRead).length +
      signatureRequests.filter((s) => s.status === 'action_required').length +
      getMissingRequirements().length,
  };
}

export function buildDocumentFolders(
  documents: InvestorDocument[],
  groupMode: FolderGroupMode,
  parentKey: string | null = null,
): DocumentFolder[] {
  const active = documents.filter((d) => !d.isArchived);
  const groups = new Map<string, { name: string; count: number }>();

  active.forEach((doc) => {
    let key: string;
    let name: string;
    switch (groupMode) {
      case 'investment':
        key = doc.investmentId;
        name = doc.investmentName;
        break;
      case 'entity':
        key = doc.entityName;
        name = doc.entityName;
        break;
      case 'category':
        key = doc.category;
        name = doc.category;
        break;
      case 'year':
        key = String(parseDate(doc.uploadedAt).getFullYear());
        name = key;
        break;
      default:
        key = 'other';
        name = 'Other';
    }
    const existing = groups.get(key);
    if (existing) {
      existing.count += 1;
    } else {
      groups.set(key, { name, count: 1 });
    }
  });

  if (parentKey === null) {
    return Array.from(groups.entries())
      .map(([key, { name, count }]) => ({
        id: `${groupMode}-${key}`,
        name,
        parentId: null,
        documentCount: count,
        groupMode,
        groupKey: key,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  return active
    .filter((doc) => {
      switch (groupMode) {
        case 'investment':
          return doc.investmentId === parentKey;
        case 'entity':
          return doc.entityName === parentKey;
        case 'category':
          return doc.category === parentKey;
        case 'year':
          return String(parseDate(doc.uploadedAt).getFullYear()) === parentKey;
        default:
          return false;
      }
    })
    .map((doc) => ({
      id: doc.id,
      name: doc.title,
      parentId: `${groupMode}-${parentKey}`,
      documentCount: 1,
      groupMode,
      groupKey: doc.id,
    }));
}

export function getDocumentsInFolder(
  documents: InvestorDocument[],
  groupMode: FolderGroupMode,
  folderKey: string,
): InvestorDocument[] {
  const active = documents.filter((d) => !d.isArchived);
  return active.filter((doc) => {
    switch (groupMode) {
      case 'investment':
        return doc.investmentId === folderKey;
      case 'entity':
        return doc.entityName === folderKey;
      case 'category':
        return doc.category === folderKey;
      case 'year':
        return String(parseDate(doc.uploadedAt).getFullYear()) === folderKey;
      default:
        return false;
    }
  });
}

export function getAvailableTaxYears(documents: InvestorDocument[]): number[] {
  const years = new Set<number>();
  documents.forEach((d) => {
    if (d.taxYear) years.add(d.taxYear);
  });
  return Array.from(years).sort((a, b) => b - a);
}

export function createMockDownloadBlob(doc: InvestorDocument): Blob {
  const content = JSON.stringify(
    {
      demo: true,
      disclaimer: 'Demonstration Only — Not Legally Binding',
      document: {
        id: doc.id,
        title: doc.title,
        fileName: doc.fileName,
        investment: doc.investmentName,
        generatedAt: new Date().toISOString(),
      },
      note: 'This is a placeholder file for demo purposes. No actual document content is included.',
    },
    null,
    2,
  );
  return new Blob([content], { type: 'application/json' });
}

export function getMergedDocumentsAndSignatures(
  docOverrides: Record<string, Partial<Pick<InvestorDocument, 'isRead' | 'isArchived' | 'status'>>>,
  sigOverrides: Record<string, Partial<Pick<SignatureRequest, 'status'>>>,
): { documents: InvestorDocument[]; signatureRequests: SignatureRequest[] } {
  return {
    documents: applyDocumentOverrides(getAllDocuments(), docOverrides),
    signatureRequests: applySignatureOverrides(getAllSignatureRequests(), sigOverrides),
  };
}
