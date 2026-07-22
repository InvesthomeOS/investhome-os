'use client';

import { BiDomainPage } from '../_components/bi-domain-page';

/** G14 path alias for /dashboard/analytics/investor */
export default function AnalyticsInvestorsAliasPage() {
  return (
    <BiDomainPage
      domain="investor"
      titleKey="pages.investor.title"
      subtitleKey="pages.investor.subtitle"
    />
  );
}
