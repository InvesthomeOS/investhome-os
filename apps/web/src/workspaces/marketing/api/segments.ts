import { apiFetch } from '@/lib/api/client';

export type SegmentSummary = {
  id: string;
  name: string;
  segment_type: string;
  visibility: string;
  estimated_size: number | null;
  calculated_size: number | null;
  calculation_status: string;
  current_version: number;
  last_refreshed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type SegmentField = {
  key: string;
  label: string;
  entity_type: string;
  value_type: string;
  operators: string[];
};

export async function fetchSegments(page = 1, pageSize = 25) {
  return apiFetch<{ items: SegmentSummary[]; total: number; pages: number }>(
    `/marketing/segments?page=${page}&page_size=${pageSize}`,
  );
}

export async function fetchSegmentSummary() {
  return apiFetch<{ total: number; calculated: number; not_calculated: number }>('/marketing/segments/summary');
}

export async function fetchSegmentFieldRegistry() {
  return apiFetch<{ fields: SegmentField[] }>('/marketing/segments/field-registry');
}

export async function fetchSegment(segmentId: string) {
  return apiFetch<SegmentSummary & { description: string | null; depends_on_segment_ids: string[] | null }>(
    `/marketing/segments/${segmentId}`,
  );
}

export async function createSegment(payload: Record<string, unknown>) {
  return apiFetch<SegmentSummary>('/marketing/segments', { method: 'POST', body: JSON.stringify(payload) });
}

export async function previewSegment(segmentId: string) {
  return apiFetch<{
    state: string;
    estimated_count: number | null;
    rule_explanation: string;
    warnings: string[];
  }>(`/marketing/segments/${segmentId}/preview`, { method: 'POST' });
}

export async function calculateSegment(segmentId: string) {
  return apiFetch<{ status: string; member_count: number | null; warnings: string[] }>(
    `/marketing/segments/${segmentId}/calculate`,
    { method: 'POST' },
  );
}

export async function fetchSegmentRules(segmentId: string) {
  return apiFetch<{ rule_groups: unknown[] }>(`/marketing/segments/${segmentId}/rules`);
}
