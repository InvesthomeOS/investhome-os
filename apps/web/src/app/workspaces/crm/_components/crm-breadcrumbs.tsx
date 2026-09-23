'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

const SEGMENT_KEYS: Record<string, string> = {
  workspaces: 'title',
  crm: 'title',
  dashboard: 'nav.dashboard',
  leads: 'nav.leads',
  pipeline: 'nav.pipeline',
  matches: 'nav.matches',
  contacts: 'nav.contacts',
  people: 'nav.contacts',
  junk: 'nav.junk',
  agents: 'nav.agents',
  agreements: 'nav.agreements',
  companies: 'nav.companies',
  investors: 'nav.investors',
  relationships: 'nav.relationships',
  timeline: 'nav.timeline',
  activities: 'nav.activities',
  tasks: 'nav.tasks',
  calendar: 'nav.calendar',
  notes: 'nav.notes',
  files: 'nav.documents',
  tags: 'nav.tags',
  communication: 'nav.communication',
  documents: 'nav.documents',
  reports: 'nav.reports',
  settings: 'nav.settings',
};

export function CrmBreadcrumbs() {
  const pathname = usePathname();
  const t = useTranslations('crm');
  const tCommon = useTranslations('common');

  const segments = pathname.split('/').filter(Boolean);
  const crmIndex = segments.indexOf('crm');
  if (crmIndex === -1) {
    return null;
  }

  const crumbs: { href: Route; label: string }[] = [
    { href: '/workspaces/crm/dashboard' as Route, label: t('title') },
  ];

  const section = segments[crmIndex + 1];
  if (section && section !== 'dashboard') {
    const key = SEGMENT_KEYS[section];
    crumbs.push({
      href: pathname as Route,
      label: key ? t(key as 'nav.dashboard') : section,
    });
  }

  if (crumbs.length <= 1) {
    return null;
  }

  return (
    <nav className="app-breadcrumbs" aria-label={tCommon('appName')}>
      <ol className="app-breadcrumbs__list">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <li key={crumb.href} className="app-breadcrumbs__item">
              {isLast ? (
                <span className="app-breadcrumbs__current" aria-current="page">
                  {crumb.label}
                </span>
              ) : (
                <Link href={crumb.href} className="app-breadcrumbs__link">
                  {crumb.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
