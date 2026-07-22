'use client';

import { useCallback, useMemo, useState } from 'react';
import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { Button, EmptyState, ErrorState, LoadingState, StatusChip } from '@investhome/ui';

import { ContextualAiActions } from '@/components/ai/contextual-ai-actions';
import { ApiError } from '@/lib/api/client';
import { useAuth } from '@/lib/auth/auth-context';
import {
  canBulkActionsCrm,
  canCreateCrm,
  canExportCrm,
  canImportCrm,
  canReadCrm,
} from '@/lib/crm/crm-permissions';
import { contactQueries, contactQueryKeys } from '@/workspaces/crm/hooks/use-contacts';
import { bulkUpdateContacts, exportContactsCsv, type ContactListParams } from '@/workspaces/crm/api/contacts';
import type { CrmContactPriority, CrmContactSummary } from '@/workspaces/crm/types';
import { useContactUiStore } from '@/workspaces/crm/stores/contact-ui-store';

import { AdminDataTable, type AdminTableColumn } from '@/app/dashboard/admin/_components/admin-data-table';

import { ContactFilters, type ContactFilterState } from './contact-filters';
import { ContactFormModal } from './contact-form-modal';

export type { ContactFilterState };

const DEFAULT_FILTERS: ContactFilterState = {
  search: '',
  page: 1,
  page_size: 25,
  sort_by: 'updated_at',
  sort_dir: 'desc',
};

