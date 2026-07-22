'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { appendAiHistory, loadAiHistory, type AiHistoryEntry } from '@/lib/ai/ai-history';
import {
  canManageAiWorkspaceSettings,
  canUseAiWorkspace,
  canViewAiWorkspace,
} from '@/lib/ai/ai-permissions';
import { runPlatformAiQuery } from '@/lib/ai/run-ai-query';
import {
  DEFAULT_AI_SETTINGS,
  loadAiSettings,
  saveAiSettings,
  type AiWorkspaceSettings,
} from '@/lib/ai/ai-settings-store';
import {
  loadFavoritePromptIds,
  PROMPT_LIBRARY,
  toggleFavoritePrompt,
  type PromptDefinition,
} from '@/lib/ai/prompt-library';
import {
  fetchExecutiveAiInsights,
  fetchExecutiveApprovals,
  fetchExecutiveAttention,
  fetchExecutiveSummary,
  type AiInsightItem,
  type AttentionItem,
  type SummaryCard,
} from '@/lib/api/executive';
import { fetchFinanceStats } from '@/lib/api/finance';
import { fetchInvestorStats } from '@/lib/api/investors';
import { fetchKnowledgeOverview, knowledgeAiSearch } from '@/lib/api/knowledge';
import { fetchProjectStats } from '@/lib/api/projects';
import { fetchGlobalSearch, searchResultHref } from '@/lib/api/search';
import { useAuth } from '@/lib/auth/auth-context';
import { fetchAIDashboard, fetchAIHealth } from '@/workspaces/marketing/api/ai';
import { fetchCrmDashboard } from '@/workspaces/crm/api/crm';

import {
  loadActionQueue,
  saveActionQueue,
  updateActionStatus,
  type AiActionItem,
} from './action-queue';
import { AI_VIEWS, parseView, VIEW_DATA_KIND, type AiViewId } from './ai-views';
import { sparkFromBase } from './derive';
import {
  ActionCenterPanel,
  ActivityLogPanel,
  AiSearchPanel,
  ApprovalGateModal,
  CommandCenterPanel,
  CopilotPanel,
  DocumentIntelPanel,
  DomainIntelPanel,
  ForecastsPanel,
  MeetingIntelPanel,
  MorningBriefPanel,
  PromptLibraryPanel,
  ProviderStatusPanel,
  RiskCenterPanel,
  SettingsPanel,
} from './domain-panels';
import { buildProviderRows, type ProviderRow } from './provider-status';

import './ai-g7.css';

