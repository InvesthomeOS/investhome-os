'use client';

/**
 * Shared Media Library hook for Creative Studio builders.
 * Lists/search/upload go through the Asset Registry API; builders store Asset IDs only.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  fetchCreativeStudioMediaBlob,
  listCreativeStudioMediaAssets,
  searchCreativeStudioMediaAssets,
  uploadCreativeStudioMediaAsset,
  type CreativeStudioMediaAsset,
} from '@/lib/api/creative-studio';

import { isMediaAssetUuid } from './cs-image-ref';
import {
  getAssetSelectability,
  shouldShowInBuilderPicker,
  type CsAssetDisabledReason,
} from './cs-media-selectability';

export type CsMediaStatus = 'idle' | 'loading' | 'ready' | 'error';

export type CsMediaPickerItem = {
  id: string;
  name: string;
  contentType: string;
  thumbUrl?: string | null;
  meta: string;
  tags: string[];
  sourceType?: string | null;
  syncStatus?: string | null;
  folderCategory?: string | null;
  linkedProjectId?: string | null;
  selectable: boolean;
  disabledReason: CsAssetDisabledReason | null;
  updatedAt: string;
  createdAt: string;
  fileSize: number;
};

export type UseCsMediaLibraryResult = {
  status: CsMediaStatus;
  error: string | null;
  items: CsMediaPickerItem[];
  rawAssets: CreativeStudioMediaAsset[];
  uploading: boolean;
  displayUrls: Record<string, string>;
  refresh: (query?: string) => Promise<void>;
  search: (query: string) => Promise<void>;
  /** Upload via Media Library API — returns registry asset (never builder-owned). */
  uploadAsset: (file: File) => Promise<CreativeStudioMediaAsset | null>;
  ensureDisplayUrl: (assetId: string) => Promise<string | null>;
  getCachedDisplayUrl: (assetId: string) => string | null;
  getRawAsset: (assetId: string) => CreativeStudioMediaAsset | null;
};

