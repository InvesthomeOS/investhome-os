'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import {
  approvePriceRequest,
  createInitialPrice,
  createPriceChangeRequest,
  fetchAssetPricingDetail,
  formatMoney,
  rejectPriceRequest,
  requestPriceRevision,
  submitPriceRequest,
  withdrawPriceRequest,
  type InventoryAssetPrice,
  type PriceChangeRequest,
  type PriceType,
} from '@/lib/api/inventory-pricing';
import { ApiError } from '@/lib/api/client';
import { hasPermission } from '@/lib/api/auth';
import type { InventoryAsset } from '@/lib/api/inventory';
import { useAuth } from '@/lib/auth/auth-context';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

import { PriceChangeModal } from './price-change-modal';

interface PricingPanelProps {
  asset: InventoryAsset;
  onChanged?: () => void;
}

export function PricingPanel({ asset, onChanged }: PricingPanelProps) {
  const t = useTranslations('inventory.pricing');
  const locale = useLocale();
  const { user } = useAuth();
  const { getPriceTypeLabel, getPriceRequestStatusLabel, getPriceStatusLabel } = useInventoryLabels();

  const [currentPrices, setCurrentPrices] = useState<InventoryAssetPrice[]>([]);
  const [pendingRequests, setPendingRequests] = useState<PriceChangeRequest[]>([]);
  const [history, setHistory] = useState<InventoryAssetPrice[]>([]);
  const [approvalHistory, setApprovalHistory] = useState<
    { id: string; decision: string; comments: string | null; created_at: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [initialMode, setInitialMode] = useState(false);
  const [decisionNotes, setDecisionNotes] = useState('');

  const canView = user ? hasPermission(user, 'inventory', 'view_price') : false;
  const canCreateInitial = user ? hasPermission(user, 'inventory', 'create_initial_price') : false;
  const canRequest = user ? hasPermission(user, 'inventory', 'request_price_change') : false;
  const canApprove = user ? hasPermission(user, 'inventory', 'approve_price') : false;
  const canReject = user ? hasPermission(user, 'inventory', 'reject_price') : false;
  const canReview = user ? hasPermission(user, 'inventory', 'review_price_change') : false;

  const load = useCallback(async () => {
    if (!canView) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const detail = await fetchAssetPricingDetail(asset.id);
      setCurrentPrices(detail.current_prices);
      setPendingRequests(detail.pending_requests);
      setHistory(detail.history.map((entry) => entry.price));
      setApprovalHistory(detail.approval_history);
    } catch {
      setError(t('loadError'));
    } finally {
      setLoading(false);
    }
  }, [asset.id, canView, t]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAction = async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
      onChanged?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('actionError'));
    } finally {
      setBusy(false);
    }
  };

  const handleInitialPrice = async (input: {
    price_type: PriceType;
    amount: number;
    effective_from: string;
    reason: string;
  }) => {
    await runAction(() =>
      createInitialPrice({
        inventory_asset_id: asset.id,
        price_type: input.price_type,
        amount: input.amount,
        currency: asset.currency,
        effective_from: input.effective_from,
        reason: input.reason,
      }),
    );
    setModalOpen(false);
  };

  const handlePriceChange = async (input: {
    price_type: PriceType;
    proposed_amount: number;
    effective_from: string;
    effective_to?: string | null;
    reason: string;
    submit: boolean;
  }) => {
    await runAction(async () => {
      const request = await createPriceChangeRequest({
        inventory_asset_id: asset.id,
        price_type: input.price_type,
        proposed_amount: input.proposed_amount,
        currency: asset.currency,
        effective_from: input.effective_from,
        effective_to: input.effective_to,
        reason: input.reason,
        submit: input.submit,
      });
      if (!input.submit && request.status === 'draft') {
        await submitPriceRequest(request.id);
      }
    });
    setModalOpen(false);
  };

  if (!canView) {
    return <p className="leads__meta">{t('noPermission')}</p>;
  }

  if (loading) {
    return <p className="leads__meta">{t('loading')}</p>;
  }

  const listPrice = currentPrices.find((price) => price.price_type === 'list');

  return (
    <div className="inventory__pricing-panel">
      {error && <p className="leads__state leads__state--error">{error}</p>}

      <div className="inventory__pricing-actions">
        {canCreateInitial && !listPrice && (
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => {
              setInitialMode(true);
              setModalOpen(true);
            }}
          >
            {t('addInitialPrice')}
          </Button>
        )}
        {canRequest && (
          <Button
            variant="primary"
            disabled={busy}
            onClick={() => {
              setInitialMode(false);
              setModalOpen(true);
            }}
          >
            {t('proposeChange')}
          </Button>
        )}
      </div>

      <section className="leads-drawer__section">
        <h3>{t('currentPrices')}</h3>
        {currentPrices.length === 0 ? (
          <p className="leads__meta">{t('noCurrentPrices')}</p>
        ) : (
          <ul className="inventory__pricing-list">
            {currentPrices.map((price) => (
              <li key={price.id}>
                <strong>{getPriceTypeLabel(price.price_type)}</strong>
                <span>{formatMoney(price.amount, price.currency, locale)}</span>
                <StatusChip>{getPriceStatusLabel(price.status)}</StatusChip>
                <span className="leads__meta">
                  {price.effective_from}
                  {price.effective_to ? ` → ${price.effective_to}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="leads-drawer__section">
        <h3>{t('pendingRequests')}</h3>
        {pendingRequests.length === 0 ? (
          <p className="leads__meta">{t('noPendingRequests')}</p>
        ) : (
          <ul className="inventory__pricing-requests">
            {pendingRequests.map((request) => (
              <li key={request.id} className="inventory__pricing-request">
                <div>
                  <strong>{getPriceTypeLabel(request.price_type)}</strong>
                  <StatusChip>{getPriceRequestStatusLabel(request.status)}</StatusChip>
                  {request.is_high_impact && (
                    <span className="inventory__pricing-warning">{t('highImpact')}</span>
                  )}
                </div>
                <p>
                  {formatMoney(request.current_amount, request.currency, locale)} →{' '}
                  {formatMoney(request.proposed_amount, request.currency, locale)}
                  {request.change_percentage && (
                    <span className="inventory__pricing-change">
                      {' '}
                      ({request.change_percentage}%)
                    </span>
                  )}
                </p>
                <p className="leads__meta">{request.reason}</p>
                {(canApprove || canReject || canReview) && (
                  <div className="inventory__pricing-request-actions">
                    {canApprove && request.valid_actions?.includes('approve') && (
                      <Button
                        variant="primary"
                        disabled={busy}
                        onClick={() => void runAction(() => approvePriceRequest(request.id, decisionNotes || null))}
                      >
                        {t('approve')}
                      </Button>
                    )}
                    {canReject && request.valid_actions?.includes('reject') && (
                      <>
                        <textarea
                          className="leads__input"
                          placeholder={t('decisionNotesPlaceholder')}
                          value={decisionNotes}
                          onChange={(event) => setDecisionNotes(event.target.value)}
                        />
                        <Button
                          variant="danger"
                          disabled={busy || !decisionNotes.trim()}
                          onClick={() =>
                            void runAction(() => rejectPriceRequest(request.id, decisionNotes.trim()))
                          }
                        >
                          {t('reject')}
                        </Button>
                        <Button
                          variant="secondary"
                          disabled={busy || !decisionNotes.trim()}
                          onClick={() =>
                            void runAction(() => requestPriceRevision(request.id, decisionNotes.trim()))
                          }
                        >
                          {t('requestRevision')}
                        </Button>
                      </>
                    )}
                    {request.valid_actions?.includes('withdraw') && (
                      <Button
                        variant="ghost"
                        disabled={busy}
                        onClick={() => void runAction(() => withdrawPriceRequest(request.id))}
                      >
                        {t('withdraw')}
                      </Button>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="leads-drawer__section">
        <h3>{t('priceHistory')}</h3>
        {history.length === 0 ? (
          <p className="leads__meta">{t('noHistory')}</p>
        ) : (
          <ul className="inventory__pricing-history">
            {history.map((price) => (
              <li key={price.id}>
                <strong>{getPriceTypeLabel(price.price_type)}</strong>
                <span>{formatMoney(price.amount, price.currency, locale)}</span>
                <StatusChip>{getPriceStatusLabel(price.status)}</StatusChip>
                <span className="leads__meta">{price.effective_from}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="leads-drawer__section">
        <h3>{t('approvalHistory')}</h3>
        {approvalHistory.length === 0 ? (
          <p className="leads__meta">{t('noApprovalHistory')}</p>
        ) : (
          <ul className="inventory__pricing-approvals">
            {approvalHistory.map((record) => (
              <li key={record.id}>
                <strong>{record.decision}</strong>
                {record.comments && <span>{record.comments}</span>}
                <span className="leads__meta">{record.created_at}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {modalOpen && (
        <PriceChangeModal
          asset={asset}
          initialMode={initialMode}
          currentListPrice={listPrice ? Number(listPrice.amount) : null}
          onClose={() => setModalOpen(false)}
          onSubmitInitial={handleInitialPrice}
          onSubmitChange={handlePriceChange}
        />
      )}
    </div>
  );
}
