'use client';

import Link from 'next/link';
import type { Route } from 'next';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { getSignatureRequestById, SIGNATURE_STATUS_LABELS } from '../../_data/signature-requests';
import { formatInvestorDate, formatInvestorDateTime, investorProfile } from '../../_data/mock-data';
import { DEMO_VERIFICATION_CODE } from '../../_data/document-types';
import { useDocumentsState } from '../../_state/documents-state';
import { sanitizePlainText } from '../../_utils/sanitize-text';
import { DemonstrationBanner } from '../documents/demonstration-banner';
import { CompletionCertificate, DeclineModal } from './decline-modal';
import { SignatureAuditTrail, SignatureDetailRecipients, SignatureNotFound } from './signature-detail-sections';
import { SignatureCanvas } from './signature-canvas';

const STEPS = ['Review', 'Identity', 'Fields', 'Adopt Signature', 'Confirm', 'Complete'] as const;
type Step = (typeof STEPS)[number];

export interface SigningFlowProps {
  signatureRequestId: string;
}

export function SigningFlow({ signatureRequestId }: SigningFlowProps) {
  const router = useRouter();
  const { signatureRequests, completeSignature } = useDocumentsState();
  const request = useMemo(
    () => signatureRequests.find((s) => s.id === signatureRequestId) ?? getSignatureRequestById(signatureRequestId),
    [signatureRequests, signatureRequestId],
  );

  const [step, setStep] = useState<Step>('Review');
  const [verificationCode, setVerificationCode] = useState('');
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [signatureMethod, setSignatureMethod] = useState<'typed' | 'drawn'>('typed');
  const [typedSignature, setTypedSignature] = useState(investorProfile.name);
  const [drawnSignature, setDrawnSignature] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const currentRecipient = request?.recipients.find((r) => r.isCurrentUser);
  const myFields = useMemo(
    () => request?.fields.filter((f) => f.recipientId === currentRecipient?.id) ?? [],
    [request, currentRecipient],
  );

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const handleComplete = useCallback(() => {
    completeSignature(signatureRequestId);
    setStep('Complete');
  }, [completeSignature, signatureRequestId]);

  if (!request) return <SignatureNotFound />;

  if (request.status === 'completed') {
    return (
      <div className="investor-page inv-sig inv-sig--flow">
        <DemonstrationBanner />
        <CompletionCertificate
          certificateId={request.certificateId ?? `cert-demo-${request.id}`}
          documentTitle={request.documentTitle}
          signedAt={request.completedAt ? formatInvestorDateTime(request.completedAt) : '—'}
          signerName={investorProfile.name}
        />
        <Link href={`/investor/signatures/${request.id}` as Route} className="inv-docs__btn inv-docs__btn--primary">
          Back to Request
        </Link>
      </div>
    );
  }

  const stepIndex = STEPS.indexOf(step);

  return (
    <div className="investor-page inv-sig inv-sig--flow">
      <DemonstrationBanner />

      <header className="inv-sig__flow-header">
        <h1>{request.documentTitle}</h1>
        <p>{request.investmentName}</p>
      </header>

      <nav className="inv-sig__flow-steps" aria-label="Signing steps">
        {STEPS.map((s, i) => (
          <span
            key={s}
            className={`inv-sig__flow-step${i <= stepIndex ? ' inv-sig__flow-step--active' : ''}${i === stepIndex ? ' inv-sig__flow-step--current' : ''}`}
          >
            {i + 1}. {s}
          </span>
        ))}
      </nav>

      <div className="inv-sig__flow-content">
        {step === 'Review' ? (
          <section>
            <h2>Review Document</h2>
            <p>{request.message}</p>
            <p className="inv-sig__flow-meta">Expires {formatInvestorDate(request.expiresAt)}</p>
            <div className="inv-sig__flow-doc-preview">
              <p>Mock document preview — {request.documentTitle}</p>
              <div className="inv-docs__preview-mock-lines">
                {Array.from({ length: 6 }, (_, i) => (
                  <div key={i} className="inv-docs__preview-line" style={{ width: `${50 + (i % 4) * 10}%` }} />
                ))}
              </div>
            </div>
          </section>
        ) : null}

        {step === 'Identity' ? (
          <section>
            <h2>Verify Identity</h2>
            <p>
              Enter the demo verification code: <strong>{DEMO_VERIFICATION_CODE}</strong>
            </p>
            <label className="inv-sig__flow-field">
              Verification Code
              <input
                type="text"
                inputMode="numeric"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                autoComplete="one-time-code"
                aria-describedby="verify-hint"
              />
            </label>
            <p id="verify-hint" className="inv-sig__flow-hint">
              Demo only — use code {DEMO_VERIFICATION_CODE} to proceed.
            </p>
          </section>
        ) : null}

        {step === 'Fields' ? (
          <section>
            <h2>Complete Fields</h2>
            {myFields.map((f) => (
              <label key={f.id} className="inv-sig__flow-field">
                {f.label}{f.required ? ' *' : ''}
                {f.type === 'checkbox' ? (
                  <input
                    type="checkbox"
                    checked={fieldValues[f.id] === 'true'}
                    onChange={(e) =>
                      setFieldValues((prev) => ({ ...prev, [f.id]: e.target.checked ? 'true' : 'false' }))
                    }
                  />
                ) : (
                  <input
                    type={f.type === 'date' ? 'date' : 'text'}
                    value={fieldValues[f.id] ?? (f.type === 'name' ? investorProfile.name : '')}
                    onChange={(e) =>
                      setFieldValues((prev) => ({
                        ...prev,
                        [f.id]: sanitizePlainText(e.target.value, 200),
                      }))
                    }
                    required={f.required}
                  />
                )}
              </label>
            ))}
          </section>
        ) : null}

        {step === 'Adopt Signature' ? (
          <section>
            <h2>Adopt Your Signature</h2>
            <div className="inv-sig__method-toggle">
              <button
                type="button"
                className={signatureMethod === 'typed' ? 'inv-sig__method--active' : undefined}
                onClick={() => setSignatureMethod('typed')}
              >
                Type
              </button>
              <button
                type="button"
                className={signatureMethod === 'drawn' ? 'inv-sig__method--active' : undefined}
                onClick={() => setSignatureMethod('drawn')}
              >
                Draw
              </button>
            </div>
            {signatureMethod === 'typed' ? (
              <label className="inv-sig__flow-field">
                Typed Signature
                <input
                  type="text"
                  value={typedSignature}
                  onChange={(e) => setTypedSignature(sanitizePlainText(e.target.value, 100))}
                  aria-label="Typed signature"
                />
                <div className="inv-sig__typed-preview" aria-hidden="true">
                  {typedSignature || 'Your signature'}
                </div>
              </label>
            ) : (
              <SignatureCanvas onChange={setDrawnSignature} />
            )}
          </section>
        ) : null}

        {step === 'Confirm' ? (
          <section>
            <h2>Confirm & Sign</h2>
            <p>By clicking Complete, you acknowledge this is a demonstration signature only.</p>
            <dl className="inv-sig__confirm-dl">
              <div><dt>Document</dt><dd>{request.documentTitle}</dd></div>
              <div><dt>Signature</dt><dd>{signatureMethod === 'typed' ? typedSignature : 'Drawn signature'}</dd></div>
              <div><dt>Fields completed</dt><dd>{myFields.length}</dd></div>
            </dl>
          </section>
        ) : null}

        {step === 'Complete' ? (
          <section>
            <CompletionCertificate
              certificateId={`cert-demo-${request.id}-${Date.now()}`}
              documentTitle={request.documentTitle}
              signedAt={formatInvestorDateTime(new Date().toISOString())}
              signerName={investorProfile.name}
            />
          </section>
        ) : null}
      </div>

      <footer className="inv-sig__flow-footer">
        {step !== 'Complete' ? (
          <>
            <button
              type="button"
              className="inv-docs__btn inv-docs__btn--ghost"
              disabled={step === 'Review'}
              onClick={() => {
                const prev = STEPS[stepIndex - 1];
                if (prev) setStep(prev);
              }}
            >
              Back
            </button>
            <button
              type="button"
              className="inv-docs__btn inv-docs__btn--primary"
              onClick={() => {
                if (step === 'Identity' && verificationCode !== DEMO_VERIFICATION_CODE) {
                  setToast(`Invalid code. Use demo code ${DEMO_VERIFICATION_CODE}.`);
                  return;
                }
                if (step === 'Adopt Signature') {
                  if (signatureMethod === 'typed' && !typedSignature.trim()) {
                    setToast('Please enter a typed signature.');
                    return;
                  }
                  if (signatureMethod === 'drawn' && !drawnSignature) {
                    setToast('Please draw your signature or switch to typed.');
                    return;
                  }
                }
                if (step === 'Confirm') {
                  handleComplete();
                  return;
                }
                const next = STEPS[stepIndex + 1];
                if (next) setStep(next);
              }}
            >
              {step === 'Confirm' ? 'Complete (Demo)' : 'Continue'}
            </button>
          </>
        ) : (
          <button
            type="button"
            className="inv-docs__btn inv-docs__btn--primary"
            onClick={() => router.push(`/investor/signatures/${request.id}` as Route)}
          >
            Done
          </button>
        )}
      </footer>

      {toast ? <div className="inv-investments__toast" role="status">{toast}</div> : null}
    </div>
  );
}

