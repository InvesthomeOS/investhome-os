import type { IhIconName } from '@/components/icons/ih-icons';

import type { JourneyActivityType } from './journey-timeline-model';

export type CrmEventVisualIdentity = {
  label: string;
  icon: IhIconName;
  className: `crm-event-identity--${string}`;
};

export const CRM_EVENT_IDENTITIES: Record<JourneyActivityType, CrmEventVisualIdentity> = {
  call: { label: 'Call', icon: 'activity', className: 'crm-event-identity--call' },
  whatsapp: { label: 'WhatsApp', icon: 'inbox', className: 'crm-event-identity--whatsapp' },
  email: { label: 'Email', icon: 'inbox', className: 'crm-event-identity--email' },
  meeting: { label: 'Meeting', icon: 'meeting', className: 'crm-event-identity--meeting' },
  proposal: { label: 'Proposal', icon: 'documents', className: 'crm-event-identity--proposal' },
  reservation: { label: 'Reservation', icon: 'calendar', className: 'crm-event-identity--reservation' },
  contract: { label: 'Contract', icon: 'documents', className: 'crm-event-identity--contract' },
  payment: { label: 'Payment', icon: 'finance', className: 'crm-event-identity--payment' },
  document: { label: 'Document', icon: 'documents', className: 'crm-event-identity--document' },
  internal_note: { label: 'Internal Note', icon: 'user', className: 'crm-event-identity--internal-note' },
  ai_summary: { label: 'AI Summary', icon: 'sparkles', className: 'crm-event-identity--ai' },
  follow_up_task: { label: 'Follow-up Task', icon: 'check', className: 'crm-event-identity--follow-up' },
  reminder: { label: 'Reminder', icon: 'bell', className: 'crm-event-identity--reminder' },
};

export function getCrmEventIdentity(activityType: JourneyActivityType): CrmEventVisualIdentity {
  return CRM_EVENT_IDENTITIES[activityType];
}
