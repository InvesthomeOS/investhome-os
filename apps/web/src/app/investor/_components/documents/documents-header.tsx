'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { formatDocumentBytes } from '../../_data/document-calculations';
import type { DocumentSummaryKpis } from '../../_data/document-types';
import { InvestorKpiCard } from '../kpi-card';

export interface DocumentsKpiRowProps {
  summary: DocumentSummaryKpis;
}

export function DocumentsKpiRow({ summary }: DocumentsKpiRowProps) {
  const kpis = [
    { label: 'Total Documents', value: summary.totalDocuments, meta: 'Active in library' },
    { label: 'New / Unread', value: summary.newDocuments, meta: 'Require attention' },
    {
      label: 'Pending Signatures',
      value: summary.pendingSignatures,
      meta: 'Action required',
    },
    {
      label: 'Completed Signatures',
      value: summary.completedSignatures,
      meta: 'All time (demo)',
    },
    { label: 'Tax Documents', value: summary.taxDocuments, meta: 'K-1, 1099, W-9' },
    { label: 'Expiring Soon', value: summary.expiringSoon, meta: 'Within 30 days' },
    { label: 'Missing', value: summary.missingDocuments, meta: 'Required uploads' },
    {
      label: 'Storage Used',
      value: formatDocumentBytes(summary.storageUsedBytes),
      meta: 'Demo placeholder',
    },
  ];

  return (
    <section className="inv-docs__kpi-grid" aria-label="Document key performance indicators">
      {kpis.map((kpi) => (
        <InvestorKpiCard key={kpi.label} label={kpi.label} value={kpi.value} meta={kpi.meta} />
      ))}
    </section>
  );
}

export interface DocumentsHeaderProps {
  onOpenPreferences: () => void;
}

export function DocumentsHeader({ onOpenPreferences }: DocumentsHeaderProps) {
  return (
    <header className="inv-docs__header">
      <div>
        <h1 className="investor-page__title">Documents</h1>
        <p className="investor-page__subtitle">
          Investment documents, tax forms, agreements, and e-signatures — all in one place.
        </p>
      </div>
      <div className="inv-docs__header-actions">
        <Link href={'/investor/signatures' as Route} className="inv-docs__btn inv-docs__btn--secondary">
          Signatures
        </Link>
        <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={onOpenPreferences}>
          Preferences
        </button>
      </div>
    </header>
  );
}
