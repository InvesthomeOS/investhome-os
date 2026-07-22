'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { formatDocumentBytes } from '../../_data/document-calculations';
import {
  DOCUMENT_CATEGORY_LABELS,
  DOCUMENT_STATUS_LABELS,
} from '../../_data/documents';
import type { InvestorDocument } from '../../_data/document-types';
import { formatInvestorDate } from '../../_data/mock-data';

function formatDocDate(iso: string): string {
  return formatInvestorDate(iso.split('T')[0] ?? iso);
}

const FILE_ICONS: Record<string, string> = {
  pdf: '📕',
  docx: '📘',
  xlsx: '📗',
  png: '🖼',
  jpg: '🖼',
  csv: '📊',
  zip: '📦',
};

export interface DocumentGridProps {
  documents: InvestorDocument[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onPreview: (doc: InvestorDocument) => void;
  onDownload: (doc: InvestorDocument) => void;
}

export function DocumentGrid({
  documents,
  selectedIds,
  onToggleSelect,
  onPreview,
  onDownload,
}: DocumentGridProps) {
  return (
    <div className="inv-docs__grid">
      {documents.map((doc) => (
        <article
          key={doc.id}
          className={`inv-docs__grid-card${!doc.isRead ? ' inv-docs__grid-card--unread' : ''}`}
        >
          <div className="inv-docs__grid-card-top">
            <span className="inv-docs__grid-icon" aria-hidden="true">
              {FILE_ICONS[doc.fileType] ?? '📄'}
            </span>
            <input
              type="checkbox"
              checked={selectedIds.includes(doc.id)}
              onChange={() => onToggleSelect(doc.id)}
              aria-label={`Select ${doc.title}`}
            />
          </div>
          <Link href={`/investor/documents/${doc.id}` as Route} className="inv-docs__grid-title">
            {doc.title}
          </Link>
          <p className="inv-docs__grid-sub">{doc.investmentName}</p>
          <div className="inv-docs__grid-meta">
            <span>{DOCUMENT_CATEGORY_LABELS[doc.category]}</span>
            <span className={`inv-docs__status inv-docs__status--${doc.status}`}>
              {DOCUMENT_STATUS_LABELS[doc.status]}
            </span>
          </div>
          <p className="inv-docs__grid-date">
            {formatDocDate(doc.uploadedAt)} · {formatDocumentBytes(doc.fileSizeBytes)}
          </p>
          <div className="inv-docs__grid-actions">
            <button type="button" onClick={() => onPreview(doc)}>
              Preview
            </button>
            <button type="button" onClick={() => onDownload(doc)}>
              Download
            </button>
          </div>
        </article>
      ))}
    </div>
  );
}
