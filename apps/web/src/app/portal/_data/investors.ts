import type {
  Contract,
  Payment,
  PortalDocument,
  PortalInvestor,
  PortalMeeting,
  PortalMessage,
  PortalNotification,
  PortalTask,
  PortfolioHolding,
  ProjectDetail,
  RentalIncomeRow,
  Reservation,
  ReportPreset,
  DeviceSession,
} from './types';

/** Demo investor A — the only identity used in the portal session. */
export const INVESTOR_A_ID = 'portal-inv-a';
/** Isolated investor B — never returned to A; used for permission tests. */
export const INVESTOR_B_ID = 'portal-inv-b';

export const investorA: PortalInvestor = {
  id: INVESTOR_A_ID,
  fullName: 'Ayşe Yılmaz',
  email: 'investor.a@investhome.demo',
  phone: '+90 532 100 2001',
  city: 'İstanbul',
  country: 'Türkiye',
  tier: 'platinum',
  memberSince: '2022-03-15',
  language: 'tr',
  avatarInitials: 'AY',
  twoFactorEnabled: true,
};

export const investorB: PortalInvestor = {
  id: INVESTOR_B_ID,
  fullName: 'Marmara Capital Partners',
  email: 'investor.b@investhome.demo',
  phone: '+90 212 555 0100',
  city: 'İstanbul',
  country: 'Türkiye',
  tier: 'preferred',
  memberSince: '2021-08-01',
  language: 'tr',
  avatarInitials: 'MC',
  twoFactorEnabled: false,
};

export const holdingsA: PortfolioHolding[] = [
  {
    id: 'hold-a1',
    projectId: 'proj-nisantasi',
    projectName: 'Nişantaşı Residence',
    location: 'İstanbul · Şişli',
    status: 'rental',
    committed: 2_500_000,
    invested: 2_500_000,
    currentValue: 2_875_000,
    ownershipPct: 4.2,
    irr: 11.4,
    roi: 15.0,
    currency: 'TRY',
    sparkline: [2.1, 2.2, 2.25, 2.4, 2.5, 2.62, 2.75, 2.88],
  },
  {
    id: 'hold-a2',
    projectId: 'proj-cadde',
    projectName: 'Caddebostan Gardens',
    location: 'İstanbul · Kadıköy',
    status: 'construction',
    committed: 1_800_000,
    invested: 1_260_000,
    currentValue: 1_350_000,
    ownershipPct: 2.8,
    irr: 9.6,
    roi: 7.1,
    currency: 'TRY',
    sparkline: [1.0, 1.05, 1.1, 1.15, 1.2, 1.26, 1.3, 1.35],
  },
  {
    id: 'hold-a3',
    projectId: 'proj-ankara',
    projectName: 'Çankaya Terraces',
    location: 'Ankara · Çankaya',
    status: 'active',
    committed: 950_000,
    invested: 950_000,
    currentValue: 1_020_000,
    ownershipPct: 3.1,
    irr: 8.2,
    roi: 7.4,
    currency: 'TRY',
    sparkline: [0.9, 0.92, 0.94, 0.95, 0.97, 0.99, 1.0, 1.02],
  },
];

/** Investor B holdings — must never appear in A session. */
export const holdingsB: PortfolioHolding[] = [
  {
    id: 'hold-b1',
    projectId: 'proj-bosphorus',
    projectName: 'Bosphorus Tower (CONFIDENTIAL B)',
    location: 'İstanbul · Beşiktaş',
    status: 'active',
    committed: 12_000_000,
    invested: 12_000_000,
    currentValue: 14_400_000,
    ownershipPct: 18.0,
    irr: 14.2,
    roi: 20.0,
    currency: 'TRY',
    sparkline: [10, 11, 12, 12.5, 13, 13.5, 14, 14.4],
  },
];

