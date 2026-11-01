'use client';

import { investorChrome } from '@/app/investor/_components/investor-labels';

import { useTranslations } from 'next-intl';

import Link from 'next/link';
import type { Route } from 'next';

import type { SignatureSummaryKpis } from '../../_data/document-types';
import { InvestorKpiCard } from '../kpi-card';

export function SignatureKpiRow({ summary }: { summary: SignatureSummaryKpis }) {
  const tChrome = useTranslations('investorPortal.chrome');
  const kpis = [
    { label: 'Action Required', value: summary.actionRequired },
    { label: 'Waiting on Others', value: summary.waitingOnOthers },
    { label: 'Completed', value: summary.completed },
    { label: 'Declined', value: summary.declined },
    { label: 'Expired', value: summary.expired },
    { label: 'Voided', value: summary.voided },
    { label: 'Total Requests', value: summary.total },
  ];

  return (
    <section className="inv-sig__kpi-grid" aria-label={tChrome('k971c88eaf0')}>
      {kpis.map((kpi) => (
        <InvestorKpiCard key={kpi.label} label={kpi.label} value={kpi.value} />
      ))}
    </section>
  );
}

export function SignaturesHeader() {
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <header className="inv-sig__header">
      <div>
        <h1 className="investor-page__title">{tChrome('k5c67f8ce7c')}</h1>
        <p className="investor-page__subtitle">
          Review, sign, and track document signature requests across your portfolio.
        </p>
      </div>
      <Link href={'/investor/documents' as Route} className="inv-docs__btn inv-docs__btn--secondary">{investorChrome(tChrome, "Document Library")}</Link>
    </header>
  );
}
