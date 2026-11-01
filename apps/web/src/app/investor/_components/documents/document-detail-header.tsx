'use client';

import { useTranslations } from 'next-intl';

import { investorChrome, investorLabel } from '@/app/investor/_components/investor-labels';
import Link from 'next/link';
import type { Route } from 'next';

import type { InvestorDocument } from '../../_data/document-types';
import { formatInvestorDate } from '../../_data/mock-data';

function formatDocDate(iso: string): string {
  return formatInvestorDate(iso.split('T')[0] ?? iso);
}
import { formatDocumentBytes } from '../../_data/document-calculations';

export interface DocumentDetailHeaderProps {
  document: InvestorDocument;
  onPreview: () => void;
  onDownload: () => void;
  onArchive: () => void;
}

export function DocumentDetailHeader({
  document: doc,
  onPreview,
  onDownload,
  onArchive,
}: DocumentDetailHeaderProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  return (
    <header className="inv-docs__detail-header">
      <Link href={'/investor/documents' as Route} className="inv-docs__back-link">
        ← Back to Documents
      </Link>
      <div className="inv-docs__detail-header-main">
        <div>
          <h1>{doc.title}</h1>
          <p>
            {doc.investmentName} · {doc.entityName}
          </p>
        </div>
        <div className="inv-docs__detail-actions">
          <button type="button" className="inv-docs__btn inv-docs__btn--secondary" onClick={onPreview}>
            Preview
          </button>
          <button type="button" className="inv-docs__btn inv-docs__btn--secondary" onClick={onDownload}>
            Download
          </button>
          {!doc.isArchived ? (
            <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={onArchive}>{investorChrome(tChrome, "Archive")}</button>
          ) : null}
          {doc.signatureRequestId && doc.requiresSignature ? (
            <Link
              href={`/investor/signatures/${doc.signatureRequestId}` as Route}
              className="inv-docs__btn inv-docs__btn--primary"
            >
              Review & Sign
            </Link>
          ) : null}
        </div>
      </div>
      <div className="inv-docs__detail-badges">
        <span className={`inv-docs__status inv-docs__status--${doc.status}`}>
          {investorLabel(tLabels, 'documentStatus', doc.status)}
        </span>
        <span className="inv-docs__detail-badge">{investorLabel(tLabels, 'documentCategory', doc.category)}</span>
        <span className="inv-docs__detail-badge">{investorLabel(tLabels, 'documentType', doc.documentType)}</span>
        {!doc.isRead ? <span className="inv-docs__detail-badge inv-docs__detail-badge--new">{tChrome('k07b032b56f')}</span> : null}
      </div>
    </header>
  );
}

export function DocumentDetailMetadata({ document: doc }: { document: InvestorDocument }) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-metadata-heading">
      <h2 id="doc-metadata-heading">{tChrome('k251edc0eb5')}</h2>
      <dl className="inv-docs__detail-dl">
        <div><dt>{tChrome('k2aabcfc266')}</dt><dd>{doc.fileName}</dd></div>
        <div><dt>{tChrome('k041a5dec48')}</dt><dd>{doc.fileType.toUpperCase()}</dd></div>
        <div><dt>{tChrome('kb7152342a2')}</dt><dd>{formatDocumentBytes(doc.fileSizeBytes)}</dd></div>
        <div><dt>{tChrome('k600584c2d5')}</dt><dd>{doc.pageCount ?? '—'}</dd></div>
        <div><dt>{tChrome('k80c494898a')}</dt><dd>{formatDocDate(doc.uploadedAt)}</dd></div>
        <div><dt>{tChrome('kf2f8570ddd')}</dt><dd>{formatDocDate(doc.updatedAt)}</dd></div>
        <div><dt>{tChrome('k2cdd20a60b')}</dt><dd>{doc.accessLevel}</dd></div>
        {doc.taxYear ? <div><dt>{tChrome('kc80ec709bc')}</dt><dd>{doc.taxYear}</dd></div> : null}
        {doc.expiresAt ? (
          <div><dt>{tChrome('ka99be3da0c')}</dt><dd>{formatInvestorDate(doc.expiresAt)}</dd></div>
        ) : null}
        {doc.distributionStatementId ? (
          <div><dt>{tChrome('ka0ff2d9d9a')}</dt><dd>{doc.distributionStatementId}</dd></div>
        ) : null}
      </dl>
      <p className="inv-docs__detail-desc">{doc.description}</p>
    </section>
  );
}
