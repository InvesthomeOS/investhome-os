'use client';

import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { OtpauthQr } from '@/components/auth/otpauth-qr';
import { confirmMfaEnrollment, startMfaEnrollment } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import {
  formatManualSetupKey,
  mapEnrollHttpError,
  parseOtpauthSecret,
} from '@/lib/auth/mfa-flow';

type EnrollStep = 'idle' | 'setup' | 'recovery' | 'enabled';

export function MfaEnrollCard({
  mfaEnabled,
  onEnabled,
}: {
  mfaEnabled: boolean;
  onEnabled: () => Promise<void> | void;
}) {
  const t = useTranslations('profile.mfa');
  const [step, setStep] = useState<EnrollStep>(mfaEnabled ? 'enabled' : 'idle');
  const [otpauthUri, setOtpauthUri] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const manualKey = useMemo(() => {
    const secret = parseOtpauthSecret(otpauthUri ?? '');
    return secret ? formatManualSetupKey(secret) : '';
  }, [otpauthUri]);

  const mapError = (err: unknown) => {
    const status = err instanceof ApiError ? err.status : 0;
    return t(`errors.${mapEnrollHttpError(status)}`);
  };

  const handleStart = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const started = await startMfaEnrollment();
      setOtpauthUri(started.otpauth_uri);
      setStep('setup');
    } catch (err) {
      setError(mapError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const submitted = code.trim();
    setCode('');
    try {
      const confirmed = await confirmMfaEnrollment(submitted);
      setOtpauthUri(null);
      setRecoveryCodes(confirmed.recovery_codes ?? []);
      setStep('recovery');
    } catch (err) {
      setError(mapError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleAckRecovery = async () => {
    setRecoveryCodes(null);
    setStep('enabled');
    await onEnabled();
  };

  return (
    <section className="admin-detail mfa-enroll" data-testid="mfa-enroll-card">
      <h2>{t('title')}</h2>

      {step === 'enabled' && (
        <p className="auth-form__success" data-testid="mfa-enroll-enabled">
          {t('statusEnabled')}
        </p>
      )}

      {step === 'idle' && (
        <>
          <p>{t('statusDisabled')}</p>
          {error && (
            <p className="auth-form__error" role="alert">
              {error}
            </p>
          )}
          <button
            className="auth-form__submit"
            type="button"
            onClick={() => void handleStart()}
            disabled={submitting}
            data-testid="mfa-enroll-enable"
          >
            {submitting ? t('enabling') : t('enable')}
          </button>
        </>
      )}

      {step === 'setup' && otpauthUri && (
        <>
          <p>{t('scanQr')}</p>
          <OtpauthQr uri={otpauthUri} label={t('scanQr')} />
          {manualKey && (
            <p className="mfa-manual-key">
              <span>{t('manualKey')}</span>
              <code data-testid="mfa-enroll-manual-key">{manualKey}</code>
            </p>
          )}
          <form className="auth-form" onSubmit={(event) => void handleConfirm(event)}>
            <label className="auth-form__field">
              <span>{t('confirmLabel')}</span>
              <input
                data-testid="mfa-enroll-code"
                name="enroll_code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                minLength={6}
                required
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))}
              />
            </label>
            {error && (
              <p className="auth-form__error" role="alert">
                {error}
              </p>
            )}
            <button
              className="auth-form__submit"
              type="submit"
              disabled={submitting}
              data-testid="mfa-enroll-confirm"
            >
              {submitting ? t('confirming') : t('confirm')}
            </button>
          </form>
        </>
      )}

      {step === 'recovery' && recoveryCodes && (
        <div className="mfa-recovery" data-testid="mfa-enroll-recovery">
          <p className="auth-form__success" data-testid="mfa-enroll-enabled">
            {t('statusEnabled')}
          </p>
          <h3>{t('recoveryTitle')}</h3>
          <p className="mfa-recovery__warning">{t('recoveryWarning')}</p>
          <ul className="mfa-recovery__list">
            {recoveryCodes.map((item) => (
              <li key={item}>
                <code>{item}</code>
              </li>
            ))}
          </ul>
          <button
            className="auth-form__submit"
            type="button"
            onClick={() => void handleAckRecovery()}
            data-testid="mfa-enroll-recovery-ack"
          >
            {t('recoveryAck')}
          </button>
        </div>
      )}
    </section>
  );
}
