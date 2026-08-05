import { CrmModuleShell } from '../../../_components/crm-module-shell';
import { ContactJourneyWorkspace } from '../../_components/contact-journey-workspace';

type ContactJourneyPageProps = {
  params: Promise<{ contactId: string }>;
};

export default async function ContactJourneyPage({ params }: ContactJourneyPageProps) {
  const { contactId } = await params;
  return (
    <CrmModuleShell titleKey="modules.contacts.title" descriptionKey="modules.contacts.description">
      <ContactJourneyWorkspace contactId={contactId} />
    </CrmModuleShell>
  );
}
