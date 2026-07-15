"""Document intelligence API client."""

import { getApiBaseUrl } from '@/lib/api/client';

export interface DocumentAnalysis {
  id: string;
  document_id: string;
  processing_status: string | null;
  extraction_method: string | null;
  detected_language: string | null;
  detected_document_type: string | null;
  classification_confidence: string | null;
  classification_explanation: string | null;
  classification_status: string | null;
  user_document_type: string | null;
  extracted_text_preview: string | null;
  page_count: number | null;
  word_count: number | null;
  ai_summary: string | null;
  ai_summary_en: string | null;
  structured_data: Record<string, unknown> | null;
  extracted_entities: string[];
  extracted_dates: Array<Record<string, unknown>>;
  extracted_amounts: Array<Record<string, unknown>>;
  extracted_parties: string[];
  extracted_obligations: Array<Record<string, unknown>>;
  extracted_risks: Array<{
    severity: string;
    category: string;
    description: string;
    evidence_reference?: string | null;
    recommended_action?: string | null;
  }>;
  model_provider: string | null;
  processing_error: string | null;
  processed_at: string | null;
  disclaimer: string;
}

export interface ProcessingStatusPayload {
  document_id: string;
  processing_status: string;
  analysis_status: string | null;
  processed_at: string | null;
  processing_error: string | null;
}

export interface AskDocumentResponse {
  answer: string;
  found: boolean;
  source_references: Array<{ reference?: string | null }>;
  conversation_id: string;
  message_id: string;
  disclaimer: string;
}

export async function fetchDocumentAnalysis(documentId: string): Promise<DocumentAnalysis> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/analysis`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('analysis_load_failed');
  return response.json() as Promise<DocumentAnalysis>;
}

export async function fetchProcessingStatus(documentId: string): Promise<ProcessingStatusPayload> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/processing-status`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('processing_status_failed');
  return response.json() as Promise<ProcessingStatusPayload>;
}

export async function reprocessDocument(documentId: string): Promise<ProcessingStatusPayload> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/reprocess`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('reprocess_failed');
  return response.json() as Promise<ProcessingStatusPayload>;
}

export async function acceptClassification(documentId: string): Promise<DocumentAnalysis> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/classification`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accept: true }),
  });
  if (!response.ok) throw new Error('classification_failed');
  return response.json() as Promise<DocumentAnalysis>;
}

export async function rejectClassification(documentId: string): Promise<DocumentAnalysis> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/classification`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ accept: false }),
  });
  if (!response.ok) throw new Error('classification_failed');
  return response.json() as Promise<DocumentAnalysis>;
}

export async function askDocument(
  documentId: string,
  question: string,
  language: string,
  conversationId?: string,
): Promise<AskDocumentResponse> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/ask`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, language, conversation_id: conversationId ?? null }),
  });
  if (!response.ok) throw new Error('ask_failed');
  return response.json() as Promise<AskDocumentResponse>;
}

export async function exportDocumentAnalysis(documentId: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/analysis/export`, {
    credentials: 'include',
    cache: 'no-store',
  });
  if (!response.ok) throw new Error('export_failed');
  return response.json() as Promise<Record<string, unknown>>;
}
