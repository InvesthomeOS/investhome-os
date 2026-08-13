'use client';

/**
 * Per-post Drive asset rehydration for Social Media Builder.
 * Canonical identity is Asset ID. Blob/object URLs are runtime-only display cache.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { isMediaAssetUuid } from '../_components/cs-image-ref';

import type { SocialElement } from './social-media-builder-elements';
import type { SocialPost } from './social-media-builder-model';

export type CoverResolveStatus = 'empty' | 'loading' | 'ready' | 'error';

export type AssetDisplayEntry = {
  status: 'loading' | 'ready' | 'error';
  url: string | null;
};

export const SMB_ASSET_RESOLVE_TIMEOUT_MS = 20_000;

function uniqueAssetIds(ids: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const id of ids) {
    if (!isMediaAssetUuid(id) || seen.has(id)) continue;
    seen.add(id);
    out.push(id);
  }
  return out;
}

export function collectElementAssetIds(
  elements: SocialElement[] | null | undefined,
): string[] {
  if (!elements?.length) return [];
  const ids: string[] = [];
  for (const el of elements) {
    if (el.type === 'IMAGE' && el.assetId && isMediaAssetUuid(el.assetId)) {
      ids.push(el.assetId);
    }
  }
  return uniqueAssetIds(ids);
}

export function collectPostAssetIds(post: SocialPost | null | undefined): string[] {
  if (!post) return [];
  const ids: string[] = [];
  if (post.coverAssetId && isMediaAssetUuid(post.coverAssetId)) {
    ids.push(post.coverAssetId);
  }
  ids.push(...collectElementAssetIds(post.elements));
  return uniqueAssetIds(ids);
}

/** Selected post first so its Drive fetch is not starved by the concurrency cap. */
export function collectAllPostsAssetIds(
  posts: SocialPost[],
  selectedPostId?: string | null,
): string[] {
  const selected = posts.find((p) => p.id === selectedPostId);
  const ordered: string[] = [];
  if (selected) ordered.push(...collectPostAssetIds(selected));
  for (const post of posts) {
    if (post.id === selectedPostId) continue;
    ordered.push(...collectPostAssetIds(post));
  }
  return uniqueAssetIds(ordered);
}

export function canonicalCoverAssetId(value: string | null | undefined): string | null {
  return value && isMediaAssetUuid(value) ? value.trim() : null;
}

export function deriveArtboardState(
  coverAssetId: string | null | undefined,
  displayById: Record<string, AssetDisplayEntry | undefined>,
): { src: string | null; state: CoverResolveStatus } {
  const id = canonicalCoverAssetId(coverAssetId);
  if (!id) return { src: null, state: 'empty' };
  const entry = displayById[id];
  if (entry?.status === 'ready' && entry.url) {
    return { src: entry.url, state: 'ready' };
  }
  if (entry?.status === 'error') {
    return { src: null, state: 'error' };
  }
  return { src: null, state: 'loading' };
}

/**
 * A resolved fetch for post A must never become the painted artboard of post B.
 * Cache updates stay keyed by assetId; this gate is for "current artboard" writes.
 */
export function canPaintResolvedAsset(input: {
  requestPostId: string;
  requestAssetId: string;
  selectedPostId: string;
  selectedCoverAssetId: string | null;
}): boolean {
  if (input.requestPostId !== input.selectedPostId) return false;
  if (!input.selectedCoverAssetId) return false;
  return input.requestAssetId === input.selectedCoverAssetId;
}

export function assetUsedByOtherPosts(
  assetId: string,
  posts: SocialPost[],
  exceptPostId: string,
): boolean {
  if (!isMediaAssetUuid(assetId)) return false;
  for (const post of posts) {
    if (post.id === exceptPostId) continue;
    if (collectPostAssetIds(post).includes(assetId)) return true;
  }
  return false;
}

export function postsAssetIdsKey(posts: SocialPost[]): string {
  return uniqueAssetIds(collectAllPostsAssetIds(posts)).sort().join('|');
}

export type EnsureDisplayUrl = (
  assetId: string,
  options?: { force?: boolean },
) => Promise<string | null>;

