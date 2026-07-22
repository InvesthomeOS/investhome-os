import { investorProfile } from './mock-data';
import type { Task, TaskChecklist, TaskOwner } from './messaging-types';

const INVESTOR: TaskOwner = {
  id: 'inv-001',
  name: investorProfile.name,
  role: 'Investor',
  avatarInitials: investorProfile.avatarInitials,
  emailMasked: 'e***@whitmorecapital.com',
};

const IR = {
  sarah: {
    id: 'ir-001',
    name: 'Sarah Chen',
    role: 'Relationship Manager',
    avatarInitials: 'SC',
    emailMasked: 's***@investhome.com',
  },
  james: {
    id: 'ir-004',
    name: 'James Okonkwo',
    role: 'Legal & Compliance',
    avatarInitials: 'JO',
    emailMasked: 'j***@investhome.com',
  },
  marcus: {
    id: 'ir-002',
    name: 'Marcus Webb',
    role: 'Investor Relations',
    avatarInitials: 'MW',
    emailMasked: 'm***@investhome.com',
  },
};

function checklist(id: string, title: string, items: TaskChecklist['items']): TaskChecklist {
  return { id, title, items };
}

function task(partial: Task): Task {
  const completed = partial.checklist.items.filter((i) => i.isCompleted).length;
  const total = partial.checklist.items.length;
  const progressPercent =
    total > 0 ? Math.round((completed / total) * 100) : partial.progressPercent;
  return { ...partial, progressPercent };
}

