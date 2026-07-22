'use client';

import { useId, useState } from 'react';

import {
  INVESTMENT_STATUS_LABELS,
  INVESTMENT_TYPE_LABELS,
  PROJECT_STAGE_LABELS,
  SORT_FIELD_LABELS,
  getInvestmentLocations,
} from '../_data/investments';
import {
  INVESTMENT_STATUSES,
  INVESTMENT_TYPES,
  PROJECT_STAGES,
  type InvestmentFilterState,
  type InvestmentSortField,
  type InvestmentViewMode,
} from '../_data/investment-types';

export interface InvestmentFiltersProps {
  filters: InvestmentFilterState;
  activeFilterCount: number;
  resultCount: number;
  onUpdateFilter: <K extends keyof InvestmentFilterState>(
    key: K,
    value: InvestmentFilterState[K],
  ) => void;
  onClearFilters: () => void;
  onToggleSortDirection: () => void;
}

export function InvestmentFilters({
  filters,
  activeFilterCount,
  resultCount,
  onUpdateFilter,
  onClearFilters,
  onToggleSortDirection,
}: InvestmentFiltersProps) {
  const baseId = useId();
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const locations = getInvestmentLocations();

  const sortOptions = Object.entries(SORT_FIELD_LABELS) as [InvestmentSortField, string][];

  return (
    <div className="inv-investments__toolbar">
      <div className="inv-investments__toolbar-row">
        <div className="inv-investments__search">
          <label htmlFor={`${baseId}-search`} className="inv-investments__sr-only">
            Search investments
          </label>
          <span className="inv-investments__search-icon" aria-hidden="true">
            ⌕
          </span>
          <input
            id={`${baseId}-search`}
            type="search"
            className="inv-investments__search-input"
            placeholder="Search by property, location, entity, or project..."
            value={filters.search}
            onChange={(e) => onUpdateFilter('search', e.target.value)}
          />
        </div>

        <div className="inv-investments__toolbar-actions">
          <button
            type="button"
            className="inv-investments__filter-toggle"
            aria-expanded={filtersExpanded}
            aria-controls={`${baseId}-filter-panel`}
            onClick={() => setFiltersExpanded((prev) => !prev)}
          >
            Filters
            {activeFilterCount > 0 ? (
              <span className="inv-investments__filter-badge" aria-label={`${activeFilterCount} active filters`}>
                {activeFilterCount}
              </span>
            ) : null}
          </button>

          <div className="inv-investments__sort">
            <label htmlFor={`${baseId}-sort`} className="inv-investments__sr-only">
              Sort investments
            </label>
            <select
              id={`${baseId}-sort`}
              className="inv-investments__select"
              value={filters.sortField}
              onChange={(e) => onUpdateFilter('sortField', e.target.value as InvestmentSortField)}
            >
              {sortOptions.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="inv-investments__sort-dir"
              onClick={onToggleSortDirection}
              aria-label={`Sort ${filters.sortDirection === 'asc' ? 'ascending' : 'descending'}`}
              title={`Sort ${filters.sortDirection === 'asc' ? 'ascending' : 'descending'}`}
            >
              {filters.sortDirection === 'asc' ? '↑' : '↓'}
            </button>
          </div>

          <div className="inv-investments__view-toggle" role="group" aria-label="View mode">
            <button
              type="button"
              className={`inv-investments__view-btn${filters.viewMode === 'grid' ? ' inv-investments__view-btn--active' : ''}`}
              aria-pressed={filters.viewMode === 'grid'}
              onClick={() => onUpdateFilter('viewMode', 'grid' as InvestmentViewMode)}
            >
              Grid
            </button>
            <button
              type="button"
              className={`inv-investments__view-btn${filters.viewMode === 'table' ? ' inv-investments__view-btn--active' : ''}`}
              aria-pressed={filters.viewMode === 'table'}
              onClick={() => onUpdateFilter('viewMode', 'table' as InvestmentViewMode)}
            >
              Table
            </button>
          </div>
        </div>
      </div>

      <div
        id={`${baseId}-filter-panel`}
        className={`inv-investments__filter-panel${filtersExpanded ? ' inv-investments__filter-panel--open' : ''}`}
      >
        <div className="inv-investments__filter-grid">
          <div className="inv-investments__filter-field">
            <label htmlFor={`${baseId}-status`}>Status</label>
            <select
              id={`${baseId}-status`}
              className="inv-investments__select"
              value={filters.status}
              onChange={(e) =>
                onUpdateFilter('status', e.target.value as InvestmentFilterState['status'])
              }
            >
              <option value="all">All</option>
              {INVESTMENT_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {INVESTMENT_STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </div>

          <div className="inv-investments__filter-field">
            <label htmlFor={`${baseId}-type`}>Investment Type</label>
            <select
              id={`${baseId}-type`}
              className="inv-investments__select"
              value={filters.type}
              onChange={(e) =>
                onUpdateFilter('type', e.target.value as InvestmentFilterState['type'])
              }
            >
              <option value="all">All Types</option>
              {INVESTMENT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {INVESTMENT_TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </div>

          <div className="inv-investments__filter-field">
            <label htmlFor={`${baseId}-location`}>Location</label>
            <select
              id={`${baseId}-location`}
              className="inv-investments__select"
              value={filters.location}
              onChange={(e) => onUpdateFilter('location', e.target.value)}
            >
              <option value="all">All Locations</option>
              {locations.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </div>

          <div className="inv-investments__filter-field">
            <label htmlFor={`${baseId}-stage`}>Project Stage</label>
            <select
              id={`${baseId}-stage`}
              className="inv-investments__select"
              value={filters.stage}
              onChange={(e) =>
                onUpdateFilter('stage', e.target.value as InvestmentFilterState['stage'])
              }
            >
              <option value="all">All Stages</option>
              {PROJECT_STAGES.map((stage) => (
                <option key={stage} value={stage}>
                  {PROJECT_STAGE_LABELS[stage]}
                </option>
              ))}
            </select>
          </div>

          <div className="inv-investments__filter-field">
            <label htmlFor={`${baseId}-date-from`}>Investment Date From</label>
            <input
              id={`${baseId}-date-from`}
              type="date"
              className="inv-investments__select"
              value={filters.investmentDateFrom}
              onChange={(e) => onUpdateFilter('investmentDateFrom', e.target.value)}
            />
          </div>

          <div className="inv-investments__filter-field">
            <label htmlFor={`${baseId}-date-to`}>Investment Date To</label>
            <input
              id={`${baseId}-date-to`}
              type="date"
              className="inv-investments__select"
              value={filters.investmentDateTo}
              onChange={(e) => onUpdateFilter('investmentDateTo', e.target.value)}
            />
          </div>
        </div>

        <div className="inv-investments__filter-footer">
          <p className="inv-investments__result-count" aria-live="polite">
            Showing {resultCount} investment{resultCount === 1 ? '' : 's'}
          </p>
          {activeFilterCount > 0 ? (
            <button type="button" className="inv-investments__clear-btn" onClick={onClearFilters}>
              Clear Filters
              <span className="inv-investments__filter-badge">{activeFilterCount}</span>
            </button>
          ) : null}
        </div>
      </div>

      <div className="inv-investments__filter-grid inv-investments__filter-grid--desktop">
        <div className="inv-investments__filter-field">
          <label htmlFor={`${baseId}-status-desktop`}>Status</label>
          <select
            id={`${baseId}-status-desktop`}
            className="inv-investments__select"
            value={filters.status}
            onChange={(e) =>
              onUpdateFilter('status', e.target.value as InvestmentFilterState['status'])
            }
          >
            <option value="all">All</option>
            {INVESTMENT_STATUSES.map((status) => (
              <option key={status} value={status}>
                {INVESTMENT_STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </div>

        <div className="inv-investments__filter-field">
          <label htmlFor={`${baseId}-type-desktop`}>Investment Type</label>
          <select
            id={`${baseId}-type-desktop`}
            className="inv-investments__select"
            value={filters.type}
            onChange={(e) =>
              onUpdateFilter('type', e.target.value as InvestmentFilterState['type'])
            }
          >
            <option value="all">All Types</option>
            {INVESTMENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {INVESTMENT_TYPE_LABELS[type]}
              </option>
            ))}
          </select>
        </div>

        <div className="inv-investments__filter-field">
          <label htmlFor={`${baseId}-location-desktop`}>Location</label>
          <select
            id={`${baseId}-location-desktop`}
            className="inv-investments__select"
            value={filters.location}
            onChange={(e) => onUpdateFilter('location', e.target.value)}
          >
            <option value="all">All Locations</option>
            {locations.map((location) => (
              <option key={location} value={location}>
                {location}
              </option>
            ))}
          </select>
        </div>

        <div className="inv-investments__filter-field">
          <label htmlFor={`${baseId}-stage-desktop`}>Project Stage</label>
          <select
            id={`${baseId}-stage-desktop`}
            className="inv-investments__select"
            value={filters.stage}
            onChange={(e) =>
              onUpdateFilter('stage', e.target.value as InvestmentFilterState['stage'])
            }
          >
            <option value="all">All Stages</option>
            {PROJECT_STAGES.map((stage) => (
              <option key={stage} value={stage}>
                {PROJECT_STAGE_LABELS[stage]}
              </option>
            ))}
          </select>
        </div>

        <div className="inv-investments__filter-field">
          <label htmlFor={`${baseId}-date-from-desktop`}>From</label>
          <input
            id={`${baseId}-date-from-desktop`}
            type="date"
            className="inv-investments__select"
            value={filters.investmentDateFrom}
            onChange={(e) => onUpdateFilter('investmentDateFrom', e.target.value)}
          />
        </div>

        <div className="inv-investments__filter-field">
          <label htmlFor={`${baseId}-date-to-desktop`}>To</label>
          <input
            id={`${baseId}-date-to-desktop`}
            type="date"
            className="inv-investments__select"
            value={filters.investmentDateTo}
            onChange={(e) => onUpdateFilter('investmentDateTo', e.target.value)}
          />
        </div>

        {activeFilterCount > 0 ? (
          <div className="inv-investments__filter-field inv-investments__filter-field--action">
            <span className="inv-investments__filter-field-spacer" aria-hidden="true">
              &nbsp;
            </span>
            <button type="button" className="inv-investments__clear-btn" onClick={onClearFilters}>
              Clear Filters
              <span className="inv-investments__filter-badge">{activeFilterCount}</span>
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
