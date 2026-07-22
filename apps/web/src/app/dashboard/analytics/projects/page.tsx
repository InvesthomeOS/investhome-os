'use client';

import { BiDomainPage } from '../_components/bi-domain-page';

/** G14 path alias for /dashboard/analytics/project */
export default function AnalyticsProjectsAliasPage() {
  return (
    <BiDomainPage
      domain="project"
      titleKey="pages.project.title"
      subtitleKey="pages.project.subtitle"
    />
  );
}
