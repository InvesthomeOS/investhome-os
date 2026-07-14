import type { HealthStatus } from '@investhome/shared';

import { apiFetch } from '@/lib/api/client';

export interface ApiHealthResponse extends HealthStatus {
  database: string;
}

export async function fetchHealth(): Promise<ApiHealthResponse> {
  return apiFetch<ApiHealthResponse>('/health');
}
