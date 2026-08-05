'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import {
  DOCUMENT_RELATED_MODULES,
  downloadCsvFile,
  exportDocumentsMetadata,
  fetchDocument,
  fetchDocuments,
  fetchDocumentsOverview,
  formatDocumentDate,
  formatFileSize,
  type Document,
  type DocumentFilters,
  type DocumentRelatedModule,
  type DocumentWorkspaceOverview,
} from '@/lib/api/documents';
import { useDocumentLabels } from '@/lib/i18n/document-labels';
import { useRecordDeepLink } from '@/lib/hooks/use-record-deep-link';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { EmptyState, LoadingState } from '@investhome/ui';

import { DocumentUploadPanel } from './document-upload-panel';

type ViewMode = 'table' | 'grid';

const EMPTY_FILTERS: DocumentFilters = {
  search: '',
  document_type: '',
  file_kind: '',
  folder: '',
  tags: '',
  visibility: '',
  status: '',
  confidentiality: '',
  owner_user_id: '',
  related_module: '',
  created_from: '',
  created_to: '',
  without_relation: false,
  include_archived: false,
  sort_by: 'updated_at',
  sort_dir: 'desc',
  page: 1,
  page_size: 25,
};

function metricDisplay(metric: DocumentWorkspaceOverview['total']): string {
  if (!metric.available) return '—';
  if (metric.value == null) return '—';
  return String(metric.value);
}

function formatStorageBytes(value: number | null | undefined, locale: string): string {
  if (value == null) return '—';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(value / (1024 * 1024 * 1024)) + ' GB';
}

