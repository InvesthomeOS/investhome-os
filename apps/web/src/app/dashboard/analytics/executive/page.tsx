'use client';

import { BiDomainPage } from '../_components/bi-domain-page';

/** G14 path alias — same executive domain as /dashboard/analytics */
export default function AnalyticsExecutiveAliasPage() {
  return (
    <BiDomainPage
      domain="executive"
      titleKey="pages.executive.title"
      subtitleKey="pages.executive.subtitle"
    />
  );
}