export const projectsA: ProjectDetail[] = [
  {
    id: 'proj-nisantasi',
    name: 'Nişantaşı Residence',
    location: 'İstanbul · Şişli',
    status: 'rental',
    completionPct: 100,
    overview:
      'Boutique residential development in Nişantaşı with 48 units. Stabilized rental phase with institutional property management.',
    photos: [
      { id: 'ph1', caption: 'Street façade', tone: 'warm' },
      { id: 'ph2', caption: 'Lobby', tone: 'stone' },
      { id: 'ph3', caption: 'Typical unit', tone: 'soft' },
      { id: 'ph4', caption: 'Rooftop', tone: 'sky' },
    ],
    milestones: [
      { id: 'm1', title: 'Foundation', date: '2022-06-01', status: 'done' },
      { id: 'm2', title: 'Structure complete', date: '2023-04-15', status: 'done' },
      { id: 'm3', title: 'Handover', date: '2024-02-01', status: 'done' },
      { id: 'm4', title: 'Stabilization', date: '2024-08-01', status: 'current' },
    ],
    budget: [
      { label: 'Land', planned: 48_000_000, actual: 48_000_000 },
      { label: 'Construction', planned: 72_000_000, actual: 74_200_000 },
      { label: 'Soft costs', planned: 12_000_000, actual: 11_400_000 },
    ],
    news: [
      {
        id: 'n1',
        title: 'Q2 occupancy update',
        date: '2026-07-01',
        summary: 'Occupancy reached 96%. Net rental distribution scheduled for 31 July.',
      },
      {
        id: 'n2',
        title: 'Facade maintenance complete',
        date: '2026-05-12',
        summary: 'Scheduled facade works finished without unit disruption.',
      },
    ],
    rentalProjection: [
      { month: 'Şub', amount: 42_000 },
      { month: 'Mar', amount: 43_500 },
      { month: 'Nis', amount: 44_000 },
      { month: 'May', amount: 45_200 },
      { month: 'Haz', amount: 46_000 },
      { month: 'Tem', amount: 46_800 },
    ],
    map: { lat: 41.0505, lng: 28.9902, label: 'Nişantaşı Residence' },
    documentIds: ['doc-a1', 'doc-a2', 'doc-a5'],
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'proj-cadde',
    name: 'Caddebostan Gardens',
    location: 'İstanbul · Kadıköy',
    status: 'construction',
    completionPct: 62,
    overview:
      'Waterfront residential project with 120 units. Construction phase — your capital calls are tracked under Payments.',
    photos: [
      { id: 'ph5', caption: 'Site aerial', tone: 'sky' },
      { id: 'ph6', caption: 'Core structure', tone: 'stone' },
      { id: 'ph7', caption: 'Show flat', tone: 'warm' },
    ],
    milestones: [
      { id: 'm5', title: 'Excavation', date: '2025-01-10', status: 'done' },
      { id: 'm6', title: 'Core & shell', date: '2025-11-01', status: 'done' },
      { id: 'm7', title: 'MEP rough-in', date: '2026-06-15', status: 'current' },
      { id: 'm8', title: 'Finishes', date: '2027-03-01', status: 'upcoming' },
    ],
    budget: [
      { label: 'Land', planned: 90_000_000, actual: 90_000_000 },
      { label: 'Construction', planned: 180_000_000, actual: 112_000_000 },
      { label: 'Contingency', planned: 18_000_000, actual: 4_200_000 },
    ],
    news: [
      {
        id: 'n3',
        title: 'MEP tender awarded',
        date: '2026-06-20',
        summary: 'Mechanical package awarded; schedule remains on baseline.',
      },
    ],
    rentalProjection: [
      { month: '2027 Q1', amount: 0 },
      { month: '2027 Q2', amount: 28_000 },
      { month: '2027 Q3', amount: 52_000 },
      { month: '2027 Q4', amount: 68_000 },
    ],
    map: { lat: 40.9638, lng: 29.0625, label: 'Caddebostan Gardens' },
    documentIds: ['doc-a3', 'doc-a4'],
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'proj-ankara',
    name: 'Çankaya Terraces',
    location: 'Ankara · Çankaya',
    status: 'active',
    completionPct: 88,
    overview: 'Mid-market residential in Çankaya with phased delivery through 2026.',
    photos: [
      { id: 'ph8', caption: 'Entrance', tone: 'soft' },
      { id: 'ph9', caption: 'Garden', tone: 'warm' },
    ],
    milestones: [
      { id: 'm9', title: 'Permit', date: '2024-02-01', status: 'done' },
      { id: 'm10', title: 'Structure', date: '2025-08-01', status: 'done' },
      { id: 'm11', title: 'Delivery block A', date: '2026-09-01', status: 'current' },
    ],
    budget: [
      { label: 'Total development', planned: 65_000_000, actual: 61_800_000 },
    ],
    news: [],
    rentalProjection: [
      { month: 'Q3', amount: 18_000 },
      { month: 'Q4', amount: 22_000 },
      { month: '2027', amount: 96_000 },
    ],
    map: { lat: 39.9075, lng: 32.86, label: 'Çankaya Terraces' },
    documentIds: ['doc-a6'],
    investorId: INVESTOR_A_ID,
  },
];

