'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { usePathname, useRouter } from 'next/navigation';

import { Button, PageHeader } from '@investhome/ui';

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

import { AdminDataTable, type AdminTableColumn } from '../../_components/admin-data-table';
import { AdminFilters, DEFAULT_ADMIN_FILTERS, type AdminFilterState } from '../../_components/admin-filters';
import { AdminFormModal } from '../../_components/admin-form-modal';
import { AdminPageStates } from '../../_components/admin-page-states';
import { useAdminToast } from '../../_components/use-admin-toast';

export function RolesAdminWorkspace() {
  const t = useTranslations('adminRoles');
  const tShell = useTranslations('adminShell');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const pathname = usePathname();
  const { user: currentUser, canManageRoles: canManage } = useAuth();
  const { notifySuccess, notifyError, notifyPermissionDenied } = useAdminToast();
  const [roles, setRoles] = useState<RoleSummary[]>([]);
  const [permissions, setPermissions] = useState<PermissionRecord[]>([]);
  const [selectedRole, setSelectedRole] = useState<RoleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [formDirty, setFormDirty] = useState(false);
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

  const handleSelectRole = useCallback(
    async (roleId: string) => {
      try {
        const role = await fetchRole(roleId);
        setSelectedRole(role);
      } catch (selectError) {
        notifyError(selectError, t('loadError'));
      }
    },
    [notifyError, t],
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const recordId = new URLSearchParams(window.location.search).get('id');
    if (recordId) {
      void handleSelectRole(recordId);
    }
  }, [handleSelectRole, pathname]);

  const filteredRoles = useMemo(() => {
    const query = appliedFilters.search.trim().toLowerCase();
    return roles.filter((role) => {
      if (!query) return true;
      return (
        role.name.toLowerCase().includes(query) ||
        role.code.toLowerCase().includes(query) ||
        (role.description ?? '').toLowerCase().includes(query)
      );
    });
  }, [appliedFilters.search, roles]);

  const handleCreate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await createRole({
        name: String(form.get('name')),
        code: String(form.get('code')),
        description: String(form.get('description') || ''),
      });
      setFormOpen(false);
      setFormDirty(false);
      notifySuccess(tShell('savedRole'));
      await load();
    } catch (createError) {
      notifyError(createError, tShell('saveFailed'));
    }
  };

  const handlePermissionToggle = async (permissionId: string, checked: boolean) => {
    if (!selectedRole) return;
    if (!canManage) {
      notifyPermissionDenied();
      return;
    }
    const current = new Set(selectedRole.permissions.map((item) => item.id));
    if (checked) {
      current.add(permissionId);
    } else {
      current.delete(permissionId);
    }
    try {
      const updated = await assignRolePermissions(selectedRole.id, Array.from(current));
      setSelectedRole(updated);
      notifySuccess(tShell('permissionsUpdated'));
      await load();
    } catch (permissionError) {
      notifyError(permissionError, tShell('saveFailed'));
    }
  };

  const columns: AdminTableColumn<RoleSummary>[] = [
    {
      id: 'name',
      header: t('columns.name'),
      sortable: true,
      exportValue: (row) => row.name,
      render: (row) => (
        <Button type="button" variant="ghost" onClick={() => void handleSelectRole(row.id)}>
          {row.name}
        </Button>
      ),
    },
    {
      id: 'code',
      header: t('columns.code'),
      sortable: true,
      exportValue: (row) => row.code,
      render: (row) => row.code,
    },
    {
      id: 'system',
      header: t('columns.system'),
      sortable: true,
      exportValue: (row) => (row.is_system_role ? t('yes') : t('no')),
      render: (row) => (row.is_system_role ? t('yes') : t('no')),
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
              {t('createRole')}
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
      />

      <AdminPageStates
        loading={loading}
        error={error}
        empty={!loading && !error && filteredRoles.length === 0}
        onRetry={() => void load()}
        emptyTitle={tShell('emptyRoles')}
      >
        <div className="admin-split">
          <AdminDataTable
            rows={filteredRoles}
            columns={columns}
            rowKey={(row) => row.id}
            exportFileName="roles.csv"
          />

          {selectedRole ? (
            <section className="admin-detail">
              <h2>{selectedRole.name}</h2>
              <p>{selectedRole.description ?? tCommon('noValue')}</p>
              {canManage ? (
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
              ) : (
                <p>{tShell('readOnlyPermissions')}</p>
              )}
            </section>
          ) : null}
        </div>
      </AdminPageStates>

      <AdminFormModal
        open={formOpen}
        title={t('createRole')}
        submitLabel={t('createRole')}
        dirty={formDirty}
        onClose={() => {
          setFormOpen(false);
          setFormDirty(false);
        }}
        onSubmit={handleCreate}
      >
        <label>
          {t('fields.name')}
          <input name="name" required onChange={() => setFormDirty(true)} />
        </label>
        <label>
          {t('fields.code')}
          <input name="code" pattern="[a-z][a-z0-9_]*" required onChange={() => setFormDirty(true)} />
        </label>
        <label>
          {t('fields.description')}
          <textarea name="description" rows={3} onChange={() => setFormDirty(true)} />
        </label>
      </AdminFormModal>
    </main>
  );
}
