'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { BarChart, LineChart, Sparkline } from '@/components/design-system/charts';
import type { AutomationSummary } from '@/workspaces/marketing/api/automations';
import type { AssetSummary } from '@/workspaces/marketing/api/assets';
import type { ContentSummary } from '@/workspaces/marketing/api/content';
import type { EmailCampaignSummary } from '@/workspaces/marketing/api/email';
import type { LandingPageSummary } from '@/workspaces/marketing/api/landing-pages';
import type { LeadSourceSummary } from '@/workspaces/marketing/api/lead-sources';
import type {
  CampaignPerformanceMetrics,
  ChannelPerformanceList,
  PerformanceOverview,
} from '@/workspaces/marketing/api/performance';
import type { SocialPostSummary } from '@/workspaces/marketing/api/social';
import type { MarketingCampaignSummary, MarketingProviderStatus } from '@/workspaces/marketing/types';
import type { ExecutiveDashboardData, MetricValue } from '@/workspaces/marketing/schemas/analytics';
import type { AIInsight, AIRecommendation } from '@/workspaces/marketing/schemas/ai';

import {
  classifyAttribution,
  deltaClass,
  formatCompact,
  formatMoney,
  formatPercent,
  metricNum,
  num,
  sparkFromBase,
  statusTone,
  type OverviewKpi,
} from './derive';
import {
  DEFAULT_FUNNEL_STAGES,
  type AttributionLabel,
  type CampaignLayout,
  type DataKind,
} from './marketing-views';

function lab(labels: Record<string, string>, key: string): string {
  return labels[key] ?? key;
}

export function DataTag({ kind, label }: { kind: DataKind; label: string }) {
  return <span className={`mkt-g6__data-tag mkt-g6__data-tag--${kind}`}>{label}</span>;
}

function ProviderBadge({
  mode,
  labels,
}: {
  mode: 'live' | 'manual' | 'demo' | 'blocked';
  labels: Record<string, string>;
}) {
  const map = {
    live: lab(labels, 'providerLive'),
    manual: lab(labels, 'providerManual'),
    demo: lab(labels, 'providerDemo'),
    blocked: lab(labels, 'providerBlocked'),
  };
  return <span className={`mkt-g6__provider mkt-g6__provider--${mode}`}>{map[mode]}</span>;
}

function AttrBadge({ kind, labels }: { kind: AttributionLabel; labels: Record<string, string> }) {
  return (
    <span className={`mkt-g6__attr-label mkt-g6__attr-label--${kind}`}>
      {lab(labels, `attr.${kind}`)}
    </span>
  );
}

function GapBanner({
  kind,
  labels,
  messageKey,
}: {
  kind: DataKind;
  labels: Record<string, string>;
  messageKey: string;
}) {
  return (
    <p className={`mkt-g6__banner mkt-g6__banner--${kind === 'blocked' ? 'blocked' : 'gap'}`}>
      <DataTag kind={kind} label={lab(labels, `${kind}Tag`)} />
      {lab(labels, messageKey)}
    </p>
  );
}

function perfVal(m?: { value?: string | number | null; state?: string } | null): string {
  if (!m || m.state !== 'ready' || m.value === null || m.value === undefined) return '—';
  return String(m.value);
}

interface Common {
  labels: Record<string, string>;
  locale: string;
}

