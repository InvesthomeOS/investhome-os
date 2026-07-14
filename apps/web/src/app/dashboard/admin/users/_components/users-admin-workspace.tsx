'use client';

import { useCallback, useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';

import { DashboardHeaderActions } from '@/app/dashboard/_components/dashboard-header-actions';
import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import {
  assignUserRoles,
  canViewUsers,
  createUser,
  deactivateUser,
  fetchRoles,
  fetchUsers,
  type RoleSummary,
  type UserRecord,
  updateUser,
} from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';

export function UsersAdminWorkspace() {
  const t = useTranslations('adminUsers');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user: currentUser, canManageUsers: canManage } = useAuth();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersResponse, rolesResponse] = await Promise.all([fetchUsers(), fetchRoles()]);
      setUsers(usersResponse.items);
      setRoles(rolesResponse.items);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (currentUser && !canViewUsers(currentUser)) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [currentUser, load, router]);

  const selected = users.find((item) => item.id === selectedId) ?? null;

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await createUser({
      full_name: String(form.get('full_name')),
      email: String(form.get('email')),
      password: String(form.get('password')),
      job_title: String(form.get('job_title') || ''),
      department: String(form.get('department') || ''),
      status: 'active',
      role_ids: [String(form.get('role_id'))],
    });
    setFormOpen(false);
    await load();
  };

  const handleDeactivate = async (userId: string) => {
    await deactivateUser(userId);
    await load();
  };

  const handleRoleChange = async (userId: string, roleId: string) => {
    await assignUserRoles(userId, [roleId]);
    await load();
  };

  const handleLanguageChange = async (userId: string, preferredLanguage: string) => {
    await updateUser(userId, { preferred_language: preferredLanguage });
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
            {t('createUser')}
          </button>
        </div>
      )}

      {loading && <p>{tCommon('loading')}</p>}
      {error && <p className="leads__error">{error}</p>}

      {!loading && !error && (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>{t('columns.name')}</th>
                <th>{t('columns.email')}</th>
                <th>{t('columns.department')}</th>
                <th>{t('columns.status')}</th>
                <th>{t('columns.roles')}</th>
                <th>{t('columns.language')}</th>
                <th>{t('columns.actions')}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className={selectedId === user.id ? 'admin-table__row--active' : ''}>
                  <td>{user.full_name}</td>
                  <td>{user.email}</td>
                  <td>{user.department ?? tCommon('noValue')}</td>
                  <td>{t(`status.${user.status}`)}</td>
                  <td>
                    {canManage ? (
                      <select
                        value={user.roles[0]?.id ?? ''}
                        onChange={(event) => void handleRoleChange(user.id, event.target.value)}
                      >
                        {roles.map((role) => (
                          <option key={role.id} value={role.id}>
                            {role.name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      user.roles.map((role) => role.name).join(', ')
                    )}
                  </td>
                  <td>
                    {canManage ? (
                      <select
                        value={user.preferred_language}
                        onChange={(event) =>
                          void handleLanguageChange(user.id, event.target.value)
                        }
                      >
                        <option value="tr">{tCommon('languageTurkish')}</option>
                        <option value="en">{tCommon('languageEnglish')}</option>
                      </select>
                    ) : (
                      user.preferred_language
                    )}
                  </td>
                  <td>
                    <button type="button" onClick={() => setSelectedId(user.id)}>
                      {tCommon('edit')}
                    </button>
                    {canManage && user.status === 'active' && user.id !== currentUser?.id && (
                      <button type="button" onClick={() => void handleDeactivate(user.id)}>
                        {t('deactivate')}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && (
        <section className="admin-detail">
          <h2>{selected.full_name}</h2>
          <p>{selected.email}</p>
          <p>{selected.job_title ?? tCommon('noValue')}</p>
          {selected.is_demo && <span className="dashboard-shell__nav-badge">{tCommon('demo')}</span>}
          <EntityActivityTimeline entityType="user" entityId={selected.id} />
        </section>
      )}

      {formOpen && (
        <div className="leads__modal-backdrop">
          <form className="leads__modal" onSubmit={(event) => void handleCreate(event)}>
            <h2>{t('createUser')}</h2>
            <label>
              {t('fields.fullName')}
              <input name="full_name" required />
            </label>
            <label>
              {t('fields.email')}
              <input name="email" type="email" required />
            </label>
            <label>
              {t('fields.password')}
              <input name="password" type="password" minLength={8} required />
            </label>
            <label>
              {t('fields.jobTitle')}
              <input name="job_title" />
            </label>
            <label>
              {t('fields.department')}
              <input name="department" />
            </label>
            <label>
              {t('fields.role')}
              <select name="role_id" required defaultValue="">
                <option value="" disabled>
                  {t('fields.selectRole')}
                </option>
                {roles.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="leads__modal-actions">
              <button type="button" onClick={() => setFormOpen(false)}>
                {tCommon('cancel')}
              </button>
              <button className="leads__primary-button" type="submit">
                {t('createUser')}
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
