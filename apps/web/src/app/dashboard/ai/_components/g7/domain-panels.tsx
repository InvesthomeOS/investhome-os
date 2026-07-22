'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useState } from 'react';

import { BarChart, LineChart, Sparkline } from '@/components/design-system/charts';
import type { AiInsightItem, AttentionItem, SummaryCard } from '@/lib/api/executive';
import type { AiHistoryEntry } from '@/lib/ai/ai-history';
import type { PromptDefinition } from '@/lib/ai/prompt-library';
import type { AiWorkspaceSettings } from '@/lib/ai/ai-settings-store';

import type { AiActionItem } from './action-queue';
import { buildCommandKpis, buildForecastBands, buildMorningBrief, sparkFromBase } from './derive';
import type { DataKind, ProviderState } from './ai-views';
import type { ProviderRow } from './provider-status';
import { modelStatusFromProviders } from './provider-status';

function lab(labels: Record<string, string>, key: string): string {
  return labels[key] ?? key;
}

export function DataTag({ kind, label }: { kind: DataKind; label: string }) {
  return <span className={`ai-g7__data-tag ai-g7__data-tag--${kind}`}>{label}</span>;
}

function ProviderBadge({ state, label }: { state: ProviderState; label: string }) {
  return <span className={`ai-g7__status ai-g7__status--${state}`}>{label}</span>;
}

type Common = {
  labels: Record<string, string>;
  locale: string;
};