export function OverviewPanel({
  overview,
  kpis,
  executive,
  channelPerf,
  locale,
  labels,
  onDrill,
}: Common & {
  overview: PerformanceOverview | null;
  kpis: OverviewKpi[];
  executive: ExecutiveDashboardData | null;
  channelPerf: ChannelPerformanceList | null;
  onDrill: (view: string) => void;
}) {
  const leadSeries =
    executive?.kpis
      ?.find((k) => k.key.includes('lead'))
      ?.evidence && Array.isArray((executive.kpis.find((k) => k.key.includes('lead'))?.evidence as { series?: number[] })?.series)
      ? ((executive.kpis.find((k) => k.key.includes('lead'))?.evidence as { series: number[] }).series)
      : sparkFromBase(num(overview?.total_leads?.value));

  const leadsTrend = leadSeries.map((v, i) => ({ label: `T${i + 1}`, value: v }));
  const channelBars =
    channelPerf?.items.slice(0, 6).map((c) => ({
      label: c.channel,
      value: Math.max(num(c.leads?.value), 1),
    })) ?? [];

  return (
    <div data-testid="mkt-g6-overview">
      <div className="mkt-g6__toolbar">
        <div className="mkt-g6__toolbar-left">
          <DataTag kind="live" label={lab(labels, 'liveTag')} />
          <span className="mkt-g6__subtitle" style={{ margin: 0 }}>
            {lab(labels, 'overviewNote')}
          </span>
        </div>
      </div>

      <div className="mkt-g6__kpis" style={{ marginTop: '0.35rem' }}>
        {kpis.map((kpi) => {
          const d = deltaClass(kpi.change);
          return (
            <button
              key={kpi.key}
              type="button"
              className="mkt-g6__kpi"
              data-testid={`mkt-g6-kpi-${kpi.key}`}
              title={lab(labels, kpi.labelKey)}
              onClick={() => kpi.drillView && onDrill(kpi.drillView)}
            >
              <p>{lab(labels, kpi.labelKey)}</p>
              <strong>{kpi.value}</strong>
              <div className="mkt-g6__kpi-meta">
                <span
                  className={`mkt-g6__kpi-delta${d ? ` mkt-g6__kpi-delta--${d}` : ''}`}
                >
                  {kpi.change === null
                    ? '—'
                    : `${kpi.change > 0 ? '+' : ''}${kpi.change.toFixed(1)}%`}
                </span>
                <span>{lab(labels, 'vsPrior')}</span>
              </div>
              {kpi.spark.length > 0 ? (
                <div className="mkt-g6__kpi-spark">
                  <Sparkline
                    values={kpi.spark}
                    ariaLabel={lab(labels, kpi.labelKey)}
                    locale={locale}
                    format="compact"
                  />
                </div>
              ) : null}
            </button>
          );
        })}
      </div>

      <div className="mkt-g6__charts" style={{ marginTop: '0.65rem' }}>
        <div className="mkt-g6__chart-card">
          <h4>{lab(labels, 'chartLeadsTrend')}</h4>
          <LineChart data={leadsTrend} ariaLabel={lab(labels, 'chartLeadsTrend')} locale={locale} format="compact" height={140} />
        </div>
        <div className="mkt-g6__chart-card">
          <h4>{lab(labels, 'chartChannelPerf')}</h4>
          {channelBars.length === 0 ? (
            <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
          ) : (
            <BarChart data={channelBars} ariaLabel={lab(labels, 'chartChannelPerf')} locale={locale} />
          )}
        </div>
      </div>

      <p className="mkt-g6__banner mkt-g6__banner--gap" style={{ marginTop: '0.55rem' }}>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} /> {lab(labels, 'sparkNote')}
      </p>
    </div>
  );
}

