import type { SensitiveAction } from './ai-views';

export type ActionStatus = 'pending' | 'approved' | 'dismissed' | 'converted' | 'awaiting_approval';

export type AiActionItem = {
  id: string;
  titleKey: string;
  rationaleKey: string;
  explanationKey: string;
  module: string;
  severity: 'information' | 'warning' | 'critical';
  sensitive?: SensitiveAction | null;
  sourceHref: string;
  sourceLabel: string;
  status: ActionStatus;
  createdAt: string;
  confidence: 'low' | 'medium' | 'high';
};

const STORAGE_KEY = 'investhome.ai.g7.actions';

const SEED: Omit<AiActionItem, 'id' | 'createdAt' | 'status'>[] = [
  {
    titleKey: 'followOverdueInvestor',
    rationaleKey: 'followOverdueInvestorWhy',
    explanationKey: 'followOverdueInvestorExplain',
    module: 'investors',
    severity: 'warning',
    sensitive: 'send_email',
    sourceHref: '/dashboard/investors',
    sourceLabel: 'investors',
    confidence: 'medium',
  },
  {
    titleKey: 'reviewPaymentApproval',
    rationaleKey: 'reviewPaymentApprovalWhy',
    explanationKey: 'reviewPaymentApprovalExplain',
    module: 'finance',
    severity: 'critical',
    sensitive: 'approve_payment',
    sourceHref: '/dashboard/finance?view=approvals',
    sourceLabel: 'finance',
    confidence: 'high',
  },
  {
    titleKey: 'advanceOpportunity',
    rationaleKey: 'advanceOpportunityWhy',
    explanationKey: 'advanceOpportunityExplain',
    module: 'crm',
    severity: 'information',
    sensitive: 'change_opportunity_stage',
    sourceHref: '/workspaces/crm',
    sourceLabel: 'crm',
    confidence: 'medium',
  },
  {
    titleKey: 'flagProjectDelay',
    rationaleKey: 'flagProjectDelayWhy',
    explanationKey: 'flagProjectDelayExplain',
    module: 'projects',
    severity: 'warning',
    sensitive: 'change_project_dates',
    sourceHref: '/dashboard/projects?view=issues',
    sourceLabel: 'projects',
    confidence: 'medium',
  },
  {
    titleKey: 'pauseUnderperformingCampaign',
    rationaleKey: 'pauseUnderperformingCampaignWhy',
    explanationKey: 'pauseUnderperformingCampaignExplain',
    module: 'marketing',
    severity: 'warning',
    sensitive: 'pause_campaign',
    sourceHref: '/workspaces/marketing',
    sourceLabel: 'marketing',
    confidence: 'low',
  },
  {
    titleKey: 'reviewDocumentClassification',
    rationaleKey: 'reviewDocumentClassificationWhy',
    explanationKey: 'reviewDocumentClassificationExplain',
    module: 'documents',
    severity: 'information',
    sensitive: null,
    sourceHref: '/dashboard/knowledge?view=review',
    sourceLabel: 'documents',
    confidence: 'high',
  },
];

function nowIso() {
  return new Date().toISOString();
}

function seedItems(): AiActionItem[] {
  return SEED.map((item, i) => ({
    ...item,
    id: `nba-${i + 1}`,
    createdAt: nowIso(),
    status: item.sensitive ? 'awaiting_approval' : 'pending',
  }));
}

export function loadActionQueue(userId?: string | null): AiActionItem[] {
  if (typeof window === 'undefined') return seedItems();
  try {
    const key = userId ? `${STORAGE_KEY}:${userId}` : STORAGE_KEY;
    const raw = localStorage.getItem(key);
    if (!raw) {
      const seeded = seedItems();
      localStorage.setItem(key, JSON.stringify(seeded));
      return seeded;
    }
    return JSON.parse(raw) as AiActionItem[];
  } catch {
    return seedItems();
  }
}

export function saveActionQueue(items: AiActionItem[], userId?: string | null): void {
  if (typeof window === 'undefined') return;
  const key = userId ? `${STORAGE_KEY}:${userId}` : STORAGE_KEY;
  localStorage.setItem(key, JSON.stringify(items));
}

export function updateActionStatus(
  items: AiActionItem[],
  id: string,
  status: ActionStatus,
): AiActionItem[] {
  return items.map((item) => (item.id === id ? { ...item, status } : item));
}
