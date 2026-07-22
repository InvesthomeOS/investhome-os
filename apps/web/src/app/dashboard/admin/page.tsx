'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useEffect } from 'react';

import { PageHeader } from '@investhome/ui';

import { canViewRoles, canViewUsers, hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

type HubCard = {
  href: Route;
  titleKey: string;
  descriptionKey: string;
  visible: boolean;
};

export default function AdminOverviewPage() {
  const t = useTranslations('adminShell');
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    const canViewUsersPage = canViewUsers(user);
    const canViewRolesPage = canViewRoles(user);
    const canViewSecurity = hasPermission(user, 'security', 'view');
    if (!canViewUsersPage && !canViewRolesPage && !hasPermission(user, 'company', 'view') && !canViewSecurity) {
      router.replace('/forbidden');
    }
  }, [loading, router, user]);

  if (loading || !user) {
    return null;
  }

  const cards: HubCard[] = [
    {
      href: '/dashboard/admin/adoption' as Route,
      titleKey: 'nav.adoption',
      descriptionKey: 'cards.adoption',
      visible: canViewUsers(user) || hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/training-builder' as Route,
      titleKey: 'nav.trainingBuilder',
      descriptionKey: 'cards.trainingBuilder',
      visible: canViewUsers(user) || hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/operations' as Route,
      titleKey: 'nav.operations',
      descriptionKey: 'cards.operations',
      visible: canViewUsers(user) || hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/users' as Route,
      titleKey: 'nav.users',
      descriptionKey: 'cards.users',
      visible: canViewUsers(user),
    },
    {
      href: '/dashboard/admin/teams' as Route,
      titleKey: 'nav.teams',
      descriptionKey: 'cards.teams',
      visible: hasPermission(user, 'organization', 'view') || hasPermission(user, 'company', 'view'),
    },
    {
      href: '/dashboard/admin/roles' as Route,
      titleKey: 'nav.roles',
      descriptionKey: 'cards.roles',
      visible: canViewRoles(user),
    },
    {
      href: '/dashboard/admin/permissions' as Route,
      titleKey: 'nav.permissions',
      descriptionKey: 'cards.permissions',
      visible: canViewRoles(user),
    },
    {
      href: '/dashboard/admin/security' as Route,
      titleKey: 'nav.security',
      descriptionKey: 'cards.security',
      visible: hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/authentication' as Route,
      titleKey: 'nav.authentication',
      descriptionKey: 'cards.authentication',
      visible: hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/sessions' as Route,
      titleKey: 'nav.sessions',
      descriptionKey: 'cards.sessions',
      visible: hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/api-keys' as Route,
      titleKey: 'nav.apiKeys',
      descriptionKey: 'cards.apiKeys',
      visible: hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/secrets' as Route,
      titleKey: 'nav.secrets',
      descriptionKey: 'cards.secrets',
      visible: hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/audit' as Route,
      titleKey: 'nav.audit',
      descriptionKey: 'cards.audit',
      visible: hasPermission(user, 'activity', 'view') || hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/compliance' as Route,
      titleKey: 'nav.compliance',
      descriptionKey: 'cards.compliance',
      visible: hasPermission(user, 'security', 'view') || hasPermission(user, 'compliance', 'view'),
    },
    {
      href: '/dashboard/admin/incidents' as Route,
      titleKey: 'nav.incidents',
      descriptionKey: 'cards.incidents',
      visible: hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/platform' as Route,
      titleKey: 'nav.platform',
      descriptionKey: 'cards.platform',
      visible:
        hasPermission(user, 'platform', 'view') ||
        hasPermission(user, 'platform', 'manage') ||
        hasPermission(user, 'security', 'view'),
    },
    {
      href: '/dashboard/admin/system' as Route,
      titleKey: 'nav.system',
      descriptionKey: 'cards.system',
      visible: hasPermission(user, 'security', 'view') || hasPermission(user, 'settings', 'view'),
    },
    {
      href: '/dashboard/admin/launch-health' as Route,
      titleKey: 'nav.launchHealth',
      descriptionKey: 'cards.launchHealth',
      visible: hasPermission(user, 'security', 'view') || hasPermission(user, 'settings', 'view'),
    },
    {
      href: '/dashboard/settings?tab=company' as Route,
      titleKey: 'nav.company',
      descriptionKey: 'cards.company',
      visible: hasPermission(user, 'company', 'view'),
    },
    {
      href: '/dashboard/settings?tab=offices' as Route,
      titleKey: 'nav.offices',
      descriptionKey: 'cards.offices',
      visible: hasPermission(user, 'offices', 'view'),
    },
    {
      href: '/dashboard/settings?tab=organization' as Route,
      titleKey: 'nav.organization',
      descriptionKey: 'cards.organization',
      visible: hasPermission(user, 'organization', 'view'),
    },
    {
      href: '/dashboard/activity' as Route,
      titleKey: 'nav.activity',
      descriptionKey: 'cards.activity',
      visible: hasPermission(user, 'activity', 'view'),
    },
    {
      href: '/dashboard/settings?tab=notifications' as Route,
      titleKey: 'nav.notifications',
      descriptionKey: 'cards.notifications',
      visible: hasPermission(user, 'settings', 'view') || hasPermission(user, 'company', 'view'),
    },
    {
      href: '/dashboard/settings' as Route,
      titleKey: 'nav.settings',
      descriptionKey: 'cards.settings',
      visible:
        hasPermission(user, 'settings', 'view') ||
        hasPermission(user, 'company', 'view') ||
        hasPermission(user, 'offices', 'view'),
    },
  ].filter((card) => card.visible);

  return (
    <main className="dashboard" data-sec-workspace="overview">
      <PageHeader eyebrow={t('eyebrow')} title={t('title')} subtitle={t('subtitle')} />
      <div className="admin-hub-grid" role="list">
        {cards.map((card) => (
          <Link key={card.href} href={card.href} className="admin-hub-card" role="listitem">
            <h2>{t(card.titleKey as 'nav.users')}</h2>
            <p>{t(card.descriptionKey as 'cards.users')}</p>
          </Link>
        ))}
      </div>
      <p className="admin-hub-note">{t('gapNote')}</p>
    </main>
  );
}