const LABEL_KEYS = [
  'liveTag',
  'partialTag',
  'demoTag',
  'blockedTag',
  'not_configuredTag',
  'empty',
  'loading',
  'commandNote',
  'kpiPriorities',
  'kpiRisks',
  'kpiCritical',
  'kpiWarnings',
  'kpiOpportunities',
  'kpiProjects',
  'kpiInvestors',
  'kpiPipeline',
  'chartAttentionTrend',
  'chartSignalMix',
  'signalFeedTitle',
  'signalFeedSubtitle',
  'signalItem',
  'openSource',
  'explainRuleBased',
  'briefTitle',
  'briefSubtitle',
  'briefExecSummary',
  'briefExecSummaryBody',
  'evidenceLink',
  'signalCount',
  'theme.changed.title',
  'theme.changed.body',
  'theme.decisions.title',
  'theme.decisions.body',
  'theme.overdue.title',
  'theme.overdue.body',
  'theme.atRisk.title',
  'theme.atRisk.body',
  'theme.moneyIn.title',
  'theme.moneyIn.body',
  'theme.moneyOut.title',
  'theme.moneyOut.body',
  'theme.investorFollowup.title',
  'theme.investorFollowup.body',
  'theme.projectDelay.title',
  'theme.projectDelay.body',
  'theme.campaigns.title',
  'theme.campaigns.body',
  'theme.documents.title',
  'theme.documents.body',
  'theme.meetings.title',
  'theme.meetings.body',
  'theme.priorities.title',
  'theme.priorities.body',
  'copilotTitle',
  'copilotSubtitle',
  'copilotPermissions',
  'copilotEmpty',
  'copilotPlaceholder',
  'clearChat',
  'ask',
  'thinking',
  'placeholderBadge',
  'source',
  'localeHint',
  'copilotChip.priorities',
  'copilotChip.pipeline',
  'copilotChip.investors',
  'copilotChip.risks',
  'copilotPrompt.priorities',
  'copilotPrompt.pipeline',
  'copilotPrompt.investors',
  'copilotPrompt.risks',
  'actionsTitle',
  'actionsSubtitle',
  'actionsApprovalBanner',
  'actionsEmpty',
  'whyRecommended',
  'confidence',
  'sensitiveLabel',
  'accept',
  'dismiss',
  'convertTask',
  'requestApproval',
  'awaitingApproval',
  'nba.followOverdueInvestor',
  'nba.followOverdueInvestorWhy',
  'nba.followOverdueInvestorExplain',
  'nba.reviewPaymentApproval',
  'nba.reviewPaymentApprovalWhy',
  'nba.reviewPaymentApprovalExplain',
  'nba.advanceOpportunity',
  'nba.advanceOpportunityWhy',
  'nba.advanceOpportunityExplain',
  'nba.flagProjectDelay',
  'nba.flagProjectDelayWhy',
  'nba.flagProjectDelayExplain',
  'nba.pauseUnderperformingCampaign',
  'nba.pauseUnderperformingCampaignWhy',
  'nba.pauseUnderperformingCampaignExplain',
  'nba.reviewDocumentClassification',
  'nba.reviewDocumentClassificationWhy',
  'nba.reviewDocumentClassificationExplain',
  'sensitive.send_email',
  'sensitive.change_investor_stage',
  'sensitive.change_opportunity_stage',
  'sensitive.approve_payment',
  'sensitive.release_payment',
  'sensitive.create_legal_document',
  'sensitive.modify_contract',
  'sensitive.modify_financial_record',
  'sensitive.delete_record',
  'sensitive.change_project_dates',
  'sensitive.change_budget',
  'sensitive.publish_content',
  'sensitive.pause_campaign',
  'sensitive.initiate_automation',
  'crmTitle',
  'crmSubtitle',
  'investorTitle',
  'investorSubtitle',
  'projectTitle',
  'projectSubtitle',
  'financeTitle',
  'financeSubtitle',
  'marketingTitle',
  'marketingSubtitle',
  'openWorkspace',
  'recommendationsTitle',
  'recommendationsSubtitle',
  'explainDomain',
  'docsTitle',
  'docsSubtitle',
  'docsHumanReview',
  'docsEmpty',
  'colDocument',
  'colStatus',
  'colConfidence',
  'colAction',
  'requestHumanReview',
  'meetingsTitle',
  'meetingsSubtitle',
  'meetingsNoAutoSend',
  'meetingBoard',
  'meetingInvestor',
  'meetingSite',
  'openPrepBrief',
  'draftNotes',
  'forecastTitle',
  'forecastSubtitle',
  'forecastHonesty',
  'forecastMidline',
  'forecastBands',
  'riskTitle',
  'riskSubtitle',
  'riskEmpty',
  'explainRisk',
  'mitigate',
  'searchTitle',
  'searchSubtitle',
  'searchPlaceholder',
  'search',
  'searching',
  'searchEmpty',
  'promptsTitle',
  'promptsSubtitle',
  'promptsEmpty',
  'runPrompt',
  'favorite',
  'unfavorite',
  'promptCat.all',
  'promptCat.favorites',
  'promptCat.executive',
  'promptCat.sales',
  'promptCat.marketing',
  'promptCat.finance',
  'promptCat.investor',
  'promptCat.projects',
  'promptCat.documents',
  'promptItem.execPriorities',
  'promptItem.docsSummarize',
  'promptItem.docsReview',
  'promptItem.execSummary',
  'promptItem.salesPipeline',
  'promptItem.salesFollowup',
  'promptItem.mktPerformance',
  'promptItem.mktNextActions',
  'promptItem.finOverview',
  'promptItem.finCash',
  'promptItem.invActivity',
  'promptItem.invBrief',
  'promptItem.prjRisks',
  'promptItem.prjStatus',
  'promptItem.overdueTasks',
  'activityTitle',
  'activitySubtitle',
  'activityLocalNote',
  'activityEmpty',
  'settingsTitle',
  'settingsSubtitle',
  'settingsNoSecrets',
  'settingsReadOnly',
  'settingsModel',
  'settingsProvider',
  'settingsLanguage',
  'settingsLength',
  'modelDefault',
  'modelLocal',
  'providerLocal',
  'providerAzure',
  'languageAuto',
  'lengthConcise',
  'lengthBalanced',
  'lengthDetailed',
  'allowExternal',
  'shareOrgContext',
  'saveSettings',
  'savedLocal',
  'providersTitle',
  'providersSubtitle',
  'modelStatusTitle',
  'marketingConnected',
  'localHeuristicModel',
  'none',
  'modelMarketingNote',
  'modelLocalNote',
  'modelUnavailableNote',
  'colProvider',
  'colCapability',
  'colState',
  'colDetail',
  'localHeuristic',
  'executiveL2',
  'marketingCopilot',
  'documentAi',
  'vectorSearch',
  'ocr',
  'indexing',
  'localHeuristicDetail',
  'executiveL2Detail',
  'marketingCopilotDetail',
  'documentAiDetail',
  'vectorSearchDetail',
  'ocrDetail',
  'indexingDetail',
  'providerState.operational',
  'providerState.degraded',
  'providerState.unavailable',
  'providerState.not_configured',
  'providerState.rate_limited',
  'approvalTitle',
  'approvalBody',
  'approvalAck',
  'approvalConfirm',
  'cancel',
  'nav.command_center',
  'nav.morning_brief',
  'nav.copilot',
  'nav.action_center',
  'nav.crm_intel',
  'nav.investor_intel',
  'nav.project_intel',
  'nav.finance_intel',
  'nav.marketing_intel',
  'nav.document_intel',
  'nav.meeting_intel',
  'nav.forecasts',
  'nav.risk_center',
  'nav.ai_search',
  'nav.prompt_library',
  'nav.activity_log',
  'nav.settings',
  'nav.provider_status',
  'title',
  'subtitle',
  'openCopilot',
  'accessDenied',
  'toastApproved',
  'toastDismissed',
  'toastConverted',
  'toastReviewRequested',
  'toastApprovalRecorded',
  'unavailable',
] as const;

