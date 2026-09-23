'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';

const MODULE_KEYS: Record<string, string> = {
  executive: 'modules.executive.title',
  leads: 'modules.leads.title',
  sales: 'modules.sales.title',
  investors: 'modules.investors.title',
  projects: 'modules.projects.title',
  inventory: 'modules.inventory.title',
  marketing: 'modules.marketing.title',
  finance: 'modules.finance.title',
  documents: 'documents',
  design: 'designStudio',
  activity: 'activity',
  settings: 'settings',
  profile: 'profile',
  admin: 'adminSection',
  analytics: 'businessIntelligence',
  ai: 'aiWorkspace',
  automation: 'automation',
  knowledge: 'documents',
};

const CRM_SEGMENT_KEYS: Record<string, string> = {
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
  tags: 'nav.tags',
  communication: 'nav.communication',
  documents: 'nav.documents',
  files: 'nav.documents',
  reports: 'nav.reports',
  settings: 'nav.settings',
};

function humanize(segment: string): string {
  return segment
    .split('-')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function Breadcrumbs() {
  const pathname = usePathname();
  const t = useTranslations('navigation');
  const tCrm = useTranslations('crm');
  const tProfile = useTranslations('profile');

  const segments = pathname.split('/').filter(Boolean);

  if (segments.length <= 1) {
    return null;
  }

  const crumbs: { href: Route; label: string }[] = [
    { href: '/dashboard' as Route, label: t('mainMenu') },
  ];

  // /workspaces/crm/... or /workspaces/marketing/...
  if (segments[0] === 'workspaces' && segments[1]) {
    const workspaceId = segments[1];
    const workspaceHref =
      workspaceId === 'marketing'
        ? ('/dashboard/marketing' as Route)
        : workspaceId === 'crm'
          ? ('/workspaces/crm/dashboard' as Route)
          : workspaceId === 'creative-studio'
            ? ('/workspaces/creative-studio' as Route)
            : (`/workspaces/${workspaceId}/dashboard` as Route);
    const workspaceLabel =
      workspaceId === 'crm'
        ? t('modules.crm.title')
        : workspaceId === 'marketing'
          ? t('modules.marketing.title')
          : humanize(workspaceId);
    crumbs.push({ href: workspaceHref, label: workspaceLabel });

    if (segments[2] && segments[2] !== 'dashboard') {
      const crmKey = workspaceId === 'crm' ? CRM_SEGMENT_KEYS[segments[2]] : null;
      crumbs.push({
        href: pathname as Route,
        label: crmKey ? tCrm(crmKey as 'nav.dashboard') : humanize(segments[2]),
      });
    }
  } else if (segments[0] === 'company') {
    crumbs.push({ href: '/company' as Route, label: t('modules.company.title') });
    if (segments[1] && segments[1] !== 'overview') {
      crumbs.push({ href: pathname as Route, label: humanize(segments[1]) });
    }
  } else if (segments[0] === 'dashboard') {
    if (segments[1] === 'admin') {
      crumbs.push({ href: '/dashboard/admin' as Route, label: t('adminSection') });
      const adminKey = segments[2];
      if (adminKey === 'users') {
        crumbs.push({ href: pathname as Route, label: t('admin.users') });
      } else if (adminKey === 'roles') {
        crumbs.push({ href: pathname as Route, label: t('admin.roles') });
      } else if (adminKey === 'permissions') {
        crumbs.push({ href: pathname as Route, label: t('admin.permissions') });
      }
    } else if (segments[1]) {
      const moduleKey = segments[1];
      const navKey = MODULE_KEYS[moduleKey];
      let label = moduleKey;

      if (moduleKey === 'profile') {
        label = tProfile('title');
      } else if (navKey) {
        label = t(navKey as 'documents');
      }

      crumbs.push({
        href: (`/dashboard/${moduleKey}`) as Route,
        label,
      });

      if (segments[2] && moduleKey === 'design') {
        crumbs.push({ href: pathname as Route, label: t('designStudio') });
      } else if (segments[2] && moduleKey !== 'admin') {
        crumbs.push({ href: pathname as Route, label: humanize(segments[2]) });
      }
    }
  }

  if (crumbs.length <= 1) {
    return null;
  }

  return (
    <nav className="app-breadcrumbs" aria-label={t('breadcrumbs')}>
      <ol className="app-breadcrumbs__list">
        {crumbs.map((crumb, index) => {
          const isLast = index === crumbs.length - 1;
          return (
            <li key={`${crumb.href}-${index}`} className="app-breadcrumbs__item">
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
