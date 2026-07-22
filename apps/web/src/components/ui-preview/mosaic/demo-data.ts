/**
 * Demo-only fixtures for Mosaic Lite isolated UI evaluation.
 * Investhome domain names — never wired to production APIs.
 */

export type LeadStatus = 'New' | 'Qualified' | 'Meeting' | 'Proposal' | 'Negotiation' | 'Won' | 'Lost';
export type LeadSource = 'Meta Ads' | 'Google' | 'Referral' | 'Walk-in' | 'WhatsApp' | 'Website';

export const MOSAIC_KPIS = [
  { id: 'pipeline', label: 'Sales pipeline', value: '₺42.8M', delta: '+12.4%', up: true },
  { id: 'leads', label: 'Open leads', value: '186', delta: '+9.1%', up: true },
  { id: 'investors', label: 'Active investors', value: '64', delta: '+3.2%', up: true },
  { id: 'revenue', label: 'Collections (MTD)', value: '₺18.4M', delta: '−1.8%', up: false },
] as const;

export const PIPELINE_STAGES = [
  { stage: 'Lead', count: 48, value: '₺6.2M', color: '#8470ff' },
  { stage: 'Qualified', count: 31, value: '₺9.8M', color: '#67bfff' },
  { stage: 'Proposal', count: 19, value: '₺12.4M', color: '#3ec972' },
  { stage: 'Negotiation', count: 11, value: '₺8.1M', color: '#f7cd4c' },
  { stage: 'Won', count: 7, value: '₺6.3M', color: '#34bd68' },
] as const;

export const REVENUE_SERIES = [
  { label: 'Jan', value: 12.4 },
  { label: 'Feb', value: 13.1 },
  { label: 'Mar', value: 14.8 },
  { label: 'Apr', value: 13.9 },
  { label: 'May', value: 15.2 },
  { label: 'Jun', value: 16.8 },
  { label: 'Jul', value: 18.4 },
  { label: 'Aug', value: 17.1 },
  { label: 'Sep', value: 19.2 },
  { label: 'Oct', value: 20.1 },
  { label: 'Nov', value: 21.4 },
  { label: 'Dec', value: 22.8 },
] as const;

export const SALES_SERIES = [
  { label: 'Jan', value: 8.2 },
  { label: 'Feb', value: 9.1 },
  { label: 'Mar', value: 10.4 },
  { label: 'Apr', value: 11.2 },
  { label: 'May', value: 12.0 },
  { label: 'Jun', value: 13.1 },
  { label: 'Jul', value: 14.6 },
  { label: 'Aug', value: 13.8 },
  { label: 'Sep', value: 15.2 },
  { label: 'Oct', value: 16.0 },
  { label: 'Nov', value: 17.4 },
  { label: 'Dec', value: 18.9 },
] as const;

export const INVESTOR_FOLLOWUPS = [
  {
    id: 'inv-1',
    name: 'Anadolu Capital',
    contact: 'Selim Kaya',
    commitment: '₺24.0M',
    status: 'Active',
    next: 'Q3 portfolio call',
    due: 'Today',
    tone: 'violet' as const,
  },
  {
    id: 'inv-2',
    name: 'Bosphorus Partners',
    contact: 'Deniz Arslan',
    commitment: '₺18.5M',
    status: 'Due diligence',
    next: 'Docs review',
    due: 'Tomorrow',
    tone: 'sky' as const,
  },
  {
    id: 'inv-3',
    name: 'Ege Family Office',
    contact: 'Ayşe Demir',
    commitment: '₺12.0M',
    status: 'Active',
    next: 'Marina site visit',
    due: 'Thu',
    tone: 'green' as const,
  },
  {
    id: 'inv-4',
    name: 'Marmara Holdings',
    contact: 'Can Öztürk',
    commitment: '₺9.2M',
    status: 'Watch',
    next: 'Follow-up call',
    due: 'Fri',
    tone: 'yellow' as const,
  },
];

export const PROJECT_STATUS = [
  { name: 'Marina Residences', phase: 'Construction', progress: 72, health: 'on_track' as const, budget: '₺48.2M' },
  { name: 'Skyline Tower', phase: 'Sales', progress: 58, health: 'watch' as const, budget: '₺62.0M' },
  { name: 'Green Park Villas', phase: 'Foundation', progress: 34, health: 'on_track' as const, budget: '₺28.5M' },
  { name: 'Central Hub Mixed', phase: 'Planning', progress: 18, health: 'risk' as const, budget: '₺91.4M' },
];

const AVATAR_TONES = ['violet', 'sky', 'green', 'yellow', 'red', 'indigo'] as const;

export type AvatarTone = (typeof AVATAR_TONES)[number];

export function avatarTone(seed: string): AvatarTone {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) h = (h + seed.charCodeAt(i) * (i + 1)) % AVATAR_TONES.length;
  return AVATAR_TONES[h] ?? 'violet';
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('');
}

