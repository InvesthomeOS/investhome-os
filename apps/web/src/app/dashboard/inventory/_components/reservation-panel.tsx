'use client';

import { useCallback, useEffect, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { Button, StatusChip } from '@investhome/ui';

import {
  approveReservation,
  cancelReservation,
  convertReservation,
  fetchReservationHistoryByAsset,
  formatCountdown,
  formatDateTime,
  markDepositReceived,
  releaseSoftHold,
  requestReservation,
  type InventoryAsset,
  type InventoryReservation,
  type ReservationHistoryEntry,
} from '@/lib/api/inventory';
import { hasPermission } from '@/lib/api/auth';
import { useAuth } from '@/lib/auth/auth-context';
import { useInventoryLabels } from '@/lib/i18n/inventory-labels';

interface ReservationPanelProps {
  asset: InventoryAsset;
  onChanged: () => void;
}

export function ReservationPanel({ asset, onChanged }: ReservationPanelProps) {
  const t = useTranslations('inventory.reservation');
  const tCommon = useTranslations('common');
  const locale = useLocale();
  const { user } = useAuth();
  const { getReservationRecordLabel } = useInventoryLabels();
  const [history, setHistory] = useState<ReservationHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [approvalNotes, setApprovalNotes] = useState('');

  const canRelease = user ? hasPermission(user, 'inventory', 'release_hold') : false;
  const canRequest = user ? hasPermission(user, 'inventory', 'request_reservation') : false;
  const canApprove = user ? hasPermission(user, 'inventory', 'approve_reservation') : false;
  const canCancel = user ? hasPermission(user, 'inventory', 'cancel_reservation') : false;
  const canDeposit = user ? hasPermission(user, 'inventory', 'mark_deposit_received') : false;
  const canConvert = user ? hasPermission(user, 'inventory', 'convert_reservation') : false;

  const active = history.find((entry) =>
    ['active', 'requested', 'approved', 'deposit_pending', 'deposit_received'].includes(
      entry.reservation.status,
    ),
  )?.reservation;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const rows = await fetchReservationHistoryByAsset(asset.id);
      setHistory(rows);
    } catch {
      setHistory([]);
    } finally {
      setLoading(false);
    }
  }, [asset.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const runAction = async (action: () => Promise<InventoryReservation>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
      await load();
      onChanged();
    } catch {
      setError(t('actionError'));
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <p className="leads__meta">{tCommon('loading')}</p>;

  return (
    <div className="inventory__reservation-panel">
      {active ? (
        <section className="leads-drawer__section">
          <h3>{t('activeReservation')}</h3>
          <dl className="leads-drawer__grid">
            <div>
              <dt>{t('status')}</dt>
              <dd>
                <StatusChip tone={active.status === 'active' ? 'warning' : 'info'}>
                  {getReservationRecordLabel(active.status)}
                </StatusChip>
              </dd>
            </div>
            <div>
              <dt>{t('party')}</dt>
              <dd>{active.party_name ?? tCommon('noValue')}</dd>
            </div>
            {active.expires_at && (
              <div>
                <dt>{t('expiresAt')}</dt>
                <dd>
                  {formatDateTime(active.expires_at, locale)}
                  {' · '}
                  {formatCountdown(active.seconds_until_expiry)}
                </dd>
              </div>
            )}
            {active.deposit_amount && (
              <div>
                <dt>{t('depositAmount')}</dt>
                <dd>
                  {active.deposit_amount} {active.deposit_currency ?? asset.currency}
                </dd>
              </div>
            )}
          </dl>

          <div className="inventory__reservation-actions">
            {canRelease && active.valid_actions?.includes('release') && (
              <Button variant="secondary" disabled={busy} onClick={() => void runAction(() => releaseSoftHold(active.id))}>
                {t('releaseHold')}
              </Button>
            )}
            {canRequest && active.valid_actions?.includes('request') && (
              <Button variant="secondary" disabled={busy} onClick={() => void runAction(() => requestReservation(active.id))}>
                {t('requestReservation')}
              </Button>
            )}
            {canApprove && active.valid_actions?.includes('approve') && (
              <>
                <textarea
                  value={approvalNotes}
                  onChange={(event) => setApprovalNotes(event.target.value)}
                  placeholder={t('approvalNotes')}
                  rows={2}
                />
                <Button
                  variant="primary"
                  disabled={busy}
                  onClick={() => void runAction(() => approveReservation(active.id, approvalNotes || null))}
                >
                  {t('approve')}
                </Button>
              </>
            )}
            {canDeposit && active.valid_actions?.includes('deposit_received') && (
              <Button
                variant="secondary"
                disabled={busy}
                onClick={() => void runAction(() => markDepositReceived(active.id))}
              >
                {t('markDepositReceived')}
              </Button>
            )}
            {canConvert && active.valid_actions?.includes('convert') && (
              <Button variant="primary" disabled={busy} onClick={() => void runAction(() => convertReservation(active.id))}>
                {t('convert')}
              </Button>
            )}
            {canCancel && active.valid_actions?.includes('cancel') && (
              <Button variant="danger" disabled={busy} onClick={() => void runAction(() => cancelReservation(active.id))}>
                {t('cancel')}
              </Button>
            )}
          </div>
        </section>
      ) : (
        <p className="leads__meta">{t('noActiveReservation')}</p>
      )}

      {error && <p className="leads__state leads__state--error">{error}</p>}

      <section className="leads-drawer__section">
        <h3>{t('history')}</h3>
        {history.length === 0 ? (
          <p className="leads__meta">{t('noHistory')}</p>
        ) : (
          <ul className="inventory__reservation-history">
            {history.map((entry) => (
              <li key={entry.reservation.id}>
                <strong>{getReservationRecordLabel(entry.reservation.status)}</strong>
                <span>{formatDateTime(entry.reservation.created_at, locale)}</span>
                {entry.reservation.party_name && <span>{entry.reservation.party_name}</span>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
