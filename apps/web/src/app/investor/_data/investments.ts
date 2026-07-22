import type {
  InvestmentSummaryMetrics,
  PortfolioInvestment,
} from './investment-types';

const portfolioInvestments: PortfolioInvestment[] = [
  {
    id: 'pi-001',
    slug: 'the-temple',
    imageUrl:
      'https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=800&h=500&fit=crop',
    projectName: 'The Temple',
    address: '1400 K Street NW',
    city: 'Washington',
    state: 'DC',
    entityName: 'Temple Holdings LLC',
    type: 'development',
    status: 'under_construction',
    stage: 'construction',
    investmentDate: '2023-04-12',
    investedAmount: 1_500_000,
    currentValue: 1_725_000,
    ownershipPercent: 4.2,
    performance: {
      roi: 15.0,
      irr: 13.8,
      annualCashFlow: 0,
      projectedRoi: 22.4,
    },
    distribution: {
      totalDistributed: 0,
      nextDistributionDate: '2026-01-15',
    },
    exitDate: '2028-06-30',
    riskLevel: 'moderate',
    progressPercent: 62,
    currency: 'USD',
  },
  {
    id: 'pi-002',
    slug: 'uniloft',
    imageUrl:
      'https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=800&h=500&fit=crop',
    projectName: 'Uniloft',
    address: '2200 14th Street NW',
    city: 'Washington',
    state: 'DC',
    entityName: 'Uniloft Residential Partners LP',
    type: 'multifamily',
    status: 'stabilized',
    stage: 'stabilized',
    investmentDate: '2021-08-20',
    investedAmount: 850_000,
    currentValue: 1_020_000,
    ownershipPercent: 2.8,
    performance: {
      roi: 19.8,
      irr: 14.2,
      annualCashFlow: 68_000,
      projectedRoi: 21.0,
    },
    distribution: {
      totalDistributed: 136_000,
      lastDistributionDate: '2025-06-30',
      nextDistributionDate: '2025-09-30',
    },
    exitDate: '2027-12-31',
    riskLevel: 'low',
    progressPercent: 100,
    currency: 'USD',
  },
  {
    id: 'pi-003',
    slug: '309-h-street',
    imageUrl:
      'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&h=500&fit=crop',
    projectName: '309 H Street',
    address: '309 H Street NE',
    city: 'Washington',
    state: 'DC',
    entityName: 'H Street Development Co.',
    type: 'development',
    status: 'active',
    stage: 'lease_up',
    investmentDate: '2022-11-05',
    investedAmount: 625_000,
    currentValue: 718_750,
    ownershipPercent: 3.5,
    performance: {
      roi: 12.4,
      irr: 10.6,
      annualCashFlow: 28_125,
      projectedRoi: 18.2,
    },
    distribution: {
      totalDistributed: 56_250,
      lastDistributionDate: '2025-03-31',
      nextDistributionDate: '2025-09-15',
    },
    exitDate: '2027-03-31',
    riskLevel: 'moderate',
    progressPercent: 88,
    currency: 'USD',
  },
  {
    id: 'pi-004',
    slug: 'the-campus',
    imageUrl:
      'https://images.unsplash.com/photo-1497366216548-37526070297c?w=800&h=500&fit=crop',
    projectName: 'The Campus',
    address: '4500 Connecticut Avenue NW',
    city: 'Washington',
    state: 'DC',
    entityName: 'Campus Mixed-Use Fund I',
    type: 'commercial',
    status: 'active',
    stage: 'stabilized',
    investmentDate: '2020-06-15',
    investedAmount: 2_000_000,
    currentValue: 2_480_000,
    ownershipPercent: 5.0,
    performance: {
      roi: 24.0,
      irr: 16.8,
      annualCashFlow: 120_000,
      projectedRoi: 26.5,
    },
    distribution: {
      totalDistributed: 480_000,
      lastDistributionDate: '2025-06-15',
      nextDistributionDate: '2025-12-15',
    },
    exitDate: '2026-06-15',
    riskLevel: 'low',
    progressPercent: 95,
    currency: 'USD',
  },
  {
    id: 'pi-005',
    slug: 'nelson-avenue',
    imageUrl:
      'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&h=500&fit=crop',
    projectName: 'Nelson Avenue',
    address: '1842 Nelson Avenue',
    city: 'Bronx',
    state: 'NY',
    entityName: 'Nelson Avenue Equity LLC',
    type: 'rental',
    status: 'stabilized',
    stage: 'stabilized',
    investmentDate: '2019-03-22',
    investedAmount: 400_000,
    currentValue: 532_000,
    ownershipPercent: 1.6,
    performance: {
      roi: 28.5,
      irr: 19.2,
      annualCashFlow: 32_000,
      projectedRoi: 30.0,
    },
    distribution: {
      totalDistributed: 160_000,
      lastDistributionDate: '2025-04-30',
      nextDistributionDate: '2025-10-31',
    },
    riskLevel: 'low',
    progressPercent: 100,
    currency: 'USD',
  },
  {
    id: 'pi-006',
    slug: 'h-place-residences',
    imageUrl:
      'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=800&h=500&fit=crop',
    projectName: 'H Place Residences',
    address: '1200 H Street NE',
    city: 'Washington',
    state: 'DC',
    entityName: 'H Place Condominium Fund',
    type: 'condominium',
    status: 'under_construction',
    stage: 'pre_construction',
    investmentDate: '2024-02-28',
    investedAmount: 750_000,
    currentValue: 750_000,
    ownershipPercent: 2.1,
    performance: {
      roi: 0,
      irr: 0,
      annualCashFlow: 0,
      projectedRoi: 19.6,
    },
    distribution: {
      totalDistributed: 0,
      nextDistributionDate: '2027-06-30',
    },
    exitDate: '2029-12-31',
    riskLevel: 'moderate',
    progressPercent: 18,
    currency: 'USD',
  },
  {
    id: 'pi-007',
    slug: 'riverside-flip-fund',
    imageUrl:
      'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800&h=500&fit=crop',
    projectName: 'Riverside Flip Fund III',
    address: '892 Riverside Drive',
    city: 'Baltimore',
    state: 'MD',
    entityName: 'Riverside Value Partners',
    type: 'flip',
    status: 'exited',
    stage: 'exit',
    investmentDate: '2018-09-10',
    investedAmount: 350_000,
    currentValue: 497_000,
    ownershipPercent: 8.0,
    performance: {
      roi: 42.0,
      irr: 28.4,
      annualCashFlow: 0,
      projectedRoi: 42.0,
    },
    distribution: {
      totalDistributed: 497_000,
      lastDistributionDate: '2024-11-20',
    },
    exitDate: '2024-11-20',
    riskLevel: 'high',
    progressPercent: 100,
    currency: 'USD',
  },
  {
    id: 'pi-008',
    slug: 'capitol-heights',
    imageUrl:
      'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800&h=500&fit=crop',
    projectName: 'Capitol Heights',
    address: '3300 East Capitol Street SE',
    city: 'Washington',
    state: 'DC',
    entityName: 'Capitol Heights Opportunity Zone Fund',
    type: 'multifamily',
    status: 'upcoming',
    stage: 'acquisition',
    investmentDate: '2025-09-01',
    investedAmount: 500_000,
    currentValue: 500_000,
    ownershipPercent: 1.9,
    performance: {
      roi: 0,
      irr: 0,
      annualCashFlow: 0,
      projectedRoi: 17.8,
    },
    distribution: {
      totalDistributed: 0,
      nextDistributionDate: '2027-03-31',
    },
    exitDate: '2030-09-01',
    riskLevel: 'moderate',
    progressPercent: 5,
    currency: 'USD',
  },
  {
    id: 'pi-009',
    slug: 'georgetown-row',
    imageUrl:
      'https://images.unsplash.com/photo-1605276374101-de4c0a5efe53?w=800&h=500&fit=crop',
    projectName: 'Georgetown Row',
    address: '1520 Wisconsin Avenue NW',
    city: 'Washington',
    state: 'DC',
    entityName: 'Georgetown Heritage REIT',
    type: 'rental',
    status: 'active',
    stage: 'construction',
    investmentDate: '2023-07-18',
    investedAmount: 975_000,
    currentValue: 1_053_000,
    ownershipPercent: 2.4,
    performance: {
      roi: 8.0,
      irr: 7.2,
      annualCashFlow: 12_188,
      projectedRoi: 16.4,
    },
    distribution: {
      totalDistributed: 24_375,
      lastDistributionDate: '2025-01-31',
      nextDistributionDate: '2025-07-31',
    },
    exitDate: '2028-07-18',
    riskLevel: 'moderate',
    progressPercent: 74,
    currency: 'USD',
  },
];

