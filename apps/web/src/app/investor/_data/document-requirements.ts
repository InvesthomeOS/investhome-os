import type { DocumentRequirement } from './document-types';

export const documentRequirements: DocumentRequirement[] = [
  {
    id: 'req-001',
    title: 'Form W-9 — Updated Tax Information',
    description:
      'An updated W-9 is required for The Temple investment before year-end tax reporting.',
    documentType: 'w9',
    investmentId: 'pi-001',
    investmentName: 'The Temple',
    status: 'missing',
    dueDate: '2025-12-31',
    priority: 'high',
    category: 'tax',
  },
  {
    id: 'req-002',
    title: 'Accreditation Renewal Letter',
    description:
      'Your accredited investor verification for 309 H Street has expired. Upload a new third-party verification letter.',
    documentType: 'accreditation_letter',
    investmentId: 'pi-003',
    investmentName: '309 H Street',
    status: 'expired',
    dueDate: '2025-08-01',
    priority: 'high',
    category: 'compliance',
  },
  {
    id: 'req-003',
    title: 'Investor Questionnaire — Capitol Heights',
    description:
      'Complete the suitability questionnaire before your Capitol Heights subscription can be finalized.',
    documentType: 'consent_form',
    investmentId: 'pi-008',
    investmentName: 'Capitol Heights',
    status: 'pending_review',
    dueDate: '2025-08-30',
    priority: 'medium',
    category: 'compliance',
  },
  {
    id: 'req-004',
    title: 'Wire Instructions Acknowledgment',
    description:
      'Sign the wire instructions acknowledgment for Georgetown Row distribution payments.',
    documentType: 'wire_instructions',
    investmentId: 'pi-009',
    investmentName: 'Georgetown Row',
    status: 'missing',
    dueDate: '2025-07-31',
    priority: 'medium',
    category: 'financial',
  },
  {
    id: 'req-005',
    title: 'Account-Level W-9 on File',
    description:
      'Ensure a current W-9 is on file at the account level for consolidated tax reporting.',
    documentType: 'w9',
    investmentId: null,
    investmentName: null,
    status: 'submitted',
    dueDate: '2025-12-31',
    priority: 'low',
    category: 'tax',
  },
];

export function getAllDocumentRequirements(): DocumentRequirement[] {
  return [...documentRequirements];
}

export function getMissingRequirements(): DocumentRequirement[] {
  return documentRequirements.filter(
    (r) => r.status === 'missing' || r.status === 'expired',
  );
}

export const REQUIREMENT_STATUS_LABELS: Record<
  DocumentRequirement['status'],
  string
> = {
  missing: 'Missing',
  pending_review: 'Pending Review',
  submitted: 'Submitted',
  approved: 'Approved',
  expired: 'Expired',
};
