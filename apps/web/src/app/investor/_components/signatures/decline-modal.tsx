'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';

import { DEMONSTRATION_DISCLAIMER } from '../../_data/document-types';
import { sanitizePlainText } from '../../_utils/sanitize-text';

export interface DeclineModalProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}

export function DeclineModal({ open, onClose, onConfirm }: DeclineModalProps) {
  const tChrome = useTranslations('investorPortal.chrome');
  const t = useTranslations('investorPortal');
  const [reason, setReason] = useState('');

  if (!open) return null;

  return (
    <div className="inv-sig__modal-overlay" role="dialog" aria-modal="true" aria-labelledby="decline-title">
      <div className="inv-sig__modal">
        <h2 id="decline-title">{tChrome('k326380af5d')}</h2>
        <p className="inv-sig__modal-disclaimer">{DEMONSTRATION_DISCLAIMER}</p>
        <label className="inv-sig__modal-field">
          Reason (optional)
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder={t('placeholders.declineReason')}
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
  const tChrome = useTranslations('investorPortal.chrome');
  return (
    <div className="inv-sig__certificate" role="region" aria-label={tChrome('k3dea71cc80')}>
      <div className="inv-sig__certificate-stamp">{tChrome('k0d55355bd7')}</div>
      <h3>{tChrome('k1386e53066')}</h3>
      <p className="inv-sig__certificate-disclaimer">{DEMONSTRATION_DISCLAIMER}</p>
      <dl>
        <div><dt>{tChrome('k9e5363fa3c')}</dt><dd>{certificateId}</dd></div>
        <div><dt>{tChrome('ke214b8a299')}</dt><dd>{sanitizePlainText(documentTitle)}</dd></div>
        <div><dt>{tChrome('k362166e456')}</dt><dd>{sanitizePlainText(signerName)}</dd></div>
        <div><dt>{tChrome('k0edd6d6666')}</dt><dd>{signedAt}</dd></div>
      </dl>
      <p className="inv-sig__certificate-footer">
        This certificate is generated for UI demonstration only and has no legal effect.
      </p>
    </div>
  );
}