export function useSmbPostAssetHydration(options: {
  enabled: boolean;
  posts: SocialPost[];
  selectedPostId: string;
  linkedProjectId?: string | null;
  ensureDisplayUrl: EnsureDisplayUrl;
  getCachedDisplayUrl?: (assetId: string) => string | null;
}): {
  displayUrls: Record<string, string>;
  artboardSrc: string | null;
  artboardState: CoverResolveStatus;
  selectedCoverAssetId: string | null;
  invalidateAsset: (assetId: string) => void;
  retryAsset: (assetId: string) => void;
} {
  const {
    enabled,
    posts,
    selectedPostId,
    linkedProjectId = null,
    ensureDisplayUrl,
    getCachedDisplayUrl,
  } = options;
  const [displayById, setDisplayById] = useState<Record<string, AssetDisplayEntry>>({});
  const displayRef = useRef(displayById);
  displayRef.current = displayById;
  const postsRef = useRef(posts);
  postsRef.current = posts;
  const selectedPostIdRef = useRef(selectedPostId);
  selectedPostIdRef.current = selectedPostId;
  const ensureRef = useRef(ensureDisplayUrl);
  ensureRef.current = ensureDisplayUrl;
  const cachedRef = useRef(getCachedDisplayUrl);
  cachedRef.current = getCachedDisplayUrl;
  const inflightGenRef = useRef<Map<string, number>>(new Map());
  const genRef = useRef(0);
  const retryingRef = useRef<Set<string>>(new Set());
  const forceTriedRef = useRef<Set<string>>(new Set());

  const selectedPost = posts.find((p) => p.id === selectedPostId) ?? posts[0] ?? null;
  const selectedCoverAssetId = canonicalCoverAssetId(selectedPost?.coverAssetId);
  const assetIdsKey = useMemo(() => postsAssetIdsKey(posts), [posts]);

  useEffect(() => {
    setDisplayById({});
    inflightGenRef.current.clear();
    retryingRef.current.clear();
    forceTriedRef.current.clear();
  }, [linkedProjectId]);

  const seedFromMediaCache = useCallback((id: string): string | null => {
    const fromState = displayRef.current[id];
    if (fromState?.status === 'ready' && fromState.url) return fromState.url;
    // Blob URLs are valid runtime display values — never persist them.
    return cachedRef.current?.(id) ?? null;
  }, []);

  useEffect(() => {
    if (!enabled) return;
    const currentPosts = postsRef.current;
    const ids = collectAllPostsAssetIds(currentPosts, selectedPostIdRef.current);
    const timeouts: number[] = [];

    for (const id of ids) {
      const seeded = seedFromMediaCache(id);
      if (seeded) {
        setDisplayById((prev) => {
          if (prev[id]?.status === 'ready' && prev[id].url === seeded) return prev;
          return { ...prev, [id]: { status: 'ready', url: seeded } };
        });
        continue;
      }

      const existing = displayRef.current[id];
      if (existing?.status === 'ready' && existing.url) continue;
      if (existing?.status === 'loading' && inflightGenRef.current.has(id)) continue;

      const gen = ++genRef.current;
      inflightGenRef.current.set(id, gen);
      setDisplayById((prev) => {
        if (prev[id]?.status === 'ready' && prev[id].url) return prev;
        return { ...prev, [id]: { status: 'loading', url: null } };
      });

      const timeoutId = window.setTimeout(() => {
        if (inflightGenRef.current.get(id) !== gen) return;
        setDisplayById((prev) => {
          if (prev[id]?.status === 'ready' && prev[id].url) return prev;
          return { ...prev, [id]: { status: 'error', url: null } };
        });
        inflightGenRef.current.delete(id);
      }, SMB_ASSET_RESOLVE_TIMEOUT_MS);
      timeouts.push(timeoutId);

      void ensureRef.current(id).then((url) => {
        if (inflightGenRef.current.get(id) !== gen) {
          // Stale generation for this asset — still cache a successful blob for later posts.
          if (url) {
            setDisplayById((prev) => {
              if (prev[id]?.status === 'ready' && prev[id].url) return prev;
              return { ...prev, [id]: { status: 'ready', url } };
            });
          }
          return;
        }
        inflightGenRef.current.delete(id);
        if (url) {
          setDisplayById((prev) => ({ ...prev, [id]: { status: 'ready', url } }));
        } else {
          setDisplayById((prev) => ({ ...prev, [id]: { status: 'error', url: null } }));
        }
      });
    }

    return () => {
      for (const timeoutId of timeouts) window.clearTimeout(timeoutId);
    };
  }, [enabled, assetIdsKey, selectedPostId, linkedProjectId, seedFromMediaCache]);

  const displayUrls = useMemo(() => {
    const out: Record<string, string> = {};
    for (const [id, entry] of Object.entries(displayById)) {
      if (entry.status === 'ready' && entry.url) out[id] = entry.url;
    }
    return out;
  }, [displayById]);

  const artboard = useMemo(() => {
    const derived = deriveArtboardState(selectedCoverAssetId, displayById);
    if (derived.state === 'ready') return derived;
    if (selectedCoverAssetId) {
      const cached = cachedRef.current?.(selectedCoverAssetId) ?? null;
      if (cached) return { src: cached, state: 'ready' as const };
    }
    return derived;
  }, [displayById, selectedCoverAssetId]);

  const invalidateAsset = useCallback((assetId: string) => {
    const id = canonicalCoverAssetId(assetId);
    if (!id) return;
    inflightGenRef.current.delete(id);
    retryingRef.current.delete(id);
    forceTriedRef.current.delete(id);
    setDisplayById((prev) => {
      if (!(id in prev)) return prev;
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }, []);

  const retryAsset = useCallback((assetId: string) => {
    const id = canonicalCoverAssetId(assetId);
    if (!id) return;
    if (retryingRef.current.has(id) || forceTriedRef.current.has(id)) return;
    retryingRef.current.add(id);
    forceTriedRef.current.add(id);
    const gen = ++genRef.current;
    inflightGenRef.current.set(id, gen);
    setDisplayById((prev) => ({ ...prev, [id]: { status: 'loading', url: null } }));
    void ensureRef.current(id, { force: true }).then((url) => {
      retryingRef.current.delete(id);
      if (inflightGenRef.current.get(id) !== gen) return;
      inflightGenRef.current.delete(id);
      if (url) {
        setDisplayById((prev) => ({ ...prev, [id]: { status: 'ready', url } }));
      } else {
        setDisplayById((prev) => ({ ...prev, [id]: { status: 'error', url: null } }));
      }
    });
  }, []);

  return {
    displayUrls,
    artboardSrc: artboard.src,
    artboardState: artboard.state,
    selectedCoverAssetId,
    invalidateAsset,
    retryAsset,
  };
}