export function CampaignsPanel({
  campaigns,
  layout,
  statusFilter,
  search,
  selectedIds,
  labels,
  locale,
  onLayout,
  onStatus,
  onSearch,
  onOpen,
  onToggleSelect,
  onSelectAll,
  onBulkArchive,
  onSaveView,
  savedViewName,
  onSavedViewName,
  savedViews,
  onApplySaved,
  onDeleteSaved,
}: Common & {
  campaigns: MarketingCampaignSummary[];
  layout: CampaignLayout;
  statusFilter: string;
  search: string;
  selectedIds: Set<string>;
  onLayout: (l: CampaignLayout) => void;
  onStatus: (s: string) => void;
  onSearch: (s: string) => void;
  onOpen: (c: MarketingCampaignSummary) => void;
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onBulkArchive: () => void;
  onSaveView: () => void;
  savedViewName: string;
  onSavedViewName: (v: string) => void;
  savedViews: Array<{ id: string; name: string }>;
  onApplySaved: (id: string) => void;
  onDeleteSaved: (id: string) => void;
}) {
  const filtered = campaigns.filter((c) => {
    if (statusFilter && c.status !== statusFilter) return false;
    if (search) {
      const q = search.toLowerCase();
      return c.name.toLowerCase().includes(q) || (c.code ?? '').toLowerCase().includes(q);
    }
    return true;
  });

  return (
    <div data-testid="mkt-g6-campaigns">
      <div className="mkt-g6__toolbar">
        <div className="mkt-g6__toolbar-left">
          <DataTag kind="live" label={lab(labels, 'liveTag')} />
          <input
            className="mkt-g6__search"
            data-testid="mkt-g6-campaign-search"
            placeholder={lab(labels, 'searchCampaigns')}
            value={search}
            onChange={(e) => onSearch(e.target.value)}
          />
          <select
            className="mkt-g6__select"
            data-testid="mkt-g6-campaign-status"
            value={statusFilter}
            onChange={(e) => onStatus(e.target.value)}
            aria-label={lab(labels, 'filterStatus')}
          >
            <option value="">{lab(labels, 'allStatuses')}</option>
            {['draft', 'planning', 'active', 'paused', 'completed', 'cancelled', 'archived'].map((s) => (
              <option key={s} value={s}>
                {lab(labels, `status.${s}`) !== `status.${s}` ? lab(labels, `status.${s}`) : s}
              </option>
            ))}
          </select>
          <div className="mkt-g6__seg" role="group" aria-label={lab(labels, 'layoutLabel')}>
            {(['table', 'cards', 'timeline', 'performance', 'calendar'] as CampaignLayout[]).map((l) => (
              <button
                key={l}
                type="button"
                className={layout === l ? 'is-active' : ''}
                data-testid={`mkt-g6-layout-${l}`}
                onClick={() => onLayout(l)}
              >
                {lab(labels, `layout.${l}`)}
              </button>
            ))}
          </div>
        </div>
        <div className="mkt-g6__toolbar-right">
          <input
            className="mkt-g6__input"
            data-testid="mkt-g6-saved-view-name"
            placeholder={lab(labels, 'savedViewName')}
            value={savedViewName}
            onChange={(e) => onSavedViewName(e.target.value)}
          />
          <button type="button" className="mkt-g6__btn" data-testid="mkt-g6-save-view" onClick={onSaveView}>
            {lab(labels, 'saveView')}
          </button>
          {selectedIds.size > 0 ? (
            <button type="button" className="mkt-g6__btn" data-testid="mkt-g6-bulk-archive" onClick={onBulkArchive}>
              {lab(labels, 'bulkArchive')} ({selectedIds.size})
            </button>
          ) : null}
        </div>
      </div>

      {savedViews.length > 0 ? (
        <div className="mkt-g6__toolbar" style={{ marginTop: '0.35rem' }}>
          <div className="mkt-g6__toolbar-left">
            {savedViews.map((v) => (
              <span key={v.id} style={{ display: 'inline-flex', gap: '0.25rem', alignItems: 'center' }}>
                <button type="button" className="mkt-g6__btn mkt-g6__btn--ghost" onClick={() => onApplySaved(v.id)}>
                  {v.name}
                </button>
                <button type="button" className="mkt-g6__btn mkt-g6__btn--ghost" onClick={() => onDeleteSaved(v.id)} aria-label="delete">
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>
      ) : null}

      {layout === 'cards' ? (
        <div className="mkt-g6__cards" data-testid="mkt-g6-campaign-cards">
          {filtered.map((c) => (
            <button
              key={c.id}
              type="button"
              className="mkt-g6__card"
              data-testid={`mkt-g6-campaign-card-${c.id}`}
              onClick={() => onOpen(c)}
            >
              <h4>{c.name}</h4>
              <p>
                <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
                {' · '}
                {c.primary_channel ?? '—'}
              </p>
              <p>
                {formatMoney(num(c.budget_amount), c.budget_currency, locale)} · {c.actual_leads ?? 0} {lab(labels, 'leadsShort')}
              </p>
            </button>
          ))}
        </div>
      ) : layout === 'timeline' || layout === 'calendar' ? (
        <div className="mkt-g6__panel" data-testid={`mkt-g6-campaign-${layout}`}>
          <h3>{lab(labels, layout === 'timeline' ? 'timelineTitle' : 'calendarLayoutTitle')}</h3>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {filtered.map((c) => (
              <li key={c.id}>
                <button type="button" className="mkt-g6__card" style={{ width: '100%' }} onClick={() => onOpen(c)}>
                  <h4>{c.name}</h4>
                  <p>
                    {c.start_date ?? '—'} → {c.end_date ?? '—'} · {c.status}
                  </p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : layout === 'performance' ? (
        <div className="mkt-g6__list-wrap" data-testid="mkt-g6-campaign-performance">
          <table className="mkt-g6__table">
            <thead>
              <tr>
                <th>{lab(labels, 'colName')}</th>
                <th>{lab(labels, 'colLeads')}</th>
                <th>{lab(labels, 'colSpend')}</th>
                <th>{lab(labels, 'colStatus')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <tr key={c.id} onClick={() => onOpen(c)}>
                  <td>{c.name}</td>
                  <td>{c.actual_leads ?? '—'}</td>
                  <td>{formatMoney(num(c.spent_amount), c.budget_currency, locale)}</td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mkt-g6__list-wrap" data-testid="mkt-g6-campaign-table">
          <table className="mkt-g6__table">
            <thead>
              <tr>
                <th>
                  <input type="checkbox" aria-label={lab(labels, 'selectAll')} onChange={onSelectAll} checked={filtered.length > 0 && filtered.every((c) => selectedIds.has(c.id))} />
                </th>
                <th>{lab(labels, 'colName')}</th>
                <th>{lab(labels, 'colType')}</th>
                <th>{lab(labels, 'colChannel')}</th>
                <th>{lab(labels, 'colStatus')}</th>
                <th>{lab(labels, 'colBudget')}</th>
                <th>{lab(labels, 'colSpend')}</th>
                <th>{lab(labels, 'colLeads')}</th>
                <th>{lab(labels, 'colDates')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                  </td>
                </tr>
              ) : (
                filtered.map((c) => (
                  <tr
                    key={c.id}
                    className={selectedIds.has(c.id) ? 'is-selected' : ''}
                    data-testid={`mkt-g6-campaign-row-${c.id}`}
                    onClick={() => onOpen(c)}
                  >
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(c.id)}
                        onChange={() => onToggleSelect(c.id)}
                        aria-label={c.name}
                      />
                    </td>
                    <td>
                      <strong>{c.name}</strong>
                      {c.code ? <div className="mkt-g6__mono">{c.code}</div> : null}
                    </td>
                    <td>{c.campaign_type}</td>
                    <td>{c.primary_channel ?? '—'}</td>
                    <td>
                      <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
                    </td>
                    <td>{formatMoney(num(c.budget_amount), c.budget_currency, locale)}</td>
                    <td>{formatMoney(num(c.spent_amount), c.budget_currency, locale)}</td>
                    <td>{c.actual_leads ?? '—'}</td>
                    <td>
                      {c.start_date ?? '—'} → {c.end_date ?? '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function AttributionPanel({
  channels,
  campaigns,
  health,
  model,
  onModel,
  labels,
  locale,
}: Common & {
  channels: ChannelPerformanceList | null;
  campaigns: CampaignPerformanceMetrics[];
  health: ExecutiveDashboardData['attribution_health'] | null;
  model: string;
  onModel: (m: string) => void;
}) {
  const models = ['first_touch', 'last_touch', 'linear', 'position_based', 'campaign', 'source', 'medium', 'landing_page', 'project', 'advisor'];
  const rows =
    channels?.items.map((c) => {
      const attr = classifyAttribution({
        attribution_status: health?.overall_status ?? 'partial',
        leads: num(c.leads?.value),
      });
      return {
        key: c.channel,
        source: c.channel,
        medium: '—',
        campaign: '—',
        leads: perfVal(c.leads),
        qualified: perfVal(c.qualified_leads),
        conversions: perfVal(c.conversions),
        spend: perfVal(c.spend),
        cpl: perfVal(c.cpl),
        rate: perfVal(c.conversion_rate),
        attr,
      };
    }) ?? [];

  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-attribution">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'attributionTitle')}</h3>
          <p>{lab(labels, 'attributionSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <GapBanner kind="partial" labels={labels} messageKey="attributionGap" />
      <div className="mkt-g6__toolbar" style={{ marginTop: '0.5rem' }}>
        <div className="mkt-g6__seg" role="group" aria-label={lab(labels, 'attributionModel')}>
          {models.map((m) => (
            <button key={m} type="button" className={model === m ? 'is-active' : ''} data-testid={`mkt-g6-attr-model-${m}`} onClick={() => onModel(m)}>
              {lab(labels, `models.${m}`)}
            </button>
          ))}
        </div>
      </div>
      {health ? (
        <p className="mkt-g6__subtitle">
          {lab(labels, 'attrHealth')}: {health.overall_status}
        </p>
      ) : null}
      <div className="mkt-g6__list-wrap" style={{ marginTop: '0.5rem' }}>
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colSource')}</th>
              <th>{lab(labels, 'colLeads')}</th>
              <th>{lab(labels, 'colQualified')}</th>
              <th>{lab(labels, 'colConversions')}</th>
              <th>{lab(labels, 'colSpend')}</th>
              <th>{lab(labels, 'colCpl')}</th>
              <th>{lab(labels, 'colRate')}</th>
              <th>{lab(labels, 'colAttr')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={8}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              rows.map((r) => (
                <tr key={r.key}>
                  <td>{r.source}</td>
                  <td>{r.leads}</td>
                  <td>{r.qualified}</td>
                  <td>{r.conversions}</td>
                  <td>{r.spend}</td>
                  <td>{r.cpl}</td>
                  <td>{r.rate}</td>
                  <td>
                    <AttrBadge kind={r.attr} labels={labels} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {campaigns.length > 0 ? (
        <p className="mkt-g6__subtitle" style={{ marginTop: '0.5rem' }}>
          {lab(labels, 'campaignsLinked')}: {campaigns.length} · {locale}
        </p>
      ) : null}
    </div>
  );
}

export function FunnelPanel({
  funnel,
  labels,
  locale,
}: Common & {
  funnel: ExecutiveDashboardData['funnel'] | null;
}) {
  const stages =
    funnel?.stages && funnel.stages.length > 0
      ? funnel.stages
      : DEFAULT_FUNNEL_STAGES.map((key, i) => ({
          key,
          label: lab(labels, `funnel.${key}`),
          count: null as number | null,
          state: 'unknown',
          conversion_percent: null as number | null,
          drop_off_percent: null as number | null,
          _idx: i,
        }));

  const max = Math.max(...stages.map((s) => num(s.count)), 1);

  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-funnel">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'funnelTitle')}</h3>
          <p>{lab(labels, 'funnelSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__funnel">
        {stages.map((s) => {
          const count = s.count;
          const width = count === null || count === undefined ? 0 : (num(count) / max) * 100;
          return (
            <div key={s.key} className="mkt-g6__funnel-row" data-testid={`mkt-g6-funnel-${s.key}`}>
              <span>{s.label || lab(labels, `funnel.${s.key}`)}</span>
              <div className="mkt-g6__funnel-bar">
                <div className="mkt-g6__funnel-fill" style={{ width: `${Math.max(width, count === null ? 0 : 4)}%` }} />
              </div>
              <span className="mkt-g6__mono">{count === null || count === undefined ? '—' : formatCompact(num(count), locale)}</span>
              <span>
                {s.conversion_percent === null || s.conversion_percent === undefined
                  ? '—'
                  : formatPercent(num(s.conversion_percent), locale)}
              </span>
            </div>
          );
        })}
      </div>
      {(!funnel || !funnel.stages?.length) && (
        <GapBanner kind="partial" labels={labels} messageKey="funnelGap" />
      )}
    </div>
  );
}

export function LeadSourcesPanel({
  sources,
  labels,
  locale,
}: Common & { sources: LeadSourceSummary[] }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-lead-sources">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'leadSourcesTitle')}</h3>
          <p>{lab(labels, 'leadSourcesSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__list-wrap">
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colSource')}</th>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colTracking')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colLinks')}</th>
            </tr>
          </thead>
          <tbody>
            {sources.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              sources.map((s) => (
                <tr key={s.id} data-testid={`mkt-g6-source-${s.id}`}>
                  <td>{s.name}</td>
                  <td>{s.source_type}</td>
                  <td>
                    <AttrBadge
                      kind={classifyAttribution({ tracking_readiness: s.tracking_readiness })}
                      labels={labels}
                    />
                  </td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${s.is_active ? 'ok' : 'warn'}`}>
                      {s.is_active ? lab(labels, 'active') : lab(labels, 'inactive')}
                    </span>
                  </td>
                  <td>
                    <Link className="mkt-g6__link" href={'/workspaces/crm/dashboard' as Route}>
                      CRM
                    </Link>
                    {' · '}
                    <Link className="mkt-g6__link" href={'/dashboard/investors' as Route}>
                      {lab(labels, 'investorsLink')}
                    </Link>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="mkt-g6__subtitle">{lab(labels, 'leadSourcesNote')} · {locale}</p>
    </div>
  );
}

export function WebsiteAnalyticsPanel({
  kpis,
  providers,
  labels,
  locale,
}: Common & { kpis: MetricValue[]; providers: MarketingProviderStatus[] }) {
  const ready = kpis.filter((k) => k.state === 'ready');
  const analyticsProvider = providers.find((p) => /analytics|web|posthog|tracking/i.test(p.channel_name + p.category));
  const connected = analyticsProvider?.connection_status === 'connected';

  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-website-analytics">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'webTitle')}</h3>
          <p>{lab(labels, 'webSubtitle')}</p>
        </div>
        <DataTag kind={connected ? 'live' : 'partial'} label={lab(labels, connected ? 'liveTag' : 'partialTag')} />
      </div>
      {!connected ? <GapBanner kind="partial" labels={labels} messageKey="webGap" /> : null}
      <div className="mkt-g6__kpis" style={{ marginTop: '0.5rem' }}>
        {(ready.length ? ready : kpis).slice(0, 8).map((k) => (
          <article key={k.key} className="mkt-g6__kpi" style={{ cursor: 'default' }}>
            <p>{k.label}</p>
            <strong>{k.state === 'ready' ? formatCompact(metricNum(k), locale) : '—'}</strong>
          </article>
        ))}
      </div>
      {ready.length === 0 ? (
        <div className="mkt-g6__empty">{lab(labels, 'noLiveAnalytics')}</div>
      ) : (
        <div className="mkt-g6__chart-card" style={{ marginTop: '0.55rem' }}>
          <h4>{lab(labels, 'chartWebTrend')}</h4>
          <LineChart
            data={sparkFromBase(num(ready[0]?.value)).map((v, i) => ({ label: `T${i + 1}`, value: v }))}
            ariaLabel={lab(labels, 'chartWebTrend')}
            locale={locale}
            format="compact"
            height={140}
          />
        </div>
      )}
    </div>
  );
}

export function SeoPanel({ labels }: { labels: Record<string, string> }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-seo">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'seoTitle')}</h3>
          <p>{lab(labels, 'seoSubtitle')}</p>
        </div>
        <DataTag kind="blocked" label={lab(labels, 'blockedTag')} />
      </div>
      <GapBanner kind="blocked" labels={labels} messageKey="seoGap" />
      <div className="mkt-g6__insights" style={{ marginTop: '0.55rem' }}>
        {['overview', 'keywords', 'pages', 'technical', 'backlinks', 'competitors', 'opportunities', 'local'].map((s) => (
          <div key={s} className="mkt-g6__insight">
            <strong>{lab(labels, `seo.${s}`)}</strong>
            <span>{lab(labels, 'integrationRequired')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ContentStudioPanel({
  items,
  labels,
  locale,
}: Common & { items: ContentSummary[] }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-content-studio">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'contentTitle')}</h3>
          <p>{lab(labels, 'contentSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__list-wrap">
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colTitle')}</th>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colLang')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colUpdated')}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              items.map((c) => (
                <tr key={c.id}>
                  <td>{c.title}</td>
                  <td>{c.content_type}</td>
                  <td>{c.primary_language}</td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
                  </td>
                  <td>{new Date(c.updated_at).toLocaleDateString(locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function BlogPanel({ items, labels, locale }: Common & { items: ContentSummary[] }) {
  const blogs = items.filter((c) => /blog|article/i.test(c.content_type));
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-blog">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'blogTitle')}</h3>
          <p>{lab(labels, 'blogSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <GapBanner kind="partial" labels={labels} messageKey="blogGap" />
      <div className="mkt-g6__list-wrap" style={{ marginTop: '0.5rem' }}>
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colTitle')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colPublish')}</th>
              <th>{lab(labels, 'colLang')}</th>
            </tr>
          </thead>
          <tbody>
            {(blogs.length ? blogs : items).slice(0, 40).map((c) => (
              <tr key={c.id}>
                <td>{c.title}</td>
                <td>
                  <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
                </td>
                <td>{c.published_at ? new Date(c.published_at).toLocaleDateString(locale) : '—'}</td>
                <td>{c.primary_language}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function SocialPanel({
  posts,
  connected,
  labels,
  locale,
}: Common & { posts: SocialPostSummary[]; connected: boolean }) {
  const mode = connected ? 'live' : 'manual';
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-social">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'socialTitle')}</h3>
          <p>{lab(labels, 'socialSubtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
          <ProviderBadge mode={mode} labels={labels} />
          <DataTag kind={connected ? 'partial' : 'partial'} label={lab(labels, 'partialTag')} />
        </div>
      </div>
      <GapBanner kind="partial" labels={labels} messageKey="socialGap" />
      <div className="mkt-g6__list-wrap" style={{ marginTop: '0.5rem' }}>
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colTitle')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colScheduled')}</th>
              <th>{lab(labels, 'colProvider')}</th>
            </tr>
          </thead>
          <tbody>
            {posts.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              posts.map((p) => (
                <tr key={p.id}>
                  <td>{p.title ?? p.id.slice(0, 8)}</td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${statusTone(p.status)}`}>{p.status}</span>
                  </td>
                  <td>{p.scheduled_at ? new Date(p.scheduled_at).toLocaleString(locale) : '—'}</td>
                  <td>
                    <ProviderBadge mode={connected ? 'live' : 'blocked'} labels={labels} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function EmailPanel({
  campaigns,
  connected,
  labels,
  locale,
}: Common & { campaigns: EmailCampaignSummary[]; connected: boolean }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-email">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'emailTitle')}</h3>
          <p>{lab(labels, 'emailSubtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.35rem' }}>
          <ProviderBadge mode={connected ? 'live' : 'blocked'} labels={labels} />
          <DataTag kind="partial" label={lab(labels, 'partialTag')} />
        </div>
      </div>
      <GapBanner kind={connected ? 'partial' : 'blocked'} labels={labels} messageKey="emailGap" />
      <div className="mkt-g6__list-wrap" style={{ marginTop: '0.5rem' }}>
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colRecipients')}</th>
              <th>{lab(labels, 'colScheduled')}</th>
            </tr>
          </thead>
          <tbody>
            {campaigns.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              campaigns.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${statusTone(c.status)}`}>{c.status}</span>
                  </td>
                  <td>{c.eligible_recipient_count ?? c.recipient_count ?? '—'}</td>
                  <td>{c.scheduled_at ? new Date(c.scheduled_at).toLocaleString(locale) : '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PaidAdsPanel({ labels }: { labels: Record<string, string> }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-paid-ads">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'paidTitle')}</h3>
          <p>{lab(labels, 'paidSubtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.35rem' }}>
          <ProviderBadge mode="blocked" labels={labels} />
          <DataTag kind="blocked" label={lab(labels, 'blockedTag')} />
        </div>
      </div>
      <GapBanner kind="blocked" labels={labels} messageKey="paidGap" />
      <div className="mkt-g6__insights" style={{ marginTop: '0.55rem' }}>
        {['meta', 'google', 'linkedin'].map((p) => (
          <div key={p} className="mkt-g6__insight">
            <strong>{lab(labels, `paid.${p}`)}</strong>
            <span>{lab(labels, 'integrationRequired')}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function LandingPagesPanel({
  pages,
  labels,
  locale,
}: Common & { pages: LandingPageSummary[] }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-landing-pages">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'landingTitle')}</h3>
          <p>{lab(labels, 'landingSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__list-wrap">
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colSlug')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colUpdated')}</th>
            </tr>
          </thead>
          <tbody>
            {pages.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              pages.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td className="mkt-g6__mono">{p.slug}</td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${statusTone(p.status)}`}>{p.status}</span>
                  </td>
                  <td>{new Date(p.updated_at).toLocaleDateString(locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      <p className="mkt-g6__subtitle">{lab(labels, 'landingNote')}</p>
    </div>
  );
}

export function CalculatorsPanel({
  forms,
  labels,
}: {
  forms: Array<{ id: string; name: string; status?: string; slug?: string; updated_at?: string }>;
  labels: Record<string, string>;
}) {
  const magnets = forms.filter((f) => /calc|magnet|guide|checklist|brochure|yield|mortgage/i.test(`${f.name} ${f.slug ?? ''}`));
  const rows = magnets.length ? magnets : forms;
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-calculators">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'calcTitle')}</h3>
          <p>{lab(labels, 'calcSubtitle')}</p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <GapBanner kind="partial" labels={labels} messageKey="calcGap" />
      <div className="mkt-g6__list-wrap" style={{ marginTop: '0.5rem' }}>
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colStatus')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={3}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              rows.map((f) => (
                <tr key={f.id}>
                  <td>{f.name}</td>
                  <td>{f.slug ?? 'lead_magnet'}</td>
                  <td>{f.status ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function CreativeLibraryPanel({
  assets,
  labels,
  locale,
}: Common & { assets: AssetSummary[] }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-creative-library">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'creativeTitle')}</h3>
          <p>{lab(labels, 'creativeSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__list-wrap">
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colType')}</th>
              <th>{lab(labels, 'colProject')}</th>
              <th>{lab(labels, 'colRights')}</th>
              <th>{lab(labels, 'colUpdated')}</th>
            </tr>
          </thead>
          <tbody>
            {assets.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              assets.map((a) => (
                <tr key={a.id}>
                  <td>{a.title || a.name}</td>
                  <td>{a.asset_type}</td>
                  <td>{a.project_name ?? '—'}</td>
                  <td>{a.rights_status}</td>
                  <td>{new Date(a.updated_at).toLocaleDateString(locale)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function CalendarPanel({
  items,
  labels,
  locale,
  mode,
  onMode,
}: Common & {
  items: Array<{ id: string; title: string; status: string; scheduled_at: string | null; source: string }>;
  mode: 'month' | 'week' | 'agenda';
  onMode: (m: 'month' | 'week' | 'agenda') => void;
}) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-calendar">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'calendarTitle')}</h3>
          <p>{lab(labels, 'calendarSubtitle')}</p>
        </div>
        <div style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
          <div className="mkt-g6__seg">
            {(['month', 'week', 'agenda'] as const).map((m) => (
              <button key={m} type="button" className={mode === m ? 'is-active' : ''} onClick={() => onMode(m)}>
                {lab(labels, `cal.${m}`)}
              </button>
            ))}
          </div>
          <DataTag kind="partial" label={lab(labels, 'partialTag')} />
        </div>
      </div>
      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
        {items.length === 0 ? (
          <li className="mkt-g6__empty">{lab(labels, 'empty')}</li>
        ) : (
          items.map((item) => (
            <li key={`${item.source}-${item.id}`} className="mkt-g6__card" style={{ cursor: 'default' }}>
              <h4>{item.title}</h4>
              <p>
                {item.source} · {item.status} ·{' '}
                {item.scheduled_at ? new Date(item.scheduled_at).toLocaleString(locale) : lab(labels, 'notScheduled')}
              </p>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}

export function VendorsPanel({ labels }: { labels: Record<string, string> }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-vendors">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'vendorsTitle')}</h3>
          <p>{lab(labels, 'vendorsSubtitle')}</p>
        </div>
        <DataTag kind="blocked" label={lab(labels, 'blockedTag')} />
      </div>
      <GapBanner kind="blocked" labels={labels} messageKey="vendorsGap" />
    </div>
  );
}

export function AutomationsPanel({
  items,
  labels,
  locale,
}: Common & { items: AutomationSummary[] }) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-automations">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'automationsTitle')}</h3>
          <p>{lab(labels, 'automationsSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__list-wrap">
        <table className="mkt-g6__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colName')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colRuns')}</th>
              <th>{lab(labels, 'colLastRun')}</th>
              <th>{lab(labels, 'colEngine')}</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5}>
                  <div className="mkt-g6__empty">{lab(labels, 'empty')}</div>
                </td>
              </tr>
            ) : (
              items.map((a) => (
                <tr key={a.id}>
                  <td>{a.name}</td>
                  <td>
                    <span className={`mkt-g6__status mkt-g6__status--${statusTone(a.status)}`}>{a.status}</span>
                  </td>
                  <td>{a.execution_count}</td>
                  <td>{a.last_run_at ? new Date(a.last_run_at).toLocaleString(locale) : '—'}</td>
                  <td>
                    <ProviderBadge mode={a.execution_engine_available ? 'live' : 'blocked'} labels={labels} />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AiInsightsPanel({
  insights,
  recommendations,
  available,
  labels,
}: {
  insights: AIInsight[];
  recommendations: AIRecommendation[];
  available: boolean;
  labels: Record<string, string>;
}) {
  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-ai-insights">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'aiTitle')}</h3>
          <p>{lab(labels, 'aiSubtitle')}</p>
        </div>
        <DataTag kind={available ? 'partial' : 'blocked'} label={lab(labels, available ? 'partialTag' : 'blockedTag')} />
      </div>
      {!available ? <GapBanner kind="blocked" labels={labels} messageKey="aiUnavailable" /> : null}
      <div className="mkt-g6__insights" style={{ marginTop: '0.5rem' }}>
        {insights.length === 0 && recommendations.length === 0 ? (
          <div className="mkt-g6__empty">{lab(labels, available ? 'aiEmpty' : 'aiUnavailable')}</div>
        ) : (
          <>
            {insights.map((i) => (
              <div key={i.id} className="mkt-g6__insight">
                <strong>{i.title}</strong>
                <span>{i.summary ?? ''}</span>
              </div>
            ))}
            {recommendations.map((r) => (
              <div key={r.id} className="mkt-g6__insight">
                <strong>{r.title}</strong>
                <span>{r.rationale ?? ''}</span>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

export function ReportsPanel({
  overview,
  labels,
  locale,
  onExport,
}: Common & {
  overview: PerformanceOverview | null;
  onExport: (preset: string) => void;
}) {
  const presets = [
    'executive',
    'campaign',
    'attribution',
    'lead_source',
    'funnel',
    'website',
    'seo',
    'content',
    'social',
    'email',
    'paid',
    'roi',
  ];

  return (
    <div className="mkt-g6__panel" data-testid="mkt-g6-reports">
      <div className="mkt-g6__toolbar">
        <div>
          <h3>{lab(labels, 'reportsTitle')}</h3>
          <p>{lab(labels, 'reportsSubtitle')}</p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <div className="mkt-g6__kpis" style={{ marginTop: '0.45rem' }}>
        <article className="mkt-g6__kpi" style={{ cursor: 'default' }}>
          <p>{lab(labels, 'kpiLeads')}</p>
          <strong>{perfVal(overview?.total_leads)}</strong>
        </article>
        <article className="mkt-g6__kpi" style={{ cursor: 'default' }}>
          <p>{lab(labels, 'kpiSpend')}</p>
          <strong>{perfVal(overview?.total_spend)}</strong>
        </article>
        <article className="mkt-g6__kpi" style={{ cursor: 'default' }}>
          <p>{lab(labels, 'kpiConversion')}</p>
          <strong>{perfVal(overview?.avg_conversion_rate)}</strong>
        </article>
      </div>
      <div className="mkt-g6__insights" style={{ marginTop: '0.55rem' }}>
        {presets.map((p) => (
          <div key={p} className="mkt-g6__insight">
            <strong>{lab(labels, `report.${p}`)}</strong>
            <button type="button" className="mkt-g6__btn" style={{ marginTop: '0.35rem' }} onClick={() => onExport(p)}>
              {lab(labels, 'exportReport')}
            </button>
          </div>
        ))}
      </div>
      <p className="mkt-g6__subtitle">{lab(labels, 'reportsNote')} · {locale}</p>
    </div>
  );
}
