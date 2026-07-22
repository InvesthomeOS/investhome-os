import { ContactDetailView } from '../_components/contact-detail-view';
import { CrmModuleShell } from '../../_components/crm-module-shell';

type ContactDetailPageProps = {
  params: Promise<{ contactId: string }>;
};

export default async function ContactDetailPage({ params }: ContactDetailPageProps) {
  const { contactId } = await params;
  return (
    <CrmModuleShell titleKey="modules.contacts.title" descriptionKey="modules.contacts.description">
      <ContactDetailView contactId={contactId} />
    </CrmModuleShell>
  );
}
