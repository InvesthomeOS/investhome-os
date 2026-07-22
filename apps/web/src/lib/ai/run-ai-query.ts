import { fetchExecutiveAiInsights, fetchExecutiveAttention } from '@/lib/api/executive';
import { ApiError } from '@/lib/api/client';
import { postCopilotQuery } from '@/workspaces/marketing/api/ai';

export type AiQueryResult = {
  answer: string;
  source: 'marketing_copilot' | 'executive_l2' | 'placeholder';
  confidence?: string;
  insufficient_data?: boolean;
  placeholder: boolean;
};

function buildPlaceholder(query: string, body: string): AiQueryResult {
  return {
    answer: body,
    source: 'placeholder',
    placeholder: true,
    insufficient_data: true,
  };
}

/** Prefer marketing copilot when available; fall back to executive L2 counts; never invent verified metrics. */
export async function runPlatformAiQuery(
  query: string,
  options?: { preferMarketing?: boolean },
): Promise<AiQueryResult> {
  const trimmed = query.trim();
  if (!trimmed) {
    return buildPlaceholder(query, 'Empty query.');
  }

  if (options?.preferMarketing !== false) {
    try {
      const response = await postCopilotQuery({ query: trimmed });
      return {
        answer: response.answer,
        source: 'marketing_copilot',
        confidence: response.confidence,
        insufficient_data: response.insufficient_data,
        placeholder: Boolean(response.insufficient_data),
      };
    } catch (err) {
      // Fall through for auth / missing route / unavailable provider
      if (err instanceof ApiError && err.status >= 500) {
        // still fall through
      }
    }
  }

  try {
    const [insights, attention] = await Promise.all([
      fetchExecutiveAiInsights({}),
      fetchExecutiveAttention({}).catch(() => null),
    ]);

    const lines = [
      `Executive L2 context (${insights.ai_level}) — rule-based signals, not generative forecasts.`,
      '',
      `Your question: ${trimmed}`,
      '',
      `Priorities: ${insights.priorities.length}`,
      `Risks: ${insights.risks.length}`,
      `Opportunities: ${insights.opportunities.length}`,
      attention ? `Attention items: ${attention.items.length}` : null,
      '',
      'Open Executive Command Center for verified figures and translated insight details.',
      'A connected AI provider is required for full conversational answers. This response does not invent business metrics.',
    ].filter(Boolean) as string[];

    return {
      answer: lines.join('\n'),
      source: 'executive_l2',
      confidence: 'medium',
      placeholder: true,
      insufficient_data: true,
    };
  } catch {
    return buildPlaceholder(
      trimmed,
      [
        'AI providers are not available for this request right now.',
        '',
        `Your question: ${trimmed}`,
        '',
        'Open Executive Command Center or Marketing AI for live module intelligence.',
        'Placeholder responses never invent business metrics as verified facts.',
      ].join('\n'),
    );
  }
}
