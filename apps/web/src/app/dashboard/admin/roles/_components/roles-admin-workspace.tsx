'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { DashboardHeaderActions } from '@/app/dashboard/_components/dashboard-header-actions';
import {
  assignRolePermissions,
  canViewRoles,
  createRole,
  fetchPermissions,
  fetchRole,
  fetchRoles,
  type PermissionRecord,
  type RoleDetail,
  type RoleSummary,
} from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

export function RolesAdminWorkspace() {
  const t = useTranslations('adminRoles');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user: currentUser, canManageRoles: canManage } = useAuth();
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

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
    if (currentUser && !canViewRoles(currentUser)) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [currentUser, load, router]);

  const handleSelectRole = async (roleId: string) => {
    const role = await fetchRole(roleId);
    setSelectedRole(role);
  };

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await createRole({
      name: String(form.get('name')),
      code: String(form.get('code')),
      description: String(form.get('description') || ''),
    });
    setFormOpen(false);
    await load();
  };

  const handlePermissionToggle = async (permissionId: string, checked: boolean) => {
    if (!selectedRole || !canManage) {
      return;
    }
    const current = new Set(selectedRole.permissions.map((item) => item.id));
    if (checked) {
      current.add(permissionId);
    } else {
      current.delete(permissionId);
    }
    const updated = await assignRolePermissions(selectedRole.id, Array.from(current));
    setSelectedRole(updated);
    await load();
  };

  return (
    <main className="dashboard">
      <header className="dashboard__header">
        <div>
          <p className="dashboard__eyebrow">{t('eyebrow')}</p>
          <h1 className="dashboard__title">{t('title')}</h1>
          <p className="dashboard__subtitle">{t('subtitle')}</p>
        </div>
        <DashboardHeaderActions />
      </header>

      {canManage && (
        <div className="leads__toolbar">
          <button className="leads__primary-button" type="button" onClick={() => setFormOpen(true)}>
            {t('createRole')}
          </button>
        </div>
      )}

      {loading && <p>{tCommon('loading')}</p>}
      {error && <p className="leads__error">{error}</p>}

      {!loading && !error && (
        <div className="admin-split">
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>{t('columns.name')}</th>
                  <th>{t('columns.code')}</th>
                  <th>{t('columns.system')}</th>
                </tr>
              </thead>
              <tbody>
                {roles.map((role) => (
                  <tr key={role.id}>
                    <td>
                      <button type="button" onClick={() => void handleSelectRole(role.id)}>
                        {role.name}
                      </button>
                    </td>
                    <td>{role.code}</td>
                    <td>{role.is_system_role ? t('yes') : t('no')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedRole && (
            <section className="admin-detail">
              <h2>{selectedRole.name}</h2>
              <p>{selectedRole.description ?? tCommon('noValue')}</p>
              {canManage && (
                <div className="admin-permissions-grid">
                  {permissions.map((permission) => {
                    const checked = selectedRole.permissions?.some((item) => item.id === permission.id);
                    return (
                      <label key={permission.id} className="admin-permission-item">
                        <input
                          type="checkbox"
                          checked={Boolean(checked)}
                          onChange={(event) =>
                            void handlePermissionToggle(permission.id, event.target.checked)
                          }
                        />
                        <span>
                          {permission.resource}:{permission.action}
                        </span>
                      </label>
                    );
                  })}
                </div>
              )}
            </section>
          )}
        </div>
      )}

      {formOpen && (
        <div className="leads__modal-backdrop">
          <form className="leads__modal" onSubmit={(event) => void handleCreate(event)}>
            <h2>{t('createRole')}</h2>
            <label>
              {t('fields.name')}
              <input name="name" required />
            </label>
            <label>
              {t('fields.code')}
              <input name="code" pattern="[a-z][a-z0-9_]*" required />
            </label>
            <label>
              {t('fields.description')}
              <textarea name="description" rows={3} />
            </label>
            <div className="leads__modal-actions">
              <button type="button" onClick={() => setFormOpen(false)}>
                {tCommon('cancel')}
              </button>
              <button className="leads__primary-button" type="submit">
                {t('createRole')}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
