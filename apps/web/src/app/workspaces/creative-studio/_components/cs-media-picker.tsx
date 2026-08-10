'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import { IhIcon } from '@/components/icons/ih-icons';

import type { CsImageRef } from './cs-image-ref';
import { imageRefFromMediaAsset } from './cs-image-ref';
import type { CsMediaPickerItem, UseCsMediaLibraryResult } from './use-cs-media-library';

import './cs-media-picker.css';

export type CsMediaSourceFilter = 'all' | 'google_drive' | 'upload';
export type CsMediaSortFilter = 'recent' | 'name';

export type CsMediaPickerLabels = {
  title?: string;
  search?: string;
  sourceAll?: string;
  sourceDrive?: string;
  sourceUpload?: string;
  categoryAll?: string;
  projectAll?: string;
  recent?: string;
  nameSort?: string;
  favoritesHint?: string;
  missing?: string;
  error?: string;
  empty?: string;
  loading?: string;
  loadFailed?: string;
  retry?: string;
  chooseAsset?: string;
  upload?: string;
  uploading?: string;
  select?: string;
  cancel?: string;
  preview?: string;
  notSelectable?: string;
};

export type CsMediaPickerProps = {
  media: UseCsMediaLibraryResult;
  open?: boolean;
  /** When false, render inline (rail) without dialog chrome. Default true for dialog usage. */
  variant?: 'inline' | 'panel';
  linkedProjectId?: string | null;
  /**
   * When true and linkedProjectId is set, lock the project filter to that id
   * and hide the "all projects" option (Landing Page Builder).
   */
  lockLinkedProject?: boolean;
  selectedAssetId?: string | null;
  onSelect: (ref: CsImageRef, item: CsMediaPickerItem) => void;
  onClose?: () => void;
  labels?: CsMediaPickerLabels;
  /** Allow upload through Media Library API (builder never owns the file). */
  allowUpload?: boolean;
  className?: string;
  testId?: string;
};

