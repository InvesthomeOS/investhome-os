'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { canViewRoles, canViewUsers, hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { ExecutiveDashboardPrototype } from './_components/executive-dashboard-prototype';

/**
 * Design System D1C visual refinement prototype ONLY — not the production executive dashboard.
 * Route: /dashboard/admin/design-system/executive-dashboard
 * Demo data must never be wired to production APIs.
 * Admin-only (same gate as Admin design-system nav).
 */
export default function ExecutiveDashboardPrototypePage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace('/login');
      return;
    }
    const canViewSettings =
      hasPermission(user, 'settings', 'view') ||
      hasPermission(user, 'company', 'view') ||
      hasPermission(user, 'offices', 'view') ||
      hasPermission(user, 'organization', 'view');
    const canViewSecurity = hasPermission(user, 'security', 'view');
    const allowed =
      canViewUsers(user) || canViewRoles(user) || canViewSecurity || canViewSettings;
    if (!allowed) {
      router.replace('/forbidden');
    }
  }, [loading, router, user]);

  if (loading || !user) {
    return null;
  }

  const canViewSettings =
    hasPermission(user, 'settings', 'view') ||
    hasPermission(user, 'company', 'view') ||
    hasPermission(user, 'offices', 'view') ||
    hasPermission(user, 'organization', 'view');
  const canViewSecurity = hasPermission(user, 'security', 'view');
  const allowed =
    canViewUsers(user) || canViewRoles(user) || canViewSecurity || canViewSettings;
  if (!allowed) {
    return null;
  }

  return <ExecutiveDashboardPrototype />;
}
