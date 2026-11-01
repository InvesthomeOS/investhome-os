'use client';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import { useTranslations } from 'next-intl';

import { getAllInvestments } from '../../_data/investments';
import {
  DOCUMENT_CATEGORIES,
  DOCUMENT_FILE_TYPES,
  DOCUMENT_STATUSES,
  DOCUMENT_TAGS,
  DOCUMENT_TYPES,
} from '../../_data/document-types';
import type { DocumentFilterState } from '../../_data/document-types';
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
  const tChrome = useTranslations('investorPortal.chrome');
  const tCommon = useTranslations('common');
  const tLabels = useTranslations('investorPortal.labels');
  const t = useTranslations('investorPortal');
  const investments = getAllInvestments();
  const taxYears = getAvailableTaxYears(documents);

  return (
    <div className="inv-docs__filters">
      <div className="inv-docs__filters-row">
        <label className="inv-docs__filter-field inv-docs__filter-field--search">
          <span className="inv-docs__filter-label">{tCommon('search')}</span>
          <input
            type="search"
            value={filters.search}
            onChange={(e) => onChange({ search: e.target.value })}
            placeholder={t('placeholders.searchDocuments')}
            aria-label={tChrome('kef37afa17c')}
          />
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('k0401729c31')}</span>
          <select
            value={filters.investmentId}
            onChange={(e) => onChange({ investmentId: e.target.value })}
            aria-label={tChrome('k3132ed40f5')}
          >
            <option value="all">{tChrome('k7b247b9d1a')}</option>
            {investments.map((inv) => (
              <option key={inv.id} value={inv.id}>
                {inv.projectName}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('ka3c686e711')}</span>
          <select
            value={filters.category}
            onChange={(e) =>
              onChange({ category: e.target.value as DocumentFilterState['category'] })
            }
            aria-label={tChrome('k459a08e4a2')}
          >
            <option value="all">{tChrome('k1fd266c217')}</option>
            {DOCUMENT_CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {investorLabel(tLabels, 'documentCategory', cat)}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('k3deb745651')}</span>
          <select
            value={filters.documentType}
            onChange={(e) =>
              onChange({ documentType: e.target.value as DocumentFilterState['documentType'] })
            }
            aria-label={tChrome('k5093dc931d')}
          >
            <option value="all">{tChrome('keb672cb3ba')}</option>
            {DOCUMENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {investorLabel(tLabels, 'documentType', t)}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('kbae7d5be70')}</span>
          <select
            value={filters.status}
            onChange={(e) =>
              onChange({ status: e.target.value as DocumentFilterState['status'] })
            }
            aria-label={tChrome('kf43653d7fa')}
          >
            <option value="all">{tChrome('k9cb29e734a')}</option>
            {DOCUMENT_STATUSES.map((s) => (
              <option key={s} value={s}>
                {investorLabel(tLabels, 'documentStatus', s)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="inv-docs__filters-row">
        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('k5023c8994c')}</span>
          <select
            value={filters.fileType}
            onChange={(e) =>
              onChange({ fileType: e.target.value as DocumentFilterState['fileType'] })
            }
            aria-label={tChrome('k3a245af898')}
          >
            <option value="all">{tChrome('k933f9f62b3')}</option>
            {DOCUMENT_FILE_TYPES.map((ft) => (
              <option key={ft} value={ft}>
                {ft.toUpperCase()}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('kc80ec709bc')}</span>
          <select
            value={String(filters.taxYear)}
            onChange={(e) =>
              onChange({
                taxYear: e.target.value === 'all' ? 'all' : Number(e.target.value),
              })
            }
            aria-label={tChrome('k6d2485491a')}
          >
            <option value="all">{tChrome('k6d76b811f7')}</option>
            {taxYears.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('k2f32be1dc7')}</span>
          <select
            value={filters.requiresSignature}
            onChange={(e) =>
              onChange({
                requiresSignature: e.target.value as DocumentFilterState['requiresSignature'],
              })
            }
            aria-label={tChrome('kcbd5bab927')}
          >
            <option value="all">{tChrome('k322444d3bb')}</option>
            <option value="yes">{tChrome('k970554ce3f')}</option>
            <option value="no">{tChrome('k19f3456b04')}</option>
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('k224a62fb91')}</span>
          <select
            value={filters.isRead}
            onChange={(e) =>
              onChange({ isRead: e.target.value as DocumentFilterState['isRead'] })
            }
            aria-label={tChrome('k4ca798b791')}
          >
            <option value="all">{tChrome('k6a72085653')}</option>
            <option value="unread">{tChrome('k07b032b56f')}</option>
            <option value="read">{tChrome('k852b438f91')}</option>
          </select>
        </label>

        <label className="inv-docs__filter-field">
          <span className="inv-docs__filter-label">{tChrome('k2621c6fd51')}</span>
          <select
            value={filters.isArchived}
            onChange={(e) =>
              onChange({ isArchived: e.target.value as DocumentFilterState['isArchived'] })
            }
            aria-label={tChrome('k68536afba1')}
          >
            <option value="active">{tChrome('k3dc1b81237')}</option>
            <option value="archived">{tChrome('k722f1601bd')}</option>
            <option value="all">{tChrome('k6a72085653')}</option>
          </select>
        </label>

        <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={onReset}>
          Reset Filters
        </button>
      </div>

      <fieldset className="inv-docs__tag-filters">
        <legend className="inv-docs__filter-label">{tChrome('k848eed0fbd')}</legend>
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
