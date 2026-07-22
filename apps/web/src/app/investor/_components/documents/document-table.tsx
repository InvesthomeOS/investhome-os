'use client';

import Link from 'next/link';
import type { Route } from 'next';

import { formatDocumentBytes } from '../../_data/document-calculations';
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

export interface DocumentTableProps {
  documents: InvestorDocument[];
  selectedIds: string[];
  onToggleSelect: (id: string) => void;
  onSelectAll: (ids: string[]) => void;
  onPreview: (doc: InvestorDocument) => void;
  onDownload: (doc: InvestorDocument) => void;
}

export function DocumentTable({
  documents,
  selectedIds,
  onToggleSelect,
  onSelectAll,
  onPreview,
  onDownload,
}: DocumentTableProps) {
  const allSelected = documents.length > 0 && documents.every((d) => selectedIds.includes(d.id));

  return (
    <div className="inv-docs__table-wrap">
      <table className="inv-docs__table">
        <thead>
          <tr>
            <th scope="col" className="inv-docs__table-check">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() =>
                  onSelectAll(allSelected ? [] : documents.map((d) => d.id))
                }
                aria-label="Select all documents"
              />
            </th>
            <th scope="col">Document</th>
            <th scope="col">Investment</th>
            <th scope="col">Category</th>
            <th scope="col">Status</th>
            <th scope="col">Date</th>
            <th scope="col">Size</th>
            <th scope="col">Actions</th>
          </tr>
        </thead>
        <tbody>
          {documents.map((doc) => (
            <tr
              key={doc.id}
              className={!doc.isRead ? 'inv-docs__table-row--unread' : undefined}
            >
              <td>
                <input
                  type="checkbox"
                  checked={selectedIds.includes(doc.id)}
                  onChange={() => onToggleSelect(doc.id)}
                  aria-label={`Select ${doc.title}`}
                />
              </td>
              <td>
                <Link href={`/investor/documents/${doc.id}` as Route} className="inv-docs__doc-link">
                  {!doc.isRead ? <span className="inv-docs__unread-dot" aria-label="Unread" /> : null}
                  <span>{doc.title}</span>
                </Link>
                <span className="inv-docs__doc-meta">{DOCUMENT_TYPE_LABELS[doc.documentType]}</span>
              </td>
              <td>{doc.investmentName}</td>
              <td>{DOCUMENT_CATEGORY_LABELS[doc.category]}</td>
              <td>
                <span className={`inv-docs__status inv-docs__status--${doc.status}`}>
                  {DOCUMENT_STATUS_LABELS[doc.status]}
                </span>
              </td>
              <td>
                <time dateTime={doc.uploadedAt}>{formatDocDate(doc.uploadedAt)}</time>
              </td>
              <td>{formatDocumentBytes(doc.fileSizeBytes)}</td>
              <td>
                <div className="inv-docs__row-actions">
                  <button type="button" onClick={() => onPreview(doc)}>
                    Preview
                  </button>
                  <button type="button" onClick={() => onDownload(doc)}>
                    Download
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
