'use client';

import { Suspense, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';

import { BrandLogo } from '@/components/brand/brand-logo';
import { MfaRequiredEnrollForm } from '@/components/auth/mfa-required-enroll-form';
import { MfaVerifyForm } from '@/components/auth/mfa-verify-form';
import { ApiError } from '@/lib/api/client';
import { requestPasswordReset } from '@/lib/api/auth';
import { AuthProvider, useAuth } from '@/lib/auth/auth-context';
import { mapMfaHttpError } from '@/lib/auth/mfa-flow';
import { PublicBrandingProvider, useCompanyBranding } from '@/lib/company/company-context';

function LoginForm() {
  const t = useTranslations('auth');
  const { displayName, slogan } = useCompanyBranding();
  const searchParams = useSearchParams();
  const { login, completeMfaLogin, cancelMfaLogin, finishRequiredEnrollment, cancelEnrollment, mfaPending, enrollmentPending } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotMessage, setForgotMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password, { next: searchParams.get('next') });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError(t('errors.invalidCredentials'));
        } else if (err.status === 403) {
          setError(t('errors.accountInactive'));
        } else if (err.status === 429) {
          setError(t(`mfa.errors.${mapMfaHttpError(429)}`));
        } else if (err.status === 503 || err.status === 502 || err.status === 504) {
          setError(t(`mfa.errors.${mapMfaHttpError(err.status)}`));
        } else {
          setError(t('errors.loginFailed'));
        }
      } else {
        setError(t('errors.loginFailed'));
      }
    } finally {
      setSubmitting(false);
      setPassword('');
    }
  };

  return (
    <div className="auth-page auth-page--visual">
      <div className="auth-card">
        <div className="auth-card__brand">
          <BrandLogo tone="auto" layout="full" className="auth-card__logo" priority />
        </div>
        <p className="dashboard__eyebrow">{displayName}</p>

        {mfaPending ? (
          <MfaVerifyForm onVerify={completeMfaLogin} onBack={cancelMfaLogin} />
        ) : enrollmentPending ? (
          <MfaRequiredEnrollForm
            challengeToken={enrollmentPending.token}
            onComplete={finishRequiredEnrollment}
            onBack={cancelEnrollment}
          />
        ) : (
          <>
            <h1 className="auth-card__title">{slogan ?? t('title')}</h1>
            <p className="auth-card__subtitle">{t('subtitle')}</p>

            {searchParams.get('next') && <p className="auth-card__hint">{t('redirectHint')}</p>}
            {searchParams.get('reset') === '1' ? <p className="auth-card__hint">{t('resetSuccess')}</p> : null}

            <form className="auth-form" onSubmit={(event) => void handleSubmit(event)} data-testid="login-password-form">
              <label className="auth-form__field">
                <span>{t('emailLabel')}</span>
                <input
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </label>

              <label className="auth-form__field">
                <span>{t('passwordLabel')}</span>
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>

              {error && <p className="auth-form__error">{error}</p>}

              <button
                className="auth-form__hint"
                type="button"
                onClick={() => {
                  setForgotOpen(true);
                  setForgotMessage(null);
                }}
              >
                {t('forgotPassword')}
              </button>

              {forgotOpen ? (
                <div className="auth-card__hint">
                  <button
                    type="button"
                    disabled={submitting || !email.trim()}
                    onClick={() => {
                      setSubmitting(true);
                      setForgotMessage(null);
                      void requestPasswordReset(email.trim())
                        .then(() => setForgotMessage(t('forgotSent')))
                        .catch(() => setForgotMessage(t('forgotSent')))
                        .finally(() => setSubmitting(false));
                    }}
                  >
                    {t('forgotPassword')}
                  </button>
                  {forgotMessage ? <p>{forgotMessage}</p> : null}
                </div>
              ) : null}

              <button className="auth-form__submit" type="submit" disabled={submitting}>
                {submitting ? t('submitting') : t('submit')}
              </button>
            </form>

            {process.env.NODE_ENV !== 'production' ? (
              <div className="auth-card__demo">
                <p>{t('demoTitle')}</p>
                <ul>
                  <li>{t('demoAdmin')}</li>
                  <li>{t('demoSales')}</li>
                  <li>{t('demoReadOnly')}</li>
                </ul>
                <p className="auth-card__demo-password">{t('demoPassword')}</p>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <PublicBrandingProvider>
      <AuthProvider>
        <Suspense fallback={<div className="auth-page auth-page--visual" />}>
          <LoginForm />
        </Suspense>
      </AuthProvider>
    </PublicBrandingProvider>
  );
}
