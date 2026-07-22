import { apiFetch } from '@/lib/api/client';

import type {
  AIBriefing,
  AIDashboard,
  AIInsight,
  AIPredictionFramework,
  AIRecommendation,
  AISettings,
  AIAnomaly,
  CopilotResponse,
} from '@/workspaces/marketing/schemas/ai';

export async function fetchAIDashboard(): Promise<AIDashboard> {
  return apiFetch<AIDashboard>('/marketing/ai/dashboard');
}

export async function fetchAIInsights(category?: string): Promise<{ items: AIInsight[]; total: number }> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : '';
  return apiFetch<{ items: AIInsight[]; total: number }>(`/marketing/ai/insights${qs}`);
}

export async function fetchAIRecommendations(
  recommendationType?: string,
): Promise<{ items: AIRecommendation[]; total: number }> {
  const qs = recommendationType ? `?recommendation_type=${encodeURIComponent(recommendationType)}` : '';
  return apiFetch<{ items: AIRecommendation[]; total: number }>(`/marketing/ai/recommendations${qs}`);
}

export async function fetchAIPredictions(): Promise<{ frameworks: AIPredictionFramework[] }> {
  return apiFetch<{ frameworks: AIPredictionFramework[] }>('/marketing/ai/predictions');
}

export async function fetchAIAnomalies(): Promise<{ items: AIAnomaly[]; total: number }> {
  return apiFetch<{ items: AIAnomaly[]; total: number }>('/marketing/ai/anomalies');
}

export async function fetchAIBriefing(period = 'weekly'): Promise<{ briefing: AIBriefing }> {
  return apiFetch<{ briefing: AIBriefing }>(`/marketing/ai/briefings?period=${encodeURIComponent(period)}`);
}

export async function fetchAIHealth(): Promise<AIDashboard['marketing_health']> {
  return apiFetch<AIDashboard['marketing_health']>('/marketing/ai/health');
}

export async function fetchAISettings(): Promise<AISettings> {
  return apiFetch<AISettings>('/marketing/ai/settings');
}

export async function updateAISettings(payload: Partial<AISettings>): Promise<AISettings> {
  return apiFetch<AISettings>('/marketing/ai/settings', {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function postCopilotQuery(payload: {
  query: string;
  preset?: string;
  timezone?: string;
}): Promise<CopilotResponse> {
  return apiFetch<CopilotResponse>('/marketing/ai/copilot', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function acceptAIRecommendation(recommendationId: string, notes?: string): Promise<AIRecommendation> {
  return apiFetch<AIRecommendation>(`/marketing/ai/recommendations/${recommendationId}/accept`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}
