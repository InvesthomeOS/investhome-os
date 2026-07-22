'use client';

import { useEffect, useRef } from 'react';

import { formatDocumentBytes } from '../../_data/document-calculations';
import {
  DOCUMENT_CATEGORY_LABELS,
  DOCUMENT_TYPE_LABELS,
} from '../../_data/documents';
import type { InvestorDocument } from '../../_data/document-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { sanitizePlainText } from '../../_utils/sanitize-text';

function formatDocDate(iso: string): string {
  return formatInvestorDate(iso.split('T')[0] ?? iso);
}

export interface DocumentPreviewProps {
  document: InvestorDocument | null;
  open: boolean;
  onClose: () => void;
  onDownload: (doc: InvestorDocument) => void;
  onMarkRead: (id: string) => void;
}

function MockPdfPreview({ doc }: { doc: InvestorDocument }) {
  const pages = doc.pageCount ?? 3;
  return (
    <div className="inv-docs__preview-pdf">
      {Array.from({ length: Math.min(pages, 4) }, (_, i) => (
        <div key={i} className="inv-docs__preview-page">
          <div className="inv-docs__preview-page-header">
            <span>{doc.fileName}</span>
            <span>Page {i + 1} of {pages}</span>
          </div>
          <div className="inv-docs__preview-page-body">
            <h4>{sanitizePlainText(doc.title)}</h4>
            <p>{sanitizePlainText(doc.description)}</p>
            <div className="inv-docs__preview-mock-lines">
              {Array.from({ length: 8 }, (__, j) => (
                <div key={j} className="inv-docs__preview-line" style={{ width: `${60 + (j % 3) * 12}%` }} />
              ))}
            </div>
            {i === 0 ? (
              <p className="inv-docs__preview-demo-note">
                Mock preview — actual document content is not rendered in this demonstration.
              </p>
            ) : null}
          </div>
        </div>
      ))}
      {pages > 4 ? (
        <p className="inv-docs__preview-more">+ {pages - 4} additional pages (demo placeholder)</p>
      ) : null}
    </div>
  );
}

function MockImagePreview({ doc }: { doc: InvestorDocument }) {
  return (
    <div className="inv-docs__preview-image">
      <div className="inv-docs__preview-image-placeholder" role="img" aria-label={`Image preview of ${doc.title}`}>
        <span aria-hidden="true">🖼</span>
        <p>{sanitizePlainText(doc.title)}</p>
        <p className="inv-docs__preview-demo-note">Image preview placeholder</p>
      </div>
    </div>
  );
}

function MockSpreadsheetPreview({ doc }: { doc: InvestorDocument }) {
  const rows = ['Investment', 'Period', 'Amount', 'Status'];
  return (
    <div className="inv-docs__preview-sheet">
      <table>
        <thead>
          <tr>
            {rows.map((h) => (
              <th key={h} scope="col">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {['Q1 2025', 'Q2 2025', 'Q3 2025'].map((period) => (
            <tr key={period}>
              <td>{sanitizePlainText(doc.investmentName)}</td>
              <td>{period}</td>
              <td>—</td>
              <td>Demo</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="inv-docs__preview-demo-note">Spreadsheet preview placeholder</p>
    </div>
  );
}

function MockContent({ doc }: { doc: InvestorDocument }) {
  if (doc.fileType === 'pdf') return <MockPdfPreview doc={doc} />;
  if (doc.fileType === 'png' || doc.fileType === 'jpg') return <MockImagePreview doc={doc} />;
  if (doc.fileType === 'xlsx' || doc.fileType === 'csv') return <MockSpreadsheetPreview doc={doc} />;
  return (
    <div className="inv-docs__preview-generic">
      <p>{sanitizePlainText(doc.description)}</p>
      <p className="inv-docs__preview-demo-note">
        Preview not available for .{doc.fileType} in demo mode.
      </p>
    </div>
  );
}

export function DocumentPreview({
  document: doc,
  open,
  onClose,
  onDownload,
  onMarkRead,
}: DocumentPreviewProps) {
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open || !doc) return;
    onMarkRead(doc.id);
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, doc, onClose, onMarkRead]);

  if (!open || !doc) return null;

  return (
    <div
      className="inv-docs__preview-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="doc-preview-title"
      ref={dialogRef}
    >
      <div className="inv-docs__preview-drawer">
        <header className="inv-docs__preview-header">
          <div>
            <h2 id="doc-preview-title">{sanitizePlainText(doc.title)}</h2>
            <p>
              {doc.investmentName} · {DOCUMENT_TYPE_LABELS[doc.documentType]} ·{' '}
              {formatDocumentBytes(doc.fileSizeBytes)}
            </p>
          </div>
          <div className="inv-docs__preview-header-actions">
            <button type="button" onClick={() => onDownload(doc)}>
              Download
            </button>
            <button type="button" onClick={onClose} aria-label="Close preview">
              ✕
            </button>
          </div>
        </header>

        <aside className="inv-docs__preview-sidebar">
          <dl className="inv-docs__preview-meta">
            <div>
              <dt>Category</dt>
              <dd>{DOCUMENT_CATEGORY_LABELS[doc.category]}</dd>
            </div>
            <div>
              <dt>Uploaded</dt>
              <dd>{formatDocDate(doc.uploadedAt)}</dd>
            </div>
            <div>
              <dt>Entity</dt>
              <dd>{sanitizePlainText(doc.entityName)}</dd>
            </div>
            {doc.taxYear ? (
              <div>
                <dt>Tax Year</dt>
                <dd>{doc.taxYear}</dd>
              </div>
            ) : null}
          </dl>
        </aside>

        <div className="inv-docs__preview-content">
          <MockContent doc={doc} />
        </div>
      </div>
      <button type="button" className="inv-docs__preview-backdrop" onClick={onClose} aria-label="Close preview" tabIndex={-1} />
    </div>
  );
}
