'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import {
  approveOwnershipTransfer,
  createOwnershipTransfer,
  fetchAssetOwnershipDetail,
  formatPercentage,
  rejectOwnershipTransfer,
  requestOwnershipRevision,
  type AssetOwnershipDetail,
  type OwnershipTransferRequest,
} from '@/lib/api/inventory-ownership';
import { ApiError } from '@/lib/api/client';
import { hasPermission } from '@/lib/api/auth';
import type { InventoryAsset } from '@/lib/api/inventory';
import { useAuth } from '@/lib/auth/auth-context';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

import { OwnershipTransferModal } from './ownership-transfer-modal';

interface OwnershipPanelProps {
  asset: InventoryAsset;
  onChanged?: () => void;
  focusRequestId?: string;
}

function OwnershipTable({
  records,
  locale,
  t,
  getOwnershipTypeLabel,
}: {
  records: AssetOwnershipDetail['current_legal'];
  locale: string;
  t: ReturnType<typeof useTranslations>;
  getOwnershipTypeLabel: (value: string) => string;
}) {
  if (records.length === 0) {
    return <p className="leads__state">{t('noRecords')}</p>;
  }
  return (
    <table className="ih-table ih-table--compact">
      <thead>
        <tr>
          <th>{t('columns.party')}</th>
          <th>{t('columns.ownershipType')}</th>
          <th>{t('columns.percentage')}</th>
          <th>{t('columns.effectiveFrom')}</th>
          <th>{t('columns.status')}</th>
        </tr>
      </thead>
      <tbody>
        {records.map((record) => (
          <tr key={record.id}>
            <td>{record.party_name ?? record.party_id}</td>
            <td>{getOwnershipTypeLabel(record.ownership_type)}</td>
            <td className="ih-table__numeric">{formatPercentage(record.ownership_percentage, locale)}</td>
            <td>{record.effective_from}</td>
            <td>
              <StatusChip tone="default">{record.status}</StatusChip>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TransferRequestCard({
  request,
  locale,
  t,
  getTransferTypeLabel,
  getTransferStatusLabel,
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
  request: OwnershipTransferRequest;
  locale: string;
  t: ReturnType<typeof useTranslations>;
  getTransferTypeLabel: (value: string) => string;
  getTransferStatusLabel: (value: string) => string;
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
        <strong>{getTransferTypeLabel(request.transfer_type)}</strong>
        <StatusChip tone="warning">{getTransferStatusLabel(request.status)}</StatusChip>
      </header>
      <p>{request.reason}</p>
      <dl className="leads-drawer__grid">
        <div>
          <dt>{t('columns.effectiveDate')}</dt>
          <dd>{request.effective_date}</dd>
        </div>
        <div>
          <dt>{t('columns.currentTotal')}</dt>
          <dd>{formatPercentage(request.current_legal_total, locale)}</dd>
        </div>
        <div>
          <dt>{t('columns.proposedTotal')}</dt>
          <dd>{formatPercentage(request.proposed_legal_total, locale)}</dd>
        </div>
      </dl>
      {request.actions.includes('approve') && canApprove && (
        <div className="inventory-pricing__actions">
          <textarea
            value={decisionNotes}
            onChange={(e) => onDecisionNotesChange(e.target.value)}
            placeholder={t('decisionNotesPlaceholder')}
            rows={2}
          />
          <Button variant="primary" disabled={busy} onClick={() => onApprove(request.id)}>
            {t('approve')}
          </Button>
          {canReject && (
            <Button variant="secondary" disabled={busy || !decisionNotes.trim()} onClick={() => onReject(request.id)}>
              {t('reject')}
            </Button>
          )}
          {canReview && (
            <Button variant="secondary" disabled={busy || !decisionNotes.trim()} onClick={() => onRevision(request.id)}>
              {t('requestRevision')}
            </Button>
          )}
        </div>
      )}
    </article>
  );
}

export function OwnershipPanel({ asset, onChanged, focusRequestId }: OwnershipPanelProps) {
  const t = useTranslations('inventory.ownership');
  const locale = useLocale();
  const { user } = useAuth();
  const { getOwnershipTypeLabel, getTransferTypeLabel, getTransferStatusLabel, getOwnershipStatusLabel } =
    useInventoryLabels();

  const [detail, setDetail] = useState<AssetOwnershipDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState('');

  const canView = user ? hasPermission(user, 'inventory', 'view_ownership') : false;
  const canRequest = user ? hasPermission(user, 'inventory', 'request_ownership_change') : false;
  const canApprove = user ? hasPermission(user, 'inventory', 'approve_ownership_change') : false;
  const canReject = user ? hasPermission(user, 'inventory', 'reject_ownership_change') : false;
  const canReview = user ? hasPermission(user, 'inventory', 'review_ownership_change') : false;
  const canViewBeneficial = user ? hasPermission(user, 'inventory', 'view_beneficial_ownership') : false;
  const canViewHistory = user ? hasPermission(user, 'inventory', 'view_ownership_history') : false;

  const load = useCallback(async () => {
    if (!canView) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setDetail(await fetchAssetOwnershipDetail(asset.id));
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [asset.id, canView, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAction = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
      onChanged?.();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : t('actionError');
      setError(message);
    } finally {
      setBusy(false);
    }
  };

  if (!canView) {
    return <p className="leads__state">{t('noPermission')}</p>;
  }

  if (loading) return <p className="leads__state">{t('loading')}</p>;
  if (error && !detail) return <p className="leads__state leads__state--error">{error}</p>;
  if (!detail) return null;

  const focused =
    focusRequestId &&
    [...detail.pending_requests, ...detail.scheduled_transfers].find((r) => r.id === focusRequestId);

  return (
    <div className="inventory-ownership">
      {error && <p className="leads__state leads__state--error">{error}</p>}

      <section className="leads-drawer__section">
        <div className="inventory-pricing__header">
          <h3>{t('currentLegal')}</h3>
          {canRequest && (
            <Button variant="secondary" onClick={() => setModalOpen(true)}>
              {t('recordTransfer')}
            </Button>
          )}
        </div>
        <p>
          {t('legalTotal')}: {formatPercentage(detail.legal_total, locale)}{' '}
          <StatusChip tone="default">{getOwnershipStatusLabel(detail.legal_total === '100.0000' ? 'complete' : 'incomplete')}</StatusChip>
        </p>
        <OwnershipTable
          records={detail.current_legal}
          locale={locale}
          t={t}
          getOwnershipTypeLabel={getOwnershipTypeLabel}
        />
      </section>

      {canViewBeneficial && detail.current_beneficial.length > 0 && (
        <section className="leads-drawer__section">
          <h3>{t('beneficial')}</h3>
          <OwnershipTable records={detail.current_beneficial} locale={locale} t={t} getOwnershipTypeLabel={getOwnershipTypeLabel} />
        </section>
      )}

      {canViewBeneficial && detail.current_economic.length > 0 && (
        <section className="leads-drawer__section">
          <h3>{t('economic')}</h3>
          <OwnershipTable records={detail.current_economic} locale={locale} t={t} getOwnershipTypeLabel={getOwnershipTypeLabel} />
        </section>
      )}

      {(detail.pending_requests.length > 0 || focused) && (
        <section className="leads-drawer__section">
          <h3>{t('pendingRequests')}</h3>
          {(focused ? [focused] : detail.pending_requests).map((request) => (
            <TransferRequestCard
              key={request.id}
              request={request}
              locale={locale}
              t={t}
              getTransferTypeLabel={getTransferTypeLabel}
              getTransferStatusLabel={getTransferStatusLabel}
              canApprove={canApprove}
              canReject={canReject}
              canReview={canReview}
              busy={busy}
              decisionNotes={decisionNotes}
              onDecisionNotesChange={setDecisionNotes}
              onApprove={(id) => void handleAction(async () => { await approveOwnershipTransfer(id, decisionNotes); })}
              onReject={(id) => void handleAction(async () => { await rejectOwnershipTransfer(id, decisionNotes); })}
              onRevision={(id) => void handleAction(async () => { await requestOwnershipRevision(id, decisionNotes); })}
            />
          ))}
        </section>
      )}

      {detail.scheduled_transfers.length > 0 && (
        <section className="leads-drawer__section">
          <h3>{t('scheduledTransfers')}</h3>
          {detail.scheduled_transfers.map((request) => (
            <article key={request.id} className="inventory-pricing__request">
              <strong>{getTransferTypeLabel(request.transfer_type)}</strong>
              <p>{t('scheduledFor', { date: request.effective_date })}</p>
            </article>
          ))}
        </section>
      )}

      {canViewHistory && (
        <section className="leads-drawer__section">
          <h3>{t('history')}</h3>
          {detail.history.length === 0 ? (
            <p className="leads__state">{t('noHistory')}</p>
          ) : (
            <OwnershipTable records={detail.history} locale={locale} t={t} getOwnershipTypeLabel={getOwnershipTypeLabel} />
          )}
        </section>
      )}

      {modalOpen && (
        <OwnershipTransferModal
          asset={asset}
          currentLegal={detail.current_legal}
          onClose={() => setModalOpen(false)}
          onSubmit={async (input) => {
            await handleAction(async () => {
              await createOwnershipTransfer(input);
              setModalOpen(false);
            });
          }}
        />
      )}
    </div>
  );
}
