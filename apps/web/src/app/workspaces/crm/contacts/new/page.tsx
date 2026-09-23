'use client';

import { useRouter } from 'next/navigation';
import type { Route } from 'next';

import { ContactFormModal } from '../_components/contact-form-modal';
import { CrmModuleShell } from '../../_components/crm-module-shell';

export default function NewContactPage() {
  const router = useRouter();
  return (
    <CrmModuleShell titleKey="contacts.form.title" descriptionKey="modules.contacts.description">
      <ContactFormModal
        open
        onClose={() => router.push('/workspaces/crm/contacts' as Route)}
        onSuccess={(contactId) => router.push(`/workspaces/crm/contacts/${contactId}` as Route)}
      />
    </CrmModuleShell>
  );
}
