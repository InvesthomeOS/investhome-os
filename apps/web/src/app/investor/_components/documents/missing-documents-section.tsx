'use client';

import { getAllDocumentRequirements, REQUIREMENT_STATUS_LABELS } from '../../_data/document-requirements';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export function MissingDocumentsSection() {
  const requirements = getAllDocumentRequirements().filter(
    (r) => r.status === 'missing' || r.status === 'expired' || r.status === 'pending_review',
  );

  return (
    <section className="inv-docs__missing" id="missing-documents" aria-labelledby="missing-docs-heading">
      <SectionHeader
        title="Missing Documents"
        subtitle={`${requirements.length} items need your attention`}
      />
      {requirements.length === 0 ? (
        <p className="inv-docs__missing-empty">All required documents are on file.</p>
      ) : (
        <ul className="inv-docs__missing-list">
          {requirements.map((req) => (
            <li key={req.id} className={`inv-docs__missing-item inv-docs__missing-item--${req.priority}`}>
              <div>
                <h3>{req.title}</h3>
                <p>{req.description}</p>
                <p className="inv-docs__missing-meta">
                  {req.investmentName ?? 'Account-level'} · Due {formatInvestorDate(req.dueDate)}
                </p>
              </div>
              <span className={`inv-docs__req-status inv-docs__req-status--${req.status}`}>
                {REQUIREMENT_STATUS_LABELS[req.status]}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