function formatBytes(size: number): string {
  if (!Number.isFinite(size) || size <= 0) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function mapToPickerItem(
  asset: CreativeStudioMediaAsset,
  displayThumbUrl?: string | null,
): CsMediaPickerItem {
  const { selectable, reason } = getAssetSelectability(asset);
  const resolution =
    asset.width && asset.height ? `${asset.width}×${asset.height}` : '';
  const metaParts = [resolution, formatBytes(asset.file_size)].filter(Boolean);
  if (reason === 'missing') metaParts.push('Missing');
  if (reason === 'error') metaParts.push('Error');
  const thumb =
    displayThumbUrl ||
    (asset.thumbnail_url && !asset.thumbnail_url.startsWith('blob:')
      ? asset.thumbnail_url
      : null) ||
    (asset.content_type?.startsWith('image/') &&
    asset.url &&
    !asset.url.startsWith('blob:')
      ? asset.url
      : null);

  return {
    id: asset.id,
    name: asset.filename,
    contentType: asset.content_type || '',
    thumbUrl: thumb,
    meta: metaParts.join(' · ') || asset.content_type || 'FILE',
    tags: Array.isArray(asset.tags) ? asset.tags : [],
    sourceType: asset.source_type ?? null,
    syncStatus: asset.sync_status ?? null,
    folderCategory: asset.folder_category ?? null,
    linkedProjectId: asset.linked_project_id ?? null,
    selectable,
    disabledReason: reason,
    updatedAt: asset.updated_at || asset.created_at,
    createdAt: asset.created_at,
    fileSize: asset.file_size,
  };
}

export function useCsMediaLibrary(options?: {
  linkedProjectId?: string | null;
  enabled?: boolean;
  /** When true, only image/* content types are listed (default true for builder image slots). */
  imagesOnly?: boolean;
  /**
   * When true (Landing Page Builder), require linkedProjectId and scope list/search
   * to that project. Other builders omit this and keep unscoped list behavior.
   */
  scopeToLinkedProject?: boolean;
}): UseCsMediaLibraryResult {
  const linkedProjectId = options?.linkedProjectId ?? null;
  const scopeToLinkedProject = options?.scopeToLinkedProject === true;
  const enabled =
    options?.enabled !== false &&
    (!scopeToLinkedProject || Boolean(linkedProjectId));
  const imagesOnly = options?.imagesOnly !== false;
  const linkedProjectIdRef = useRef(linkedProjectId);
  linkedProjectIdRef.current = linkedProjectId;
  const scopeToLinkedProjectRef = useRef(scopeToLinkedProject);
  scopeToLinkedProjectRef.current = scopeToLinkedProject;

  const [status, setStatus] = useState<CsMediaStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [rawAssets, setRawAssets] = useState<CreativeStudioMediaAsset[]>([]);
  const [items, setItems] = useState<CsMediaPickerItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const [displayUrls, setDisplayUrls] = useState<Record<string, string>>({});

  const blobCacheRef = useRef<Map<string, string>>(new Map());
  const inflightBlobRef = useRef<Map<string, Promise<string | null>>>(new Map());
  const listGenRef = useRef(0);
  const listInflightKeyRef = useRef<string | null>(null);
  const listInflightPromiseRef = useRef<Promise<void> | null>(null);
  const lastQueryRef = useRef('');
  const uploadLockRef = useRef(false);
  const mountedRef = useRef(true);
  const rawByIdRef = useRef<Map<string, CreativeStudioMediaAsset>>(new Map());
  const warmThumbsRef = useRef<(ids: string[]) => void>(() => {});

  const revokeAll = useCallback(() => {
    for (const url of blobCacheRef.current.values()) {
      URL.revokeObjectURL(url);
    }
    blobCacheRef.current.clear();
    inflightBlobRef.current.clear();
    setDisplayUrls({});
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      revokeAll();
    };
  }, [revokeAll]);

  const ensureDisplayUrl = useCallback(async (assetId: string): Promise<string | null> => {
    if (!isMediaAssetUuid(assetId)) return null;
    const cached = blobCacheRef.current.get(assetId);
    if (cached) return cached;

    const inflight = inflightBlobRef.current.get(assetId);
    if (inflight) return inflight;

    const promise = (async () => {
      try {
        const blob = await fetchCreativeStudioMediaBlob(assetId);
        if (!mountedRef.current) return null;
        const prev = blobCacheRef.current.get(assetId);
        const url = URL.createObjectURL(blob);
        blobCacheRef.current.set(assetId, url);
        if (prev && prev !== url) URL.revokeObjectURL(prev);
        setDisplayUrls((prevMap) => ({ ...prevMap, [assetId]: url }));
        return url;
      } catch {
        return null;
      } finally {
        inflightBlobRef.current.delete(assetId);
      }
    })();

    inflightBlobRef.current.set(assetId, promise);
    return promise;
  }, []);

  warmThumbsRef.current = (ids: string[]) => {
    for (const id of ids) {
      void ensureDisplayUrl(id).then((url) => {
        if (!url || !mountedRef.current) return;
        setItems((prev) =>
          prev.map((card) => (card.id === id ? { ...card, thumbUrl: url } : card)),
        );
      });
    }
  };

  const applyList = useCallback(
    (list: CreativeStudioMediaAsset[]) => {
      const scopeId = linkedProjectIdRef.current;
      const mustScope = scopeToLinkedProjectRef.current;
      const visible = list.filter((a) => {
        if (!shouldShowInBuilderPicker(a)) return false;
        if (imagesOnly && a.content_type && !a.content_type.startsWith('image/')) {
          return false;
        }
        // Scope strictly to the active construction project — never leak cross-project assets.
        if (mustScope) {
          if (!scopeId || a.linked_project_id !== scopeId) return false;
        }
        return true;
      });
      rawByIdRef.current = new Map(visible.map((a) => [a.id, a]));
      setRawAssets(visible);
      // Empty Media Library = empty picker (no demo/sample fallback assets).
      setItems(
        visible.map((asset) =>
          mapToPickerItem(asset, blobCacheRef.current.get(asset.id) ?? null),
        ),
      );

      const warmIds = visible
        .filter(
          (a) =>
            a.content_type?.startsWith('image/') &&
            isMediaAssetUuid(a.id) &&
            getAssetSelectability(a).selectable,
        )
        .map((a) => a.id)
        .slice(0, 24);
      warmThumbsRef.current(warmIds);
    },
    [imagesOnly],
  );

  const getCachedDisplayUrl = useCallback((assetId: string) => {
    return blobCacheRef.current.get(assetId) ?? null;
  }, []);

  const getRawAsset = useCallback((assetId: string) => {
    return rawByIdRef.current.get(assetId) ?? null;
  }, []);

  const fetchList = useCallback(
    async (query?: string) => {
      if (!enabled) return;
      if (scopeToLinkedProject && !linkedProjectId) return;
      const q = (query ?? lastQueryRef.current).trim();
      lastQueryRef.current = q;
      const key = scopeToLinkedProject
        ? `${linkedProjectId}:${q || '__all__'}`
        : q || '__all__';
      const gen = ++listGenRef.current;

      if (listInflightKeyRef.current === key && listInflightPromiseRef.current) {
        await listInflightPromiseRef.current;
        return;
      }

      const run = async () => {
        setStatus('loading');
        setError(null);
        try {
          const listParams = {
            page: 1 as const,
            page_size: 100 as const,
            ...(scopeToLinkedProject && linkedProjectId
              ? { linked_project_id: linkedProjectId }
              : {}),
          };
          const response = q
            ? await searchCreativeStudioMediaAssets({ q, ...listParams })
            : await listCreativeStudioMediaAssets(listParams);
          if (gen !== listGenRef.current || !mountedRef.current) return;
          applyList(response.items ?? []);
          setStatus('ready');
        } catch (err) {
          if (gen !== listGenRef.current || !mountedRef.current) return;
          const message = err instanceof Error ? err.message : 'Media library load failed';
          setError(message);
          setStatus('error');
          setRawAssets((prev) => {
            if (!prev.length) applyList([]);
            return prev;
          });
        }
      };

      const pending = run().finally(() => {
        if (listInflightPromiseRef.current === pending) {
          listInflightPromiseRef.current = null;
          listInflightKeyRef.current = null;
        }
      });
      listInflightKeyRef.current = key;
      listInflightPromiseRef.current = pending;
      await pending;
    },
    [applyList, enabled, linkedProjectId, scopeToLinkedProject],
  );

  const refresh = useCallback(
    async (query?: string) => {
      listInflightKeyRef.current = null;
      listInflightPromiseRef.current = null;
      await fetchList(query);
    },
    [fetchList],
  );

  const search = useCallback(
    async (query: string) => {
      await fetchList(query);
    },
    [fetchList],
  );

  const uploadAsset = useCallback(
    async (file: File): Promise<CreativeStudioMediaAsset | null> => {
      if (!enabled) return null;
      if (scopeToLinkedProject && !linkedProjectId) return null;
      if (uploadLockRef.current) return null;
      uploadLockRef.current = true;
      setUploading(true);
      setError(null);
      try {
        const uploaded = await uploadCreativeStudioMediaAsset({
          file,
          linked_project_id: linkedProjectId,
        });
        if (!mountedRef.current) return uploaded;
        rawByIdRef.current.set(uploaded.id, uploaded);
        await refresh(lastQueryRef.current);
        await ensureDisplayUrl(uploaded.id);
        return uploaded;
      } catch (err) {
        if (mountedRef.current) {
          const message = err instanceof Error ? err.message : 'Upload failed';
          setError(message);
        }
        return null;
      } finally {
        uploadLockRef.current = false;
        if (mountedRef.current) setUploading(false);
      }
    },
    [enabled, ensureDisplayUrl, linkedProjectId, refresh, scopeToLinkedProject],
  );

  // Default (Blog/Email/etc): unchanged — fetch when enabled; linkedProjectId is upload-only.
  useEffect(() => {
    if (scopeToLinkedProject) return;
    if (!enabled) return;
    void fetchList('');
  }, [enabled, fetchList, scopeToLinkedProject]);

  // Landing Page Builder: require linkedProjectId and re-scope on project switch.
  useEffect(() => {
    if (!scopeToLinkedProject) return;
    if (!enabled || !linkedProjectId) {
      listGenRef.current += 1;
      listInflightKeyRef.current = null;
      listInflightPromiseRef.current = null;
      rawByIdRef.current = new Map();
      setRawAssets([]);
      setItems([]);
      setStatus('idle');
      setError(null);
      return;
    }
    revokeAll();
    lastQueryRef.current = '';
    void fetchList('');
  }, [enabled, linkedProjectId, scopeToLinkedProject, fetchList, revokeAll]);

  return {
    status,
    error,
    items,
    rawAssets,
    uploading,
    displayUrls,
    refresh,
    search,
    uploadAsset,
    ensureDisplayUrl,
    getCachedDisplayUrl,
    getRawAsset,
  };
}
