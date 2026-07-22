'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { Button, Drawer, StatusChip, Tabs } from '@investhome/ui';

import type { BranchDetail } from '@/lib/api/branches';
import { getBranchMapsUrl } from '@/lib/api/branches';
import {
  canAssignBranchManager,
  canCreateBranch,
  canDeleteBranch,
  canTransferBranchEmployees,
  canUpdateBranch,
} from '@/lib/company/branch-permissions';
import { useAuth } from '@/lib/auth/auth-context';

type BranchDetailDrawerProps = {
  branch: BranchDetail | null;
  open: boolean;
  loading?: boolean;
  onClose: () => void;
  onEdit: () => void;
  onDuplicate: () => void;
  onAssignManager: () => void;
  onTransferEmployees: () => void;
  onArchive: () => void;
  onDeactivate: () => void;
  onDelete: () => void;
};

export function BranchDetailDrawer({
  branch,
  open,
  loading = false,
  onClose,
  onEdit,
  onDuplicate,
  onAssignManager,
  onTransferEmployees,
  onArchive,
  onDeactivate,
  onDelete,
}: BranchDetailDrawerProps) {
  const t = useTranslations('company.branches');
  const tTypes = useTranslations('company.branches.types');
  const tStatuses = useTranslations('company.branches.statuses');
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('general');
  const mapsUrl = branch ? getBranchMapsUrl(branch) : null;

  return (
    <Drawer open={open} onClose={onClose} title={branch?.branch_name ?? t('detailTitle')} wide>
      {loading || !branch ? (
        <p>{t('loadingDetail')}</p>
      ) : (
        <>
          <div className="company-drawer__actions">
            <Button type="button" variant="secondary" onClick={onEdit} disabled={!canUpdateBranch(user)}>
              {t('actions.edit')}
            </Button>
            <Button type="button" variant="secondary" onClick={onDuplicate} disabled={!canCreateBranch(user)}>
              {t('actions.duplicate')}
            </Button>
            <Button type="button" variant="secondary" onClick={onAssignManager} disabled={!canAssignBranchManager(user)}>
              {t('actions.assignManager')}
            </Button>
            <Button type="button" variant="secondary" onClick={onTransferEmployees} disabled={!canTransferBranchEmployees(user)}>
              {t('actions.transferEmployees')}
            </Button>
            <Button type="button" variant="secondary" onClick={onDeactivate} disabled={!canUpdateBranch(user)}>
              {t('actions.deactivate')}
            </Button>
            <Button type="button" variant="secondary" onClick={onArchive} disabled={!canUpdateBranch(user)}>
              {t('actions.archive')}
            </Button>
            <Button type="button" variant="danger" onClick={onDelete} disabled={!canDeleteBranch(user)}>
              {t('actions.delete')}
            </Button>
            <Link href={`/company/branches/${branch.id}` as Route} className="dashboard-shell__nav-link">
              {t('openFullProfile')}
            </Link>
          </div>

          {branch.warnings.length > 0 ? (
            <div className="company-drawer__warnings">
              {branch.warnings.map((warning) => (
                <p key={warning}>{t('duplicateAddressWarning', { matches: warning.split(':').slice(1).join(':') || warning })}</p>
              ))}
            </div>
          ) : null}

          <Tabs
            tabs={[
              { id: 'general', label: t('sections.general') },
              { id: 'company', label: t('sections.company') },
              { id: 'location', label: t('sections.location') },
              { id: 'hours', label: t('sections.workingHours') },
              { id: 'assets', label: t('sections.assets') },
              { id: 'documents', label: t('sections.documents') },
              { id: 'notes', label: t('sections.notes') },
            ]}
            activeId={activeTab}
            onChange={setActiveTab}
          />

          {activeTab === 'general' ? (
            <dl className="company-detail-grid">
              <div><dt>{t('fields.branch_code')}</dt><dd>{branch.branch_code}</dd></div>
              <div><dt>{t('fields.status')}</dt><dd><StatusChip tone={branch.status === 'active' ? 'success' : 'default'}>{tStatuses(branch.status)}</StatusChip></dd></div>
              <div><dt>{t('fields.branch_type')}</dt><dd>{tTypes(branch.branch_type)}</dd></div>
              <div><dt>{t('fields.opening_date')}</dt><dd>{branch.opening_date ?? '—'}</dd></div>
              <div><dt>{t('fields.department_count')}</dt><dd>{branch.department_count}</dd></div>
              <div><dt>{t('fields.employee_count')}</dt><dd>{branch.employee_count}</dd></div>
            </dl>
          ) : null}

          {activeTab === 'company' ? (
            <dl className="company-detail-grid">
              <div><dt>{t('fields.company')}</dt><dd>{branch.company_name ?? branch.company_id}</dd></div>
              <div><dt>{t('fields.manager')}</dt><dd>{branch.manager_name ?? '—'}</dd></div>
            </dl>
          ) : null}

          {activeTab === 'location' ? (
            <>
              <dl className="company-detail-grid">
                <div><dt>{t('fields.full_address')}</dt><dd>{branch.full_address}</dd></div>
                <div><dt>{t('fields.city')}</dt><dd>{branch.city}</dd></div>
                <div><dt>{t('fields.country')}</dt><dd>{branch.country}</dd></div>
                <div><dt>{t('fields.timezone')}</dt><dd>{branch.timezone ?? '—'}</dd></div>
              </dl>
              {mapsUrl ? (
                <div className="company-map-preview">
                  <p>{t('mapPreviewHint')}</p>
                  <a href={mapsUrl} target="_blank" rel="noreferrer">
                    <Button type="button">{t('openInGoogleMaps')}</Button>
                  </a>
                </div>
              ) : null}
            </>
          ) : null}

          {activeTab === 'hours' ? (
            branch.working_hours ? (
              <dl className="company-detail-grid">
                <div><dt>{t('fields.open_time')}</dt><dd>{branch.working_hours.open_time ?? '—'}</dd></div>
                <div><dt>{t('fields.close_time')}</dt><dd>{branch.working_hours.close_time ?? '—'}</dd></div>
              </dl>
            ) : (
              <p>{t('emptyWorkingHours')}</p>
            )
          ) : null}

          {activeTab === 'assets' ? (
            branch.assets.length ? (
              <ul className="company-detail-list">
                {branch.assets.map((asset) => (
                  <li key={asset.id}>{asset.name} · {asset.asset_type}</li>
                ))}
              </ul>
            ) : (
              <p>{t('emptyAssets')}</p>
            )
          ) : null}

          {activeTab === 'documents' ? (
            branch.documents.length ? (
              <ul className="company-detail-list">
                {branch.documents.map((document) => (
                  <li key={document.id}>{document.title} · {document.document_type}</li>
                ))}
              </ul>
            ) : (
              <p>{t('emptyDocuments')}</p>
            )
          ) : null}

          {activeTab === 'notes' ? <p>{branch.notes ?? t('emptyNotes')}</p> : null}
        </>
      )}
    </Drawer>
  );
}
