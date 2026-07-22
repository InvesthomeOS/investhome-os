import { investorProfile } from './mock-data';
import type {
  SignatureAuditEntry,
  SignatureEvent,
  SignatureField,
  SignatureRecipient,
  SignatureRequest,
} from './document-types';

function recipient(
  id: string,
  name: string,
  email: string,
  role: SignatureRecipient['role'],
  status: SignatureRecipient['status'],
  order: number,
  isCurrentUser: boolean,
  signedAt: string | null = null,
): SignatureRecipient {
  return { id, name, email, role, status, order, signedAt, isCurrentUser };
}

function field(
  id: string,
  type: SignatureField['type'],
  label: string,
  page: number,
  recipientId: string,
  required = true,
  value: string | null = null,
  completedAt: string | null = null,
): SignatureField {
  return { id, type, label, page, required, recipientId, value, completedAt };
}

function audit(
  id: string,
  timestamp: string,
  event: string,
  actor: string,
  details: string,
): SignatureAuditEntry {
  return {
    id,
    timestamp,
    event,
    actor,
    details,
    ipAddressMasked: '192.168.***.**',
    userAgent: 'Mozilla/5.0 (Demo Browser)',
  };
}

function event(
  id: string,
  timestamp: string,
  type: SignatureEvent['type'],
  actor: string,
  description: string,
): SignatureEvent {
  return {
    id,
    timestamp,
    type,
    actor,
    description,
    ipAddressMasked: '192.168.***.**',
  };
}

function sig(
  partial: Omit<
    SignatureRequest,
    'recipients' | 'fields' | 'events' | 'auditTrail' | 'isDemoOnly'
  > & {
    recipients: SignatureRecipient[];
    fields: SignatureField[];
    events?: SignatureEvent[];
    auditTrail?: SignatureAuditEntry[];
  },
): SignatureRequest {
  const created = partial.createdAt;
  return {
    ...partial,
    isDemoOnly: true,
    events: partial.events ?? [
      event(`${partial.id}-e1`, created, 'created', 'Investhome Operations', 'Signature request created'),
      ...(partial.sentAt
        ? [event(`${partial.id}-e2`, partial.sentAt, 'sent', 'Investhome Operations', 'Sent to recipients')]
        : []),
    ],
    auditTrail: partial.auditTrail ?? [
      audit(`${partial.id}-a1`, created, 'Request Created', 'Investhome Operations', 'Demo signature request initiated'),
    ],
  };
}

const CURRENT_USER = investorProfile.name;
const CURRENT_EMAIL = investorProfile.email;