export const LEADS = [
  {
    id: 'lead-1',
    name: 'Elif Yılmaz',
    email: 'elif.yilmaz@email.com',
    phone: '+90 532 111 2233',
    source: 'Meta Ads' as LeadSource,
    salesperson: 'Ayşe Torun',
    project: 'Marina Residences',
    status: 'Negotiation' as LeadStatus,
    lastContact: '2026-07-20',
    nextAction: 'Send unit A-1204 offer',
    budget: '₺4.2M',
  },
  {
    id: 'lead-2',
    name: 'Mehmet Koç',
    email: 'mehmet.koc@email.com',
    phone: '+90 533 444 5566',
    source: 'Referral' as LeadSource,
    salesperson: 'Burak Şen',
    project: 'Skyline Tower',
    status: 'Qualified' as LeadStatus,
    lastContact: '2026-07-19',
    nextAction: 'Schedule showroom tour',
    budget: '₺6.8M',
  },
  {
    id: 'lead-3',
    name: 'Zeynep Arslan',
    email: 'zeynep.arslan@email.com',
    phone: '+90 534 777 8899',
    source: 'Google' as LeadSource,
    salesperson: 'Ayşe Torun',
    project: 'Green Park Villas',
    status: 'Meeting' as LeadStatus,
    lastContact: '2026-07-21',
    nextAction: 'Confirm Saturday visit',
    budget: '₺3.1M',
  },
  {
    id: 'lead-4',
    name: 'Can Öztürk',
    email: 'can.ozturk@email.com',
    phone: '+90 535 222 3344',
    source: 'WhatsApp' as LeadSource,
    salesperson: 'Deniz Kara',
    project: 'Marina Residences',
    status: 'Proposal' as LeadStatus,
    lastContact: '2026-07-18',
    nextAction: 'Follow up on payment plan',
    budget: '₺5.5M',
  },
  {
    id: 'lead-5',
    name: 'Selin Aydın',
    email: 'selin.aydin@email.com',
    phone: '+90 536 555 6677',
    source: 'Website' as LeadSource,
    salesperson: 'Burak Şen',
    project: 'Central Hub Mixed',
    status: 'New' as LeadStatus,
    lastContact: '2026-07-22',
    nextAction: 'First discovery call',
    budget: '₺8.0M',
  },
  {
    id: 'lead-6',
    name: 'Emre Demir',
    email: 'emre.demir@email.com',
    phone: '+90 537 888 9900',
    source: 'Walk-in' as LeadSource,
    salesperson: 'Deniz Kara',
    project: 'Skyline Tower',
    status: 'Won' as LeadStatus,
    lastContact: '2026-07-15',
    nextAction: 'Contract signing',
    budget: '₺7.2M',
  },
  {
    id: 'lead-7',
    name: 'Hatice Güneş',
    email: 'hatice.gunes@email.com',
    phone: '+90 538 101 2020',
    source: 'Meta Ads' as LeadSource,
    salesperson: 'Ayşe Torun',
    project: 'Green Park Villas',
    status: 'Lost' as LeadStatus,
    lastContact: '2026-07-10',
    nextAction: 'Nurture in 90 days',
    budget: '₺2.4M',
  },
  {
    id: 'lead-8',
    name: 'Baran Çelik',
    email: 'baran.celik@email.com',
    phone: '+90 539 303 4040',
    source: 'Referral' as LeadSource,
    salesperson: 'Burak Şen',
    project: 'Marina Residences',
    status: 'Qualified' as LeadStatus,
    lastContact: '2026-07-21',
    nextAction: 'Share floor plans',
    budget: '₺4.9M',
  },
  {
    id: 'lead-9',
    name: 'İrem Kılıç',
    email: 'irem.kilic@email.com',
    phone: '+90 530 505 6060',
    source: 'Google' as LeadSource,
    salesperson: 'Deniz Kara',
    project: 'Skyline Tower',
    status: 'Meeting' as LeadStatus,
    lastContact: '2026-07-20',
    nextAction: 'Investor intro lunch',
    budget: '₺11.0M',
  },
  {
    id: 'lead-10',
    name: 'Ozan Yurt',
    email: 'ozan.yurt@email.com',
    phone: '+90 531 707 8080',
    source: 'WhatsApp' as LeadSource,
    salesperson: 'Ayşe Torun',
    project: 'Central Hub Mixed',
    status: 'Proposal' as LeadStatus,
    lastContact: '2026-07-17',
    nextAction: 'Revise commercial offer',
    budget: '₺9.5M',
  },
];

export const RECENT_LEADS = LEADS.slice(0, 6);