function buildLabels(t: (key: string) => string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const key of LABEL_KEYS) {
    try {
      out[key] = t(key);
    } catch {
      out[key] = key;
    }
  }
  return out;
}

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  placeholder?: boolean;
  sources?: Array<{ href: string; label: string }>;
};

export function AiG7Workspace() {
  const t = useTranslations('ai.g7');
  const tRoot = useTranslations('ai');
  const tPrompts = useTranslations('ai.prompts.items');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const view = parseView(searchParams.get('view'));
  const labels = useMemo(() => buildLabels((key) => t(key as never)), [t]);

  const setView = (next: AiViewId) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'command_center') params.delete('view');
    else params.set('view', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const canView = canViewAiWorkspace(user);
  const canUse = canUseAiWorkspace(user);
  const canManage = canManageAiWorkspaceSettings(user);

  const [loading, setLoading] = useState(true);
  const [insights, setInsights] = useState<{
    priorities: AiInsightItem[];
    risks: AiInsightItem[];
    opportunities: AiInsightItem[];
    ai_level: string;
  } | null>(null);
  const [attention, setAttention] = useState<AttentionItem[]>([]);
  const [summaryCards, setSummaryCards] = useState<SummaryCard[]>([]);
  const [approvalsCount, setApprovalsCount] = useState(0);
  const [actions, setActions] = useState<AiActionItem[]>([]);
  const [history, setHistory] = useState<AiHistoryEntry[]>([]);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [promptCategory, setPromptCategory] = useState('all');
  const [settings, setSettings] = useState<AiWorkspaceSettings>(DEFAULT_AI_SETTINGS);
  const [settingsSaved, setSettingsSaved] = useState(false);
  const [providerRows, setProviderRows] = useState<ProviderRow[]>([]);
  const [toast, setToast] = useState<string | null>(null);
  const [approvalId, setApprovalId] = useState<string | null>(null);

  const [chat, setChat] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatPending, setChatPending] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchPending, setSearchPending] = useState(false);
  const [searchResults, setSearchResults] = useState<
    Array<{ id: string; title: string; snippet: string; href: string; source: string }>
  >([]);

  const [crmMetrics, setCrmMetrics] = useState<Array<{ label: string; value: string; spark?: number[] }>>([]);
  const [investorMetrics, setInvestorMetrics] = useState<Array<{ label: string; value: string; spark?: number[] }>>([]);
  const [projectMetrics, setProjectMetrics] = useState<Array<{ label: string; value: string; spark?: number[] }>>([]);
  const [financeMetrics, setFinanceMetrics] = useState<Array<{ label: string; value: string; spark?: number[] }>>([]);
  const [marketingMetrics, setMarketingMetrics] = useState<Array<{ label: string; value: string; spark?: number[] }>>([]);
  const [docRows, setDocRows] = useState<Array<{ id: string; title: string; status: string; confidence?: string | null }>>([]);
  const [forecastBase, setForecastBase] = useState(100);

  useEffect(() => {
    setFavorites(loadFavoritePromptIds());
    setHistory(loadAiHistory(null, user?.id));
    setActions(loadActionQueue(user?.id));
    setSettings(loadAiSettings());
  }, [user?.id]);

  const loadCore = useCallback(async () => {
    setLoading(true);
    const withTimeout = <T,>(promise: Promise<T>, fallback: T, ms = 8_000): Promise<T> =>
      Promise.race([
        promise,
        new Promise<T>((resolve) => {
          window.setTimeout(() => resolve(fallback), ms);
        }),
      ]);
    try {
      const [ai, att, sum, approvals] = await Promise.all([
        withTimeout(fetchExecutiveAiInsights({}).catch(() => null), null),
        withTimeout(
          fetchExecutiveAttention({}).catch(() => ({ items: [] as AttentionItem[] })),
          { items: [] as AttentionItem[] },
        ),
        withTimeout(
          fetchExecutiveSummary({}).catch(() => ({ cards: [] as SummaryCard[] })),
          { cards: [] as SummaryCard[] },
        ),
        withTimeout(fetchExecutiveApprovals({}).catch(() => ({ items: [] })), { items: [] }),
      ]);
      if (ai) setInsights(ai);
      setAttention(att.items);
      setSummaryCards(sum.cards);
      setApprovalsCount(approvals.items?.length ?? 0);

      const overdue = att.items.filter((a) => (a.age_days ?? 0) > 0 || a.severity === 'critical').length;

      // Keep domain fan-out modest so Docker web is not overwhelmed.
      const domainLoads = await Promise.allSettled([
        withTimeout(fetchCrmDashboard().catch(() => null), null, 6_000),
        withTimeout(fetchInvestorStats().catch(() => null), null, 6_000),
        withTimeout(fetchProjectStats().catch(() => null), null, 6_000),
        withTimeout(fetchFinanceStats().catch(() => null), null, 6_000),
        withTimeout(fetchAIDashboard().catch(() => null), null, 6_000),
        withTimeout(fetchAIHealth().catch(() => null), null, 6_000),
        withTimeout(fetchKnowledgeOverview().catch(() => null), null, 6_000),
      ]);

      const crm = domainLoads[0].status === 'fulfilled' ? domainLoads[0].value : null;
      const inv = domainLoads[1].status === 'fulfilled' ? domainLoads[1].value : null;
      const prj = domainLoads[2].status === 'fulfilled' ? domainLoads[2].value : null;
      const fin = domainLoads[3].status === 'fulfilled' ? domainLoads[3].value : null;
      const mkt = domainLoads[4].status === 'fulfilled' ? domainLoads[4].value : null;
      const mktHealth = domainLoads[5].status === 'fulfilled' ? domainLoads[5].value : null;
      const knowledge = domainLoads[6].status === 'fulfilled' ? domainLoads[6].value : null;

      if (crm) {
        const alerts = crm.relationship_alerts?.length ?? 0;
        const tasks = crm.upcoming_tasks?.length ?? 0;
        const meetings = crm.todays_meetings?.length ?? 0;
        setCrmMetrics([
          { label: 'Alerts', value: String(alerts), spark: sparkFromBase(alerts || 1) },
          { label: 'Tasks', value: String(tasks), spark: sparkFromBase(tasks || 1) },
          { label: 'Meetings', value: String(meetings), spark: sparkFromBase(meetings || 1) },
        ]);
      } else {
        setCrmMetrics([{ label: '—', value: '—', spark: sparkFromBase(1) }]);
      }

      if (inv) {
        setInvestorMetrics([
          { label: 'Investors', value: String(inv.active || inv.total || '—'), spark: sparkFromBase(inv.active || 1) },
          { label: 'Invested', value: String(inv.invested || 0), spark: sparkFromBase(inv.invested || 1) },
        ]);
      }

      if (prj) {
        setProjectMetrics([
          { label: 'Projects', value: String(prj.active || prj.total || '—'), spark: sparkFromBase(prj.active || 1) },
          { label: 'Construction', value: String(prj.under_construction || 0), spark: sparkFromBase(prj.under_construction || 1) },
        ]);
      }

      if (fin) {
        const cash = Object.values(fin.total_cash ?? {})[0] ?? '—';
        setFinanceMetrics([
          { label: 'Cash', value: String(cash), spark: sparkFromBase(50) },
          {
            label: 'AR',
            value: String(Object.values(fin.pending_receivables ?? {})[0] ?? '—'),
            spark: sparkFromBase(40),
          },
        ]);
        setForecastBase(80 + overdue * 5);
      }

      if (mkt) {
        const score = mkt.marketing_health?.overall_score;
        setMarketingMetrics([
          {
            label: 'Health',
            value: score != null ? String(score) : mkt.marketing_health?.overall_status || '—',
            spark: sparkFromBase(score ?? 3),
          },
          {
            label: 'Insights',
            value: String(mkt.critical_insights?.length ?? 0),
            spark: sparkFromBase(mkt.critical_insights?.length || 1),
          },
        ]);
      }

      if (knowledge) {
        const awaiting = knowledge.awaiting_review?.value ?? 0;
        setDocRows([
          {
            id: 'review-queue',
            title: 'Review queue',
            status: knowledge.awaiting_review?.available ? `awaiting:${awaiting}` : 'unavailable',
            confidence: knowledge.ai_status?.available ? 'provider-ok' : 'provider-gap',
          },
        ]);
      }

      const healthStatus =
        mktHealth && typeof mktHealth === 'object' && 'overall_status' in mktHealth
          ? String((mktHealth as { overall_status?: string }).overall_status || '')
          : mkt?.marketing_health?.overall_status;

      setProviderRows(
        buildProviderRows({
          aiStatus: knowledge?.ai_status,
          vectorStatus: knowledge?.vector_search_status,
          ocrStatus: knowledge?.ocr_status,
          indexingStatus: knowledge?.indexing_status,
          marketingHealth: healthStatus ? { status: healthStatus.toLowerCase() } : null,
          marketingAvailable: Boolean(mkt || mktHealth),
          executiveAvailable: Boolean(ai),
          localHeuristic: true,
        }),
      );
      void overdue;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!canView) return;
    void loadCore();
  }, [canView, loadCore]);

  const domainRecs = useMemo(
    () => ({
      crm: [
        {
          title: labels['nba.advanceOpportunity'] || 'Advance opportunity',
          body: labels['nba.advanceOpportunityWhy'] || '',
          href: '/workspaces/crm',
          severity: 'info',
        },
      ],
      investor: [
        {
          title: labels['nba.followOverdueInvestor'] || 'Investor follow-up',
          body: labels['nba.followOverdueInvestorWhy'] || '',
          href: '/dashboard/investors',
          severity: 'warn',
        },
      ],
      project: [
        {
          title: labels['nba.flagProjectDelay'] || 'Project delay',
          body: labels['nba.flagProjectDelayWhy'] || '',
          href: '/dashboard/projects?view=issues',
          severity: 'warn',
        },
      ],
      finance: [
        {
          title: labels['nba.reviewPaymentApproval'] || 'Payment approval',
          body: labels['nba.reviewPaymentApprovalWhy'] || '',
          href: '/dashboard/finance?view=approvals',
          severity: 'critical',
        },
      ],
      marketing: [
        {
          title: labels['nba.pauseUnderperformingCampaign'] || 'Campaign',
          body: labels['nba.pauseUnderperformingCampaignWhy'] || '',
          href: '/workspaces/marketing',
          severity: 'warn',
        },
      ],
    }),
    [labels],
  );

  const persistActions = (next: AiActionItem[]) => {
    setActions(next);
    saveActionQueue(next, user?.id);
  };

  const showToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2500);
  };

  async function askCopilot(query: string) {
    const trimmed = query.trim();
    if (!trimmed || chatPending || !canUse) return;
    setChat((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: trimmed }]);
    setChatInput('');
    setChatPending(true);
    try {
      const result = await runPlatformAiQuery(trimmed);
      const sources = [
        { href: '/dashboard/executive', label: 'executive' },
        { href: '/workspaces/marketing/ai', label: 'marketing-ai' },
      ];
      if (result.source === 'executive_l2') {
        sources.length = 0;
        sources.push({ href: '/dashboard/executive', label: 'executive-l2' });
      }
      const assistant: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.answer,
        placeholder: result.placeholder,
        sources,
      };
      setChat((prev) => [...prev, assistant]);
      appendAiHistory(
        {
          title: trimmed.slice(0, 80),
          prompt: trimmed,
          response: result.answer,
          source: 'copilot',
          module: 'ai_workspace',
          placeholder: result.placeholder,
        },
        null,
        user?.id,
      );
      setHistory(loadAiHistory(null, user?.id));
    } finally {
      setChatPending(false);
    }
  }

  async function runSearch() {
    const q = searchQuery.trim();
    if (!q) return;
    setSearchPending(true);
    try {
      const results: Array<{ id: string; title: string; snippet: string; href: string; source: string }> = [];
      try {
        const global = await fetchGlobalSearch(q, { limit: 20 });
        for (const group of global.groups ?? []) {
          for (const item of group.items ?? []) {
            results.push({
              id: item.entity_id,
              title: item.title || q,
              snippet: item.subtitle || item.preview || '',
              href: searchResultHref(item),
              source: item.module || group.entity_type,
            });
          }
        }
      } catch {
        /* fall through */
      }
      try {
        const ai = await knowledgeAiSearch(q, 20);
        for (const hit of ai.hits ?? []) {
          results.push({
            id: hit.document_id || crypto.randomUUID(),
            title: hit.title || 'Document',
            snippet: hit.snippet || '',
            href: hit.document_id ? `/dashboard/knowledge?document=${hit.document_id}` : '/dashboard/knowledge',
            source: 'knowledge-ai',
          });
        }
      } catch {
        /* knowledge AI may be unavailable */
      }
      if (results.length === 0) {
        results.push({
          id: 'fallback-exec',
          title: labels.searchEmpty || 'No AI hits — open executive signals',
          snippet: q,
          href: '/dashboard/executive',
          source: 'fallback',
        });
      }
      setSearchResults(results);
    } finally {
      setSearchPending(false);
    }
  }

  const risks = useMemo(() => {
    const fromInsights = (insights?.risks ?? []).map((r, i) => ({
      id: `risk-${i}`,
      title: r.title_key,
      body: r.description_key,
      severity: r.severity || 'warning',
      href: `/${r.link_module}`.startsWith('/dashboard') ? `/${r.link_module}` : `/dashboard/${r.link_module}`,
    }));
    const fromAttention = attention
      .filter((a) => a.severity === 'critical' || a.severity === 'warning')
      .slice(0, 8)
      .map((a, i) => ({
        id: `att-${i}`,
        title: a.title_key,
        body: a.related_label || a.description_key,
        severity: a.severity,
        href: `/dashboard/${a.link_module}`,
      }));
    return [...fromInsights, ...fromAttention].slice(0, 12);
  }, [insights, attention]);

  const approvalAction = actions.find((a) => a.id === approvalId);

  if (authLoading) {
    return (
      <main className="ai-g7" data-testid="ai-g7-workspace">
        <div className="ai-g7__empty">{labels.loading || tRoot('loading')}</div>
      </main>
    );
  }

  if (!canView) {
    return (
      <main className="ai-g7" data-testid="ai-g7-workspace">
        <div className="ai-g7__empty">{labels.accessDenied || tRoot('accessDenied')}</div>
      </main>
    );
  }

  return (
    <main className="ai-g7" data-ai-workspace data-testid="ai-g7-workspace">
      <header className="ai-g7__top">
        <div>
          <p className="ai-g7__eyebrow">{tRoot('eyebrow')}</p>
          <h1 className="ai-g7__title">{labels.title}</h1>
          <p className="ai-g7__subtitle">{labels.subtitle}</p>
        </div>
        <div className="ai-g7__top-actions">
          <button type="button" className="ai-g7__btn ai-g7__btn--primary" onClick={() => setView('copilot')}>
            {labels.openCopilot}
          </button>
        </div>
      </header>

      <nav className="ai-g7__nav" aria-label={tRoot('nav.aria')}>
        {AI_VIEWS.map((id) => (
          <button
            key={id}
            type="button"
            className={`ai-g7__nav-btn${view === id ? ' is-active' : ''}`}
            data-testid={`ai-g7-nav-${id}`}
            onClick={() => setView(id)}
          >
            {labels[`nav.${id}`] || id}
          </button>
        ))}
      </nav>

      <div className="ai-g7__body">
        {loading ? <div className="ai-g7__empty">{labels.loading || tRoot('loading')}</div> : null}
        {toast ? (
          <div className="ai-g7__banner ai-g7__banner--info" role="status">
            {toast}
          </div>
        ) : null}

        {!loading && view === 'command_center' ? (
          <CommandCenterPanel
            labels={labels}
            locale={locale}
            summaryCards={summaryCards}
            attention={attention}
            insights={insights}
            onDrill={(href) => {
              if (href.includes('view=')) {
                const v = new URL(href, 'http://local').searchParams.get('view');
                if (v && (AI_VIEWS as readonly string[]).includes(v)) setView(v as AiViewId);
                else router.push(href as Route);
              } else router.push(href as Route);
            }}
          />
        ) : null}

        {!loading && view === 'morning_brief' ? (
          <MorningBriefPanel
            labels={labels}
            locale={locale}
            attention={attention}
            insights={insights}
            approvalsCount={approvalsCount}
            overdueCount={attention.filter((a) => (a.age_days ?? 0) > 0).length}
          />
        ) : null}

        {!loading && view === 'copilot' ? (
          <CopilotPanel
            labels={labels}
            locale={locale}
            canUse={canUse}
            pending={chatPending}
            messages={chat}
            input={chatInput}
            onInput={setChatInput}
            onAsk={(q) => void askCopilot(q)}
            onClear={() => setChat([])}
          />
        ) : null}

        {!loading && view === 'action_center' ? (
          <ActionCenterPanel
            labels={labels}
            locale={locale}
            items={actions}
            onApprove={(id) => {
              persistActions(updateActionStatus(actions, id, 'approved'));
              showToast(labels.toastApproved ?? 'OK');
            }}
            onDismiss={(id) => {
              persistActions(updateActionStatus(actions, id, 'dismissed'));
              showToast(labels.toastDismissed ?? 'OK');
            }}
            onConvert={(id) => {
              persistActions(updateActionStatus(actions, id, 'converted'));
              showToast(labels.toastConverted ?? 'OK');
            }}
            onRequestApproval={(id) => setApprovalId(id)}
          />
        ) : null}

        {!loading && view === 'crm_intel' ? (
          <DomainIntelPanel
            labels={labels}
            locale={locale}
            viewId="crm_intel"
            titleKey="crmTitle"
            subtitleKey="crmSubtitle"
            kind={VIEW_DATA_KIND.crm_intel}
            metrics={crmMetrics}
            items={domainRecs.crm || []}
            href="/workspaces/crm"
          />
        ) : null}

        {!loading && view === 'investor_intel' ? (
          <DomainIntelPanel
            labels={labels}
            locale={locale}
            viewId="investor_intel"
            titleKey="investorTitle"
            subtitleKey="investorSubtitle"
            kind={VIEW_DATA_KIND.investor_intel}
            metrics={investorMetrics}
            items={domainRecs.investor || []}
            href="/dashboard/investors"
          />
        ) : null}

        {!loading && view === 'project_intel' ? (
          <DomainIntelPanel
            labels={labels}
            locale={locale}
            viewId="project_intel"
            titleKey="projectTitle"
            subtitleKey="projectSubtitle"
            kind={VIEW_DATA_KIND.project_intel}
            metrics={projectMetrics}
            items={domainRecs.project || []}
            href="/dashboard/projects"
          />
        ) : null}

        {!loading && view === 'finance_intel' ? (
          <DomainIntelPanel
            labels={labels}
            locale={locale}
            viewId="finance_intel"
            titleKey="financeTitle"
            subtitleKey="financeSubtitle"
            kind={VIEW_DATA_KIND.finance_intel}
            metrics={financeMetrics}
            items={domainRecs.finance || []}
            href="/dashboard/finance"
          />
        ) : null}

        {!loading && view === 'marketing_intel' ? (
          <DomainIntelPanel
            labels={labels}
            locale={locale}
            viewId="marketing_intel"
            titleKey="marketingTitle"
            subtitleKey="marketingSubtitle"
            kind={VIEW_DATA_KIND.marketing_intel}
            metrics={marketingMetrics}
            items={domainRecs.marketing || []}
            href="/workspaces/marketing"
          />
        ) : null}

        {!loading && view === 'document_intel' ? (
          <DocumentIntelPanel
            labels={labels}
            locale={locale}
            docs={docRows}
            onRequestReview={() => showToast(labels.toastReviewRequested ?? 'OK')}
          />
        ) : null}

        {!loading && view === 'meeting_intel' ? <MeetingIntelPanel labels={labels} locale={locale} /> : null}

        {!loading && view === 'forecasts' ? (
          <ForecastsPanel labels={labels} locale={locale} base={forecastBase} />
        ) : null}

        {!loading && view === 'risk_center' ? (
          <RiskCenterPanel labels={labels} locale={locale} risks={risks} />
        ) : null}

        {!loading && view === 'ai_search' ? (
          <AiSearchPanel
            labels={labels}
            locale={locale}
            query={searchQuery}
            onQuery={setSearchQuery}
            pending={searchPending}
            results={searchResults}
            onSearch={() => void runSearch()}
          />
        ) : null}

        {!loading && view === 'prompt_library' ? (
          <PromptLibraryPanel
            labels={labels}
            locale={locale}
            prompts={PROMPT_LIBRARY}
            favorites={favorites}
            category={promptCategory}
            onCategory={setPromptCategory}
            onToggleFavorite={(id) => setFavorites(toggleFavoritePrompt(id))}
            onRun={(prompt: PromptDefinition) => {
              setView('copilot');
              void askCopilot(tPrompts(prompt.promptKey as 'execPrioritiesPrompt'));
            }}
            auditNote={labels.activityLocalNote ?? ''}
          />
        ) : null}

        {!loading && view === 'activity_log' ? (
          <ActivityLogPanel labels={labels} locale={locale} history={history} />
        ) : null}

        {!loading && view === 'settings' ? (
          <SettingsPanel
            labels={labels}
            locale={locale}
            settings={settings}
            canManage={canManage}
            onChange={setSettings}
            onSave={() => {
              saveAiSettings(settings);
              setSettingsSaved(true);
            }}
            saved={settingsSaved}
          />
        ) : null}

        {!loading && view === 'provider_status' ? (
          <ProviderStatusPanel labels={labels} locale={locale} rows={providerRows} />
        ) : null}
      </div>

      <ApprovalGateModal
        labels={labels}
        open={Boolean(approvalId)}
        actionLabel={
          approvalAction?.sensitive
            ? labels[`sensitive.${approvalAction.sensitive}`] || approvalAction.sensitive
            : ''
        }
        onCancel={() => setApprovalId(null)}
        onConfirm={() => {
          if (approvalId) {
            persistActions(updateActionStatus(actions, approvalId, 'approved'));
            showToast(labels.toastApprovalRecorded ?? 'OK');
          }
          setApprovalId(null);
        }}
      />
    </main>
  );
}
