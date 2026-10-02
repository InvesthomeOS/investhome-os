'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';

import { BrandLogo } from '@/components/brand/brand-logo';
import { ApiError } from '@/lib/api/client';
import { acceptInvite, fetchInvitePreview, type InvitePreview } from '@/lib/api/auth';
import { PublicBrandingProvider, useCompanyBranding } from '@/lib/company/company-context';

function InviteAcceptForm() {
  const t = useTranslations('auth');
  const { displayName } = useCompanyBranding();
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const token = typeof params.token === 'string' ? params.token : '';
  const [preview, setPreview] = useState<InvitePreview | null>(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchInvitePreview(token)
      .then((body) => {
        if (!cancelled) {
          setPreview(body);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setPreview(null);
          setError(err instanceof ApiError && err.status === 404 ? t('invite.invalid') : t('invite.failed'));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t, token]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (password !== confirm) {
      setError(t('invite.mismatch'));
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await acceptInvite(token, password);
      router.replace('/login');
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(err.message);
      } else if (err instanceof ApiError && err.status === 404) {
        setError(t('invite.invalid'));
      } else {
        setError(t('invite.failed'));
      }
    } finally {
      setSubmitting(false);
      setPassword('');
      setConfirm('');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card__brand">
          <BrandLogo tone="auto" layout="full" className="auth-card__logo" priority />
        </div>
        <p className="dashboard__eyebrow">{displayName}</p>
        <h1 className="auth-card__title">{t('invite.title')}</h1>
        <p className="auth-card__subtitle">{t('invite.subtitle')}</p>
        {preview ? <p className="auth-card__hint">{preview.email}</p> : null}
        {loading ? <p className="auth-card__hint">{t('submitting')}</p> : null}
        {error && !preview ? <p className="auth-form__error">{error}</p> : null}
        {preview ? (
          <form className="auth-form" onSubmit={(event) => void handleSubmit(event)}>
            <label className="auth-form__field">
              <span>{t('invite.passwordLabel')}</span>
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={256}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <label className="auth-form__field">
              <span>{t('invite.confirmLabel')}</span>
              <input
                type="password"
                autoComplete="new-password"
                required
                minLength={12}
                maxLength={256}
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
              />
            </label>
            {error ? <p className="auth-form__error">{error}</p> : null}
            <button className="auth-form__submit" type="submit" disabled={submitting}>
              {submitting ? t('invite.submitting') : t('invite.submit')}
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
}

export default function InviteAcceptPage() {
  return (
    <PublicBrandingProvider>
      <InviteAcceptForm />
    </PublicBrandingProvider>
  );
}
