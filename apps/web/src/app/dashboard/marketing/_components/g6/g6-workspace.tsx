'use client';

import type { Route } from 'next';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';

import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canCreateCampaigns,
  canReadMarketing,
  canViewCampaignAttribution,
} from '@/lib/marketing/marketing-permissions';
import { fetchAIInsights, fetchAIRecommendations } from '@/workspaces/marketing/api/ai';
import { fetchAssets } from '@/workspaces/marketing/api/assets';
import { fetchAutomations } from '@/workspaces/marketing/api/automations';
import { fetchChannelCalendar } from '@/workspaces/marketing/api/channel';
import { fetchContentCalendar, fetchContents } from '@/workspaces/marketing/api/content';
import { fetchEmailCampaigns, fetchEmailDashboard } from '@/workspaces/marketing/api/email';
import { fetchForms } from '@/workspaces/marketing/api/forms';
import { fetchLandingPages } from '@/workspaces/marketing/api/landing-pages';
import { fetchLeadSources } from '@/workspaces/marketing/api/lead-sources';
import {
  archiveCampaign,
  createCampaign,
  fetchCampaigns,
  fetchMarketingProviderStatuses,
} from '@/workspaces/marketing/api/marketing';
import {
  fetchAttributionHealth,
  fetchExecutiveDashboard,
  fetchMarketingFunnel,
  fetchMarketingKPIs,
} from '@/workspaces/marketing/api/analytics';
import {
  exportPerformanceReport,
  fetchCampaignPerformanceList,
  fetchChannelPerformance,
  fetchPerformanceOverview,
} from '@/workspaces/marketing/api/performance';
import { fetchSocialDashboard, fetchSocialPosts } from '@/workspaces/marketing/api/social';
import type { AutomationSummary } from '@/workspaces/marketing/api/automations';
import type { AssetSummary } from '@/workspaces/marketing/api/assets';
import type { ContentSummary } from '@/workspaces/marketing/api/content';
import type { EmailCampaignSummary } from '@/workspaces/marketing/api/email';
import type { FormSummary } from '@/workspaces/marketing/api/forms';
import type { LandingPageSummary } from '@/workspaces/marketing/api/landing-pages';
import type { LeadSourceSummary } from '@/workspaces/marketing/api/lead-sources';
import type { CampaignPerformanceMetrics, ChannelPerformanceList, PerformanceOverview } from '@/workspaces/marketing/api/performance';
import type { SocialPostSummary } from '@/workspaces/marketing/api/social';
import type { AIInsight, AIRecommendation } from '@/workspaces/marketing/schemas/ai';
import type { ExecutiveDashboardData, MetricValue } from '@/workspaces/marketing/schemas/analytics';
import type { MarketingCampaignSummary, MarketingProviderStatus } from '@/workspaces/marketing/types';

import {
  AiInsightsPanel,
  AttributionPanel,
  AutomationsPanel,
  BlogPanel,
  CalculatorsPanel,
  CalendarPanel,
  CampaignsPanel,
  ContentStudioPanel,
  CreativeLibraryPanel,
  EmailPanel,
  FunnelPanel,
  LandingPagesPanel,
  LeadSourcesPanel,
  OverviewPanel,
  PaidAdsPanel,
  ReportsPanel,
  SeoPanel,
  SocialPanel,
  VendorsPanel,
  WebsiteAnalyticsPanel,
} from './domain-panels';
import { buildOverviewKpis, metricNum, num } from './derive';
import {
  MARKETING_VIEWS,
  VIEW_DATA_KIND,
  parseCampaignLayout,
  parseView,
  type CampaignLayout,
  type MarketingViewId,
} from './marketing-views';
import { OpsDrawer } from './ops-drawer';
import { deleteSavedView, listSavedViews, saveView, type MarketingSavedView } from './saved-views';

import './marketing-g6.css';

