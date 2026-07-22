'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  computeDocumentAlerts,
  computeDocumentSummary,
  computeSidebarBadges,
  computeSignatureSummary,
  getMergedDocumentsAndSignatures,
} from '../_data/document-calculations';
import type {
  DocumentFilterState,
  DocumentSortState,
  DocumentSummaryKpis,
  InvestorDocument,
  LibraryViewMode,
  SignatureRequest,
  SignatureSummaryKpis,
} from '../_data/document-types';
import type { DocumentAlert } from '../_data/document-types';
import type { SidebarDocumentBadges } from '../_data/document-types';

const STORAGE_KEY = 'investor-documents-state-v1';

interface PersistedState {
  documentOverrides: Record<string, Partial<Pick<InvestorDocument, 'isRead' | 'isArchived' | 'status'>>>;
  signatureOverrides: Record<string, Partial<Pick<SignatureRequest, 'status'>>>;
  viewMode: LibraryViewMode;
  preferences: DocumentPreferences;
}

export interface DocumentPreferences {
  emailNotifications: boolean;
  autoArchiveSigned: boolean;
  defaultView: LibraryViewMode;
  downloadFormat: 'original' | 'pdf';
}

const DEFAULT_PREFERENCES: DocumentPreferences = {
  emailNotifications: true,
  autoArchiveSigned: false,
  defaultView: 'table',
  downloadFormat: 'original',
};

interface DocumentsStateContextValue {
  documents: InvestorDocument[];
  signatureRequests: SignatureRequest[];
  summary: DocumentSummaryKpis;
  signatureSummary: SignatureSummaryKpis;
  alerts: DocumentAlert[];
  sidebarBadges: SidebarDocumentBadges;
  viewMode: LibraryViewMode;
  setViewMode: (mode: LibraryViewMode) => void;
  preferences: DocumentPreferences;
  setPreferences: (prefs: Partial<DocumentPreferences>) => void;
  markAsRead: (documentId: string) => void;
  archiveDocument: (documentId: string) => void;
  unarchiveDocument: (documentId: string) => void;
  completeSignature: (signatureRequestId: string) => void;
  declineSignature: (signatureRequestId: string, reason: string) => void;
  selectedDocumentIds: string[];
  setSelectedDocumentIds: (ids: string[]) => void;
  toggleDocumentSelection: (id: string) => void;
  clearSelection: () => void;
}

const DocumentsStateContext = createContext<DocumentsStateContextValue | null>(null);

function loadPersistedState(): Partial<PersistedState> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as Partial<PersistedState>;
  } catch {
    return {};
  }
}

function savePersistedState(state: PersistedState): void {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore quota errors in demo
  }
}

