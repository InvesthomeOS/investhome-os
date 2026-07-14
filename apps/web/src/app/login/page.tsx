'use client';

import { Suspense, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useSearchParams } from 'next/navigation';

import { ApiError } from '@/lib/api/client';
import { AuthProvider, useAuth } from '@/lib/auth/auth-context';

function LoginForm() {
  const t = useTranslations('auth');
  const searchParams = useSearchParams();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError(t('errors.invalidCredentials'));
        } else if (err.status === 403) {
          setError(t('errors.accountInactive'));
        } else {
          setError(err.message);
        }
      } else {
        setError(t('errors.loginFailed'));
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <p className="dashboard__eyebrow">{t('eyebrow')}</p>
        <h1 className="auth-card__title">{t('title')}</h1>
        <p className="auth-card__subtitle">{t('subtitle')}</p>

        {searchParams.get('next') && (
          <p className="auth-card__hint">{t('redirectHint')}</p>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
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

          <button className="auth-form__submit" type="submit" disabled={submitting}>
            {submitting ? t('submitting') : t('submit')}
          </button>
        </form>

        <div className="auth-card__demo">
          <p>{t('demoTitle')}</p>
          <ul>
            <li>{t('demoAdmin')}</li>
            <li>{t('demoSales')}</li>
            <li>{t('demoReadOnly')}</li>
          </ul>
          <p className="auth-card__demo-password">{t('demoPassword')}</p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <AuthProvider>
      <Suspense fallback={<div className="auth-page" />}>
        <LoginForm />
      </Suspense>
    </AuthProvider>
  );
}
