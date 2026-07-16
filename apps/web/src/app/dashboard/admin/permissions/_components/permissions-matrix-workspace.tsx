'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { canViewRoles, fetchPermissions, fetchRoles, type PermissionRecord, type RoleSummary } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

export function PermissionsMatrixWorkspace() {
  const t = useTranslations('adminPermissions');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user: currentUser } = useAuth();
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rolesResponse, permissionsResponse] = await Promise.all([
        fetchRoles(),
        fetchPermissions(),
      ]);
      setRoles(rolesResponse.items);
      setPermissions(permissionsResponse.items);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    const canView = canViewRoles(currentUser);
    if (currentUser && !canView) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [currentUser, load, router]);

  const resources = useMemo(
    () => Array.from(new Set(permissions.map((item) => item.resource))).sort(),
    [permissions],
  );
  const actions = useMemo(
    () => Array.from(new Set(permissions.map((item) => item.action))).sort(),
    [permissions],
  );

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="dashboard__title">{t('title')}</h1>
        <p className="dashboard__subtitle">{t('subtitle')}</p>
      </header>

      {loading && <p>{tCommon('loading')}</p>}
      {error && <p className="leads__error">{error}</p>}

      {!loading && !error && (
        <div className="admin-table-wrap admin-table-wrap--scroll">
          <table className="admin-table admin-matrix">
            <thead>
              <tr>
                <th>{t('columns.resource')}</th>
                {actions.map((action) => (
                  <th key={action}>{action}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {resources.map((resource) => (
                <tr key={resource}>
                  <td>{resource}</td>
                  {actions.map((action) => {
                    const permission = permissions.find(
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
      )}
    </main>
  );
}
