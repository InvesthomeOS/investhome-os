'use client';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  filterSignatureRequests,
  filterSignatureRequestsByTab,
} from '../../_data/document-calculations';
import type { SignatureFilterState, SignatureTab } from '../../_data/document-types';
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
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const t = useTranslations('investorPortal');
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

      <div className="inv-sig__tabs" role="tablist" aria-label={tChrome('k20906b39db')}>
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? 'inv-sig__tab--active' : undefined}
            onClick={() => setTab(t)}
          >
            {investorLabel(tLabels, 'signatureTab', t)}
          </button>
        ))}
      </div>

      <div className="inv-sig__filters">
        <input
          type="search"
          value={filters.search}
          onChange={(e) => updateFilters({ search: e.target.value })}
          placeholder={t('placeholders.searchSignatures')}
          aria-label={tChrome('k1530d7be56')}
        />
        <select
          value={filters.investmentId}
          onChange={(e) => updateFilters({ investmentId: e.target.value })}
          aria-label={tChrome('k3132ed40f5')}
        >
          <option value="all">{tChrome('k7b247b9d1a')}</option>
          {investments.map((inv) => (
            <option key={inv.id} value={inv.id}>{inv.projectName}</option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon="✍"
          title={tChrome('k3079c9d6ef')}
          description={`No requests in the "${investorLabel(tLabels, 'signatureTab', tab)}" tab match your filters.`}
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
