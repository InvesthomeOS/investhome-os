export type PromptCategory =
  | 'sales'
  | 'marketing'
  | 'finance'
  | 'investor'
  | 'projects'
  | 'executive'
  | 'documents';

export type PromptDefinition = {
  id: string;
  category: PromptCategory;
  /** i18n key under ai.prompts.items.* */
  titleKey: string;
  promptKey: string;
  favoriteDefault?: boolean;
};

export const PROMPT_LIBRARY: PromptDefinition[] = [
  {
    id: 'exec-priorities',
    category: 'executive',
    titleKey: 'execPriorities',
    promptKey: 'execPrioritiesPrompt',
    favoriteDefault: true,
  },
  {
    id: 'docs-summarize',
    category: 'documents',
    titleKey: 'docsSummarize',
    promptKey: 'docsSummarizePrompt',
    favoriteDefault: true,
  },
  {
    id: 'docs-review',
    category: 'documents',
    titleKey: 'docsReview',
    promptKey: 'docsReviewPrompt',
  },
  {
    id: 'exec-summary',
    category: 'executive',
    titleKey: 'execSummary',
    promptKey: 'execSummaryPrompt',
  },
  {
    id: 'sales-pipeline',
    category: 'sales',
    titleKey: 'salesPipeline',
    promptKey: 'salesPipelinePrompt',
    favoriteDefault: true,
  },
  {
    id: 'sales-followup',
    category: 'sales',
    titleKey: 'salesFollowup',
    promptKey: 'salesFollowupPrompt',
  },
  {
    id: 'mkt-performance',
    category: 'marketing',
    titleKey: 'mktPerformance',
    promptKey: 'mktPerformancePrompt',
    favoriteDefault: true,
  },
  {
    id: 'mkt-next-actions',
    category: 'marketing',
    titleKey: 'mktNextActions',
    promptKey: 'mktNextActionsPrompt',
  },
  {
    id: 'fin-overview',
    category: 'finance',
    titleKey: 'finOverview',
    promptKey: 'finOverviewPrompt',
  },
  {
    id: 'fin-cash',
    category: 'finance',
    titleKey: 'finCash',
    promptKey: 'finCashPrompt',
  },
  {
    id: 'inv-activity',
    category: 'investor',
    titleKey: 'invActivity',
    promptKey: 'invActivityPrompt',
    favoriteDefault: true,
  },
  {
    id: 'inv-brief',
    category: 'investor',
    titleKey: 'invBrief',
    promptKey: 'invBriefPrompt',
  },
  {
    id: 'prj-risks',
    category: 'projects',
    titleKey: 'prjRisks',
    promptKey: 'prjRisksPrompt',
    favoriteDefault: true,
  },
  {
    id: 'prj-status',
    category: 'projects',
    titleKey: 'prjStatus',
    promptKey: 'prjStatusPrompt',
  },
  {
    id: 'overdue-tasks',
    category: 'executive',
    titleKey: 'overdueTasks',
    promptKey: 'overdueTasksPrompt',
  },
];

export const PROMPT_CATEGORIES: PromptCategory[] = [
  'executive',
  'sales',
  'marketing',
  'finance',
  'investor',
  'projects',
  'documents',
];

const FAVORITES_KEY = 'investhome.ai.promptFavorites';

export function loadFavoritePromptIds(): Set<string> {
  if (typeof window === 'undefined') {
    return new Set(PROMPT_LIBRARY.filter((p) => p.favoriteDefault).map((p) => p.id));
  }
  try {
    const raw = localStorage.getItem(FAVORITES_KEY);
    if (!raw) {
      return new Set(PROMPT_LIBRARY.filter((p) => p.favoriteDefault).map((p) => p.id));
    }
    const parsed = JSON.parse(raw) as string[];
    return new Set(parsed);
  } catch {
    return new Set(PROMPT_LIBRARY.filter((p) => p.favoriteDefault).map((p) => p.id));
  }
}

export function saveFavoritePromptIds(ids: Set<string>): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(FAVORITES_KEY, JSON.stringify([...ids]));
}

export function toggleFavoritePrompt(id: string): Set<string> {
  const next = loadFavoritePromptIds();
  if (next.has(id)) next.delete(id);
  else next.add(id);
  saveFavoritePromptIds(next);
  return next;
}

export type AiActionKind =
  | 'summarize'
  | 'analyze'
  | 'generate'
  | 'recommend'
  | 'explain'
  | 'predict';

export type AiModuleContext =
  | 'crm'
  | 'marketing'
  | 'investor'
  | 'projects'
  | 'finance'
  | 'sales'
  | 'executive'
  | 'documents'
  | 'general';

export const MODULE_AI_ACTIONS: Record<AiModuleContext, AiActionKind[]> = {
  crm: ['summarize', 'generate', 'recommend', 'explain'],
  marketing: ['summarize', 'analyze', 'generate', 'recommend', 'predict'],
  investor: ['summarize', 'analyze', 'generate', 'recommend'],
  projects: ['summarize', 'analyze', 'recommend', 'explain', 'predict'],
  finance: ['summarize', 'analyze', 'explain', 'predict'],
  sales: ['summarize', 'analyze', 'generate', 'recommend', 'predict'],
  executive: ['summarize', 'analyze', 'recommend', 'explain'],
  documents: ['summarize', 'analyze', 'explain', 'recommend'],
  general: ['summarize', 'generate', 'recommend', 'explain'],
};
