'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { canViewRoles, canViewUsers, hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { GithubUiPreview } from './_preview/GithubUiPreview';
import './_preview/github-ui-preview.css';

/**
 * GitHub product UI G1 preview — admin-only, demo data, no production mutations.
 * Route: /dashboard/admin/github-ui-preview
 *
 * Isolated under `_preview/` for clean removal. Does not replace production workspaces.
 */
export default function GithubUiPreviewPage() {
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

  return <GithubUiPreview />;
}
