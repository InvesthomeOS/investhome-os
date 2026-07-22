'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';
import { ApiError } from '@/lib/api/client';
import { documentPreviewUrl, uploadDocuments } from '@/lib/api/documents';
import { useAuth } from '@/lib/auth/auth-context';
import { canManageAssets, hasMarketingPermission } from '@/lib/marketing/marketing-permissions';
import {
  assetExportUrl,
  createAssetFromDocument,
  fetchAssetFolders,
  fetchAssetSummary,
  fetchAssets,
  type AssetSummary,
} from '@/workspaces/marketing/api/assets';

import { SummaryWidget } from '../../_components/summary-widget';

const ASSET_TYPES = [
  'image',
  'video',
  'logo',
  'brochure',
  'pdf',
  'social_post',
  'blog',
  'email_template',
  'presentation',
  'document',
  'other',
] as const;

function statusTone(status: string): 'default' | 'success' | 'warning' | 'danger' {
  if (status === 'ready' || status === 'active') return 'success';
  if (status === 'draft') return 'warning';
  if (status === 'archived') return 'danger';
  return 'default';
}

function metricWidgetState(state: string): 'loading' | 'empty' | 'ready' | 'no_data' {
  if (state === 'empty') return 'empty';
  if (state === 'ready') return 'ready';
  return 'no_data';
}

