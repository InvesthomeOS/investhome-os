import { getAllInvestments } from './investments';
import type {
  Distribution,
  DistributionBreakdown,
  DistributionFrequency,
  DistributionStatus,
  DistributionType,
  PaymentMethod,
  PaymentStatus,
  PaymentTimelineStep,
} from './distribution-types';

/** Reference "today" aligned with existing investor mock data (mid-2025). */
export const DISTRIBUTION_REFERENCE_DATE = '2025-07-16';

interface DistributionSeed {
  id: string;
  investmentId: string;
  periodLabel: string;
  taxYear: number;
  distributionType: DistributionType;
  frequency: DistributionFrequency;
  declaredDate: string;
  recordDate: string;
  paymentDate: string;
  preferredReturn?: number;
  returnOfCapital?: number;
  profitShare?: number;
  refinance?: number;
  sale?: number;
  fees?: number;
  withholding?: number;
  status: DistributionStatus;
  paymentMethod: PaymentMethod;
  paymentStatus: PaymentStatus;
  reference: string;
  statementId: string | null;
  notes?: string | null;
  delayReason?: string | null;
  failureReason?: string | null;
}

function buildBreakdown(seed: DistributionSeed): DistributionBreakdown {
  const preferredReturnAmount = seed.preferredReturn ?? 0;
  const returnOfCapitalAmount = seed.returnOfCapital ?? 0;
  const profitShareAmount = seed.profitShare ?? 0;
  const refinanceAmount = seed.refinance ?? 0;
  const saleAmount = seed.sale ?? 0;
  const grossAmount =
    preferredReturnAmount +
    returnOfCapitalAmount +
    profitShareAmount +
    refinanceAmount +
    saleAmount;
  const fees = seed.fees ?? 0;
  const withholding = seed.withholding ?? 0;
  const netAmount = grossAmount - fees - withholding;

  return {
    grossAmount,
    preferredReturnAmount,
    returnOfCapitalAmount,
    profitShareAmount,
    refinanceAmount,
    saleAmount,
    fees,
    withholding,
    netAmount,
  };
}

function setStage(
  stages: PaymentTimelineStep[],
  index: number,
  patch: Partial<PaymentTimelineStep>,
): void {
  const stage = stages[index];
  if (!stage) return;
  Object.assign(stage, patch);
}

