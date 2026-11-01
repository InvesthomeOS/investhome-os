'use client';

import { useTranslations } from 'next-intl';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import Link from 'next/link';
import type { Route } from 'next';

import { formatDocumentBytes } from '../../_data/document-calculations';
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
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
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
                aria-label={tChrome('k6697d5e578')}
              />
            </th>
            <th scope="col">{tChrome('ke214b8a299')}</th>
            <th scope="col">{tChrome('k0401729c31')}</th>
            <th scope="col">{tChrome('ka3c686e711')}</th>
            <th scope="col">{tChrome('kbae7d5be70')}</th>
            <th scope="col">{tChrome('keb9a4bc1c0')}</th>
            <th scope="col">{tChrome('kb7152342a2')}</th>
            <th scope="col">{tChrome('kc3cd636a58')}</th>
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
                  {!doc.isRead ? <span className="inv-docs__unread-dot" aria-label={tChrome('k07b032b56f')} /> : null}
                  <span>{doc.title}</span>
                </Link>
                <span className="inv-docs__doc-meta">{investorLabel(tLabels, 'documentType', doc.documentType)}</span>
              </td>
              <td>{doc.investmentName}</td>
              <td>{investorLabel(tLabels, 'documentCategory', doc.category)}</td>
              <td>
                <span className={`inv-docs__status inv-docs__status--${doc.status}`}>
                  {investorLabel(tLabels, 'documentStatus', doc.status)}
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
