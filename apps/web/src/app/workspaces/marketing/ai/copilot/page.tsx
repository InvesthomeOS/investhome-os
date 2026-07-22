'use client';

import { useTranslations } from 'next-intl';
import { useMutation } from '@tanstack/react-query';

import { Button, ErrorState } from '@investhome/ui';

import { canQueryCopilot } from '@/lib/marketing/marketing-permissions';
import { useAuth } from '@/lib/auth/auth-context';
import { postCopilotQuery } from '@/workspaces/marketing/api/ai';
import { useAIUiStore } from '@/workspaces/marketing/stores/ai-ui-store';

import { AIPageShell, AIConfidenceBadge } from '../_components/ai-shell';

export default function MarketingAICopilotPage() {
  const t = useTranslations('marketing.ai.copilot');
  const { user } = useAuth();
  const canQuery = canQueryCopilot(user);
  const copilotInput = useAIUiStore((s) => s.copilotInput);
  const copilotMessages = useAIUiStore((s) => s.copilotMessages);
  const setCopilotInput = useAIUiStore((s) => s.setCopilotInput);
  const addCopilotMessage = useAIUiStore((s) => s.addCopilotMessage);
  const clearCopilot = useAIUiStore((s) => s.clearCopilot);

  const mutation = useMutation({
    mutationFn: postCopilotQuery,
    onSuccess: (response) => {
      addCopilotMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: response.answer,
        confidence: response.confidence,
        insufficient_data: response.insufficient_data,
        intent: response.intent,
        timestamp: new Date().toISOString(),
      });
    },
  });

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const query = copilotInput.trim();
    if (!query || !canQuery) return;
    addCopilotMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    });
    setCopilotInput('');
    mutation.mutate({ query });
  }

  if (!canQuery) {
    return (
      <AIPageShell title={t('title')} subtitle={t('subtitle')}>
        <ErrorState title={t('accessDenied')} message={t('accessDeniedHint')} />
      </AIPageShell>
    );
  }

  return (
    <AIPageShell title={t('title')} subtitle={t('subtitle')}>
      <div className="mkt-ai-copilot">
        <p className="mkt-ai-copilot__disclaimer">{t('disclaimer')}</p>
        <div className="mkt-ai-copilot__messages">
          {copilotMessages.length === 0 ? (
            <p className="mkt-ai-copilot__placeholder">{t('placeholder')}</p>
          ) : (
            copilotMessages.map((msg) => (
              <div key={msg.id} className={`mkt-ai-copilot__message mkt-ai-copilot__message--${msg.role}`}>
                <p>{msg.content}</p>
                {msg.confidence ? (
                  <div className="mkt-ai-copilot__meta">
                    <AIConfidenceBadge confidence={msg.confidence} />
                    {msg.insufficient_data ? <span className="mkt-ai-copilot__insufficient">{t('insufficient')}</span> : null}
                  </div>
                ) : null}
              </div>
            ))
          )}
        </div>
        <form className="mkt-ai-copilot__form" onSubmit={handleSubmit}>
          <textarea
            className="mkt-ai-copilot__input"
            value={copilotInput}
            onChange={(e) => setCopilotInput(e.target.value)}
            placeholder={t('inputPlaceholder')}
            rows={3}
          />
          <div className="mkt-ai-copilot__actions">
            <Button type="submit" disabled={mutation.isPending || !copilotInput.trim()}>
              {mutation.isPending ? t('thinking') : t('ask')}
            </Button>
            <Button type="button" variant="secondary" onClick={clearCopilot}>
              {t('clear')}
            </Button>
          </div>
        </form>
        {mutation.isError ? (
          <ErrorState title={t('error')} message={mutation.error.message} />
        ) : null}
      </div>
    </AIPageShell>
  );
}
