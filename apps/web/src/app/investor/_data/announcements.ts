import type { Announcement } from './messaging-types';

function ann(
  partial: Omit<Announcement, 'isRead'> & { isRead?: boolean },
): Announcement {
  return { isRead: false, ...partial };
}

export const announcements: Announcement[] = [
  ann({
    id: 'ann-001',
    title: 'Q3 2025 Investor Portal Enhancements',
    summary: 'New portfolio analytics, distribution tracking, and secure messaging features now live.',
    body: 'We are pleased to announce significant enhancements to your Investor Workspace. Portfolio analytics now include benchmark comparisons, risk metrics, and cash flow projections. The distributions module provides detailed breakdowns and tax summaries. Messages and tasks are fully integrated with your investment activity.',
    category: 'platform',
    publishedAt: '2025-07-10T09:00:00Z',
    expiresAt: null,
    priority: 'normal',
    attachments: [],
    actionLabel: 'Explore Portfolio',
    actionHref: '/investor/portfolio',
  }),
  ann({
    id: 'ann-002',
    title: 'Annual Investor Summit — Save the Date',
    summary: 'Join us September 12, 2025 in Washington, DC for our annual investor summit.',
    body: 'Mark your calendar for the Investhome Annual Investor Summit on September 12, 2025 at the Willard InterContinental, Washington DC. The program includes portfolio reviews, market outlook sessions, and exclusive property tours.',
    category: 'events',
    publishedAt: '2025-07-05T10:00:00Z',
    expiresAt: '2025-09-12T23:59:59Z',
    priority: 'normal',
    attachments: [
      {
        id: 'ann-att-001',
        fileName: 'Summit-2025-Agenda.pdf',
        fileType: 'pdf',
        fileSizeBytes: 456_789,
        isMock: true,
      },
    ],
    actionLabel: 'RSVP',
    actionHref: null,
    isRead: true,
  }),
  ann({
    id: 'ann-003',
    title: 'Updated Privacy Policy & Data Handling',
    summary: 'Review our updated privacy policy effective August 1, 2025.',
    body: 'We have updated our privacy policy to reflect enhanced data protection measures and GDPR compliance. No action is required unless you wish to review the changes.',
    category: 'compliance',
    publishedAt: '2025-07-01T08:00:00Z',
    expiresAt: null,
    priority: 'low',
    attachments: [
      {
        id: 'ann-att-002',
        fileName: 'Privacy-Policy-2025.pdf',
        fileType: 'pdf',
        fileSizeBytes: 234_567,
        isMock: true,
      },
    ],
    actionLabel: 'View Policy',
    actionHref: '/investor/settings',
  }),
  ann({
    id: 'ann-004',
    title: 'Capitol Heights Fund — Now Open for Investment',
    summary: 'Opportunity Zone fund accepting allocations through September 30.',
    body: 'Capitol Heights Opportunity Zone Fund is now accepting investor allocations. Early investors benefit from enhanced preferred return terms during the initial closing period.',
    category: 'portfolio',
    publishedAt: '2025-06-28T12:00:00Z',
    expiresAt: '2025-09-30T23:59:59Z',
    priority: 'high',
    attachments: [],
    actionLabel: 'View Investment',
    actionHref: '/investor/investments/pi-008',
  }),
  ann({
    id: 'ann-005',
    title: 'Scheduled Maintenance — July 20',
    summary: 'Brief portal maintenance window planned for July 20, 2:00–4:00 AM ET.',
    body: 'Investor portal will undergo routine maintenance on July 20 from 2:00–4:00 AM ET. Documents and messaging will be temporarily unavailable.',
    category: 'maintenance',
    publishedAt: '2025-07-14T07:00:00Z',
    expiresAt: '2025-07-20T08:00:00Z',
    priority: 'low',
    attachments: [],
    actionLabel: null,
    actionHref: null,
  }),
  ann({
    id: 'ann-006',
    title: 'Tax Season Reminder — K-1 Documents',
    summary: '2024 K-1 tax documents are being distributed through July.',
    body: 'All 2024 K-1 partnership tax documents will be available in your Documents section by July 31. Contact your relationship manager with questions.',
    category: 'compliance',
    publishedAt: '2025-06-25T09:00:00Z',
    expiresAt: '2025-07-31T23:59:59Z',
    priority: 'normal',
    attachments: [],
    actionLabel: 'View Documents',
    actionHref: '/investor/documents',
  }),
];

export function getAllAnnouncements(): Announcement[] {
  return [...announcements];
}

export function getAnnouncementById(id: string): Announcement | undefined {
  return announcements.find((a) => a.id === id);
}
