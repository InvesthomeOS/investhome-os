'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { useAiCopilot } from '@/lib/ai/ai-copilot-context';
import { appendAiHistory } from '@/lib/ai/ai-history';
import { canUseAiWorkspace } from '@/lib/ai/ai-permissions';
import { runPlatformAiQuery } from '@/lib/ai/run-ai-query';
import { useAuth } from '@/lib/auth/auth-context';

export function AiActionPanel() {
  const t = useTranslations('ai.actionPanel');
  const { user } = useAuth();
  const { actionPanel, closeActionPanel } = useAiCopilot();
  const [result, setResult] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [placeholder, setPlaceholder] = useState(false);

  if (!actionPanel.open) return null;

  const actionLabel = t(`actions.${actionPanel.action}` as 'actions.summarize');
  const defaultPrompt =
    actionPanel.seedPrompt ||
    t('defaultPrompt', {
      action: actionLabel,
      module: actionPanel.module,
      entity: actionPanel.entityLabel || t('currentView'),
    });

  async function run() {
    if (!canUseAiWorkspace(user) || pending) return;
    setPending(true);
    setResult(null);
    try {
      const response = await runPlatformAiQuery(defaultPrompt);
      setResult(response.answer);
      setPlaceholder(response.placeholder);
      appendAiHistory(
        {
          title: `${actionLabel}${actionPanel.entityLabel ? `: ${actionPanel.entityLabel}` : ''}`,
          prompt: defaultPrompt,
          response: response.answer,
          source: 'action',
          module: actionPanel.module,
          action: actionPanel.action,
          placeholder: response.placeholder,
        },
        null,
        user?.id,
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="ih-dialog ai-action-dialog" role="dialog" aria-modal="true" aria-labelledby="ai-action-title">
      <div className="ih-dialog__panel ai-action-dialog__panel">
        <header className="ih-dialog__header">
          <div>
            <p className="ai-action-dialog__eyebrow">{t('eyebrow')}</p>
            <h2 id="ai-action-title" className="ih-dialog__title">
              {actionLabel}
            </h2>
            {actionPanel.entityLabel ? (
              <p className="ai-action-dialog__entity">{actionPanel.entityLabel}</p>
            ) : null}
          </div>
          <button type="button" className="ih-dialog__close" onClick={closeActionPanel} aria-label={t('close')}>
            ×
          </button>
        </header>

        <p className="ai-action-dialog__hint">{t('hint')}</p>
        <pre className="ai-action-dialog__prompt">{defaultPrompt}</pre>

        {result ? (
          <div className="ai-action-dialog__result">
            <p>{result}</p>
            {placeholder ? <span className="ai-copilot-drawer__badge">{t('placeholderBadge')}</span> : null}
          </div>
        ) : null}

        <footer className="ih-dialog__footer">
          <button type="button" className="ih-btn ih-btn--secondary" onClick={closeActionPanel}>
            {t('close')}
          </button>
          <button
            type="button"
            className="ih-btn ih-btn--primary"
            onClick={() => void run()}
            disabled={pending || !canUseAiWorkspace(user)}
          >
            {pending ? t('running') : t('run')}
          </button>
        </footer>
      </div>
    </div>
  );
}
