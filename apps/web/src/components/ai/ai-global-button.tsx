'use client';

import { useTranslations } from 'next-intl';

import { IhIcon } from '@/components/icons/ih-icons';
import { useAiCopilotOptional } from '@/lib/ai/ai-copilot-context';
import { canViewAiWorkspace } from '@/lib/ai/ai-permissions';
import { useAuth } from '@/lib/auth/auth-context';

export function AiGlobalButton() {
  const t = useTranslations('ai');
  const { user } = useAuth();
  const copilot = useAiCopilotOptional();

  if (!canViewAiWorkspace(user) || !copilot) return null;

  return (
    <button
      type="button"
      className="app-header__quick ai-global-btn"
      onClick={() => copilot.openCopilot()}
      aria-label={t('globalButton.aria')}
      title={t('globalButton.label')}
    >
      <IhIcon name="sparkles" size={15} />
      <span className="ai-global-btn__label">{t('globalButton.label')}</span>
    </button>
  );
}
