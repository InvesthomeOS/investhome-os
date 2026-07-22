'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { canViewRoles, canViewUsers, hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { TailAdminSpikePreview } from './_tailadmin/TailAdminSpikePreview';
import './_tailadmin/tailadmin-spike.css';

/**
 * TailAdmin Free compatibility spike — admin-only visual preview.
 * Route: /dashboard/admin/tailadmin-preview
 *
 * Constraints:
 * - Demo data only (no production API mutations)
 * - Isolated under `_tailadmin/` for clean removal
 * - Does not replace /dashboard/executive or other production routes
 */
export default function TailAdminPreviewPage() {
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

  return <TailAdminSpikePreview />;
}
