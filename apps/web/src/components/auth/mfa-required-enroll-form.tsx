'use client';

import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { OtpauthQr } from '@/components/auth/otpauth-qr';
import { confirmRequiredMfaEnrollment, startRequiredMfaEnrollment, type CurrentUser } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';
import {
  formatManualSetupKey,
  mapEnrollHttpError,
  parseOtpauthSecret,
} from '@/lib/auth/mfa-flow';

type EnrollStep = 'starting' | 'setup' | 'recovery';

export function MfaRequiredEnrollForm({
  challengeToken,
  onComplete,
  onBack,
}: {
  challengeToken: string;
  onComplete: (user: CurrentUser) => void;
  onBack: () => void;
}) {
  const t = useTranslations('auth.enroll');
  const [step, setStep] = useState<EnrollStep>('starting');
  const [otpauthUri, setOtpauthUri] = useState<string | null>(null);
  const [code, setCode] = useState('');
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [completedUser, setCompletedUser] = useState<CurrentUser | null>(null);
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

  useEffect(() => {
    let cancelled = false;
    const start = async () => {
      setSubmitting(true);
      setError(null);
      try {
        const started = await startRequiredMfaEnrollment(challengeToken);
        if (cancelled) return;
        setOtpauthUri(started.otpauth_uri);
        setStep('setup');
      } catch (err) {
        if (!cancelled) setError(mapError(err));
      } finally {
        if (!cancelled) setSubmitting(false);
      }
    };
    void start();
    return () => {
      cancelled = true;
    };
    // challengeToken is the enrollment step identity; restart only when it changes.
  }, [challengeToken]);

  const handleConfirm = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    const submitted = code.trim();
    setCode('');
    try {
      const confirmed = await confirmRequiredMfaEnrollment(challengeToken, submitted);
      setOtpauthUri(null);
      setRecoveryCodes(confirmed.recovery_codes ?? []);
      setCompletedUser(confirmed.user);
      setStep('recovery');
    } catch (err) {
      setError(mapError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleAckRecovery = () => {
    const user = completedUser;
    setRecoveryCodes(null);
    setCompletedUser(null);
    if (user) {
      onComplete(user);
    }
  };

  return (
    <div className="auth-card__mfa" data-testid="mfa-enroll-required-screen">
      <h1 className="auth-card__title">{t('title')}</h1>
      <p className="auth-card__subtitle">{t('subtitle')}</p>

      {step === 'starting' && (
        <>
          {error && (
            <p className="auth-form__error" role="alert" data-testid="mfa-enroll-required-error">
              {error}
            </p>
          )}
          {!error && <p>{t('starting')}</p>}
        </>
      )}

      {step === 'setup' && otpauthUri && (
        <>
          <p>{t('scanQr')}</p>
          <OtpauthQr uri={otpauthUri} label={t('scanQr')} />
          {manualKey && (
            <p className="mfa-manual-key">
              <span>{t('manualKey')}</span>
              <code data-testid="mfa-enroll-required-manual-key">{manualKey}</code>
            </p>
          )}
          <form className="auth-form" onSubmit={(event) => void handleConfirm(event)}>
            <label className="auth-form__field">
              <span>{t('confirmLabel')}</span>
              <input
                data-testid="mfa-enroll-required-code"
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
              <p className="auth-form__error" role="alert" data-testid="mfa-enroll-required-error">
                {error}
              </p>
            )}
            <button
              className="auth-form__submit"
              type="submit"
              disabled={submitting}
              data-testid="mfa-enroll-required-confirm"
            >
              {submitting ? t('confirming') : t('confirm')}
            </button>
          </form>
        </>
      )}

      {step === 'recovery' && recoveryCodes && (
        <div className="mfa-recovery" data-testid="mfa-enroll-required-recovery">
          <p className="auth-form__success">{t('statusEnabled')}</p>
          <h2>{t('recoveryTitle')}</h2>
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
            onClick={handleAckRecovery}
            data-testid="mfa-enroll-required-recovery-ack"
          >
            {t('recoveryAck')}
          </button>
        </div>
      )}

      {step !== 'recovery' && (
        <button className="auth-form__back" type="button" onClick={onBack} data-testid="mfa-enroll-required-back">
          {t('back')}
        </button>
      )}
    </div>
  );
}
