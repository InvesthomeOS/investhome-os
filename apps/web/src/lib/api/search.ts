import type { Route } from 'next';

import { apiFetch } from '@/lib/api/client';

export interface SearchHighlight {
  field: string;
  snippet: string;
}

export interface SearchResultItem {
  entity_type: string;
  entity_id: string;
  title: string;
  subtitle: string | null;
  preview: string | null;
  module: string;
  link_query: Record<string, string>;
  status: string | null;
  assigned_to: string | null;
  created_at: string | null;
  score: number;
  highlights: SearchHighlight[];
}

export interface SearchGroup {
  entity_type: string;
  label_key: string;
  items: SearchResultItem[];
  total: number;
}

export interface SearchResponse {
  query: string;
  groups: SearchGroup[];
  total: number;
  took_ms: number;
}

export interface SearchFilters {
  entity_types?: string[];
  status?: string;
  assigned_to?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
}

export async function fetchGlobalSearch(query: string, filters: SearchFilters = {}) {
  const params = new URLSearchParams({ q: query });
  if (filters.entity_types?.length) {
    params.set('entity_types', filters.entity_types.join(','));
  }
  if (filters.status) params.set('status', filters.status);
  if (filters.assigned_to) params.set('assigned_to', filters.assigned_to);
  if (filters.date_from) params.set('date_from', filters.date_from);
  if (filters.date_to) params.set('date_to', filters.date_to);
  if (filters.limit) params.set('limit', String(filters.limit));
  return apiFetch<SearchResponse>(`/search?${params.toString()}`);
}

export function searchResultHref(item: SearchResultItem): Route {
  const base = `/dashboard/${item.module}`;
  if (!item.link_query || Object.keys(item.link_query).length === 0) {
    return base as Route;
  }
  const params = new URLSearchParams(item.link_query);
  return `${base}?${params.toString()}` as Route;
}

export const SEARCH_ENTITY_TYPES = [
  'lead',
  'investor',
  'project',
  'financial_transaction',
  'financial_account',
  'funding_commitment',
  'payment_obligation',
  'user',
  'notification',
  'activity',
] as const;

export type SearchEntityType = (typeof SEARCH_ENTITY_TYPES)[number];

export const FUTURE_SEARCH_ENTITY_TYPES = [
  'document',
  'unit',
  'construction',
  'email',
] as const;

export const SEARCH_DEBOUNCE_MS = 250;
