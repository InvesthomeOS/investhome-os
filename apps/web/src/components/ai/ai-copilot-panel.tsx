'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAiCopilot } from '@/lib/ai/ai-copilot-context';
import { appendAiHistory } from '@/lib/ai/ai-history';
import { canUseAiWorkspace } from '@/lib/ai/ai-permissions';
import { runPlatformAiQuery } from '@/lib/ai/run-ai-query';
import { useAuth } from '@/lib/auth/auth-context';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  placeholder?: boolean;
};

const SUGGESTED_KEYS = [
  'priorities',
  'salesPipeline',
  'investorActivity',
  'overdueTasks',
  'marketingPerformance',
  'projectRisks',
] as const;

export function AiCopilotPanel() {
  const t = useTranslations('ai.copilot');
  const tPrompts = useTranslations('ai.prompts.items');
  const { user } = useAuth();
  const { copilotOpen, closeCopilot, seedPrompt, clearSeedPrompt } = useAiCopilot();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (seedPrompt && copilotOpen) {
      setInput(seedPrompt);
      clearSeedPrompt();
    }
  }, [seedPrompt, copilotOpen, clearSeedPrompt]);

  if (!copilotOpen) return null;

  async function ask(query: string) {
    const trimmed = query.trim();
    if (!trimmed || pending || !canUseAiWorkspace(user)) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: trimmed };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setPending(true);

    try {
      const result = await runPlatformAiQuery(trimmed);
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: result.answer,
        placeholder: result.placeholder,
      };
      setMessages((prev) => [...prev, assistantMsg]);
      appendAiHistory(
        {
          title: trimmed.slice(0, 80),
          prompt: trimmed,
          response: result.answer,
          source: 'copilot',
          module: 'executive',
          placeholder: result.placeholder,
        },
        null,
        user?.id,
      );
    } finally {
      setPending(false);
    }
  }

  function handleSuggested(key: (typeof SUGGESTED_KEYS)[number]) {
    const promptMap: Record<(typeof SUGGESTED_KEYS)[number], string> = {
      priorities: tPrompts('execPrioritiesPrompt'),
      salesPipeline: tPrompts('salesPipelinePrompt'),
      investorActivity: tPrompts('invActivityPrompt'),
      overdueTasks: tPrompts('overdueTasksPrompt'),
      marketingPerformance: tPrompts('mktPerformancePrompt'),
      projectRisks: tPrompts('prjRisksPrompt'),
    };
    void ask(promptMap[key]);
  }

  return (
    <div className="ih-drawer ai-copilot-drawer" role="dialog" aria-modal="true" aria-labelledby="ai-copilot-title">
      <button type="button" className="ai-copilot-drawer__scrim" aria-label={t('close')} onClick={closeCopilot} />
      <aside className="ih-drawer__panel ih-drawer__panel--wide ai-copilot-drawer__panel">
        <header className="ih-drawer__header">
          <div>
            <p className="ai-copilot-drawer__eyebrow">{t('eyebrow')}</p>
            <h2 id="ai-copilot-title" className="ih-drawer__title">
              {t('title')}
            </h2>
          </div>
          <button type="button" className="ih-drawer__close" onClick={closeCopilot} aria-label={t('close')}>
            ×
          </button>
        </header>

        <p className="ai-copilot-drawer__disclaimer">{t('disclaimer')}</p>

        <div className="ai-copilot-drawer__suggestions" aria-label={t('suggestedAria')}>
          {SUGGESTED_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              className="ih-btn ih-btn--ghost ai-copilot-drawer__chip"
              onClick={() => handleSuggested(key)}
              disabled={pending}
            >
              {t(`suggested.${key}`)}
            </button>
          ))}
        </div>

        <div className="ai-copilot-drawer__messages">
          {messages.length === 0 ? (
            <div className="ai-copilot-drawer__empty">
              <IhIcon name="sparkles" size={28} />
              <p>{t('empty')}</p>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`ai-copilot-drawer__msg ai-copilot-drawer__msg--${msg.role}`}>
                <p>{msg.content}</p>
                {msg.placeholder ? <span className="ai-copilot-drawer__badge">{t('placeholderBadge')}</span> : null}
              </div>
            ))
          )}
        </div>

        <form
          className="ai-copilot-drawer__form"
          onSubmit={(e) => {
            e.preventDefault();
            void ask(input);
          }}
        >
          <textarea
            className="ai-copilot-drawer__input"
            rows={3}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={t('inputPlaceholder')}
            disabled={!canUseAiWorkspace(user) || pending}
          />
          <div className="ai-copilot-drawer__actions">
            <button type="submit" className="ih-btn ih-btn--primary" disabled={pending || !input.trim()}>
              {pending ? t('thinking') : t('ask')}
            </button>
            <button
              type="button"
              className="ih-btn ih-btn--secondary"
              onClick={() => setMessages([])}
              disabled={pending || messages.length === 0}
            >
              {t('clear')}
            </button>
          </div>
        </form>
      </aside>
    </div>
  );
}