export interface SignatureDetailViewProps {
  signatureRequestId: string;
}

export function SignatureDetailView({ signatureRequestId }: SignatureDetailViewProps) {
  const { signatureRequests, declineSignature } = useDocumentsState();
  const [declineOpen, setDeclineOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const request = useMemo(
    () => signatureRequests.find((s) => s.id === signatureRequestId) ?? getSignatureRequestById(signatureRequestId),
    [signatureRequests, signatureRequestId],
  );

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(t);
  }, [toast]);

  if (!request) return <SignatureNotFound />;

  const currentRecipient = request.recipients.find((r) => r.isCurrentUser);
  const canSign = request.status === 'action_required' && currentRecipient?.status !== 'signed';

  return (
    <div className="investor-page inv-sig">
      <DemonstrationBanner />
      <Link href={'/investor/signatures' as Route} className="inv-docs__back-link">
        ← Back to Signatures
      </Link>

      <header className="inv-sig__detail-header">
        <div>
          <h1>{request.documentTitle}</h1>
          <p>{request.investmentName} · {request.entityName}</p>
        </div>
        <span className={`inv-sig__status inv-sig__status--${request.status}`}>
          {SIGNATURE_STATUS_LABELS[request.status]}
        </span>
      </header>

      <p className="inv-sig__detail-message">{request.message}</p>

      <dl className="inv-sig__detail-meta">
        <div><dt>Created</dt><dd>{formatInvestorDateTime(request.createdAt)}</dd></div>
        <div><dt>Expires</dt><dd>{formatInvestorDate(request.expiresAt)}</dd></div>
        {request.completedAt ? (
          <div><dt>Completed</dt><dd>{formatInvestorDateTime(request.completedAt)}</dd></div>
        ) : null}
      </dl>

      <div className="inv-sig__detail-actions">
        {canSign ? (
          <Link
            href={`/investor/signatures/${request.id}/sign` as Route}
            className="inv-docs__btn inv-docs__btn--primary"
          >
            Review & Sign
          </Link>
        ) : null}
        {request.status === 'action_required' ? (
          <button
            type="button"
            className="inv-docs__btn inv-docs__btn--danger"
            onClick={() => setDeclineOpen(true)}
          >
            Decline (Demo)
          </button>
        ) : null}
        <Link href={`/investor/documents/${request.documentId}` as Route} className="inv-docs__btn inv-docs__btn--ghost">
          View Document
        </Link>
      </div>

      <SignatureDetailRecipients request={request} />
      <SignatureAuditTrail entries={request.auditTrail} />

      {request.status === 'completed' && request.certificateId ? (
        <CompletionCertificate
          certificateId={request.certificateId}
          documentTitle={request.documentTitle}
          signedAt={request.completedAt ? formatInvestorDateTime(request.completedAt) : '—'}
          signerName={investorProfile.name}
        />
      ) : null}

      <DeclineModal
        open={declineOpen}
        onClose={() => setDeclineOpen(false)}
        onConfirm={() => {
          declineSignature(request.id, '');
          setToast('Signature declined (demo). Status updated locally.');
        }}
      />

      {toast ? <div className="inv-investments__toast" role="status">{toast}</div> : null}
    </div>
  );
}
