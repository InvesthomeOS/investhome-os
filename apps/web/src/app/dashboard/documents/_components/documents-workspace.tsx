'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  archiveDocument,
  fetchDocument,
  fetchDocuments,
  formatDocumentDate,
  formatFileSize,
  restoreDocument,
  type Document,
  type DocumentFilters,
} from '@/lib/api/documents';
import { useDocumentLabels } from '@/lib/i18n/document-labels';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { DocumentDetailDrawer } from './document-detail-drawer';
import { DocumentUploadPanel } from './document-upload-panel';

type ViewMode = 'table' | 'grid';

const EMPTY_FILTERS: DocumentFilters = {
  search: '',
  document_type: '',
  status: '',
  confidentiality: '',
  sort_by: 'updated_at',
  sort_dir: 'desc',
  page: 1,
  page_size: 25,
};

export function DocumentsWorkspace() {
  const t = useTranslations('documents');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getTypeLabel, getStatusLabel, getConfidentialityLabel, typeOptions, statusOptions, confidentialityOptions } =
    useDocumentLabels();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState<DocumentFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<DocumentFilters>(EMPTY_FILTERS);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [archiving, setArchiving] = useState(false);

  const canCreate = user ? hasPermission(user, 'documents', 'create') : false;
  const canArchive = user ? hasPermission(user, 'documents', 'archive') : false;
  const canDownload = user ? hasPermission(user, 'documents', 'download') : false;

  const loadDocuments = useCallback(async (nextFilters: DocumentFilters) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchDocuments(nextFilters);
      setDocuments(response.items);
      setTotal(response.total);
    } catch {
      setError(t('loadError'));
      setDocuments([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    void loadDocuments(appliedFilters);
  }, [appliedFilters, loadDocuments]);

  const handleOpenDocument = useCallback((doc: Document) => setSelectedDocument(doc), []);
  useRecordDeepLink(fetchDocument, handleOpenDocument);

  const demoCount = useMemo(() => documents.filter((doc) => doc.is_demo).length, [documents]);

  const handleApplyFilters = () => setAppliedFilters({ ...filters, page: 1 });
  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  const handleArchive = async (doc: Document) => {
    setArchiving(true);
    setActionError(null);
    try {
      if (doc.archived_at) {
        await restoreDocument(doc.id);
      } else {
        await archiveDocument(doc.id);
      }
      await loadDocuments(appliedFilters);
      setSelectedDocument(null);
    } catch {
      setActionError(t('actionError'));
    } finally {
      setArchiving(false);
    }
  };

  return (
    <div className="leads-page">
      <header className="leads-page__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1>{t('title')}</h1>
        <p className="leads-page__subtitle">{t('subtitle')}</p>
      </header>

      {demoCount > 0 && (
        <p className="leads-page__demo-banner">{t('demoBanner', { count: demoCount })}</p>
      )}

      <section className="leads-page__toolbar">
        <div className="leads-page__filters">
          <label>
            <span>{t('searchLabel')}</span>
            <input
              type="search"
              value={filters.search ?? ''}
              placeholder={t('searchPlaceholder')}
              onChange={(e) => setFilters((prev) => ({ ...prev, search: e.target.value }))}
            />
          </label>
          <label>
            <span>{t('typeLabel')}</span>
            <select
              value={filters.document_type ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, document_type: e.target.value as DocumentFilters['document_type'] }))}
            >
              <option value="">{t('allTypes')}</option>
              {typeOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('statusLabel')}</span>
            <select
              value={filters.status ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, status: e.target.value as DocumentFilters['status'] }))}
            >
              <option value="">{t('allStatuses')}</option>
              {statusOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('confidentialityLabel')}</span>
            <select
              value={filters.confidentiality ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, confidentiality: e.target.value as DocumentFilters['confidentiality'] }))}
            >
              <option value="">{t('allConfidentiality')}</option>
              {confidentialityOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <div className="leads-page__filter-actions">
            <button type="button" className="leads__button leads__button--secondary" onClick={handleApplyFilters}>
              {tCommon('apply')}
            </button>
            <button type="button" className="leads__button leads__button--ghost" onClick={handleResetFilters}>
              {tCommon('reset')}
            </button>
          </div>
        </div>
        <div className="leads-page__actions">
          <div className="documents-view-toggle" role="group" aria-label={t('viewModeLabel')}>
            <button
              type="button"
              className={`leads__button leads__button--ghost${viewMode === 'table' ? ' leads__button--active' : ''}`}
              onClick={() => setViewMode('table')}
            >
              {t('tableView')}
            </button>
            <button
              type="button"
              className={`leads__button leads__button--ghost${viewMode === 'grid' ? ' leads__button--active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              {t('gridView')}
            </button>
          </div>
          {canCreate && (
            <button type="button" className="leads__button leads__button--primary" onClick={() => setShowUpload(true)}>
              {t('uploadDocuments')}
            </button>
          )}
        </div>
      </section>

      {actionError && <p className="leads-page__error">{actionError}</p>}
      {error && (
        <div className="leads-page__error">
          <p>{error}</p>
          <button type="button" className="leads__button leads__button--secondary" onClick={() => void loadDocuments(appliedFilters)}>
            {tCommon('retry')}
          </button>
        </div>
      )}

      {loading ? (
        <p className="leads-page__loading">{tCommon('loading')}</p>
      ) : documents.length === 0 ? (
        <div className="documents-empty">
          <h2>{t('emptyTitle')}</h2>
          <p>{t('emptyDescription')}</p>
        </div>
      ) : viewMode === 'table' ? (
        <div className="leads-table-wrap">
          <table className="leads-table documents-table">
            <thead>
              <tr>
                <th>{t('columns.document')}</th>
                <th>{t('columns.type')}</th>
                <th>{t('columns.relatedRecord')}</th>
                <th>{t('columns.version')}</th>
                <th>{t('columns.status')}</th>
                <th>{t('columns.confidentiality')}</th>
                <th>{t('columns.uploadedBy')}</th>
                <th>{t('columns.documentDate')}</th>
                <th>{t('columns.updatedDate')}</th>
                <th>{t('columns.fileSize')}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} onClick={() => setSelectedDocument(doc)} className="leads-table__row--clickable">
                  <td>
                    <strong>{doc.title}</strong>
                    <span className="documents-table__filename">{doc.original_file_name}</span>
                    {doc.is_demo && <span className="leads__demo-tag">{tCommon('demo')}</span>}
                  </td>
                  <td>{getTypeLabel(doc.document_type)}</td>
                  <td>{doc.related_record_label ?? tCommon('noValue')}</td>
                  <td>v{doc.version_number}</td>
                  <td>{getStatusLabel(doc.status)}</td>
                  <td>{getConfidentialityLabel(doc.confidentiality_level)}</td>
                  <td>{doc.uploaded_by_name ?? tCommon('noValue')}</td>
                  <td>{formatDocumentDate(doc.document_date, locale)}</td>
                  <td>{formatDocumentDate(doc.updated_at, locale)}</td>
                  <td>{formatFileSize(doc.file_size, locale)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="documents-grid">
          {documents.map((doc) => (
            <button key={doc.id} type="button" className="documents-grid__card" onClick={() => setSelectedDocument(doc)}>
              <span className="documents-grid__ext">{doc.file_extension.toUpperCase()}</span>
              <strong>{doc.title}</strong>
              <span>{getTypeLabel(doc.document_type)}</span>
              <span>{formatFileSize(doc.file_size, locale)}</span>
            </button>
          ))}
        </div>
      )}

      {!loading && total > 0 && (
        <p className="documents-summary">{t('summary', { shown: documents.length, total })}</p>
      )}

      {showUpload && (
        <DocumentUploadPanel
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            setShowUpload(false);
            void loadDocuments(appliedFilters);
          }}
        />
      )}

      <DocumentDetailDrawer
        document={selectedDocument}
        archiving={archiving}
        canArchive={canArchive}
        canDownload={canDownload}
        onClose={() => setSelectedDocument(null)}
        onArchive={handleArchive}
        onRefresh={() => void loadDocuments(appliedFilters)}
      />
    </div>
  );
}
