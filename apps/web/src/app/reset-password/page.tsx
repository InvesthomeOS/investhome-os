'use client';

import { Suspense, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter, useSearchParams } from 'next/navigation';

import { BrandLogo } from '@/components/brand/brand-logo';
import { ApiError } from '@/lib/api/client';
import { completePasswordReset } from '@/lib/api/auth';
import { PublicBrandingProvider, useCompanyBranding } from '@/lib/company/company-context';

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
      if (err instanceof ApiError && err.status === 400 && err.message.toLowerCase().includes('password')) {
        setError(t('invite.ruleLength'));
      } else {
        setError(t('resetInvalid'));
      }
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
          <label className="auth-form__field">
            <span>{t('newPassword')}</span>
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <label className="auth-form__field">
            <span>{t('confirmPassword')}</span>
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={12}
              value={confirm}
              onChange={(event) => setConfirm(event.target.value)}
            />
          </label>
          {error ? <p className="auth-form__error">{error}</p> : null}
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
