'use client';

import { useAuth } from '@/lib/auth/auth-context';
import { hasMarketingPermission } from '@/lib/marketing/marketing-permissions';

import { IntegrationSetupState } from '../_components/integration-setup-state';
import { MarketingModuleShell } from '../_components/marketing-module-shell';

export default function MarketingVendorsPage() {
  const { user } = useAuth();

  if (!hasMarketingPermission(user, 'manage_settings')) {
    return (
      <MarketingModuleShell
        titleKey="modules.vendors.title"
        descriptionKey="modules.vendors.description"
        notConnected={false}
        permissionRestricted
      />
    );
  }

  return (
    <main className="dashboard marketing-module-shell">
      <IntegrationSetupState
        titleKey="modules.vendors.title"
        descriptionKey="modules.vendors.description"
        reason="platform_config"
        requirementKeys={['vendorRegistry', 'contractWorkflow', 'spendReconciliation']}
      />
    </main>
  );
}
