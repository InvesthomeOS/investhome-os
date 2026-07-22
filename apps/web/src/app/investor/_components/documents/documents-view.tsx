'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  createMockDownloadBlob,
  filterDocuments,
  sortDocuments,
} from '../../_data/document-calculations';
import type { DocumentFilterState, DocumentSortState, InvestorDocument } from '../../_data/document-types';
import type { LibraryViewMode } from '../../_data/document-types';
import { LoadingSkeletonGrid } from '../loading-skeleton';
import { EmptyState } from '../empty-state';
import {
  DEFAULT_DOCUMENT_FILTERS,
  DEFAULT_DOCUMENT_SORT,
  useDocumentsState,
} from '../../_state/documents-state';
import { DemonstrationBanner } from './demonstration-banner';
import { DocumentAlertsSection } from './document-alerts-section';
import { DocumentFilters } from './document-filters';
import { DocumentFolderView } from './document-folder';
import { DocumentGrid } from './document-grid';
import { DocumentPreview } from './document-preview';
import { DocumentPreferencesDrawer } from './document-preferences-drawer';
import { DocumentTable } from './document-table';
import { DocumentsHeader, DocumentsKpiRow } from './documents-header';
import { MissingDocumentsSection } from './missing-documents-section';

export function DocumentsView() {
  const {
    documents,
    summary,
    alerts,
    viewMode,
    setViewMode,
    preferences,
    setPreferences,
    markAsRead,
    selectedDocumentIds,
    setSelectedDocumentIds,
    toggleDocumentSelection,
    clearSelection,
  } = useDocumentsState();

  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [filters, setFilters] = useState<DocumentFilterState>(DEFAULT_DOCUMENT_FILTERS);
  const [sort, setSort] = useState<DocumentSortState>(DEFAULT_DOCUMENT_SORT);
  const [previewDoc, setPreviewDoc] = useState<InvestorDocument | null>(null);
  const [prefsOpen, setPrefsOpen] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 400);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const filtered = useMemo(
    () => sortDocuments(filterDocuments(documents, filters), sort),
    [documents, filters, sort],
  );

  const showToast = useCallback((message: string) => setToastMessage(message), []);

  const handleDownload = useCallback(
    (doc: InvestorDocument) => {
      const blob = createMockDownloadBlob(doc);
      const url = URL.createObjectURL(blob);
      const a = window.document.createElement('a');
      a.href = url;
      a.download = `${doc.fileName.replace(/\.[^.]+$/, '')}-demo.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(`Download started: ${doc.fileName} (demo placeholder)`);
      markAsRead(doc.id);
    },
    [showToast, markAsRead],
  );

  const handleBulkDownload = useCallback(() => {
    if (selectedDocumentIds.length === 0) {
      showToast('Select documents to download');
      return;
    }
    showToast(`Bulk download queued for ${selectedDocumentIds.length} document(s) — demo placeholder`);
    clearSelection();
  }, [selectedDocumentIds, showToast, clearSelection]);

  const updateFilters = useCallback((patch: Partial<DocumentFilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  if (isLoading) {
    return (
      <div className="investor-page">
        <LoadingSkeletonGrid count={8} />
      </div>
    );
  }

  return (
    <div className="investor-page inv-docs">
      <DemonstrationBanner />
      <DocumentsHeader onOpenPreferences={() => setPrefsOpen(true)} />
      <DocumentsKpiRow summary={summary} />
      <DocumentAlertsSection alerts={alerts} />

      <section className="inv-docs__library" aria-labelledby="library-heading">
        <div className="inv-docs__library-toolbar">
          <h2 id="library-heading">Document Library</h2>
          <div className="inv-docs__view-toggle" role="tablist" aria-label="View mode">
            {(['table', 'grid', 'folder'] as LibraryViewMode[]).map((mode) => (
              <button
                key={mode}
                type="button"
                role="tab"
                aria-selected={viewMode === mode}
                className={viewMode === mode ? 'inv-docs__view-btn--active' : undefined}
                onClick={() => setViewMode(mode)}
              >
                {mode.charAt(0).toUpperCase() + mode.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <DocumentFilters
          filters={filters}
          documents={documents}
          onChange={updateFilters}
          onReset={() => setFilters(DEFAULT_DOCUMENT_FILTERS)}
        />

        <div className="inv-docs__sort-bar">
          <label>
            Sort by
            <select
              value={sort.field}
              onChange={(e) =>
                setSort((prev) => ({
                  ...prev,
                  field: e.target.value as DocumentSortState['field'],
                }))
              }
            >
              <option value="uploadedAt">Upload Date</option>
              <option value="title">Title</option>
              <option value="investmentName">Investment</option>
              <option value="category">Category</option>
              <option value="status">Status</option>
              <option value="fileSizeBytes">Size</option>
            </select>
          </label>
          <button
            type="button"
            onClick={() =>
              setSort((prev) => ({
                ...prev,
                direction: prev.direction === 'asc' ? 'desc' : 'asc',
              }))
            }
            aria-label={`Sort ${sort.direction === 'asc' ? 'descending' : 'ascending'}`}
          >
            {sort.direction === 'asc' ? '↑' : '↓'}
          </button>
          {selectedDocumentIds.length > 0 ? (
            <button type="button" className="inv-docs__btn inv-docs__btn--secondary" onClick={handleBulkDownload}>
              Download Selected ({selectedDocumentIds.length})
            </button>
          ) : null}
          <span className="inv-docs__result-count">{filtered.length} documents</span>
        </div>

        {filtered.length === 0 ? (
          <EmptyState
            icon="📄"
            title="No documents match your filters"
            description="Try adjusting your search or filter criteria."
            actionLabel="Reset Filters"
            onAction={() => setFilters(DEFAULT_DOCUMENT_FILTERS)}
          />
        ) : viewMode === 'table' ? (
          <DocumentTable
            documents={filtered}
            selectedIds={selectedDocumentIds}
            onToggleSelect={toggleDocumentSelection}
            onSelectAll={setSelectedDocumentIds}
            onPreview={setPreviewDoc}
            onDownload={handleDownload}
          />
        ) : viewMode === 'grid' ? (
          <DocumentGrid
            documents={filtered}
            selectedIds={selectedDocumentIds}
            onToggleSelect={toggleDocumentSelection}
            onPreview={setPreviewDoc}
            onDownload={handleDownload}
          />
        ) : (
          <DocumentFolderView
            documents={filtered}
            selectedIds={selectedDocumentIds}
            onToggleSelect={toggleDocumentSelection}
            onPreview={setPreviewDoc}
            onDownload={handleDownload}
          />
        )}
      </section>

      <MissingDocumentsSection />

      <DocumentPreview
        document={previewDoc}
        open={previewDoc !== null}
        onClose={() => setPreviewDoc(null)}
        onDownload={handleDownload}
        onMarkRead={markAsRead}
      />

      <DocumentPreferencesDrawer
        open={prefsOpen}
        preferences={preferences}
        onClose={() => setPrefsOpen(false)}
        onChange={setPreferences}
      />

      {toastMessage ? (
        <div className="inv-investments__toast" role="status" aria-live="polite">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
