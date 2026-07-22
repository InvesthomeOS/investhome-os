'use client';

import { useTranslations } from 'next-intl';

import { EmptyState } from '@investhome/ui';

export type IntegrationSetupReason = 'provider_required' | 'api_pending' | 'platform_config';

type IntegrationSetupStateProps = {
  titleKey: string;
  descriptionKey: string;
  reason: IntegrationSetupReason;
  requirementKeys?: string[];
};

export function IntegrationSetupState({
  titleKey,
  descriptionKey,
  reason,
  requirementKeys = [],
}: IntegrationSetupStateProps) {
  const t = useTranslations('marketing.integrationSetup');
  const tModule = useTranslations('marketing');

  return (
    <div className="marketing-integration-setup">
      <EmptyState
        title={tModule(titleKey as 'modules.advertising.title')}
        description={tModule(descriptionKey as 'modules.advertising.description')}
      />
      <section className="marketing-integration-setup__panel" aria-labelledby="integration-setup-status">
        <h2 id="integration-setup-status" className="marketing-integration-setup__heading">
          {t(`reasons.${reason}.title`)}
        </h2>
        <p className="marketing-integration-setup__summary">{t(`reasons.${reason}.description`)}</p>
        {requirementKeys.length > 0 && (
          <ul className="marketing-integration-setup__requirements">
            {requirementKeys.map((key) => (
              <li key={key}>{t(`requirements.${key}` as 'requirements.providerConnection')}</li>
            ))}
          </ul>
        )}
        <p className="marketing-integration-setup__note">{t('disabledNote')}</p>
      </section>
    </div>
  );
}