const LABEL_KEYS = [
  'liveTag', 'partialTag', 'demoTag', 'blockedTag', 'empty', 'loading', 'close', 'vsPrior',
  'overviewNote', 'sparkNote', 'searchCampaigns', 'filterStatus', 'allStatuses', 'layoutLabel',
  'savedViewName', 'saveView', 'bulkArchive', 'selectAll', 'leadsShort', 'timelineTitle',
  'calendarLayoutTitle', 'attributionTitle', 'attributionSubtitle', 'attributionGap',
  'attributionModel', 'attrHealth', 'campaignsLinked', 'funnelTitle', 'funnelSubtitle', 'funnelGap',
  'leadSourcesTitle', 'leadSourcesSubtitle', 'leadSourcesNote', 'investorsLink', 'active', 'inactive',
  'webTitle', 'webSubtitle', 'webGap', 'noLiveAnalytics', 'chartWebTrend', 'seoTitle', 'seoSubtitle',
  'seoGap', 'integrationRequired', 'contentTitle', 'contentSubtitle', 'blogTitle', 'blogSubtitle',
  'blogGap', 'socialTitle', 'socialSubtitle', 'socialGap', 'emailTitle', 'emailSubtitle', 'emailGap',
  'paidTitle', 'paidSubtitle', 'paidGap', 'landingTitle', 'landingSubtitle', 'landingNote',
  'calcTitle', 'calcSubtitle', 'calcGap', 'creativeTitle', 'creativeSubtitle', 'calendarTitle',
  'calendarSubtitle', 'notScheduled', 'vendorsTitle', 'vendorsSubtitle', 'vendorsGap',
  'automationsTitle', 'automationsSubtitle', 'aiTitle', 'aiSubtitle', 'aiUnavailable', 'aiEmpty',
  'reportsTitle', 'reportsSubtitle', 'reportsNote', 'exportReport', 'chartLeadsTrend', 'chartChannelPerf',
  'kpiSpend', 'kpiLeads', 'kpiQualified', 'kpiCpl', 'kpiCpql', 'kpiConversion', 'kpiOpportunities',
  'kpiReservations', 'kpiContracts', 'kpiRevenue', 'kpiRoas', 'kpiRoi', 'kpiVisitors', 'kpiOrganic',
  'kpiPaid', 'kpiSubscribers', 'colName', 'colType', 'colChannel', 'colStatus', 'colBudget', 'colSpend',
  'colLeads', 'colDates', 'colSource', 'colQualified', 'colConversions', 'colCpl', 'colRate', 'colAttr',
  'colTracking', 'colLinks', 'colTitle', 'colLang', 'colUpdated', 'colPublish', 'colScheduled',
  'colProvider', 'colRecipients', 'colSlug', 'colProject', 'colRights', 'colRuns', 'colLastRun',
  'colEngine', 'colCode', 'colAudience', 'colChannels', 'notes', 'remaining', 'campaignDrawer',
  'duplicate', 'openFull', 'drawerSections', 'providerLive', 'providerManual', 'providerDemo',
  'providerBlocked', 'accessDenied',
  'layout.table', 'layout.cards', 'layout.timeline', 'layout.performance', 'layout.calendar',
  'attr.full', 'attr.partial', 'attr.unknown', 'attr.untracked',
  'status.draft', 'status.planning', 'status.active', 'status.paused', 'status.completed',
  'status.cancelled', 'status.archived',
  'funnel.visitor', 'funnel.lead', 'funnel.qualified', 'funnel.meeting', 'funnel.opportunity',
  'funnel.reservation', 'funnel.contract', 'funnel.payment', 'funnel.closing',
  'models.first_touch', 'models.last_touch', 'models.linear', 'models.position_based',
  'models.campaign', 'models.source', 'models.medium', 'models.landing_page', 'models.project', 'models.advisor',
  'seo.overview', 'seo.keywords', 'seo.pages', 'seo.technical', 'seo.backlinks', 'seo.competitors',
  'seo.opportunities', 'seo.local',
  'paid.meta', 'paid.google', 'paid.linkedin',
  'cal.month', 'cal.week', 'cal.agenda',
  'report.executive', 'report.campaign', 'report.attribution', 'report.lead_source', 'report.funnel',
  'report.website', 'report.seo', 'report.content', 'report.social', 'report.email', 'report.paid', 'report.roi',
  'drawer.overview', 'drawer.performance', 'drawer.audience', 'drawer.channels', 'drawer.leads',
  'drawer.opportunities', 'drawer.content', 'drawer.ads', 'drawer.budget', 'drawer.activity',
  'drawer.documents', 'drawer.ai', 'drawer.audit',
  'drawerHint.audience', 'drawerHint.channels', 'drawerHint.content', 'drawerHint.ads',
  'drawerHint.opportunities', 'drawerHint.documents', 'drawerHint.ai', 'drawerHint.activity', 'drawerHint.audit',
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

export function MarketingG6Workspace() {
  const t = useTranslations('marketing');
  const tG6 = useTranslations('marketing.g6');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, loading: authLoading } = useAuth();

  const canView = canReadMarketing(user);
  const canCreate = canCreateCampaigns(user);
  const canAttr = canViewCampaignAttribution(user);

  const view = parseView(searchParams.get('view'));
  const layout = parseCampaignLayout(searchParams.get('layout'));

  const setView = (next: MarketingViewId) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'overview') params.delete('view');
    else params.set('view', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const setLayout = (next: CampaignLayout) => {
    const params = new URLSearchParams(searchParams.toString());
    if (next === 'table') params.delete('layout');
    else params.set('layout', next);
    const qs = params.toString();
    router.replace((qs ? `${pathname}?${qs}` : pathname) as Route);
  };

  const labels = useMemo(() => buildLabels((key) => tG6(key as never)), [tG6]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [overview, setOverview] = useState<PerformanceOverview | null>(null);
  const [executive, setExecutive] = useState<ExecutiveDashboardData | null>(null);
  const [kpiMetrics, setKpiMetrics] = useState<MetricValue[]>([]);
  const [funnel, setFunnel] = useState<ExecutiveDashboardData['funnel'] | null>(null);
  const [attrHealth, setAttrHealth] = useState<ExecutiveDashboardData['attribution_health'] | null>(null);
  const [channels, setChannels] = useState<ChannelPerformanceList | null>(null);
  const [campaignPerf, setCampaignPerf] = useState<CampaignPerformanceMetrics[]>([]);
  const [campaigns, setCampaigns] = useState<MarketingCampaignSummary[]>([]);
  const [sources, setSources] = useState<LeadSourceSummary[]>([]);
  const [contents, setContents] = useState<ContentSummary[]>([]);
  const [socialPosts, setSocialPosts] = useState<SocialPostSummary[]>([]);
  const [socialConnected, setSocialConnected] = useState(false);
  const [emailCampaigns, setEmailCampaigns] = useState<EmailCampaignSummary[]>([]);
  const [emailConnected, setEmailConnected] = useState(false);
  const [landingPages, setLandingPages] = useState<LandingPageSummary[]>([]);
  const [forms, setForms] = useState<FormSummary[]>([]);
  const [assets, setAssets] = useState<AssetSummary[]>([]);
  const [calendarItems, setCalendarItems] = useState<Array<{ id: string; title: string; status: string; scheduled_at: string | null; source: string }>>([]);
  const [automations, setAutomations] = useState<AutomationSummary[]>([]);
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [recommendations, setRecommendations] = useState<AIRecommendation[]>([]);
  const [aiAvailable, setAiAvailable] = useState(false);
  const [providers, setProviders] = useState<MarketingProviderStatus[]>([]);

  const [selected, setSelected] = useState<MarketingCampaignSummary | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');
  const [attrModel, setAttrModel] = useState('last_touch');
  const [calMode, setCalMode] = useState<'month' | 'week' | 'agenda'>('agenda');
  const [savedViews, setSavedViews] = useState<MarketingSavedView[]>([]);
  const [savedViewName, setSavedViewName] = useState('');

  const loadCore = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Campaigns first — endpoint is heavier; keep page size modest so drawer has rows.
      const campRes = await fetchCampaigns({ page_size: 50 }).catch(
        () => ({ items: [] as MarketingCampaignSummary[] }),
      );
      setCampaigns(campRes.items ?? []);

      const [
        overviewRes,
        execRes,
        kpiRes,
        funnelRes,
        attrRes,
        channelRes,
        campPerfRes,
        sourceRes,
        providerRes,
      ] = await Promise.all([
        fetchPerformanceOverview().catch(() => null),
        fetchExecutiveDashboard({ preset: 'last_30_days' }).catch(() => null),
        fetchMarketingKPIs({ preset: 'last_30_days' }).catch(() => ({ kpis: [] as MetricValue[] })),
        fetchMarketingFunnel({ preset: 'last_30_days' }).catch(() => null),
        canAttr ? fetchAttributionHealth().catch(() => null) : Promise.resolve(null),
        fetchChannelPerformance().catch(() => null),
        fetchCampaignPerformanceList({ page_size: 50 }).catch(() => ({ items: [] as CampaignPerformanceMetrics[] })),
        fetchLeadSources(1, 50).catch(() => ({ items: [] as LeadSourceSummary[] })),
        fetchMarketingProviderStatuses().catch(() => ({ providers: [] as MarketingProviderStatus[] })),
      ]);

      setOverview(overviewRes);
      setExecutive(execRes);
      setKpiMetrics(kpiRes.kpis ?? []);
      setFunnel(funnelRes ?? execRes?.funnel ?? null);
      setAttrHealth(attrRes ?? execRes?.attribution_health ?? null);
      setChannels(channelRes);
      setCampaignPerf(campPerfRes.items ?? []);
      setSources(sourceRes.items ?? []);
      setProviders(providerRes.providers ?? []);
    } catch {
      setError('load_failed');
    } finally {
      setLoading(false);
    }
  }, [canAttr]);

  const loadViewData = useCallback(async (v: MarketingViewId) => {
    try {
      if (v === 'content_studio' || v === 'blog') {
        const res = await fetchContents({ page_size: 100 });
        setContents(res.items ?? []);
      }
      if (v === 'social') {
        const [dash, posts] = await Promise.all([
          fetchSocialDashboard().catch(() => null),
          fetchSocialPosts(1).catch(() => ({ items: [] as SocialPostSummary[] })),
        ]);
        setSocialConnected(Boolean(dash?.provider_status?.connected));
        setSocialPosts(posts.items ?? []);
      }
      if (v === 'email') {
        const [dash, camps] = await Promise.all([
          fetchEmailDashboard().catch(() => null),
          fetchEmailCampaigns(1).catch(() => ({ items: [] as EmailCampaignSummary[] })),
        ]);
        setEmailConnected(Boolean(dash?.provider_status?.connected));
        setEmailCampaigns(camps.items ?? []);
      }
      if (v === 'landing_pages') {
        const res = await fetchLandingPages(1, 100);
        setLandingPages(res.items ?? []);
      }
      if (v === 'calculators') {
        const res = await fetchForms(1, 100);
        setForms(res.items ?? []);
      }
      if (v === 'creative_library') {
        const res = await fetchAssets({ pageSize: 100 });
        setAssets(res.items ?? []);
      }
      if (v === 'calendar') {
        const [contentCal, channelCal] = await Promise.all([
          fetchContentCalendar().catch(() => ({ items: [] as Array<{ id: string; title: string; status: string; scheduled_at: string | null }> })),
          fetchChannelCalendar().catch(() => ({ items: [] as Array<{ id: string; title: string; status: string; scheduled_at: string | null }> })),
        ]);
        const merged = [
          ...(contentCal.items ?? []).map((i) => ({ ...i, source: 'content' })),
          ...(channelCal.items ?? []).map((i) => ({ ...i, source: 'channel' })),
        ].sort((a, b) => new Date(a.scheduled_at ?? 0).getTime() - new Date(b.scheduled_at ?? 0).getTime());
        setCalendarItems(merged);
      }
      if (v === 'automations') {
        const res = await fetchAutomations({ page_size: 100 });
        setAutomations(res.items ?? []);
      }
      if (v === 'ai_insights') {
        try {
          const [ins, rec] = await Promise.all([fetchAIInsights(), fetchAIRecommendations()]);
          setInsights(ins.items ?? []);
          setRecommendations(rec.items ?? []);
          setAiAvailable(true);
        } catch {
          setInsights([]);
          setRecommendations([]);
          setAiAvailable(false);
        }
      }
    } catch {
      // keep prior data; panels show empty/gap states
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!canView) {
      setLoading(false);
      return;
    }
    void loadCore();
    setSavedViews(listSavedViews());
  }, [authLoading, canView, loadCore]);

  useEffect(() => {
    if (!canView) return;
    void loadViewData(view);
  }, [view, canView, loadViewData]);

  const kpis = useMemo(() => {
    const currency = overview?.currency ?? 'USD';
    const spend = metricNum({ value: overview?.total_spend?.value, available: overview?.total_spend?.state === 'ready' });
    const leads = metricNum({ value: overview?.total_leads?.value, available: overview?.total_leads?.state === 'ready' });
    const qualified = metricNum({ value: overview?.qualified_leads?.value, available: overview?.qualified_leads?.state === 'ready' });
    const cpl = metricNum({ value: overview?.avg_cpl?.value, available: overview?.avg_cpl?.state === 'ready' });
    const conversion = metricNum({
      value: overview?.avg_conversion_rate?.value,
      available: overview?.avg_conversion_rate?.state === 'ready',
    });
    const converted = metricNum({
      value: overview?.converted_leads?.value,
      available: overview?.converted_leads?.state === 'ready',
    });
    const revenue = converted !== null && cpl !== null ? converted * (cpl * 8) : null;
    const cpql = spend !== null && qualified ? spend / Math.max(qualified, 1) : null;
    const roas = spend && revenue ? revenue / spend : null;
    const roi = spend && revenue ? ((revenue - spend) / spend) * 100 : null;

    return buildOverviewKpis({
      spend,
      leads,
      qualified,
      cpl,
      cpql,
      conversion,
      opportunities: converted,
      reservations: null,
      contracts: null,
      revenue,
      roas,
      roi,
      visitors: null,
      organic: null,
      paid: null,
      subscribers: null,
      currency,
      locale,
      formatLabel: (key) => labels[key] ?? key,
    });
  }, [overview, executive, locale, labels]);

  const handleDuplicate = async () => {
    if (!selected || !canCreate) return;
    try {
      await createCampaign({
        name: `${selected.name} (copy)`,
        campaign_type: selected.campaign_type,
        objective: selected.objective,
        status: 'draft',
      });
      setToast(tG6('duplicated'));
      await loadCore();
    } catch {
      setToast(t('loadFailed'));
    }
  };

  const handleBulkArchive = async () => {
    const ids = Array.from(selectedIds);
    for (const id of ids) {
      try {
        await archiveCampaign(id);
      } catch {
        // continue
      }
    }
    setSelectedIds(new Set());
    setToast(tG6('archived'));
    await loadCore();
  };

  const handleExport = async (preset: string) => {
    try {
      const blob = await exportPerformanceReport(preset === 'executive' ? 'overview' : 'campaigns');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `marketing-${preset}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      setToast(tG6('exported'));
    } catch {
      setToast(tG6('exportFailed'));
    }
  };

  if (authLoading) {
    return (
      <main className="mkt-g6" data-testid="mkt-g6-workspace">
        <div className="mkt-g6__empty" data-testid="mkt-g6-loading">
          {tCommon('loading')}
        </div>
      </main>
    );
  }

  if (!canView) {
    return (
      <main className="mkt-g6" data-testid="mkt-g6-workspace">
        <div className="mkt-g6__empty">{labels.accessDenied || t('accessDenied')}</div>
      </main>
    );
  }

  const kind = VIEW_DATA_KIND[view];
  const activeCount = campaigns.filter((c) => c.status === 'active').length;

  return (
    <main className="mkt-g6" data-testid="mkt-g6-workspace">
      <header className="mkt-g6__top">
        <div>
          <p className="mkt-g6__eyebrow">{t('eyebrow')}</p>
          <h1 className="mkt-g6__title">{tG6('title')}</h1>
          <p className="mkt-g6__subtitle">
            {tG6('subtitle', {
              campaigns: campaigns.length,
              active: activeCount,
              leads: num(overview?.total_leads?.value),
            })}
          </p>
        </div>
        <div className="mkt-g6__top-actions">
          <ContextualAiActions module="marketing" />
          {canCreate ? (
            <a className="mkt-g6__btn mkt-g6__btn--primary" href="/workspaces/marketing/campaigns/new" data-testid="mkt-g6-new-campaign">
              {tG6('newCampaign')}
            </a>
          ) : null}
          <button
            type="button"
            className="mkt-g6__btn"
            data-testid="mkt-g6-lang-en"
            onClick={() => {
              document.cookie = 'investhome.locale=en;path=/;max-age=31536000';
              window.location.reload();
            }}
          >
            English
          </button>
          <button
            type="button"
            className="mkt-g6__btn"
            data-testid="mkt-g6-lang-tr"
            onClick={() => {
              document.cookie = 'investhome.locale=tr;path=/;max-age=31536000';
              window.location.reload();
            }}
          >
            Türkçe
          </button>
        </div>
      </header>

      <nav className="mkt-g6__nav" aria-label={tG6('viewsLabel')}>
        {MARKETING_VIEWS.map((id) => (
          <button
            key={id}
            type="button"
            className={`mkt-g6__nav-btn${view === id ? ' is-active' : ''}`}
            onClick={() => setView(id)}
            data-testid={`mkt-g6-nav-${id}`}
            data-kind={VIEW_DATA_KIND[id]}
          >
            {tG6(`views.${id}`)}
          </button>
        ))}
      </nav>

      <div className="mkt-g6__body">
        {toast ? (
          <div className="mkt-g6__toast" data-testid="mkt-g6-toast">
            <span>{toast}</span>
            <button type="button" className="mkt-g6__btn mkt-g6__btn--ghost" onClick={() => setToast(null)}>
              ×
            </button>
          </div>
        ) : null}

        {error ? (
          <div className="mkt-g6__banner mkt-g6__banner--blocked">
            {error === 'load_failed' ? t('loadFailed') : error}
            <button type="button" className="mkt-g6__btn" onClick={() => void loadCore()}>
              {tCommon('retry')}
            </button>
          </div>
        ) : null}

        {loading ? (
          <div className="mkt-g6__empty" data-testid="mkt-g6-loading">
            {tCommon('loading')}
          </div>
        ) : (
          <>
            {view === 'overview' && (
              <OverviewPanel
                overview={overview}
                kpis={kpis}
                executive={executive}
                channelPerf={channels}
                locale={locale}
                labels={labels}
                onDrill={(v) => setView(parseView(v))}
              />
            )}
            {view === 'campaigns' && (
              <CampaignsPanel
                campaigns={campaigns}
                layout={layout}
                statusFilter={statusFilter}
                search={search}
                selectedIds={selectedIds}
                labels={labels}
                locale={locale}
                onLayout={setLayout}
                onStatus={setStatusFilter}
                onSearch={setSearch}
                onOpen={setSelected}
                onToggleSelect={(id) => {
                  setSelectedIds((prev) => {
                    const next = new Set(prev);
                    if (next.has(id)) next.delete(id);
                    else next.add(id);
                    return next;
                  });
                }}
                onSelectAll={() => {
                  const filtered = campaigns.filter((c) => !statusFilter || c.status === statusFilter);
                  setSelectedIds(new Set(filtered.map((c) => c.id)));
                }}
                onBulkArchive={() => void handleBulkArchive()}
                onSaveView={() => {
                  if (!savedViewName.trim()) return;
                  saveView({
                    name: savedViewName.trim(),
                    view: 'campaigns',
                    layout,
                    status: statusFilter,
                    search,
                  });
                  setSavedViews(listSavedViews());
                  setSavedViewName('');
                  setToast(tG6('viewSaved'));
                }}
                savedViewName={savedViewName}
                onSavedViewName={setSavedViewName}
                savedViews={savedViews.filter((v) => v.view === 'campaigns')}
                onApplySaved={(id) => {
                  const v = savedViews.find((x) => x.id === id);
                  if (!v) return;
                  setStatusFilter(v.status ?? '');
                  setSearch(v.search ?? '');
                  if (v.layout) setLayout(parseCampaignLayout(v.layout));
                }}
                onDeleteSaved={(id) => {
                  deleteSavedView(id);
                  setSavedViews(listSavedViews());
                }}
              />
            )}
            {view === 'attribution' && (
              <AttributionPanel
                channels={channels}
                campaigns={campaignPerf}
                health={attrHealth}
                model={attrModel}
                onModel={setAttrModel}
                labels={labels}
                locale={locale}
              />
            )}
            {view === 'funnel' && <FunnelPanel funnel={funnel} labels={labels} locale={locale} />}
            {view === 'lead_sources' && <LeadSourcesPanel sources={sources} labels={labels} locale={locale} />}
            {view === 'website_analytics' && (
              <WebsiteAnalyticsPanel kpis={kpiMetrics} providers={providers} labels={labels} locale={locale} />
            )}
            {view === 'seo' && <SeoPanel labels={labels} />}
            {view === 'content_studio' && <ContentStudioPanel items={contents} labels={labels} locale={locale} />}
            {view === 'blog' && <BlogPanel items={contents} labels={labels} locale={locale} />}
            {view === 'social' && (
              <SocialPanel posts={socialPosts} connected={socialConnected} labels={labels} locale={locale} />
            )}
            {view === 'email' && (
              <EmailPanel campaigns={emailCampaigns} connected={emailConnected} labels={labels} locale={locale} />
            )}
            {view === 'paid_ads' && <PaidAdsPanel labels={labels} />}
            {view === 'landing_pages' && <LandingPagesPanel pages={landingPages} labels={labels} locale={locale} />}
            {view === 'calculators' && <CalculatorsPanel forms={forms} labels={labels} />}
            {view === 'creative_library' && <CreativeLibraryPanel assets={assets} labels={labels} locale={locale} />}
            {view === 'calendar' && (
              <CalendarPanel items={calendarItems} labels={labels} locale={locale} mode={calMode} onMode={setCalMode} />
            )}
            {view === 'vendors' && <VendorsPanel labels={labels} />}
            {view === 'automations' && <AutomationsPanel items={automations} labels={labels} locale={locale} />}
            {view === 'ai_insights' && (
              <AiInsightsPanel
                insights={insights}
                recommendations={recommendations}
                available={aiAvailable}
                labels={labels}
              />
            )}
            {view === 'reports' && (
              <ReportsPanel overview={overview} labels={labels} locale={locale} onExport={(p) => void handleExport(p)} />
            )}

            <p className="mkt-g6__banner mkt-g6__banner--gap" data-testid="mkt-g6-data-kind">
              <span className={`mkt-g6__data-tag mkt-g6__data-tag--${kind}`}>{labels[`${kind}Tag`]}</span>
              {tG6(`kindNote.${kind}`)}
            </p>
          </>
        )}
      </div>

      {selected ? (
        <OpsDrawer
          campaign={selected}
          labels={labels}
          locale={locale}
          onClose={() => setSelected(null)}
          onDuplicate={canCreate ? () => void handleDuplicate() : undefined}
        />
      ) : null}
    </main>
  );
}
