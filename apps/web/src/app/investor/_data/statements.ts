import { getAllDistributions } from './distributions';
import type { DistributionStatement } from './distribution-types';

function buildStatementsFromDistributions(): DistributionStatement[] {
  const distributions = getAllDistributions();

  return distributions
    .filter((d) => d.statementId !== null)
    .map((d) => ({
      id: d.statementId!,
      distributionId: d.id,
      investmentId: d.investmentId,
      investmentName: d.investmentName,
      entityName: d.entityName,
      statementDate: d.paymentDate,
      periodLabel: d.periodLabel,
      taxYear: d.taxYear,
      distributionType: d.distributionType,
      grossAmount: d.breakdown.grossAmount,
      netAmount: d.breakdown.netAmount,
      currency: d.currency,
      status: d.status === 'completed' ? ('available' as const) : ('pending' as const),
      fileName: `${d.reference}-Statement.pdf`,
      pageCount: 2 + Math.floor(d.breakdown.grossAmount / 50_000),
    }));
}

const statements: DistributionStatement[] = buildStatementsFromDistributions();

export function getAllStatements(): DistributionStatement[] {
  return [...statements].sort(
    (a, b) => new Date(b.statementDate).getTime() - new Date(a.statementDate).getTime(),
  );
}

export function getStatementById(id: string): DistributionStatement | undefined {
  return statements.find((s) => s.id === id);
}

export function getStatementByDistributionId(
  distributionId: string,
): DistributionStatement | undefined {
  return statements.find((s) => s.distributionId === distributionId);
}

export function filterStatements(filters: {
  search: string;
  investmentId: string | 'all';
  taxYear: number | 'all';
  type: DistributionStatement['distributionType'] | 'all';
  status: DistributionStatement['status'] | 'all';
}): DistributionStatement[] {
  return getAllStatements().filter((s) => {
    if (filters.investmentId !== 'all' && s.investmentId !== filters.investmentId) return false;
    if (filters.taxYear !== 'all' && s.taxYear !== filters.taxYear) return false;
    if (filters.type !== 'all' && s.distributionType !== filters.type) return false;
    if (filters.status !== 'all' && s.status !== filters.status) return false;
    if (filters.search.trim()) {
      const q = filters.search.toLowerCase();
      const haystack = [s.investmentName, s.entityName, s.periodLabel, s.fileName]
        .join(' ')
        .toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

export const STATEMENT_STATUS_LABELS: Record<DistributionStatement['status'], string> = {
  available: 'Available',
  pending: 'Pending',
  archived: 'Archived',
};
