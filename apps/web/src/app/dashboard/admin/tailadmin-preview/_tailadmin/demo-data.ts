/**
 * Demo-only fixtures for the TailAdmin compatibility spike.
 * Never wire these to production APIs or mutations.
 */

export const KPI_METRICS = [
  { id: 'revenue', label: 'Net revenue (YTD)', value: '₺186.4M', delta: '+8.2%', up: true },
  { id: 'pipeline', label: 'Sales pipeline', value: '₺42.8M', delta: '+12.4%', up: true },
  { id: 'equity', label: 'Equity committed', value: '₺98.1M', delta: '+3.1%', up: true },
  { id: 'occupancy', label: 'Units reserved', value: '312', delta: '−2.4%', up: false },
] as const;

export const FINANCE_SERIES = {
  months: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  collections: [12.4, 13.1, 14.8, 13.9, 15.2, 16.8, 17.1, 18.4, 19.2, 20.1, 21.4, 22.8],
  disbursements: [8.2, 9.1, 9.8, 10.4, 11.2, 12.0, 12.6, 13.1, 13.8, 14.2, 14.9, 15.5],
} as const;

export const PROJECTS = [
  { name: 'Marina Residences', phase: 'Construction', progress: 72, budget: '₺48.2M', health: 'on_track' },
  { name: 'Skyline Tower', phase: 'Sales', progress: 58, budget: '₺62.0M', health: 'watch' },
  { name: 'Green Park Villas', phase: 'Foundation', progress: 34, budget: '₺28.5M', health: 'on_track' },
  { name: 'Central Hub Mixed', phase: 'Planning', progress: 18, budget: '₺91.4M', health: 'risk' },
] as const;

export const PIPELINE_STAGES = [
  { stage: 'Lead', count: 48, value: '₺6.2M' },
  { stage: 'Qualified', count: 31, value: '₺9.8M' },
  { stage: 'Proposal', count: 19, value: '₺12.4M' },
  { stage: 'Negotiation', count: 11, value: '₺8.1M' },
  { stage: 'Won', count: 7, value: '₺6.3M' },
] as const;

export const INVESTORS = [
  { name: 'Anadolu Capital', commitment: '₺24.0M', status: 'Active', next: 'Q3 call' },
  { name: 'Bosphorus Partners', commitment: '₺18.5M', status: 'Due diligence', next: 'Docs review' },
  { name: 'Ege Family Office', commitment: '₺12.0M', status: 'Active', next: 'Site visit' },
  { name: 'Marmara Holdings', commitment: '₺9.2M', status: 'Watch', next: 'Follow-up' },
] as const;

export const TASKS = [
  { title: 'Approve Marina draw #14', owner: 'CFO', due: 'Today', priority: 'high' },
  { title: 'Investor pack — Skyline', owner: 'IR', due: 'Tomorrow', priority: 'high' },
  { title: 'Campaign budget reforecast', owner: 'MKT', due: 'Wed', priority: 'med' },
  { title: 'CRM sync — sales handoff', owner: 'Sales', due: 'Thu', priority: 'med' },
  { title: 'Board KPI snapshot', owner: 'Exec', due: 'Fri', priority: 'low' },
] as const;

export const CALENDAR_DAYS = [
  { day: 14, label: 'Board prep', tone: 'brand' },
  { day: 15, label: 'Site visit', tone: 'success' },
  { day: 18, label: 'Investor call', tone: 'warn' },
  { day: 22, label: 'Launch review', tone: 'brand' },
] as const;

export const MARKETING = [
  { campaign: 'Marina Early Bird', channel: 'Meta + Search', spend: '₺420K', leads: 186, cpl: '₺2.3K' },
  { campaign: 'Skyline Soft Launch', channel: 'Email + WhatsApp', spend: '₺180K', leads: 94, cpl: '₺1.9K' },
  { campaign: 'Brand Always-On', channel: 'Display', spend: '₺95K', leads: 41, cpl: '₺2.3K' },
] as const;

export const AI_RECS = [
  {
    title: 'Accelerate Marina Phase 2 sales',
    detail: 'Pipeline velocity +18% vs last month; prioritize 3 negotiation deals before draw #15.',
  },
  {
    title: 'Investor concentration risk',
    detail: 'Top 2 LPs = 43% of commitments. Schedule diversification outreach this week.',
  },
  {
    title: 'Marketing CPL opportunity',
    detail: 'WhatsApp nurtures convert 1.4× Meta. Shift 12% budget for Skyline Soft Launch.',
  },
] as const;
