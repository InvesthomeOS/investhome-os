'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { PageHeader } from '@investhome/ui';

import { canViewRoles, fetchPermissions, fetchRoles, type PermissionRecord, type RoleSummary } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

import { AdminFilters, DEFAULT_ADMIN_FILTERS, type AdminFilterState } from '../../_components/admin-filters';
import { AdminPageStates } from '../../_components/admin-page-states';
import { useAdminToast } from '../../_components/use-admin-toast';

export function PermissionsMatrixWorkspace() {
  const t = useTranslations('adminPermissions');
  const tShell = useTranslations('adminShell');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user: currentUser } = useAuth();
  const { notifyError } = useAdminToast();
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draftFilters, setDraftFilters] = useState<AdminFilterState>(DEFAULT_ADMIN_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<AdminFilterState>(DEFAULT_ADMIN_FILTERS);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rolesResponse, permissionsResponse] = await Promise.all([fetchRoles(), fetchPermissions()]);
      setRoles(rolesResponse.items);
      setPermissions(permissionsResponse.items);
    } catch (loadError) {
      notifyError(loadError, t('loadError'));
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [notifyError, t]);

  useEffect(() => {
    if (currentUser && !canViewRoles(currentUser)) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [currentUser, load, router]);

  const filteredPermissions = useMemo(() => {
    const query = appliedFilters.search.trim().toLowerCase();
    if (!query) return permissions;
    return permissions.filter(
      (item) =>
        item.resource.toLowerCase().includes(query) ||
        item.action.toLowerCase().includes(query) ||
        (item.description ?? '').toLowerCase().includes(query),
    );
  }, [appliedFilters.search, permissions]);

  const resources = useMemo(
    () => Array.from(new Set(filteredPermissions.map((item) => item.resource))).sort(),
    [filteredPermissions],
  );
  const actions = useMemo(
    () => Array.from(new Set(filteredPermissions.map((item) => item.action))).sort(),
    [filteredPermissions],
  );

  return (
    <main className="dashboard">
      <PageHeader eyebrow={t('eyebrow')} title={t('title')} subtitle={t('subtitle')} />

      <AdminFilters
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={() => setAppliedFilters(draftFilters)}
        onReset={() => {
          setDraftFilters(DEFAULT_ADMIN_FILTERS);
          setAppliedFilters(DEFAULT_ADMIN_FILTERS);
        }}
      />

      <AdminPageStates
        loading={loading}
        error={error}
        empty={!loading && !error && filteredPermissions.length === 0}
        onRetry={() => void load()}
        emptyTitle={tShell('emptyPermissions')}
      >
        <div className="admin-table-wrap admin-table-wrap--scroll">
          <table className="admin-table admin-matrix">
            <thead>
              <tr>
                <th scope="col">{t('columns.resource')}</th>
                {actions.map((action) => (
                  <th key={action} scope="col">
                    {action}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {resources.map((resource) => (
                <tr key={resource}>
                  <th scope="row">{resource}</th>
                  {actions.map((action) => {
                    const permission = filteredPermissions.find(
                      (item) => item.resource === resource && item.action === action,
                    );
                    return (
                      <td key={`${resource}-${action}`}>
                        {permission ? t('defined') : tCommon('noValue')}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="admin-matrix__roles">{t('rolesCount', { count: roles.length })}</p>
        </div>
      </AdminPageStates>
    </main>
  );
}
