'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useLocale, useTranslations } from 'next-intl';

import { AiWorkspaceShell } from '@/app/dashboard/ai/_components/ai-workspace-shell';
import { useAiCopilot } from '@/lib/ai/ai-copilot-context';
import { groupHistoryByDate, loadAiHistory, type AiHistoryEntry } from '@/lib/ai/ai-history';
import { canViewAiWorkspace } from '@/lib/ai/ai-permissions';
import { loadFavoritePromptIds, PROMPT_LIBRARY } from '@/lib/ai/prompt-library';
import {
  fetchExecutiveAiInsights,
  fetchExecutiveAttention,
  fetchExecutiveSummary,
  type AiInsightItem,
  type AttentionItem,
  type SummaryCard,
} from '@/lib/api/executive';
import { useAuth } from '@/lib/auth/auth-context';

function stripKey(key: string): string {
  return key.replace(/^executive\./, '');
}

export function AiHomeWorkspace() {
  const t = useTranslations('ai');
  const tHome = useTranslations('ai.home');
  const tPrompts = useTranslations('ai.prompts');
  const tItems = useTranslations('ai.prompts.items');
  const tExec = useTranslations('executive');
  const locale = useLocale();
  const { user, loading: authLoading } = useAuth();
  const { openCopilot } = useAiCopilot();

  const [insights, setInsights] = useState<{
    priorities: AiInsightItem[];
    risks: AiInsightItem[];
    opportunities: AiInsightItem[];
    ai_level: string;
  } | null>(null);
  const [attention, setAttention] = useState<AttentionItem[]>([]);
  const [summaryCards, setSummaryCards] = useState<SummaryCard[]>([]);
  const [history, setHistory] = useState<AiHistoryEntry[]>([]);
  const [favorites, setFavorites] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    setFavorites(loadFavoritePromptIds());
    setHistory(loadAiHistory(null, user?.id));
  }, [user?.id]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [ai, att, sum] = await Promise.all([
          fetchExecutiveAiInsights({}),
          fetchExecutiveAttention({}).catch(() => ({ items: [] as AttentionItem[] })),
          fetchExecutiveSummary({}).catch(() => ({ cards: [] as SummaryCard[] })),
        ]);
        if (cancelled) return;
        setInsights(ai);
        setAttention(att.items.slice(0, 5));
        setSummaryCards(sum.cards.slice(0, 4));
        setUnavailable(false);
      } catch {
        if (!cancelled) setUnavailable(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const savedPrompts = useMemo(
    () => PROMPT_LIBRARY.filter((p) => favorites.has(p.id)).slice(0, 6),
    [favorites],
  );

  const recentGrouped = useMemo(
    () => groupHistoryByDate(history, locale).slice(0, 2),
    [history, locale],
  );

  if (authLoading) {
    return (
      <AiWorkspaceShell title={tHome('title')} subtitle={tHome('subtitle')}>
        <p className="ai-workspace__empty">{t('loading')}</p>
      </AiWorkspaceShell>
    );
  }

  if (!canViewAiWorkspace(user)) {
    return (
      <AiWorkspaceShell title={tHome('title')} subtitle={tHome('subtitle')}>
        <div className="ih-panel">
          <div className="ih-panel__body">
            <p className="ai-workspace__empty">{t('accessDenied')}</p>
          </div>
        </div>
      </AiWorkspaceShell>
    );
  }

  return (
    <AiWorkspaceShell
      title={tHome('title')}
      subtitle={tHome('subtitle')}
      actions={
        <button type="button" className="ih-btn ih-btn--primary" onClick={() => openCopilot()}>
          {tHome('openCopilot')}
        </button>
      }
    >
      <p className="ai-workspace__disclaimer">{tHome('disclaimer')}</p>

      <div className="ai-workspace__grid">
        <section className="ih-panel ai-workspace__span-7">
          <header className="ih-panel__header">
            <h2 className="ih-panel__title">{tHome('insightsTitle')}</h2>
          </header>
          <div className="ih-panel__body">
            {loading ? (
              <p className="ai-workspace__meta">{t('loading')}</p>
            ) : unavailable || !insights ? (
              <p className="ai-workspace__empty">{tHome('insightsUnavailable')}</p>
            ) : (
              <ul className="ai-workspace__list">
                {[...insights.priorities, ...insights.risks].slice(0, 5).map((item, idx) => (
                  <li key={`${item.kind}-${item.title_key}-${idx}`} className="ai-workspace__list-item">
                    <strong>
                      {tExec(stripKey(item.title_key) as 'aiPanel.deadline_priority.title')}
                    </strong>
                    <span>
                      {tExec(stripKey(item.description_key) as 'aiPanel.deadline_priority.description')}
                    </span>
                    <span className="ai-workspace__meta">
                      {item.kind} · L2 · {insights.ai_level}
                    </span>
                  </li>
                ))}
                {insights.priorities.length + insights.risks.length === 0 ? (
                  <li className="ai-workspace__empty">{tHome('insightsEmpty')}</li>
                ) : null}
              </ul>
            )}
          </div>
        </section>

        <section className="ih-panel ai-workspace__span-5">
          <header className="ih-panel__header">
            <h2 className="ih-panel__title">{tHome('actionsTitle')}</h2>
          </header>
          <div className="ih-panel__body">
            {attention.length === 0 && !loading ? (
              <p className="ai-workspace__empty">{tHome('actionsEmpty')}</p>
            ) : (
              <ul className="ai-workspace__list">
                {attention.map((item) => (
                  <li key={`${item.entity_type}-${item.entity_id}`} className="ai-workspace__list-item">
                    <strong>
                      {tExec(stripKey(item.title_key) as 'attention.overdue_payment.title')}
                    </strong>
                    <span>{item.related_label || item.severity}</span>
                    <Link
                      href={`/dashboard/${item.link_module}` as Route}
                      className="ih-btn ih-btn--ghost ai-workspace__chip"
                    >
                      {tHome('openModule')}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="ih-panel ai-workspace__span-6">
          <header className="ih-panel__header">
            <h2 className="ih-panel__title">{tHome('summaryTitle')}</h2>
          </header>
          <div className="ih-panel__body">
            {summaryCards.length === 0 ? (
              <p className="ai-workspace__empty">{tHome('summaryEmpty')}</p>
            ) : (
              <ul className="ai-workspace__list">
                {summaryCards.map((card) => (
                  <li key={card.key} className="ai-workspace__list-item">
                    <strong>
                      {tExec(`companyOverview.${card.key}` as 'companyOverview.active_projects')}
                    </strong>
                    <span>
                      {card.value === null || card.value === undefined
                        ? t('unavailableMetric')
                        : String(card.value)}
                    </span>
                    <span className="ai-workspace__meta">{tHome('verifiedSource')}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="ih-panel ai-workspace__span-6">
          <header className="ih-panel__header">
            <h2 className="ih-panel__title">{tHome('activityTitle')}</h2>
            <Link href={'/dashboard/ai/history' as Route} className="ih-btn ih-btn--ghost">
              {tHome('viewHistory')}
            </Link>
          </header>
          <div className="ih-panel__body">
            {recentGrouped.length === 0 ? (
              <p className="ai-workspace__empty">{tHome('activityEmpty')}</p>
            ) : (
              recentGrouped.map((group) => (
                <div key={group.dateKey} className="ai-history__group">
                  <h3>{group.dateLabel}</h3>
                  <ul className="ai-workspace__list">
                    {group.items.slice(0, 3).map((item) => (
                      <li key={item.id} className="ai-workspace__list-item">
                        <strong>{item.title}</strong>
                        <span className="ai-workspace__meta">
                          {item.source}
                          {item.placeholder ? ` · ${tHome('placeholderTag')}` : ''}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="ih-panel ai-workspace__span-6">
          <header className="ih-panel__header">
            <h2 className="ih-panel__title">{tHome('quickPromptsTitle')}</h2>
          </header>
          <div className="ih-panel__body">
            <div className="ai-workspace__chips">
              {PROMPT_LIBRARY.slice(0, 6).map((prompt) => (
                <button
                  key={prompt.id}
                  type="button"
                  className="ih-btn ih-btn--secondary ai-workspace__chip"
                  onClick={() => openCopilot(tItems(prompt.promptKey as 'execPrioritiesPrompt'))}
                >
                  {tItems(prompt.titleKey as 'execPriorities')}
                </button>
              ))}
            </div>
          </div>
        </section>

        <section className="ih-panel ai-workspace__span-6">
          <header className="ih-panel__header">
            <h2 className="ih-panel__title">{tHome('savedPromptsTitle')}</h2>
            <Link href={'/dashboard/ai/prompts' as Route} className="ih-btn ih-btn--ghost">
              {tPrompts('title')}
            </Link>
          </header>
          <div className="ih-panel__body">
            {savedPrompts.length === 0 ? (
              <p className="ai-workspace__empty">{tHome('savedEmpty')}</p>
            ) : (
              <ul className="ai-workspace__list">
                {savedPrompts.map((prompt) => (
                  <li key={prompt.id} className="ai-workspace__list-item">
                    <strong>{tItems(prompt.titleKey as 'execPriorities')}</strong>
                    <button
                      type="button"
                      className="ih-btn ih-btn--ghost ai-workspace__chip"
                      onClick={() => openCopilot(tItems(prompt.promptKey as 'execPrioritiesPrompt'))}
                    >
                      {tHome('runPrompt')}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </AiWorkspaceShell>
  );
}
