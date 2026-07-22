'use client';

import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';

import { IntegrationSetupState } from '../_components/integration-setup-state';
import { MarketingModuleShell } from '../_components/marketing-module-shell';

export default function MarketingAdvertisingPage() {
  const { user } = useAuth();

  if (!hasMarketingPermission(user, 'manage_advertising')) {
    return (
      <MarketingModuleShell
        titleKey="modules.advertising.title"
        descriptionKey="modules.advertising.description"
        notConnected={false}
        permissionRestricted
      />
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <IntegrationSetupState
        titleKey="modules.advertising.title"
        descriptionKey="modules.advertising.description"
        reason="provider_required"
        requirementKeys={['providerConnection', 'adAccount', 'conversionTracking']}
      />
    </main>
  );
}
