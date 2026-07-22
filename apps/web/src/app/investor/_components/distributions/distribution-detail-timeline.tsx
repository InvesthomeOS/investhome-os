'use client';

import type { Distribution } from '../../_data/distribution-types';
import { PAYMENT_METHOD_LABELS, PAYMENT_STATUS_LABELS } from '../../_data/distributions';
import { formatInvestorDate } from '../../_data/mock-data';
import { SectionHeader } from '../section-header';

export interface DistributionDetailTimelineProps {
  distribution: Distribution;
}

export function DistributionDetailTimeline({ distribution: d }: DistributionDetailTimelineProps) {
  return (
    <section className="inv-distributions__panel">
      <SectionHeader title="Payment Status Timeline" subtitle="Distribution lifecycle stages" />

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
                <span className="inv-distributions__payment-pending">Pending</span>
              )}
            </div>
          </li>
        ))}
      </ol>

      <dl className="inv-distributions__payment-meta">
        <div>
          <dt>Payment Method</dt>
          <dd>{PAYMENT_METHOD_LABELS[d.paymentMethod]}</dd>
        </div>
        <div>
          <dt>Payment Status</dt>
          <dd>{PAYMENT_STATUS_LABELS[d.paymentStatus]}</dd>
        </div>
        <div>
          <dt>Declared</dt>
          <dd>{formatInvestorDate(d.declaredDate)}</dd>
        </div>
        <div>
          <dt>Record Date</dt>
          <dd>{formatInvestorDate(d.recordDate)}</dd>
        </div>
      </dl>
    </section>
  );
}
