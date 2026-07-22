'use client';

import { useState } from 'react';

import { DEMONSTRATION_DISCLAIMER } from '../../_data/document-types';
import { sanitizePlainText } from '../../_utils/sanitize-text';

export interface DeclineModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}

export function DeclineModal({ open, onClose, onConfirm }: DeclineModalProps) {
  const [reason, setReason] = useState('');

  if (!open) return null;

  return (
    <div className="inv-sig__modal-overlay" role="dialog" aria-modal="true" aria-labelledby="decline-title">
      <div className="inv-sig__modal">
        <h2 id="decline-title">Decline to Sign</h2>
        <p className="inv-sig__modal-disclaimer">{DEMONSTRATION_DISCLAIMER}</p>
        <label className="inv-sig__modal-field">
          Reason (optional)
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Explain why you are declining…"
          />
        </label>
        <div className="inv-sig__modal-actions">
          <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="inv-docs__btn inv-docs__btn--danger"
            onClick={() => {
              onConfirm(sanitizePlainText(reason, 300));
              setReason('');
              onClose();
            }}
          >
            Decline (Demo)
          </button>
        </div>
      </div>
    </div>
  );
}

export interface CompletionCertificateProps {
  certificateId: string;
  documentTitle: string;
  signedAt: string;
  signerName: string;
}

export function CompletionCertificate({
  certificateId,
  documentTitle,
  signedAt,
  signerName,
}: CompletionCertificateProps) {
  return (
    <div className="inv-sig__certificate" role="region" aria-label="Completion certificate">
      <div className="inv-sig__certificate-stamp">NOT LEGALLY VALID</div>
      <h3>Demo Completion Certificate</h3>
      <p className="inv-sig__certificate-disclaimer">{DEMONSTRATION_DISCLAIMER}</p>
      <dl>
        <div><dt>Certificate ID</dt><dd>{certificateId}</dd></div>
        <div><dt>Document</dt><dd>{sanitizePlainText(documentTitle)}</dd></div>
        <div><dt>Signer</dt><dd>{sanitizePlainText(signerName)}</dd></div>
        <div><dt>Signed At</dt><dd>{signedAt}</dd></div>
      </dl>
      <p className="inv-sig__certificate-footer">
        This certificate is generated for UI demonstration only and has no legal effect.
      </p>
    </div>
  );
}