export function getAllInvestments(): PortfolioInvestment[] {
  return [...portfolioInvestments];
}

export function getInvestmentById(id: string): PortfolioInvestment | undefined {
  return portfolioInvestments.find((inv) => inv.id === id || inv.slug === id);
}

export function getInvestmentLocations(): string[] {
  const locations = new Set(
    portfolioInvestments.map((inv) => `${inv.city}, ${inv.state}`),
  );
  return Array.from(locations).sort();
}

export function computeInvestmentSummary(
  investments: PortfolioInvestment[],
): InvestmentSummaryMetrics {
  if (investments.length === 0) {
    return {
      totalInvestments: 0,
      totalInvested: 0,
      currentPortfolioValue: 0,
      estimatedEquity: 0,
      activeInvestments: 0,
      completedInvestments: 0,
      averageProjectedRoi: 0,
      averageIrr: 0,
      currency: 'USD',
    };
  }

  const totalInvested = investments.reduce((sum, inv) => sum + inv.investedAmount, 0);
  const currentPortfolioValue = investments.reduce((sum, inv) => sum + inv.currentValue, 0);
  const estimatedEquity = currentPortfolioValue - totalInvested;

  const activeStatuses: PortfolioInvestment['status'][] = [
    'active',
    'under_construction',
    'stabilized',
  ];
  const activeInvestments = investments.filter((inv) =>
    activeStatuses.includes(inv.status),
  ).length;
  const completedInvestments = investments.filter((inv) => inv.status === 'exited').length;

  const withRoi = investments.filter((inv) => inv.performance.projectedRoi > 0);
  const withIrr = investments.filter((inv) => inv.performance.irr > 0);

  const averageProjectedRoi =
    withRoi.length > 0
      ? withRoi.reduce((sum, inv) => sum + inv.performance.projectedRoi, 0) / withRoi.length
      : 0;

  const averageIrr =
    withIrr.length > 0
      ? withIrr.reduce((sum, inv) => sum + inv.performance.irr, 0) / withIrr.length
      : 0;

  return {
    totalInvestments: investments.length,
    totalInvested,
    currentPortfolioValue,
    estimatedEquity,
    activeInvestments,
    completedInvestments,
    averageProjectedRoi,
    averageIrr,
    currency: investments[0]?.currency ?? 'USD',
  };
}

