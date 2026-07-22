'use client';

import { use, useCallback, useEffect, useState } from 'react';

import { DistributionDetailBreakdown } from '../../_components/distributions/distribution-detail-breakdown';
import { DistributionDetailHeader } from '../../_components/distributions/distribution-detail-header';
import { DistributionDetailTimeline } from '../../_components/distributions/distribution-detail-timeline';
import { DistributionNotFound } from '../../_components/distributions/distribution-not-found';
import { getDistributionById } from '../../_data/distribution-calculations';
import { LoadingSkeleton } from '../../_components/loading-skeleton';

interface DistributionDetailPageProps {
  params: Promise<{ distributionId: string }>;
}

export default function DistributionDetailPage({ params }: DistributionDetailPageProps) {
  const { distributionId } = use(params);
  const [isLoading, setIsLoading] = useState(true);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const distribution = getDistributionById(distributionId);

  useEffect(() => {
    const timer = window.setTimeout(() => setIsLoading(false), 300);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!toastMessage) return;
    const timer = window.setTimeout(() => setToastMessage(null), 3200);
    return () => window.clearTimeout(timer);
  }, [toastMessage]);

  const showToast = useCallback((message: string) => setToastMessage(message), []);

  if (isLoading) {
    return (
      <div className="investor-page inv-distributions">
        <LoadingSkeleton variant="title" />
        <LoadingSkeleton variant="card" count={2} />
      </div>
    );
  }

  if (!distribution) {
    return <DistributionNotFound />;
  }

  return (
    <div className="investor-page inv-distributions inv-distributions--detail">
      <DistributionDetailHeader
        distribution={distribution}
        onDownloadStatement={() => showToast('Statement download coming soon.')}
        onContactIr={() => showToast('Investor Relations contact form coming soon.')}
        onReportIssue={() => showToast('Issue report submitted (mock).')}
      />

      <div className="inv-distributions__detail-grid">
        <DistributionDetailBreakdown distribution={distribution} />
        <DistributionDetailTimeline distribution={distribution} />
      </div>

      {toastMessage ? (
        <div className="inv-investments__toast" role="status">
          {toastMessage}
        </div>
      ) : null}
    </div>
  );
}