export function DocumentsWorkspace() {
  const t = useTranslations('documents');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const { user } = useAuth();
  const {
    getTypeLabel,
    getFileKindLabel,
    getFolderLabel,
    getStatusLabel,
    getConfidentialityLabel,
    getVisibilityLabel,
    typeOptions,
    fileKindOptions,
    folderOptions,
    visibilityOptions,
    statusOptions,
    confidentialityOptions,
  } = useDocumentLabels();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [total, setTotal] = useState(0);
  const [overview, setOverview] = useState<DocumentWorkspaceOverview | null>(null);
  const [filters, setFilters] = useState<DocumentFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<DocumentFilters>(EMPTY_FILTERS);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const canView = user ? hasPermission(user, 'documents', 'view') : false;
  const canCreate = user ? hasPermission(user, 'documents', 'create') : false;
  const canExport = user ? hasPermission(user, 'documents', 'export') : false;

  const loadDocuments = useCallback(async (nextFilters: DocumentFilters) => {
    if (!canView) {
      setPermissionDenied(true);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    setPermissionDenied(false);
    try {
      const [response, overviewResponse] = await Promise.all([
        fetchDocuments(nextFilters),
        fetchDocumentsOverview().catch(() => null),
      ]);
      setDocuments(response.items);
      setTotal(response.total);
      setOverview(overviewResponse);
    } catch (err) {
      if (err instanceof Error && err.message === 'permission_denied') {
        setPermissionDenied(true);
      } else {
        setError(t('loadError'));
      }
      setDocuments([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [canView, t]);

  useEffect(() => {
    void loadDocuments(appliedFilters);
  }, [appliedFilters, loadDocuments]);

  const handleOpenDocument = useCallback(
    (doc: Document) => {
      router.push(`/dashboard/documents/${doc.id}`);
    },
    [router],
  );
  useRecordDeepLink(fetchDocument, handleOpenDocument);

  const demoCount = useMemo(() => documents.filter((doc) => doc.is_demo).length, [documents]);

  const handleApplyFilters = () => setAppliedFilters({ ...filters, page: 1 });
  const handleResetFilters = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  const handleExport = async () => {
    setExporting(true);
    setActionError(null);
    try {
      const payload = await exportDocumentsMetadata(appliedFilters);
      downloadCsvFile(payload.filename, payload.csv);
    } catch {
      setActionError(t('exportError'));
    } finally {
      setExporting(false);
    }
  };

  if (!canView || permissionDenied) {
    return (
      <div className="leads-page">
        <header className="leads-page__header">
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1>{t('title')}</h1>
        </header>
        <div className="documents-empty">
          <h2>{t('permissionDenied')}</h2>
          <p>{t('permissionDeniedHint')}</p>
        </div>
      </div>
    );
  }

  const typeBreakdown = overview?.documents_by_type?.length
    ? overview.documents_by_type
    : overview?.most_used_types ?? [];

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

      {overview && (
        <section className="documents-overview" aria-label={t('overview.title')}>
          <article className="documents-overview__card">
            <span>{t('overview.total')}</span>
            <strong>{metricDisplay(overview.total)}</strong>
          </article>
          <article className="documents-overview__card">
            <span>{t('overview.storageUsed')}</span>
            <strong>
              {overview.storage_used_bytes?.available
                ? formatStorageBytes(overview.storage_used_bytes.value, locale)
                : '—'}
            </strong>
          </article>
          <article className="documents-overview__card">
            <span>{t('overview.recentUploads')}</span>
            <strong>{metricDisplay(overview.recent_uploads)}</strong>
          </article>
          <article className="documents-overview__card">
            <span>{t('overview.mostViewed')}</span>
            <strong>
              {overview.most_viewed?.available
                ? metricDisplay(overview.most_viewed)
                : '—'}
            </strong>
            {!overview.most_viewed?.available && (
              <span className="documents-overview__hint">{t('overview.mostViewedUnavailable')}</span>
            )}
          </article>
          <article className="documents-overview__card">
            <span>{t('overview.archived')}</span>
            <strong>{metricDisplay(overview.archived)}</strong>
          </article>
          <article className="documents-overview__card documents-overview__card--wide">
            <span>{t('overview.mostUsedTypes')}</span>
            <strong>
              {typeBreakdown.length === 0
                ? t('overview.emptyList')
                : typeBreakdown
                    .slice(0, 6)
                    .map((item) => `${getFileKindLabel(item.file_kind)} (${item.count})`)
                    .join(' · ')}
            </strong>
          </article>
          <article className="documents-overview__card documents-overview__card--wide">
            <span>{t('overview.largestFiles')}</span>
            <strong>
              {(overview.largest_files ?? []).length === 0
                ? t('overview.emptyList')
                : overview.largest_files
                    .slice(0, 3)
                    .map((item) => `${item.title} (${formatFileSize(item.file_size)})`)
                    .join(' · ')}
            </strong>
          </article>
          <article className="documents-overview__card documents-overview__card--wide">
            <span>{t('overview.mostViewedFiles')}</span>
            <strong>
              {(overview.most_viewed_files ?? []).length === 0
                ? t('overview.emptyList')
                : overview.most_viewed_files
                    .slice(0, 3)
                    .map(
                      (item) =>
                        `${item.title} (${item.preview_count + item.download_count})`,
                    )
                    .join(' · ')}
            </strong>
          </article>
        </section>
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
            <span>{t('folderLabel')}</span>
            <select
              value={filters.folder ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, folder: e.target.value as DocumentFilters['folder'] }))}
            >
              <option value="">{t('allFolders')}</option>
              {folderOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('fileKindLabel')}</span>
            <select
              value={filters.file_kind ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, file_kind: e.target.value as DocumentFilters['file_kind'] }))}
            >
              <option value="">{t('allFileKinds')}</option>
              {fileKindOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
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
            <span>{t('relatedModuleLabel')}</span>
            <select
              value={filters.related_module ?? ''}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  related_module: e.target.value as DocumentRelatedModule | '',
                }))
              }
            >
              <option value="">{t('allRelatedModules')}</option>
              {DOCUMENT_RELATED_MODULES.map((moduleKey) => (
                <option key={moduleKey} value={moduleKey}>
                  {t(`relatedModules.${moduleKey}`)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('ownerLabel')}</span>
            <input
              type="search"
              value={filters.owner_user_id ?? ''}
              placeholder={t('ownerPlaceholder')}
              onChange={(e) => setFilters((prev) => ({ ...prev, owner_user_id: e.target.value }))}
            />
          </label>
          <label>
            <span>{t('dateFromLabel')}</span>
            <input
              type="date"
              value={filters.created_from ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, created_from: e.target.value }))}
            />
          </label>
          <label>
            <span>{t('dateToLabel')}</span>
            <input
              type="date"
              value={filters.created_to ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, created_to: e.target.value }))}
            />
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
            <span>{t('visibilityLabel')}</span>
            <select
              value={filters.visibility ?? ''}
              onChange={(e) => setFilters((prev) => ({ ...prev, visibility: e.target.value as DocumentFilters['visibility'] }))}
            >
              <option value="">{t('allVisibility')}</option>
              {visibilityOptions.map((opt) => (
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
          <label>
            <span>{t('tagsLabel')}</span>
            <input
              type="search"
              value={filters.tags ?? ''}
              placeholder={t('tagsPlaceholder')}
              onChange={(e) => setFilters((prev) => ({ ...prev, tags: e.target.value }))}
            />
          </label>
          <label className="documents-filter-checkbox">
            <input
              type="checkbox"
              checked={Boolean(filters.without_relation)}
              onChange={(e) => setFilters((prev) => ({ ...prev, without_relation: e.target.checked }))}
            />
            <span>{t('withoutRelationLabel')}</span>
          </label>
          <label className="documents-filter-checkbox">
            <input
              type="checkbox"
              checked={Boolean(filters.include_archived)}
              onChange={(e) => setFilters((prev) => ({ ...prev, include_archived: e.target.checked }))}
            />
            <span>{t('includeArchivedLabel')}</span>
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
          {canExport && (
            <button
              type="button"
              className="leads__button leads__button--secondary"
              disabled={exporting}
              onClick={() => void handleExport()}
            >
              {exporting ? t('exporting') : t('exportMetadata')}
            </button>
          )}
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
        <LoadingState label={tCommon('loading')} lines={6} />
      ) : documents.length === 0 ? (
        <EmptyState
          title={t('emptyTitle')}
          description={t('emptyDescription')}
          className="documents-empty"
          action={
            canCreate ? (
              <button type="button" className="leads__button leads__button--primary" onClick={() => setShowUpload(true)}>
                {t('uploadDocuments')}
              </button>
            ) : undefined
          }
        />
      ) : viewMode === 'table' ? (
        <div className="leads-table-wrap">
          <table className="leads-table documents-table">
            <thead>
              <tr>
                <th>{t('columns.document')}</th>
                <th>{t('columns.folder')}</th>
                <th>{t('columns.fileKind')}</th>
                <th>{t('columns.type')}</th>
                <th>{t('columns.relatedRecord')}</th>
                <th>{t('columns.status')}</th>
                <th>{t('columns.visibility')}</th>
                <th>{t('columns.owner')}</th>
                <th>{t('columns.updatedDate')}</th>
                <th>{t('columns.fileSize')}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  onClick={() => handleOpenDocument(doc)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault();
                      handleOpenDocument(doc);
                    }
                  }}
                  tabIndex={0}
                  className="leads-table__row--clickable"
                >
                  <td>
                    <strong>{doc.title}</strong>
                    <span className="documents-table__filename">{doc.original_file_name}</span>
                    {doc.is_demo && <span className="leads__demo-tag">{tCommon('demo')}</span>}
                  </td>
                  <td>{getFolderLabel(doc.folder)}</td>
                  <td>{getFileKindLabel(doc.file_kind)}</td>
                  <td>{getTypeLabel(doc.document_type)}</td>
                  <td>{doc.related_record_label ?? tCommon('noValue')}</td>
                  <td>{getStatusLabel(doc.status)}</td>
                  <td>{getVisibilityLabel(doc.visibility)}</td>
                  <td>{doc.owner_name ?? doc.uploaded_by_name ?? tCommon('noValue')}</td>
                  <td>{formatDocumentDate(doc.updated_at, locale)}</td>
                  <td>{formatFileSize(doc.file_size)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="documents-grid">
          {documents.map((doc) => (
            <Link key={doc.id} href={`/dashboard/documents/${doc.id}`} className="documents-grid__card">
              <span className="documents-grid__ext">{doc.file_extension.toUpperCase()}</span>
              <strong>{doc.title}</strong>
              <span>{getFolderLabel(doc.folder)}</span>
              <span>{getFileKindLabel(doc.file_kind)}</span>
              <span>{formatFileSize(doc.file_size)}</span>
              <span>{getConfidentialityLabel(doc.confidentiality_level)}</span>
            </Link>
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
    </div>
  );
}
