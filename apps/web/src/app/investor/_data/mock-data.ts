import type {
  DashboardKpis,
  Distribution,
  Investment,
  InvestorNotification,
  InvestorProfile,
  PendingDocument,
  TimelineEvent,
} from './types';

export const investorProfile: InvestorProfile = {
  id: 'inv-001',
  name: 'Eleanor Whitmore',
  email: 'eleanor.whitmore@whitmorecapital.com',
  avatarInitials: 'EW',
  memberSince: '2019-03-15',
  investorTier: 'platinum',
  phone: '+1 (212) 555-0147',
};

export const investments: Investment[] = [
  {
    id: 'invst-001',
    name: 'Harborview Residences — Class A',
    property: 'Harborview Residences',
    location: 'Miami, FL',
    status: 'active',
    investedAmount: 750_000,
    currentValue: 892_500,
    equity: 19.0,
    roi: 14.2,
    irr: 11.8,
    currency: 'USD',
    investedAt: '2022-06-01',
    projectedExitDate: '2027-06-01',
  },
  {
    id: 'invst-002',
    name: 'Summit Ridge Townhomes',
    property: 'Summit Ridge',
    location: 'Denver, CO',
    status: 'active',
    investedAmount: 500_000,
    currentValue: 545_000,
    equity: 9.0,
    roi: 9.8,
    irr: 8.4,
    currency: 'USD',
    investedAt: '2023-01-15',
    projectedExitDate: '2028-01-15',
  },
  {
    id: 'invst-003',
    name: 'Lakeside Mixed-Use Fund II',
    property: 'Lakeside District',
    location: 'Austin, TX',
    status: 'active',
    investedAmount: 1_250_000,
    currentValue: 1_437_500,
    equity: 15.0,
    roi: 16.5,
    irr: 13.2,
    currency: 'USD',
    investedAt: '2021-09-10',
    projectedExitDate: '2026-09-10',
  },
  {
    id: 'invst-004',
    name: 'Pacific Heights Condos',
    property: 'Pacific Heights',
    location: 'San Francisco, CA',
    status: 'matured',
    investedAmount: 400_000,
    currentValue: 512_000,
    equity: 28.0,
    roi: 22.1,
    irr: 17.6,
    currency: 'USD',
    investedAt: '2019-11-20',
    projectedExitDate: '2024-11-20',
  },
  {
    id: 'invst-005',
    name: 'Riverside Industrial Park',
    property: 'Riverside Industrial',
    location: 'Phoenix, AZ',
    status: 'pending',
    investedAmount: 300_000,
    currentValue: 300_000,
    equity: 0,
    roi: 0,
    irr: 0,
    currency: 'USD',
    investedAt: '2025-02-01',
    projectedExitDate: '2030-02-01',
  },
  {
    id: 'invst-006',
    name: 'Cedar Grove Senior Living',
    property: 'Cedar Grove',
    location: 'Nashville, TN',
    status: 'exited',
    investedAmount: 600_000,
    currentValue: 798_000,
    equity: 33.0,
    roi: 31.4,
    irr: 24.2,
    currency: 'USD',
    investedAt: '2018-04-05',
    projectedExitDate: '2023-04-05',
  },
];

export const distributions: Distribution[] = [
  {
    id: 'dist-001',
    investmentId: 'invst-001',
    investmentName: 'Harborview Residences — Class A',
    amount: 18_750,
    currency: 'USD',
    scheduledDate: '2025-07-31',
    status: 'scheduled',
  },
  {
    id: 'dist-002',
    investmentId: 'invst-003',
    investmentName: 'Lakeside Mixed-Use Fund II',
    amount: 31_250,
    currency: 'USD',
    scheduledDate: '2025-08-15',
    status: 'scheduled',
  },
  {
    id: 'dist-003',
    investmentId: 'invst-002',
    investmentName: 'Summit Ridge Townhomes',
    amount: 12_500,
    currency: 'USD',
    scheduledDate: '2025-06-30',
    status: 'paid',
  },
  {
    id: 'dist-004',
    investmentId: 'invst-001',
    investmentName: 'Harborview Residences — Class A',
    amount: 18_750,
    currency: 'USD',
    scheduledDate: '2025-04-30',
    status: 'paid',
  },
  {
    id: 'dist-005',
    investmentId: 'invst-003',
    investmentName: 'Lakeside Mixed-Use Fund II',
    amount: 31_250,
    currency: 'USD',
    scheduledDate: '2025-05-15',
    status: 'paid',
  },
];

