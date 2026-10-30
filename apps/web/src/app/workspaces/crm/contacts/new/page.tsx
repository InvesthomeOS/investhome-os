'use client';

import { useRouter } from 'next/navigation';
import type { Route } from 'next';
import { useLocale } from 'next-intl';

import { ErrorState, LoadingState } from '@investhome/ui';

import { useCrmAccess } from '@/lib/crm/use-crm-access';

import { ContactFormModal } from '../_components/contact-form-modal';
import { CrmModuleShell } from '../../_components/crm-module-shell';

export default function NewContactPage() {
  const router = useRouter();
  const locale = useLocale();
  const tr = !locale.startsWith('en');
  const { authLoading, canCreate } = useCrmAccess();
  return (
    <CrmModuleShell titleKey="contacts.form.title" descriptionKey="modules.contacts.description">
      {authLoading ? <LoadingState /> : null}
      {!authLoading && !canCreate ? (
        <ErrorState
          title={tr ? 'Kişi oluşturma yetkisi yok' : 'You cannot create a contact'}
          message={
            tr
              ? 'Yeni kişi eklemek için crm.create yetkisi gerekir.'
              : 'Creating a contact requires the crm.create permission.'
          }
        />
      ) : null}
      {!authLoading && canCreate ? (
        <ContactFormModal
          open
          onClose={() => router.push('/workspaces/crm/contacts' as Route)}
          onSuccess={(contactId) => router.push(`/workspaces/crm/contacts/${contactId}` as Route)}
        />
      ) : null}
    </CrmModuleShell>
  );
}