export const INVESTMENT_STATUS_LABELS: Record<PortfolioInvestment['status'], string> = {
  active: 'Active',
  under_construction: 'Under Construction',
  stabilized: 'Stabilized',
  exited: 'Exited',
  upcoming: 'Upcoming',
};

export const INVESTMENT_TYPE_LABELS: Record<PortfolioInvestment['type'], string> = {
  development: 'Development',
  rental: 'Rental',
  flip: 'Flip',
  condominium: 'Condominium',
  multifamily: 'Multifamily',
  commercial: 'Commercial',
};

export const PROJECT_STAGE_LABELS: Record<PortfolioInvestment['stage'], string> = {
  acquisition: 'Acquisition',
  pre_construction: 'Pre-Construction',
  construction: 'Construction',
  lease_up: 'Lease-Up',
  stabilized: 'Stabilized',
  exit: 'Exit',
};

export const RISK_LEVEL_LABELS: Record<PortfolioInvestment['riskLevel'], string> = {
  low: 'Low Risk',
  moderate: 'Moderate Risk',
  high: 'High Risk',
};

export const SORT_FIELD_LABELS: Record<
  import('./investment-types').InvestmentSortField,
  string
> = {
  projectName: 'Project Name',
  investmentDate: 'Investment Date',
  investedAmount: 'Amount Invested',
  currentValue: 'Current Value',
  roi: 'ROI',
  irr: 'IRR',
  status: 'Status',
  progressPercent: 'Progress',
  city: 'Location',
};
