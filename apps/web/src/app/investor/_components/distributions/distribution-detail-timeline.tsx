'use client';

import { useTranslations } from 'next-intl';

import { investorLabel } from '@/app/investor/_components/investor-labels';
import type { Distribution } from '../../_data/distribution-types';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface DistributionDetailTimelineProps {
  distribution: Distribution;
}

export function DistributionDetailTimeline({ distribution: d }: DistributionDetailTimelineProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const tLabels = useTranslations('investorPortal.labels');
  return (
    <section className="inv-distributions__panel">
      <SectionHeader title={tChrome('k929027ea0c')} subtitle={tChrome('k62edab40f0')} />

      <ol className="inv-distributions__payment-timeline">
        {d.paymentTimeline.map((step) => (
          <li
            key={step.stage}
            className={`inv-distributions__payment-step${step.completed ? ' inv-distributions__payment-step--done' : ''}`}
          >
            <div className="inv-distributions__payment-step-marker" aria-hidden="true" />
            <div>
              <strong>{step.label}</strong>
              {step.date ? (
                <time dateTime={step.date}>{formatInvestorDate(step.date)}</time>
              ) : (
                <span className="inv-distributions__payment-pending">{tChrome('k96f608c16c')}</span>
              )}
            </div>
          </li>
        ))}
      </ol>

      <dl className="inv-distributions__payment-meta">
        <div>
          <dt>{tChrome('kf383f6a23c')}</dt>
          <dd>{investorLabel(tLabels, 'paymentMethod', d.paymentMethod)}</dd>
        </div>
        <div>
          <dt>{tChrome('k584e977886')}</dt>
          <dd>{investorLabel(tLabels, 'paymentStatus', d.paymentStatus)}</dd>
        </div>
        <div>
          <dt>{tChrome('k8df7435bef')}</dt>
          <dd>{formatInvestorDate(d.declaredDate)}</dd>
        </div>
        <div>
          <dt>{tChrome('ka05f5755ac')}</dt>
          <dd>{formatInvestorDate(d.recordDate)}</dd>
        </div>
      </dl>
    </section>
  );
}
