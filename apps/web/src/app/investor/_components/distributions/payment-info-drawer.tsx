'use client';

import { useCallback, useEffect, useRef } from 'react';

export interface PaymentInfoDrawerProps {
  open: boolean;
  onClose: () => void;
}

const MOCK_PAYMENT_INFO = {
  primaryMethod: 'ACH Transfer',
  bankName: 'First National Bank',
  accountType: 'Checking',
  accountLast4: '4829',
  routingLast4: '0156',
  beneficiaryName: 'Eleanor Whitmore',
  wireInstructions: 'Available upon request via Investor Relations',
  updatedAt: '2025-03-15',
};

export function PaymentInfoDrawer({ open, onClose }: PaymentInfoDrawerProps) {
  const panelRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener('keydown', handleKeyDown);
    panelRef.current?.focus();
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div className="inv-distributions__drawer-backdrop" onClick={onClose} role="presentation">
      <aside
        ref={panelRef}
        className="inv-distributions__drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="payment-info-title"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="inv-distributions__drawer-header">
          <h2 id="payment-info-title">Payment Information</h2>
          <button type="button" className="inv-distributions__drawer-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </header>

        <p className="inv-distributions__disclaimer" role="note">
          Sensitive account details are masked for security. This is mock data — no real payments are processed.
        </p>

        <dl className="inv-distributions__payment-info">
          <div>
            <dt>Primary Method</dt>
            <dd>{MOCK_PAYMENT_INFO.primaryMethod}</dd>
          </div>
          <div>
            <dt>Bank</dt>
            <dd>{MOCK_PAYMENT_INFO.bankName}</dd>
          </div>
          <div>
            <dt>Account Type</dt>
            <dd>{MOCK_PAYMENT_INFO.accountType}</dd>
          </div>
          <div>
            <dt>Account Number</dt>
            <dd>•••• •••• •••• {MOCK_PAYMENT_INFO.accountLast4}</dd>
          </div>
          <div>
            <dt>Routing Number</dt>
            <dd>•••••{MOCK_PAYMENT_INFO.routingLast4}</dd>
          </div>
          <div>
            <dt>Beneficiary</dt>
            <dd>{MOCK_PAYMENT_INFO.beneficiaryName}</dd>
          </div>
          <div>
            <dt>Wire Instructions</dt>
            <dd>{MOCK_PAYMENT_INFO.wireInstructions}</dd>
          </div>
          <div>
            <dt>Last Updated</dt>
            <dd>{MOCK_PAYMENT_INFO.updatedAt}</dd>
          </div>
        </dl>

        <footer className="inv-distributions__drawer-footer">
          <button type="button" className="investor-header__action-btn" onClick={onClose}>
            Close
          </button>
          <button
            type="button"
            className="investor-header__action-btn investor-header__action-btn--primary"
            onClick={() => {
              /* placeholder */
            }}
          >
            Request Update
          </button>
        </footer>
      </aside>
    </div>
  );
}