export const ACTIVITY_FEED = [
  { id: 'a1', actor: 'Ayşe Torun', action: 'moved Elif Yılmaz to Negotiation', time: '12m ago', tone: 'violet' as const },
  { id: 'a2', actor: 'Burak Şen', action: 'booked showroom for Mehmet Koç', time: '38m ago', tone: 'sky' as const },
  { id: 'a3', actor: 'System', action: 'Marina draw #14 approved', time: '1h ago', tone: 'green' as const },
  { id: 'a4', actor: 'Deniz Kara', action: 'logged WhatsApp with Can Öztürk', time: '2h ago', tone: 'yellow' as const },
  { id: 'a5', actor: 'IR Desk', action: 'sent pack to Bosphorus Partners', time: '3h ago', tone: 'indigo' as const },
  { id: 'a6', actor: 'Finance', action: 'collections sync completed', time: '4h ago', tone: 'green' as const },
];

export const TASKS = [
  { id: 't1', title: 'Approve Marina draw #14 docs', owner: 'CFO', due: 'Today', priority: 'high' as const, done: false },
  { id: 't2', title: 'Investor pack — Skyline Tower', owner: 'IR', due: 'Tomorrow', priority: 'high' as const, done: false },
  { id: 't3', title: 'Call Elif Yılmaz — unit offer', owner: 'Sales', due: 'Today', priority: 'high' as const, done: false },
  { id: 't4', title: 'Campaign budget reforecast', owner: 'MKT', due: 'Wed', priority: 'med' as const, done: false },
  { id: 't5', title: 'CRM sync — sales handoff', owner: 'Sales', due: 'Thu', priority: 'med' as const, done: true },
  { id: 't6', title: 'Board KPI snapshot', owner: 'Exec', due: 'Fri', priority: 'low' as const, done: false },
];

export const DEMO_CUSTOMER = {
  id: 'cust-elif',
  name: 'Elif Yılmaz',
  email: 'elif.yilmaz@email.com',
  phone: '+90 532 111 2233',
  company: 'Yılmaz Holding',
  status: 'Negotiation' as LeadStatus,
  salesperson: 'Ayşe Torun',
  source: 'Meta Ads' as LeadSource,
  budget: '₺4.2M – ₺5.0M',
  lastComm: 'WhatsApp · Jul 20, 16:40',
  nextAction: 'Send unit A-1204 offer + payment plan',
  city: 'İstanbul',
  projects: [
    { name: 'Marina Residences', unit: 'A-1204 · 3+1', interest: 'Primary', stage: 'Negotiation' },
    { name: 'Skyline Tower', unit: 'B-802 · Ofis', interest: 'Secondary', stage: 'Qualified' },
  ],
  timeline: [
    { id: 'tl1', at: 'Jul 22, 09:10', title: 'Task created', detail: 'Send unit A-1204 offer', type: 'task' as const },
    { id: 'tl2', at: 'Jul 20, 16:40', title: 'WhatsApp', detail: 'Discussed payment plan options (30/40/30)', type: 'comm' as const },
    { id: 'tl3', at: 'Jul 18, 11:20', title: 'Site visit', detail: 'Marina showroom — preferred sea view', type: 'meeting' as const },
    { id: 'tl4', at: 'Jul 15, 14:05', title: 'Status change', detail: 'Qualified → Negotiation', type: 'status' as const },
    { id: 'tl5', at: 'Jul 12, 10:00', title: 'Lead created', detail: 'Meta Ads · Marina Early Bird', type: 'lead' as const },
  ],
  notes: [
    { id: 'n1', author: 'Ayşe Torun', at: 'Jul 20', text: 'Strong preference for sea-view 3+1. Husband joins decision. Open to 24-month plan.' },
    { id: 'n2', author: 'Burak Şen', at: 'Jul 18', text: 'Compared Skyline office as investment hedge — secondary interest only.' },
  ],
  docs: [
    { id: 'd1', name: 'ID scan — Elif Yılmaz.pdf', kind: 'Identity', size: '1.2 MB' },
    { id: 'd2', name: 'Marina A-1204 floor plan.pdf', kind: 'Unit', size: '840 KB' },
    { id: 'd3', name: 'Draft payment plan.xlsx', kind: 'Offer', size: '220 KB' },
  ],
  customerTasks: [
    { id: 'ct1', title: 'Send A-1204 offer PDF', due: 'Today', priority: 'high' as const },
    { id: 'ct2', title: 'Confirm husband availability', due: 'Tomorrow', priority: 'med' as const },
    { id: 'ct3', title: 'Prepare notary checklist', due: 'Fri', priority: 'low' as const },
  ],
};

export const LEAD_STATUSES: LeadStatus[] = [
  'New',
  'Qualified',
  'Meeting',
  'Proposal',
  'Negotiation',
  'Won',
  'Lost',
];

export const LEAD_SOURCES: LeadSource[] = [
  'Meta Ads',
  'Google',
  'Referral',
  'Walk-in',
  'WhatsApp',
  'Website',
];