export function DocumentsStateProvider({ children }: { children: ReactNode }) {
  const [documentOverrides, setDocumentOverrides] = useState<
    PersistedState['documentOverrides']
  >({});
  const [signatureOverrides, setSignatureOverrides] = useState<
    PersistedState['signatureOverrides']
  >({});
  const [viewMode, setViewModeState] = useState<LibraryViewMode>('table');
  const [preferences, setPreferencesState] = useState<DocumentPreferences>(DEFAULT_PREFERENCES);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const persisted = loadPersistedState();
    if (persisted.documentOverrides) setDocumentOverrides(persisted.documentOverrides);
    if (persisted.signatureOverrides) setSignatureOverrides(persisted.signatureOverrides);
    if (persisted.viewMode) setViewModeState(persisted.viewMode);
    if (persisted.preferences) setPreferencesState({ ...DEFAULT_PREFERENCES, ...persisted.preferences });
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    savePersistedState({
      documentOverrides,
      signatureOverrides,
      viewMode,
      preferences,
    });
  }, [hydrated, documentOverrides, signatureOverrides, viewMode, preferences]);

  const { documents, signatureRequests } = useMemo(
    () => getMergedDocumentsAndSignatures(documentOverrides, signatureOverrides),
    [documentOverrides, signatureOverrides],
  );

  const summary = useMemo(
    () => computeDocumentSummary(documents, signatureRequests),
    [documents, signatureRequests],
  );

  const signatureSummary = useMemo(
    () => computeSignatureSummary(signatureRequests),
    [signatureRequests],
  );

  const alerts = useMemo(
    () => computeDocumentAlerts(documents, signatureRequests),
    [documents, signatureRequests],
  );

  const sidebarBadges = useMemo(
    () => computeSidebarBadges(documents, signatureRequests),
    [documents, signatureRequests],
  );

  const setViewMode = useCallback((mode: LibraryViewMode) => {
    setViewModeState(mode);
  }, []);

  const setPreferences = useCallback((patch: Partial<DocumentPreferences>) => {
    setPreferencesState((prev) => ({ ...prev, ...patch }));
  }, []);

  const markAsRead = useCallback((documentId: string) => {
    setDocumentOverrides((prev) => ({
      ...prev,
      [documentId]: {
        ...prev[documentId],
        isRead: true,
        status: prev[documentId]?.status === 'new' ? 'viewed' : prev[documentId]?.status,
      },
    }));
  }, []);

  const archiveDocument = useCallback((documentId: string) => {
    setDocumentOverrides((prev) => ({
      ...prev,
      [documentId]: { ...prev[documentId], isArchived: true, status: 'archived' },
    }));
  }, []);

  const unarchiveDocument = useCallback((documentId: string) => {
    setDocumentOverrides((prev) => ({
      ...prev,
      [documentId]: { ...prev[documentId], isArchived: false, status: 'viewed' },
    }));
  }, []);

  const completeSignature = useCallback((signatureRequestId: string) => {
    setSignatureOverrides((prev) => ({
      ...prev,
      [signatureRequestId]: { status: 'completed' },
    }));
    const req = signatureRequests.find((s) => s.id === signatureRequestId);
    if (req) {
      setDocumentOverrides((prev) => ({
        ...prev,
        [req.documentId]: {
          ...prev[req.documentId],
          isRead: true,
          status: 'signed',
          requiresSignature: false,
        },
      }));
    }
  }, [signatureRequests]);

  const declineSignature = useCallback((signatureRequestId: string, _reason: string) => {
    void _reason;
    setSignatureOverrides((prev) => ({
      ...prev,
      [signatureRequestId]: { status: 'declined' },
    }));
  }, []);

  const toggleDocumentSelection = useCallback((id: string) => {
    setSelectedDocumentIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }, []);

  const clearSelection = useCallback(() => setSelectedDocumentIds([]), []);

  const value = useMemo<DocumentsStateContextValue>(
    () => ({
      documents,
      signatureRequests,
      summary,
      signatureSummary,
      alerts,
      sidebarBadges,
      viewMode,
      setViewMode,
      preferences,
      setPreferences,
      markAsRead,
      archiveDocument,
      unarchiveDocument,
      completeSignature,
      declineSignature,
      selectedDocumentIds,
      setSelectedDocumentIds,
      toggleDocumentSelection,
      clearSelection,
    }),
    [
      documents,
      signatureRequests,
      summary,
      signatureSummary,
      alerts,
      sidebarBadges,
      viewMode,
      setViewMode,
      preferences,
      setPreferences,
      markAsRead,
      archiveDocument,
      unarchiveDocument,
      completeSignature,
      declineSignature,
      selectedDocumentIds,
      toggleDocumentSelection,
      clearSelection,
    ],
  );

  return (
    <DocumentsStateContext.Provider value={value}>{children}</DocumentsStateContext.Provider>
  );
}

export function useDocumentsState(): DocumentsStateContextValue {
  const ctx = useContext(DocumentsStateContext);
  if (!ctx) {
    throw new Error('useDocumentsState must be used within DocumentsStateProvider');
  }
  return ctx;
}

export const DEFAULT_DOCUMENT_FILTERS: DocumentFilterState = {
  search: '',
  investmentId: 'all',
  category: 'all',
  documentType: 'all',
  status: 'all',
  fileType: 'all',
  taxYear: 'all',
  accessLevel: 'all',
  requiresSignature: 'all',
  isRead: 'all',
  isArchived: 'active',
  tags: [],
  dateFrom: '',
  dateTo: '',
};

export const DEFAULT_DOCUMENT_SORT: DocumentSortState = {
  field: 'uploadedAt',
  direction: 'desc',
};
