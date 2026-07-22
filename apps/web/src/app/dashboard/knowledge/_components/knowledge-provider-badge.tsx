'use client';

import type { ProviderCapabilityStatus } from '@/lib/api/knowledge';
import { useTranslations } from 'next-intl';

type Props = {
  label: string;
  status: ProviderCapabilityStatus;
};

export function KnowledgeProviderBadge({ label, status }: Props) {
  const t = useTranslations('knowledge');
  return (
    <div
      className={`knowledge-hub__provider${status.available ? '' : ' knowledge-hub__provider--unavailable'}`}
      data-available={status.available ? 'true' : 'false'}
    >
      <div className="knowledge-hub__provider-head">
        <strong>{label}</strong>
        <span className="knowledge-hub__provider-pill">
          {status.available ? t('providers.available') : t('providers.unavailable')}
        </span>
      </div>
      <p className="knowledge-hub__provider-meta">{status.provider}</p>
      {!status.available && status.reason && (
        <p className="knowledge-hub__provider-reason">{status.reason}</p>
      )}
      {!status.available && status.required_env.length > 0 && (
        <p className="knowledge-hub__provider-env">
          {t('providers.requiredEnv')}: {status.required_env.join(', ')}
        </p>
      )}
    </div>
  );
}
