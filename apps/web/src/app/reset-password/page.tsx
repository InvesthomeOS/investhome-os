'use client';

import { Suspense, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';

import { BrandLogo } from '@/components/brand/brand-logo';
import { PasswordField } from '@/components/auth/password-field';
import { ApiError } from '@/lib/api/client';
import { completePasswordReset } from '@/lib/api/auth';
import { classifyResetFailure } from '@/lib/auth/password-reset-ux';
import { PublicBrandingProvider, useCompanyBranding } from '@/lib/company/company-context';

const RESET_ERROR_KEYS = {
  too_short: 'resetErrors.tooShort',
  too_long: 'resetErrors.tooLong',
  invalid_chars: 'resetErrors.invalidChars',
  common: 'resetErrors.common',
  trivial: 'resetErrors.trivial',
  identity: 'resetErrors.identity',
  policy: 'resetErrors.policy',
  malformed: 'resetErrors.malformed',
  invalid_link: 'resetErrors.invalidLink',
  expired: 'resetErrors.expired',
  used: 'resetErrors.used',
  rate_limit: 'rateLimited',
  unexpected: 'resetErrors.unexpected',
} as const;

function ResetPasswordForm() {
  const t = useTranslations('auth');
  const { displayName } = useCompanyBranding();
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirm) {
      setError(t('resetMismatch'));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await completePasswordReset(token, password);
      router.replace('/login?reset=1');
    } catch (err) {
      const status = err instanceof ApiError ? err.status : 0;
      const reasonCode = err instanceof ApiError ? err.details?.[0]?.code : null;
      const message = err instanceof ApiError ? err.message : '';
      const kind = classifyResetFailure({ status, reasonCode, message });
      setError(t(RESET_ERROR_KEYS[kind]));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page auth-page--visual">
      <div className="auth-card">
        <div className="auth-card__brand">
          <BrandLogo tone="auto" layout="full" className="auth-card__logo" priority />
        </div>
        <p className="dashboard__eyebrow">{displayName}</p>
        <h1 className="auth-card__title">{t('resetTitle')}</h1>
        <p className="auth-card__subtitle">{t('resetSubtitle')}</p>
        <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
          <PasswordField
            label={t('newPassword')}
            value={password}
            onChange={setPassword}
            autoComplete="new-password"
            showLabel={t('showPassword')}
            hideLabel={t('hidePassword')}
            minLength={12}
            testId="reset-new-password"
          />
          <ul className="auth-form__rules">
            <li>{t('resetRules.length')}</li>
            <li>{t('resetRules.identity')}</li>
            <li>{t('resetRules.common')}</li>
          </ul>
          <PasswordField
            label={t('confirmPassword')}
            value={confirm}
            onChange={setConfirm}
            autoComplete="new-password"
            showLabel={t('showPassword')}
            hideLabel={t('hidePassword')}
            minLength={12}
            testId="reset-confirm-password"
          />
          {error ? (
            <p className="auth-form__error" role="alert">
              {error}
            </p>
          ) : null}
          <button className="auth-form__submit" type="submit" disabled={submitting || !token}>
            {submitting ? t('submitting') : t('resetSubmit')}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <PublicBrandingProvider>
      <Suspense fallback={<div className="auth-page auth-page--visual" />}>
        <ResetPasswordForm />
      </Suspense>
    </PublicBrandingProvider>
  );
}
