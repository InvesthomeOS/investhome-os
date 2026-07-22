'use client';

import { useCallback, useMemo } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import type { BiFilterPreset, BiFilters } from './bi-types';

const FILTER_KEYS = [
  'date_from',
  'date_to',
  'comparison',
  'workspace',
  'project_id',
  'assigned_to',
  'lead_source',
  'investor_id',
  'campaign_id',
  'currency',
  'status',
  'preset',
] as const;

export function filtersFromSearchParams(params: URLSearchParams): BiFilters {
  const filters: BiFilters = {};
  for (const key of FILTER_KEYS) {
    const value = params.get(key);
    if (value) {
      (filters as Record<string, string>)[key] = value;
    }
  }
  if (!filters.preset && !filters.date_from) {
    filters.preset = '30d';
  }
  if (!filters.comparison) {
    filters.comparison = 'previous_period';
  }
  return filters;
}

export function useBiFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo(() => filtersFromSearchParams(searchParams), [searchParams]);

  const setFilters = useCallback(
    (patch: Partial<BiFilters>, replace = true) => {
      const next = new URLSearchParams(searchParams.toString());
      const merged = { ...filters, ...patch };
      for (const key of FILTER_KEYS) {
        const value = merged[key];
        if (value === undefined || value === null || value === '') {
          next.delete(key);
        } else {
          next.set(key, String(value));
        }
      }
      if (patch.preset && patch.preset !== 'custom') {
        next.delete('date_from');
        next.delete('date_to');
      }
      const qs = next.toString();
      const href = qs ? `${pathname}?${qs}` : pathname;
      if (replace) {
        router.replace(href);
      } else {
        router.push(href);
      }
    },
    [filters, pathname, router, searchParams],
  );

  const setPreset = useCallback(
    (preset: BiFilterPreset) => {
      setFilters({ preset, date_from: undefined, date_to: undefined });
    },
    [setFilters],
  );

  return { filters, setFilters, setPreset };
}