function filterItems(
  items: CsMediaPickerItem[],
  opts: {
    query: string;
    source: CsMediaSourceFilter;
    category: string;
    projectId: string;
    sort: CsMediaSortFilter;
  },
): CsMediaPickerItem[] {
  const q = opts.query.trim().toLowerCase();
  let next = items.filter((item) => {
    if (opts.source === 'google_drive' && item.sourceType !== 'google_drive') return false;
    if (opts.source === 'upload' && item.sourceType === 'google_drive') return false;
    if (opts.category && opts.category !== 'all') {
      const cat = (item.folderCategory || '').toLowerCase();
      if (cat !== opts.category.toLowerCase()) return false;
    }
    if (opts.projectId && opts.projectId !== 'all') {
      if (item.linkedProjectId !== opts.projectId) return false;
    }
    if (q) {
      const hay = `${item.name} ${item.tags.join(' ')} ${item.meta}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });

  next = [...next].sort((a, b) => {
    if (opts.sort === 'name') return a.name.localeCompare(b.name);
    return String(b.updatedAt).localeCompare(String(a.updatedAt));
  });
  return next;
}

export function CsMediaPicker({
  media,
  variant = 'panel',
  linkedProjectId,
  lockLinkedProject = false,
  selectedAssetId,
  onSelect,
  onClose,
  labels: labelOverrides,
  allowUpload = true,
  className,
  testId = 'cs-media-picker',
}: CsMediaPickerProps) {
  const t = useTranslations('creativeStudio.mediaPicker');
  const labels: Required<CsMediaPickerLabels> = {
    title: labelOverrides?.title ?? t('title'),
    search: labelOverrides?.search ?? t('search'),
    sourceAll: labelOverrides?.sourceAll ?? t('sourceAll'),
    sourceDrive: labelOverrides?.sourceDrive ?? t('sourceDrive'),
    sourceUpload: labelOverrides?.sourceUpload ?? t('sourceUpload'),
    categoryAll: labelOverrides?.categoryAll ?? t('categoryAll'),
    projectAll: labelOverrides?.projectAll ?? t('projectAll'),
    recent: labelOverrides?.recent ?? t('recent'),
    nameSort: labelOverrides?.nameSort ?? t('nameSort'),
    favoritesHint: labelOverrides?.favoritesHint ?? t('favoritesHint'),
    missing: labelOverrides?.missing ?? t('missing'),
    error: labelOverrides?.error ?? t('error'),
    empty: labelOverrides?.empty ?? t('empty'),
    loading: labelOverrides?.loading ?? t('loading'),
    loadFailed: labelOverrides?.loadFailed ?? t('loadFailed'),
    retry: labelOverrides?.retry ?? t('retry'),
    chooseAsset: labelOverrides?.chooseAsset ?? t('chooseAsset'),
    upload: labelOverrides?.upload ?? t('upload'),
    uploading: labelOverrides?.uploading ?? t('uploading'),
    select: labelOverrides?.select ?? t('select'),
    cancel: labelOverrides?.cancel ?? t('cancel'),
    preview: labelOverrides?.preview ?? t('preview'),
    notSelectable: labelOverrides?.notSelectable ?? t('notSelectable'),
  };

  const lockedProjectId =
    lockLinkedProject && linkedProjectId ? linkedProjectId : null;

  const [query, setQuery] = useState('');
  const [source, setSource] = useState<CsMediaSourceFilter>('all');
  const [category, setCategory] = useState('all');
  const [projectFilter, setProjectFilter] = useState(
    linkedProjectId ? linkedProjectId : 'all',
  );
  const [sort, setSort] = useState<CsMediaSortFilter>('recent');
  const [previewId, setPreviewId] = useState<string | null>(selectedAssetId ?? null);
  const [warn, setWarn] = useState<string | null>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const searchTimer = useRef<number | null>(null);

  useEffect(() => {
    setProjectFilter(linkedProjectId ? linkedProjectId : 'all');
  }, [linkedProjectId]);

  useEffect(() => {
    if (lockedProjectId) setProjectFilter(lockedProjectId);
  }, [lockedProjectId]);

  useEffect(() => {
    if (searchTimer.current) window.clearTimeout(searchTimer.current);
    searchTimer.current = window.setTimeout(() => {
      void media.search(query);
    }, 280);
    return () => {
      if (searchTimer.current) window.clearTimeout(searchTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- debounce query only
  }, [query]);

  const categories = useMemo(() => {
    const set = new Set<string>();
    for (const item of media.items) {
      if (item.folderCategory) set.add(item.folderCategory);
    }
    return [...set].sort();
  }, [media.items]);

  const projects = useMemo(() => {
    if (lockedProjectId) return [lockedProjectId];
    const set = new Set<string>();
    for (const item of media.items) {
      if (item.linkedProjectId) set.add(item.linkedProjectId);
    }
    if (linkedProjectId) set.add(linkedProjectId);
    return [...set].sort();
  }, [linkedProjectId, lockedProjectId, media.items]);

  const effectiveProjectFilter = lockedProjectId ?? projectFilter;

  const filtered = useMemo(
    () =>
      filterItems(media.items, {
        query: '',
        source,
        category,
        projectId: effectiveProjectFilter,
        sort,
      }),
    [category, effectiveProjectFilter, media.items, sort, source],
  );

  const preview = filtered.find((i) => i.id === previewId) ?? null;

  function trySelect(item: CsMediaPickerItem) {
    if (!item.selectable) {
      setWarn(labels.notSelectable);
      window.setTimeout(() => setWarn(null), 2200);
      return;
    }
    const raw = media.getRawAsset(item.id);
    if (!raw) {
      setWarn(labels.notSelectable);
      return;
    }
    onSelect(imageRefFromMediaAsset(raw), item);
  }

  async function handleUpload(file: File | null | undefined) {
    if (!file || media.uploading) return;
    try {
      const uploaded = await media.uploadAsset(file);
      if (!uploaded) {
        setWarn(media.error || labels.loadFailed);
        return;
      }
      const item =
        media.items.find((i) => i.id === uploaded.id) ||
        ({
          id: uploaded.id,
          name: uploaded.filename,
          contentType: uploaded.content_type,
          selectable: true,
          disabledReason: null,
          meta: '',
          tags: [],
          updatedAt: uploaded.updated_at,
          createdAt: uploaded.created_at,
          fileSize: uploaded.file_size,
        } satisfies CsMediaPickerItem);
      onSelect(imageRefFromMediaAsset(uploaded), item);
    } catch {
      setWarn(labels.loadFailed);
    }
  }

  return (
    <div
      className={`cs-media-picker cs-media-picker--${variant}${className ? ` ${className}` : ''}`}
      data-testid={testId}
    >
      <div className="cs-media-picker__head">
        <div className="cs-media-picker__title-row">
          <h2>{labels.title}</h2>
          {onClose ? (
            <button
              type="button"
              className="cs-media-picker__icon-btn"
              aria-label={labels.cancel}
              onClick={onClose}
              data-testid={`${testId}-close`}
            >
              ×
            </button>
          ) : null}
        </div>
        <label className="cs-media-picker__search">
          <IhIcon name="search" size={14} />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={labels.search}
            aria-label={labels.search}
            data-testid={`${testId}-search`}
          />
        </label>
        <div className="cs-media-picker__filters" role="group" aria-label={labels.title}>
          <select
            value={source}
            onChange={(e) => setSource(e.target.value as CsMediaSourceFilter)}
            data-testid={`${testId}-source`}
          >
            <option value="all">{labels.sourceAll}</option>
            <option value="google_drive">{labels.sourceDrive}</option>
            <option value="upload">{labels.sourceUpload}</option>
          </select>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            data-testid={`${testId}-category`}
          >
            <option value="all">{labels.categoryAll}</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <select
            value={effectiveProjectFilter}
            onChange={(e) => {
              if (lockedProjectId) return;
              setProjectFilter(e.target.value);
            }}
            disabled={Boolean(lockedProjectId)}
            data-testid={`${testId}-project`}
          >
            {lockedProjectId ? null : <option value="all">{labels.projectAll}</option>}
            {projects.map((p) => (
              <option key={p} value={p}>
                {p.slice(0, 8)}…
              </option>
            ))}
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as CsMediaSortFilter)}
            data-testid={`${testId}-sort`}
          >
            <option value="recent">{labels.recent}</option>
            <option value="name">{labels.nameSort}</option>
          </select>
        </div>
        <p className="cs-media-picker__hint" data-testid={`${testId}-favorites-hint`}>
          {labels.favoritesHint}
        </p>
      </div>

      <div className="cs-media-picker__body">
        {media.status === 'error' ? (
          <p className="cs-media-picker__muted">
            {labels.loadFailed}{' '}
            <button type="button" onClick={() => void media.refresh(query)}>
              {labels.retry}
            </button>
          </p>
        ) : null}
        {media.status === 'loading' && filtered.length === 0 ? (
          <p className="cs-media-picker__muted">{labels.loading}</p>
        ) : null}
        {media.status === 'ready' && filtered.length === 0 ? (
          <p className="cs-media-picker__muted">{labels.empty}</p>
        ) : null}

        <div className="cs-media-picker__grid" data-testid={`${testId}-grid`}>
          {filtered.map((item) => {
            const selected = selectedAssetId === item.id || previewId === item.id;
            const disabled = !item.selectable;
            return (
              <button
                key={item.id}
                type="button"
                className={`cs-media-picker__card${selected ? ' is-selected' : ''}${
                  disabled ? ' is-disabled' : ''
                }`}
                disabled={disabled}
                aria-disabled={disabled}
                title={disabled ? labels.notSelectable : item.name}
                data-testid={`${testId}-item-${item.id}`}
                data-selectable={item.selectable ? 'true' : 'false'}
                data-sync-status={item.syncStatus || ''}
                onClick={() => {
                  setPreviewId(item.id);
                  if (!disabled) trySelect(item);
                }}
              >
                <span className="cs-media-picker__thumb">
                  {item.thumbUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={item.thumbUrl} alt="" loading="lazy" />
                  ) : (
                    <IhIcon name="inventory" size={20} />
                  )}
                </span>
                <span className="cs-media-picker__card-meta">
                  <strong>{item.name}</strong>
                  <span>{item.meta}</span>
                </span>
                {item.disabledReason === 'missing' ? (
                  <StatusChip tone="warning">{labels.missing}</StatusChip>
                ) : null}
                {item.disabledReason === 'error' ? (
                  <StatusChip tone="danger">{labels.error}</StatusChip>
                ) : null}
                {item.sourceType === 'google_drive' && item.disabledReason !== 'missing' ? (
                  <span className="cs-media-picker__drive-dot" aria-hidden="true" />
                ) : null}
              </button>
            );
          })}
        </div>

        {preview ? (
          <aside className="cs-media-picker__preview" data-testid={`${testId}-preview`}>
            <p className="cs-media-picker__section-label">{labels.preview}</p>
            <div className="cs-media-picker__preview-frame">
              {preview.thumbUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview.thumbUrl} alt="" />
              ) : (
                <IhIcon name="inventory" size={28} />
              )}
            </div>
            <strong>{preview.name}</strong>
            <p className="cs-media-picker__muted">{preview.meta}</p>
            {preview.tags.length ? (
              <p className="cs-media-picker__muted">{preview.tags.join(', ')}</p>
            ) : null}
            <Button
              type="button"
              size="sm"
              disabled={!preview.selectable}
              onClick={() => trySelect(preview)}
              data-testid={`${testId}-use`}
            >
              {labels.select}
            </Button>
          </aside>
        ) : null}
      </div>

      <div className="cs-media-picker__footer">
        {allowUpload ? (
          <>
            <input
              ref={uploadRef}
              type="file"
              accept="image/*"
              hidden
              data-testid={`${testId}-upload-input`}
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = '';
                void handleUpload(file);
              }}
            />
            <Button
              type="button"
              size="sm"
              variant="secondary"
              disabled={media.uploading}
              onClick={() => uploadRef.current?.click()}
              data-testid={`${testId}-upload`}
            >
              <IhIcon name="plus" size={12} />
              {media.uploading ? labels.uploading : labels.upload}
            </Button>
          </>
        ) : null}
        {warn ? (
          <p className="cs-media-picker__warn" role="status" data-testid={`${testId}-warn`}>
            {warn}
          </p>
        ) : null}
      </div>
    </div>
  );
}