function buildTimeline(
  seed: DistributionSeed,
  status: DistributionStatus,
): PaymentTimelineStep[] {
  const stages: PaymentTimelineStep[] = [
    { stage: 'declared', label: 'Declared', date: seed.declaredDate, completed: false },
    { stage: 'record_date', label: 'Record Date', date: seed.recordDate, completed: false },
    { stage: 'approved', label: 'Approved', date: null, completed: false },
    { stage: 'initiated', label: 'Payment Initiated', date: null, completed: false },
    { stage: 'completed', label: 'Completed', date: null, completed: false },
  ];

  const approvedDate = addDays(seed.recordDate, 2);
  const initiatedDate = addDays(seed.paymentDate, -1);
  const completedDate = seed.paymentDate;

  if (status === 'scheduled') {
    setStage(stages, 0, { completed: false });
    return stages;
  }

  if (status === 'declared') {
    setStage(stages, 0, { completed: true });
    return stages;
  }

  if (status === 'approved' || status === 'delayed') {
    setStage(stages, 0, { completed: true });
    setStage(stages, 1, { completed: true });
    setStage(stages, 2, { date: approvedDate, completed: true });
    return stages;
  }

  if (status === 'processing') {
    setStage(stages, 0, { completed: true });
    setStage(stages, 1, { completed: true });
    setStage(stages, 2, { date: approvedDate, completed: true });
    setStage(stages, 3, { date: initiatedDate, completed: true });
    return stages;
  }

  if (status === 'completed') {
    setStage(stages, 0, { completed: true });
    setStage(stages, 1, { completed: true });
    setStage(stages, 2, { date: approvedDate, completed: true });
    setStage(stages, 3, { date: initiatedDate, completed: true });
    setStage(stages, 4, { date: completedDate, completed: true });
    return stages;
  }

  if (status === 'failed') {
    setStage(stages, 0, { completed: true });
    setStage(stages, 1, { completed: true });
    setStage(stages, 2, { date: approvedDate, completed: true });
    setStage(stages, 3, { date: initiatedDate, completed: true });
    setStage(stages, 4, { completed: false });
    return stages;
  }

  setStage(stages, 0, { completed: true });
  return stages;
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function resolveInvestmentMeta(investmentId: string): {
  investmentName: string;
  entityName: string;
  currency: string;
} {
  const inv = getAllInvestments().find((i) => i.id === investmentId);
  if (!inv) {
    return { investmentName: 'Unknown Investment', entityName: 'Unknown Entity', currency: 'USD' };
  }
  return {
    investmentName: inv.projectName,
    entityName: inv.entityName,
    currency: inv.currency,
  };
}

function buildDistribution(seed: DistributionSeed): Distribution {
  const meta = resolveInvestmentMeta(seed.investmentId);
  const breakdown = buildBreakdown(seed);

  return {
    id: seed.id,
    investmentId: seed.investmentId,
    investmentName: meta.investmentName,
    entityName: meta.entityName,
    periodLabel: seed.periodLabel,
    taxYear: seed.taxYear,
    distributionType: seed.distributionType,
    frequency: seed.frequency,
    declaredDate: seed.declaredDate,
    recordDate: seed.recordDate,
    paymentDate: seed.paymentDate,
    breakdown,
    currency: meta.currency,
    status: seed.status,
    paymentMethod: seed.paymentMethod,
    paymentStatus: seed.paymentStatus,
    reference: seed.reference,
    statementId: seed.statementId,
    notes: seed.notes ?? null,
    delayReason: seed.delayReason ?? null,
    failureReason: seed.failureReason ?? null,
    paymentTimeline: buildTimeline(seed, seed.status),
  };
}

const distributionSeeds: DistributionSeed[] = [
  // pi-002 Uniloft — quarterly preferred return
  {
    id: 'dist-002-01',
    investmentId: 'pi-002',
    periodLabel: 'Q1 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-03-25',
    recordDate: '2024-03-31',
    paymentDate: '2024-04-15',
    preferredReturn: 17_000,
    fees: 25,
    withholding: 1_700,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'UNI-Q1-2024-001',
    statementId: 'stmt-002-01',
  },
  {
    id: 'dist-002-02',
    investmentId: 'pi-002',
    periodLabel: 'Q2 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-06-25',
    recordDate: '2024-06-30',
    paymentDate: '2024-07-15',
    preferredReturn: 17_000,
    fees: 25,
    withholding: 1_700,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'UNI-Q2-2024-001',
    statementId: 'stmt-002-02',
  },
  {
    id: 'dist-002-03',
    investmentId: 'pi-002',
    periodLabel: 'Q3 2024',
    taxYear: 2024,
    distributionType: 'mixed',
    frequency: 'quarterly',
    declaredDate: '2024-09-25',
    recordDate: '2024-09-30',
    paymentDate: '2024-10-15',
    preferredReturn: 17_000,
    profitShare: 2_000,
    fees: 30,
    withholding: 1_900,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'UNI-Q3-2024-001',
    statementId: 'stmt-002-03',
  },
  {
    id: 'dist-002-04',
    investmentId: 'pi-002',
    periodLabel: 'Q4 2024',
    taxYear: 2024,
    distributionType: 'mixed',
    frequency: 'quarterly',
    declaredDate: '2024-12-20',
    recordDate: '2024-12-31',
    paymentDate: '2025-01-15',
    preferredReturn: 17_000,
    profitShare: 2_500,
    fees: 30,
    withholding: 1_950,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'UNI-Q4-2024-001',
    statementId: 'stmt-002-04',
  },
  {
    id: 'dist-002-05',
    investmentId: 'pi-002',
    periodLabel: 'Q1 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-03-25',
    recordDate: '2025-03-31',
    paymentDate: '2025-04-15',
    preferredReturn: 17_000,
    fees: 25,
    withholding: 1_700,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'UNI-Q1-2025-001',
    statementId: 'stmt-002-05',
  },
  {
    id: 'dist-002-06',
    investmentId: 'pi-002',
    periodLabel: 'Q2 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-06-25',
    recordDate: '2025-06-30',
    paymentDate: '2025-07-15',
    preferredReturn: 17_000,
    fees: 25,
    withholding: 1_700,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'UNI-Q2-2025-001',
    statementId: 'stmt-002-06',
  },
  {
    id: 'dist-002-07',
    investmentId: 'pi-002',
    periodLabel: 'Q3 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-09-20',
    recordDate: '2025-09-30',
    paymentDate: '2025-09-30',
    preferredReturn: 17_000,
    fees: 25,
    withholding: 1_700,
    status: 'scheduled',
    paymentMethod: 'ach',
    paymentStatus: 'pending',
    reference: 'UNI-Q3-2025-001',
    statementId: null,
    notes: 'Estimated based on current occupancy and NOI projections.',
  },
  // pi-003 309 H Street
  {
    id: 'dist-003-01',
    investmentId: 'pi-003',
    periodLabel: 'Q2 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-06-20',
    recordDate: '2024-06-30',
    paymentDate: '2024-07-15',
    preferredReturn: 7_031,
    fees: 15,
    withholding: 703,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'HST-Q2-2024-001',
    statementId: 'stmt-003-01',
  },
  {
    id: 'dist-003-02',
    investmentId: 'pi-003',
    periodLabel: 'Q3 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-09-20',
    recordDate: '2024-09-30',
    paymentDate: '2024-10-15',
    preferredReturn: 7_031,
    fees: 15,
    withholding: 703,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'HST-Q3-2024-001',
    statementId: 'stmt-003-02',
  },
  {
    id: 'dist-003-03',
    investmentId: 'pi-003',
    periodLabel: 'Q4 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-12-18',
    recordDate: '2024-12-31',
    paymentDate: '2025-01-15',
    preferredReturn: 7_031,
    fees: 15,
    withholding: 703,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'HST-Q4-2024-001',
    statementId: 'stmt-003-03',
  },
  {
    id: 'dist-003-04',
    investmentId: 'pi-003',
    periodLabel: 'Q1 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-03-18',
    recordDate: '2025-03-31',
    paymentDate: '2025-04-15',
    preferredReturn: 7_031,
    fees: 15,
    withholding: 703,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'HST-Q1-2025-001',
    statementId: 'stmt-003-04',
  },
  {
    id: 'dist-003-05',
    investmentId: 'pi-003',
    periodLabel: 'Q2 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-06-18',
    recordDate: '2025-06-30',
    paymentDate: '2025-07-10',
    preferredReturn: 7_031,
    fees: 15,
    withholding: 703,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'HST-Q2-2025-001',
    statementId: 'stmt-003-05',
  },
  {
    id: 'dist-003-06',
    investmentId: 'pi-003',
    periodLabel: 'Q3 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-09-05',
    recordDate: '2025-09-15',
    paymentDate: '2025-09-15',
    preferredReturn: 7_031,
    fees: 15,
    withholding: 703,
    status: 'scheduled',
    paymentMethod: 'ach',
    paymentStatus: 'pending',
    reference: 'HST-Q3-2025-001',
    statementId: null,
  },
  {
    id: 'dist-003-07',
    investmentId: 'pi-003',
    periodLabel: 'Q2 2025 (Supplemental)',
    taxYear: 2025,
    distributionType: 'profit_share',
    frequency: 'one_time',
    declaredDate: '2025-06-01',
    recordDate: '2025-06-15',
    paymentDate: '2025-06-28',
    profitShare: 7_031,
    fees: 20,
    withholding: 1_054,
    status: 'delayed',
    paymentMethod: 'wire',
    paymentStatus: 'pending',
    reference: 'HST-SUP-2025-001',
    statementId: null,
    delayReason: 'Awaiting final lease-up certification from asset manager before release.',
    notes: 'Supplemental profit share tied to lease-up milestone.',
  },
  // pi-004 The Campus
  {
    id: 'dist-004-01',
    investmentId: 'pi-004',
    periodLabel: 'H1 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'semi_annual',
    declaredDate: '2024-06-01',
    recordDate: '2024-06-15',
    paymentDate: '2024-06-15',
    preferredReturn: 60_000,
    fees: 50,
    withholding: 9_000,
    status: 'completed',
    paymentMethod: 'wire',
    paymentStatus: 'completed',
    reference: 'CAM-H1-2024-001',
    statementId: 'stmt-004-01',
  },
  {
    id: 'dist-004-02',
    investmentId: 'pi-004',
    periodLabel: 'H2 2024',
    taxYear: 2024,
    distributionType: 'mixed',
    frequency: 'semi_annual',
    declaredDate: '2024-12-01',
    recordDate: '2024-12-15',
    paymentDate: '2024-12-15',
    preferredReturn: 60_000,
    profitShare: 10_000,
    fees: 75,
    withholding: 10_500,
    status: 'completed',
    paymentMethod: 'wire',
    paymentStatus: 'completed',
    reference: 'CAM-H2-2024-001',
    statementId: 'stmt-004-02',
  },
  {
    id: 'dist-004-03',
    investmentId: 'pi-004',
    periodLabel: 'H1 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'semi_annual',
    declaredDate: '2025-06-01',
    recordDate: '2025-06-15',
    paymentDate: '2025-06-15',
    preferredReturn: 60_000,
    fees: 50,
    withholding: 9_000,
    status: 'completed',
    paymentMethod: 'wire',
    paymentStatus: 'completed',
    reference: 'CAM-H1-2025-001',
    statementId: 'stmt-004-03',
  },
  {
    id: 'dist-004-04',
    investmentId: 'pi-004',
    periodLabel: 'H2 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'semi_annual',
    declaredDate: '2025-11-25',
    recordDate: '2025-12-15',
    paymentDate: '2025-12-15',
    preferredReturn: 60_000,
    fees: 50,
    withholding: 9_000,
    status: 'scheduled',
    paymentMethod: 'wire',
    paymentStatus: 'pending',
    reference: 'CAM-H2-2025-001',
    statementId: null,
  },
  // pi-005 Nelson Avenue
  {
    id: 'dist-005-01',
    investmentId: 'pi-005',
    periodLabel: 'Q1 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-04-20',
    recordDate: '2024-04-30',
    paymentDate: '2024-05-15',
    preferredReturn: 8_000,
    fees: 10,
    withholding: 800,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'NEL-Q1-2024-001',
    statementId: 'stmt-005-01',
  },
  {
    id: 'dist-005-02',
    investmentId: 'pi-005',
    periodLabel: 'Q2 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-07-20',
    recordDate: '2024-07-31',
    paymentDate: '2024-08-15',
    preferredReturn: 8_000,
    fees: 10,
    withholding: 800,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'NEL-Q2-2024-001',
    statementId: 'stmt-005-02',
  },
  {
    id: 'dist-005-03',
    investmentId: 'pi-005',
    periodLabel: 'Q3 2024',
    taxYear: 2024,
    distributionType: 'return_of_capital',
    frequency: 'quarterly',
    declaredDate: '2024-10-15',
    recordDate: '2024-10-31',
    paymentDate: '2024-11-15',
    preferredReturn: 8_000,
    returnOfCapital: 5_000,
    fees: 15,
    withholding: 1_300,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'NEL-Q3-2024-001',
    statementId: 'stmt-005-03',
  },
  {
    id: 'dist-005-04',
    investmentId: 'pi-005',
    periodLabel: 'Q4 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-01-15',
    recordDate: '2025-01-31',
    paymentDate: '2025-02-15',
    preferredReturn: 8_000,
    fees: 10,
    withholding: 800,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'NEL-Q4-2024-001',
    statementId: 'stmt-005-04',
  },
  {
    id: 'dist-005-05',
    investmentId: 'pi-005',
    periodLabel: 'Q1 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-04-20',
    recordDate: '2025-04-30',
    paymentDate: '2025-05-15',
    preferredReturn: 8_000,
    fees: 10,
    withholding: 800,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'NEL-Q1-2025-001',
    statementId: 'stmt-005-05',
  },
  {
    id: 'dist-005-06',
    investmentId: 'pi-005',
    periodLabel: 'Q2 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-07-01',
    recordDate: '2025-07-15',
    paymentDate: '2025-07-31',
    preferredReturn: 8_000,
    fees: 10,
    withholding: 800,
    status: 'processing',
    paymentMethod: 'ach',
    paymentStatus: 'initiated',
    reference: 'NEL-Q2-2025-001',
    statementId: null,
  },
  // pi-007 Riverside Flip — exit distribution
  {
    id: 'dist-007-01',
    investmentId: 'pi-007',
    periodLabel: 'Interim Return 2023',
    taxYear: 2023,
    distributionType: 'return_of_capital',
    frequency: 'one_time',
    declaredDate: '2023-06-01',
    recordDate: '2023-06-15',
    paymentDate: '2023-06-30',
    returnOfCapital: 100_000,
    fees: 100,
    withholding: 0,
    status: 'completed',
    paymentMethod: 'wire',
    paymentStatus: 'completed',
    reference: 'RIV-INT-2023-001',
    statementId: 'stmt-007-01',
  },
  {
    id: 'dist-007-02',
    investmentId: 'pi-007',
    periodLabel: 'Final Exit 2024',
    taxYear: 2024,
    distributionType: 'sale_proceeds',
    frequency: 'one_time',
    declaredDate: '2024-11-01',
    recordDate: '2024-11-15',
    paymentDate: '2024-11-20',
    returnOfCapital: 250_000,
    profitShare: 147_000,
    fees: 500,
    withholding: 22_050,
    status: 'completed',
    paymentMethod: 'wire',
    paymentStatus: 'completed',
    reference: 'RIV-EXIT-2024-001',
    statementId: 'stmt-007-02',
    notes: 'Final exit distribution upon sale of Riverside property portfolio.',
  },
  // pi-009 Georgetown Row
  {
    id: 'dist-009-01',
    investmentId: 'pi-009',
    periodLabel: 'Q3 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2024-10-15',
    recordDate: '2024-10-31',
    paymentDate: '2024-11-15',
    preferredReturn: 3_047,
    fees: 10,
    withholding: 305,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'GEO-Q3-2024-001',
    statementId: 'stmt-009-01',
  },
  {
    id: 'dist-009-02',
    investmentId: 'pi-009',
    periodLabel: 'Q4 2024',
    taxYear: 2024,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-01-10',
    recordDate: '2025-01-31',
    paymentDate: '2025-01-31',
    preferredReturn: 3_047,
    fees: 10,
    withholding: 305,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'GEO-Q4-2024-001',
    statementId: 'stmt-009-02',
  },
  {
    id: 'dist-009-03',
    investmentId: 'pi-009',
    periodLabel: 'Q1 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-04-10',
    recordDate: '2025-04-30',
    paymentDate: '2025-05-15',
    preferredReturn: 3_047,
    fees: 10,
    withholding: 305,
    status: 'completed',
    paymentMethod: 'ach',
    paymentStatus: 'completed',
    reference: 'GEO-Q1-2025-001',
    statementId: 'stmt-009-03',
  },
  {
    id: 'dist-009-04',
    investmentId: 'pi-009',
    periodLabel: 'Q2 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-07-01',
    recordDate: '2025-07-15',
    paymentDate: '2025-07-31',
    preferredReturn: 3_047,
    fees: 10,
    withholding: 305,
    status: 'failed',
    paymentMethod: 'ach',
    paymentStatus: 'failed',
    reference: 'GEO-Q2-2025-001',
    statementId: null,
    failureReason: 'ACH transfer rejected — bank account verification expired. Please update payment information.',
  },
  {
    id: 'dist-009-05',
    investmentId: 'pi-009',
    periodLabel: 'Q3 2025',
    taxYear: 2025,
    distributionType: 'preferred_return',
    frequency: 'quarterly',
    declaredDate: '2025-08-15',
    recordDate: '2025-08-31',
    paymentDate: '2025-08-31',
    preferredReturn: 3_047,
    fees: 10,
    withholding: 305,
    status: 'scheduled',
    paymentMethod: 'ach',
    paymentStatus: 'pending',
    reference: 'GEO-Q3-2025-001',
    statementId: null,
    notes: 'Pending resolution of Q2 payment failure before processing.',
  },
  // pi-004 refinance proceeds (one-time)
  {
    id: 'dist-004-05',
    investmentId: 'pi-004',
    periodLabel: 'Refinance Proceeds 2023',
    taxYear: 2023,
    distributionType: 'refinance_proceeds',
    frequency: 'one_time',
    declaredDate: '2023-09-01',
    recordDate: '2023-09-15',
    paymentDate: '2023-09-30',
    refinance: 45_000,
    fees: 75,
    withholding: 6_750,
    status: 'completed',
    paymentMethod: 'wire',
    paymentStatus: 'completed',
    reference: 'CAM-REFI-2023-001',
    statementId: 'stmt-004-04',
  },
];

const portfolioDistributions: Distribution[] = distributionSeeds.map(buildDistribution);

export function getAllDistributions(): Distribution[] {
  return [...portfolioDistributions].sort(
    (a, b) => new Date(b.paymentDate).getTime() - new Date(a.paymentDate).getTime(),
  );
}

export function getDistributionById(id: string): Distribution | undefined {
  return portfolioDistributions.find((d) => d.id === id);
}

export function getDistributionsByInvestmentId(investmentId: string): Distribution[] {
  return getAllDistributions().filter((d) => d.investmentId === investmentId);
}

export const DISTRIBUTION_TYPE_LABELS: Record<Distribution['distributionType'], string> = {
  preferred_return: 'Preferred Return',
  return_of_capital: 'Return of Capital',
  profit_share: 'Profit Share',
  refinance_proceeds: 'Refinance Proceeds',
  sale_proceeds: 'Sale Proceeds',
  mixed: 'Mixed Distribution',
};

export const DISTRIBUTION_STATUS_LABELS: Record<DistributionStatus, string> = {
  scheduled: 'Scheduled',
  declared: 'Declared',
  approved: 'Approved',
  processing: 'Processing',
  completed: 'Completed',
  delayed: 'Delayed',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  ach: 'ACH Transfer',
  wire: 'Wire Transfer',
  check: 'Check',
};

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  pending: 'Pending',
  initiated: 'Initiated',
  completed: 'Completed',
  failed: 'Failed',
};

export function verifyDistributionReconciliation(distribution: Distribution): boolean {
  const { breakdown } = distribution;
  const gross =
    breakdown.preferredReturnAmount +
    breakdown.returnOfCapitalAmount +
    breakdown.profitShareAmount +
    breakdown.refinanceAmount +
    breakdown.saleAmount;
  return (
    breakdown.grossAmount === gross &&
    breakdown.netAmount === breakdown.grossAmount - breakdown.fees - breakdown.withholding
  );
}
