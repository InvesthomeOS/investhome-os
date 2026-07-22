'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import {
  archiveCompanyDocument,
  formatFileSize,
  restoreCompanyDocument,
  toggleFavorite,
  trashCompanyDocument,
  uploadCompanyDocument,
  type CompanyDocument,
  type CompanyDocumentListParams,
  type CompanyDocumentView,
  type DocumentFolder,
} from '@/lib/api/company-documents';
import { fetchCompanies } from '@/lib/api/companies';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canArchiveCompanyDocuments,
  canCreateCompanyDocuments,
  canDownloadCompanyDocuments,
  canReadCompanyDocuments,
} from '@/lib/company/company-document-permissions';
import { companyDocumentQueries, companyDocumentQueryKeys } from '@/lib/query/company-document-queries';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { CompanyDocumentDetailDrawer } from './document-detail-drawer';
import { CompanyDocumentUploadPanel } from './document-upload-panel';

type ViewMode = 'table' | 'grid';

const DEFAULT_PARAMS: CompanyDocumentListParams = {
  page: 1,
  page_size: 25,
  sort_by: 'updated_at',
  sort_dir: 'desc',
  view: 'all',
};

export function CompanyDocumentsWorkspace() {
  const t = useTranslations('company.documents');
  const { user } = useAuth();
  const queryClient = useQueryClient();

  const [companyId, setCompanyId] = useState<string>('');
  const [folderId, setFolderId] = useState<string | null>(null);
  const [view, setView] = useState<CompanyDocumentView>('all');
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [params] = useState<CompanyDocumentListParams>(DEFAULT_PARAMS);
  const [selectedDoc, setSelectedDoc] = useState<CompanyDocument | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [showUpload, setShowUpload] = useState(false);

  const companiesQuery = useQuery({
    queryKey: ['companies', 'picker'],
    queryFn: () => fetchCompanies({ page: 1, page_size: 50 }),
    enabled: canReadCompanyDocuments(user),
  });

  useEffect(() => {
    if (!companyId && companiesQuery.data?.items[0]?.id) {
      setCompanyId(companiesQuery.data.items[0].id);
    }
  }, [companiesQuery.data, companyId]);

  const listParams = useMemo(
    () => ({
      ...params,
      company_id: companyId || undefined,
      folder_id: folderId || undefined,
      search: appliedSearch || undefined,
      view,
    }),
    [params, companyId, folderId, appliedSearch, view],
  );

  const listQuery = useQuery({
    ...companyDocumentQueries.list(listParams),
    enabled: Boolean(companyId) && canReadCompanyDocuments(user),
  });

  const foldersQuery = useQuery({
    ...companyDocumentQueries.folders(companyId),
    enabled: Boolean(companyId),
  });

  const summaryQuery = useQuery({
    ...companyDocumentQueries.summary(companyId),
    enabled: Boolean(companyId),
  });

  const invalidate = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: companyDocumentQueryKeys.all });
  }, [queryClient]);

  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      const results = [];
      for (const file of files) {
        results.push(await uploadCompanyDocument(file, { company_id: companyId, folder_id: folderId ?? undefined }));
      }
      return results;
    },
    onSuccess: async () => {
      await invalidate();
      setShowUpload(false);
    },
  });

  const actionMutation = useMutation({
    mutationFn: async ({ type, id }: { type: string; id: string }) => {
      switch (type) {
        case 'archive':
          return archiveCompanyDocument(id);
        case 'restore':
          return restoreCompanyDocument(id);
        case 'trash':
          return trashCompanyDocument(id);
        case 'favorite':
          return toggleFavorite(id, true);
        case 'unfavorite':
          return toggleFavorite(id, false);
        default:
          throw new Error('Unknown action');
      }
    },
    onSuccess: invalidate,
  });

  const columns: AdminTableColumn<CompanyDocument>[] = useMemo(
    () => [
      { id: 'document_number', header: t('columns.documentNumber'), render: (row) => row.document_number, exportValue: (row) => row.document_number },
      { id: 'title', header: t('columns.title'), render: (row) => row.title, exportValue: (row) => row.title },
      { id: 'category', header: t('columns.category'), render: (row) => row.category, exportValue: (row) => row.category },
      { id: 'folder', header: t('columns.folder'), render: (row) => row.folder_name ?? '—', exportValue: (row) => row.folder_name ?? '' },
      { id: 'confidentiality', header: t('columns.confidentiality'), render: (row) => row.confidentiality_level, exportValue: (row) => row.confidentiality_level },
      { id: 'status', header: t('columns.status'), render: (row) => <StatusChip tone="default">{row.status}</StatusChip>, exportValue: (row) => row.status },
      { id: 'file_size', header: t('columns.size'), render: (row) => formatFileSize(row.file_size), exportValue: (row) => String(row.file_size ?? 0) },
      { id: 'expiration', header: t('columns.expiration'), render: (row) => row.expiration_date ?? '—', exportValue: (row) => row.expiration_date ?? '' },
      { id: 'owner', header: t('columns.owner'), render: (row) => row.owner_name ?? '—', exportValue: (row) => row.owner_name ?? '' },
      { id: 'updated', header: t('columns.updated'), render: (row) => new Date(row.updated_at).toLocaleDateString(), exportValue: (row) => row.updated_at },
    ],
    [t],
  );

  const openDocument = (doc: CompanyDocument) => {
    setSelectedDoc(doc);
    setDrawerOpen(true);
  };

  if (!canReadCompanyDocuments(user)) {
    return <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />;
  }

  if (companiesQuery.isLoading) return <LoadingState />;
  if (companiesQuery.isError) return <ErrorState title={t('loadFailed')} message={t('loadFailed')} />;

  const documents = listQuery.data?.items ?? [];
  const folders = foldersQuery.data?.items ?? [];
  const summary = summaryQuery.data;

  return (
    <div className="company-workspace">
      <header className="leads-page__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1>{t('title')}</h1>
        <p className="leads-page__subtitle">{t('subtitle')}</p>
      </header>

      {summary && (
        <section className="company-doc-metrics" aria-label={t('metrics.title')}>
          <div><strong>{summary.total_documents}</strong><span>{t('metrics.total')}</span></div>
          <div><strong>{formatFileSize(summary.total_bytes)}</strong><span>{t('metrics.storage')}</span></div>
          <div><strong>{summary.expiring_soon}</strong><span>{t('metrics.expiring')}</span></div>
          <div><strong>{summary.in_trash}</strong><span>{t('metrics.trash')}</span></div>
        </section>
      )}

      <section className="leads-page__toolbar">
        <div className="leads-page__filters">
          <label>
            <span>{t('filters.company')}</span>
            <select value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
              {(companiesQuery.data?.items ?? []).map((c) => (
                <option key={c.id} value={c.id}>{c.company_name}</option>
              ))}
            </select>
          </label>
          <label>
            <span>{t('filters.search')}</span>
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('filters.searchPlaceholder')} />
          </label>
          <Button variant="secondary" onClick={() => setAppliedSearch(search)}>{t('filters.apply')}</Button>
        </div>
        <div className="leads-page__actions">
          {canCreateCompanyDocuments(user) && (
            <Button onClick={() => setShowUpload(true)}>{t('actions.upload')}</Button>
          )}
          <Button variant={viewMode === 'table' ? 'primary' : 'secondary'} onClick={() => setViewMode('table')}>{t('views.table')}</Button>
          <Button variant={viewMode === 'grid' ? 'primary' : 'secondary'} onClick={() => setViewMode('grid')}>{t('views.grid')}</Button>
        </div>
      </section>

      <div className="company-doc-layout">
        <aside className="company-doc-folders" aria-label={t('folders.title')}>
          <button type="button" className={!folderId ? 'is-active' : ''} onClick={() => setFolderId(null)}>{t('folders.all')}</button>
          {folders.map((folder: DocumentFolder) => (
            <button
              key={folder.id}
              type="button"
              className={folderId === folder.id ? 'is-active' : ''}
              onClick={() => setFolderId(folder.id)}
            >
              {folder.name} ({folder.document_count})
            </button>
          ))}
        </aside>

        <div className="company-doc-main">
          <nav className="company-doc-views" aria-label={t('views.label')}>
            {(['all', 'recent', 'favorites', 'expiring', 'archived', 'trash'] as CompanyDocumentView[]).map((v) => (
              <button key={v} type="button" className={view === v ? 'is-active' : ''} onClick={() => setView(v)}>
                {t(`views.${v}`)}
              </button>
            ))}
          </nav>

          {listQuery.isLoading ? (
            <LoadingState />
          ) : listQuery.isError ? (
            <ErrorState title={t('loadFailed')} message={t('loadFailed')} />
          ) : documents.length === 0 ? (
            <EmptyState title={t('empty.title')} description={t('empty.description')} />
          ) : viewMode === 'table' ? (
            <AdminDataTable
              columns={columns}
              rows={documents}
              rowKey={(row) => row.id}
              onRowClick={openDocument}
              exportFileName="company-documents.csv"
              emptyMessage={t('empty.title')}
            />
          ) : (
            <div className="company-doc-grid">
              {documents.map((doc) => (
                <button key={doc.id} type="button" className="company-doc-card" onClick={() => openDocument(doc)}>
                  <strong>{doc.title}</strong>
                  <span>{doc.document_number}</span>
                  <span>{formatFileSize(doc.file_size)}</span>
                  {doc.is_favorited && <span aria-hidden>★</span>}
                </button>
              ))}
            </div>
          )}

        </div>
      </div>

      {showUpload && companyId && (
        <CompanyDocumentUploadPanel
          companyId={companyId}
          folderId={folderId}
          onClose={() => setShowUpload(false)}
          onUpload={(files) => uploadMutation.mutateAsync(files)}
          uploading={uploadMutation.isPending}
        />
      )}

      {selectedDoc && (
        <CompanyDocumentDetailDrawer
          document={selectedDoc}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          canDownload={canDownloadCompanyDocuments(user)}
          canArchive={canArchiveCompanyDocuments(user)}
          onAction={(type) => actionMutation.mutate({ type, id: selectedDoc.id })}
        />
      )}
    </div>
  );
}
