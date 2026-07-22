'use client';

import { getAllInvestments } from '../../_data/investments';
import {
  DOCUMENT_CATEGORIES,
  DOCUMENT_FILE_TYPES,
  DOCUMENT_STATUSES,
  DOCUMENT_TAGS,
  DOCUMENT_TYPES,
} from '../../_data/document-types';
import type { DocumentFilterState } from '../../_data/document-types';
import {
  DOCUMENT_CATEGORY_LABELS,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
} from '../../_data/documents';
import { getAvailableTaxYears } from '../../_data/document-calculations';
import type { InvestorDocument } from '../../_data/document-types';

export interface DocumentFiltersProps {
  filters: DocumentFilterState;
  documents: InvestorDocument[];
  onChange: (patch: Partial<DocumentFilterState>) => void;
  onReset: () => void;
}

export function DocumentFilters({
  filters,
  documents,
  onChange,
  onReset,
}: DocumentFiltersProps) {
  const investments = getAllInvestments();
  const taxYears = getAvailableTaxYears(documents);

  return (
    <div className="inv-docs__filters">
      <div className="inv-docs__filters-row">
        <label className="inv-docs__filter-field inv-docs__filter-field--search">
          <span className="inv-docs__filter-label">Search</span>
          <input
            type="search"
            value={filters.search}
            onChange={(e) => onChange({ search: e.target.value })}
            placeholder="Search documents…"
            aria-label="Search documents"
          />
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Investment</span>
          <select
            value={filters.investmentId}
            onChange={(e) => onChange({ investmentId: e.target.value })}
            aria-label="Filter by investment"
          >
            <option value="all">All Investments</option>
            {investments.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.projectName}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Category</span>
          <select
            value={filters.category}
            onChange={(e) =>
              onChange({ category: e.target.value as DocumentFilterState['category'] })
            }
            aria-label="Filter by category"
          >
            <option value="all">All Categories</option>
            {DOCUMENT_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {DOCUMENT_CATEGORY_LABELS[cat]}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Type</span>
          <select
            value={filters.documentType}
            onChange={(e) =>
              onChange({ documentType: e.target.value as DocumentFilterState['documentType'] })
            }
            aria-label="Filter by document type"
          >
            <option value="all">All Types</option>
            {DOCUMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {DOCUMENT_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Status</span>
          <select
            value={filters.status}
            onChange={(e) =>
              onChange({ status: e.target.value as DocumentFilterState['status'] })
            }
            aria-label="Filter by status"
          >
            <option value="all">All Statuses</option>
            {DOCUMENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {DOCUMENT_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="inv-docs__filters-row">
        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">File Type</span>
          <select
            value={filters.fileType}
            onChange={(e) =>
              onChange({ fileType: e.target.value as DocumentFilterState['fileType'] })
            }
            aria-label="Filter by file type"
          >
            <option value="all">All Formats</option>
            {DOCUMENT_FILE_TYPES.map((ft) => (
              <option key={ft} value={ft}>
                {ft.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Tax Year</span>
          <select
            value={String(filters.taxYear)}
            onChange={(e) =>
              onChange({
                taxYear: e.target.value === 'all' ? 'all' : Number(e.target.value),
              })
            }
            aria-label="Filter by tax year"
          >
            <option value="all">All Years</option>
            {taxYears.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Signature</span>
          <select
            value={filters.requiresSignature}
            onChange={(e) =>
              onChange({
                requiresSignature: e.target.value as DocumentFilterState['requiresSignature'],
              })
            }
            aria-label="Filter by signature requirement"
          >
            <option value="all">Any</option>
            <option value="yes">Requires Signature</option>
            <option value="no">No Signature</option>
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Read Status</span>
          <select
            value={filters.isRead}
            onChange={(e) =>
              onChange({ isRead: e.target.value as DocumentFilterState['isRead'] })
            }
            aria-label="Filter by read status"
          >
            <option value="all">All</option>
            <option value="unread">Unread</option>
            <option value="read">Read</option>
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">Archive</span>
          <select
            value={filters.isArchived}
            onChange={(e) =>
              onChange({ isArchived: e.target.value as DocumentFilterState['isArchived'] })
            }
            aria-label="Filter archived documents"
          >
            <option value="active">Active Only</option>
            <option value="archived">Archived Only</option>
            <option value="all">All</option>
          </select>
        </label>

        <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={onReset}>
          Reset Filters
        </button>
      </div>

      <fieldset className="inv-docs__tag-filters">
        <legend className="inv-docs__filter-label">Tags</legend>
        {DOCUMENT_TAGS.map((tag) => (
          <label key={tag} className="inv-docs__tag-chip">
            <input
              type="checkbox"
              checked={filters.tags.includes(tag)}
              onChange={(e) => {
                const tags = e.target.checked
                  ? [...filters.tags, tag]
                  : filters.tags.filter((t) => t !== tag);
                onChange({ tags });
              }}
            />
            {tag.replace(/_/g, ' ')}
          </label>
        ))}
      </fieldset>
    </div>
  );
}
