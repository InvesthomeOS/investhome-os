'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { usePathname, useRouter } from 'next/navigation';

import { Button, Dialog, PageHeader } from '@investhome/ui';

import { EntityActivityTimeline } from '@/app/dashboard/_components/entity-activity-timeline';
import { EntityDocumentsPanel } from '@/app/dashboard/_components/entity-documents-panel';
import {
  activateUser,
  assignUserRoles,
  canViewUsers,
  createUser,
  deactivateUser,
  fetchRoles,
  fetchUsers,
  resendUserInvite,
  combinePersonName,
  type InviteDelivery,
  type RoleSummary,
  type UserRecord,
  updateUser,
} from '@/lib/api/auth';
import {
  forceLogoutUser,
  resetUserMfa,
  resetUserPassword,
  suspendUser,
} from '@/lib/api/security-center';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canShowMfaAdminReset,
  postMfaResetRedirect,
  shouldExecuteMfaReset,
} from '@/lib/auth/mfa-admin-reset';

import { AdminDataTable, type AdminTableColumn } from '../../_components/admin-data-table';
import { AdminFilters, DEFAULT_ADMIN_FILTERS, type AdminFilterState } from '../../_components/admin-filters';
import { AdminFormModal } from '../../_components/admin-form-modal';
import { AdminPageStates } from '../../_components/admin-page-states';
import { useAdminToast } from '../../_components/use-admin-toast';

