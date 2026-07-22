'use client';

import Link from 'next/link';
import type { Route } from 'next';

import type { InvestmentDetail } from '../../_data/investment-detail-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

const CATEGORY_LABELS: Record<string, string> = {
  subscription: 'Subscription',
  tax: 'Tax',
  financial: 'Financial',
  legal: 'Legal',
  report: 'Reports',
  insurance: 'Insurance',
};

export interface DocumentsSectionProps {
  detail: InvestmentDetail;
  onPlaceholderAction: (message: string) => void;
}

export function DocumentsSection({ detail, onPlaceholderAction }: DocumentsSectionProps) {
  const { documents } = detail;
  const byCategory = documents.reduce<Record<string, typeof documents>>((acc, doc) => {
    const cat = doc.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(doc);
    return acc;
  }, {});

  return (
    <section className="inv-detail-panel" aria-labelledby="documents-heading">
      <SectionHeader title="Documents" subtitle="Recent documents by category" />

      <div className="inv-detail-documents">
        {Object.entries(byCategory).map(([category, docs]) => (
          <div key={category} className="inv-detail-documents__category">
            <h3 className="inv-detail-documents__category-title">
              {CATEGORY_LABELS[category] ?? category}
            </h3>
            <ul className="inv-detail-documents__list">
              {docs.map((doc) => (
                <li key={doc.id} className="inv-detail-documents__item">
                  <div className="inv-detail-documents__info">
                    <span className="inv-detail-documents__icon" aria-hidden="true">
                      📄
                    </span>
                    <div>
                      <p className="inv-detail-documents__title">{doc.title}</p>
                      <p className="inv-detail-documents__meta">
                        <time dateTime={doc.date}>{formatInvestorDate(doc.date)}</time>
                        · {doc.format} · {doc.fileSize}
                      </p>
                    </div>
                  </div>
                  <div className="inv-detail-documents__actions">
                    <button
                      type="button"
                      className="inv-detail-documents__btn"
                      onClick={() => onPlaceholderAction(`Preview for "${doc.title}" coming soon.`)}
                    >
                      Preview
                    </button>
                    <button
                      type="button"
                      className="inv-detail-documents__btn inv-detail-documents__btn--primary"
                      onClick={() => onPlaceholderAction(`Download for "${doc.title}" coming soon.`)}
                    >
                      Download
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <Link href={'/investor/documents' as Route} className="inv-section-header__action inv-detail-documents__link">
        View all documents →
      </Link>
    </section>
  );
}
