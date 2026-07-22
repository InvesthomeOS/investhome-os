'use client';

import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAiCopilotOptional } from '@/lib/ai/ai-copilot-context';
import { canUseAiWorkspace } from '@/lib/ai/ai-permissions';
import { MODULE_AI_ACTIONS, type AiActionKind, type AiModuleContext } from '@/lib/ai/prompt-library';
import { useAuth } from '@/lib/auth/auth-context';

type Props = {
  module: AiModuleContext;
  entityLabel?: string;
  entityId?: string;
  className?: string;
  compact?: boolean;
};

export function ContextualAiActions({ module, entityLabel, entityId, className, compact }: Props) {
  const t = useTranslations('ai.contextual');
  const tActions = useTranslations('ai.actionPanel.actions');
  const { user } = useAuth();
  const copilot = useAiCopilotOptional();

  if (!canUseAiWorkspace(user) || !copilot) return null;

  const actions = MODULE_AI_ACTIONS[module] ?? MODULE_AI_ACTIONS.general;

  function open(action: AiActionKind) {
    copilot!.openActionPanel({
      module,
      action,
      entityLabel,
      entityId,
      seedPrompt: t('seedPrompt', {
        action: tActions(action),
        module,
        entity: entityLabel || t('thisView'),
      }),
    });
  }

  return (
    <div className={`ai-contextual ${compact ? 'ai-contextual--compact' : ''} ${className ?? ''}`.trim()}>
      {!compact ? (
        <span className="ai-contextual__label">
          <IhIcon name="sparkles" size={14} />
          {t('label')}
        </span>
      ) : null}
      <div className="ai-contextual__actions">
        {actions.map((action) => (
          <button
            key={action}
            type="button"
            className="ih-btn ih-btn--ghost ai-contextual__btn"
            onClick={() => open(action)}
          >
            {tActions(action)}
          </button>
        ))}
        <button
          type="button"
          className="ih-btn ih-btn--secondary ai-contextual__btn"
          onClick={() =>
            copilot.openActionPanel({
              module,
              action: 'executive_summary',
              entityLabel,
              entityId,
            })
          }
        >
          {tActions('executive_summary')}
        </button>
      </div>
    </div>
  );
}
