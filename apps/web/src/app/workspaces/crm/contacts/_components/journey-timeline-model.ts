export type JourneyActivityType =
  | 'call'
  | 'whatsapp'
  | 'email'
  | 'meeting'
  | 'proposal'
  | 'reservation'
  | 'contract'
  | 'payment'
  | 'document'
  | 'internal_note'
  | 'ai_summary'
  | 'follow_up_task'
  | 'reminder';

export type JourneyEventKind = 'customer_communication' | 'internal_observation' | 'ai_generated';

export type JourneyEventStatus =
  | 'completed'
  | 'sent'
  | 'scheduled'
  | 'due'
  | 'pending'
  | 'signed'
  | 'paid';

export type JourneyTeamMember = {
  id: string;
  name: string;
  initials: string;
};

export type JourneyInternalSalesNote = {
  id: string;
  body: string;
  author: JourneyTeamMember;
  createdAt: string;
};

type JourneyEventBase = {
  id: string;
  occurredAt: string;
  activityType: JourneyActivityType;
  assignedTo: JourneyTeamMember;
  relatedProject?: string;
  status: JourneyEventStatus;
  summary: string;
  internalSalesNote?: JourneyInternalSalesNote;
  attachment?: {
    fileName: string;
  };
};

export type CustomerCommunicationEvent = JourneyEventBase & {
  kind: 'customer_communication';
  channelDirection: 'inbound' | 'outbound' | 'in_person';
};

export type InternalObservationEvent = JourneyEventBase & {
  kind: 'internal_observation';
  visibility: 'team_only';
};

export type AiGeneratedSummaryEvent = JourneyEventBase & {
  kind: 'ai_generated';
  sourceLabel: 'local_mock';
};

export type JourneyTimelineEvent =
  | CustomerCommunicationEvent
  | InternalObservationEvent
  | AiGeneratedSummaryEvent;

const onur: JourneyTeamMember = { id: 'team-onur', name: 'Onur Kılıç', initials: 'OK' };
const selin: JourneyTeamMember = { id: 'team-selin', name: 'Selin Kaya', initials: 'SK' };

