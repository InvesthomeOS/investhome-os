import { apiFetch } from '@/lib/api/client';

export type ProjectAssistantCitation = {
  asset_id: string | null;
  document_id: string;
  document_name: string;
  chunk_id: string;
  chunk_reference: string;
  chunk_order: number;
  project_id: string;
  score: number;
  excerpt: string | null;
};

export type ProjectAssistantAssetRef = {
  asset_id: string;
  document_name: string;
  project_id: string;
};

export type ProjectAssistantDocumentRef = {
  document_id: string;
  document_name: string;
  project_id: string;
  asset_id: string | null;
};

export type ProjectAssistantResponse = {
  answer: string;
  confidence: number;
  citations: ProjectAssistantCitation[];
  assets: ProjectAssistantAssetRef[];
  documents: ProjectAssistantDocumentRef[];
  projects: string[];
  search_time_ms: number;
  latency_ms: number;
  conversation_id: string;
  provider: string;
  model: string;
  grounded: boolean;
};

export type ProjectAssistantRequest = {
  question: string;
  project_id: string;
  project_scope?: 'single' | 'multi' | 'global';
  conversation_id?: string | null;
};

export async function askProjectAssistant(
  body: ProjectAssistantRequest,
): Promise<ProjectAssistantResponse> {
  return apiFetch<ProjectAssistantResponse>('/ai/project-assistant', {
    method: 'POST',
    body: JSON.stringify({
      question: body.question,
      project_id: body.project_id,
      project_scope: body.project_scope ?? 'single',
      conversation_id: body.conversation_id ?? undefined,
    }),
  });
}
