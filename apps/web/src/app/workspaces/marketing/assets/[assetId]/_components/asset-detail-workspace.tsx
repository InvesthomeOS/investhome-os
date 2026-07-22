'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ApiError } from '@/lib/api/client';
import { documentDownloadUrl, documentPreviewUrl } from '@/lib/api/documents';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canManageAssets,
  canViewMarketingAI,
  hasMarketingPermission,
} from '@/lib/marketing/marketing-permissions';
import {
  archiveAsset,
  fetchAsset,
  fetchAssetRightsReadiness,
  restoreAsset,
  updateAsset,
} from '@/workspaces/marketing/api/assets';

function statusTone(status: string): 'default' | 'success' | 'warning' | 'danger' {
  if (status === 'ready' || status === 'active') return 'success';
  if (status === 'draft') return 'warning';
  if (status === 'archived') return 'danger';
  return 'default';
}

export function AssetDetailWorkspace() {
  const params = useParams<{ assetId: string }>();
  const assetId = params.assetId;
  const t = useTranslations('marketing.assets');
  const tAi = useTranslations('marketing.ai.assistant');
  const tCommon = useTranslations('common');
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canEdit = canManageAssets(user);
  const canView = canEdit || hasMarketingPermission(user, 'view');

  const detailQuery = useQuery({
    queryKey: ['marketing', 'assets', 'detail', assetId],
    queryFn: () => fetchAsset(assetId, true),
    enabled: canView && Boolean(assetId),
  });
  const readinessQuery = useQuery({
    queryKey: ['marketing', 'assets', 'rights-readiness', assetId],
    queryFn: () => fetchAssetRightsReadiness(assetId),
    enabled: canView && Boolean(assetId),
  });

  const asset = detailQuery.data;
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState('draft');
  const [folder, setFolder] = useState('');
  const [tags, setTags] = useState('');
  const [language, setLanguage] = useState('');
  const [audience, setAudience] = useState('');
  const [market, setMarket] = useState('');
  const [propertyType, setPropertyType] = useState('');
  const [country, setCountry] = useState('');
  const [city, setCity] = useState('');
  const [keywords, setKeywords] = useState('');

  useEffect(() => {
    if (!asset) return;
    setTitle(asset.title || asset.name);
    setDescription(asset.description ?? '');
    setNotes(asset.notes ?? '');
    setStatus(asset.status);
    setFolder(asset.folder ?? '');
    setTags((asset.tags ?? []).join(', '));
    setLanguage(asset.ai_prep?.language ?? '');
    setAudience(asset.ai_prep?.audience ?? '');
    setMarket(asset.ai_prep?.market ?? '');
    setPropertyType(asset.ai_prep?.property_type ?? '');
    setCountry(asset.ai_prep?.country ?? '');
    setCity(asset.ai_prep?.city ?? '');
    setKeywords((asset.ai_prep?.keywords ?? []).join(', '));
  }, [asset]);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateAsset(assetId, {
        title,
        description: description || null,
        notes: notes || null,
        status,
        folder: folder || null,
        tags: tags
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        ai_prep: {
          language: language || null,
          audience: audience || null,
          market: market || null,
          property_type: propertyType || null,
          country: country || null,
          city: city || null,
          keywords: keywords
            .split(',')
            .map((item) => item.trim())
            .filter(Boolean),
        },
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['marketing', 'assets'] });
    },
  });

  const archiveMutation = useMutation({
    mutationFn: () => (asset?.archived_at ? restoreAsset(assetId) : archiveAsset(assetId)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['marketing', 'assets'] });
    },
  });

  if (!canView) {
    return (
      <main className="dashboard marketing-module-shell">
        <EmptyState title={t('accessDenied')} description={t('accessDeniedDescription')} />
      </main>
    );
  }

  if (detailQuery.isLoading) {
    return (
      <main className="dashboard marketing-module-shell">
        <LoadingState label={t('loading')} />
      </main>
    );
  }

  if (detailQuery.isError || !asset) {
    return (
      <main className="dashboard marketing-module-shell">
        <ErrorState
          title={t('loadFailed')}
          message={detailQuery.error instanceof ApiError ? detailQuery.error.message : t('notFound')}
        />
      </main>
    );
  }

  const previewId = asset.thumbnail_document_id || asset.document_id;

  return (
    <main className="dashboard marketing-module-shell">
      <header className="dashboard__header marketing-assets__header">
        <div>
          <Link href={'/workspaces/marketing/assets' as Route} className="marketing-link">
            {t('backToList')}
          </Link>
          <h1 className="dashboard__title">{asset.title || asset.name}</h1>
          <div className="marketing-assets__detail-meta">
            <StatusChip tone={statusTone(asset.status)}>{t(`status.${asset.status}` as 'status.draft')}</StatusChip>
            <span>{t(`types.${asset.asset_type}` as 'types.image')}</span>
            {asset.folder && <span>{t(`folders.${asset.folder}` as 'folders.documents')}</span>}
          </div>
        </div>
        <div className="marketing-assets__actions">
          {canViewMarketingAI(user) ? (
            <Link
              href={
                `/workspaces/marketing/ai/assistant?mode=content_draft&assetId=${assetId}${
                  asset.campaign_id ? `&campaignId=${asset.campaign_id}` : ''
                }${asset.project_id ? `&projectId=${asset.project_id}` : ''}` as Route
              }
              className="button button--secondary"
            >
              {tAi('contextualEntry')}
            </Link>
          ) : null}
          {asset.document_id && (
            <>
              <a className="button button--secondary" href={documentPreviewUrl(asset.document_id)} target="_blank" rel="noreferrer">
                {t('preview')}
              </a>
              <a className="button button--secondary" href={documentDownloadUrl(asset.document_id)} target="_blank" rel="noreferrer">
                {t('download')}
              </a>
            </>
          )}
          {canEdit && (
            <>
              <Button type="button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending}>
                {saveMutation.isPending ? tCommon('loading') : t('save')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => archiveMutation.mutate()}
                disabled={archiveMutation.isPending}
              >
                {asset.archived_at ? t('restore') : t('archive')}
              </Button>
            </>
          )}
        </div>
      </header>

      <div className="marketing-assets__detail-layout">
        <section className="marketing-assets__detail-preview">
          <div
            className="marketing-assets__preview marketing-assets__preview--large"
            style={previewId ? { backgroundImage: `url(${documentPreviewUrl(previewId)})` } : undefined}
          >
            {!previewId && <span className="marketing-assets__preview-fallback">{t('noPreview')}</span>}
          </div>
          <p>
            {t('rights')}: {asset.rights_status}
            {readinessQuery.data ? ` · ${readinessQuery.data.state}` : ''}
          </p>
          {asset.campaign_name && (
            <p>
              {t('columns.campaign')}: {asset.campaign_name}
            </p>
          )}
          {asset.project_name && (
            <p>
              {t('columns.project')}: {asset.project_name}
            </p>
          )}
        </section>

        <section className="marketing-assets__detail-form">
          <label className="marketing-assets__field">
            <span>{t('columns.title')}</span>
            <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={!canEdit} />
          </label>
          <label className="marketing-assets__field">
            <span>{t('columns.status')}</span>
            <select value={status} onChange={(event) => setStatus(event.target.value)} disabled={!canEdit}>
              <option value="draft">{t('status.draft')}</option>
              <option value="ready">{t('status.ready')}</option>
              <option value="archived">{t('status.archived')}</option>
            </select>
          </label>
          <label className="marketing-assets__field">
            <span>{t('columns.folder')}</span>
            <select value={folder} onChange={(event) => setFolder(event.target.value)} disabled={!canEdit}>
              <option value="">{t('notSet')}</option>
              {['projects', 'campaigns', 'brand', 'logos', 'videos', 'social', 'documents'].map((item) => (
                <option key={item} value={item}>
                  {t(`folders.${item}` as 'folders.documents')}
                </option>
              ))}
            </select>
          </label>
          <label className="marketing-assets__field">
            <span>{t('columns.tags')}</span>
            <input value={tags} onChange={(event) => setTags(event.target.value)} disabled={!canEdit} />
          </label>
          <label className="marketing-assets__field">
            <span>{t('description')}</span>
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} disabled={!canEdit} rows={3} />
          </label>
          <label className="marketing-assets__field">
            <span>{t('notes')}</span>
            <textarea value={notes} onChange={(event) => setNotes(event.target.value)} disabled={!canEdit} rows={3} />
          </label>

          <h2>{t('aiPrep.title')}</h2>
          <p className="marketing-assets__hint">{t('aiPrep.subtitle')}</p>
          <div className="marketing-assets__ai-grid">
            {(
              [
                ['language', language, setLanguage],
                ['audience', audience, setAudience],
                ['market', market, setMarket],
                ['property_type', propertyType, setPropertyType],
                ['country', country, setCountry],
                ['city', city, setCity],
              ] as const
            ).map(([key, value, setter]) => (
              <label key={key} className="marketing-assets__field">
                <span>{t(`aiPrep.${key}` as 'aiPrep.language')}</span>
                <input value={value} onChange={(event) => setter(event.target.value)} disabled={!canEdit} />
              </label>
            ))}
            <label className="marketing-assets__field marketing-assets__field--wide">
              <span>{t('aiPrep.keywords')}</span>
              <input value={keywords} onChange={(event) => setKeywords(event.target.value)} disabled={!canEdit} />
            </label>
          </div>
        </section>
      </div>
    </main>
  );
}
