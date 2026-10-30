'use client';

import type { Route } from 'next';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

export const LIST_SEARCH_DEBOUNCE_MS = 300;

const NO_DEFAULTS: Record<string, string> = {};
const pendingQueries = new Map<string, string>();

export function buildListQuery(
  current: URLSearchParams,
  patch: Record<string, string | null | undefined>,
  defaults: Record<string, string> = NO_DEFAULTS,
): string {
  const next = new URLSearchParams(current.toString());
  for (const [key, raw] of Object.entries(patch)) {
    const value = (raw ?? '').trim();
    if (!value || value === (defaults[key] ?? '')) next.delete(key);
    else next.set(key, value);
  }
  return next.toString();
}

export function useListQueryPatch(defaults: Record<string, string> = NO_DEFAULTS) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const defaultsRef = useRef(defaults);
  defaultsRef.current = defaults;

  useEffect(() => {
    pendingQueries.set(pathname, searchParams.toString());
  }, [pathname, searchParams]);

  return useCallback(
    (patch: Record<string, string | null | undefined>) => {
      const base = pendingQueries.get(pathname) ?? searchParams.toString();
      const qs = buildListQuery(new URLSearchParams(base), patch, defaultsRef.current);
      if (qs === base) return;
      pendingQueries.set(pathname, qs);
      router.replace((qs ? `${pathname}?${qs}` : pathname) as Route, { scroll: false });
    },
    [pathname, router, searchParams],
  );
}

export function useDebouncedQueryParam(
  key: string,
  delay = LIST_SEARCH_DEBOUNCE_MS,
  options?: { resetPage?: boolean },
) {
  const searchParams = useSearchParams();
  const patch = useListQueryPatch();
  const committed = searchParams.get(key) ?? '';
  const [draft, setDraft] = useState(committed);
  const pending = useRef<string | null>(null);
  const resetPage = options?.resetPage ?? false;

  useEffect(() => {
    if (pending.current === committed) {
      pending.current = null;
      return;
    }
    setDraft(committed);
  }, [committed]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const next = draft.trim();
      if (next === committed) return;
      pending.current = next;
      patch(resetPage ? { [key]: next, page: null } : { [key]: next });
    }, delay);
    return () => window.clearTimeout(timer);
  }, [committed, delay, draft, key, patch, resetPage]);

  return [draft, setDraft, committed] as const;
}
