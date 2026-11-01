'use client';

import { useTranslations } from 'next-intl';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import { getAllDocumentRequirements, } from '../../_data/document-requirements';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export function MissingDocumentsSection() {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  const requirements = getAllDocumentRequirements().filter(
    (r) => r.status === 'missing' || r.status === 'expired' || r.status === 'pending_review',
  );

  return (
    <section className="inv-docs__missing" id="missing-documents" aria-labelledby="missing-docs-heading">
      <SectionHeader
        title={tChrome('k6ae39d9138')}
        subtitle={`${requirements.length} items need your attention`}
      />
      {requirements.length === 0 ? (
        <p className="inv-docs__missing-empty">{tChrome('k18bb9c05b9')}</p>
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
                {investorLabel(tLabels, 'requirementStatus', req.status)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