export function AssetsWorkspace() {
  const t = useTranslations('marketing.assets');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canEdit = canManageAssets(user);
  const canExport = hasMarketingPermission(user, 'export') || canEdit;
  const canView = canEdit || hasMarketingPermission(user, 'view');

  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [folder, setFolder] = useState('');
  const [assetType, setAssetType] = useState('');
  const [status, setStatus] = useState('');
  const [tag, setTag] = useState('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [uploadName, setUploadName] = useState('');
  const [uploadType, setUploadType] = useState<string>('image');
  const [uploadFolder, setUploadFolder] = useState('documents');
  const [uploadTags, setUploadTags] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const listParams = {
    page,
    search: search || undefined,
    folder: folder || undefined,
    assetType: assetType || undefined,
    status: status || undefined,
    tag: tag || undefined,
  };

  const summaryQuery = useQuery({
    queryKey: ['marketing', 'assets', 'summary'],
    queryFn: fetchAssetSummary,
    enabled: canView,
  });
  const foldersQuery = useQuery({
    queryKey: ['marketing', 'assets', 'folders'],
    queryFn: fetchAssetFolders,
    enabled: canView,
  });
  const listQuery = useQuery({
    queryKey: ['marketing', 'assets', 'list', listParams],
    queryFn: () => fetchAssets(listParams),
    enabled: canView,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadFile) throw new Error(t('upload.fileRequired'));
      const results = await uploadDocuments([uploadFile], {
        title: uploadName || uploadFile.name,
        document_type: 'marketing_material',
        tags: uploadTags || undefined,
        description: t('upload.documentDescription'),
      });
      const documentId = results[0]?.document?.id;
      if (!documentId) throw new Error(t('upload.failed'));
      return createAssetFromDocument({
        document_id: documentId,
        title: uploadName || uploadFile.name,
        asset_type: uploadType,
        folder: uploadFolder || undefined,
        tags: uploadTags
          ? uploadTags
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean)
          : undefined,
        status: 'draft',
      });
    },
    onSuccess: async () => {
      setUploadOpen(false);
      setUploadFile(null);
      setUploadName('');
      setUploadTags('');
      setUploadError(null);
      await queryClient.invalidateQueries({ queryKey: ['marketing', 'assets'] });
    },
    onError: (error) => {
      setUploadError(error instanceof Error ? error.message : t('upload.failed'));
    },
  });

  const columns: AdminTableColumn<AssetSummary>[] = useMemo(
    () => [
      {
        id: 'title',
        header: t('columns.title'),
        exportValue: (row) => row.title || row.name,
        render: (row) => (
          <Link href={`/workspaces/marketing/assets/${row.id}` as Route} className="marketing-link">
            {row.title || row.name}
          </Link>
        ),
      },
      {
        id: 'asset_type',
        header: t('columns.type'),
        exportValue: (row) => row.asset_type,
        render: (row) => t(`types.${row.asset_type}` as 'types.image'),
      },
      {
        id: 'status',
        header: t('columns.status'),
        exportValue: (row) => row.status,
        render: (row) => (
          <StatusChip tone={statusTone(row.status)}>{t(`status.${row.status}` as 'status.draft')}</StatusChip>
        ),
      },
      {
        id: 'folder',
        header: t('columns.folder'),
        exportValue: (row) => row.folder ?? '',
        render: (row) => (row.folder ? t(`folders.${row.folder}` as 'folders.documents') : t('notSet')),
      },
      {
        id: 'tags',
        header: t('columns.tags'),
        exportValue: (row) => (row.tags ?? []).join('|'),
        render: (row) => ((row.tags ?? []).length ? (row.tags ?? []).join(', ') : t('notSet')),
      },
      {
        id: 'campaign',
        header: t('columns.campaign'),
        exportValue: (row) => row.campaign_name ?? row.campaign_id ?? '',
        render: (row) => row.campaign_name ?? t('notSet'),
      },
      {
        id: 'project',
        header: t('columns.project'),
        exportValue: (row) => row.project_name ?? row.project_id ?? '',
        render: (row) => row.project_name ?? t('notSet'),
      },
      {
        id: 'updated_at',
        header: t('columns.updated'),
        exportValue: (row) => row.updated_at,
        render: (row) => new Date(row.updated_at).toLocaleDateString(),
      },
    ],
    [t],
  );

  if (!canView) {
    return (
      <main className="dashboard marketing-module-shell">
        <EmptyState title={t('accessDenied')} description={t('accessDeniedDescription')} />
      </main>
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header marketing-assets__header">
        <div>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        <div className="marketing-assets__actions">
          {canExport && (
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                void fetch(assetExportUrl(listParams), { credentials: 'include' })
                  .then((response) => {
                    if (!response.ok) throw new Error(t('exportFailed'));
                    return response.blob();
                  })
                  .then((blob) => {
                    const url = URL.createObjectURL(blob);
                    const anchor = document.createElement('a');
                    anchor.href = url;
                    anchor.download = 'marketing-assets.csv';
                    anchor.click();
                    URL.revokeObjectURL(url);
                  })
                  .catch(() => undefined);
              }}
            >
              {t('exportCsv')}
            </Button>
          )}
          {canEdit && (
            <Button type="button" onClick={() => setUploadOpen(true)}>
              {t('upload.cta')}
            </Button>
          )}
        </div>
      </header>

      <section className="marketing-assets__widgets" aria-label={t('summary.label')}>
        {(summaryQuery.data?.metrics ?? []).map((metric) => (
          <SummaryWidget
            key={metric.key}
            title={t(`summary.${metric.key}` as 'summary.total_assets')}
            state={summaryQuery.isLoading ? 'loading' : metricWidgetState(metric.state)}
            value={metric.value ?? 0}
          />
        ))}
        {summaryQuery.isLoading && !summaryQuery.data && (
          <>
            <SummaryWidget title={t('summary.total_assets')} state="loading" />
            <SummaryWidget title={t('summary.ready_assets')} state="loading" />
          </>
        )}
      </section>

      <section className="marketing-assets__toolbar">
        <input
          className="marketing-assets__search"
          value={search}
          onChange={(event) => {
            setPage(1);
            setSearch(event.target.value);
          }}
          placeholder={t('searchPlaceholder')}
          aria-label={t('searchPlaceholder')}
        />
        <select
          className="marketing-assets__filter"
          value={folder}
          onChange={(event) => {
            setPage(1);
            setFolder(event.target.value);
          }}
          aria-label={t('filters.folder')}
        >
          <option value="">{t('filters.allFolders')}</option>
          {(foldersQuery.data?.items ?? []).map((item) => (
            <option key={item} value={item}>
              {t(`folders.${item}` as 'folders.documents')}
            </option>
          ))}
        </select>
        <select
          className="marketing-assets__filter"
          value={assetType}
          onChange={(event) => {
            setPage(1);
            setAssetType(event.target.value);
          }}
          aria-label={t('filters.type')}
        >
          <option value="">{t('filters.allTypes')}</option>
          {ASSET_TYPES.map((type) => (
            <option key={type} value={type}>
              {t(`types.${type}`)}
            </option>
          ))}
        </select>
        <select
          className="marketing-assets__filter"
          value={status}
          onChange={(event) => {
            setPage(1);
            setStatus(event.target.value);
          }}
          aria-label={t('filters.status')}
        >
          <option value="">{t('filters.allStatuses')}</option>
          <option value="draft">{t('status.draft')}</option>
          <option value="ready">{t('status.ready')}</option>
          <option value="archived">{t('status.archived')}</option>
        </select>
        <input
          className="marketing-assets__filter"
          value={tag}
          onChange={(event) => {
            setPage(1);
            setTag(event.target.value);
          }}
          placeholder={t('filters.tag')}
          aria-label={t('filters.tag')}
        />
        <div className="marketing-assets__view-modes" role="group" aria-label={t('viewMode')}>
          {(['grid', 'list'] as const).map((mode) => (
            <button
              key={mode}
              type="button"
              className={
                viewMode === mode
                  ? 'marketing-assets__view-btn marketing-assets__view-btn--active'
                  : 'marketing-assets__view-btn'
              }
              onClick={() => setViewMode(mode)}
            >
              {t(`viewModes.${mode}`)}
            </button>
          ))}
        </div>
      </section>

      {listQuery.isLoading ? (
        <LoadingState label={t('loading')} />
      ) : listQuery.isError ? (
        <ErrorState
          title={t('loadFailed')}
          message={listQuery.error instanceof ApiError ? listQuery.error.message : t('loadFailed')}
        />
      ) : listQuery.data?.total === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : viewMode === 'grid' ? (
        <div className="marketing-assets__grid">
          {listQuery.data?.items.map((asset) => {
            const previewId = asset.thumbnail_document_id || asset.document_id;
            return (
              <Link
                key={asset.id}
                href={`/workspaces/marketing/assets/${asset.id}` as Route}
                className="marketing-assets__card"
              >
                <div
                  className="marketing-assets__preview"
                  style={
                    previewId
                      ? { backgroundImage: `url(${documentPreviewUrl(previewId)})` }
                      : undefined
                  }
                >
                  {!previewId && (
                    <span className="marketing-assets__preview-fallback">
                      {t(`types.${asset.asset_type}` as 'types.other')}
                    </span>
                  )}
                </div>
                <h3>{asset.title || asset.name}</h3>
                <p className="marketing-assets__meta">
                  {t(`types.${asset.asset_type}` as 'types.image')}
                  {asset.folder ? ` · ${t(`folders.${asset.folder}` as 'folders.documents')}` : ''}
                </p>
                <StatusChip tone={statusTone(asset.status)}>{t(`status.${asset.status}` as 'status.draft')}</StatusChip>
                {(asset.tags ?? []).length > 0 && (
                  <p className="marketing-assets__tags">{(asset.tags ?? []).join(', ')}</p>
                )}
              </Link>
            );
          })}
        </div>
      ) : (
        <AdminDataTable
          columns={columns}
          rows={listQuery.data?.items ?? []}
          rowKey={(row) => row.id}
          exportFileName="marketing-assets.csv"
        />
      )}

      {(listQuery.data?.pages ?? 0) > 1 && (
        <div className="marketing-assets__pagination">
          <Button type="button" variant="secondary" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>
            {t('pagination.previous')}
          </Button>
          <span>
            {page} / {listQuery.data?.pages}
          </span>
          <Button
            type="button"
            variant="secondary"
            disabled={page >= (listQuery.data?.pages ?? 1)}
            onClick={() => setPage((value) => value + 1)}
          >
            {t('pagination.next')}
          </Button>
        </div>
      )}

      {uploadOpen && canEdit && (
        <div className="marketing-assets__modal" role="dialog" aria-modal="true" aria-labelledby="asset-upload-title">
          <div className="marketing-assets__modal-card">
            <h2 id="asset-upload-title">{t('upload.title')}</h2>
            <p>{t('upload.subtitle')}</p>
            <label className="marketing-assets__field">
              <span>{t('upload.file')}</span>
              <input
                type="file"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
              />
            </label>
            <label className="marketing-assets__field">
              <span>{t('columns.title')}</span>
              <input value={uploadName} onChange={(event) => setUploadName(event.target.value)} />
            </label>
            <label className="marketing-assets__field">
              <span>{t('columns.type')}</span>
              <select value={uploadType} onChange={(event) => setUploadType(event.target.value)}>
                {ASSET_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`types.${type}`)}
                  </option>
                ))}
              </select>
            </label>
            <label className="marketing-assets__field">
              <span>{t('columns.folder')}</span>
              <select value={uploadFolder} onChange={(event) => setUploadFolder(event.target.value)}>
                {(foldersQuery.data?.items ?? ['documents']).map((item) => (
                  <option key={item} value={item}>
                    {t(`folders.${item}` as 'folders.documents')}
                  </option>
                ))}
              </select>
            </label>
            <label className="marketing-assets__field">
              <span>{t('columns.tags')}</span>
              <input
                value={uploadTags}
                onChange={(event) => setUploadTags(event.target.value)}
                placeholder={t('upload.tagsPlaceholder')}
              />
            </label>
            {uploadError && <p className="marketing-assets__error">{uploadError}</p>}
            <div className="marketing-assets__modal-actions">
              <Button type="button" variant="secondary" onClick={() => setUploadOpen(false)}>
                {tCommon('cancel')}
              </Button>
              <Button type="button" onClick={() => uploadMutation.mutate()} disabled={uploadMutation.isPending || !uploadFile}>
                {uploadMutation.isPending ? t('upload.uploading') : t('upload.submit')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
