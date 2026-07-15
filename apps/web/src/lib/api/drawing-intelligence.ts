import { getApiBaseUrl } from '@/lib/api/client';

export interface DrawingElement {
  id: string;
  element_type: string;
  label: string | null;
  value_text: string | null;
  numeric_value: number | null;
  unit: string | null;
  confidence: string;
}

export interface DrawingSheet {
  id: string;
  sheet_index: number;
  sheet_name: string | null;
  sheet_number: string | null;
  sheet_type: string | null;
  confidence: string | null;
}

export interface DrawingAnnotation {
  id: string;
  label: string | null;
  content: string | null;
  color: string | null;
  is_resolved: boolean;
}

export interface DrawingUnitProposal {
  id: string;
  unit_label: string;
  confidence: string;
  status: string;
  created_unit_id: string | null;
}

export interface DrawingAnalysis {
  document_id: string;
  processing_status: string;
  preview_status: string | null;
  discipline: string | null;
  discipline_confidence: string | null;
  drawing_type: string | null;
  scale_detected: string | null;
  scale_confidence: string | null;
  scale_corrected: string | null;
  sheet_count: number | null;
  summary: string | null;
  summary_en: string | null;
  low_confidence_count: number;
  sheets: DrawingSheet[];
  elements: DrawingElement[];
  annotations: DrawingAnnotation[];
  unit_proposals: DrawingUnitProposal[];
  processing_error: string | null;
}

export interface DrawingProcessingStatus {
  document_id: string;
  processing_status: string;
  preview_status: string | null;
  processing_error: string | null;
}

export async function fetchDrawingAnalysis(documentId: string): Promise<DrawingAnalysis> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/drawing-analysis`, {
    credentials: 'include',
  });
  if (!response.ok) throw new Error('drawing_analysis_fetch_failed');
  return response.json();
}

export async function fetchDrawingProcessingStatus(documentId: string): Promise<DrawingProcessingStatus> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/drawing-processing-status`, {
    credentials: 'include',
  });
  if (!response.ok) throw new Error('drawing_status_fetch_failed');
  return response.json();
}

export function drawingPreviewUrl(documentId: string): string {
  return `${getApiBaseUrl()}/documents/${documentId}/drawing-preview`;
}

export async function correctDrawingScale(documentId: string, scale: string): Promise<DrawingAnalysis> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/drawing-scale`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scale }),
  });
  if (!response.ok) throw new Error('drawing_scale_correction_failed');
  return response.json();
}

export async function askDrawing(
  documentId: string,
  question: string,
  locale: 'en' | 'tr',
): Promise<{ answer: string; grounded: boolean; sources: string[] }> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/drawing-ask`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, locale }),
  });
  if (!response.ok) throw new Error('drawing_ask_failed');
  return response.json();
}

export async function addDrawingAnnotation(
  documentId: string,
  payload: { label?: string; content?: string },
): Promise<DrawingAnnotation> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/drawing-annotations`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('drawing_annotation_failed');
  return response.json();
}

export async function reprocessDrawing(documentId: string): Promise<DrawingProcessingStatus> {
  const response = await fetch(`${getApiBaseUrl()}/documents/${documentId}/drawing-reprocess`, {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('drawing_reprocess_failed');
  return response.json();
}
