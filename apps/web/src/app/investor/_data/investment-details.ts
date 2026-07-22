import { getAllInvestments, getInvestmentById } from './investments';
import type { PortfolioInvestment, ProjectStage } from './investment-types';
import type {
  CapitalStructure,
  ChartDataPoint,
  DistributionRecord,
  InvestmentDetail,
  InvestmentDocument,
  InvestmentFinancials,
  InvestmentOverview,
  InvestmentRisk,
  InvestmentSummaryPanel,
  InvestmentUpdate,
  InvestorPosition,
  ProjectContact,
  ProjectMilestone,
  ProjectProgress,
  PropertySummary,
} from './investment-detail-types';

interface ProjectDetailConfig {
  thesis: string;
  strategy: string;
  businessPlan: string;
  holdPeriod: string;
  assetClass: string;
  propertyType: string;
  neighborhood: string;
  submarket: string;
  unitCount: number;
  buildingSizeSqFt: number;
  amenities: string[];
  galleryImages: { url: string; alt: string }[];
  totalBudget: number;
}

const PROJECT_CONFIGS: Record<string, ProjectDetailConfig> = {
  'pi-001': {
    thesis:
      'Prime downtown DC office-to-residential conversion capturing premium rents in a supply-constrained submarket with strong employment growth.',
    strategy: 'Value-add development with phased unit delivery and pre-leasing to institutional tenants.',
    businessPlan:
      'Complete structural retrofit, deliver 142 luxury units over 18 months, achieve 90% occupancy within 12 months of certificate of occupancy.',
    holdPeriod: '5–7 years',
    assetClass: 'Multifamily',
    propertyType: 'High-Rise Residential',
    neighborhood: 'Downtown / Penn Quarter',
    submarket: 'Central Business District',
    unitCount: 142,
    buildingSizeSqFt: 185_000,
    amenities: ['Rooftop terrace', 'Co-working lounge', 'Fitness center', 'Concierge', 'EV charging'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop', alt: 'The Temple exterior rendering' },
      { url: 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop', alt: 'Lobby design concept' },
      { url: 'https://images.unsplash.com/photo-1502672260266-1c1ef2cd936?w=600&h=400&fit=crop', alt: 'Model unit interior' },
    ],
    totalBudget: 42_000_000,
  },
  'pi-002': {
    thesis:
      'Stabilized multifamily asset in a high-demand urban corridor with consistent rental growth and below-market in-place rents.',
    strategy: 'Core-plus hold with light unit upgrades and amenity enhancements to drive NOI growth.',
    businessPlan:
      'Maintain 95%+ occupancy, implement $2.1M renovation program across common areas and select units, refinance at stabilization.',
    holdPeriod: '4–6 years',
    assetClass: 'Multifamily',
    propertyType: 'Mid-Rise Apartment',
    neighborhood: 'U Street Corridor',
    submarket: 'Northwest DC',
    unitCount: 86,
    buildingSizeSqFt: 72_000,
    amenities: ['Courtyard garden', 'Package lockers', 'Pet spa', 'Bike storage'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop', alt: 'Uniloft building facade' },
      { url: 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?w=600&h=400&fit=crop', alt: 'Unit living space' },
      { url: 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?w=600&h=400&fit=crop', alt: 'Courtyard amenity' },
    ],
    totalBudget: 18_500_000,
  },
  'pi-003': {
    thesis:
      'Transit-oriented mixed-use development on H Street NE benefiting from neighborhood revitalization and retail demand.',
    strategy: 'Ground-floor retail activation with residential above; lease-up focused on young professionals.',
    businessPlan:
      'Complete final punch-list items, achieve 85% residential occupancy, stabilize retail tenancy at 70%+ by Q4.',
    holdPeriod: '5 years',
    assetClass: 'Mixed-Use',
    propertyType: 'Retail + Residential',
    neighborhood: 'H Street NE',
    submarket: 'Capitol Hill East',
    unitCount: 48,
    buildingSizeSqFt: 55_000,
    amenities: ['Ground-floor retail', 'Rooftop deck', 'In-unit laundry', 'Secure entry'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=600&h=400&fit=crop', alt: '309 H Street building' },
      { url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&h=400&fit=crop', alt: 'Retail storefront' },
      { url: 'https://images.unsplash.com/photo-1502672260266-1c1ef2cd936?w=600&h=400&fit=crop', alt: 'Residential unit' },
    ],
    totalBudget: 14_200_000,
  },
  'pi-004': {
    thesis:
      'Institutional-grade commercial campus with long-term anchor tenants and below-market lease rollovers creating upside.',
    strategy: 'Core income strategy with tenant retention focus and strategic capital improvements.',
    businessPlan:
      'Renew anchor leases, complete lobby modernization, explore adjacent parcel acquisition for expansion.',
    holdPeriod: '7–10 years',
    assetClass: 'Commercial',
    propertyType: 'Office Campus',
    neighborhood: 'Van Ness / Forest Hills',
    submarket: 'Upper Northwest DC',
    unitCount: 0,
    buildingSizeSqFt: 320_000,
    amenities: ['Conference center', 'Cafeteria', 'Surface parking', 'Fitness facility', 'Shuttle service'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1497366216548-37526070297c?w=600&h=400&fit=crop', alt: 'The Campus aerial view' },
      { url: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop', alt: 'Office tower' },
      { url: 'https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=600&h=400&fit=crop', alt: 'Campus lobby' },
    ],
    totalBudget: 65_000_000,
  },
  'pi-005': {
    thesis:
      'Affordable rental portfolio in the Bronx with stable cash flow, Section 8 exposure, and tax abatement benefits.',
    strategy: 'Buy-and-hold with operational efficiency improvements and deferred maintenance reduction.',
    businessPlan:
      'Maintain occupancy above 98%, reduce operating expenses 8% through energy upgrades, distribute quarterly.',
    holdPeriod: 'Indefinite hold',
    assetClass: 'Multifamily',
    propertyType: 'Garden-Style Rental',
    neighborhood: 'Morris Park',
    submarket: 'East Bronx',
    unitCount: 24,
    buildingSizeSqFt: 18_500,
    amenities: ['On-site laundry', 'Playground', 'Off-street parking', 'Superintendent unit'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=600&h=400&fit=crop', alt: 'Nelson Avenue building' },
      { url: 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=600&h=400&fit=crop', alt: 'Residential exterior' },
      { url: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&h=400&fit=crop', alt: 'Neighborhood context' },
    ],
    totalBudget: 4_800_000,
  },
  'pi-006': {
    thesis:
      'Boutique condominium development targeting owner-occupants in a gentrifying corridor with limited new supply.',
    strategy: 'Pre-sales driven development with phased closings and premium finish packages.',
    businessPlan:
      'Complete foundation and structural work, launch sales gallery Q3, achieve 40% pre-sales before vertical construction.',
    holdPeriod: '3–4 years (development)',
    assetClass: 'Residential',
    propertyType: 'Condominium',
    neighborhood: 'Atlas District',
    submarket: 'H Street NE',
    unitCount: 36,
    buildingSizeSqFt: 42_000,
    amenities: ['Private balconies', 'Designer kitchens', 'Smart home package', 'Storage units'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=600&h=400&fit=crop', alt: 'H Place rendering' },
      { url: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=600&h=400&fit=crop', alt: 'Sales gallery concept' },
      { url: 'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=600&h=400&fit=crop', alt: 'Model kitchen' },
    ],
    totalBudget: 22_000_000,
  },
  'pi-007': {
    thesis:
      'Value-add flip strategy targeting undervalued Riverside properties with forced appreciation through renovation.',
    strategy: 'Acquire, renovate, and sell within 18-month hold periods across a diversified portfolio.',
    businessPlan:
      'Complete final disposition of Fund III assets, distribute proceeds to LPs, launch Fund IV fundraising.',
    holdPeriod: '18 months per asset',
    assetClass: 'Single-Family',
    propertyType: 'Renovation Flip',
    neighborhood: 'Riverside',
    submarket: 'Baltimore Inner Harbor',
    unitCount: 1,
    buildingSizeSqFt: 2_400,
    amenities: ['Renovated kitchen', 'Updated HVAC', 'New roof', 'Landscaping'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&h=400&fit=crop', alt: 'Riverside property before' },
      { url: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=600&h=400&fit=crop', alt: 'Renovated exterior' },
      { url: 'https://images.unsplash.com/photo-1600566753086-00f18fb576b9?w=600&h=400&fit=crop', alt: 'Updated interior' },
    ],
    totalBudget: 890_000,
  },
  'pi-008': {
    thesis:
      'Opportunity Zone multifamily development with tax-advantaged returns and strong demographic tailwinds.',
    strategy: 'Ground-up development with QOF structure, targeting workforce housing rents.',
    businessPlan:
      'Complete land acquisition, finalize entitlements, break ground Q1 2026, deliver 120 units by 2028.',
    holdPeriod: '10+ years (OZ compliance)',
    assetClass: 'Multifamily',
    propertyType: 'Garden-Style Apartment',
    neighborhood: 'Capitol Heights',
    submarket: 'East of the River',
    unitCount: 120,
    buildingSizeSqFt: 108_000,
    amenities: ['Community center', 'Playground', 'Surface parking', 'On-site management'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=600&h=400&fit=crop', alt: 'Capitol Heights site plan' },
      { url: 'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=600&h=400&fit=crop', alt: 'Architectural rendering' },
      { url: 'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=600&h=400&fit=crop', alt: 'Neighborhood context' },
    ],
    totalBudget: 28_000_000,
  },
  'pi-009': {
    thesis:
      'Historic Georgetown rowhouse conversion preserving architectural character while delivering luxury rental product.',
    strategy: 'Adaptive reuse with premium finishes targeting diplomatic and executive tenant profile.',
    businessPlan:
      'Complete structural reinforcement, deliver 8 luxury units, achieve stabilization by Q2 2026.',
    holdPeriod: '6–8 years',
    assetClass: 'Multifamily',
    propertyType: 'Historic Rowhouse',
    neighborhood: 'Georgetown',
    submarket: 'West End DC',
    unitCount: 8,
    buildingSizeSqFt: 12_500,
    amenities: ['Original brick facade', 'Private entrances', 'Wine cellar', 'Roof deck'],
    galleryImages: [
      { url: 'https://images.unsplash.com/photo-1605276374101-de4c0a5efe53?w=600&h=400&fit=crop', alt: 'Georgetown Row exterior' },
      { url: 'https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?w=600&h=400&fit=crop', alt: 'Historic facade detail' },
      { url: 'https://images.unsplash.com/photo-1600566753086-00f18fb576b9?w=600&h=400&fit=crop', alt: 'Luxury interior' },
    ],
    totalBudget: 8_500_000,
  },
};

const DEFAULT_CONFIG = PROJECT_CONFIGS['pi-001']!;

function getProjectConfig(id: string): ProjectDetailConfig {
  return PROJECT_CONFIGS[id] ?? DEFAULT_CONFIG;
}

function generateChartSeries(
  invested: number,
  current: number,
  quarters: number,
  cashFlowBase = 0,
): {
  investmentGrowth: ChartDataPoint[];
  equityGrowth: ChartDataPoint[];
  cashFlowHistory: ChartDataPoint[];
  roiProgression: ChartDataPoint[];
} {
  const labels = ['Q1', 'Q2', 'Q3', 'Q4', 'Q1', 'Q2', 'Q3', 'Q4'].slice(0, quarters);
  const investmentGrowth: ChartDataPoint[] = [];
  const equityGrowth: ChartDataPoint[] = [];
  const cashFlowHistory: ChartDataPoint[] = [];
  const roiProgression: ChartDataPoint[] = [];

  for (let i = 0; i < quarters; i++) {
    const progress = (i + 1) / quarters;
    const value = invested + (current - invested) * progress;
    const equity = value - invested;
    const roi = invested > 0 ? ((value - invested) / invested) * 100 : 0;
    investmentGrowth.push({ label: labels[i] ?? `P${i + 1}`, value: Math.round(value) });
    equityGrowth.push({ label: labels[i] ?? `P${i + 1}`, value: Math.round(equity) });
    cashFlowHistory.push({
      label: labels[i] ?? `P${i + 1}`,
      value: Math.round(cashFlowBase * progress * (0.85 + (i % 4) * 0.05)),
    });
    roiProgression.push({ label: labels[i] ?? `P${i + 1}`, value: Math.round(roi * 10) / 10 });
  }

  return { investmentGrowth, equityGrowth, cashFlowHistory, roiProgression };
}

function generateMilestones(inv: PortfolioInvestment, config: ProjectDetailConfig): ProjectMilestone[] {
  const baseMilestones: Omit<ProjectMilestone, 'id'>[] = [
    { title: 'Site Acquisition', description: 'Closed on property acquisition and transferred title.', targetDate: '2020-01-15', completedDate: '2020-01-15', status: 'completed', phase: 'Acquisition' },
    { title: 'Entitlements & Permits', description: 'Secured all zoning approvals and building permits.', targetDate: '2020-09-30', completedDate: '2020-10-12', status: 'completed', phase: 'Pre-Development' },
    { title: 'Financing Close', description: 'Closed construction loan and equity raise.', targetDate: '2021-03-15', completedDate: '2021-03-15', status: 'completed', phase: 'Financing' },
    { title: 'Groundbreaking', description: 'Official construction commencement ceremony.', targetDate: '2021-06-01', completedDate: '2021-06-08', status: 'completed', phase: 'Construction' },
    { title: 'Foundation Complete', description: 'Structural foundation and underground work finished.', targetDate: '2022-02-28', completedDate: '2022-03-15', status: 'completed', phase: 'Construction' },
    { title: 'Topping Out', description: 'Final structural beam placed; building enclosed.', targetDate: '2023-08-30', status: inv.progressPercent >= 60 ? 'completed' : inv.progressPercent >= 40 ? 'in_progress' : 'upcoming', completedDate: inv.progressPercent >= 60 ? '2023-09-05' : undefined, phase: 'Construction' },
    { title: 'Certificate of Occupancy', description: 'Receive CO and begin lease-up or sales program.', targetDate: '2025-06-30', status: inv.progressPercent >= 90 ? 'completed' : inv.progressPercent >= 70 ? 'in_progress' : 'upcoming', phase: 'Delivery' },
    { title: 'Stabilization', description: `Achieve target occupancy across ${config.unitCount || 'all'} units.`, targetDate: inv.exitDate ?? '2026-12-31', status: inv.status === 'stabilized' ? 'completed' : inv.status === 'exited' ? 'completed' : inv.progressPercent >= 85 ? 'in_progress' : 'upcoming', phase: 'Operations' },
    { title: 'Disposition / Exit', description: 'Refinance or sell asset per business plan.', targetDate: inv.exitDate ?? '2027-06-30', status: inv.status === 'exited' ? 'completed' : 'upcoming', completedDate: inv.status === 'exited' ? inv.exitDate : undefined, phase: 'Exit' },
  ];

  if (inv.status === 'upcoming') {
    baseMilestones[3] = { ...baseMilestones[3]!, status: 'upcoming', completedDate: undefined };
    baseMilestones[4] = { ...baseMilestones[4]!, status: 'upcoming', completedDate: undefined };
    baseMilestones[5] = { ...baseMilestones[5]!, status: 'upcoming', completedDate: undefined };
  }

  if (inv.id === 'pi-003') {
    baseMilestones[6] = { ...baseMilestones[6]!, status: 'in_progress' };
    baseMilestones[7] = {
      ...baseMilestones[7]!,
      status: 'delayed',
      description: 'Lease-up pace below pro forma due to retail tenant delays.',
    };
  }

  return baseMilestones.map((m, i) => ({ ...m, id: `${inv.id}-ms-${i + 1}` }));
}

function generateUpdates(inv: PortfolioInvestment): InvestmentUpdate[] {
  const name = inv.projectName;
  return [
    { id: `${inv.id}-upd-1`, title: `Q2 2025 Investor Update — ${name}`, summary: 'Construction progress remains on schedule with 62% completion. Pre-leasing interest exceeds projections.', category: 'construction', date: '2025-06-15', isRead: true, author: 'Project Management Team' },
    { id: `${inv.id}-upd-2`, title: 'Capital Call Notice — Tranche 3', summary: 'Third capital call of $125,000 due by August 15, 2025. Funds allocated to interior finishes.', category: 'financial', date: '2025-06-01', isRead: false, author: 'Fund Administration' },
    { id: `${inv.id}-upd-3`, title: 'Market Report: DC Multifamily Q1 2025', summary: 'Submarket vacancy declined 40 bps. Rent growth of 3.2% YoY supports underwriting assumptions.', category: 'market', date: '2025-05-20', isRead: true, author: 'Research Team' },
    { id: `${inv.id}-upd-4`, title: 'Insurance Certificate Renewal', summary: 'Updated builder\'s risk and general liability policies effective through December 2025.', category: 'legal', date: '2025-05-01', isRead: true, author: 'Legal Counsel' },
    { id: `${inv.id}-upd-5`, title: 'Quarterly Distribution Announcement', summary: inv.distribution.nextDistributionDate ? `Next distribution scheduled for ${inv.distribution.nextDistributionDate}.` : 'Distribution schedule to be announced upon stabilization.', category: 'financial', date: '2025-04-15', isRead: false, author: 'Investor Relations' },
    { id: `${inv.id}-upd-6`, title: 'Site Visit Invitation — Investor Day', summary: 'Join us for an on-site tour and management presentation. RSVP required by July 1.', category: 'investor_relations', date: '2025-04-01', isRead: true, author: 'Investor Relations' },
    { id: `${inv.id}-upd-7`, title: 'Operational Update: Leasing Velocity', summary: 'Net absorption positive for third consecutive month. Average rent $2,850/unit.', category: 'operations', date: '2025-03-15', isRead: true, author: 'Asset Management' },
  ];
}

function generateDistributions(inv: PortfolioInvestment): DistributionRecord[] {
  const records: DistributionRecord[] = [];
  const total = inv.distribution.totalDistributed;

  if (total === 0) {
    records.push({
      id: `${inv.id}-dist-1`,
      date: inv.distribution.nextDistributionDate ?? '2026-01-15',
      type: 'preferred_return',
      amount: Math.round(inv.investedAmount * 0.08),
      status: 'scheduled',
      taxYear: 2026,
      paymentMethod: 'ACH',
      reference: 'DIST-SCHED-001',
      notes: 'Projected first distribution upon stabilization.',
    });
    return records;
  }

  const count = inv.status === 'exited' ? 6 : 4;
  const perPayment = Math.round(total / count);
  const dates = ['2024-11-20', '2024-06-30', '2024-03-31', '2023-12-31', '2023-06-30', '2023-03-31'];
  const types: DistributionRecord['type'][] = ['final', 'profit_share', 'preferred_return', 'cash', 'return_of_capital', 'cash'];

  for (let i = 0; i < count; i++) {
    records.push({
      id: `${inv.id}-dist-${i + 1}`,
      date: dates[i] ?? '2023-01-15',
      type: types[i] ?? 'cash',
      amount: i === 0 && inv.status === 'exited' ? total - perPayment * (count - 1) : perPayment,
      status: 'paid',
      taxYear: parseInt((dates[i] ?? '2023-01-15').slice(0, 4), 10),
      paymentMethod: i % 2 === 0 ? 'ACH' : 'Wire',
      reference: `DIST-${inv.id.toUpperCase()}-${String(i + 1).padStart(3, '0')}`,
    });
  }

  if (inv.distribution.nextDistributionDate) {
    records.unshift({
      id: `${inv.id}-dist-next`,
      date: inv.distribution.nextDistributionDate,
      type: 'cash',
      amount: Math.round(inv.performance.annualCashFlow / 4),
      status: 'scheduled',
      taxYear: 2025,
      paymentMethod: 'ACH',
      reference: 'DIST-SCHED-NEXT',
    });
  }

  return records;
}

function generateDocuments(inv: PortfolioInvestment): InvestmentDocument[] {
  return [
    { id: `${inv.id}-doc-1`, title: 'Subscription Agreement', category: 'subscription', date: inv.investmentDate, fileSize: '2.4 MB', format: 'PDF' },
    { id: `${inv.id}-doc-2`, title: 'Private Placement Memorandum', category: 'legal', date: inv.investmentDate, fileSize: '8.1 MB', format: 'PDF' },
    { id: `${inv.id}-doc-3`, title: 'K-1 Tax Schedule — 2024', category: 'tax', date: '2025-03-15', fileSize: '156 KB', format: 'PDF' },
    { id: `${inv.id}-doc-4`, title: 'Q1 2025 Financial Statement', category: 'financial', date: '2025-04-30', fileSize: '1.2 MB', format: 'PDF' },
    { id: `${inv.id}-doc-5`, title: 'Q2 2025 Investor Report', category: 'report', date: '2025-07-01', fileSize: '3.8 MB', format: 'PDF' },
    { id: `${inv.id}-doc-6`, title: 'Operating Agreement Amendment', category: 'legal', date: '2024-11-01', fileSize: '890 KB', format: 'PDF' },
    { id: `${inv.id}-doc-7`, title: 'Property Insurance Certificate', category: 'insurance', date: '2025-01-01', fileSize: '420 KB', format: 'PDF' },
    { id: `${inv.id}-doc-8`, title: 'Capital Account Statement — Q2 2025', category: 'financial', date: '2025-07-05', fileSize: '245 KB', format: 'PDF' },
  ];
}

function generateRisks(inv: PortfolioInvestment): InvestmentRisk[] {
  const risks: InvestmentRisk[] = [
    { id: `${inv.id}-risk-1`, title: 'Construction Cost Overrun', description: 'Material and labor costs may exceed budget due to supply chain volatility.', severity: inv.status === 'under_construction' ? 'medium' : 'low', status: inv.status === 'under_construction' ? 'monitoring' : 'mitigated', category: 'Construction', mitigationPlan: 'Fixed-price GMP contract with 5% contingency reserve.', lastReviewed: '2025-06-01' },
    { id: `${inv.id}-risk-2`, title: 'Interest Rate Exposure', description: 'Floating-rate construction loan subject to rate increases.', severity: 'medium', status: 'open', category: 'Financial', mitigationPlan: 'Rate cap purchased through Q4 2025; refinance planned at stabilization.', lastReviewed: '2025-05-15' },
    { id: `${inv.id}-risk-3`, title: 'Lease-Up Velocity', description: 'Market absorption may lag pro forma assumptions.', severity: inv.stage === 'lease_up' ? 'high' : 'low', status: inv.stage === 'lease_up' ? 'open' : 'mitigated', category: 'Market', mitigationPlan: 'Concession package approved; enhanced marketing budget allocated.', lastReviewed: '2025-06-10' },
    { id: `${inv.id}-risk-4`, title: 'Regulatory / Zoning', description: 'Potential changes to local zoning ordinances affecting density.', severity: 'low', status: 'closed', category: 'Legal', mitigationPlan: 'All entitlements secured and vested.', lastReviewed: '2024-12-01' },
  ];

  if (inv.riskLevel === 'high') {
    risks.push({
      id: `${inv.id}-risk-5`,
      title: 'Market Timing Risk',
      description: 'Exit timing dependent on favorable market conditions for disposition.',
      severity: 'high',
      status: 'monitoring',
      category: 'Market',
      mitigationPlan: 'Flexible hold period; multiple exit strategies under evaluation.',
      lastReviewed: '2025-06-01',
    });
  }

  return risks;
}

function generateContacts(inv: PortfolioInvestment): ProjectContact[] {
  return [
    { id: `${inv.id}-ct-1`, name: 'Sarah Chen', role: 'investor_relations', title: 'Director of Investor Relations', email: 'sarah.chen@investhome.com', phone: '+1 (202) 555-0101', availability: 'Mon–Fri, 9am–6pm ET' },
    { id: `${inv.id}-ct-2`, name: 'Marcus Williams', role: 'project_manager', title: 'Senior Project Manager', email: 'marcus.williams@investhome.com', phone: '+1 (202) 555-0102', availability: 'Mon–Fri, 8am–5pm ET' },
    { id: `${inv.id}-ct-3`, name: 'Elena Rodriguez', role: 'asset_manager', title: 'Asset Manager', email: 'elena.rodriguez@investhome.com', phone: '+1 (202) 555-0103', availability: 'Mon–Thu, 9am–5pm ET' },
    { id: `${inv.id}-ct-4`, name: 'David Park', role: 'legal', title: 'General Counsel', email: 'david.park@investhome.com', phone: '+1 (202) 555-0104', availability: 'By appointment' },
    { id: `${inv.id}-ct-5`, name: 'Jennifer Walsh', role: 'accounting', title: 'Fund Controller', email: 'jennifer.walsh@investhome.com', phone: '+1 (202) 555-0105', availability: 'Mon–Fri, 9am–5pm ET' },
  ];
}

function buildProgress(inv: PortfolioInvestment, config: ProjectDetailConfig): ProjectProgress {
  const budgetSpent = Math.round(config.totalBudget * (inv.progressPercent / 100));
  let timelineStatus: ProjectProgress['timelineStatus'] = 'on_track';
  if (inv.id === 'pi-003') timelineStatus = 'behind';
  if (inv.status === 'upcoming') timelineStatus = 'on_track';
  if (inv.progressPercent < 20 && inv.status === 'under_construction') timelineStatus = 'on_track';

  const stageProgress = (stage: ProjectStage): number => {
    const map: Record<ProjectStage, number> = {
      acquisition: 10,
      pre_construction: 25,
      construction: inv.progressPercent,
      lease_up: Math.min(inv.progressPercent + 10, 95),
      stabilized: 100,
      exit: 100,
    };
    return map[stage] ?? inv.progressPercent;
  };

  return {
    overallPercent: inv.progressPercent,
    currentPhase: inv.stage.replace('_', ' '),
    constructionPercent: inv.type === 'commercial' ? 100 : stageProgress('construction'),
    leasingPercent: inv.stage === 'lease_up' ? 72 : inv.status === 'stabilized' ? 100 : inv.stage === 'construction' ? 0 : 45,
    salesPercent: inv.type === 'condominium' ? inv.progressPercent * 0.6 : inv.type === 'flip' ? 100 : 0,
    budgetSpent,
    totalBudget: config.totalBudget,
    budgetSpentPercent: Math.round((budgetSpent / config.totalBudget) * 100),
    timelineStatus,
    estimatedCompletion: inv.exitDate ?? '2027-12-31',
    daysRemaining: inv.exitDate ? Math.max(0, Math.round((new Date(inv.exitDate).getTime() - Date.now()) / 86400000)) : 900,
  };
}

function buildCapitalStructure(inv: PortfolioInvestment, config: ProjectDetailConfig): CapitalStructure {
  const total = config.totalBudget;
  const seniorDebt = Math.round(total * 0.55);
  const mezzanineDebt = Math.round(total * 0.1);
  const preferredEquity = Math.round(total * 0.1);
  const commonEquity = total - seniorDebt - mezzanineDebt - preferredEquity;
  const investorEquity = Math.round(commonEquity * (inv.ownershipPercent / 100));

  return {
    totalCapitalization: total,
    seniorDebt,
    mezzanineDebt,
    preferredEquity,
    commonEquity,
    investorEquity,
    items: [
      { label: 'Senior Debt', amount: seniorDebt, percent: 55, color: '#4682b4' },
      { label: 'Mezzanine', amount: mezzanineDebt, percent: 10, color: '#708090' },
      { label: 'Preferred Equity', amount: preferredEquity, percent: 10, color: '#b8860b' },
      { label: 'Common Equity', amount: commonEquity, percent: 25, color: '#228b22' },
    ],
  };
}

function buildPosition(inv: PortfolioInvestment): InvestorPosition {
  const totalUnits = Math.round(100 / inv.ownershipPercent * 100) / 100;
  return {
    committedCapital: inv.investedAmount,
    calledCapital: inv.investedAmount,
    uncalledCapital: inv.status === 'upcoming' ? Math.round(inv.investedAmount * 0.4) : 0,
    capitalAccountBalance: inv.currentValue,
    ownershipUnits: Math.round(totalUnits * inv.ownershipPercent / 100),
    totalFundUnits: Math.round(totalUnits),
    preferredReturnRate: 8,
    profitSplitPercent: 70,
    votingRights: inv.ownershipPercent >= 2,
    capitalCallSchedule: inv.status === 'upcoming' ? 'Quarterly over 18 months' : 'Fully called',
    lastCapitalCallDate: inv.status !== 'upcoming' ? inv.investmentDate : undefined,
    nextCapitalCallDate: inv.status === 'upcoming' ? '2025-10-01' : undefined,
  };
}

function buildFinancials(inv: PortfolioInvestment): InvestmentFinancials {
  const quarters = inv.status === 'exited' ? 8 : 6;
  const charts = generateChartSeries(
    inv.investedAmount,
    inv.currentValue,
    quarters,
    inv.performance.annualCashFlow / 4,
  );
  const equity = inv.currentValue - inv.investedAmount;

  return {
    ...charts,
    netAssetValue: inv.currentValue,
    unrealizedGain: equity > 0 ? equity : 0,
    realizedGain: inv.status === 'exited' ? equity : 0,
    totalReturn: inv.performance.roi,
    cashOnCashReturn: inv.investedAmount > 0 ? (inv.performance.annualCashFlow / inv.investedAmount) * 100 : 0,
    debtServiceCoverage: 1.35,
    loanToValue: 55,
    capRate: 5.8,
    metrics: [
      { key: 'nav', label: 'Net Asset Value', value: `$${inv.currentValue.toLocaleString()}`, tooltip: 'Current estimated value of your investment position.' },
      { key: 'unrealized', label: 'Unrealized Gain', value: `$${Math.max(0, equity).toLocaleString()}`, tooltip: 'Paper gain based on latest valuation.' },
      { key: 'realized', label: 'Realized Gain', value: `$${(inv.status === 'exited' ? equity : 0).toLocaleString()}`, tooltip: 'Gains realized through distributions or exit.' },
      { key: 'total_return', label: 'Total Return', value: `${inv.performance.roi.toFixed(1)}%`, tooltip: 'Combined realized and unrealized returns.' },
      { key: 'cash_on_cash', label: 'Cash-on-Cash', value: `${((inv.performance.annualCashFlow / inv.investedAmount) * 100 || 0).toFixed(1)}%`, tooltip: 'Annual cash flow divided by invested capital.' },
      { key: 'dscr', label: 'DSCR', value: '1.35x', tooltip: 'Debt service coverage ratio at asset level.' },
      { key: 'ltv', label: 'Loan-to-Value', value: '55%', tooltip: 'Outstanding debt as percentage of asset value.' },
      { key: 'cap_rate', label: 'Cap Rate', value: '5.8%', tooltip: 'Net operating income divided by property value.' },
    ],
  };
}

function buildOverview(inv: PortfolioInvestment, config: ProjectDetailConfig): InvestmentOverview {
  return {
    thesis: config.thesis,
    strategy: config.strategy,
    businessPlan: config.businessPlan,
    holdPeriod: config.holdPeriod,
    assetClass: config.assetClass,
    propertyType: config.propertyType,
    acquisitionDate: inv.investmentDate,
    stabilizationDate: inv.status === 'stabilized' || inv.status === 'exited' ? '2024-06-30' : undefined,
    keyDates: [
      { label: 'Investment Date', date: inv.investmentDate },
      { label: 'Projected Exit', date: inv.exitDate ?? 'TBD' },
      { label: 'Next Distribution', date: inv.distribution.nextDistributionDate ?? 'TBD' },
      { label: 'Last Distribution', date: inv.distribution.lastDistributionDate ?? 'N/A' },
    ],
  };
}

function buildProperty(inv: PortfolioInvestment, config: ProjectDetailConfig): PropertySummary {
  return {
    description: `${config.propertyType} located in ${config.neighborhood}, ${inv.city}, ${inv.state}. ${config.thesis.slice(0, 120)}…`,
    neighborhood: config.neighborhood,
    submarket: config.submarket,
    yearBuilt: inv.type === 'flip' ? 1985 : undefined,
    yearRenovated: inv.type === 'flip' ? 2024 : undefined,
    unitCount: config.unitCount,
    buildingSizeSqFt: config.buildingSizeSqFt,
    lotSizeAcres: config.unitCount > 50 ? 1.8 : 0.25,
    parkingSpaces: config.unitCount > 0 ? Math.round(config.unitCount * 0.8) : 120,
    amenities: config.amenities,
    galleryImages: config.galleryImages,
  };
}

function buildSummaryPanel(inv: PortfolioInvestment): InvestmentSummaryPanel {
  const milestones = generateMilestones(inv, getProjectConfig(inv.id));
  const nextMs = milestones.find((m) => m.status === 'in_progress' || m.status === 'upcoming') ?? milestones[milestones.length - 1];

  return {
    nextMilestone: nextMs?.title ?? 'Stabilization',
    nextMilestoneDate: nextMs?.targetDate ?? inv.exitDate ?? '2026-12-31',
    irContactName: 'Sarah Chen',
    irContactEmail: 'sarah.chen@investhome.com',
    overallRiskLevel: inv.riskLevel,
  };
}

function buildDetailForInvestment(inv: PortfolioInvestment): InvestmentDetail {
  const config = getProjectConfig(inv.id);

  return {
    investment: inv,
    overview: buildOverview(inv, config),
    position: buildPosition(inv),
    financials: buildFinancials(inv),
    capitalStructure: buildCapitalStructure(inv, config),
    progress: buildProgress(inv, config),
    milestones: generateMilestones(inv, config),
    distributions: generateDistributions(inv),
    documents: generateDocuments(inv),
    updates: generateUpdates(inv),
    risks: generateRisks(inv),
    contacts: generateContacts(inv),
    property: buildProperty(inv, config),
    summaryPanel: buildSummaryPanel(inv),
  };
}

export function getInvestmentDetailById(id: string): InvestmentDetail | null {
  const investment = getInvestmentById(id);
  if (!investment) return null;
  return buildDetailForInvestment(investment);
}

export function getAllInvestmentDetails(): InvestmentDetail[] {
  return getAllInvestments().map(buildDetailForInvestment);
}
