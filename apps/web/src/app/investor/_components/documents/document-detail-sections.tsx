'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { InvestorDocument } from '../../_data/document-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { formatDocumentBytes } from '../../_data/document-calculations';
import { DOCUMENT_TYPE_LABELS } from '../../_data/documents';

function formatDocDate(iso: string): string {
  return formatInvestorDate(iso.split('T')[0] ?? iso);
}

export function DocumentDetailVersions({ document: doc }: { document: InvestorDocument }) {
  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-versions-heading">
      <h2 id="doc-versions-heading">Versions</h2>
      <ul className="inv-docs__versions-list">
        {doc.versions.map((v) => (
          <li key={v.id} className={v.isCurrent ? 'inv-docs__version--current' : undefined}>
            <div>
              <strong>v{v.versionNumber}</strong>
              {v.isCurrent ? <span className="inv-docs__version-current">Current</span> : null}
            </div>
            <span>{formatDocDate(v.uploadedAt)} · {formatDocumentBytes(v.fileSizeBytes)}</span>
            {v.changeNotes ? <p>{v.changeNotes}</p> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DocumentDetailActivity({ document: doc }: { document: InvestorDocument }) {
  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-activity-heading">
      <h2 id="doc-activity-heading">Activity</h2>
      <ol className="inv-docs__activity-list">
        {doc.activity.map((a) => (
          <li key={a.id}>
            <time dateTime={a.timestamp}>{formatDocDate(a.timestamp)}</time>
            <strong>{a.action}</strong>
            <span>{a.description}</span>
            <span className="inv-docs__activity-actor">{a.actor}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export interface DocumentDetailRelatedProps {
  document: InvestorDocument;
  relatedDocuments: InvestorDocument[];
}

export function DocumentDetailRelated({ relatedDocuments }: DocumentDetailRelatedProps) {
  if (relatedDocuments.length === 0) return null;

  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-related-heading">
      <h2 id="doc-related-heading">Related Documents</h2>
      <ul className="inv-docs__related-list">
        {relatedDocuments.map((rel) => (
          <li key={rel.id}>
            <Link href={`/investor/documents/${rel.id}` as Route}>
              {rel.title}
            </Link>
            <span>{DOCUMENT_TYPE_LABELS[rel.documentType]}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DocumentNotFound() {
  return (
    <div className="inv-docs__not-found">
      <h1>Document Not Found</h1>
      <p>The document you are looking for does not exist or may have been removed.</p>
      <Link href={'/investor/documents' as Route} className="inv-docs__btn inv-docs__btn--primary">
        Back to Documents
      </Link>
    </div>
  );
}