export const JOURNEY_TIMELINE_EVENTS: readonly JourneyTimelineEvent[] = [
  {
    id: 'journey-follow-up',
    occurredAt: '2026-07-24T16:00:00+03:00',
    activityType: 'follow_up_task',
    assignedTo: onur,
    relatedProject: 'North Towers A-1204',
    status: 'due',
    summary: 'Prepare the updated proposal and send the payment-plan terms by end of day.',
    kind: 'internal_observation',
    visibility: 'team_only',
    internalSalesNote: {
      id: 'note-follow-up',
      body: 'Ada preferred the 24-month plan but asked us to keep the reservation window flexible until Monday. Lead with the view and family-area benefits; do not frame this as a discount conversation.',
      author: onur,
      createdAt: '2026-07-24T09:12:00+03:00',
    },
  },
  {
    id: 'journey-proposal',
    occurredAt: '2026-07-23T14:30:00+03:00',
    activityType: 'proposal',
    assignedTo: onur,
    relatedProject: 'North Towers A-1204',
    status: 'sent',
    summary: 'Proposal sent by email with floor plan, availability, and revised installment schedule.',
    attachment: {
      fileName: 'North-Towers-A1204-proposal.pdf',
    },
    kind: 'customer_communication',
    channelDirection: 'outbound',
    internalSalesNote: {
      id: 'note-proposal',
      body: 'Opened twice within the first hour. Follow up on the balcony layout before discussing price.',
      author: selin,
      createdAt: '2026-07-23T15:45:00+03:00',
    },
  },
  {
    id: 'journey-ai-summary',
    occurredAt: '2026-07-22T17:10:00+03:00',
    activityType: 'ai_summary',
    assignedTo: selin,
    status: 'completed',
    summary: 'Local mock summary: high intent, focused on a 2+1 home, school access, and a move-in-ready timeline.',
    kind: 'ai_generated',
    sourceLabel: 'local_mock',
  },
  {
    id: 'journey-whatsapp',
    occurredAt: '2026-07-21T11:05:00+03:00',
    activityType: 'whatsapp',
    assignedTo: selin,
    relatedProject: 'North Towers A-1204',
    status: 'completed',
    summary: 'Ada confirmed that Saturday morning works for a second viewing with her partner.',
    kind: 'customer_communication',
    channelDirection: 'inbound',
  },
  {
    id: 'journey-viewing',
    occurredAt: '2026-07-18T11:15:00+03:00',
    activityType: 'meeting',
    assignedTo: onur,
    relatedProject: 'North Towers A-1204',
    status: 'completed',
    summary: 'Unit viewed in person; customer responded positively to natural light and shared amenities.',
    kind: 'customer_communication',
    channelDirection: 'in_person',
    internalSalesNote: {
      id: 'note-viewing',
      body: 'Strongest reaction was to the living-room light. Partner is likely the final decision-maker, so prepare a concise comparison with the B-block alternative before the second viewing.',
      author: onur,
      createdAt: '2026-07-18T12:20:00+03:00',
    },
  },
  {
    id: 'journey-call',
    occurredAt: '2026-07-16T10:00:00+03:00',
    activityType: 'call',
    assignedTo: onur,
    status: 'completed',
    summary: 'Introductory call completed in 12 minutes; budget, preferred districts, and move date were confirmed.',
    kind: 'customer_communication',
    channelDirection: 'outbound',
  },
  {
    id: 'journey-email',
    occurredAt: '2026-07-14T16:25:00+03:00',
    activityType: 'email',
    assignedTo: selin,
    relatedProject: 'North Towers A-1204',
    status: 'sent',
    summary: 'Neighborhood guide and school-access comparison sent after the discovery call.',
    kind: 'customer_communication',
    channelDirection: 'outbound',
  },
  {
    id: 'journey-reservation',
    occurredAt: '2026-07-12T13:40:00+03:00',
    activityType: 'reservation',
    assignedTo: onur,
    relatedProject: 'North Towers A-1204',
    status: 'pending',
    summary: 'A provisional reservation window was discussed for unit A-1204.',
    kind: 'customer_communication',
    channelDirection: 'in_person',
  },
  {
    id: 'journey-contract',
    occurredAt: '2026-07-10T09:15:00+03:00',
    activityType: 'contract',
    assignedTo: onur,
    relatedProject: 'North Towers A-1204',
    status: 'pending',
    summary: 'Draft purchase agreement prepared for review; no signature action has been initiated.',
    attachment: {
      fileName: 'draft-purchase-agreement.pdf',
    },
    kind: 'customer_communication',
    channelDirection: 'outbound',
  },
  {
    id: 'journey-payment',
    occurredAt: '2026-07-08T15:05:00+03:00',
    activityType: 'payment',
    assignedTo: selin,
    relatedProject: 'North Towers A-1204',
    status: 'pending',
    summary: 'Illustrative deposit schedule reviewed; no payment was requested or processed.',
    kind: 'customer_communication',
    channelDirection: 'in_person',
  },
  {
    id: 'journey-document',
    occurredAt: '2026-07-06T12:20:00+03:00',
    activityType: 'document',
    assignedTo: selin,
    relatedProject: 'North Towers A-1204',
    status: 'sent',
    summary: 'Floor plan and technical specification pack shared for local review.',
    attachment: {
      fileName: 'A1204-specification-pack.pdf',
    },
    kind: 'customer_communication',
    channelDirection: 'outbound',
  },
  {
    id: 'journey-internal-note',
    occurredAt: '2026-07-04T17:30:00+03:00',
    activityType: 'internal_note',
    assignedTo: selin,
    relatedProject: 'North Towers A-1204',
    status: 'completed',
    summary: 'Team-only buying-context observation recorded after the initial qualification review.',
    kind: 'internal_observation',
    visibility: 'team_only',
    internalSalesNote: {
      id: 'note-qualification',
      body: 'Keep follow-ups concise and lead with school access, daylight, and move-in readiness. Price sensitivity appears secondary to timing certainty.',
      author: selin,
      createdAt: '2026-07-04T17:30:00+03:00',
    },
  },
  {
    id: 'journey-reminder',
    occurredAt: '2026-07-02T10:00:00+03:00',
    activityType: 'reminder',
    assignedTo: onur,
    status: 'scheduled',
    summary: 'Reminder scheduled to confirm attendees before the second viewing.',
    kind: 'internal_observation',
    visibility: 'team_only',
  },
];