export function UsersAdminWorkspace() {
  const t = useTranslations('adminUsers');
  const tShell = useTranslations('adminShell');
  const tSec = useTranslations('adminSecurity');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const pathname = usePathname();
  const { user: currentUser, canManageUsers: canManage, logout } = useAuth();
  const { notifySuccess, notifyError } = useAdminToast();
  const [users, setUsers] = useState<UserRecord[]>([]);
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formDirty, setFormDirty] = useState(false);
  const [mfaResetTarget, setMfaResetTarget] = useState<UserRecord | null>(null);
  const [mfaResetBusy, setMfaResetBusy] = useState(false);
  const canResetMfa = canShowMfaAdminReset(currentUser);
  const [draftFilters, setDraftFilters] = useState<AdminFilterState>(DEFAULT_ADMIN_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<AdminFilterState>(DEFAULT_ADMIN_FILTERS);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersResponse, rolesResponse] = await Promise.all([
        fetchUsers({
          search: appliedFilters.search || undefined,
          status: appliedFilters.status || undefined,
        }),
        fetchRoles(),
      ]);
      setUsers(usersResponse.items);
      setRoles(rolesResponse.items);
    } catch (loadError) {
      notifyError(loadError, t('loadError'));
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [appliedFilters.search, appliedFilters.status, notifyError, t]);

  useEffect(() => {
    if (currentUser && !canViewUsers(currentUser)) {
      router.replace('/forbidden');
      return;
    }
    void load();
  }, [currentUser, load, router]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const recordId = new URLSearchParams(window.location.search).get('id');
    if (recordId) setSelectedId(recordId);
  }, [pathname]);

  const filteredUsers = useMemo(() => {
    return users.filter((item) => {
      if (appliedFilters.roleId && item.roles[0]?.id !== appliedFilters.roleId) {
        return false;
      }
      if (
        appliedFilters.department &&
        !(item.department ?? '').toLowerCase().includes(appliedFilters.department.toLowerCase())
      ) {
        return false;
      }
      if (appliedFilters.dateFrom) {
        const created = new Date(item.created_at);
        if (created < new Date(`${appliedFilters.dateFrom}T00:00:00`)) {
          return false;
        }
      }
      if (appliedFilters.dateTo) {
        const created = new Date(item.created_at);
        if (created > new Date(`${appliedFilters.dateTo}T23:59:59`)) {
          return false;
        }
      }
      return true;
    });
  }, [appliedFilters.dateFrom, appliedFilters.dateTo, appliedFilters.department, appliedFilters.roleId, users]);

  const selected = filteredUsers.find((item) => item.id === selectedId) ?? null;

  const handleDeactivate = async (userId: string) => {
    try {
      await deactivateUser(userId);
      notifySuccess(tShell('deactivatedUser'));
      await load();
    } catch (deactivateError) {
      notifyError(deactivateError, tShell('saveFailed'));
    }
  };

  const handleActivate = async (userId: string) => {
    try {
      await activateUser(userId);
      notifySuccess(tShell('activatedUser'));
      await load();
    } catch (activateError) {
      notifyError(activateError, tShell('saveFailed'));
    }
  };

  const notifyInviteDelivery = (result: InviteDelivery, successKey: 'invitedUser' | 'inviteResent') => {
    notifySuccess(tShell(successKey));
    if (result.delivery_status === 'not_connected') {
      notifySuccess(tShell('emailNotConnected'));
    } else if (result.delivery_status === 'failed') {
      notifySuccess(tShell('emailFailed'));
    } else if (result.delivery_status !== 'sent') {
      notifySuccess(tShell('emailNotSent'));
    }
  };

  const handleResendInvite = async (userId: string) => {
    try {
      const result = await resendUserInvite(userId);
      notifyInviteDelivery(result, 'inviteResent');
      await load();
    } catch (resendError) {
      notifyError(resendError, tShell('saveFailed'));
    }
  };

  const handleRolesChange = async (userId: string, roleIds: string[]) => {
    if (roleIds.length === 0) {
      return;
    }
    try {
      await assignUserRoles(userId, roleIds);
      notifySuccess(tShell('roleAssigned'));
      await load();
    } catch (roleError) {
      notifyError(roleError, tShell('saveFailed'));
    }
  };

  const handleLanguageChange = async (userId: string, preferredLanguage: string) => {
    try {
      await updateUser(userId, { preferred_language: preferredLanguage });
      notifySuccess(tShell('savedUser'));
      await load();
    } catch (updateError) {
      notifyError(updateError, tShell('saveFailed'));
    }
  };

  const handleConfirmMfaReset = async () => {
    if (!mfaResetTarget || !currentUser) {
      return;
    }
    if (!shouldExecuteMfaReset({ confirmed: true })) {
      return;
    }
    setMfaResetBusy(true);
    try {
      await resetUserMfa(mfaResetTarget.id);
      notifySuccess(tSec('resetMfaDone'));
      const redirectTo = postMfaResetRedirect(currentUser.id, mfaResetTarget.id);
      setMfaResetTarget(null);
      if (redirectTo) {
        await logout();
        return;
      }
      await load();
    } catch (resetError) {
      notifyError(resetError, tShell('saveFailed'));
    } finally {
      setMfaResetBusy(false);
    }
  };

  const renderResetMfaButton = (row: UserRecord) =>
    canResetMfa ? (
      <Button
        type="button"
        variant="ghost"
        data-testid="mfa-reset-button"
        data-user-id={row.id}
        onClick={(event) => {
          event.stopPropagation();
          setMfaResetTarget(row);
        }}
      >
        {tSec('resetMfa')}
      </Button>
    ) : null;

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const roleIds = form.getAll('role_ids').map(String).filter(Boolean);
    if (roleIds.length === 0) {
      notifyError(new Error(t('fields.selectRoles')), tShell('saveFailed'));
      return;
    }
    try {
      const fullName = combinePersonName(String(form.get('first_name') || ''), String(form.get('last_name') || ''));
      if (!fullName) {
        notifyError(new Error(t('fields.firstName')), tShell('saveFailed'));
        return;
      }
      const result = await createUser({
        full_name: fullName,
        email: String(form.get('email')),
        job_title: String(form.get('job_title') || ''),
        department: String(form.get('department') || ''),
        role_ids: roleIds,
      });
      setFormOpen(false);
      setFormDirty(false);
      notifyInviteDelivery(result, 'invitedUser');
      await load();
    } catch (createError) {
      notifyError(createError, tShell('saveFailed'));
    }
  };

  const columns: AdminTableColumn<UserRecord>[] = [
    {
      id: 'name',
      header: t('columns.name'),
      sortable: true,
      exportValue: (row) => row.full_name,
      render: (row) => row.full_name,
    },
    {
      id: 'email',
      header: t('columns.email'),
      sortable: true,
      exportValue: (row) => row.email,
      render: (row) => row.email,
    },
    {
      id: 'department',
      header: t('columns.department'),
      sortable: true,
      exportValue: (row) => row.department ?? '',
      render: (row) => row.department ?? tCommon('noValue'),
    },
    {
      id: 'status',
      header: t('columns.status'),
      sortable: true,
      exportValue: (row) => row.status,
      render: (row) => t(`status.${row.status}`),
    },
    {
      id: 'roles',
      header: t('columns.roles'),
      render: (row) =>
        canManage ? (
          <select
            multiple
            value={row.roles.map((role) => role.id)}
            onClick={(event) => event.stopPropagation()}
            onChange={(event) => {
              const selected = Array.from(event.currentTarget.selectedOptions, (option) => option.value);
              void handleRolesChange(row.id, selected);
            }}
          >
            {roles.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        ) : (
          row.roles.map((role) => role.name).join(', ')
        ),
    },
    {
      id: 'language',
      header: t('columns.language'),
      render: (row) =>
        canManage ? (
          <select
            value={row.preferred_language}
            onClick={(event) => event.stopPropagation()}
            onChange={(event) => void handleLanguageChange(row.id, event.target.value)}
          >
            <option value="tr">{tCommon('languageTurkish')}</option>
            <option value="en">{tCommon('languageEnglish')}</option>
          </select>
        ) : (
          row.preferred_language
        ),
    },
    {
      id: 'lastLogin',
      header: tSec('lastLogin'),
      sortable: true,
      exportValue: (row) => row.last_login_at ?? '',
      render: (row) =>
        row.last_login_at ? new Date(row.last_login_at).toLocaleString() : tCommon('noValue'),
    },
    {
      id: 'mfa',
      header: tSec('mfaStatus'),
      exportValue: (row) => (row.mfa_enabled ? 'enabled' : 'off'),
      render: (row) => (row.mfa_enabled ? row.mfa_method ?? 'on' : 'off'),
    },
    {
      id: 'actions',
      header: t('columns.actions'),
      render: (row) => (
        <>
          <Button type="button" variant="ghost" onClick={() => setSelectedId(row.id)}>
            {tCommon('edit')}
          </Button>
          {renderResetMfaButton(row)}
          {canManage && row.id !== currentUser?.id ? (
            <>
              <Button
                type="button"
                variant="ghost"
                onClick={async () => {
                  try {
                    await forceLogoutUser(row.id);
                    notifySuccess(tSec('forceLogoutDone'));
                  } catch (err) {
                    notifyError(err, tShell('saveFailed'));
                  }
                }}
              >
                {tSec('forceLogout')}
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={async () => {
                  try {
                    await resetUserPassword(row.id);
                    notifySuccess(tSec('resetPasswordDone'));
                  } catch (err) {
                    notifyError(err, tShell('saveFailed'));
                  }
                }}
              >
                {tSec('resetPassword')}
              </Button>
              {row.status === 'active' ? (
                <Button
                  type="button"
                  variant="danger"
                  onClick={async () => {
                    try {
                      await suspendUser(row.id);
                      notifySuccess(tSec('suspendDone'));
                      await load();
                    } catch (err) {
                      notifyError(err, tShell('saveFailed'));
                    }
                  }}
                >
                  {tSec('suspend')}
                </Button>
              ) : null}
              {row.status === 'invited' ? (
                <Button type="button" variant="ghost" onClick={() => void handleResendInvite(row.id)}>
                  {t('resendInvite')}
                </Button>
              ) : null}
              {row.status === 'inactive' ? (
                <Button type="button" variant="ghost" onClick={() => void handleActivate(row.id)}>
                  {t('activate')}
                </Button>
              ) : null}
              {row.status === 'active' ? (
                <Button type="button" variant="danger" onClick={() => void handleDeactivate(row.id)}>
                  {t('deactivate')}
                </Button>
              ) : null}
            </>
          ) : null}
        </>
      ),
    },
  ];

  return (
    <main className="dashboard">
      <PageHeader
        eyebrow={t('eyebrow')}
        title={t('title')}
        subtitle={t('subtitle')}
        actions={
          canManage ? (
            <Button type="button" onClick={() => setFormOpen(true)}>
              {t('inviteUser')}
            </Button>
          ) : null
        }
      />

      <AdminFilters
        filters={draftFilters}
        onChange={setDraftFilters}
        onApply={() => setAppliedFilters(draftFilters)}
        onReset={() => {
          setDraftFilters(DEFAULT_ADMIN_FILTERS);
          setAppliedFilters(DEFAULT_ADMIN_FILTERS);
        }}
        roleOptions={roles.map((role) => ({ value: role.id, label: role.name }))}
        showRole
        showDepartment
        showDate
      />

      <AdminPageStates
        loading={loading}
        error={error}
        empty={!loading && !error && filteredUsers.length === 0}
        onRetry={() => void load()}
        emptyTitle={tShell('emptyUsers')}
        emptyDescription={tShell('emptyUsersHint')}
      >
        <AdminDataTable
          rows={filteredUsers}
          columns={columns}
          rowKey={(row) => row.id}
          activeRowKey={selectedId}
          onRowClick={(row) => setSelectedId(row.id)}
          exportFileName="users.csv"
        />
      </AdminPageStates>

      {selected ? (
        <section className="admin-detail">
          <h2>{selected.full_name}</h2>
          <p>{selected.email}</p>
          <p>{selected.job_title ?? tCommon('noValue')}</p>
          {selected.is_demo ? <span className="dashboard-shell__nav-badge">{tCommon('demo')}</span> : null}
          {renderResetMfaButton(selected)}
          <EntityDocumentsPanel entityType="user" entityId={selected.id} />
          <EntityActivityTimeline entityType="user" entityId={selected.id} />
        </section>
      ) : null}

      <Dialog
        open={Boolean(mfaResetTarget)}
        title={tSec('resetMfaConfirmTitle')}
        onClose={() => {
          if (!mfaResetBusy) setMfaResetTarget(null);
        }}
        footer={
          <>
            <Button
              type="button"
              variant="secondary"
              data-testid="mfa-reset-cancel"
              disabled={mfaResetBusy}
              onClick={() => setMfaResetTarget(null)}
            >
              {tCommon('cancel')}
            </Button>
            <Button
              type="button"
              variant="danger"
              data-testid="mfa-reset-confirm"
              disabled={mfaResetBusy}
              onClick={() => void handleConfirmMfaReset()}
            >
              {tSec('resetMfa')}
            </Button>
          </>
        }
      >
        <div data-testid="mfa-reset-confirm-dialog">
          <p>{tSec('resetMfaConfirmBody', { name: mfaResetTarget?.full_name ?? mfaResetTarget?.email ?? '' })}</p>
          <p>{tSec('resetMfaConfirmSessions')}</p>
        </div>
      </Dialog>

      <AdminFormModal
        open={formOpen}
        title={t('inviteUser')}
        submitLabel={t('inviteUser')}
        dirty={formDirty}
        onClose={() => {
          setFormOpen(false);
          setFormDirty(false);
        }}
        onSubmit={handleCreate}
      >
        <label>
          {t('fields.firstName')}
          <input name="first_name" required autoComplete="given-name" onChange={() => setFormDirty(true)} />
        </label>
        <label>
          {t('fields.lastName')}
          <input name="last_name" required autoComplete="family-name" onChange={() => setFormDirty(true)} />
        </label>
        <label>
          {t('fields.email')}
          <input name="email" type="email" required onChange={() => setFormDirty(true)} />
        </label>
        <label>
          {t('fields.jobTitle')}
          <input name="job_title" onChange={() => setFormDirty(true)} />
        </label>
        <label>
          {t('fields.department')}
          <input name="department" onChange={() => setFormDirty(true)} />
        </label>
        <fieldset>
          <legend>{t('fields.roles')}</legend>
          <p>{t('fields.selectRoles')}</p>
          {roles.map((role) => (
            <label key={role.id}>
              <input
                type="checkbox"
                name="role_ids"
                value={role.id}
                onChange={() => setFormDirty(true)}
              />
              {role.name}
            </label>
          ))}
        </fieldset>
      </AdminFormModal>
    </main>
  );
}