export const timelineEvents: TimelineEvent[] = [
  {
    id: 'evt-001',
    type: 'distribution',
    title: 'Distribution received',
    description: 'Q2 distribution of $12,500 from Summit Ridge Townhomes deposited to your account.',
    timestamp: '2025-06-30T14:22:00Z',
  },
  {
    id: 'evt-002',
    type: 'document',
    title: 'K-1 tax document available',
    description: '2024 K-1 for Lakeside Mixed-Use Fund II is ready for download.',
    timestamp: '2025-06-28T09:15:00Z',
  },
  {
    id: 'evt-003',
    type: 'signature',
    title: 'Subscription agreement pending',
    description: 'Riverside Industrial Park subscription agreement requires your signature.',
    timestamp: '2025-06-25T16:40:00Z',
  },
  {
    id: 'evt-004',
    type: 'message',
    title: 'Portfolio review scheduled',
    description: 'Your relationship manager confirmed a Q3 portfolio review for July 18.',
    timestamp: '2025-06-22T11:00:00Z',
  },
  {
    id: 'evt-005',
    type: 'investment',
    title: 'Capital call processed',
    description: 'Capital call of $300,000 for Riverside Industrial Park was successfully funded.',
    timestamp: '2025-06-18T08:30:00Z',
  },
  {
    id: 'evt-006',
    type: 'task',
    title: 'Accreditation renewal due',
    description: 'Please upload updated accreditation documentation by August 1, 2025.',
    timestamp: '2025-06-15T10:00:00Z',
  },
  {
    id: 'evt-007',
    type: 'distribution',
    title: 'Distribution received',
    description: 'Q2 distribution of $18,750 from Harborview Residences deposited to your account.',
    timestamp: '2025-04-30T14:22:00Z',
  },
];

export const notifications: InvestorNotification[] = [
  {
    id: 'notif-001',
    title: 'Upcoming distribution',
    message: 'Harborview Residences distribution of $18,750 scheduled for July 31.',
    read: false,
    timestamp: '2025-07-10T08:00:00Z',
    type: 'info',
  },
  {
    id: 'notif-002',
    title: 'Document requires signature',
    message: 'Riverside Industrial Park subscription agreement is awaiting your signature.',
    read: false,
    timestamp: '2025-07-08T14:30:00Z',
    type: 'action',
  },
  {
    id: 'notif-003',
    title: 'New message from RM',
    message: 'Sarah Chen sent you a message regarding Q3 portfolio allocation.',
    read: false,
    timestamp: '2025-07-07T11:15:00Z',
    type: 'info',
  },
  {
    id: 'notif-004',
    title: 'Performance report available',
    message: 'Your Q2 2025 portfolio performance report is now available.',
    read: true,
    timestamp: '2025-07-01T09:00:00Z',
    type: 'info',
  },
  {
    id: 'notif-005',
    title: 'Accreditation renewal',
    message: 'Your accredited investor status renewal is due in 30 days.',
    read: true,
    timestamp: '2025-06-28T16:45:00Z',
    type: 'alert',
  },
];

export const pendingDocuments: PendingDocument[] = [
  {
    id: 'doc-001',
    title: 'Subscription Agreement — Riverside Industrial Park',
    investmentName: 'Riverside Industrial Park',
    dueDate: '2025-07-20',
    requiresSignature: true,
  },
  {
    id: 'doc-002',
    title: 'Accreditation Renewal Form',
    investmentName: 'Account',
    dueDate: '2025-08-01',
    requiresSignature: true,
  },
  {
    id: 'doc-003',
    title: 'Q2 2025 Investor Update — Lakeside Fund II',
    investmentName: 'Lakeside Mixed-Use Fund II',
    dueDate: '2025-07-15',
    requiresSignature: false,
  },
];

export const dashboardKpis: DashboardKpis = {
  totalInvested: 3_800_000,
  portfolioValue: 4_485_000,
  estimatedEquity: 18.0,
  annualCashFlow: 243_750,
  projectedRoi: 15.8,
  irr: 12.4,
  nextDistribution: {
    date: '2025-07-31',
    amount: 18_750,
    currency: 'USD',
    investmentName: 'Harborview Residences — Class A',
  },
  unreadMessages: 3,
  pendingDocuments: 3,
  pendingSignatures: 2,
  currency: 'USD',
};

export function formatInvestorCurrency(
  amount: number,
  currency = 'USD',
  locale = 'en-US',
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatInvestorPercent(value: number, locale = 'en-US'): string {
  return new Intl.NumberFormat(locale, {
    style: 'percent',
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(value / 100);
}

export function formatInvestorDate(dateStr: string, locale = 'en-US'): string {
  return new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateStr));
}

export function formatInvestorDateTime(dateStr: string, locale = 'en-US'): string {
  return new Intl.DateTimeFormat(locale, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr));
}
