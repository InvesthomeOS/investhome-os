import { apiFetch } from '@/lib/api/client';

export type TemplateSummary = {
  id: string;
  name: string;
  template_type: string;
  content_type: string | null;
  channel_category: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type TemplateListResponse = {
  items: TemplateSummary[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
};

export async function fetchTemplates(page = 1, pageSize = 25) {
  return apiFetch<TemplateListResponse>(`/marketing/templates?page=${page}&page_size=${pageSize}`);
}

export async function fetchTemplate(templateId: string) {
  return apiFetch<TemplateSummary & { description: string | null }>(`/marketing/templates/${templateId}`);
}

export async function createTemplate(payload: {
  name: string;
  template_type?: string;
  body_template?: string;
  placeholders?: Array<{ placeholder_key: string; label: string; placeholder_type: string; required?: boolean }>;
}) {
  return apiFetch<{ template: TemplateSummary }>('/marketing/templates', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function validateTemplatePlaceholders(templateId: string, values: Record<string, string>) {
  return apiFetch<{ valid: boolean; errors: string[] }>(`/marketing/templates/${templateId}/validate`, {
    method: 'POST',
    body: JSON.stringify({ values }),
  });
}

export async function previewTemplate(templateId: string, values: Record<string, string>) {
  return apiFetch<{ rendered: string }>(`/marketing/templates/${templateId}/preview`, {
    method: 'POST',
    body: JSON.stringify({ values }),
  });
}

export async function fetchTemplatePlaceholders(templateId: string) {
  return apiFetch<{ items: unknown[] }>(`/marketing/templates/${templateId}/placeholders`);
}
