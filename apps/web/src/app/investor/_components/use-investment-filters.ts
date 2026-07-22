'use client';

import { useCallback, useMemo, useState } from 'react';

import { getAllInvestments } from '../_data/investments';
import type {
  InvestmentFilterState,
  InvestmentSortField,
  PortfolioInvestment,
  SortDirection,
} from '../_data/investment-types';

export const DEFAULT_INVESTMENT_FILTERS: InvestmentFilterState = {
  search: '',
  status: 'all',
  type: 'all',
  location: 'all',
  stage: 'all',
  investmentDateFrom: '',
  investmentDateTo: '',
  sortField: 'investmentDate',
  sortDirection: 'desc',
  viewMode: 'grid',
};

function matchesSearch(investment: PortfolioInvestment, query: string): boolean {
  if (!query.trim()) return true;

  const haystack = [
    investment.projectName,
    investment.address,
    investment.city,
    investment.state,
    investment.entityName,
    `${investment.city}, ${investment.state}`,
  ]
    .join(' ')
    .toLowerCase();

  return haystack.includes(query.trim().toLowerCase());
}

function getSortValue(investment: PortfolioInvestment, field: InvestmentSortField): string | number {
  switch (field) {
    case 'projectName':
      return investment.projectName.toLowerCase();
    case 'investmentDate':
      return new Date(investment.investmentDate).getTime();
    case 'investedAmount':
      return investment.investedAmount;
    case 'currentValue':
      return investment.currentValue;
    case 'roi':
      return investment.performance.roi;
    case 'irr':
      return investment.performance.irr;
    case 'status':
      return investment.status;
    case 'progressPercent':
      return investment.progressPercent;
    case 'city':
      return `${investment.city}, ${investment.state}`.toLowerCase();
    default:
      return 0;
  }
}

function compareValues(a: string | number, b: string | number, direction: SortDirection): number {
  if (a < b) return direction === 'asc' ? -1 : 1;
  if (a > b) return direction === 'asc' ? 1 : -1;
  return 0;
}

function countActiveFilters(filters: InvestmentFilterState): number {
  let count = 0;
  if (filters.status !== 'all') count += 1;
  if (filters.type !== 'all') count += 1;
  if (filters.location !== 'all') count += 1;
  if (filters.stage !== 'all') count += 1;
  if (filters.investmentDateFrom) count += 1;
  if (filters.investmentDateTo) count += 1;
  return count;
}

export interface UseInvestmentFiltersResult {
  filters: InvestmentFilterState;
  setFilters: React.Dispatch<React.SetStateAction<InvestmentFilterState>>;
  filteredInvestments: PortfolioInvestment[];
  allInvestments: PortfolioInvestment[];
  activeFilterCount: number;
  updateFilter: <K extends keyof InvestmentFilterState>(
    key: K,
    value: InvestmentFilterState[K],
  ) => void;
  clearFilters: () => void;
  toggleSortDirection: () => void;
  setSortField: (field: InvestmentSortField) => void;
}

export function useInvestmentFilters(
  source: PortfolioInvestment[] = getAllInvestments(),
): UseInvestmentFiltersResult {
  const [filters, setFilters] = useState<InvestmentFilterState>(DEFAULT_INVESTMENT_FILTERS);

  const filteredInvestments = useMemo(() => {
    let result = source.filter((investment) => {
      if (!matchesSearch(investment, filters.search)) return false;
      if (filters.status !== 'all' && investment.status !== filters.status) return false;
      if (filters.type !== 'all' && investment.type !== filters.type) return false;
      if (filters.stage !== 'all' && investment.stage !== filters.stage) return false;

      const locationKey = `${investment.city}, ${investment.state}`;
      if (filters.location !== 'all' && locationKey !== filters.location) return false;

      if (filters.investmentDateFrom) {
        const from = new Date(filters.investmentDateFrom).getTime();
        if (new Date(investment.investmentDate).getTime() < from) return false;
      }

      if (filters.investmentDateTo) {
        const to = new Date(filters.investmentDateTo).getTime();
        if (new Date(investment.investmentDate).getTime() > to) return false;
      }

      return true;
    });

    result = [...result].sort((a, b) => {
      const aVal = getSortValue(a, filters.sortField);
      const bVal = getSortValue(b, filters.sortField);
      return compareValues(aVal, bVal, filters.sortDirection);
    });

    return result;
  }, [source, filters]);

  const activeFilterCount = useMemo(() => countActiveFilters(filters), [filters]);

  const updateFilter = useCallback(
    <K extends keyof InvestmentFilterState>(key: K, value: InvestmentFilterState[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const clearFilters = useCallback(() => {
    setFilters((prev) => ({
      ...DEFAULT_INVESTMENT_FILTERS,
      viewMode: prev.viewMode,
      sortField: prev.sortField,
      sortDirection: prev.sortDirection,
    }));
  }, []);

  const toggleSortDirection = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      sortDirection: prev.sortDirection === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  const setSortField = useCallback((field: InvestmentSortField) => {
    setFilters((prev) => {
      if (prev.sortField === field) {
        return {
          ...prev,
          sortDirection: prev.sortDirection === 'asc' ? 'desc' : 'asc',
        };
      }
      return { ...prev, sortField: field, sortDirection: 'desc' };
    });
  }, []);

  return {
    filters,
    setFilters,
    filteredInvestments,
    allInvestments: source,
    activeFilterCount,
    updateFilter,
    clearFilters,
    toggleSortDirection,
    setSortField,
  };
}
