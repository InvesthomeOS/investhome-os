'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  filterSignatureRequests,
  filterSignatureRequestsByTab,
} from '../../_data/document-calculations';
import type { SignatureFilterState, SignatureTab } from '../../_data/document-types';
import { SIGNATURE_TAB_LABELS } from '../../_data/signature-requests';
import { getAllInvestments } from '../../_data/investments';
import { LoadingSkeletonGrid } from '../loading-skeleton';
import { EmptyState } from '../empty-state';
import { useDocumentsState } from '../../_state/documents-state';
import { DemonstrationBanner } from '../documents/demonstration-banner';
import { SignatureCard } from './signature-card';
import { SignatureKpiRow, SignaturesHeader } from './signature-kpi-row';

const TABS: SignatureTab[] = [
  'action_required',
  'waiting_on_others',
  'completed',
  'declined',
  'expired',
  'voided',
  'all',
];

const DEFAULT_FILTERS: SignatureFilterState = {
  search: '',
  investmentId: 'all',
  status: 'all',
  dateFrom: '',
  dateTo: '',
};

export function SignatureDashboard() {
  const { signatureRequests, signatureSummary } = useDocumentsState();
  const [tab, setTab] = useState<SignatureTab>('action_required');
  const [filters, setFilters] = useState<SignatureFilterState>(DEFAULT_FILTERS);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 350);
    return () => window.clearTimeout(timer);
  }, []);

  const filtered = useMemo(() => {
    const byTab = filterSignatureRequestsByTab(signatureRequests, tab);
    return filterSignatureRequests(byTab, filters);
  }, [signatureRequests, tab, filters]);

  const investments = getAllInvestments();

  const updateFilters = useCallback((patch: Partial<SignatureFilterState>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
  }, []);

  if (isLoading) {
    return (
      <div className="investor-page">
        <LoadingSkeletonGrid count={6} />
      </div>
    );
  }

  return (
    <div className="investor-page inv-sig">
      <DemonstrationBanner />
      <SignaturesHeader />
      <SignatureKpiRow summary={signatureSummary} />

      <div className="inv-sig__tabs" role="tablist" aria-label="Signature request tabs">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? 'inv-sig__tab--active' : undefined}
            onClick={() => setTab(t)}
          >
            {SIGNATURE_TAB_LABELS[t]}
          </button>
        ))}
      </div>

      <div className="inv-sig__filters">
        <input
          type="search"
          value={filters.search}
          onChange={(e) => updateFilters({ search: e.target.value })}
          placeholder="Search signature requests…"
          aria-label="Search signature requests"
        />
        <select
          value={filters.investmentId}
          onChange={(e) => updateFilters({ investmentId: e.target.value })}
          aria-label="Filter by investment"
        >
          <option value="all">All Investments</option>
          {investments.map((inv) => (
            <option key={inv.id} value={inv.id}>{inv.projectName}</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon="✍"
          title="No signature requests"
          description={`No requests in the "${SIGNATURE_TAB_LABELS[tab]}" tab match your filters.`}
        />
      ) : (
        <div className="inv-sig__card-grid">
          {filtered.map((req) => (
            <SignatureCard key={req.id} request={req} />
          ))}
        </div>
      )}
    </div>
  );
}
