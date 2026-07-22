import { apiFetch } from '@/lib/api/client';

import type {
  AssistantGenerateRequest,
  AssistantModesResponse,
  AssistantOutput,
} from '@/workspaces/marketing/schemas/assistant';

export async function fetchAssistantModes(): Promise<AssistantModesResponse> {
  return apiFetch<AssistantModesResponse>('/marketing/ai/assistant/modes');
}

export async function generateAssistantOutput(
  payload: AssistantGenerateRequest,
): Promise<AssistantOutput> {
  return apiFetch<AssistantOutput>('/marketing/ai/assistant/generate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function listAssistantOutputs(params?: {
  output_type?: string;
  status?: string;
  page?: number;
}): Promise<{ items: AssistantOutput[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams();
  if (params?.output_type) qs.set('output_type', params.output_type);
  if (params?.status) qs.set('status', params.status);
  if (params?.page) qs.set('page', String(params.page));
  const suffix = qs.toString() ? `?${qs}` : '';
  return apiFetch(`/marketing/ai/assistant/outputs${suffix}`);
}

export async function saveAssistantOutput(
  outputId: string,
  payload: { title?: string; generated_content?: string; structured_output?: Record<string, unknown> },
): Promise<AssistantOutput> {
  return apiFetch<AssistantOutput>(`/marketing/ai/assistant/outputs/${outputId}/save`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function archiveAssistantOutput(outputId: string, reason?: string): Promise<AssistantOutput> {
  return apiFetch<AssistantOutput>(`/marketing/ai/assistant/outputs/${outputId}/archive`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}
