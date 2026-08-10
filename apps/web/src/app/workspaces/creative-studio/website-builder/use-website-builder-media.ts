'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  fetchCreativeStudioMediaBlob,
  listCreativeStudioMediaAssets,
  searchCreativeStudioMediaAssets,
  uploadCreativeStudioMediaAsset,
  type CreativeStudioMediaAsset,
} from '@/lib/api/creative-studio';

import {
  isMediaAssetUuid,
  mapMediaAssetToWbAsset,
} from './website-builder-media';
import type { WbAsset } from './website-builder-model';

export type WbMediaStatus = 'idle' | 'loading' | 'ready' | 'error';

export type UseWebsiteBuilderMediaResult = {
  status: WbMediaStatus;
  error: string | null;
  /** Picker cards from Media Library scoped to linked_project_id. Empty library = empty list. */
  assets: WbAsset[];
  rawAssets: CreativeStudioMediaAsset[];
  /** Always false in production — demo sample assets are not used. */
  usingSamples: boolean;
  uploading: boolean;
  displayUrls: Record<string, string>;
  refresh: (query?: string) => Promise<void>;
  search: (query: string) => Promise<void>;
  uploadImage: (file: File) => Promise<CreativeStudioMediaAsset | null>;
  ensureDisplayUrl: (assetId: string) => Promise<string | null>;
  getCachedDisplayUrl: (assetId: string) => string | null;
  getRawAsset: (assetId: string) => CreativeStudioMediaAsset | null;
};

function isImageFile(file: File): boolean {
  if (file.type && file.type.startsWith('image/')) return true;
  return /\.(jpe?g|png|gif|webp|avif|bmp|svg)$/i.test(file.name);
}

export function useWebsiteBuilderMedia(options?: {
  linkedProjectId?: string | null;
  enabled?: boolean;
}): UseWebsiteBuilderMediaResult {
  const linkedProjectId = options?.linkedProjectId ?? null;
  const enabled = options?.enabled !== false && Boolean(linkedProjectId);

  const [status, setStatus] = useState<WbMediaStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [rawAssets, setRawAssets] = useState<CreativeStudioMediaAsset[]>([]);
  const [assets, setAssets] = useState<WbAsset[]>([]);
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
  const linkedProjectIdRef = useRef(linkedProjectId);
  linkedProjectIdRef.current = linkedProjectId;

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
        setAssets((prev) =>
          prev.map((card) => (card.id === id ? { ...card, thumbUrl: url } : card)),
        );
      });
    }
  };

  const applyList = useCallback((items: CreativeStudioMediaAsset[]) => {
    // Archived stay out of builder pickers. MISSING remain visible but are not selectable
    // (enforced in apply paths via sync_status / canApplyMediaAsset).
    // Scope strictly to the active construction project — never leak cross-project assets.
    const scopeId = linkedProjectIdRef.current;
    const visible = items.filter(
      (a) =>
        !a.archived_at &&
        Boolean(scopeId) &&
        a.linked_project_id === scopeId,
    );
    rawByIdRef.current = new Map(visible.map((a) => [a.id, a]));
    setRawAssets(visible);
    // Empty Media Library = empty picker (no demo/sample fallback assets).
    setAssets(
      visible.map((asset) =>
        mapMediaAssetToWbAsset(asset, blobCacheRef.current.get(asset.id) ?? null),
      ),
    );

    const imageIds = visible
      .filter(
        (a) =>
          a.content_type?.startsWith('image/') &&
          isMediaAssetUuid(a.id) &&
          String(a.sync_status || '').toLowerCase() !== 'missing' &&
          String(a.sync_status || '').toLowerCase() !== 'error',
      )
      .map((a) => a.id);
    warmThumbsRef.current(imageIds);
  }, []);

  const getCachedDisplayUrl = useCallback((assetId: string) => {
    return blobCacheRef.current.get(assetId) ?? null;
  }, []);

  const getRawAsset = useCallback((assetId: string) => {
    return rawByIdRef.current.get(assetId) ?? null;
  }, []);

  const fetchList = useCallback(
    async (query?: string) => {
      if (!enabled || !linkedProjectId) return;
      const q = (query ?? lastQueryRef.current).trim();
      lastQueryRef.current = q;
      const key = `${linkedProjectId}:${q || '__all__'}`;
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
            linked_project_id: linkedProjectId,
            page: 1 as const,
            page_size: 100 as const,
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
    [applyList, enabled, linkedProjectId],
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

  const uploadImage = useCallback(
    async (file: File): Promise<CreativeStudioMediaAsset | null> => {
      if (!enabled || !linkedProjectId) return null;
      if (uploadLockRef.current) return null;
      if (!isImageFile(file)) {
        setError('Only image files can be uploaded');
        return null;
      }
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
    [enabled, ensureDisplayUrl, linkedProjectId, refresh],
  );

  useEffect(() => {
    if (!enabled || !linkedProjectId) {
      listGenRef.current += 1;
      listInflightKeyRef.current = null;
      listInflightPromiseRef.current = null;
      rawByIdRef.current = new Map();
      setRawAssets([]);
      setAssets([]);
      setStatus('idle');
      setError(null);
      return;
    }
    revokeAll();
    lastQueryRef.current = '';
    void fetchList('');
  }, [enabled, linkedProjectId, fetchList, revokeAll]);

  return {
    status,
    error,
    assets,
    rawAssets,
    usingSamples: false,
    uploading,
    displayUrls,
    refresh,
    search,
    uploadImage,
    ensureDisplayUrl,
    getCachedDisplayUrl,
    getRawAsset,
  };
}
