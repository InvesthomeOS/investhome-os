'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  createCreativeStudioMediaFolder,
  deleteCreativeStudioMediaAsset,
  fetchCreativeStudioMediaBlob,
  listCreativeStudioMediaAssets,
  listCreativeStudioMediaFolders,
  searchCreativeStudioMediaAssets,
  updateCreativeStudioMediaTags,
  uploadCreativeStudioMediaAsset,
  type CreativeStudioMediaAsset,
  type CreativeStudioMediaFolder,
} from '@/lib/api/creative-studio';

import {
  isAllowedMediaUpload,
  isApiFolderId,
  isMediaAssetUuid,
  mapApiAssetToMediaAsset,
  mapApiFolderToMediaFolder,
  markSampleAssets,
} from './media-library-api-map';
import { DEMO_ASSETS, type MediaAsset, type MediaFolder } from './media-library-model';

export type MlMediaStatus = 'idle' | 'loading' | 'ready' | 'error';

export type UseMediaLibraryResult = {
  status: MlMediaStatus;
  error: string | null;
  assets: MediaAsset[];
  rawAssets: CreativeStudioMediaAsset[];
  folders: MediaFolder[];
  rawFolders: CreativeStudioMediaFolder[];
  total: number;
  usingSamples: boolean;
  uploading: boolean;
  tagsUpdating: boolean;
  displayUrls: Record<string, string>;
  refresh: (opts?: { query?: string; folderId?: string | null; includeArchived?: boolean }) => Promise<void>;
  uploadFiles: (files: FileList | File[], folderId?: string | null) => Promise<CreativeStudioMediaAsset | null>;
  createFolder: (name: string) => Promise<CreativeStudioMediaFolder | null>;
  updateTags: (assetId: string, tags: string[]) => Promise<CreativeStudioMediaAsset | null>;
  archiveAsset: (assetId: string) => Promise<CreativeStudioMediaAsset | null>;
  ensureDisplayUrl: (assetId: string) => Promise<string | null>;
  getCachedDisplayUrl: (assetId: string) => string | null;
  downloadAsset: (assetId: string, filename: string) => Promise<boolean>;
  getRawAsset: (assetId: string) => CreativeStudioMediaAsset | null;
};

/** Only real Media Library folder UUIDs may be sent as folder_id. */
function sanitizeFolderId(folderId: string | null | undefined): string | null {
  if (!folderId) return null;
  return isApiFolderId(folderId) ? folderId : null;
}

