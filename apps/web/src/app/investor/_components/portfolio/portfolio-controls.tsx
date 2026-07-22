'use client';

import { useCallback, useMemo, useState } from 'react';

import {
  INVESTMENT_STATUSES,
  INVESTMENT_TYPES,
  PROJECT_STAGES,
  RISK_LEVELS,
  type InvestmentStatus,
  type InvestmentType,
  type ProjectStage,
  type RiskLevel,
} from '../../_data/investment-types';
import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
  RISK_LEVEL_LABELS,
} from '../../_data/investments';
import type { PortfolioDatePreset, PortfolioFilterState } from '../../_data/portfolio-types';

export interface PortfolioControlsState {
  dateRange: PortfolioDatePreset;
  filters: PortfolioFilterState;
}

export interface PortfolioControlsProps {
  state: PortfolioControlsState;
  activeFilterCount: number;
  assetClasses: string[];
  locations: string[];
  onDateRangeChange: (preset: PortfolioDatePreset) => void;
  onFilterChange: <K extends keyof PortfolioFilterState>(
    key: K,
    value: PortfolioFilterState[K],
  ) => void;
  onClearFilters: () => void;
}

const DATE_PRESETS: { value: PortfolioDatePreset; label: string }[] = [
  { value: '3M', label: '3M' },
  { value: '6M', label: '6M' },
  { value: 'YTD', label: 'YTD' },
  { value: '1Y', label: '1Y' },
  { value: '3Y', label: '3Y' },
  { value: 'inception', label: 'Since Inception' },
  { value: 'custom', label: 'Custom' },
];

export function usePortfolioControls(initial?: Partial<PortfolioControlsState>) {
  const [dateRange, setDateRange] = useState<PortfolioDatePreset>(
    initial?.dateRange ?? '1Y',
  );
  const [filters, setFilters] = useState<PortfolioFilterState>(
    initial?.filters ?? {
      status: 'all',
      assetClass: 'all',
      type: 'all',
      location: 'all',
      stage: 'all',
      riskLevel: 'all',
    },
  );

  const updateFilter = useCallback(
    <K extends keyof PortfolioFilterState>(key: K, value: PortfolioFilterState[K]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const clearFilters = useCallback(() => {
    setFilters({
      status: 'all',
      assetClass: 'all',
      type: 'all',
      location: 'all',
      stage: 'all',
      riskLevel: 'all',
    });
  }, []);

  return useMemo(
    () => ({
      dateRange,
      filters,
      setDateRange,
      updateFilter,
      clearFilters,
    }),
    [dateRange, filters, updateFilter, clearFilters],
  );
}

export function PortfolioControls({
  state,
  activeFilterCount,
  assetClasses,
  locations,
  onDateRangeChange,
  onFilterChange,
  onClearFilters,
}: PortfolioControlsProps) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [customOpen, setCustomOpen] = useState(false);

  const filterFields = (
    <>
      <FilterSelect
        label="Status"
        value={state.filters.status}
        onChange={(v) => onFilterChange('status', v as InvestmentStatus | 'all')}
        options={[
          { value: 'all', label: 'All Statuses' },
          ...INVESTMENT_STATUSES.map((s) => ({
            value: s,
            label: INVESTMENT_STATUS_LABELS[s],
          })),
        ]}
      />
      <FilterSelect
        label="Asset Class"
        value={state.filters.assetClass}
        onChange={(v) => onFilterChange('assetClass', v)}
        options={[
          { value: 'all', label: 'All Asset Classes' },
          ...assetClasses.map((c) => ({ value: c, label: c })),
        ]}
      />
      <FilterSelect
        label="Investment Type"
        value={state.filters.type}
        onChange={(v) => onFilterChange('type', v as InvestmentType | 'all')}
        options={[
          { value: 'all', label: 'All Types' },
          ...INVESTMENT_TYPES.map((t) => ({
            value: t,
            label: INVESTMENT_TYPE_LABELS[t],
          })),
        ]}
      />
      <FilterSelect
        label="Location"
        value={state.filters.location}
        onChange={(v) => onFilterChange('location', v)}
        options={[
          { value: 'all', label: 'All Locations' },
          ...locations.map((l) => ({ value: l, label: l })),
        ]}
      />
      <FilterSelect
        label="Project Stage"
        value={state.filters.stage}
        onChange={(v) => onFilterChange('stage', v as ProjectStage | 'all')}
        options={[
          { value: 'all', label: 'All Stages' },
          ...PROJECT_STAGES.map((s) => ({
            value: s,
            label: PROJECT_STAGE_LABELS[s],
          })),
        ]}
      />
      <FilterSelect
        label="Risk Level"
        value={state.filters.riskLevel}
        onChange={(v) => onFilterChange('riskLevel', v as RiskLevel | 'all')}
        options={[
          { value: 'all', label: 'All Risk Levels' },
          ...RISK_LEVELS.map((r) => ({
            value: r,
            label: RISK_LEVEL_LABELS[r],
          })),
        ]}
      />
    </>
  );

  return (
    <div className="inv-portfolio-controls">
      <div className="inv-portfolio-controls__date-row">
        <span className="inv-portfolio-controls__label">Date range</span>
        <div className="inv-portfolio-controls__presets" role="group" aria-label="Date range presets">
          {DATE_PRESETS.map((preset) => (
            <button
              key={preset.value}
              type="button"
              className={`inv-portfolio-controls__preset${state.dateRange === preset.value ? ' inv-portfolio-controls__preset--active' : ''}`}
              aria-pressed={state.dateRange === preset.value}
              onClick={() => {
                onDateRangeChange(preset.value);
                if (preset.value === 'custom') setCustomOpen(true);
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>
        {customOpen && state.dateRange === 'custom' ? (
          <p className="inv-portfolio-controls__custom-note" role="status">
            Custom date range selection will be available in a future release.
          </p>
        ) : null}
      </div>

      <div className="inv-portfolio-controls__filter-row">
        <button
          type="button"
          className="inv-portfolio-controls__filter-toggle inv-investments__filter-toggle"
          aria-expanded={drawerOpen}
          onClick={() => setDrawerOpen((p) => !p)}
        >
          Filters
          {activeFilterCount > 0 ? (
            <span className="inv-investments__filter-badge">{activeFilterCount}</span>
          ) : null}
        </button>
        {activeFilterCount > 0 ? (
          <button type="button" className="inv-portfolio-controls__clear" onClick={onClearFilters}>
            Clear filters ({activeFilterCount})
          </button>
        ) : null}
        <div className="inv-portfolio-controls__filter-grid inv-portfolio-controls__filter-grid--desktop">
          {filterFields}
        </div>
      </div>

      {drawerOpen ? (
        <div className="inv-portfolio-controls__drawer" role="region" aria-label="Portfolio filters">
          <div className="inv-portfolio-controls__filter-grid">{filterFields}</div>
        </div>
      ) : null}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}) {
  const id = label.replace(/\s/g, '-').toLowerCase();
  return (
    <div className="inv-portfolio-controls__field">
      <label htmlFor={id} className="inv-portfolio-controls__field-label">
        {label}
      </label>
      <select
        id={id}
        className="inv-investments__select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