export function ContactsWorkspace() {
  const t = useTranslations('crm.contacts');
  const tTypes = useTranslations('crm.contactTypes');
  const tLifecycle = useTranslations('crm.contacts.lifecycle');
  const tPriority = useTranslations('crm.contacts.priority');
  const tRelStatus = useTranslations('crm.contacts.relationshipStatuses');
  const tCommon = useTranslations('common');
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const { selectedIds, setSelectedIds, clearSelection, density } = useContactUiStore();

  const [filters, setFilters] = useState<ContactFilterState>(DEFAULT_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ContactFilterState>(DEFAULT_FILTERS);
  const [formOpen, setFormOpen] = useState(false);

  const listParams: ContactListParams = useMemo(
    () => ({
      search: appliedFilters.search || undefined,
      contact_type: appliedFilters.contact_type,
      lifecycle_stage: appliedFilters.lifecycle_stage,
      priority: appliedFilters.priority,
      status: appliedFilters.status,
      sort_by: appliedFilters.sort_by,
      sort_dir: appliedFilters.sort_dir,
      page: appliedFilters.page,
      page_size: appliedFilters.page_size,
    }),
    [appliedFilters],
  );

  const listQuery = useQuery(contactQueries.list(listParams));

  const invalidate = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: contactQueryKeys.all });
  }, [queryClient]);

  const bulkMutation = useMutation({
    mutationFn: (payload: { priority?: CrmContactPriority; archive?: boolean }) =>
      bulkUpdateContacts({
        contact_ids: selectedIds,
        priority: payload.priority,
        archive: payload.archive,
      }),
    onSuccess: async () => {
      clearSelection();
      await invalidate();
    },
  });

  const columns = useMemo<AdminTableColumn<CrmContactSummary>[]>(
    () => [
      {
        id: 'display_name',
        header: t('columns.contact'),
        sortable: true,
        exportValue: (row) => row.display_name,
        render: (row) => (
          <Link href={`/workspaces/crm/contacts/${row.id}` as Route} className="crm-contacts__link">
            {row.display_name}
          </Link>
        ),
      },
      {
        id: 'contact_type',
        header: t('columns.type'),
        exportValue: (row) => row.contact_type,
        render: (row) => tTypes(row.contact_type),
      },
      {
        id: 'organization_name',
        header: t('columns.company'),
        exportValue: (row) => row.organization_name ?? row.company_name ?? '',
        render: (row) => row.organization_name ?? row.company_name ?? '—',
      },
      {
        id: 'lifecycle_stage',
        header: t('columns.lifecycle'),
        sortable: true,
        exportValue: (row) => row.lifecycle_stage,
        render: (row) => tLifecycle(row.lifecycle_stage),
      },
      {
        id: 'relationship_status',
        header: t('columns.relationship'),
        exportValue: (row) => row.relationship_status,
        render: (row) =>
          tRelStatus.has(row.relationship_status)
            ? tRelStatus(row.relationship_status)
            : row.relationship_status.replace(/_/g, ' '),
      },
      {
        id: 'owner_name',
        header: t('columns.owner'),
        exportValue: (row) => row.owner_name ?? '',
        render: (row) => row.owner_name ?? '—',
      },
      {
        id: 'last_contact_at',
        header: t('columns.lastContact'),
        sortable: true,
        exportValue: (row) => row.last_contact_at ?? '',
        render: (row) => (row.last_contact_at ? new Date(row.last_contact_at).toLocaleDateString() : '—'),
      },
      {
        id: 'next_follow_up_at',
        header: t('columns.nextFollowUp'),
        sortable: true,
        exportValue: (row) => row.next_follow_up_at ?? '',
        render: (row) => (row.next_follow_up_at ? new Date(row.next_follow_up_at).toLocaleDateString() : '—'),
      },
      {
        id: 'priority',
        header: t('columns.priority'),
        sortable: true,
        exportValue: (row) => row.priority,
        render: (row) => (
          <StatusChip tone={row.priority === 'urgent' || row.priority === 'high' ? 'warning' : 'default'}>
            {tPriority(row.priority)}
          </StatusChip>
        ),
      },
      {
        id: 'relationship_score',
        header: t('columns.score'),
        sortable: true,
        exportValue: (row) => String(row.relationship_score),
        render: (row) => row.relationship_score,
      },
      {
        id: 'tags',
        header: t('columns.tags'),
        exportValue: (row) => (row.tags ?? []).join(', '),
        render: (row) => (row.tags?.length ? row.tags.join(', ') : '—'),
      },
    ],
    [t, tLifecycle, tPriority, tRelStatus, tTypes],
  );

  const handleExport = async () => {
    const blob = await exportContactsCsv();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'crm-contacts-export.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  };

  if (authLoading) {
    return <LoadingState label={t('loading')} variant="skeleton" lines={5} />;
  }

  if (!canReadCrm(user)) {
    return <EmptyState title={t('accessDenied')} description={t('accessDeniedHint')} />;
  }

  if (listQuery.isLoading) {
    return <LoadingState label={t('loading')} variant="skeleton" lines={6} />;
  }

  if (listQuery.isError) {
    return (
      <ErrorState
        title={t('loadError')}
        message={listQuery.error instanceof ApiError ? listQuery.error.message : t('loadError')}
        action={
          <Button type="button" onClick={() => void listQuery.refetch()}>
            {tCommon('retry')}
          </Button>
        }
      />
    );
  }

  const rows = listQuery.data?.items ?? [];

  return (
    <div className={`company-workspace crm-contacts crm-contacts--${density}`}>
      <header className="company-workspace__header">
        <div>
          <p className="company-workspace__eyebrow">{t('eyebrow')}</p>
          <h1>{t('title')}</h1>
          <p className="company-workspace__subtitle">{t('subtitle')}</p>
        </div>
        <div className="company-workspace__header-actions">
          {canCreateCrm(user) ? (
            <Button type="button" onClick={() => setFormOpen(true)}>
              {t('createContact')}
            </Button>
          ) : null}
          {canImportCrm(user) ? (
            <Button
              type="button"
              variant="secondary"
              onClick={() => router.push('/workspaces/crm/contacts/import' as Route)}
            >
              {t('importAction')}
            </Button>
          ) : null}
          {canExportCrm(user) ? (
            <Button type="button" variant="secondary" onClick={() => void handleExport()}>
              {t('export')}
            </Button>
          ) : null}
        </div>
      </header>

      <ContextualAiActions module="crm" />

      <ContactFilters
        filters={filters}
        onChange={setFilters}
        onApply={() => setAppliedFilters({ ...filters, page: 1 })}
        onClear={() => {
          setFilters(DEFAULT_FILTERS);
          setAppliedFilters(DEFAULT_FILTERS);
        }}
        onPreset={(preset) => {
          const next = { ...DEFAULT_FILTERS, ...preset, page: 1 };
          setFilters(next);
          setAppliedFilters(next);
        }}
      />

      {canBulkActionsCrm(user) && selectedIds.length > 0 ? (
        <div className="crm-contacts__bulk-bar">
          <span>{t('bulkSelected', { count: selectedIds.length })}</span>
          <Button type="button" variant="secondary" onClick={() => bulkMutation.mutate({ priority: 'high' })}>
            {t('bulkPriorityHigh')}
          </Button>
          <Button type="button" variant="secondary" onClick={() => bulkMutation.mutate({ archive: true })}>
            {t('bulkArchive')}
          </Button>
          <Button type="button" variant="ghost" onClick={clearSelection}>
            {t('bulkClear')}
          </Button>
        </div>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <AdminDataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.id}
          pageSize={appliedFilters.page_size}
          exportFileName="crm-contacts.csv"
          selectedIds={canBulkActionsCrm(user) ? selectedIds : undefined}
          onSelectedIdsChange={canBulkActionsCrm(user) ? setSelectedIds : undefined}
        />
      )}

      <ContactFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSuccess={async (contactId) => {
          setFormOpen(false);
          await invalidate();
          router.push(`/workspaces/crm/contacts/${contactId}` as Route);
        }}
      />
    </div>
  );
}