const tasks: Task[] = [
  task({
    id: 'task-001',
    title: 'Sign The Temple subscription agreement',
    description:
      'Review and electronically sign the Class A subscription agreement for The Temple development investment. All terms have been pre-approved by your legal counsel.',
    investmentId: 'pi-001',
    investmentName: 'The Temple',
    status: 'open',
    priority: 'critical',
    category: 'signature',
    dueDate: '2025-07-20',
    createdAt: '2025-06-28T10:00:00Z',
    updatedAt: '2025-07-10T14:30:00Z',
    completedAt: null,
    owner: IR.james,
    assignee: INVESTOR,
    checklist: checklist('cl-001', 'Signature steps', [
      { id: 'cl-001-1', label: 'Review subscription agreement', isCompleted: true, completedAt: '2025-07-05T11:00:00Z' },
      { id: 'cl-001-2', label: 'Verify investment amount ($1,500,000)', isCompleted: true, completedAt: '2025-07-05T11:15:00Z' },
      { id: 'cl-001-3', label: 'Apply electronic signature', isCompleted: false, completedAt: null },
      { id: 'cl-001-4', label: 'Confirm receipt', isCompleted: false, completedAt: null },
    ]),
    comments: [
      {
        id: 'tc-001-1',
        author: IR.james,
        body: 'Agreement has been updated per your counsel review. Ready for signature.',
        createdAt: '2025-07-05T14:00:00Z',
        isInternal: false,
      },
    ],
    attachments: [],
    activity: [
      { id: 'ta-001-1', type: 'created', description: 'Task created from signature request', actor: 'James Okonkwo', timestamp: '2025-06-28T10:00:00Z' },
      { id: 'ta-001-2', type: 'updated', description: 'Checklist item completed: Review subscription agreement', actor: investorProfile.name, timestamp: '2025-07-05T11:00:00Z' },
      { id: 'ta-001-3', type: 'reminder', description: 'Reminder sent: 10 days until deadline', actor: 'System', timestamp: '2025-07-10T14:30:00Z' },
    ],
    reminders: [
      { id: 'tr-001-1', label: 'Signature deadline', scheduledAt: '2025-07-20T23:59:59Z', status: 'upcoming' },
      { id: 'tr-001-2', label: 'First reminder', scheduledAt: '2025-07-10T09:00:00Z', status: 'sent' },
    ],
    relatedDocumentIds: ['doc-001'],
    relatedSignatureIds: ['sig-001'],
    relatedConversationIds: ['conv-004'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-002',
    title: 'Upload accreditation renewal documentation',
    description:
      'Provide updated accredited investor verification including CPA letter and brokerage statements dated within 90 days.',
    investmentId: null,
    investmentName: 'Account',
    status: 'in_progress',
    priority: 'high',
    category: 'accreditation',
    dueDate: '2025-08-01',
    createdAt: '2025-06-15T10:00:00Z',
    updatedAt: '2025-07-08T09:00:00Z',
    completedAt: null,
    owner: IR.james,
    assignee: INVESTOR,
    checklist: checklist('cl-002', 'Required documents', [
      { id: 'cl-002-1', label: 'CPA verification letter', isCompleted: false, completedAt: null },
      { id: 'cl-002-2', label: 'Brokerage statements (last 90 days)', isCompleted: false, completedAt: null },
      { id: 'cl-002-3', label: 'Completed accreditation form', isCompleted: true, completedAt: '2025-07-01T10:00:00Z' },
    ]),
    comments: [
      {
        id: 'tc-002-1',
        author: INVESTOR,
        body: 'Gathering CPA letter — expected by July 25.',
        createdAt: '2025-07-08T09:00:00Z',
        isInternal: false,
      },
      {
        id: 'tc-002-int',
        author: IR.james,
        body: 'Internal: Eleanor historically submits docs 3 days before deadline.',
        createdAt: '2025-07-08T09:05:00Z',
        isInternal: true,
      },
    ],
    attachments: [],
    activity: [
      { id: 'ta-002-1', type: 'created', description: 'Accreditation renewal task created', actor: 'James Okonkwo', timestamp: '2025-06-15T10:00:00Z' },
      { id: 'ta-002-2', type: 'comment', description: 'Investor commented on timeline', actor: investorProfile.name, timestamp: '2025-07-08T09:00:00Z' },
    ],
    reminders: [
      { id: 'tr-002-1', label: 'Renewal deadline', scheduledAt: '2025-08-01T23:59:59Z', status: 'upcoming' },
      { id: 'tr-002-2', label: '30-day reminder', scheduledAt: '2025-07-02T09:00:00Z', status: 'sent' },
    ],
    relatedDocumentIds: ['doc-002'],
    relatedSignatureIds: ['sig-002'],
    relatedConversationIds: ['conv-007'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-003',
    title: 'Review Q2 investor update — 309 H Street',
    description:
      'Review the Q2 2025 investor update covering lease-up progress, NOI projections, and revised exit timeline for 309 H Street.',
    investmentId: 'pi-003',
    investmentName: '309 H Street',
    status: 'overdue',
    priority: 'medium',
    category: 'review',
    dueDate: '2025-07-15',
    createdAt: '2025-07-01T09:00:00Z',
    updatedAt: '2025-07-15T09:00:00Z',
    completedAt: null,
    owner: IR.sarah,
    assignee: INVESTOR,
    checklist: checklist('cl-003', 'Review checklist', [
      { id: 'cl-003-1', label: 'Read executive summary', isCompleted: false, completedAt: null },
      { id: 'cl-003-2', label: 'Review financial exhibits', isCompleted: false, completedAt: null },
      { id: 'cl-003-3', label: 'Acknowledge receipt', isCompleted: false, completedAt: null },
    ]),
    comments: [],
    attachments: [
      {
        id: 'ta-att-003',
        fileName: 'Q2-Investor-Update-H-Street.pdf',
        fileType: 'pdf',
        fileSizeBytes: 1_234_567,
        uploadedAt: '2025-07-01T09:00:00Z',
        uploadedBy: 'Sarah Chen',
        isMock: true,
      },
    ],
    activity: [
      { id: 'ta-003-1', type: 'created', description: 'Review task assigned', actor: 'Sarah Chen', timestamp: '2025-07-01T09:00:00Z' },
      { id: 'ta-003-2', type: 'reminder', description: 'Due date reminder sent', actor: 'System', timestamp: '2025-07-14T09:00:00Z' },
    ],
    reminders: [
      { id: 'tr-003-1', label: 'Review deadline', scheduledAt: '2025-07-15T23:59:59Z', status: 'overdue' },
    ],
    relatedDocumentIds: ['doc-008'],
    relatedSignatureIds: [],
    relatedConversationIds: ['conv-016'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-004',
    title: 'Confirm Q3 portfolio review appointment',
    description: 'Confirm attendance for Q3 portfolio review with Sarah Chen on July 18 at 2:00 PM ET.',
    investmentId: null,
    investmentName: 'Portfolio',
    status: 'completed',
    priority: 'low',
    category: 'general',
    dueDate: '2025-07-18',
    createdAt: '2025-07-10T14:00:00Z',
    updatedAt: '2025-07-14T16:30:00Z',
    completedAt: '2025-07-14T16:30:00Z',
    owner: IR.sarah,
    assignee: INVESTOR,
    checklist: checklist('cl-004', 'Confirmation', [
      { id: 'cl-004-1', label: 'Review agenda', isCompleted: true, completedAt: '2025-07-14T16:00:00Z' },
      { id: 'cl-004-2', label: 'Confirm attendance', isCompleted: true, completedAt: '2025-07-14T16:30:00Z' },
    ]),
    comments: [
      {
        id: 'tc-004-1',
        author: INVESTOR,
        body: 'Confirmed — looking forward to the review.',
        createdAt: '2025-07-14T16:30:00Z',
        isInternal: false,
      },
    ],
    attachments: [],
    activity: [
      { id: 'ta-004-1', type: 'created', description: 'Appointment confirmation requested', actor: 'Sarah Chen', timestamp: '2025-07-10T14:00:00Z' },
      { id: 'ta-004-2', type: 'status_change', description: 'Status changed to completed', actor: investorProfile.name, timestamp: '2025-07-14T16:30:00Z' },
    ],
    reminders: [],
    relatedDocumentIds: [],
    relatedSignatureIds: [],
    relatedConversationIds: ['conv-001'],
    relatedDistributionIds: [],
    progressPercent: 100,
  }),

  task({
    id: 'task-005',
    title: 'Complete Capitol Heights subscription documents',
    description: 'Review and sign subscription documents for Capitol Heights Opportunity Zone Fund allocation.',
    investmentId: 'pi-008',
    investmentName: 'Capitol Heights',
    status: 'open',
    priority: 'high',
    category: 'signature',
    dueDate: '2025-07-25',
    createdAt: '2025-07-01T09:00:00Z',
    updatedAt: '2025-07-01T09:00:00Z',
    completedAt: null,
    owner: IR.sarah,
    assignee: INVESTOR,
    checklist: checklist('cl-005', 'Subscription steps', [
      { id: 'cl-005-1', label: 'Review offering memorandum', isCompleted: false, completedAt: null },
      { id: 'cl-005-2', label: 'Sign subscription agreement', isCompleted: false, completedAt: null },
      { id: 'cl-005-3', label: 'Submit wire instructions', isCompleted: false, completedAt: null },
    ]),
    comments: [],
    attachments: [],
    activity: [
      { id: 'ta-005-1', type: 'created', description: 'Subscription task created', actor: 'Sarah Chen', timestamp: '2025-07-01T09:00:00Z' },
    ],
    reminders: [
      { id: 'tr-005-1', label: 'Subscription deadline', scheduledAt: '2025-07-25T23:59:59Z', status: 'upcoming' },
    ],
    relatedDocumentIds: ['doc-015'],
    relatedSignatureIds: ['sig-003'],
    relatedConversationIds: ['conv-011'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-006',
    title: 'Download 2024 K-1 — Uniloft',
    description: 'Download and retain your 2024 K-1 tax document for Uniloft Residential Partners LP for tax filing purposes.',
    investmentId: 'pi-002',
    investmentName: 'Uniloft',
    status: 'open',
    priority: 'medium',
    category: 'tax',
    dueDate: '2025-07-31',
    createdAt: '2025-06-28T09:15:00Z',
    updatedAt: '2025-06-28T09:15:00Z',
    completedAt: null,
    owner: IR.james,
    assignee: INVESTOR,
    checklist: checklist('cl-006', 'Tax document', [
      { id: 'cl-006-1', label: 'Download K-1 PDF', isCompleted: false, completedAt: null },
      { id: 'cl-006-2', label: 'Forward to tax preparer', isCompleted: false, completedAt: null },
    ]),
    comments: [],
    attachments: [],
    activity: [
      { id: 'ta-006-1', type: 'created', description: 'K-1 availability task created', actor: 'James Okonkwo', timestamp: '2025-06-28T09:15:00Z' },
    ],
    reminders: [
      { id: 'tr-006-1', label: 'Tax filing reminder', scheduledAt: '2025-07-31T23:59:59Z', status: 'upcoming' },
    ],
    relatedDocumentIds: ['doc-006'],
    relatedSignatureIds: [],
    relatedConversationIds: ['conv-012'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-007',
    title: 'Sign amended operating agreement — The Campus',
    description: 'Review and sign the amended operating agreement for The Campus Mixed-Use Fund I by July 25.',
    investmentId: 'pi-004',
    investmentName: 'The Campus',
    status: 'open',
    priority: 'high',
    category: 'signature',
    dueDate: '2025-07-25',
    createdAt: '2025-07-13T10:00:00Z',
    updatedAt: '2025-07-13T10:00:00Z',
    completedAt: null,
    owner: IR.james,
    assignee: INVESTOR,
    checklist: checklist('cl-007', 'Legal review', [
      { id: 'cl-007-1', label: 'Review amendment summary', isCompleted: false, completedAt: null },
      { id: 'cl-007-2', label: 'Apply e-signature', isCompleted: false, completedAt: null },
    ]),
    comments: [],
    attachments: [],
    activity: [
      { id: 'ta-007-1', type: 'created', description: 'Legal signature task created', actor: 'James Okonkwo', timestamp: '2025-07-13T10:00:00Z' },
    ],
    reminders: [
      { id: 'tr-007-1', label: 'Signature deadline', scheduledAt: '2025-07-25T23:59:59Z', status: 'upcoming' },
    ],
    relatedDocumentIds: ['doc-010'],
    relatedSignatureIds: ['sig-004'],
    relatedConversationIds: ['conv-015'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-008',
    title: 'Upload delegate authorization form',
    description: 'Complete and upload the read-only delegate authorization form for your CFO portal access.',
    investmentId: null,
    investmentName: 'Account',
    status: 'pending_review',
    priority: 'low',
    category: 'document_upload',
    dueDate: '2025-07-30',
    createdAt: '2025-07-02T11:30:00Z',
    updatedAt: '2025-07-14T10:00:00Z',
    completedAt: null,
    owner: IR.marcus,
    assignee: INVESTOR,
    checklist: checklist('cl-008', 'Upload steps', [
      { id: 'cl-008-1', label: 'Complete authorization form', isCompleted: true, completedAt: '2025-07-14T09:00:00Z' },
      { id: 'cl-008-2', label: 'Upload signed form', isCompleted: true, completedAt: '2025-07-14T10:00:00Z' },
      { id: 'cl-008-3', label: 'Await compliance review', isCompleted: false, completedAt: null },
    ]),
    comments: [
      {
        id: 'tc-008-1',
        author: INVESTOR,
        body: 'Uploaded signed delegate form for Michael Torres, CFO.',
        createdAt: '2025-07-14T10:00:00Z',
        isInternal: false,
      },
    ],
    attachments: [
      {
        id: 'ta-att-008',
        fileName: 'Delegate-Authorization-Signed.pdf',
        fileType: 'pdf',
        fileSizeBytes: 198_432,
        uploadedAt: '2025-07-14T10:00:00Z',
        uploadedBy: investorProfile.name,
        isMock: true,
      },
    ],
    activity: [
      { id: 'ta-008-1', type: 'created', description: 'Upload task created', actor: 'Marcus Webb', timestamp: '2025-07-02T11:30:00Z' },
      { id: 'ta-008-2', type: 'attachment', description: 'Document uploaded', actor: investorProfile.name, timestamp: '2025-07-14T10:00:00Z' },
      { id: 'ta-008-3', type: 'status_change', description: 'Status changed to pending review', actor: 'System', timestamp: '2025-07-14T10:00:00Z' },
    ],
    reminders: [],
    relatedDocumentIds: [],
    relatedSignatureIds: [],
    relatedConversationIds: ['conv-013'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-009',
    title: 'Review Georgetown Row construction photos',
    description: 'Review latest construction progress photos and provide feedback if desired.',
    investmentId: 'pi-009',
    investmentName: 'Georgetown Row',
    status: 'open',
    priority: 'low',
    category: 'review',
    dueDate: '2025-07-22',
    createdAt: '2025-07-06T14:00:00Z',
    updatedAt: '2025-07-06T14:00:00Z',
    completedAt: null,
    owner: IR.marcus,
    assignee: INVESTOR,
    checklist: checklist('cl-009', 'Review', [
      { id: 'cl-009-1', label: 'View progress photos', isCompleted: false, completedAt: null },
    ]),
    comments: [],
    attachments: [],
    activity: [
      { id: 'ta-009-1', type: 'created', description: 'Review task created', actor: 'Marcus Webb', timestamp: '2025-07-06T14:00:00Z' },
    ],
    reminders: [],
    relatedDocumentIds: ['doc-014'],
    relatedSignatureIds: [],
    relatedConversationIds: ['conv-010'],
    relatedDistributionIds: [],
    progressPercent: 0,
  }),

  task({
    id: 'task-010',
    title: 'Confirm wire instructions for Q3 distribution',
    description: 'Verify ACH wire instructions on file for upcoming Uniloft Q3 distribution.',
    investmentId: 'pi-002',
    investmentName: 'Uniloft',
    status: 'open',
    priority: 'medium',
    category: 'distribution',
    dueDate: '2025-07-16',
    createdAt: '2025-07-10T08:00:00Z',
    updatedAt: '2025-07-10T08:00:00Z',
    completedAt: null,
    owner: IR.marcus,
    assignee: INVESTOR,
    checklist: checklist('cl-010', 'Verification', [
      { id: 'cl-010-1', label: 'Review bank account on file (••••4821)', isCompleted: false, completedAt: null },
      { id: 'cl-010-2', label: 'Confirm or update instructions', isCompleted: false, completedAt: null },
    ]),
    comments: [],
    attachments: [],
    activity: [
      { id: 'ta-010-1', type: 'created', description: 'Wire verification task created', actor: 'Marcus Webb', timestamp: '2025-07-10T08:00:00Z' },
    ],
    reminders: [
      { id: 'tr-010-1', label: 'Due today', scheduledAt: '2025-07-16T23:59:59Z', status: 'due_today' },
    ],
    relatedDocumentIds: [],
    relatedSignatureIds: [],
    relatedConversationIds: ['conv-003'],
    relatedDistributionIds: ['dist-002-05'],
    progressPercent: 0,
  }),
];

export function getAllTasks(): Task[] {
  return tasks.map((t) => ({
    ...t,
    comments: t.comments.filter((c) => !c.isInternal),
    checklist: { ...t.checklist, items: [...t.checklist.items] },
    activity: [...t.activity],
    reminders: [...t.reminders],
    attachments: [...t.attachments],
  }));
}

export function getTaskById(id: string): Task | undefined {
  const found = tasks.find((t) => t.id === id);
  if (!found) return undefined;
  return {
    ...found,
    comments: found.comments.filter((c) => !c.isInternal),
    checklist: { ...found.checklist, items: [...found.checklist.items] },
    activity: [...found.activity],
    reminders: [...found.reminders],
    attachments: [...found.attachments],
  };
}

export function getVisibleTaskComments(task: Task) {
  return task.comments.filter((c) => !c.isInternal);
}
