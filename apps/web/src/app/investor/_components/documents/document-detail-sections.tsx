'use client';

import { useTranslations } from 'next-intl';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import Link from 'next/link';
import type { Route } from 'next';

import type { InvestorDocument } from '../../_data/document-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { formatDocumentBytes } from '../../_data/document-calculations';

function formatDocDate(iso: string): string {
  return formatInvestorDate(iso.split('T')[0] ?? iso);
}

export function DocumentDetailVersions({ document: doc }: { document: InvestorDocument }) {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-versions-heading">
      <h2 id="doc-versions-heading">{tChrome('ka239107ef2')}</h2>
      <ul className="inv-docs__versions-list">
        {doc.versions.map((v) => (
          <li key={v.id} className={v.isCurrent ? 'inv-docs__version--current' : undefined}>
            <div>
              <strong>v{v.versionNumber}</strong>
              {v.isCurrent ? <span className="inv-docs__version-current">{tChrome('k4fc0e2bc80')}</span> : null}
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
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-activity-heading">
      <h2 id="doc-activity-heading">{tChrome('k81c0d915fa')}</h2>
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
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  if (relatedDocuments.length === 0) return null;

  return (
    <section className="inv-docs__detail-panel" aria-labelledby="doc-related-heading">
      <h2 id="doc-related-heading">{tChrome('kcaa53feb7f')}</h2>
      <ul className="inv-docs__related-list">
        {relatedDocuments.map((rel) => (
          <li key={rel.id}>
            <Link href={`/investor/documents/${rel.id}` as Route}>
              {rel.title}
            </Link>
            <span>{investorLabel(tLabels, 'documentType', rel.documentType)}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function DocumentNotFound() {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="inv-docs__not-found">
      <h1>{tChrome('k2a39b0c130')}</h1>
      <p>{tChrome('ka75b36e735')}</p>
      <Link href={'/investor/documents' as Route} className="inv-docs__btn inv-docs__btn--primary">
        Back to Documents
      </Link>
    </div>
  );
}
