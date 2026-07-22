import type { ProviderCapabilityStatus } from '@/lib/api/knowledge';

import type { ProviderState } from './ai-views';

export type ProviderRow = {
  id: string;
  nameKey: string;
  capability: string;
  state: ProviderState;
  detailKey: string;
  requiredEnv: string[];
};

function mapCapability(status: ProviderCapabilityStatus | null | undefined): ProviderState {
  if (!status) return 'not_configured';
  if (status.available) return 'operational';
  const reason = (status.reason || '').toLowerCase();
  if (reason.includes('rate') || reason.includes('quota') || reason.includes('429')) {
    return 'rate_limited';
  }
  if (reason.includes('degrad') || reason.includes('partial') || reason.includes('timeout')) {
    return 'degraded';
  }
  if (
    reason.includes('not configured') ||
    reason.includes('missing') ||
    reason.includes('env') ||
    (status.required_env?.length ?? 0) > 0
  ) {
    return 'not_configured';
  }
  return 'unavailable';
}

export function buildProviderRows(input: {
  aiStatus?: ProviderCapabilityStatus | null;
  vectorStatus?: ProviderCapabilityStatus | null;
  ocrStatus?: ProviderCapabilityStatus | null;
  indexingStatus?: ProviderCapabilityStatus | null;
  marketingHealth?: { status?: string; provider?: string; model?: string } | null;
  marketingAvailable?: boolean;
  executiveAvailable?: boolean;
  localHeuristic?: boolean;
}): ProviderRow[] {
  const marketingState: ProviderState = !input.marketingAvailable
    ? 'unavailable'
    : input.marketingHealth?.status === 'degraded'
      ? 'degraded'
      : input.marketingHealth?.status === 'rate_limited'
        ? 'rate_limited'
        : input.marketingAvailable
          ? 'operational'
          : 'not_configured';

  return [
    {
      id: 'local-heuristic',
      nameKey: 'localHeuristic',
      capability: 'platform_fallback',
      state: input.localHeuristic !== false ? 'operational' : 'unavailable',
      detailKey: 'localHeuristicDetail',
      requiredEnv: [],
    },
    {
      id: 'executive-l2',
      nameKey: 'executiveL2',
      capability: 'rule_insights',
      state: input.executiveAvailable ? 'operational' : 'unavailable',
      detailKey: 'executiveL2Detail',
      requiredEnv: [],
    },
    {
      id: 'marketing-copilot',
      nameKey: 'marketingCopilot',
      capability: 'conversational',
      state: marketingState,
      detailKey: 'marketingCopilotDetail',
      requiredEnv: [],
    },
    {
      id: 'document-ai',
      nameKey: 'documentAi',
      capability: 'document_intelligence',
      state: mapCapability(input.aiStatus),
      detailKey: 'documentAiDetail',
      requiredEnv: input.aiStatus?.required_env ?? [],
    },
    {
      id: 'vector-search',
      nameKey: 'vectorSearch',
      capability: 'semantic_search',
      state: mapCapability(input.vectorStatus),
      detailKey: 'vectorSearchDetail',
      requiredEnv: input.vectorStatus?.required_env ?? [],
    },
    {
      id: 'ocr',
      nameKey: 'ocr',
      capability: 'ocr',
      state: mapCapability(input.ocrStatus),
      detailKey: 'ocrDetail',
      requiredEnv: input.ocrStatus?.required_env ?? [],
    },
    {
      id: 'indexing',
      nameKey: 'indexing',
      capability: 'indexing',
      state: mapCapability(input.indexingStatus),
      detailKey: 'indexingDetail',
      requiredEnv: input.indexingStatus?.required_env ?? [],
    },
  ];
}

export function modelStatusFromProviders(rows: ProviderRow[]): {
  modelKey: string;
  state: ProviderState;
  noteKey: string;
} {
  const conversational = rows.find((r) => r.id === 'marketing-copilot');
  const local = rows.find((r) => r.id === 'local-heuristic');
  if (conversational?.state === 'operational') {
    return { modelKey: 'marketingConnected', state: 'operational', noteKey: 'modelMarketingNote' };
  }
  if (local?.state === 'operational') {
    return { modelKey: 'localHeuristicModel', state: 'degraded', noteKey: 'modelLocalNote' };
  }
  return { modelKey: 'none', state: 'unavailable', noteKey: 'modelUnavailableNote' };
}