export function useMediaLibrary(options?: { enabled?: boolean }): UseMediaLibraryResult {
  const enabled = options?.enabled !== false;

  const [status, setStatus] = useState<MlMediaStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [rawAssets, setRawAssets] = useState<CreativeStudioMediaAsset[]>([]);
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [rawFolders, setRawFolders] = useState<CreativeStudioMediaFolder[]>([]);
  const [folders, setFolders] = useState<MediaFolder[]>([]);
  const [total, setTotal] = useState(0);
  const [usingSamples, setUsingSamples] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [tagsUpdating, setTagsUpdating] = useState(false);
  const [displayUrls, setDisplayUrls] = useState<Record<string, string>>({});

  const blobCacheRef = useRef<Map<string, string>>(new Map());
  const inflightBlobRef = useRef<Map<string, Promise<string | null>>>(new Map());
  const listGenRef = useRef(0);
  const listAbortRef = useRef<AbortController | null>(null);
  const lastQueryRef = useRef('');
  const lastFolderRef = useRef<string | null>(null);
  const lastArchivedRef = useRef(false);
  const uploadLockRef = useRef(false);
  const tagsLockRef = useRef(false);
  const mountedRef = useRef(true);
  const apiReadyRef = useRef(false);
  const rawByIdRef = useRef<Map<string, CreativeStudioMediaAsset>>(new Map());
  const folderNameByIdRef = useRef<Map<string, string>>(new Map());
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
      listAbortRef.current?.abort();
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

  const applyFolders = useCallback(
    (folderRows: CreativeStudioMediaFolder[], assetRows: CreativeStudioMediaAsset[]) => {
      const activeFolders = folderRows.filter((f) => !f.archived_at);
      folderNameByIdRef.current = new Map(activeFolders.map((f) => [f.id, f.name]));
      setRawFolders(activeFolders);
      const counts = new Map<string, number>();
      for (const asset of assetRows) {
        if (!asset.folder_id || asset.archived_at) continue;
        counts.set(asset.folder_id, (counts.get(asset.folder_id) ?? 0) + 1);
      }
      setFolders(activeFolders.map((f) => mapApiFolderToMediaFolder(f, counts.get(f.id) ?? 0)));
    },
    [],
  );

  const applyDemoSamples = useCallback(() => {
    setUsingSamples(true);
    // Keep trashed samples so Çöp Kutusu can filter them client-side.
    setAssets(markSampleAssets(DEMO_ASSETS));
    setRawAssets([]);
    setTotal(0);
  }, []);

  const applyList = useCallback(
    (items: CreativeStudioMediaAsset[], listTotal: number, includeArchived: boolean) => {
      const filtered = includeArchived
        ? items.filter((a) => Boolean(a.archived_at))
        : items.filter((a) => !a.archived_at);
      rawByIdRef.current = new Map(filtered.map((a) => [a.id, a]));
      setRawAssets(filtered);
      setTotal(listTotal);
      // Successful API responses (including empty) are primary — never swap in DEMO.
      setUsingSamples(false);
      setAssets(
        filtered.map((asset) =>
          mapApiAssetToMediaAsset(asset, {
            folderName: asset.folder_id
              ? folderNameByIdRef.current.get(asset.folder_id)
              : undefined,
            displayThumbUrl: blobCacheRef.current.get(asset.id) ?? null,
          }),
        ),
      );

      const imageIds = filtered
        .filter((a) => a.content_type?.startsWith('image/') && isMediaAssetUuid(a.id))
        .map((a) => a.id);
      warmThumbsRef.current(imageIds);
    },
    [],
  );

  const getCachedDisplayUrl = useCallback((assetId: string) => {
    return blobCacheRef.current.get(assetId) ?? null;
  }, []);

  const getRawAsset = useCallback((assetId: string) => {
    return rawByIdRef.current.get(assetId) ?? null;
  }, []);

  const fetchList = useCallback(
    async (opts?: { query?: string; folderId?: string | null; includeArchived?: boolean }) => {
      if (!enabled) return;
      const q = (opts?.query ?? lastQueryRef.current).trim();
      const rawFolder =
        opts && 'folderId' in opts ? opts.folderId ?? null : lastFolderRef.current;
      const folderId = sanitizeFolderId(rawFolder);
      const includeArchived =
        opts && 'includeArchived' in opts
          ? Boolean(opts.includeArchived)
          : lastArchivedRef.current;
      lastQueryRef.current = q;
      lastFolderRef.current = folderId;
      lastArchivedRef.current = includeArchived;

      const gen = ++listGenRef.current;
      listAbortRef.current?.abort();
      const abort = new AbortController();
      listAbortRef.current = abort;

      setStatus('loading');
      setError(null);
      try {
        const folderPromise = listCreativeStudioMediaFolders({ include_archived: false });
        const listParams = {
          folder_id: folderId,
          include_archived: includeArchived,
          page: 1,
          page_size: 100,
        };
        const assetsPromise = q
          ? searchCreativeStudioMediaAssets({ q, ...listParams })
          : listCreativeStudioMediaAssets(listParams);

        const [folderRes, assetRes] = await Promise.all([folderPromise, assetsPromise]);
        if (gen !== listGenRef.current || abort.signal.aborted || !mountedRef.current) return;

        apiReadyRef.current = true;
        applyFolders(folderRes.items ?? [], assetRes.items ?? []);
        applyList(assetRes.items ?? [], assetRes.total ?? 0, includeArchived);
        setStatus('ready');
      } catch (err) {
        if (gen !== listGenRef.current || abort.signal.aborted || !mountedRef.current) return;
        const message = err instanceof Error ? err.message : 'Media library load failed';
        setError(message);
        setStatus('error');
        // DEMO only before any successful API session — never overwrite a live API list.
        if (!apiReadyRef.current) {
          applyFolders([], []);
          applyDemoSamples();
        }
      }
    },
    [applyDemoSamples, applyFolders, applyList, enabled],
  );

  const refresh = useCallback(
    async (opts?: { query?: string; folderId?: string | null; includeArchived?: boolean }) => {
      await fetchList(opts);
    },
    [fetchList],
  );

  const uploadFiles = useCallback(
    async (
      files: FileList | File[],
      folderId?: string | null,
    ): Promise<CreativeStudioMediaAsset | null> => {
      if (!enabled) return null;
      if (uploadLockRef.current) return null;
      const list = Array.from(files).filter(Boolean);
      if (!list.length) return null;

      const invalid = list.find((f) => !isAllowedMediaUpload(f));
      if (invalid) {
        setError(`Unsupported file type: ${invalid.name}`);
        return null;
      }

      // Explicit null = All Assets (root). Do not fall back to lastFolderRef.
      const targetFolder =
        folderId !== undefined ? sanitizeFolderId(folderId) : sanitizeFolderId(lastFolderRef.current);

      uploadLockRef.current = true;
      setUploading(true);
      setError(null);
      let lastUploaded: CreativeStudioMediaAsset | null = null;
      try {
        for (const file of list) {
          const uploaded = await uploadCreativeStudioMediaAsset({
            file,
            folder_id: targetFolder,
          });
          lastUploaded = uploaded;
          if (!mountedRef.current) return uploaded;
          rawByIdRef.current.set(uploaded.id, uploaded);
        }
        if (lastUploaded && mountedRef.current) {
          await refresh({
            query: lastQueryRef.current,
            folderId: lastFolderRef.current,
            includeArchived: lastArchivedRef.current,
          });
          if (lastUploaded.content_type?.startsWith('image/')) {
            await ensureDisplayUrl(lastUploaded.id);
          }
        }
        return lastUploaded;
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
    [enabled, ensureDisplayUrl, refresh],
  );

  const createFolder = useCallback(
    async (name: string): Promise<CreativeStudioMediaFolder | null> => {
      if (!enabled) return null;
      const trimmed = name.trim();
      if (!trimmed) return null;
      setError(null);
      try {
        const folder = await createCreativeStudioMediaFolder({ name: trimmed });
        if (!mountedRef.current) return folder;
        await refresh({
          query: lastQueryRef.current,
          folderId: lastFolderRef.current,
          includeArchived: lastArchivedRef.current,
        });
        return folder;
      } catch (err) {
        if (mountedRef.current) {
          const message = err instanceof Error ? err.message : 'Folder create failed';
          setError(message);
        }
        return null;
      }
    },
    [enabled, refresh],
  );

  const updateTags = useCallback(
    async (assetId: string, tags: string[]): Promise<CreativeStudioMediaAsset | null> => {
      if (!enabled || !isMediaAssetUuid(assetId)) return null;
      if (tagsLockRef.current) return null;
      tagsLockRef.current = true;
      setTagsUpdating(true);
      setError(null);
      try {
        const updated = await updateCreativeStudioMediaTags(assetId, tags);
        if (!mountedRef.current) return updated;
        rawByIdRef.current.set(updated.id, updated);
        setRawAssets((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
        setAssets((prev) =>
          prev.map((a) =>
            a.id === updated.id
              ? {
                  ...a,
                  tags: Array.isArray(updated.tags) ? updated.tags.filter(Boolean) : [],
                }
              : a,
          ),
        );
        return updated;
      } catch (err) {
        if (mountedRef.current) {
          const message = err instanceof Error ? err.message : 'Tag update failed';
          setError(message);
        }
        return null;
      } finally {
        tagsLockRef.current = false;
        if (mountedRef.current) setTagsUpdating(false);
      }
    },
    [enabled],
  );

  const archiveAsset = useCallback(
    async (assetId: string): Promise<CreativeStudioMediaAsset | null> => {
      if (!enabled || !isMediaAssetUuid(assetId)) return null;
      setError(null);
      try {
        const archived = await deleteCreativeStudioMediaAsset(assetId);
        if (!mountedRef.current) return archived;
        await refresh({
          query: lastQueryRef.current,
          folderId: lastFolderRef.current,
          includeArchived: lastArchivedRef.current,
        });
        return archived;
      } catch (err) {
        if (mountedRef.current) {
          const message = err instanceof Error ? err.message : 'Archive failed';
          setError(message);
        }
        return null;
      }
    },
    [enabled, refresh],
  );

  const downloadAsset = useCallback(
    async (assetId: string, filename: string): Promise<boolean> => {
      if (!isMediaAssetUuid(assetId)) return false;
      try {
        const blob = await fetchCreativeStudioMediaBlob(assetId);
        if (!mountedRef.current) return false;
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = filename || 'download';
        anchor.rel = 'noopener';
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
        return true;
      } catch (err) {
        if (mountedRef.current) {
          const message = err instanceof Error ? err.message : 'Download failed';
          setError(message);
        }
        return false;
      }
    },
    [],
  );

  useEffect(() => {
    if (!enabled) return;
    void fetchList({ query: '', folderId: null, includeArchived: false });
  }, [enabled, fetchList]);

  return {
    status,
    error,
    assets,
    rawAssets,
    folders,
    rawFolders,
    total,
    usingSamples,
    uploading,
    tagsUpdating,
    displayUrls,
    refresh,
    uploadFiles,
    createFolder,
    updateTags,
    archiveAsset,
    ensureDisplayUrl,
    getCachedDisplayUrl,
    downloadAsset,
    getRawAsset,
  };
}
