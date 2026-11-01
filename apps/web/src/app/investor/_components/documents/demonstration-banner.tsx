'use client';

import { useTranslations } from 'next-intl';

import { investorChrome } from '@/app/investor/_components/investor-labels';
import { DEMONSTRATION_DISCLAIMER } from '../../_data/document-types';

const DEMO_BODY =
  'All signatures, certificates, and document actions in this workspace are simulated for demonstration purposes only. No legally binding agreements are created.';

export function DemonstrationBanner({ compact = false }: { compact?: boolean }) {
  const tChrome = useTranslations('investorPortal.chrome');
  const title = investorChrome(tChrome, DEMONSTRATION_DISCLAIMER);
  return (
    <div
      className={`inv-docs__demo-banner${compact ? ' inv-docs__demo-banner--compact' : ''}`}
      role="note"
      aria-label={title}
    >
      <span className="inv-docs__demo-banner-icon" aria-hidden="true">
        ⚠
      </span>
      <div>
        <strong>{title}</strong>
        {!compact ? <p>{investorChrome(tChrome, DEMO_BODY)}</p> : null}
      </div>
    </div>
  );
}