const signatureRequests: SignatureRequest[] = [
  sig({
    id: 'sig-001',
    documentId: 'doc-001',
    documentTitle: 'Subscription Agreement — Class A Units',
    investmentId: 'pi-001',
    investmentName: 'The Temple',
    entityName: 'Temple Holdings LLC',
    status: 'action_required',
    createdAt: '2025-06-28T10:30:00Z',
    sentAt: '2025-07-01T09:00:00Z',
    expiresAt: '2025-08-15',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Please review and sign the updated subscription agreement for The Temple investment.',
    certificateId: null,
    recipients: [
      recipient('rec-001-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'viewed', 1, true),
      recipient('rec-001-b', 'Sarah Chen', 's.chen@investhome.com', 'sponsor', 'signed', 2, false, '2025-07-05T14:00:00Z'),
      recipient('rec-001-c', 'Legal Counsel', 'legal@investhome.com', 'legal', 'pending', 3, false),
    ],
    fields: [
      field('fld-001-1', 'signature', 'Investor Signature', 38, 'rec-001-a'),
      field('fld-001-2', 'date', 'Date Signed', 38, 'rec-001-a'),
      field('fld-001-3', 'initials', 'Initial Page 12', 12, 'rec-001-a'),
      field('fld-001-4', 'signature', 'Sponsor Signature', 39, 'rec-001-b', true, 'Sarah Chen', '2025-07-05T14:00:00Z'),
    ],
  }),
  sig({
    id: 'sig-002',
    documentId: 'doc-004',
    documentTitle: 'Form W-9 — Tax Identification',
    investmentId: 'pi-001',
    investmentName: 'The Temple',
    entityName: 'Temple Holdings LLC',
    status: 'action_required',
    createdAt: '2025-07-01T12:30:00Z',
    sentAt: '2025-07-01T13:00:00Z',
    expiresAt: '2025-12-31',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Please complete and sign your W-9 for tax reporting. Tax ID fields are masked in this demo.',
    certificateId: null,
    recipients: [
      recipient('rec-002-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'sent', 1, true),
    ],
    fields: [
      field('fld-002-1', 'name', 'Legal Name', 1, 'rec-002-a'),
      field('fld-002-2', 'text', 'Business Name (if different)', 1, 'rec-002-a', false),
      field('fld-002-3', 'signature', 'Signature', 2, 'rec-002-a'),
      field('fld-002-4', 'date', 'Date', 2, 'rec-002-a'),
    ],
  }),
  sig({
    id: 'sig-003',
    documentId: 'doc-023',
    documentTitle: 'Capital Call Notice — Tranche 2',
    investmentId: 'pi-006',
    investmentName: 'H Place Residences',
    entityName: 'H Place Condominium Fund',
    status: 'action_required',
    createdAt: '2025-07-05T10:30:00Z',
    sentAt: '2025-07-05T11:00:00Z',
    expiresAt: '2025-07-25',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Capital call of $187,500 due by July 25, 2025. Please sign to acknowledge receipt.',
    certificateId: null,
    recipients: [
      recipient('rec-003-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'viewed', 1, true),
    ],
    fields: [
      field('fld-003-1', 'checkbox', 'I acknowledge the capital call terms', 2, 'rec-003-a'),
      field('fld-003-2', 'signature', 'Investor Signature', 3, 'rec-003-a'),
      field('fld-003-3', 'date', 'Date', 3, 'rec-003-a'),
    ],
  }),
  sig({
    id: 'sig-004',
    documentId: 'doc-029',
    documentTitle: 'Subscription Agreement — Capitol Heights OZ Fund',
    investmentId: 'pi-008',
    investmentName: 'Capitol Heights',
    entityName: 'Capitol Heights Opportunity Zone Fund',
    status: 'action_required',
    createdAt: '2025-07-08T10:30:00Z',
    sentAt: '2025-07-10T09:00:00Z',
    expiresAt: '2025-08-30',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Complete your subscription for the upcoming Capitol Heights opportunity zone investment.',
    certificateId: null,
    recipients: [
      recipient('rec-004-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'sent', 1, true),
      recipient('rec-004-b', 'Fund Manager', 'manager@capitolheights.com', 'sponsor', 'pending', 2, false),
    ],
    fields: [
      field('fld-004-1', 'initials', 'Initial Each Page', 1, 'rec-004-a'),
      field('fld-004-2', 'signature', 'Investor Signature', 44, 'rec-004-a'),
      field('fld-004-3', 'date', 'Date', 44, 'rec-004-a'),
      field('fld-004-4', 'text', 'Investment Amount', 5, 'rec-004-a'),
    ],
  }),
  sig({
    id: 'sig-005',
    documentId: 'doc-030',
    documentTitle: 'Investor Questionnaire & Suitability Form',
    investmentId: 'pi-008',
    investmentName: 'Capitol Heights',
    entityName: 'Capitol Heights Opportunity Zone Fund',
    status: 'action_required',
    createdAt: '2025-07-08T10:30:00Z',
    sentAt: '2025-07-10T09:00:00Z',
    expiresAt: '2025-08-30',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Please complete the investor suitability questionnaire.',
    certificateId: null,
    recipients: [
      recipient('rec-005-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'pending', 1, true),
    ],
    fields: [
      field('fld-005-1', 'checkbox', 'Accredited Investor Confirmation', 3, 'rec-005-a'),
      field('fld-005-2', 'checkbox', 'Risk Acknowledgment', 5, 'rec-005-a'),
      field('fld-005-3', 'signature', 'Signature', 12, 'rec-005-a'),
      field('fld-005-4', 'date', 'Date', 12, 'rec-005-a'),
    ],
  }),
  sig({
    id: 'sig-006',
    documentId: 'doc-034',
    documentTitle: 'Wire Instructions Acknowledgment',
    investmentId: 'pi-009',
    investmentName: 'Georgetown Row',
    entityName: 'Georgetown Heritage REIT',
    status: 'action_required',
    createdAt: '2025-07-12T10:30:00Z',
    sentAt: '2025-07-12T11:00:00Z',
    expiresAt: '2025-07-31',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Acknowledge wire instructions for distribution payments. Account ending in ••••4821.',
    certificateId: null,
    recipients: [
      recipient('rec-006-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'viewed', 1, true),
    ],
    fields: [
      field('fld-006-1', 'checkbox', 'I confirm wire instructions', 1, 'rec-006-a'),
      field('fld-006-2', 'signature', 'Signature', 1, 'rec-006-a'),
    ],
  }),
  sig({
    id: 'sig-007',
    documentId: 'doc-036',
    documentTitle: 'Amendment No. 2 — Operating Agreement',
    investmentId: 'pi-009',
    investmentName: 'Georgetown Row',
    entityName: 'Georgetown Heritage REIT',
    status: 'waiting_on_others',
    createdAt: '2025-06-20T10:30:00Z',
    sentAt: '2025-06-22T09:00:00Z',
    expiresAt: '2025-08-15',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Amendment requires signatures from all limited partners. You have signed; awaiting co-investors.',
    certificateId: null,
    recipients: [
      recipient('rec-007-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2025-07-01T10:00:00Z'),
      recipient('rec-007-b', 'James Whitmore', 'j.whitmore@whitmorecapital.com', 'co_investor', 'pending', 2, false),
      recipient('rec-007-c', 'Fund Administrator', 'admin@georgetownreit.com', 'sponsor', 'signed', 3, false, '2025-06-25T14:00:00Z'),
    ],
    fields: [
      field('fld-007-1', 'signature', 'Investor Signature', 5, 'rec-007-a', true, CURRENT_USER, '2025-07-01T10:00:00Z'),
      field('fld-007-2', 'signature', 'Co-Investor Signature', 5, 'rec-007-b'),
      field('fld-007-3', 'signature', 'Administrator Signature', 6, 'rec-007-c', true, 'Fund Administrator', '2025-06-25T14:00:00Z'),
    ],
    events: [
      event('sig-007-e1', '2025-06-20T10:30:00Z', 'created', 'Investhome Operations', 'Request created'),
      event('sig-007-e2', '2025-06-22T09:00:00Z', 'sent', 'Investhome Operations', 'Sent to all recipients'),
      event('sig-007-e3', '2025-06-25T14:00:00Z', 'signed', 'Fund Administrator', 'Administrator signed'),
      event('sig-007-e4', '2025-07-01T10:00:00Z', 'signed', CURRENT_USER, 'Investor signed'),
    ],
    auditTrail: [
      audit('sig-007-a1', '2025-06-20T10:30:00Z', 'Request Created', 'Investhome Operations', 'Amendment signature request'),
      audit('sig-007-a2', '2025-07-01T10:00:00Z', 'Signed', CURRENT_USER, 'Investor signature captured (demo)'),
    ],
  }),
  sig({
    id: 'sig-008',
    documentId: 'doc-003',
    documentTitle: 'Side Letter — Co-Investment Rights',
    investmentId: 'pi-001',
    investmentName: 'The Temple',
    entityName: 'Temple Holdings LLC',
    status: 'completed',
    createdAt: '2023-04-08T10:00:00Z',
    sentAt: '2023-04-08T11:00:00Z',
    expiresAt: '2023-04-30',
    completedAt: '2023-04-12T16:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Side letter for co-investment rights.',
    certificateId: 'cert-demo-008',
    recipients: [
      recipient('rec-008-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2023-04-12T16:00:00Z'),
      recipient('rec-008-b', 'Sarah Chen', 's.chen@investhome.com', 'sponsor', 'signed', 2, false, '2023-04-10T10:00:00Z'),
    ],
    fields: [
      field('fld-008-1', 'signature', 'Investor Signature', 7, 'rec-008-a', true, CURRENT_USER, '2023-04-12T16:00:00Z'),
      field('fld-008-2', 'signature', 'Sponsor Signature', 8, 'rec-008-b', true, 'Sarah Chen', '2023-04-10T10:00:00Z'),
    ],
  }),
  sig({
    id: 'sig-009',
    documentId: 'doc-007',
    documentTitle: 'Subscription Agreement — Uniloft LP',
    investmentId: 'pi-002',
    investmentName: 'Uniloft',
    entityName: 'Uniloft Residential Partners LP',
    status: 'completed',
    createdAt: '2021-08-15T10:00:00Z',
    sentAt: '2021-08-16T09:00:00Z',
    expiresAt: '2021-09-15',
    completedAt: '2021-08-20T14:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Original subscription agreement.',
    certificateId: 'cert-demo-009',
    recipients: [
      recipient('rec-009-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2021-08-20T14:00:00Z'),
    ],
    fields: [
      field('fld-009-1', 'signature', 'Investor Signature', 36, 'rec-009-a', true, CURRENT_USER, '2021-08-20T14:00:00Z'),
    ],
  }),
  sig({
    id: 'sig-020',
    documentId: 'doc-015',
    documentTitle: 'Accredited Investor Verification Letter',
    investmentId: 'pi-003',
    investmentName: '309 H Street',
    entityName: 'H Street Development Co.',
    status: 'declined',
    createdAt: '2025-06-01T10:00:00Z',
    sentAt: '2025-06-02T09:00:00Z',
    expiresAt: '2025-07-01',
    completedAt: null,
    declinedAt: '2025-06-10T11:00:00Z',
    voidedAt: null,
    message: 'Please upload updated accreditation documentation from a qualified verifier.',
    certificateId: null,
    recipients: [
      recipient('rec-020-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'declined', 1, true),
    ],
    fields: [
      field('fld-020-1', 'signature', 'Investor Signature', 2, 'rec-020-a'),
    ],
    events: [
      event('sig-020-e1', '2025-06-01T10:00:00Z', 'created', 'Investhome Operations', 'Request created'),
      event('sig-020-e2', '2025-06-10T11:00:00Z', 'declined', CURRENT_USER, 'Declined — will provide updated letter separately'),
    ],
  }),
  sig({
    id: 'sig-021',
    documentId: 'doc-028',
    documentTitle: 'Exit Summary Report',
    investmentId: 'pi-007',
    investmentName: 'Riverside Flip Fund III',
    entityName: 'Riverside Value Partners',
    status: 'expired',
    createdAt: '2024-11-01T10:00:00Z',
    sentAt: '2024-11-02T09:00:00Z',
    expiresAt: '2024-11-30',
    completedAt: null,
    declinedAt: null,
    voidedAt: null,
    message: 'Acknowledge receipt of exit summary report.',
    certificateId: null,
    recipients: [
      recipient('rec-021-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'pending', 1, true),
    ],
    fields: [
      field('fld-021-1', 'signature', 'Investor Signature', 20, 'rec-021-a'),
    ],
    events: [
      event('sig-021-e1', '2024-11-01T10:00:00Z', 'created', 'Investhome Operations', 'Request created'),
      event('sig-021-e2', '2024-12-01T00:00:00Z', 'expired', 'System', 'Request expired without signature'),
    ],
  }),
  sig({
    id: 'sig-022',
    documentId: 'doc-016',
    documentTitle: 'Subscription Agreement — Campus Mixed-Use Fund I',
    investmentId: 'pi-004',
    investmentName: 'The Campus',
    entityName: 'Campus Mixed-Use Fund I',
    status: 'voided',
    createdAt: '2025-05-01T10:00:00Z',
    sentAt: '2025-05-02T09:00:00Z',
    expiresAt: '2025-06-01',
    completedAt: null,
    declinedAt: null,
    voidedAt: '2025-05-15T10:00:00Z',
    message: 'Amendment signature request voided — superseded by updated document.',
    certificateId: null,
    recipients: [
      recipient('rec-022-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'pending', 1, true),
    ],
    fields: [
      field('fld-022-1', 'signature', 'Investor Signature', 10, 'rec-022-a'),
    ],
    events: [
      event('sig-022-e1', '2025-05-01T10:00:00Z', 'created', 'Investhome Operations', 'Request created'),
      event('sig-022-e2', '2025-05-15T10:00:00Z', 'voided', 'Investhome Operations', 'Voided — document superseded'),
    ],
  }),
];

// Completed historical signatures referenced by documents
const historicalCompleted: SignatureRequest[] = [
  sig({
    id: 'sig-010',
    documentId: 'doc-003',
    documentTitle: 'Side Letter — Co-Investment Rights',
    investmentId: 'pi-001',
    investmentName: 'The Temple',
    entityName: 'Temple Holdings LLC',
    status: 'completed',
    createdAt: '2023-04-08T10:00:00Z',
    sentAt: '2023-04-08T11:00:00Z',
    expiresAt: '2023-04-30',
    completedAt: '2023-04-12T16:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Side letter for co-investment rights.',
    certificateId: 'cert-demo-010',
    recipients: [
      recipient('rec-010-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2023-04-12T16:00:00Z'),
    ],
    fields: [field('fld-010-1', 'signature', 'Investor Signature', 7, 'rec-010-a', true, CURRENT_USER, '2023-04-12T16:00:00Z')],
  }),
  sig({
    id: 'sig-011',
    documentId: 'doc-007',
    documentTitle: 'Subscription Agreement — Uniloft LP',
    investmentId: 'pi-002',
    investmentName: 'Uniloft',
    entityName: 'Uniloft Residential Partners LP',
    status: 'completed',
    createdAt: '2021-08-15T10:00:00Z',
    sentAt: '2021-08-16T09:00:00Z',
    expiresAt: '2021-09-15',
    completedAt: '2021-08-20T14:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Original subscription.',
    certificateId: 'cert-demo-011',
    recipients: [
      recipient('rec-011-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2021-08-20T14:00:00Z'),
    ],
    fields: [field('fld-011-1', 'signature', 'Investor Signature', 36, 'rec-011-a', true, CURRENT_USER, '2021-08-20T14:00:00Z')],
  }),
  sig({
    id: 'sig-012',
    documentId: 'doc-012',
    documentTitle: 'Subscription Agreement — 309 H Street',
    investmentId: 'pi-003',
    investmentName: '309 H Street',
    entityName: 'H Street Development Co.',
    status: 'completed',
    createdAt: '2022-11-01T10:00:00Z',
    sentAt: '2022-11-02T09:00:00Z',
    expiresAt: '2022-11-30',
    completedAt: '2022-11-05T15:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Subscription agreement.',
    certificateId: 'cert-demo-012',
    recipients: [
      recipient('rec-012-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2022-11-05T15:00:00Z'),
    ],
    fields: [field('fld-012-1', 'signature', 'Investor Signature', 34, 'rec-012-a', true, CURRENT_USER, '2022-11-05T15:00:00Z')],
  }),
  sig({
    id: 'sig-013',
    documentId: 'doc-016',
    documentTitle: 'Subscription Agreement — Campus Mixed-Use Fund I',
    investmentId: 'pi-004',
    investmentName: 'The Campus',
    entityName: 'Campus Mixed-Use Fund I',
    status: 'completed',
    createdAt: '2020-06-10T10:00:00Z',
    sentAt: '2020-06-11T09:00:00Z',
    expiresAt: '2020-07-15',
    completedAt: '2020-06-15T16:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Subscription agreement.',
    certificateId: 'cert-demo-013',
    recipients: [
      recipient('rec-013-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2020-06-15T16:00:00Z'),
    ],
    fields: [field('fld-013-1', 'signature', 'Investor Signature', 42, 'rec-013-a', true, CURRENT_USER, '2020-06-15T16:00:00Z')],
  }),
  sig({
    id: 'sig-014',
    documentId: 'doc-021',
    documentTitle: 'Subscription Agreement — Nelson Avenue',
    investmentId: 'pi-005',
    investmentName: 'Nelson Avenue',
    entityName: 'Nelson Avenue Equity LLC',
    status: 'completed',
    createdAt: '2019-03-18T10:00:00Z',
    sentAt: '2019-03-19T09:00:00Z',
    expiresAt: '2019-04-15',
    completedAt: '2019-03-22T14:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Subscription agreement.',
    certificateId: 'cert-demo-014',
    recipients: [
      recipient('rec-014-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2019-03-22T14:00:00Z'),
    ],
    fields: [field('fld-014-1', 'signature', 'Investor Signature', 30, 'rec-014-a', true, CURRENT_USER, '2019-03-22T14:00:00Z')],
  }),
  sig({
    id: 'sig-015',
    documentId: 'doc-024',
    documentTitle: 'Subscription Agreement — H Place Condominium Fund',
    investmentId: 'pi-006',
    investmentName: 'H Place Residences',
    entityName: 'H Place Condominium Fund',
    status: 'completed',
    createdAt: '2024-02-20T10:00:00Z',
    sentAt: '2024-02-21T09:00:00Z',
    expiresAt: '2024-03-15',
    completedAt: '2024-02-28T16:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Subscription agreement.',
    certificateId: 'cert-demo-015',
    recipients: [
      recipient('rec-015-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2024-02-28T16:00:00Z'),
    ],
    fields: [field('fld-015-1', 'signature', 'Investor Signature', 38, 'rec-015-a', true, CURRENT_USER, '2024-02-28T16:00:00Z')],
  }),
  sig({
    id: 'sig-016',
    documentId: 'doc-031',
    documentTitle: 'NDA — Capitol Heights Offering',
    investmentId: 'pi-008',
    investmentName: 'Capitol Heights',
    entityName: 'Capitol Heights Opportunity Zone Fund',
    status: 'completed',
    createdAt: '2025-06-01T10:00:00Z',
    sentAt: '2025-06-02T09:00:00Z',
    expiresAt: '2025-06-15',
    completedAt: '2025-06-03T14:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'NDA for offering materials.',
    certificateId: 'cert-demo-016',
    recipients: [
      recipient('rec-016-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2025-06-03T14:00:00Z'),
    ],
    fields: [field('fld-016-1', 'signature', 'Investor Signature', 4, 'rec-016-a', true, CURRENT_USER, '2025-06-03T14:00:00Z')],
  }),
  sig({
    id: 'sig-017',
    documentId: 'doc-032',
    documentTitle: 'Subscription Agreement — Georgetown Row',
    investmentId: 'pi-009',
    investmentName: 'Georgetown Row',
    entityName: 'Georgetown Heritage REIT',
    status: 'completed',
    createdAt: '2023-07-12T10:00:00Z',
    sentAt: '2023-07-13T09:00:00Z',
    expiresAt: '2023-08-15',
    completedAt: '2023-07-18T16:00:00Z',
    declinedAt: null,
    voidedAt: null,
    message: 'Subscription agreement.',
    certificateId: 'cert-demo-017',
    recipients: [
      recipient('rec-017-a', CURRENT_USER, CURRENT_EMAIL, 'investor', 'signed', 1, true, '2023-07-18T16:00:00Z'),
    ],
    fields: [field('fld-017-1', 'signature', 'Investor Signature', 32, 'rec-017-a', true, CURRENT_USER, '2023-07-18T16:00:00Z')],
  }),
];

const allRequests = [...signatureRequests, ...historicalCompleted];

export function getAllSignatureRequests(): SignatureRequest[] {
  return [...allRequests].sort(
    (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(),
  );
}

export function getSignatureRequestById(id: string): SignatureRequest | undefined {
  return allRequests.find((s) => s.id === id);
}

export function getSignatureRequestByDocumentId(
  documentId: string,
): SignatureRequest | undefined {
  return allRequests.find((s) => s.documentId === documentId);
}

export const SIGNATURE_STATUS_LABELS: Record<
  import('./document-types').SignatureRequestStatus,
  string
> = {
  draft: 'Draft',
  sent: 'Sent',
  action_required: 'Action Required',
  waiting_on_others: 'Waiting on Others',
  completed: 'Completed',
  declined: 'Declined',
  expired: 'Expired',
  voided: 'Voided',
};

export const SIGNATURE_TAB_LABELS: Record<
  import('./document-types').SignatureTab,
  string
> = {
  action_required: 'Action Required',
  waiting_on_others: 'Waiting on Others',
  completed: 'Completed',
  declined: 'Declined',
  expired: 'Expired',
  voided: 'Voided',
  all: 'All',
};