export function CommandCenterPanel({
  labels,
  locale,
  summaryCards,
  attention,
  insights,
  onDrill,
}: Common & {
  summaryCards: SummaryCard[];
  attention: AttentionItem[];
  insights: {
    priorities: AiInsightItem[];
    risks: AiInsightItem[];
    opportunities: AiInsightItem[];
  } | null;
  onDrill: (href: string) => void;
}) {
  const kpis = buildCommandKpis({ summaryCards, attention, insights, locale });
  const trend = sparkFromBase(Math.max(attention.length, 3)).map((v, i) => ({
    label: `T${i + 1}`,
    value: v,
  }));
  const bars = [
    { label: lab(labels, 'kpiPriorities'), value: Math.max(insights?.priorities.length ?? 0, 1) },
    { label: lab(labels, 'kpiRisks'), value: Math.max(insights?.risks.length ?? 0, 1) },
    { label: lab(labels, 'kpiCritical'), value: Math.max(attention.filter((a) => a.severity === 'critical').length, 1) },
  ];

  return (
    <div data-testid="ai-g7-command_center">
      <div className="ai-g7__toolbar">
        <div className="ai-g7__toolbar-left">
          <DataTag kind="partial" label={lab(labels, 'partialTag')} />
          <span className="ai-g7__muted" style={{ margin: 0 }}>
            {lab(labels, 'commandNote')}
          </span>
        </div>
      </div>

      <div className="ai-g7__kpis" style={{ marginTop: '0.35rem' }}>
        {kpis.map((kpi) => (
          <button
            key={kpi.id}
            type="button"
            className={`ai-g7__kpi ai-g7__kpi--${kpi.severity}`}
            data-testid={`ai-g7-kpi-${kpi.id}`}
            onClick={() => onDrill(kpi.href)}
          >
            <p>{lab(labels, kpi.labelKey)}</p>
            <strong>{kpi.value}</strong>
            <div className="ai-g7__kpi-spark">
              <Sparkline values={kpi.spark} ariaLabel={lab(labels, kpi.labelKey)} locale={locale} format="compact" />
            </div>
          </button>
        ))}
      </div>

      <div className="ai-g7__charts" style={{ marginTop: '0.65rem' }}>
        <div className="ai-g7__chart-card">
          <h4>{lab(labels, 'chartAttentionTrend')}</h4>
          <LineChart data={trend} ariaLabel={lab(labels, 'chartAttentionTrend')} locale={locale} format="compact" height={140} />
        </div>
        <div className="ai-g7__chart-card">
          <h4>{lab(labels, 'chartSignalMix')}</h4>
          <BarChart data={bars} ariaLabel={lab(labels, 'chartSignalMix')} locale={locale} />
        </div>
      </div>

      <div className="ai-g7__panel" style={{ marginTop: '0.65rem' }}>
        <h3>{lab(labels, 'signalFeedTitle')}</h3>
        <p>{lab(labels, 'signalFeedSubtitle')}</p>
        {!insights && attention.length === 0 ? (
          <div className="ai-g7__empty">{lab(labels, 'empty')}</div>
        ) : (
          <ul className="ai-g7__list">
            {[...(insights?.priorities ?? []), ...(insights?.risks ?? [])].slice(0, 6).map((item, idx) => (
              <li
                key={`${item.kind}-${idx}`}
                className={`ai-g7__list-item ai-g7__list-item--${item.severity === 'critical' ? 'critical' : item.severity === 'warning' ? 'warn' : 'info'}`}
              >
                <strong>{lab(labels, 'signalItem')} · {item.kind}</strong>
                <span className="ai-g7__meta">{item.title_key}</span>
                <div className="ai-g7__chips">
                  <Link href={`/${item.link_module}`.replace(/^\/dashboard/, '/dashboard') as Route} className="ai-g7__btn ai-g7__btn--ghost">
                    {lab(labels, 'openSource')}
                  </Link>
                </div>
                <div className="ai-g7__explain">{lab(labels, 'explainRuleBased')}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function MorningBriefPanel({
  labels,
  attention,
  insights,
  approvalsCount,
  overdueCount,
}: Common & {
  attention: AttentionItem[];
  insights: {
    priorities: AiInsightItem[];
    risks: AiInsightItem[];
    opportunities: AiInsightItem[];
  } | null;
  approvalsCount: number;
  overdueCount: number;
}) {
  const sections = buildMorningBrief({ attention, insights, approvalsCount, overdueCount });

  return (
    <div data-testid="ai-g7-morning_brief">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'briefTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'briefSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>

      <div className="ai-g7__panel" style={{ marginTop: '0.45rem' }}>
        <h3>{lab(labels, 'briefExecSummary')}</h3>
        <p>{lab(labels, 'briefExecSummaryBody')}</p>
      </div>

      <div className="ai-g7__grid" style={{ marginTop: '0.55rem' }}>
        {sections.map((section) => (
          <article key={section.theme} className="ai-g7__panel ai-g7__span-6" data-testid={`ai-g7-brief-${section.theme}`}>
            <div className="ai-g7__toolbar">
              <h3 style={{ margin: 0 }}>{lab(labels, `theme.${section.theme}.title`)}</h3>
              <DataTag
                kind={section.live ? 'live' : 'demo'}
                label={lab(labels, section.live ? 'liveTag' : 'demoTag')}
              />
            </div>
            <p>{lab(labels, `theme.${section.theme}.body`)}</p>
            <span className="ai-g7__meta">
              {lab(labels, 'signalCount')}: {section.count} · {section.severity}
            </span>
            <div className="ai-g7__chips" style={{ marginTop: '0.35rem' }}>
              <Link href={section.evidenceHref as Route} className="ai-g7__btn ai-g7__btn--ghost">
                {lab(labels, 'evidenceLink')} → {section.evidenceLabel}
              </Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export function CopilotPanel({
  labels,
  locale,
  canUse,
  pending,
  messages,
  input,
  onInput,
  onAsk,
  onClear,
}: Common & {
  canUse: boolean;
  pending: boolean;
  messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    placeholder?: boolean;
    sources?: Array<{ href: string; label: string }>;
  }>;
  input: string;
  onInput: (v: string) => void;
  onAsk: (q: string) => void;
  onClear: () => void;
}) {
  return (
    <div data-testid="ai-g7-copilot">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'copilotTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'copilotSubtitle')}
          </p>
        </div>
        <div className="ai-g7__toolbar-right">
          <DataTag kind="partial" label={lab(labels, 'partialTag')} />
          <button type="button" className="ai-g7__btn ai-g7__btn--ghost" onClick={onClear}>
            {lab(labels, 'clearChat')}
          </button>
        </div>
      </div>

      <p className="ai-g7__banner ai-g7__banner--info">{lab(labels, 'copilotPermissions')}</p>

      <div className="ai-g7__chips">
        {(['priorities', 'pipeline', 'investors', 'risks'] as const).map((key) => (
          <button
            key={key}
            type="button"
            className="ai-g7__btn"
            disabled={pending || !canUse}
            onClick={() => onAsk(lab(labels, `copilotPrompt.${key}`))}
          >
            {lab(labels, `copilotChip.${key}`)}
          </button>
        ))}
      </div>

      <div className="ai-g7__chat" style={{ marginTop: '0.55rem' }}>
        {messages.length === 0 ? (
          <div className="ai-g7__empty">{lab(labels, 'copilotEmpty')}</div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className={`ai-g7__msg ai-g7__msg--${msg.role}`}>
              {msg.content}
              {msg.placeholder ? (
                <div className="ai-g7__meta" style={{ marginTop: '0.35rem' }}>
                  {lab(labels, 'placeholderBadge')}
                </div>
              ) : null}
              {msg.sources && msg.sources.length > 0 ? (
                <div className="ai-g7__sources">
                  {msg.sources.map((s) => (
                    <Link key={s.href} href={s.href as Route} className="ai-g7__btn ai-g7__btn--ghost">
                      {lab(labels, 'source')}: {s.label}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          ))
        )}
        {pending ? <div className="ai-g7__meta">{lab(labels, 'thinking')}</div> : null}
      </div>

      <div className="ai-g7__composer">
        <input
          className="ai-g7__field"
          value={input}
          onChange={(e) => onInput(e.target.value)}
          placeholder={lab(labels, 'copilotPlaceholder')}
          disabled={!canUse || pending}
          onKeyDown={(e) => {
            if (e.key === 'Enter') onAsk(input);
          }}
          data-testid="ai-g7-copilot-input"
        />
        <button
          type="button"
          className="ai-g7__btn ai-g7__btn--primary"
          disabled={!canUse || pending || !input.trim()}
          onClick={() => onAsk(input)}
          data-testid="ai-g7-copilot-ask"
        >
          {lab(labels, 'ask')}
        </button>
      </div>
      <p className="ai-g7__meta">{lab(labels, 'localeHint')}: {locale === 'tr' ? 'TR' : 'EN'}</p>
    </div>
  );
}

export function ActionCenterPanel({
  labels,
  items,
  onApprove,
  onDismiss,
  onConvert,
  onRequestApproval,
}: Common & {
  items: AiActionItem[];
  onApprove: (id: string) => void;
  onDismiss: (id: string) => void;
  onConvert: (id: string) => void;
  onRequestApproval: (id: string) => void;
}) {
  const open = items.filter((i) => i.status === 'pending' || i.status === 'awaiting_approval');

  return (
    <div data-testid="ai-g7-action_center">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'actionsTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'actionsSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>

      <p className="ai-g7__banner">{lab(labels, 'actionsApprovalBanner')}</p>

      {open.length === 0 ? (
        <div className="ai-g7__empty">{lab(labels, 'actionsEmpty')}</div>
      ) : (
        <ul className="ai-g7__list">
          {open.map((item) => (
            <li
              key={item.id}
              className={`ai-g7__list-item ai-g7__list-item--${item.severity === 'critical' ? 'critical' : item.severity === 'warning' ? 'warn' : 'info'}`}
              data-testid={`ai-g7-action-${item.id}`}
            >
              <strong>{lab(labels, `nba.${item.titleKey}`)}</strong>
              <span>{lab(labels, `nba.${item.rationaleKey}`)}</span>
              <div className="ai-g7__explain">
                <strong>{lab(labels, 'whyRecommended')}</strong>
                <div>{lab(labels, `nba.${item.explanationKey}`)}</div>
                <div className="ai-g7__meta">
                  {lab(labels, 'confidence')}: {item.confidence}
                  {item.sensitive ? ` · ${lab(labels, 'sensitiveLabel')}: ${lab(labels, `sensitive.${item.sensitive}`)}` : ''}
                </div>
              </div>
              <div className="ai-g7__chips">
                <Link href={item.sourceHref as Route} className="ai-g7__btn ai-g7__btn--ghost">
                  {lab(labels, 'openSource')}
                </Link>
                {item.sensitive && item.status === 'awaiting_approval' ? (
                  <button
                    type="button"
                    className="ai-g7__btn ai-g7__btn--primary"
                    data-testid={`ai-g7-approve-${item.id}`}
                    onClick={() => onRequestApproval(item.id)}
                  >
                    {lab(labels, 'requestApproval')}
                  </button>
                ) : (
                  <button
                    type="button"
                    className="ai-g7__btn ai-g7__btn--primary"
                    data-testid={`ai-g7-accept-${item.id}`}
                    onClick={() => onApprove(item.id)}
                  >
                    {lab(labels, 'accept')}
                  </button>
                )}
                <button type="button" className="ai-g7__btn" onClick={() => onConvert(item.id)}>
                  {lab(labels, 'convertTask')}
                </button>
                <button type="button" className="ai-g7__btn ai-g7__btn--danger" onClick={() => onDismiss(item.id)}>
                  {lab(labels, 'dismiss')}
                </button>
              </div>
              {item.status === 'awaiting_approval' ? (
                <span className="ai-g7__meta">{lab(labels, 'awaitingApproval')}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function DomainIntelPanel({
  labels,
  locale,
  viewId,
  titleKey,
  subtitleKey,
  kind,
  metrics,
  items,
  href,
}: Common & {
  viewId: string;
  titleKey: string;
  subtitleKey: string;
  kind: DataKind;
  metrics: Array<{ label: string; value: string; spark?: number[] }>;
  items: Array<{ title: string; body: string; href?: string; severity?: string }>;
  href: string;
}) {
  return (
    <div data-testid={`ai-g7-${viewId}`}>
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, titleKey)}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, subtitleKey)}
          </p>
        </div>
        <div className="ai-g7__toolbar-right">
          <DataTag kind={kind} label={lab(labels, `${kind}Tag`)} />
          <Link href={href as Route} className="ai-g7__btn">
            {lab(labels, 'openWorkspace')}
          </Link>
        </div>
      </div>

      <div className="ai-g7__kpis" style={{ marginTop: '0.45rem' }}>
        {metrics.map((m) => (
          <article key={m.label} className="ai-g7__kpi ai-g7__kpi--info">
            <p>{m.label}</p>
            <strong>{m.value}</strong>
            {m.spark ? (
              <div className="ai-g7__kpi-spark">
                <Sparkline values={m.spark} ariaLabel={m.label} locale={locale} format="compact" />
              </div>
            ) : null}
          </article>
        ))}
      </div>

      <div className="ai-g7__panel" style={{ marginTop: '0.55rem' }}>
        <h3>{lab(labels, 'recommendationsTitle')}</h3>
        <p>{lab(labels, 'recommendationsSubtitle')}</p>
        {items.length === 0 ? (
          <div className="ai-g7__empty">{lab(labels, 'empty')}</div>
        ) : (
          <ul className="ai-g7__list">
            {items.map((item, idx) => (
              <li
                key={`${item.title}-${idx}`}
                className={`ai-g7__list-item ai-g7__list-item--${item.severity === 'critical' ? 'critical' : item.severity === 'warn' ? 'warn' : 'info'}`}
              >
                <strong>{item.title}</strong>
                <span>{item.body}</span>
                <div className="ai-g7__explain">{lab(labels, 'explainDomain')}</div>
                {item.href ? (
                  <Link href={item.href as Route} className="ai-g7__btn ai-g7__btn--ghost">
                    {lab(labels, 'openSource')}
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function DocumentIntelPanel({
  labels,
  docs,
  onRequestReview,
}: Common & {
  docs: Array<{ id: string; title: string; status: string; confidence?: string | null }>;
  onRequestReview: (id: string) => void;
}) {
  return (
    <div data-testid="ai-g7-document_intel">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'docsTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'docsSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <p className="ai-g7__banner">{lab(labels, 'docsHumanReview')}</p>
      <div className="ai-g7__table-wrap">
        <table className="ai-g7__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colDocument')}</th>
              <th>{lab(labels, 'colStatus')}</th>
              <th>{lab(labels, 'colConfidence')}</th>
              <th>{lab(labels, 'colAction')}</th>
            </tr>
          </thead>
          <tbody>
            {docs.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="ai-g7__empty">{lab(labels, 'docsEmpty')}</div>
                </td>
              </tr>
            ) : (
              docs.map((doc) => (
                <tr key={doc.id}>
                  <td>{doc.title}</td>
                  <td>{doc.status}</td>
                  <td className="ai-g7__meta">{doc.confidence ?? '—'}</td>
                  <td>
                    <button type="button" className="ai-g7__btn ai-g7__btn--primary" onClick={() => onRequestReview(doc.id)}>
                      {lab(labels, 'requestHumanReview')}
                    </button>
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

export function MeetingIntelPanel({ labels }: Common) {
  const meetings = [
    { id: 'm1', titleKey: 'meetingBoard', when: '09:30', prep: true },
    { id: 'm2', titleKey: 'meetingInvestor', when: '14:00', prep: true },
    { id: 'm3', titleKey: 'meetingSite', when: '16:30', prep: false },
  ];

  return (
    <div data-testid="ai-g7-meeting_intel">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'meetingsTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'meetingsSubtitle')}
          </p>
        </div>
        <DataTag kind="demo" label={lab(labels, 'demoTag')} />
      </div>
      <p className="ai-g7__banner ai-g7__banner--gap">{lab(labels, 'meetingsNoAutoSend')}</p>
      <ul className="ai-g7__list">
        {meetings.map((m) => (
          <li key={m.id} className="ai-g7__list-item">
            <strong>{lab(labels, m.titleKey)}</strong>
            <span className="ai-g7__meta">{m.when}</span>
            <div className="ai-g7__chips">
              <button type="button" className="ai-g7__btn">
                {lab(labels, 'openPrepBrief')}
              </button>
              <button type="button" className="ai-g7__btn" disabled title={lab(labels, 'meetingsNoAutoSend')}>
                {lab(labels, 'draftNotes')}
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ForecastsPanel({ labels, locale, base }: Common & { base: number }) {
  const bands = buildForecastBands(base, locale);
  const line = bands.map((b) => ({ label: b.label, value: b.mid }));

  return (
    <div data-testid="ai-g7-forecasts">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'forecastTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'forecastSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <p className="ai-g7__banner ai-g7__banner--info">{lab(labels, 'forecastHonesty')}</p>
      <div className="ai-g7__charts">
        <div className="ai-g7__chart-card">
          <h4>{lab(labels, 'forecastMidline')}</h4>
          <LineChart data={line} ariaLabel={lab(labels, 'forecastMidline')} locale={locale} format="compact" height={150} />
        </div>
        <div className="ai-g7__chart-card">
          <h4>{lab(labels, 'forecastBands')}</h4>
          <div className="ai-g7__confidence">
            {bands.map((b) => {
              const max = Math.max(...bands.map((x) => x.high));
              const left = (b.low / max) * 100;
              const width = ((b.high - b.low) / max) * 100;
              const mid = (b.mid / max) * 100;
              return (
                <div key={b.label} className="ai-g7__band">
                  <span>{b.label}</span>
                  <div className="ai-g7__band-track">
                    <div className="ai-g7__band-range" style={{ left: `${left}%`, width: `${width}%` }} />
                    <div className="ai-g7__band-mid" style={{ left: `${mid}%` }} />
                  </div>
                  <span className="ai-g7__meta">
                    {Math.round(b.low)}–{Math.round(b.high)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export function RiskCenterPanel({
  labels,
  risks,
}: Common & {
  risks: Array<{ id: string; title: string; body: string; severity: string; href: string }>;
}) {
  return (
    <div data-testid="ai-g7-risk_center">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'riskTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'riskSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      {risks.length === 0 ? (
        <div className="ai-g7__empty">{lab(labels, 'riskEmpty')}</div>
      ) : (
        <ul className="ai-g7__list">
          {risks.map((r) => (
            <li
              key={r.id}
              className={`ai-g7__list-item ai-g7__list-item--${r.severity === 'critical' ? 'critical' : 'warn'}`}
            >
              <strong>{r.title}</strong>
              <span>{r.body}</span>
              <div className="ai-g7__explain">{lab(labels, 'explainRisk')}</div>
              <Link href={r.href as Route} className="ai-g7__btn ai-g7__btn--primary">
                {lab(labels, 'mitigate')}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function AiSearchPanel({
  labels,
  query,
  onQuery,
  pending,
  results,
  onSearch,
}: Common & {
  query: string;
  onQuery: (v: string) => void;
  pending: boolean;
  results: Array<{ id: string; title: string; snippet: string; href: string; source: string }>;
  onSearch: () => void;
}) {
  return (
    <div data-testid="ai-g7-ai_search">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'searchTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'searchSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="ai-g7__composer">
        <input
          className="ai-g7__field"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={lab(labels, 'searchPlaceholder')}
          data-testid="ai-g7-search-input"
          onKeyDown={(e) => {
            if (e.key === 'Enter') onSearch();
          }}
        />
        <button type="button" className="ai-g7__btn ai-g7__btn--primary" disabled={pending} onClick={onSearch}>
          {lab(labels, 'search')}
        </button>
      </div>
      {pending ? <p className="ai-g7__meta">{lab(labels, 'searching')}</p> : null}
      <ul className="ai-g7__list" style={{ marginTop: '0.55rem' }}>
        {results.map((r) => (
          <li key={r.id} className="ai-g7__list-item">
            <strong>{r.title}</strong>
            <span>{r.snippet}</span>
            <span className="ai-g7__meta">{r.source}</span>
            <Link href={r.href as Route} className="ai-g7__btn ai-g7__btn--ghost">
              {lab(labels, 'openSource')}
            </Link>
          </li>
        ))}
        {!pending && results.length === 0 ? <li className="ai-g7__empty">{lab(labels, 'searchEmpty')}</li> : null}
      </ul>
    </div>
  );
}

export function PromptLibraryPanel({
  labels,
  prompts,
  favorites,
  category,
  onCategory,
  onToggleFavorite,
  onRun,
  auditNote,
}: Common & {
  prompts: PromptDefinition[];
  favorites: Set<string>;
  category: string;
  onCategory: (c: string) => void;
  onToggleFavorite: (id: string) => void;
  onRun: (prompt: PromptDefinition) => void;
  auditNote: string;
}) {
  const cats = ['all', 'favorites', 'executive', 'sales', 'marketing', 'finance', 'investor', 'projects', 'documents'];
  const filtered = prompts.filter((p) => {
    if (category === 'all') return true;
    if (category === 'favorites') return favorites.has(p.id);
    return p.category === category;
  });

  return (
    <div data-testid="ai-g7-prompt_library">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'promptsTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'promptsSubtitle')}
          </p>
        </div>
        <DataTag kind="live" label={lab(labels, 'liveTag')} />
      </div>
      <p className="ai-g7__banner ai-g7__banner--gap">{auditNote}</p>
      <div className="ai-g7__chips">
        {cats.map((c) => (
          <button
            key={c}
            type="button"
            className={`ai-g7__btn${category === c ? ' ai-g7__btn--primary' : ''}`}
            onClick={() => onCategory(c)}
          >
            {lab(labels, `promptCat.${c}`)}
          </button>
        ))}
      </div>
      <ul className="ai-g7__list" style={{ marginTop: '0.55rem' }}>
        {filtered.map((p) => (
          <li key={p.id} className="ai-g7__list-item">
            <strong>{lab(labels, `promptItem.${p.titleKey}`)}</strong>
            <span className="ai-g7__meta">{p.category}</span>
            <div className="ai-g7__chips">
              <button type="button" className="ai-g7__btn ai-g7__btn--primary" onClick={() => onRun(p)}>
                {lab(labels, 'runPrompt')}
              </button>
              <button type="button" className="ai-g7__btn" onClick={() => onToggleFavorite(p.id)}>
                {favorites.has(p.id) ? lab(labels, 'unfavorite') : lab(labels, 'favorite')}
              </button>
            </div>
          </li>
        ))}
        {filtered.length === 0 ? <li className="ai-g7__empty">{lab(labels, 'promptsEmpty')}</li> : null}
      </ul>
    </div>
  );
}

export function ActivityLogPanel({
  labels,
  locale,
  history,
}: Common & { history: AiHistoryEntry[] }) {
  return (
    <div data-testid="ai-g7-activity_log">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'activityTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'activitySubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <p className="ai-g7__banner ai-g7__banner--gap">{lab(labels, 'activityLocalNote')}</p>
      {history.length === 0 ? (
        <div className="ai-g7__empty">{lab(labels, 'activityEmpty')}</div>
      ) : (
        <ul className="ai-g7__list">
          {history.slice(0, 40).map((h) => (
            <li key={h.id} className="ai-g7__list-item">
              <strong>{h.title}</strong>
              <span className="ai-g7__meta">
                {h.source} · {new Date(h.createdAt).toLocaleString(locale)}
                {h.placeholder ? ` · ${lab(labels, 'placeholderBadge')}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function SettingsPanel({
  labels,
  settings,
  canManage,
  onChange,
  onSave,
  saved,
}: Common & {
  settings: AiWorkspaceSettings;
  canManage: boolean;
  onChange: (next: AiWorkspaceSettings) => void;
  onSave: () => void;
  saved: boolean;
}) {
  return (
    <div data-testid="ai-g7-settings">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'settingsTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'settingsSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <p className="ai-g7__banner ai-g7__banner--info">{lab(labels, 'settingsNoSecrets')}</p>
      {!canManage ? <p className="ai-g7__empty">{lab(labels, 'settingsReadOnly')}</p> : null}
      <div className="ai-g7__field-row">
        <label>
          {lab(labels, 'settingsModel')}
          <select
            className="ai-g7__field"
            disabled={!canManage}
            value={settings.model}
            onChange={(e) => onChange({ ...settings, model: e.target.value })}
          >
            <option value="platform-default">{lab(labels, 'modelDefault')}</option>
            <option value="local-heuristic">{lab(labels, 'modelLocal')}</option>
          </select>
        </label>
        <label>
          {lab(labels, 'settingsProvider')}
          <select
            className="ai-g7__field"
            disabled={!canManage}
            value={settings.provider}
            onChange={(e) => onChange({ ...settings, provider: e.target.value })}
          >
            <option value="local">{lab(labels, 'providerLocal')}</option>
            <option value="azure">{lab(labels, 'providerAzure')}</option>
          </select>
        </label>
        <label>
          {lab(labels, 'settingsLanguage')}
          <select
            className="ai-g7__field"
            disabled={!canManage}
            value={settings.language}
            onChange={(e) => onChange({ ...settings, language: e.target.value as AiWorkspaceSettings['language'] })}
          >
            <option value="auto">{lab(labels, 'languageAuto')}</option>
            <option value="tr">TR</option>
            <option value="en">EN</option>
          </select>
        </label>
        <label>
          {lab(labels, 'settingsLength')}
          <select
            className="ai-g7__field"
            disabled={!canManage}
            value={settings.responseLength}
            onChange={(e) =>
              onChange({ ...settings, responseLength: e.target.value as AiWorkspaceSettings['responseLength'] })
            }
          >
            <option value="concise">{lab(labels, 'lengthConcise')}</option>
            <option value="balanced">{lab(labels, 'lengthBalanced')}</option>
            <option value="detailed">{lab(labels, 'lengthDetailed')}</option>
          </select>
        </label>
      </div>
      <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', fontSize: '0.75rem' }}>
        <input
          type="checkbox"
          disabled={!canManage}
          checked={settings.allowExternal}
          onChange={(e) => onChange({ ...settings, allowExternal: e.target.checked })}
        />
        {lab(labels, 'allowExternal')}
      </label>
      <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', fontSize: '0.75rem', marginTop: '0.35rem' }}>
        <input
          type="checkbox"
          disabled={!canManage}
          checked={settings.shareOrgContext}
          onChange={(e) => onChange({ ...settings, shareOrgContext: e.target.checked })}
        />
        {lab(labels, 'shareOrgContext')}
      </label>
      {canManage ? (
        <div style={{ marginTop: '0.75rem' }}>
          <button type="button" className="ai-g7__btn ai-g7__btn--primary" onClick={onSave}>
            {lab(labels, 'saveSettings')}
          </button>
          {saved ? <span className="ai-g7__meta"> {lab(labels, 'savedLocal')}</span> : null}
        </div>
      ) : null}
    </div>
  );
}

export function ProviderStatusPanel({
  labels,
  rows,
}: Common & { rows: ProviderRow[] }) {
  const model = modelStatusFromProviders(rows);

  return (
    <div data-testid="ai-g7-provider_status">
      <div className="ai-g7__toolbar">
        <div>
          <h3 style={{ margin: 0 }}>{lab(labels, 'providersTitle')}</h3>
          <p className="ai-g7__muted" style={{ margin: '0.2rem 0 0' }}>
            {lab(labels, 'providersSubtitle')}
          </p>
        </div>
        <DataTag kind="partial" label={lab(labels, 'partialTag')} />
      </div>
      <div className="ai-g7__panel">
        <h3>{lab(labels, 'modelStatusTitle')}</h3>
        <p>
          {lab(labels, model.modelKey)} · <ProviderBadge state={model.state} label={lab(labels, `providerState.${model.state}`)} />
        </p>
        <p className="ai-g7__muted">{lab(labels, model.noteKey)}</p>
      </div>
      <div className="ai-g7__table-wrap" style={{ marginTop: '0.55rem' }}>
        <table className="ai-g7__table">
          <thead>
            <tr>
              <th>{lab(labels, 'colProvider')}</th>
              <th>{lab(labels, 'colCapability')}</th>
              <th>{lab(labels, 'colState')}</th>
              <th>{lab(labels, 'colDetail')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} data-testid={`ai-g7-provider-${row.id}`}>
                <td>{lab(labels, row.nameKey)}</td>
                <td className="ai-g7__meta">{row.capability}</td>
                <td>
                  <ProviderBadge state={row.state} label={lab(labels, `providerState.${row.state}`)} />
                </td>
                <td>
                  {lab(labels, row.detailKey)}
                  {row.requiredEnv.length > 0 ? (
                    <div className="ai-g7__meta">{row.requiredEnv.join(', ')}</div>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Approval confirm modal for sensitive actions */
export function ApprovalGateModal({
  labels,
  open,
  actionLabel,
  onConfirm,
  onCancel,
}: {
  labels: Record<string, string>;
  open: boolean;
  actionLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const [ack, setAck] = useState(false);
  if (!open) return null;
  return (
    <div className="ai-g7" style={{ position: 'fixed', inset: 0, zIndex: 90, background: 'rgba(23,20,18,0.35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="ai-g7__panel" style={{ width: 'min(420px, 92vw)' }} data-testid="ai-g7-approval-modal">
        <h3>{lab(labels, 'approvalTitle')}</h3>
        <p>{lab(labels, 'approvalBody')}</p>
        <p className="ai-g7__meta">{actionLabel}</p>
        <label style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', fontSize: '0.75rem' }}>
          <input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} data-testid="ai-g7-approval-ack" />
          {lab(labels, 'approvalAck')}
        </label>
        <div className="ai-g7__chips" style={{ marginTop: '0.75rem' }}>
          <button type="button" className="ai-g7__btn ai-g7__btn--primary" disabled={!ack} onClick={onConfirm} data-testid="ai-g7-approval-confirm">
            {lab(labels, 'approvalConfirm')}
          </button>
          <button type="button" className="ai-g7__btn" onClick={onCancel}>
            {lab(labels, 'cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
