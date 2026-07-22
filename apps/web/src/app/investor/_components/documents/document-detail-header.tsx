'use client';

import Link from 'next/link';
import type { Route } from 'next';

import {
  DOCUMENT_CATEGORY_LABELS,
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
} from '../../_data/documents';
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
            <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={onArchive}>
              Archive
            </button>
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
          {DOCUMENT_STATUS_LABELS[doc.status]}
        </span>
        <span className="inv-docs__detail-badge">{DOCUMENT_CATEGORY_LABELS[doc.category]}</span>
        <span className="inv-docs__detail-badge">{DOCUMENT_TYPE_LABELS[doc.documentType]}</span>
        {!doc.isRead ? <span className="inv-docs__detail-badge inv-docs__detail-badge--new">Unread</span> : null}
      </div>
    </header>
  );
}

export function DocumentDetailMetadata({ document: doc }: { document: InvestorDocument }) {
  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-metadata-heading">
      <h2 id="doc-metadata-heading">Metadata</h2>
      <dl className="inv-docs__detail-dl">
        <div><dt>File Name</dt><dd>{doc.fileName}</dd></div>
        <div><dt>Format</dt><dd>{doc.fileType.toUpperCase()}</dd></div>
        <div><dt>Size</dt><dd>{formatDocumentBytes(doc.fileSizeBytes)}</dd></div>
        <div><dt>Pages</dt><dd>{doc.pageCount ?? '—'}</dd></div>
        <div><dt>Uploaded</dt><dd>{formatDocDate(doc.uploadedAt)}</dd></div>
        <div><dt>Updated</dt><dd>{formatDocDate(doc.updatedAt)}</dd></div>
        <div><dt>Access Level</dt><dd>{doc.accessLevel}</dd></div>
        {doc.taxYear ? <div><dt>Tax Year</dt><dd>{doc.taxYear}</dd></div> : null}
        {doc.expiresAt ? (
          <div><dt>Expires</dt><dd>{formatInvestorDate(doc.expiresAt)}</dd></div>
        ) : null}
        {doc.distributionStatementId ? (
          <div><dt>Statement ID</dt><dd>{doc.distributionStatementId}</dd></div>
        ) : null}
      </dl>
      <p className="inv-docs__detail-desc">{doc.description}</p>
    </section>
  );
}
