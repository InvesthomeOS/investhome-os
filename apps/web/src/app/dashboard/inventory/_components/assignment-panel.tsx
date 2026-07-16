'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import {
  approveAssignmentRequest,
  createAssignmentRequest,
  fetchAssetAssignmentDetail,
  formatAssignmentMoney,
  rejectAssignmentRequest,
  requestAssignmentRevision,
  type AssetAssignmentDetail,
  type AssignmentRequest,
  type AssignmentRequestInput,
} from '@/lib/api/inventory-assignment';
import { ApiError } from '@/lib/api/client';
import { hasPermission } from '@/lib/api/auth';
import { isParkingAsset, isStorageAsset, type InventoryAsset } from '@/lib/api/inventory';
import { useAuth } from '@/lib/auth/auth-context';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

import { AssignmentFormModal } from './assignment-form-modal';

interface AssignmentPanelProps {
  asset: InventoryAsset;
  parentUnits: InventoryAsset[];
  onChanged?: () => void;
  focusRequestId?: string;
}

function RequestCard({
  request,
  locale,
  t,
  getRequestTypeLabel,
  getRequestStatusLabel,
  canApprove,
  canReject,
  canReview,
  busy,
  decisionNotes,
  onDecisionNotesChange,
  onApprove,
  onReject,
  onRevision,
}: {
  request: AssignmentRequest;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  getRequestTypeLabel: (value: string) => string;
  getRequestStatusLabel: (value: string) => string;
  canApprove: boolean;
  canReject: boolean;
  canReview: boolean;
  busy: boolean;
  decisionNotes: string;
  onDecisionNotesChange: (value: string) => void;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onRevision: (id: string) => void;
}) {
  return (
    <article className="inventory-pricing__request">
      <header>
        <strong>{getRequestTypeLabel(request.request_type)}</strong>
        <StatusChip tone="warning">{getRequestStatusLabel(request.status)}</StatusChip>
      </header>
      <p>{request.reason}</p>
      <dl className="leads-drawer__grid">
        <div>
          <dt>{t('columns.effectiveDate')}</dt>
          <dd>{request.effective_date}</dd>
        </div>
        <div>
          <dt>{t('columns.parentUnit')}</dt>
          <dd>{request.parent_display_id ?? '—'}</dd>
        </div>
        <div>
          <dt>{t('columns.assignmentPrice')}</dt>
          <dd>{formatAssignmentMoney(request.assignment_price, request.currency, locale)}</dd>
        </div>
      </dl>
      {(canApprove || canReject || canReview) && (
        <div className="inventory-pricing__request-actions">
          <textarea
            value={decisionNotes}
            onChange={(e) => onDecisionNotesChange(e.target.value)}
            placeholder={t('decisionNotesPlaceholder')}
            rows={2}
          />
          {canReview && (
            <Button variant="secondary" disabled={busy} onClick={() => onRevision(request.id)}>
              {t('requestRevision')}
            </Button>
          )}
          {canReject && (
            <Button variant="secondary" disabled={busy || !decisionNotes.trim()} onClick={() => onReject(request.id)}>
              {t('reject')}
            </Button>
          )}
          {canApprove && (
            <Button disabled={busy} onClick={() => onApprove(request.id)}>
              {t('approve')}
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

export function AssignmentPanel({ asset, parentUnits, onChanged, focusRequestId: _focusRequestId }: AssignmentPanelProps) {
  const t = useTranslations('inventory.assignments');
  const locale = useLocale();
  const { user } = useAuth();
  const { getAssignmentRequestTypeLabel, getAssignmentRequestStatusLabel } = useInventoryLabels();

  const [detail, setDetail] = useState<AssetAssignmentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState('');

  const isChild = isParkingAsset(asset.asset_type) || isStorageAsset(asset.asset_type);
  const canView = user ? hasPermission(user, 'inventory', 'view_assignment') : false;
  const canRequest = user ? hasPermission(user, 'inventory', 'request_assignment') : false;
  const canApprove = user ? hasPermission(user, 'inventory', 'approve_assignment') : false;
  const canReject = user ? hasPermission(user, 'inventory', 'reject_assignment') : false;
  const canReview = user ? hasPermission(user, 'inventory', 'review_assignment') : false;
  const canUnassign = user ? hasPermission(user, 'inventory', 'unassign') : false;
  const canViewPrice = user ? hasPermission(user, 'inventory', 'view_assignment_price') : false;

  const load = useCallback(async () => {
    if (!canView) {
      setDetail(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await fetchAssetAssignmentDetail(asset.id);
      setDetail(data);
      setError(null);
    } catch {
      setDetail(null);
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [asset.id, canView, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async (input: AssignmentRequestInput) => {
    await createAssignmentRequest(input);
    setFormOpen(false);
    await load();
    onChanged?.();
  };

  const handleApprove = async (id: string) => {
    setBusy(true);
    try {
      await approveAssignmentRequest(id, decisionNotes.trim() || undefined);
      setDecisionNotes('');
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('actionError'));
    } finally {
      setBusy(false);
    }
  };

  const handleReject = async (id: string) => {
    setBusy(true);
    try {
      await rejectAssignmentRequest(id, decisionNotes.trim());
      setDecisionNotes('');
      await load();
      onChanged?.();
    } catch {
      setError(t('actionError'));
    } finally {
      setBusy(false);
    }
  };

  const handleRevision = async (id: string) => {
    setBusy(true);
    try {
      await requestAssignmentRevision(id, decisionNotes.trim());
      setDecisionNotes('');
      await load();
      onChanged?.();
    } catch {
      setError(t('actionError'));
    } finally {
      setBusy(false);
    }
  };

  if (!canView) {
    return <p className="leads__state">{t('noPermission')}</p>;
  }

  if (loading) return <p className="leads__state">{t('loading')}</p>;
  if (error) return <p className="leads__state leads__state--error">{error}</p>;
  if (!detail) return null;

  const pending = detail.pending_requests;
  const scheduled = detail.scheduled_requests;

  return (
    <div className="inventory-assignments">
      {isChild && (
        <section className="leads-drawer__section">
          <header className="inventory-pricing__header">
            <h3>{t('currentAssignment')}</h3>
            {canRequest && (
              <Button variant="secondary" onClick={() => setFormOpen(true)}>
                {detail.current ? t('reassign') : t('assign')}
              </Button>
            )}
            {canUnassign && detail.current && (
              <Button variant="secondary" onClick={() => setFormOpen(true)}>
                {t('unassign')}
              </Button>
            )}
          </header>
          {!detail.current && <p className="leads__state">{t('unassigned')}</p>}
          {detail.current && (
            <dl className="leads-drawer__grid">
              <div>
                <dt>{t('columns.parentUnit')}</dt>
                <dd>{detail.current.parent_display_id ?? detail.current.parent_asset_id}</dd>
              </div>
              <div>
                <dt>{t('columns.effectiveFrom')}</dt>
                <dd>{detail.current.effective_from}</dd>
              </div>
              {canViewPrice && (
                <div>
                  <dt>{t('columns.assignmentPrice')}</dt>
                  <dd>
                    {formatAssignmentMoney(
                      detail.current.assignment_price,
                      detail.current.currency,
                      locale,
                    )}
                  </dd>
                </div>
              )}
            </dl>
          )}
        </section>
      )}

      {!isChild && (
        <section className="leads-drawer__section">
          <h3>{t('accessoriesTitle')}</h3>
          {detail.parent_accessories.length === 0 && (
            <p className="leads__state">{t('noAccessories')}</p>
          )}
          {detail.parent_accessories.length > 0 && (
            <table className="ih-table ih-table--compact">
              <thead>
                <tr>
                  <th>{t('columns.childAsset')}</th>
                  <th>{t('columns.assignmentType')}</th>
                  {canViewPrice && <th>{t('columns.assignmentPrice')}</th>}
                </tr>
              </thead>
              <tbody>
                {detail.parent_accessories.map((row) => (
                  <tr key={row.id}>
                    <td>{row.child_display_id}</td>
                    <td>{row.assignment_type}</td>
                    {canViewPrice && (
                      <td className="ih-table__numeric">
                        {formatAssignmentMoney(row.assignment_price, row.currency, locale)}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}

      {scheduled.length > 0 && (
        <section className="leads-drawer__section">
          <h3>{t('scheduledTitle')}</h3>
          {scheduled.map((request) => (
            <RequestCard
              key={request.id}
              request={request}
              locale={locale}
              t={t}
              getRequestTypeLabel={getAssignmentRequestTypeLabel}
              getRequestStatusLabel={getAssignmentRequestStatusLabel}
              canApprove={false}
              canReject={false}
              canReview={false}
              busy={busy}
              decisionNotes={decisionNotes}
              onDecisionNotesChange={setDecisionNotes}
              onApprove={handleApprove}
              onReject={handleReject}
              onRevision={handleRevision}
            />
          ))}
        </section>
      )}

      {pending.length > 0 && (
        <section className="leads-drawer__section">
          <h3>{t('pendingTitle')}</h3>
          {pending.map((request) => (
            <RequestCard
              key={request.id}
              request={request}
              locale={locale}
              t={t}
              getRequestTypeLabel={getAssignmentRequestTypeLabel}
              getRequestStatusLabel={getAssignmentRequestStatusLabel}
              canApprove={canApprove && request.actions.includes('approve')}
              canReject={canReject && request.actions.includes('reject')}
              canReview={canReview && request.actions.includes('review')}
              busy={busy}
              decisionNotes={decisionNotes}
              onDecisionNotesChange={setDecisionNotes}
              onApprove={handleApprove}
              onReject={handleReject}
              onRevision={handleRevision}
            />
          ))}
        </section>
      )}

      {isChild && detail.history.length > 0 && (
        <section className="leads-drawer__section">
          <h3>{t('historyTitle')}</h3>
          <table className="ih-table ih-table--compact">
            <thead>
              <tr>
                <th>{t('columns.parentUnit')}</th>
                <th>{t('columns.effectiveFrom')}</th>
                <th>{t('columns.effectiveTo')}</th>
                <th>{t('columns.status')}</th>
              </tr>
            </thead>
            <tbody>
              {detail.history.map((row) => (
                <tr key={row.id}>
                  <td>{row.parent_display_id}</td>
                  <td>{row.effective_from}</td>
                  <td>{row.effective_to ?? '—'}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {formOpen && (
        <AssignmentFormModal
          asset={asset}
          parentUnits={parentUnits}
          currentParentId={detail.current?.parent_asset_id ?? null}
          onClose={() => setFormOpen(false)}
          onSubmit={handleCreate}
        />
      )}
    </div>
  );
}
