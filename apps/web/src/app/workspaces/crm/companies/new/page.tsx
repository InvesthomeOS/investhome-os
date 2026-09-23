'use client';

import { useEffect } from 'react';

import { CrmModuleShell } from '../../_components/crm-module-shell';
import { CrmCompanyForm } from '../../_components/crm-company-form';
import { useCrmCompaniesStore } from '@/workspaces/crm/_stores/crm-companies-store';

export default function CrmCompanyNewPage() {
  const setDraftFormOpen = useCrmCompaniesStore((state) => state.setDraftFormOpen);

  useEffect(() => {
    setDraftFormOpen(true);
    return () => setDraftFormOpen(false);
  }, [setDraftFormOpen]);

  return (
    <CrmModuleShell titleKey="companies.createTitle" descriptionKey="companies.createDescription">
      <CrmCompanyForm mode="create" />
    </CrmModuleShell>
  );
}