export const projectsB: ProjectDetail[] = [
  {
    id: 'proj-bosphorus',
    name: 'Bosphorus Tower (CONFIDENTIAL B)',
    location: 'İstanbul · Beşiktaş',
    status: 'active',
    completionPct: 70,
    overview: 'Investor B exclusive project — must not leak to investor A.',
    photos: [],
    milestones: [],
    budget: [],
    news: [],
    rentalProjection: [],
    map: { lat: 41.0422, lng: 29.0067, label: 'Bosphorus Tower' },
    documentIds: ['doc-b1'],
    investorId: INVESTOR_B_ID,
  },
];

export const reservationsA: Reservation[] = [
  {
    id: 'res-a1',
    projectName: 'Caddebostan Gardens',
    unit: 'B-1204',
    status: 'confirmed',
    reservedAt: '2026-05-10',
    expiresAt: '2026-08-10',
    amount: 180_000,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'res-a2',
    projectName: 'Çankaya Terraces',
    unit: 'A-302',
    status: 'held',
    reservedAt: '2026-07-01',
    expiresAt: '2026-07-31',
    amount: 95_000,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
];

export const reservationsB: Reservation[] = [
  {
    id: 'res-b1',
    projectName: 'Bosphorus Tower (CONFIDENTIAL B)',
    unit: 'PH-01',
    status: 'confirmed',
    reservedAt: '2026-04-01',
    expiresAt: '2026-12-01',
    amount: 2_400_000,
    currency: 'TRY',
    investorId: INVESTOR_B_ID,
  },
];

export const contractsA: Contract[] = [
  {
    id: 'ctr-a1',
    title: 'Nişantaşı — Partnership Agreement',
    projectName: 'Nişantaşı Residence',
    status: 'active',
    signedAt: '2022-03-20',
    value: 2_500_000,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'ctr-a2',
    title: 'Caddebostan — Subscription Side Letter',
    projectName: 'Caddebostan Gardens',
    status: 'pending_signature',
    signedAt: null,
    value: 1_800_000,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
];

export const contractsB: Contract[] = [
  {
    id: 'ctr-b1',
    title: 'Bosphorus — Master LP Agreement (CONFIDENTIAL B)',
    projectName: 'Bosphorus Tower (CONFIDENTIAL B)',
    status: 'active',
    signedAt: '2021-09-01',
    value: 12_000_000,
    currency: 'TRY',
    investorId: INVESTOR_B_ID,
  },
];

export const paymentsA: Payment[] = [
  {
    id: 'pay-a1',
    label: 'Capital call #3',
    projectName: 'Caddebostan Gardens',
    dueDate: '2026-07-25',
    paidAt: null,
    amount: 270_000,
    currency: 'TRY',
    status: 'due',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'pay-a2',
    label: 'Capital call #2',
    projectName: 'Caddebostan Gardens',
    dueDate: '2026-04-15',
    paidAt: '2026-04-12',
    amount: 360_000,
    currency: 'TRY',
    status: 'paid',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'pay-a3',
    label: 'Reservation deposit',
    projectName: 'Çankaya Terraces',
    dueDate: '2026-07-05',
    paidAt: '2026-07-04',
    amount: 95_000,
    currency: 'TRY',
    status: 'paid',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'pay-a4',
    label: 'Capital call #4 (scheduled)',
    projectName: 'Caddebostan Gardens',
    dueDate: '2026-10-01',
    paidAt: null,
    amount: 270_000,
    currency: 'TRY',
    status: 'scheduled',
    investorId: INVESTOR_A_ID,
  },
];

export const paymentsB: Payment[] = [
  {
    id: 'pay-b1',
    label: 'Confidential capital call B',
    projectName: 'Bosphorus Tower (CONFIDENTIAL B)',
    dueDate: '2026-08-01',
    paidAt: null,
    amount: 1_500_000,
    currency: 'TRY',
    status: 'scheduled',
    investorId: INVESTOR_B_ID,
  },
];

export const rentalA: RentalIncomeRow[] = [
  {
    id: 'rent-a1',
    projectName: 'Nişantaşı Residence',
    period: '2026-06',
    gross: 52_400,
    net: 46_800,
    occupancy: 96,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'rent-a2',
    projectName: 'Nişantaşı Residence',
    period: '2026-05',
    gross: 51_100,
    net: 45_200,
    occupancy: 94,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'rent-a3',
    projectName: 'Nişantaşı Residence',
    period: '2026-04',
    gross: 50_200,
    net: 44_000,
    occupancy: 93,
    currency: 'TRY',
    investorId: INVESTOR_A_ID,
  },
];

export const documentsA: PortalDocument[] = [
  {
    id: 'doc-a1',
    title: 'Partnership Agreement — Nişantaşı',
    category: 'contracts',
    projectName: 'Nişantaşı Residence',
    version: 'v1.2',
    uploadedAt: '2022-03-20',
    sizeLabel: '1.4 MB',
    mime: 'application/pdf',
    investorId: INVESTOR_A_ID,
    canDownload: true,
    canPreview: true,
    classification: 'DEMO',
  },
  {
    id: 'doc-a2',
    title: 'Q2 2026 Distribution Statement',
    category: 'statements',
    projectName: 'Nişantaşı Residence',
    version: 'v1.0',
    uploadedAt: '2026-07-05',
    sizeLabel: '420 KB',
    mime: 'application/pdf',
    investorId: INVESTOR_A_ID,
    canDownload: true,
    canPreview: true,
    classification: 'DEMO',
  },
  {
    id: 'doc-a3',
    title: 'Construction Progress Report — June',
    category: 'project',
    projectName: 'Caddebostan Gardens',
    version: 'v3',
    uploadedAt: '2026-07-02',
    sizeLabel: '8.1 MB',
    mime: 'application/pdf',
    investorId: INVESTOR_A_ID,
    canDownload: true,
    canPreview: true,
    classification: 'DEMO',
  },
  {
    id: 'doc-a4',
    title: 'KYC Pack — Ayşe Yılmaz',
    category: 'kyc',
    projectName: null,
    version: 'v2',
    uploadedAt: '2026-01-12',
    sizeLabel: '2.2 MB',
    mime: 'application/pdf',
    investorId: INVESTOR_A_ID,
    canDownload: true,
    canPreview: false,
    classification: 'DEMO',
  },
  {
    id: 'doc-a5',
    title: 'Tax Certificate 2025',
    category: 'tax',
    projectName: 'Nişantaşı Residence',
    version: 'v1',
    uploadedAt: '2026-03-01',
    sizeLabel: '310 KB',
    mime: 'application/pdf',
    investorId: INVESTOR_A_ID,
    canDownload: true,
    canPreview: true,
    classification: 'DEMO',
  },
  {
    id: 'doc-a6',
    title: 'Reservation Confirmation — A-302',
    category: 'legal',
    projectName: 'Çankaya Terraces',
    version: 'v1',
    uploadedAt: '2026-07-01',
    sizeLabel: '180 KB',
    mime: 'application/pdf',
    investorId: INVESTOR_A_ID,
    canDownload: true,
    canPreview: true,
    classification: 'DEMO',
  },
];

export const documentsB: PortalDocument[] = [
  {
    id: 'doc-b1',
    title: 'Bosphorus LP Agreement (CONFIDENTIAL B)',
    category: 'contracts',
    projectName: 'Bosphorus Tower (CONFIDENTIAL B)',
    version: 'v4',
    uploadedAt: '2021-09-01',
    sizeLabel: '3.8 MB',
    mime: 'application/pdf',
    investorId: INVESTOR_B_ID,
    canDownload: true,
    canPreview: true,
    classification: 'DEMO',
  },
];

export const reportPresets: ReportPreset[] = [
  {
    id: 'rpt-portfolio',
    titleKey: 'reports.portfolioSummary',
    descriptionKey: 'reports.portfolioSummaryDesc',
    frequency: 'monthly',
    classification: 'DEMO',
  },
  {
    id: 'rpt-cash',
    titleKey: 'reports.cashActivity',
    descriptionKey: 'reports.cashActivityDesc',
    frequency: 'quarterly',
    classification: 'DEMO',
  },
  {
    id: 'rpt-tax',
    titleKey: 'reports.taxPack',
    descriptionKey: 'reports.taxPackDesc',
    frequency: 'annual',
    classification: 'DEMO',
  },
  {
    id: 'rpt-construction',
    titleKey: 'reports.construction',
    descriptionKey: 'reports.constructionDesc',
    frequency: 'on_demand',
    classification: 'DEMO',
  },
];

export const messagesA: PortalMessage[] = [
  {
    id: 'msg-a1',
    threadId: 'thr-a1',
    from: 'Investor Relations',
    subject: 'Capital call #3 reminder',
    preview: 'Your Caddebostan capital call is due 25 July…',
    body: 'Dear Ayşe,\n\nThis is a courtesy reminder that capital call #3 for Caddebostan Gardens (TRY 270,000) is due on 25 July 2026.\n\nWire instructions are attached in Documents.\n\n— Investor Relations',
    at: '2026-07-18T09:12:00+03:00',
    read: false,
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'msg-a2',
    threadId: 'thr-a2',
    from: 'Project Office',
    subject: 'Nişantaşı Q2 update available',
    preview: 'Occupancy 96% — statement published…',
    body: 'The Q2 distribution statement for Nişantaşı Residence is now available under Documents.',
    at: '2026-07-05T14:30:00+03:00',
    read: true,
    investorId: INVESTOR_A_ID,
  },
];

export const messagesB: PortalMessage[] = [
  {
    id: 'msg-b1',
    threadId: 'thr-b1',
    from: 'IR Desk',
    subject: 'CONFIDENTIAL B board pack',
    preview: 'Bosphorus board materials…',
    body: 'Investor B only content.',
    at: '2026-07-10T11:00:00+03:00',
    read: false,
    investorId: INVESTOR_B_ID,
  },
];

export const tasksA: PortalTask[] = [
  {
    id: 'task-a1',
    title: 'Sign Caddebostan side letter',
    dueDate: '2026-07-28',
    status: 'open',
    priority: 'high',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'task-a2',
    title: 'Upload updated ID scan',
    dueDate: '2026-08-05',
    status: 'open',
    priority: 'medium',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'task-a3',
    title: 'Confirm wire for capital call #2',
    dueDate: '2026-04-12',
    status: 'done',
    priority: 'high',
    investorId: INVESTOR_A_ID,
  },
];

export const meetingsA: PortalMeeting[] = [
  {
    id: 'mtg-a1',
    title: 'Quarterly portfolio review',
    at: '2026-07-24T15:00:00+03:00',
    location: 'Video · Teams',
    withWhom: 'IR — Emre Kaya',
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'mtg-a2',
    title: 'Caddebostan site walkthrough',
    at: '2026-08-08T10:30:00+03:00',
    location: 'Caddebostan site office',
    withWhom: 'Project Office',
    investorId: INVESTOR_A_ID,
  },
];

export const notificationsA: PortalNotification[] = [
  {
    id: 'ntf-a1',
    type: 'payment',
    title: 'Payment due',
    body: 'Capital call #3 · Caddebostan · 25 Jul',
    at: '2026-07-18T09:00:00+03:00',
    read: false,
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'ntf-a2',
    type: 'document',
    title: 'New statement',
    body: 'Q2 2026 distribution statement published',
    at: '2026-07-05T14:00:00+03:00',
    read: false,
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'ntf-a3',
    type: 'project',
    title: 'Construction update',
    body: 'Caddebostan MEP tender awarded',
    at: '2026-06-20T16:00:00+03:00',
    read: true,
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'ntf-a4',
    type: 'security',
    title: 'New device sign-in',
    body: 'Chrome on Windows · İstanbul',
    at: '2026-07-19T20:12:00+03:00',
    read: true,
    investorId: INVESTOR_A_ID,
  },
  {
    id: 'ntf-a5',
    type: 'message',
    title: 'Unread message',
    body: 'Capital call #3 reminder from IR',
    at: '2026-07-18T09:12:00+03:00',
    read: false,
    investorId: INVESTOR_A_ID,
  },
];

export const devicesA: DeviceSession[] = [
  {
    id: 'dev-1',
    device: 'Chrome · Windows',
    location: 'İstanbul, TR',
    lastActive: '2026-07-20T12:00:00+03:00',
    current: true,
  },
  {
    id: 'dev-2',
    device: 'Safari · iPhone',
    location: 'İstanbul, TR',
    lastActive: '2026-07-18T21:40:00+03:00',
    current: false,
  },
];

export const navValueSeries = [
  { label: 'Oca', value: 4_200_000 },
  { label: 'Şub', value: 4_280_000 },
  { label: 'Mar', value: 4_350_000 },
  { label: 'Nis', value: 4_480_000 },
  { label: 'May', value: 4_620_000 },
  { label: 'Haz', value: 4_900_000 },
  { label: 'Tem', value: 5_245_000 },
];

export const paymentBarSeries = [
  { label: 'Ödendi', value: 455_000 },
  { label: 'Vadesi gelen', value: 270_000 },
  { label: 'Planlı', value: 270_000 },
];
